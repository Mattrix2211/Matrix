"""Limitation progressive des connexions (AC-18).

Architecture retenue et conséquences pour les utilisateurs légitimes :
- le compteur est tenu par couple (identifiant, source réseau) : un tiers qui s'acharne sur un identifiant depuis un autre poste
  ne bloque pas le marin depuis son poste habituel ; deux marins qui partagent un poste ou une adresse n'ont pas de compteur
  commun puisque leurs identifiants diffèrent ;
- chaque série d'échecs au-delà du seuil bloque ce couple pour une durée qui double (15, 30, 60 minutes… jusqu'au plafond) ;
- un compteur global par identifiant (source « * ») détecte l'attaque répartie sur plusieurs postes : il ne bloque que les
  sources inconnues de cet identifiant, jamais celles qui s'y sont déjà connectées avec succès durant la période de conservation ;
- l'adresse seule n'est jamais le critère ; elle n'est que la moitié du couple. Limite résiduelle : un tiers qui agit depuis le
  poste même du marin peut le bloquer sur ce poste (accès physique, hors périmètre) ;
- les incréments sont des UPDATE atomiques (SQLite comme PostgreSQL) ; un échec n'est compté qu'une fois par requête ;
- les compteurs inactifs sont purgés (tâche quotidienne et purge opportuniste) ; l'AuditLog n'est jamais purgé par ce module.
"""
import time
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from django.utils import timezone

from .models import AuditLog, CompteurConnexion

SOURCE_GLOBALE = "*"
FACTEUR_GLOBAL = 5  # le compteur global déclenche à FACTEUR_GLOBAL fois le seuil d'un couple


def cle_identifiant(identifiant):
    return (identifiant or "").strip().lower()[:150]


def source_de(request):
    """Adresse réseau directe de la requête (jamais un en-tête transmis par le client)."""
    base = getattr(request, "_request", request)
    meta = getattr(base, "META", None) or {}
    return (meta.get("REMOTE_ADDR") or "inconnue")[:64]


def _compteur(identifiant, source, creer=False):
    if not creer:
        return CompteurConnexion.objects.filter(identifiant=identifiant, source=source).first()
    try:
        compteur, _ = CompteurConnexion.objects.get_or_create(
            identifiant=identifiant, source=source, defaults={"derniere_activite": timezone.now()})
    except IntegrityError:  # création simultanée : l'autre processus l'a déjà faite
        compteur = CompteurConnexion.objects.get(identifiant=identifiant, source=source)
    return compteur


def _duree_blocage(niveau):
    minutes = min(settings.VERROUILLAGE_CONNEXION_MINUTES * (2 ** niveau), settings.VERROUILLAGE_CONNEXION_PLAFOND_MINUTES)
    return timedelta(minutes=minutes)


def _source_connue(identifiant, source, maintenant):
    compteur = _compteur(identifiant, source)
    limite = maintenant - timedelta(days=settings.CONSERVATION_COMPTEURS_JOURS)
    return bool(compteur and compteur.derniere_reussite and compteur.derniere_reussite >= limite)


def est_limite(identifiant, source):
    """Vrai si ce couple (ou, pour une source inconnue, l'identifiant entier) est en attente de fin de blocage."""
    identifiant, maintenant = cle_identifiant(identifiant), timezone.now()
    couple = _compteur(identifiant, source)
    if couple and couple.bloque_jusqua and couple.bloque_jusqua > maintenant:
        return True
    globale = _compteur(identifiant, SOURCE_GLOBALE)
    if globale and globale.bloque_jusqua and globale.bloque_jusqua > maintenant:
        return not _source_connue(identifiant, source, maintenant)
    return False


def _echec_sur(identifiant, source, seuil, audit):
    """Incrément atomique ; au franchissement du seuil, blocage progressif (une seule trace d'audit par blocage)."""
    maintenant = timezone.now()
    compteur = _compteur(identifiant, source, creer=True)
    if compteur.niveau and maintenant - compteur.derniere_activite > timedelta(minutes=settings.VERROUILLAGE_CONNEXION_PLAFOND_MINUTES):
        # Le blocage progressif retombe après une période calme : un tiers ne peut pas l'entretenir indéfiniment.
        CompteurConnexion.objects.filter(pk=compteur.pk).update(niveau=0)
    CompteurConnexion.objects.filter(pk=compteur.pk).update(essais=F("essais") + 1, derniere_activite=maintenant)
    compteur.refresh_from_db()
    if compteur.essais >= seuil:
        # La remise à zéro conditionnelle garantit qu'un seul des accès concurrents prononce le blocage.
        bloque = CompteurConnexion.objects.filter(pk=compteur.pk, essais__gte=seuil).update(
            essais=0, niveau=F("niveau") + 1, bloque_jusqua=maintenant + _duree_blocage(compteur.niveau))
        if bloque:
            AuditLog.objects.create(
                actor=None, action=audit, details=f"identifiant={identifiant}; source={source}; niveau={compteur.niveau + 1}")


REPRISES = 8  # SQLite sérialise les écritures : une base momentanément verrouillée se rejoue, l'échec doit être compté


def _avec_reprises(operation):
    for essai in range(REPRISES):
        try:
            return operation()
        except OperationalError:
            if essai == REPRISES - 1:
                raise
            time.sleep(0.02 * (essai + 1))


def _compte_existant(identifiant):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(username__iexact=identifiant).exists()


def enregistrer_echec(identifiant, source, seuil=None, existe=None):
    """Compte un échec. Un identifiant inexistant n'ouvre aucun compteur (sinon un flot d'identifiants inventés ferait croître
    la table sans borne) ; il est refusé comme les autres, sans différence visible. `seuil` : essais d'un code de réinitialisation,
    sans compteur global."""
    identifiant = cle_identifiant(identifiant)
    if not identifiant:
        return
    if existe is None:
        existe = _compte_existant(identifiant)
    if not existe:
        return

    def compter():
        with transaction.atomic():
            _echec_sur(identifiant, source, seuil or settings.TENTATIVES_CONNEXION_MAX, "connexion_limitee")
            if seuil is None:
                _echec_sur(identifiant, SOURCE_GLOBALE, settings.TENTATIVES_CONNEXION_MAX * FACTEUR_GLOBAL, "connexion_limitee_globale")

    try:
        _avec_reprises(compter)
    except OperationalError:
        pass  # base durablement occupée : la connexion est refusée de toute façon, l'échec n'est pas compté
    purger_compteurs(opportuniste=True)


def enregistrer_reussite(identifiant, source):
    identifiant, maintenant = cle_identifiant(identifiant), timezone.now()
    try:
        compteur = _compteur(identifiant, source, creer=True)
        CompteurConnexion.objects.filter(pk=compteur.pk).update(
            essais=0, niveau=0, bloque_jusqua=None, derniere_reussite=maintenant, derniere_activite=maintenant)
        CompteurConnexion.objects.filter(identifiant=identifiant, source=SOURCE_GLOBALE).update(essais=0)
    except OperationalError:
        pass


def effacer_compteurs(identifiant):
    CompteurConnexion.objects.filter(identifiant=cle_identifiant(identifiant)).delete()


def purger_compteurs(opportuniste=False):
    """Supprime les compteurs inactifs depuis plus de `CONSERVATION_COMPTEURS_JOURS` ; renvoie leur nombre.

    En mode opportuniste (appelé à chaque échec), la purge ne tourne qu'une fois sur cinquante environ."""
    if opportuniste and timezone.now().microsecond % 50:
        return 0
    limite = timezone.now() - timedelta(days=settings.CONSERVATION_COMPTEURS_JOURS)
    supprimes, _ = CompteurConnexion.objects.filter(derniere_activite__lt=limite).delete()
    return supprimes
