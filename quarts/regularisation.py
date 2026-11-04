"""Terminer un créneau de quart à l'heure effective : régularisation motivée, jamais automatique ni rétroactive."""
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from notifications.models import Notification, NotificationLevel
from quarts.models import CreneauQuart, Quart, peut_gerer_liste


class RegularisationImpossible(Exception):
    """Refus métier, message affichable tel quel."""


@transaction.atomic
def terminer_creneau(user, creneau, nouvelle_fin, motif):
    """Raccourcit un créneau d'un quart publié à une heure effective, par le responsable de la liste de quarts
    (chef de liste des quarts ou supervision du commandement). La partie déjà écoulée n'est jamais modifiée ;
    l'affectation est conservée sur la partie restante ; une nouvelle version de la liste est figée."""
    creneau = CreneauQuart.objects.select_for_update().select_related("quart", "marin").get(pk=creneau.pk)
    liste = creneau.quart
    if not isinstance(liste, Quart) or not peut_gerer_liste(user, liste):
        raise RegularisationImpossible("Seul le responsable de la liste de quarts peut terminer un créneau.")
    if liste.statut != Quart.STATUT_PUBLIEE:
        raise RegularisationImpossible("Seul un créneau d'un quart publié peut être terminé à l'heure effective.")
    if not motif.strip():
        raise RegularisationImpossible("Un motif est obligatoire.")
    maintenant = timezone.now()
    if creneau.fin <= maintenant:
        raise RegularisationImpossible("Ce créneau est déjà terminé : la période écoulée n'est jamais modifiée.")
    if nouvelle_fin is None or nouvelle_fin <= creneau.debut or nouvelle_fin >= creneau.fin:
        raise RegularisationImpossible("La nouvelle fin doit être comprise entre le début et la fin prévue du créneau.")
    if nouvelle_fin < maintenant:
        raise RegularisationImpossible("La nouvelle fin ne peut pas être antérieure à maintenant : la période déjà écoulée est préservée.")
    ancienne_fin = creneau.fin
    creneau.fin_initiale = creneau.fin_initiale or ancienne_fin
    creneau.fin = nouvelle_fin
    creneau.save(update_fields=["fin", "fin_initiale", "updated_at"])
    version = liste.creer_version(user)
    marin = creneau.marin
    AuditLog.objects.create(
        actor=user, action="quart_creneau_termine", target_user=marin,
        details=(
            f"Quart #{liste.pk} ({liste.perimetre}) ; poste « {creneau.poste} » : fin ramenée de "
            f"{timezone.localtime(ancienne_fin):%d/%m/%Y %H:%M} à {timezone.localtime(nouvelle_fin):%d/%m/%Y %H:%M} "
            f"(version {version.numero}). Motif : {motif.strip()}."
        ),
    )
    if marin is not None and marin.pk != user.pk:
        Notification.objects.create(
            user=marin, level=NotificationLevel.WARNING, url=reverse("quarts-index"),
            verb=(
                f"Votre quart « {creneau.poste} » prend fin plus tôt : {timezone.localtime(nouvelle_fin):%d/%m/%Y à %H:%M} "
                f"au lieu de {timezone.localtime(ancienne_fin):%H:%M}. Motif : {motif.strip()}."
            ),
        )
    _prevenir_les_chefs_a_quai(creneau, user)
    return creneau


def _prevenir_les_chefs_a_quai(creneau, auteur):
    """Informe les chefs de liste à quai dont un service du même marin recouvre ce quart : le recouvrement a pu évoluer."""
    if creneau.marin_id is None:
        return
    from quarts.alertes_activation import chefs_de_liste_habilites
    from quarts.models import CreneauServiceGarde

    listes = {
        c.service_garde for c in CreneauServiceGarde.objects.filter(
            marin_id=creneau.marin_id, debut__lt=creneau.fin_initiale or creneau.fin, fin__gt=creneau.debut,
        ).select_related("service_garde")
    }
    destinataires = {u.pk: u for liste in listes for u in chefs_de_liste_habilites(liste)}
    for utilisateur in destinataires.values():
        if utilisateur.pk != auteur.pk:
            Notification.objects.create(
                user=utilisateur, level=NotificationLevel.INFO, url=reverse("quarts-index"),
                verb=f"Un quart de {creneau.marin.get_full_name() or creneau.marin.username} a été terminé à l'heure effective : les recouvrements avec vos listes à quai sont recalculés.",
            )
