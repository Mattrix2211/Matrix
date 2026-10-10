"""Traçabilité des connexions et des déconnexions manuelles (l'expiration est tracée à part)."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.urls import reverse

from .models import AuditLog


@receiver(user_logged_in)
def tracer_connexion(sender, request, user, **kwargs):
    AuditLog.objects.create(actor=user, action="connexion")


@receiver(user_logged_out)
def tracer_deconnexion(sender, request, user, **kwargs):
    # Un retour à la connexion après expiration passe aussi par /logout/ : déjà tracé comme expiration.
    if user is not None and request is not None and request.path == reverse("logout") \
            and not getattr(request, "session_expiree_tracee", False):
        AuditLog.objects.create(actor=user, action="deconnexion")
