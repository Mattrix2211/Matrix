from celery import shared_task

from .brouillons import purger_brouillons_anciens


@shared_task
def purger_brouillons():
    """Purge quotidienne des brouillons plus anciens que BROUILLONS_CONSERVATION_JOURS."""
    return purger_brouillons_anciens()
