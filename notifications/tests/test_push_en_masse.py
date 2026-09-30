"""Tests du Web Push pour les notifications créées en masse (bulk_create)."""
from unittest import mock

from django.contrib.auth.models import User
from django.db import transaction
from django.test import TestCase, override_settings

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


class PassationPushDeBoutEnBoutTests(TestCase):
    """Relève immédiate sur un double équipage : synthèse, notifications et push (envoi mocké)."""

    def setUp(self):
        from django.core.cache import cache
        from notifications.models import PushSubscription
        from org.models import Equipage, Sector, Service, Ship
        from org.tests.test_equipages import creer_marin

        cache.clear()
        self.navire = Ship.objects.create(name="FREMM P", code="FP", classe_navire="FREMM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        self.navire.equipage_a_bord = self.bleu
        self.navire.save()
        self.service = Service.objects.create(ship=self.navire, name="Machine")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.abonne = creer_marin("abonne", "EQUIPIER", self.navire, self.rouge)
        self.non_abonne = creer_marin("sans_abo", "EQUIPIER", self.navire, self.rouge)
        self.descendant = creer_marin("descendant", "EQUIPIER", self.navire, self.bleu)
        creer_marin("admin", "ADMIN_NAVIRE", self.navire)
        PushSubscription.objects.create(user=self.abonne, endpoint="https://push.invalide/abo", p256dh="k", auth="a")

    def _stock_critique(self):
        from logistics.models import StockPiece
        StockPiece.objects.create(
            reference="R1", designation="Joint", quantite=0, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )

    def _anomalie(self):
        from logistics.models import Anomalie
        Anomalie.objects.create(titre="Fuite", ship=self.navire, statut="SIGNALEE")

    def _releve(self):
        from django.urls import reverse
        from django.utils import timezone
        self.client.login(username="admin", password="pass")
        return self.client.post(reverse("equipages"), {
            "action": "planifier_releve", "equipage_id": self.rouge.pk, "date": timezone.localdate().isoformat(),
        })

    def _avec_push(self):
        return override_settings(VAPID_PRIVATE_KEY="prive", VAPID_PUBLIC_KEY="public")

    def test_releve_danger_pousse_aux_seuls_abonnes(self):
        self._stock_critique()
        with self._avec_push(), mock.patch("notifications.push.push_disponible", return_value=True), \
                mock.patch("notifications.push.webpush") as webpush, self.captureOnCommitCallbacks(execute=True):
            self._releve()
        self.assertEqual(Notification.objects.filter(level=NotificationLevel.DANGER).count(), 2)
        self.assertEqual(webpush.call_count, 1)
        self.assertEqual(webpush.call_args.kwargs["subscription_info"]["endpoint"], "https://push.invalide/abo")

    def test_releve_danger_pousse_une_fois_par_notification(self):
        self._stock_critique()
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True):
            self._releve()
        destinataires = sorted(c.args[0].user.username for c in envoi.call_args_list)
        self.assertEqual(destinataires, ["abonne", "sans_abo"])

    def test_releve_warning_ne_pousse_pas(self):
        self._anomalie()
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True):
            self._releve()
        self.assertEqual(Notification.objects.filter(level=NotificationLevel.WARNING).count(), 2)
        envoi.assert_not_called()

    def test_releve_info_ne_pousse_pas(self):
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True):
            self._releve()
        self.assertEqual(Notification.objects.filter(level=NotificationLevel.INFO).count(), 2)
        envoi.assert_not_called()

    def test_releve_dont_la_generation_echoue_ne_pousse_rien(self):
        from org import passation
        self._stock_critique()
        with mock.patch(CIBLE) as envoi, self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(passation, "construire_contenu", side_effect=RuntimeError("panne")):
            with self.assertRaises(RuntimeError):
                self._releve()
        envoi.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    def test_echec_du_push_n_empeche_ni_la_releve_ni_les_notifications(self):
        from org.models import SynthesePassation
        self._stock_critique()
        with mock.patch(CIBLE, side_effect=RuntimeError("panne")), self.assertLogs("notifications.services", "ERROR"), \
                self.captureOnCommitCallbacks(execute=True):
            self._releve()
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, self.rouge)
        self.assertEqual(SynthesePassation.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 2)


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
