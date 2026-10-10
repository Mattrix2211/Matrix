from celery import shared_task
from django.core.management import call_command

from .brouillons import purger_brouillons_anciens


@shared_task
def purger_brouillons():
    """Purge quotidienne des brouillons plus anciens que BROUILLONS_CONSERVATION_JOURS."""
    return purger_brouillons_anciens()


@shared_task
def purger_sessions():
    """Supprime chaque jour les sessions expirées conservées en base."""
    call_command("clearsessions")
