"""Priorité d'affichage selon le mode du bâtiment : aucune notification n'est supprimée ni masquée."""
from .models import NotificationLevel, RegimeNotification


def est_urgente(notification):
    return notification.level == NotificationLevel.DANGER or (notification.action_requise and notification.traitee_le is None)


def repartir(notifications, mode):
    """(prioritaires, autres_regimes). Mode inconnu : tout reste prioritaire. Une notification urgente (niveau « Urgent » ou
    action à traiter) reste toujours prioritaire, quel que soit son régime."""
    notifications = list(notifications)
    if mode not in (RegimeNotification.MER, RegimeNotification.QUAI):
        return notifications, []
    communs = (mode, RegimeNotification.COMMUNES, RegimeNotification.TRANSITION)
    prioritaires = [n for n in notifications if est_urgente(n) or n.regime in communs]
    autres = [n for n in notifications if not (est_urgente(n) or n.regime in communs)]
    return prioritaires, autres
