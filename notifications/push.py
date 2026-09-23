"""Envoi des notifications Web Push (RFC 8030) pour les alertes critiques.

Utilise pywebpush, qui s'appuie sur le protocole Web Push standard des
navigateurs (chiffrement natif, clé VAPID auto-hébergée). Conformément au
principe hors-ligne du projet : seule la bibliothèque Python s'installe via
pip (requirements.txt), aucun service tiers propriétaire ni dépendance CDN
n'est nécessaire pour l'envoi lui-même.
"""
import json
import logging

from django.conf import settings

from .models import PushSubscription

logger = logging.getLogger(__name__)

# pywebpush est une dépendance optionnelle : son installation dépend de
# http-ece, une extension native qui ne compile pas sur tous les postes
# (cf. CLAUDE.md). Son absence ne doit jamais empêcher la création d'une
# notification in-app : seul l'envoi Web Push doit être indisponible, avec
# un simple log (même modèle que pdf_disponible() dans reports/services.py
# et xlsx_disponible() dans matrix/core/export.py).
try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - dépend de la compilation de http-ece sur la machine
    WebPushException = None
    webpush = None


def push_disponible() -> bool:
    """Indique si l'envoi Web Push est disponible (pywebpush installé)."""
    return webpush is not None


def _url_notification(notification):
    """Lien cible de la notification, si connu (même logique que le contexte
    processeur des notifications in-app pour les installations fixes)."""
    if notification.content_type_id and notification.object_id:
        if notification.content_type.model == "installation":
            return f"/installations/{notification.object_id}/"
    return "/"


def envoyer_notification_push(notification):
    """Envoie une notification Web Push à tous les appareils abonnés de
    l'utilisateur concerné.

    Réservé aux appelants qui ont déjà vérifié le niveau DANGER (cf.
    notifications/signals.py) : cette fonction ne filtre pas elle-même le
    niveau, pour rester testable indépendamment du déclencheur.
    """
    if not push_disponible():
        # pywebpush indisponible sur ce poste (http-ece non compilé) : la
        # notification in-app reste créée, seul l'envoi Web Push est ignoré.
        logger.warning(
            "Envoi Web Push ignoré (pywebpush indisponible) pour la notification %s",
            notification.pk,
        )
        return

    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        # Web Push non configuré (clés VAPID absentes) : rien à envoyer. Évite
        # de planter en environnement de développement/tests sans clés.
        return

    payload = json.dumps({
        "titre": "Matrix — Alerte critique",
        "corps": notification.verb,
        "url": _url_notification(notification),
    })

    for abonnement in PushSubscription.objects.filter(user=notification.user):
        subscription_info = {
            "endpoint": abonnement.endpoint,
            "keys": {"p256dh": abonnement.p256dh, "auth": abonnement.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
        except WebPushException as exc:
            statut = getattr(exc.response, "status_code", None)
            if statut in (404, 410):
                # Abonnement expiré ou invalide côté service de push du
                # navigateur (410 Gone / 404 Not Found) : on le supprime
                # proprement plutôt que de retenter indéfiniment un
                # abonnement mort.
                abonnement.delete()
            else:
                logger.warning(
                    "Échec d'envoi Web Push vers %s : %s", abonnement.endpoint, exc
                )
        except Exception:  # défense en profondeur : un envoi push ne doit jamais planter l'appelant
            logger.exception("Erreur inattendue lors de l'envoi Web Push vers %s", abonnement.endpoint)
