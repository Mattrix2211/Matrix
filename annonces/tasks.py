from celery import shared_task

from .services import diffuser_du_jour, rappeler_accuses


@shared_task
def diffuser_annonces():
    """Diffuse les annonces programmées dont la date d'effet est arrivée."""
    return {"status": "ok", "diffusees": diffuser_du_jour()}


@shared_task
def rappeler_accuses_annonces():
    """Relance une fois les destinataires qui n'ont pas accusé réception après le délai réglé."""
    return {"status": "ok", "rappels": rappeler_accuses()}
