from celery import shared_task

from .securite import purger_compteurs


@shared_task
def purger_compteurs_connexion():
    """Purge quotidienne des compteurs techniques de connexion inactifs ; les journaux d'audit ne sont jamais touchés."""
    return purger_compteurs()
