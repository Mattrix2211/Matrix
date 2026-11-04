"""Remplacement temporaire d'un chef de liste des services à quai : désignation explicite, bornée et tracée."""
from datetime import timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.scopes import equipage_agissant
from notifications.models import Notification, NotificationLevel
from quarts.activation import ActivationImpossible
from quarts.models import ChefDeListe, ConfigurationActivation, RemplacementChefDeListe

DUREE_MAX_PAR_DEFAUT_HEURES = 72


def duree_max_heures(ship):
    reglage = ConfigurationActivation.objects.filter(ship=ship).first()
    return reglage.remplacement_duree_max_heures if reglage else DUREE_MAX_PAR_DEFAUT_HEURES


def _nom(user):
    return user.get_full_name() or user.username


@transaction.atomic
def designer_remplacant(auteur, designation, remplacant, debut, fin, motif):
    """Désigne `remplacant` pour tenir, du début à la fin, le rôle de la désignation de chef de liste donnée
    (activer, reporter, retirer une prévision seulement). Le contrôle du droit de désigner est fait par l'appelant."""
    if not designation.couvre(ChefDeListe.TYPE_QUAI):
        raise ActivationImpossible("Le remplacement ne concerne que les chefs de liste des services à quai.")
    if not motif.strip():
        raise ActivationImpossible("Un motif est obligatoire.")
    if remplacant.pk == designation.user_id:
        raise ActivationImpossible("Le remplaçant doit être une autre personne que le titulaire.")
    profil = getattr(remplacant, "profile", None)
    ship = designation.ship or (designation.service.ship if designation.service else None) \
        or (designation.sector.service.ship if designation.sector else None) \
        or (designation.section.sector.service.ship if designation.section else None)
    if not remplacant.is_active or profil is None or profil.ship_id != ship.pk:
        raise ActivationImpossible("Le remplaçant doit être un marin actif du bâtiment.")
    maintenant = timezone.now()
    if debut is None or fin is None or fin <= debut or fin <= maintenant:
        raise ActivationImpossible("La période de remplacement est invalide.")
    if debut < maintenant - timedelta(minutes=5):
        raise ActivationImpossible("Le remplacement ne peut pas commencer dans le passé.")
    maximum = duree_max_heures(ship)
    if fin - debut > timedelta(hours=maximum):
        raise ActivationImpossible(f"La durée d'un remplacement est limitée à {maximum} h, sans renouvellement automatique.")
    en_double = RemplacementChefDeListe.objects.filter(
        titulaire=designation.user, type_liste=ChefDeListe.TYPE_QUAI, revoque_le__isnull=True, fin__gt=debut, debut__lt=fin,
        ship=ship, service=designation.service, sector=designation.sector, section=designation.section,
    ).exists()
    if en_double:
        raise ActivationImpossible("Un remplacement du même titulaire sur ce niveau couvre déjà cette période.")
    remplacement = RemplacementChefDeListe.objects.create(
        ship=ship, equipage=equipage_agissant(auteur) or "", service=designation.service, sector=designation.sector,
        section=designation.section, perimetre_navire=designation.ship_id is not None, type_liste=ChefDeListe.TYPE_QUAI,
        remplacant=remplacant, titulaire=designation.user, debut=debut, fin=fin, motif=motif.strip(), designe_par=auteur,
    )
    AuditLog.objects.create(
        actor=auteur, action="remplacement_chef_de_liste_designe", target_user=remplacant,
        details=(
            f"{_nom(remplacant)} remplace {_nom(designation.user)} ({remplacement.perimetre}, services à quai) du "
            f"{timezone.localtime(debut):%d/%m/%Y %H:%M} au {timezone.localtime(fin):%d/%m/%Y %H:%M} : activer, reporter, retirer une prévision. "
            f"Motif : {motif.strip()}."
        ),
    )
    for destinataire, texte in (
        (remplacant, f"Vous remplacez {_nom(designation.user)} pour activer, reporter ou retirer les listes à quai de « {remplacement.perimetre} » jusqu'au {timezone.localtime(fin):%d/%m/%Y à %H:%M}."),
        (designation.user, f"{_nom(remplacant)} vous remplace pour activer les listes à quai de « {remplacement.perimetre} » du {timezone.localtime(debut):%d/%m/%Y %H:%M} au {timezone.localtime(fin):%d/%m/%Y %H:%M}."),
    ):
        Notification.objects.create(user=destinataire, verb=texte, level=NotificationLevel.INFO, url=reverse("quarts-index"))
    return remplacement


@transaction.atomic
def revoquer_remplacement(auteur, remplacement, motif):
    if remplacement.revoque_le is not None or remplacement.fin <= timezone.now():
        raise ActivationImpossible("Ce remplacement est déjà terminé ou révoqué.")
    if not motif.strip():
        raise ActivationImpossible("Un motif est obligatoire pour révoquer un remplacement.")
    remplacement.revoque_le, remplacement.revoque_par, remplacement.motif_revocation = timezone.now(), auteur, motif.strip()
    remplacement.save(update_fields=["revoque_le", "revoque_par", "motif_revocation", "updated_at"])
    AuditLog.objects.create(
        actor=auteur, action="remplacement_chef_de_liste_revoque", target_user=remplacement.remplacant,
        details=f"Remplacement de {_nom(remplacement.titulaire)} par {_nom(remplacement.remplacant)} révoqué. Motif : {motif.strip()}.",
    )
