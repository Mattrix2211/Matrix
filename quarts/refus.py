"""Trace des tentatives refusées sur les actions sensibles (activation, mouvements, régularisation, remplacement, réglages)."""
from accounts.models import AuditLog


def tracer_refus(user, action, details):
    """Journalise une tentative d'action refusée côté serveur, sans rien modifier d'autre."""
    AuditLog.objects.create(actor=user, action="tentative_refusee", details=f"{action} : {details}")
