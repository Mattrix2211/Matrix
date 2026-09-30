"""Suppléance explicite du commandant par le commandant en second : désignation
d'une période, suivi (début, fin, annulation) tracé dans l'AuditLog et notifié.
Pendant la période, `matrix.core.roles.user_role_level` donne au suppléant le
niveau du commandant ; hors période, aucun droit supplémentaire."""
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import AuditLog, Roles
from notifications.models import Notification, NotificationLevel

from .commandants_adjoints import _navire_cible, _tracer
from .models import CommandantEnSecond, SuppleanceCommandant

ACTIONS = ("designer_suppleance", "annuler_suppleance")


def suppleance_en_cours(user):
    """Suppléance active de `user` sur son navire (et son équipage), ou None."""
    if not getattr(user, "pk", None):
        return None
    profile = getattr(user, "profile", None)
    navire_id = profile.navire_id_effectif if profile else None
    if not navire_id:
        return None
    maintenant = timezone.now()
    return (
        SuppleanceCommandant.objects.filter(
            suppleant=user, ship_id=navire_id, annulee_le__isnull=True, debut__lte=maintenant, fin__gt=maintenant,
        )
        .filter(Q(equipage__isnull=True) | Q(equipage_id=profile.equipage_id))
        .filter(ship__commandants_en_second__titulaire=user)
        .first()
    )


def _notifier(suppleance, texte, niveau=NotificationLevel.INFO):
    for destinataire in {suppleance.suppleant, suppleance.designe_par}:
        if destinataire is not None:
            Notification.objects.create(user=destinataire, verb=texte, level=niveau, target=suppleance)


def _description(suppleance):
    return (
        f"suppleant={suppleance.suppleant.username}; "
        f"du {suppleance.debut:%d/%m/%Y %H:%M} au {suppleance.fin:%d/%m/%Y %H:%M}"
        + (f"; equipage={suppleance.equipage.nom}" if suppleance.equipage_id else "")
    )


def traiter_suppleances_echues():
    """Trace (AuditLog) et notifie le début et la fin de chaque suppléance ;
    appelée régulièrement par Celery. La période s'applique d'elle-même à
    l'échéance (`suppleance_en_cours` compare aux dates) : ce passage ne fait
    que tenir l'historique à jour. Idempotent et atomique : chaque événement est
    « réservé » par un UPDATE conditionnel (état non traité) dans la même
    transaction que sa trace ; deux traitements concurrents ne créent jamais de
    doublon. Retourne le nombre d'événements traités par cet appel."""
    maintenant = timezone.now()
    nombre = 0
    a_demarrer = SuppleanceCommandant.objects.filter(
        debut_trace=False, annulee_le__isnull=True, debut__lte=maintenant
    ).select_related("ship", "suppleant", "equipage", "designe_par")
    for suppleance in a_demarrer:
        with transaction.atomic():
            reservee = SuppleanceCommandant.objects.filter(
                pk=suppleance.pk, debut_trace=False, annulee_le__isnull=True
            ).update(debut_trace=True, updated_at=timezone.now())
            if not reservee:
                continue
            AuditLog.objects.create(
                actor=suppleance.designe_par, action="debut_suppleance_commandant",
                target_user=suppleance.suppleant, details=f"navire={suppleance.ship.name}; {_description(suppleance)}",
            )
            _notifier(suppleance, "Votre suppléance du commandant commence : vous exercez ses droits jusqu'à son terme.")
        nombre += 1
    a_terminer = SuppleanceCommandant.objects.filter(
        fin_tracee=False, annulee_le__isnull=True, debut_trace=True, fin__lte=maintenant
    ).select_related("ship", "suppleant", "equipage", "designe_par")
    for suppleance in a_terminer:
        with transaction.atomic():
            reservee = SuppleanceCommandant.objects.filter(
                pk=suppleance.pk, fin_tracee=False, annulee_le__isnull=True
            ).update(fin_tracee=True, updated_at=timezone.now())
            if not reservee:
                continue
            AuditLog.objects.create(
                actor=None, action="fin_suppleance_commandant", target_user=suppleance.suppleant,
                details=f"navire={suppleance.ship.name}; {_description(suppleance)}",
            )
            _notifier(suppleance, "Votre suppléance du commandant est terminée : vos droits reviennent à ceux de votre poste.")
        nombre += 1
    return nombre


def peut_designer(user):
    """Seuls le commandant et l'administrateur d'unité (rôle réel, jamais une
    suppléance) désignent une suppléance : le suppléant ne peut ni se
    désigner ni prolonger sa propre période."""
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role in (Roles.COMMANDANT, Roles.ADMIN_NAVIRE))


def contexte_onglet(ship):
    if ship is None:
        return {}
    # Lecture seule : une suppléance échue s'affiche « Terminée » par simple
    # comparaison de dates ; la trace et la notification sont écrites par la
    # tâche Celery, jamais lors d'un affichage.
    return {
        "suppleances": list(ship.suppleances_commandant.select_related("suppleant", "equipage")[:20]),
        "suppleants_possibles": [
            p for p in ship.commandants_en_second.select_related("titulaire", "equipage") if p.titulaire_id
        ],
    }


def _lire_date(valeur):
    resultat = parse_datetime(valeur or "")
    if resultat is not None and timezone.is_naive(resultat):
        resultat = timezone.make_aware(resultat)
    return resultat


def traiter_action(request, action):
    """Désigne ou annule une suppléance, sur le navire de l'appelant (ou le
    navire choisi pour un superuser)."""
    if not peut_designer(request.user):
        messages.error(request, "Seul le commandant peut désigner ou annuler une suppléance.")
        return
    ship = _navire_cible(request)
    if ship is None:
        messages.error(request, "Aucune unité sélectionnée.")
        return

    if action == "annuler_suppleance":
        suppleance = ship.suppleances_commandant.filter(
            pk=request.POST.get("suppleance_id") or 0, annulee_le__isnull=True, fin__gt=timezone.now()
        ).first()
        if suppleance is None:
            messages.error(request, "Suppléance introuvable ou déjà terminée.")
            return
        suppleance.annulee_le, suppleance.annulee_par = timezone.now(), request.user
        suppleance.save(update_fields=["annulee_le", "annulee_par", "updated_at"])
        _tracer(request, "annulation_suppleance_commandant", ship, _description(suppleance))
        _notifier(suppleance, "Votre suppléance du commandant a été annulée.", NotificationLevel.WARNING)
        messages.success(request, "Suppléance annulée.")
        return

    poste = CommandantEnSecond.objects.filter(
        ship=ship, pk=request.POST.get("poste_id") or 0, titulaire__isnull=False
    ).select_related("titulaire", "equipage").first()
    if poste is None:
        messages.error(request, "Choisissez un commandant en second désigné.")
        return
    debut, fin = _lire_date(request.POST.get("debut")), _lire_date(request.POST.get("fin"))
    if debut is None or fin is None:
        messages.error(request, "Indiquez le début et la fin de la suppléance.")
        return
    if fin <= debut or fin <= timezone.now():
        messages.error(request, "La fin doit être postérieure au début et à l'heure actuelle.")
        return
    suppleance = SuppleanceCommandant.objects.create(
        ship=ship, equipage=poste.equipage, suppleant=poste.titulaire, debut=debut, fin=fin,
        motif=(request.POST.get("motif") or "")[:200], designe_par=request.user,
    )
    _tracer(request, "designation_suppleance_commandant", ship, _description(suppleance))
    _notifier(suppleance, "Vous êtes désigné pour suppléer le commandant sur la période indiquée.")
    traiter_suppleances_echues()
    messages.success(request, f"Suppléance de {poste.titulaire.username} enregistrée.")
