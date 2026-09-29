from celery import shared_task

from . import passation


@shared_task
def appliquer_releves_planifiees():
    """Chaque jour : bascule les relèves de double équipage arrivées à échéance
    et produit la synthèse de passation de l'équipage montant."""
    return {"status": "ok", "releves": passation.appliquer_releves_echues()}
