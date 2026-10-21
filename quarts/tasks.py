from celery import shared_task

from .rectificatif import signaler_divergences_a_venir


@shared_task
def signaler_divergences_feuilles():
    """Reprise périodique : signale les divergences que le signalement immédiat a manquées (erreur, saisie directe)."""
    return signaler_divergences_a_venir("lors de la reprise périodique")
