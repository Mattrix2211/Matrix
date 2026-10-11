from celery import shared_task

from .services import diffuser_du_jour


@shared_task
def diffuser_annonces():
    """Diffuse les annonces programmées dont la date d'effet est arrivée."""
    return {"status": "ok", "diffusees": diffuser_du_jour()}
