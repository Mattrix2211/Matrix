from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from notifications.models import Notification

BASE = "/api/notifications/notifications/"


class NotificationApiDroitsTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username="u1", password="pass")
        self.u2 = User.objects.create_user(username="u2", password="pass")
        self.n1 = Notification.objects.create(user=self.u1, verb="n1")
        self.n2 = Notification.objects.create(user=self.u2, verb="n2")
        self.client = APIClient()
        self.client.login(username="u1", password="pass")

    def test_creation_interdite(self):
        reponse = self.client.post(BASE, {"user": self.u2.pk, "verb": "faux"}, format="json")
        self.assertEqual(reponse.status_code, 405)
        self.assertFalse(Notification.objects.filter(verb="faux").exists())

    def test_suppression_et_remplacement_interdits(self):
        self.assertEqual(self.client.delete(f"{BASE}{self.n1.pk}/").status_code, 405)
        reponse = self.client.put(f"{BASE}{self.n1.pk}/", {"verb": "x"}, format="json")
        self.assertEqual(reponse.status_code, 405)
        self.assertTrue(Notification.objects.filter(pk=self.n1.pk).exists())

    def test_marquage_lu_autorise(self):
        reponse = self.client.patch(f"{BASE}{self.n1.pk}/", {"is_read": True}, format="json")
        self.assertEqual(reponse.status_code, 200)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_champs_autres_que_is_read_ignores(self):
        self.client.patch(
            f"{BASE}{self.n1.pk}/",
            {"user": self.u2.pk, "verb": "détourné", "level": "danger"},
            format="json",
        )
        self.n1.refresh_from_db()
        self.assertEqual(self.n1.user, self.u1)
        self.assertEqual(self.n1.verb, "n1")
        self.assertEqual(self.n1.level, "info")

    def test_notification_d_autrui_inaccessible(self):
        url = f"{BASE}{self.n2.pk}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"is_read": True}, format="json").status_code, 404)
        self.n2.refresh_from_db()
        self.assertFalse(self.n2.is_read)

    def test_mark_all_read_limite_a_soi(self):
        reponse = self.client.post(f"{BASE}mark_all_read/")
        self.assertEqual(reponse.status_code, 200)
        self.n1.refresh_from_db()
        self.n2.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.assertFalse(self.n2.is_read)

    def test_anonyme_refuse(self):
        reponse = APIClient().get(BASE)
        self.assertIn(reponse.status_code, (401, 403))
