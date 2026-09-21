from celery import shared_task

from . import services


@shared_task
def generer_rondes():
    """Propose chaque jour les rondes dont la périodicité est atteinte."""
    return services.generer_rondes()


@shared_task
def marquer_rondes_en_retard():
    """Marque les rondes échues non terminées comme en retard (et prévient)."""
    return services.marquer_rondes_en_retard()
