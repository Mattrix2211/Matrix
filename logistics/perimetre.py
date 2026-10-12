from matrix.core.mixins import build_scope_q
from matrix.core.scopes import assignes_equipage_q

from .models import CorrectiveTicket


def perimetre_tickets_q(user):
    """Tickets visibles : périmètre de l'utilisateur, puis étanchéité par équipage (double équipage)."""
    return build_scope_q(user, "asset__", "installation__") & assignes_equipage_q(user, CorrectiveTicket, "assignees")
