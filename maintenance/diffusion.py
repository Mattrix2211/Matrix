"""Information des chefs à chaque compte rendu (sans visa) : saisie, ou correction d'un compte rendu terminé."""
from django.contrib.contenttypes.models import ContentType

from accounts.models import Roles, UserProfile
from notifications.models import Notification, NotificationLevel

from .models import MaintenanceExecution

CONFORMITES = dict(MaintenanceExecution.CONFORMITY)


def notifier_compte_rendu(secteur_id, titre, objet, auteur, conformity, texte, a_surveiller, modification=False, original=None):
    """Prévient les chefs du secteur (et le marin d'origine si un chef corrige son compte rendu), l'auteur exclu."""
    if not secteur_id and not original:
        return
    attention = conformity != "CONFORME" or bool(a_surveiller)
    verbe = f"Compte rendu {'modifié' if modification else 'saisi'} : {titre} — {CONFORMITES[conformity]} ({texte})"
    ct = ContentType.objects.get_for_model(type(objet))
    destinataires = {}
    if secteur_id:
        for profil in UserProfile.objects.filter(role=Roles.CHEF_SECTEUR, sector_id=secteur_id).select_related("user"):
            destinataires[profil.user_id] = profil.user
    if modification and original is not None:
        destinataires[original.pk] = original
    destinataires.pop(getattr(auteur, "pk", None), None)
    for utilisateur in destinataires.values():
        Notification.objects.create(
            user=utilisateur, verb=verbe[:255], content_type=ct, object_id=str(objet.pk),
            level=NotificationLevel.WARNING if attention else NotificationLevel.INFO,
        )
