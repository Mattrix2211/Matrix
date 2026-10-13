from django.db.models import Q

from matrix.core.mixins import build_scope_q
from matrix.core.scopes import assignes_equipage_q

from .models import CorrectiveTicket


def equipage_tickets_q(user, prefixe: str = "") -> Q:
    """Étanchéité par équipage des tickets, directement ou via une relation (`prefixe` : « ticket__ », « part_request__ticket__ »…)."""
    equipage = assignes_equipage_q(user, CorrectiveTicket, "assignees")
    if not prefixe or not equipage:
        return equipage
    return Q(**{f"{prefixe}pk__in": CorrectiveTicket.objects.filter(equipage).values("pk")})


def perimetre_tickets_q(user):
    """Tickets visibles : périmètre de l'utilisateur, puis étanchéité par équipage (double équipage)."""
    return build_scope_q(user, "asset__", "installation__") & equipage_tickets_q(user)
