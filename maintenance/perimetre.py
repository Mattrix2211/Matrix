from django.db.models import Q

from matrix.core.mixins import build_scope_q
from matrix.core.scopes import assignes_equipage_q

from .models import MaintenanceOccurrence


def perimetre_occurrences_q(user):
    """Occurrences visibles : périmètre de l'utilisateur, puis étanchéité par équipage (double équipage)."""
    return build_scope_q(user, "asset__", "installation_maintenance__installation__") & assignes_equipage_q(
        user, MaintenanceOccurrence, "assignees"
    )


# Une validation en attente n'est pas un retard de l'équipe.
STATUTS_SANS_RETARD = ("DONE", "CANCELLED", "WAITING_VALIDATION")


def retard_q(aujourdhui):
    """Occurrences en retard : statut OVERDUE ou échéance passée, hors terminées, annulées et en attente de validation.
    Définition unique du compteur « en retard » d'Aujourd'hui et du filtre de la liste des occurrences."""
    return (Q(status="OVERDUE") | Q(scheduled_for__lt=aujourdhui)) & ~Q(status__in=STATUTS_SANS_RETARD)


def installations_en_retard(user, aujourdhui):
    """Installations du périmètre de l'utilisateur ayant une occurrence en retard (installation sans statut propre)."""
    from assets.models import Installation

    retards = MaintenanceOccurrence.objects.filter(perimetre_occurrences_q(user)).filter(retard_q(aujourdhui))
    return Installation.objects.filter(build_scope_q(user, ""), maintenances__occurrences__in=retards).distinct()
