"""Tests du Web Push pour les notifications créées en masse (bulk_create)."""
from unittest import mock

from django.contrib.auth.models import User
from django.db import transaction
from django.test import TestCase

from notifications.models import Notification, NotificationLevel
from notifications.services import creer_notifications_en_masse

CIBLE = "notifications.services.envoyer_notification_push"


class PushEnMasseTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("marin1", password="x")
        self.u2 = User.objects.create_user("marin2", password="x")

    def _lot(self, niveau):
        return [Notification(user=u, verb="Test", level=niveau) for u in (self.u1, self.u2)]

    def test_danger_en_masse_pousse_pour_chaque_notification(self):
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True):
            creer_notifications_en_masse(self._lot(NotificationLevel.DANGER))
        self.assertEqual(envoi.call_count, 2)
        self.assertEqual(Notification.objects.count(), 2)

    def test_info_et_warning_ne_poussent_pas(self):
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True):
            creer_notifications_en_masse(self._lot(NotificationLevel.INFO))
            creer_notifications_en_masse(self._lot(NotificationLevel.WARNING))
        envoi.assert_not_called()
        self.assertEqual(Notification.objects.count(), 4)

    def test_pas_de_double_envoi_avec_le_signal(self):
        # Le signal post_save (import tardif) appelle notifications.push directement.
        with mock.patch(CIBLE) as envoi, mock.patch("notifications.push.envoyer_notification_push") as via_signal, \
                self.captureOnCommitCallbacks(execute=True):
            creer_notifications_en_masse(self._lot(NotificationLevel.DANGER))
        self.assertEqual(envoi.call_count, 2)
        via_signal.assert_not_called()

    def test_echec_du_push_n_annule_pas_les_notifications(self):
        with mock.patch(CIBLE, side_effect=RuntimeError("panne")) as envoi, \
                self.assertLogs("notifications.services", "ERROR"), self.captureOnCommitCallbacks(execute=True):
            creer_notifications_en_masse(self._lot(NotificationLevel.DANGER))
        self.assertEqual(envoi.call_count, 2)  # le second est tenté malgré l'échec du premier
        self.assertEqual(Notification.objects.count(), 2)

    def test_rien_n_est_pousse_si_la_transaction_est_annulee(self):
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    creer_notifications_en_masse(self._lot(NotificationLevel.DANGER))
                    raise RuntimeError("annulation")
            except RuntimeError:
                pass
        envoi.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)


class PushParSaveInchangeTests(TestCase):
    def test_save_danger_pousse_une_seule_fois_via_le_signal(self):
        user = User.objects.create_user("m", password="x")
        with mock.patch("notifications.push.envoyer_notification_push") as via_signal, \
                mock.patch(CIBLE) as via_service:
            Notification.objects.create(user=user, verb="Alerte", level=NotificationLevel.DANGER)
        self.assertEqual(via_signal.call_count, 1)
        via_service.assert_not_called()

    def test_save_info_et_warning_ne_poussent_pas(self):
        user = User.objects.create_user("m", password="x")
        with mock.patch("notifications.push.envoyer_notification_push") as via_signal:
            Notification.objects.create(user=user, verb="a", level=NotificationLevel.INFO)
            Notification.objects.create(user=user, verb="b", level=NotificationLevel.WARNING)
        via_signal.assert_not_called()
