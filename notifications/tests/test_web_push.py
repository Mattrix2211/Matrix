from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from pywebpush import WebPushException
from rest_framework.test import APIClient

from notifications.models import Notification, NotificationLevel, PushSubscription
from notifications.push import envoyer_notification_push


class ReponsePushFactice:
    """Simule la réponse HTTP portée par une WebPushException (statut du
    service de push du navigateur)."""

    def __init__(self, status_code):
        self.status_code = status_code
        self.text = ""


@override_settings(VAPID_PUBLIC_KEY="clé-publique-test", VAPID_PRIVATE_KEY="clé-privée-test")
class AbonnementPushViewsTests(TestCase):
    """Vues d'abonnement/désabonnement Web Push (endpoint côté Django)."""

    def setUp(self):
        self.user = User.objects.create_user(username="marin1", password="pass")
        self.client = APIClient()
        self.client.login(username="marin1", password="pass")

    def test_abonnement_cree_une_souscription(self):
        payload = {
            "endpoint": "https://push.example.com/abo-1",
            "keys": {"p256dh": "clé-p256dh", "auth": "clé-auth"},
        }
        resp = self.client.post("/api/notifications/push/subscribe/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(
            PushSubscription.objects.filter(user=self.user, endpoint=payload["endpoint"]).exists()
        )

    def test_abonnement_incomplet_rejete(self):
        resp = self.client.post(
            "/api/notifications/push/subscribe/", {"endpoint": "https://push.example.com/abo-2"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_reabonnement_meme_endpoint_met_a_jour_sans_doublon(self):
        payload = {
            "endpoint": "https://push.example.com/abo-3",
            "keys": {"p256dh": "clé-1", "auth": "clé-auth"},
        }
        self.client.post("/api/notifications/push/subscribe/", payload, format="json")
        payload["keys"]["p256dh"] = "clé-2"
        self.client.post("/api/notifications/push/subscribe/", payload, format="json")
        self.assertEqual(PushSubscription.objects.filter(endpoint=payload["endpoint"]).count(), 1)
        self.assertEqual(
            PushSubscription.objects.get(endpoint=payload["endpoint"]).p256dh, "clé-2"
        )

    def test_desabonnement_supprime_la_souscription(self):
        sub = PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/abo-4", p256dh="p", auth="a"
        )
        resp = self.client.post(
            "/api/notifications/push/unsubscribe/", {"endpoint": sub.endpoint}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PushSubscription.objects.filter(pk=sub.pk).exists())

    def test_desabonnement_ne_touche_pas_les_souscriptions_dautrui(self):
        autre = User.objects.create_user(username="marin2", password="pass")
        sub_autrui = PushSubscription.objects.create(
            user=autre, endpoint="https://push.example.com/abo-5", p256dh="p", auth="a"
        )
        resp = self.client.post(
            "/api/notifications/push/unsubscribe/", {"endpoint": sub_autrui.endpoint}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(pk=sub_autrui.pk).exists())

    def test_cle_publique_exposee_aux_utilisateurs_connectes(self):
        resp = self.client.get("/api/notifications/push/public-key/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["publicKey"], "clé-publique-test")

    def test_endpoints_push_refuses_sans_authentification(self):
        client_anonyme = APIClient()
        resp = client_anonyme.get("/api/notifications/push/public-key/")
        self.assertEqual(resp.status_code, 403)


@override_settings(VAPID_PUBLIC_KEY="clé-publique-test", VAPID_PRIVATE_KEY="clé-privée-test")
class DeclenchementPushSurDangerTests(TestCase):
    """Le signal post_save ne doit envoyer un push QUE pour les notifications
    de niveau DANGER, jamais pour WARNING/INFO."""

    def setUp(self):
        self.user = User.objects.create_user(username="marin1", password="pass")
        PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/abo", p256dh="p", auth="a"
        )

    @patch("notifications.push.webpush")
    def test_notification_danger_declenche_un_envoi_push(self, mock_webpush):
        Notification.objects.create(user=self.user, verb="Rupture de stock critique", level=NotificationLevel.DANGER)
        self.assertTrue(mock_webpush.called)

    @patch("notifications.push.webpush")
    def test_notification_warning_ne_declenche_aucun_envoi(self, mock_webpush):
        Notification.objects.create(user=self.user, verb="Échéance proche", level=NotificationLevel.WARNING)
        mock_webpush.assert_not_called()

    @patch("notifications.push.webpush")
    def test_notification_info_ne_declenche_aucun_envoi(self, mock_webpush):
        Notification.objects.create(user=self.user, verb="Information", level=NotificationLevel.INFO)
        mock_webpush.assert_not_called()

    @patch("notifications.push.webpush")
    def test_mise_a_jour_dune_notification_existante_ne_redeclenche_pas(self, mock_webpush):
        notif = Notification.objects.create(user=self.user, verb="Alerte", level=NotificationLevel.DANGER)
        mock_webpush.reset_mock()
        notif.is_read = True
        notif.save()
        mock_webpush.assert_not_called()

    @patch("notifications.push.webpush")
    def test_perimetre_seuls_les_abonnements_du_destinataire_sont_notifies(self, mock_webpush):
        autre = User.objects.create_user(username="marin2", password="pass")
        PushSubscription.objects.create(
            user=autre, endpoint="https://push.example.com/abo-autre", p256dh="p", auth="a"
        )
        Notification.objects.create(user=self.user, verb="Alerte pour marin1", level=NotificationLevel.DANGER)
        # Un seul appel, vers l'unique abonnement de marin1 (pas celui de marin2).
        self.assertEqual(mock_webpush.call_count, 1)
        appel = mock_webpush.call_args.kwargs
        self.assertEqual(appel["subscription_info"]["endpoint"], "https://push.example.com/abo")

    @override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="")
    @patch("notifications.push.webpush")
    def test_aucun_envoi_si_cles_vapid_absentes(self, mock_webpush):
        Notification.objects.create(user=self.user, verb="Alerte sans clé VAPID", level=NotificationLevel.DANGER)
        mock_webpush.assert_not_called()


@override_settings(VAPID_PUBLIC_KEY="clé-publique-test", VAPID_PRIVATE_KEY="clé-privée-test")
class NettoyageAbonnementsInvalidesTests(TestCase):
    """Un abonnement expiré/invalide (410 Gone ou 404 Not Found côté service
    de push du navigateur) doit être supprimé proprement, sans planter."""

    def setUp(self):
        self.user = User.objects.create_user(username="marin1", password="pass")

    @patch("notifications.push.webpush")
    def test_abonnement_supprime_si_410_gone(self, mock_webpush):
        sub = PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/mort", p256dh="p", auth="a"
        )
        mock_webpush.side_effect = WebPushException("expiré", response=ReponsePushFactice(410))
        notif = Notification(user=self.user, verb="Alerte", level=NotificationLevel.DANGER)
        # Appel direct (indépendant du signal) : vérifie le comportement de nettoyage lui-même.
        envoyer_notification_push(notif)
        self.assertFalse(PushSubscription.objects.filter(pk=sub.pk).exists())

    @patch("notifications.push.webpush")
    def test_abonnement_supprime_si_404_not_found(self, mock_webpush):
        sub = PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/introuvable", p256dh="p", auth="a"
        )
        mock_webpush.side_effect = WebPushException("introuvable", response=ReponsePushFactice(404))
        notif = Notification(user=self.user, verb="Alerte", level=NotificationLevel.DANGER)
        envoyer_notification_push(notif)
        self.assertFalse(PushSubscription.objects.filter(pk=sub.pk).exists())

    @patch("notifications.push.webpush")
    def test_erreur_serveur_ne_supprime_pas_labonnement_et_ne_plante_pas(self, mock_webpush):
        sub = PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/temporaire", p256dh="p", auth="a"
        )
        mock_webpush.side_effect = WebPushException("indisponible", response=ReponsePushFactice(503))
        notif = Notification(user=self.user, verb="Alerte", level=NotificationLevel.DANGER)
        try:
            envoyer_notification_push(notif)
        except Exception as exc:  # pragma: no cover - l'assertion suivante échouerait déjà
            self.fail(f"L'envoi push ne doit jamais lever d'exception non gérée : {exc}")
        self.assertTrue(PushSubscription.objects.filter(pk=sub.pk).exists())

    @patch("notifications.push.webpush")
    def test_erreur_inattendue_ne_plante_pas(self, mock_webpush):
        PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/panne", p256dh="p", auth="a"
        )
        mock_webpush.side_effect = RuntimeError("panne réseau imprévue")
        notif = Notification(user=self.user, verb="Alerte", level=NotificationLevel.DANGER)
        try:
            envoyer_notification_push(notif)
        except Exception as exc:  # pragma: no cover
            self.fail(f"L'envoi push ne doit jamais lever d'exception non gérée : {exc}")
