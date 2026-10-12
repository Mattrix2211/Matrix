from matrix.core.mixins import build_scope_q
from matrix.core.scopes import assignes_equipage_q

from .models import MaintenanceOccurrence


def perimetre_occurrences_q(user):
    """Occurrences visibles : périmètre de l'utilisateur, puis étanchéité par équipage (double équipage)."""
    return build_scope_q(user, "asset__", "installation_maintenance__installation__") & assignes_equipage_q(
        user, MaintenanceOccurrence, "assignees"
    )
