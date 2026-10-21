"""Feuilles de service publiées et versions rectificatives.

Une version publiée est immuable. Quand le planning effectif (échange de
service validé, tour modifié) diverge de la dernière version, la feuille le
signale sans rien modifier : l'échange reste effectif, la version reste la
référence publiée. Le rédacteur ouvre alors un rectificatif qui suit le
circuit de visa habituel ; l'ancienne version n'est « remplacée » qu'à sa
publication."""
import hashlib
import json
import logging

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from notifications.models import Notification, NotificationLevel

User = get_user_model()
logger = logging.getLogger(__name__)


def _affectations(contenu, avec_cles_de_repli=False):
    """{clé: (libellé, nom du titulaire, identifiant du marin)} des fonctions et postes d'alerte."""
    entrees = {}
    for e in contenu.get("personnel", []):
        valeur = (e["fonction"], e.get("marin", ""), e.get("marin_id"))
        entrees[("fonction", e.get("uid") or e["fonction"])] = valeur
        if avec_cles_de_repli:
            entrees.setdefault(("fonction", e["fonction"]), valeur)
    for s in contenu.get("alertes", []):
        for p in s["postes"]:
            entrees[("alerte", s["scenario"], p["role"])] = (
                f"{s['scenario']} — {p['role']}", p.get("marin", ""), p.get("marin_id"),
            )
    return entrees


def differences_affectations(ancien, nouveau):
    """Titulaires qui diffèrent entre deux contenus de feuille. Seules les
    fonctions et postes présents des deux côtés sont comparés : une rubrique ou
    une fonction ajoutée n'est pas un changement d'affectation."""
    avant = _affectations(ancien)
    apres = _affectations(nouveau, avec_cles_de_repli=True)
    differences = []
    for cle, (libelle, marin_avant, id_avant) in avant.items():
        # Version ancienne sans identifiant de fonction : repli sur le libellé.
        suivant = apres.get(cle) or apres.get(("fonction", libelle))
        # Même titulaire = même marin ; le texte (grade, nom) ne sert qu'aux anciennes versions sans identifiant.
        if suivant is None:
            continue
        if id_avant is not None and suivant[2] is not None:
            change = id_avant != suivant[2]
        else:
            change = suivant[1] != marin_avant
        if change:
            differences.append({
                "libelle": libelle, "avant": marin_avant, "apres": suivant[1],
                "marins": {i for i in (id_avant, suivant[2]) if i},
            })
    return differences


def divergences_effectives(feuille):
    """Différences entre la dernière version publiée et les affectations effectives du planning."""
    version = feuille.version_publiee
    if version is None:
        return []
    return differences_affectations(version.contenu_fige, feuille.contenu_courant())


def notifier_rectificatif(feuille, version, remplace, redacteur):
    """À la publication d'un rectificatif seulement : prévient les titulaires
    dont l'affectation change et le rédacteur."""
    date = f"{feuille.date:%d/%m/%Y}"
    titre = f"Feuille de service du {date} : version rectificative n°{version.numero} publiée, elle remplace la version {remplace.numero}"
    url = reverse("feuille-service-detail", args=[feuille.ship_id, f"{feuille.date:%Y-%m-%d}"])
    touches = {
        i for d in differences_affectations(remplace.contenu_fige, version.contenu_fige) for i in d["marins"]
    }
    destinataires = {u.pk: (u, f"{titre} — votre affectation a changé.") for u in User.objects.filter(pk__in=touches, is_active=True)}
    if redacteur is not None and redacteur.pk not in destinataires:
        destinataires[redacteur.pk] = (redacteur, f"{titre}.")
    for destinataire, verb in destinataires.values():
        Notification.objects.create(user=destinataire, verb=verb, level=NotificationLevel.INFO, url=url)


MESSAGE_CONTENU_CHANGE = (
    "Une information a changé depuis le visa. Actualisez la feuille et procédez à une nouvelle validation."
)
SEL_JETON_VISA = "quarts.visa_comaeq"
DUREE_JETON_VISA = 30 * 60


def empreinte_de(contenu):
    """Empreinte des affectations et alertes d'un contenu (identifiants des marins, pas leurs noms)."""
    base = [[e["uid"], e["marin_id"]] for e in contenu["personnel"]] + [
        [s["scenario"], p["role"], p["marin_id"]] for s in contenu["alertes"] for p in s["postes"]
    ]
    return hashlib.sha1(json.dumps(base).encode()).hexdigest()


def empreinte_contenu(feuille):
    return empreinte_de(feuille.contenu_courant())


def jeton_visa(feuille, user):
    """Valeur signée côté serveur : contenu affiché au COMAEQ, liée à la feuille et à l'utilisateur."""
    return signing.dumps(
        {"f": feuille.pk, "u": user.pk, "e": empreinte_contenu(feuille)}, salt=SEL_JETON_VISA,
    )


def empreinte_du_jeton(jeton, feuille, user):
    """Empreinte signée, ou None si la signature est absente, falsifiée, expirée ou d'une autre feuille/utilisateur."""
    try:
        donnees = signing.loads(jeton or "", salt=SEL_JETON_VISA, max_age=DUREE_JETON_VISA)
    except signing.BadSignature:
        return None
    if donnees.get("f") != feuille.pk or donnees.get("u") != user.pk:
        return None
    return donnees.get("e")


def signaler_divergence(feuille):
    """Prévient, une seule fois par divergence, les responsables de la feuille de
    son équipage (rédacteur et COMAEQ) qu'un rectificatif est à préparer. Sans
    nouvelle notification tant que la divergence ne change pas ; l'empreinte est
    remise à zéro quand l'écart disparaît ou que le rectificatif est publié.
    La feuille est verrouillée puis relue : une publication concurrente est attendue."""
    from .models import FeuilleService, titulaires_comaeq
    with transaction.atomic():
        feuille = FeuilleService.objects.select_for_update().get(pk=feuille.pk)
        differences = divergences_effectives(feuille)
        empreinte = hashlib.sha1(json.dumps(
            sorted((d["libelle"], sorted(d["marins"])) for d in differences)
        ).encode()).hexdigest() if differences else ""
        if empreinte == feuille.divergence_signalee:
            return
        feuille.divergence_signalee = empreinte
        feuille.save(update_fields=["divergence_signalee", "updated_at"])
        if not empreinte or feuille.rectificatif_en_cours:
            return
        destinataires = {u.pk: u for u in titulaires_comaeq(feuille)}
        if feuille.redacteur is not None and feuille.redacteur.is_active:
            destinataires[feuille.redacteur.pk] = feuille.redacteur
        equipage = f" (équipage {feuille.equipage})" if feuille.equipage else ""
        url = reverse("feuille-service-detail", args=[feuille.ship_id, f"{feuille.date:%Y-%m-%d}"])
        for destinataire in destinataires.values():
            Notification.objects.create(
                user=destinataire, level=NotificationLevel.WARNING, url=url,
                verb=f"Feuille de service du {feuille.date:%d/%m/%Y}{equipage} : rectificatif à préparer, les affectations "
                     f"effectives ont changé depuis la publication de la version {feuille.version_publiee.numero}.",
            )


def _ship_id_de_la_liste(liste):
    return (
        liste.ship_id
        or (liste.service.ship_id if liste.service_id else None)
        or (liste.sector.service.ship_id if liste.sector_id else None)
        or (liste.section.sector.service.ship_id if liste.section_id else None)
    )


def signaler_divergences_apres_echange(echange):
    """Après un échange validé : examine les feuilles déjà publiées du même
    bâtiment, aux jours des deux créneaux. Une erreur de signalement est tracée
    et ne fait jamais échouer la validation de l'échange."""
    from .models import FeuilleService
    creneaux = (echange.creneau_demandeur, echange.creneau_cible)
    debut = min(timezone.localdate(c.debut) for c in creneaux)
    fin = max(timezone.localdate(c.fin) for c in creneaux)
    ship_id = _ship_id_de_la_liste(echange.liste)
    feuilles = FeuilleService.objects.filter(
        ship_id=ship_id, date__range=(debut, fin), versions__isnull=False,
    ).distinct()
    for feuille in feuilles:
        signaler_sans_risque(feuille, f"après l'échange {echange.pk}")


def signaler_sans_risque(feuille, contexte):
    """Signale la divergence ; une erreur est journalisée (logger + AuditLog) et
    laisse l'empreinte non marquée, pour qu'un nouveau passage retente."""
    try:
        signaler_divergence(feuille)
    except Exception as erreur:
        logger.exception("Signalement de divergence impossible (feuille %s)", feuille.pk)
        AuditLog.objects.create(
            actor=None, action="feuille_service_signalement_echoue",
            details=f"Feuille de service du {feuille.date:%d/%m/%Y} ({feuille.ship}) : signalement du rectificatif "
                    f"à préparer impossible {contexte} ({erreur.__class__.__name__} : {erreur}).",
        )


def signaler_divergences_a_venir(contexte):
    """Examine les feuilles publiées d'aujourd'hui et à venir (idempotent : une divergence
    déjà signalée ne l'est pas deux fois). Retourne le nombre de feuilles examinées."""
    from .models import FeuilleService
    feuilles = list(FeuilleService.objects.filter(date__gte=timezone.localdate(), versions__isnull=False).distinct())
    for feuille in feuilles:
        signaler_sans_risque(feuille, contexte)
    return len(feuilles)
