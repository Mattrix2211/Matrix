"""Feuilles de service publiées et versions rectificatives.

Une version publiée est immuable. Quand le planning effectif (échange de
service validé, tour modifié) diverge de la dernière version, la feuille le
signale sans rien modifier : l'échange reste effectif, la version reste la
référence publiée. Le rédacteur ouvre alors un rectificatif qui suit le
circuit de visa habituel ; l'ancienne version n'est « remplacée » qu'à sa
publication."""
import hashlib
import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification, NotificationLevel

User = get_user_model()


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


def signaler_divergence(feuille):
    """Prévient, une seule fois par divergence, les responsables de la feuille de
    son équipage (rédacteur et COMAEQ) qu'un rectificatif est à préparer. Sans
    nouvelle notification tant que la divergence ne change pas ; l'empreinte est
    remise à zéro quand l'écart disparaît ou que le rectificatif est publié."""
    from .models import titulaires_comaeq
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


def signaler_divergences_apres_echange(echange):
    """Après un échange validé : examine les feuilles déjà publiées des jours des deux créneaux."""
    from .models import FeuilleService
    creneaux = (echange.creneau_demandeur, echange.creneau_cible)
    debut = min(timezone.localdate(c.debut) for c in creneaux)
    fin = max(timezone.localdate(c.fin) for c in creneaux)
    feuilles = FeuilleService.objects.filter(date__range=(debut, fin), versions__isnull=False).distinct()
    for feuille in feuilles:
        signaler_divergence(feuille)
