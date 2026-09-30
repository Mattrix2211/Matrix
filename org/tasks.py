from celery import shared_task

from . import passation, suppleance


@shared_task
def appliquer_releves_planifiees():
    """Chaque jour : bascule les relèves de double équipage arrivées à échéance
    et produit la synthèse de passation de l'équipage montant."""
    return {"status": "ok", "releves": passation.appliquer_releves_echues()}


@shared_task
def traiter_suppleances():
    """Toutes les cinq minutes : trace et notifie le début et la fin des
    suppléances du commandant."""
    return {"status": "ok", "evenements": suppleance.traiter_suppleances_echues()}
