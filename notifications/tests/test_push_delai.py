"""Le Web Push ne doit jamais bloquer durablement la création d'une notification."""
import base64
import logging
import socket
import threading
import time
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from py_vapid import Vapid

from notifications.models import Notification, NotificationLevel, PushSubscription


def _b64(octets):
    return base64.urlsafe_b64encode(octets).decode().rstrip("=")


def _cle_p256dh():
    cle = ec.generate_private_key(ec.SECP256R1()).public_key()
    return _b64(cle.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))


class ServeurSourd:
    """Serveur local qui accepte les connexions mais ne répond jamais."""

    def __enter__(self):
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(5)
        self.clients = []
        self.actif = True
        threading.Thread(target=self._accepter, daemon=True).start()
        return self

    def _accepter(self):
        self.socket.settimeout(0.2)
        while self.actif:
            try:
                self.clients.append(self.socket.accept()[0])
            except OSError:
                continue

    def __exit__(self, *exc):
        self.actif = False
        for client in self.clients:
            client.close()
        self.socket.close()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.socket.getsockname()[1]}/push"


def _cle_vapid():
    vapid = Vapid()
    vapid.generate_keys()
    return _b64(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))


class PushEndpointInjoignableTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="marin", password="pass")

    def _abonner(self, endpoint):
        PushSubscription.objects.create(
            user=self.user, endpoint=endpoint, p256dh=_cle_p256dh(), auth=_b64(b"0123456789abcdef"),
        )

    @override_settings(WEBPUSH_DELAI_MAX=1, VAPID_PUBLIC_KEY="pub")
    def test_creation_revient_dans_un_delai_borne_si_lendpoint_ne_repond_pas(self):
        with ServeurSourd() as serveur, self.settings(VAPID_PRIVATE_KEY=_cle_vapid()):
            self._abonner(serveur.url)
            self._abonner(serveur.url + "2")
            debut = time.monotonic()
            with self.assertLogs("notifications.push", level=logging.WARNING) as journal:
                notification = Notification.objects.create(
                    user=self.user, verb="Alerte", level=NotificationLevel.DANGER,
                )
            duree = time.monotonic() - debut
        self.assertTrue(any("Web Push" in ligne for ligne in journal.output))
        self.assertLess(duree, 2.5)
        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())

    @override_settings(WEBPUSH_DELAI_MAX=1, VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv")
    def test_le_delai_configure_est_transmis_a_webpush(self):
        self._abonner("http://127.0.0.1:9/push")
        with patch("notifications.push.webpush") as envoi:
            Notification.objects.create(user=self.user, verb="Alerte", level=NotificationLevel.DANGER)
        self.assertLessEqual(envoi.call_args.kwargs["timeout"], 1)
        self.assertGreater(envoi.call_args.kwargs["timeout"], 0)
