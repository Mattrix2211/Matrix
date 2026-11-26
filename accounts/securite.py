"""Limitation progressive des connexions (AC-18).

Architecture retenue et conséquences pour les utilisateurs légitimes :
- la source est l'adresse réseau directe de la requête ; l'en-tête X-Forwarded-For n'est cru que si cette adresse est celle d'un
  mandataire inverse déclaré de confiance (`MATRIX_MANDATAIRES_DE_CONFIANCE`), et la source retenue est alors la première adresse
  non déclarée de confiance en remontant la chaîne depuis la droite ; une adresse IPv6 est ramenée à son préfixe /64 ;
- le compteur est tenu par couple (identifiant, source) : un tiers qui s'acharne sur un identifiant depuis une autre source ne
  bloque pas le marin ; deux marins qui partagent une adresse ont des identifiants, donc des compteurs, distincts ;
- chaque série d'échecs au-delà du seuil bloque ce couple pour une durée qui double (15, 30, 60 minutes… jusqu'au plafond) ;
- une adresse réellement partagée (poste commun, mandataire non déclaré) ne suffit pas à distinguer un tiers du titulaire : le
  titulaire qui s'est déjà connecté depuis son poste porte un « poste connu » (cookie signé, lié à l'identifiant, révocable côté
  serveur). Ses essais sont comptés sur ce poste seul et ne dépendent plus du blocage de l'adresse ; un tiers sans ce cookie reste
  limité par sa source. Un nouveau poste placé derrière une adresse attaquée attend la fin du blocage (plafonné) ou passe par une
  réinitialisation ;
- un compteur global par identifiant (source « * ») détecte l'attaque répartie sur plusieurs postes : il ne bloque que les
  sources inconnues de cet identifiant, jamais un poste connu ;
- un identifiant inexistant n'ouvre aucun compteur (table bornée) et reçoit la même réponse, au même coût de calcul ;
- les incréments sont des UPDATE atomiques (SQLite comme PostgreSQL) ; un échec n'est compté qu'une fois par requête ;
- les compteurs inactifs sont purgés (tâche quotidienne et purge opportuniste) ; l'AuditLog n'est jamais purgé par ce module.
Limites : aucun dispositif ne supprime tout déni de service ; un tiers maître de la même adresse et du poste du marin (accès
physique), ou de la base de données, sort du périmètre de ces contrôles.
"""
import ipaddress
import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from django.utils import timezone

from .models import AuditLog, CompteurConnexion

SOURCE_GLOBALE = "*"
FACTEUR_GLOBAL = 5  # le compteur global déclenche à FACTEUR_GLOBAL fois le seuil d'un couple


def cle_identifiant(identifiant):
    return (identifiant or "").strip().lower()[:150]


def _adresse(texte):
    try:
        return ipaddress.ip_address((texte or "").strip())
    except ValueError:
        return None


def _normalisee(adresse):
    """IPv4 telle quelle ; IPv6 ramenée à son préfixe /64 (un réseau entier ne multiplie pas les sources)."""
    if adresse.version == 6:
        return str(ipaddress.ip_network(f"{adresse}/64", strict=False))
    return str(adresse)


def _de_confiance(adresse):
    return any(adresse in reseau for reseau in settings.MANDATAIRES_DE_CONFIANCE if reseau.version == adresse.version)


def source_de(request):
    """Source réseau de la requête : adresse directe, ou client réel derrière un mandataire déclaré de confiance."""
    base = getattr(request, "_request", request)
    meta = getattr(base, "META", None) or {}
    direct = _adresse(meta.get("REMOTE_ADDR"))
    if direct is None:
        return "inconnue"
    if settings.MANDATAIRES_DE_CONFIANCE and _de_confiance(direct):
        for element in reversed((meta.get("HTTP_X_FORWARDED_FOR") or "").split(",")):
            adresse = _adresse(element)
            if adresse is None:
                break  # chaîne illisible : rien n'est cru, on garde l'adresse du mandataire
            if not _de_confiance(adresse):
                return _normalisee(adresse)
    return _normalisee(direct)


COOKIE_POSTE = "matrix_poste"
POSTES_PAR_COOKIE = 8
POSTES_PAR_IDENTIFIANT = 10
SEL_POSTE = "matrix.poste-connu"


def postes_de(request):
    """Postes connus présentés par le navigateur : {identifiant: jeton}. Un cookie falsifié ou périmé ne donne rien."""
    base = getattr(request, "_request", request)
    if getattr(base, "_postes_connus", None) is not None:
        return base._postes_connus
    postes = {}
    brut = (getattr(base, "COOKIES", None) or {}).get(COOKIE_POSTE)
    if brut:
        try:
            donnees = signing.loads(brut, salt=SEL_POSTE, max_age=settings.CONSERVATION_COMPTEURS_JOURS * 86400)
            postes = {str(k): str(v) for k, v in donnees.items()} if isinstance(donnees, dict) else {}
        except signing.BadSignature:
            postes = {}
    try:
        base._postes_connus = postes
    except AttributeError:
        pass
    return postes


def poste_valide(postes, identifiant):
    """Clé de compteur du poste connu de cet identifiant (« poste:<jeton> »), si le serveur le reconnaît encore."""
    identifiant = cle_identifiant(identifiant)
    jeton = (postes or {}).get(identifiant)
    if not jeton:
        return None
    cle = f"poste:{jeton}"
    limite = timezone.now() - timedelta(days=settings.CONSERVATION_COMPTEURS_JOURS)
    if CompteurConnexion.objects.filter(identifiant=identifiant, source=cle, derniere_reussite__gte=limite).exists():
        return cle
    return None


def cookie_poste(postes, identifiant, jeton):
    """Valeur signée du cookie après ajout du poste (les plus anciens sortent au-delà de `POSTES_PAR_COOKIE`)."""
    postes = {k: v for k, v in (postes or {}).items() if k != identifiant}
    postes[identifiant] = jeton
    return signing.dumps(dict(list(postes.items())[-POSTES_PAR_COOKIE:]), salt=SEL_POSTE)


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


def est_limite(identifiant, source, poste=None):
    """Vrai si ce couple (ou, pour une source inconnue, l'identifiant entier) est en attente de fin de blocage.

    Un poste connu ne dépend que de son propre compteur : le blocage de l'adresse qu'il partage ne l'atteint pas."""
    identifiant, maintenant = cle_identifiant(identifiant), timezone.now()
    if poste:
        propre = _compteur(identifiant, poste)
        return bool(propre and propre.bloque_jusqua and propre.bloque_jusqua > maintenant)
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


def avec_reprises(operation):
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


def enregistrer_echec(identifiant, source, seuil=None, existe=None, poste=None):
    """Compte un échec. Un identifiant inexistant n'ouvre aucun compteur (sinon un flot d'identifiants inventés ferait croître
    la table sans borne) ; il est refusé comme les autres, sans différence visible. `seuil` : essais autorisés avant blocage
    (connexion ou code de réinitialisation) ; le compteur global déclenche à `FACTEUR_GLOBAL` fois ce seuil."""
    identifiant = cle_identifiant(identifiant)
    if not identifiant:
        return
    seuil = seuil or settings.TENTATIVES_CONNEXION_MAX
    try:
        if existe is None:
            existe = avec_reprises(lambda: _compte_existant(identifiant))
    except OperationalError:
        return
    if not existe:
        return

    def compter():
        with transaction.atomic():
            if poste:
                _echec_sur(identifiant, poste, seuil, "connexion_limitee")
                return
            _echec_sur(identifiant, source, seuil, "connexion_limitee")
            _echec_sur(identifiant, SOURCE_GLOBALE, seuil * FACTEUR_GLOBAL, "connexion_limitee_globale")

    try:
        avec_reprises(compter)
    except OperationalError:
        pass  # base durablement occupée : la connexion est refusée de toute façon, l'échec n'est pas compté
    try:
        purger_compteurs(opportuniste=True)
    except OperationalError:
        pass  # la purge reprendra à un prochain échec ou par la tâche quotidienne


def enregistrer_reussite(identifiant, source, request=None):
    """Réussite : remet à zéro le couple et enregistre (ou renouvelle) le poste connu du titulaire."""
    identifiant, maintenant = cle_identifiant(identifiant), timezone.now()
    try:
        compteur = _compteur(identifiant, source, creer=True)
        CompteurConnexion.objects.filter(pk=compteur.pk).update(
            essais=0, niveau=0, bloque_jusqua=None, derniere_reussite=maintenant, derniere_activite=maintenant)
        CompteurConnexion.objects.filter(identifiant=identifiant, source=SOURCE_GLOBALE).update(essais=0)
        if request is not None:
            _retenir_poste(request, identifiant, maintenant)
    except OperationalError:
        pass


def _retenir_poste(request, identifiant, maintenant):
    base = getattr(request, "_request", request)
    postes = postes_de(base)
    cle = poste_valide(postes, identifiant)
    if cle:
        CompteurConnexion.objects.filter(identifiant=identifiant, source=cle).update(
            essais=0, niveau=0, bloque_jusqua=None, derniere_reussite=maintenant, derniere_activite=maintenant)
        return
    jeton = secrets.token_urlsafe(16)
    CompteurConnexion.objects.create(
        identifiant=identifiant, source=f"poste:{jeton}", derniere_reussite=maintenant, derniere_activite=maintenant)
    anciens = list(CompteurConnexion.objects.filter(identifiant=identifiant, source__startswith="poste:")
                   .order_by("-derniere_activite", "-id").values_list("pk", flat=True))[POSTES_PAR_IDENTIFIANT:]
    if anciens:
        CompteurConnexion.objects.filter(pk__in=anciens).delete()
    base._poste_emis = (identifiant, jeton)


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
