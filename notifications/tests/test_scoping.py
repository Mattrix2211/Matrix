from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from notifications.models import Notification


class NotificationScopingTests(TestCase):
    def test_notifications_scoped_to_user(self):
        u1 = User.objects.create_user(username="u1", password="pass")
        u2 = User.objects.create_user(username="u2", password="pass")

        Notification.objects.create(user=u1, verb="n1")
        Notification.objects.create(user=u2, verb="n2")

        client = APIClient()
        client.login(username="u1", password="pass")
        resp = client.get("/api/notifications/notifications/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["verb"], "n1")
