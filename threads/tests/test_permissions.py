from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from threads.models import Thread, Message
from django.contrib.contenttypes.models import ContentType


class ThreadPermissionTests(TestCase):
    def test_only_author_can_update_message(self):
        user1 = User.objects.create_user(username="u1", password="pass")
        user2 = User.objects.create_user(username="u2", password="pass")
        client = APIClient()

        # Création d'une discussion (rattachée à n'importe quel modèle, ex. User)
        ct = ContentType.objects.get_for_model(User)
        thread = Thread.objects.create(content_type=ct, object_id=str(user1.pk))
        msg = Message.objects.create(thread=thread, author=user1, body="hello")

        # user2 tente de modifier le message de user1
        client.login(username="u2", password="pass")
        url = f"/api/threads/messages/{msg.id}/"
        resp = client.patch(url, {"body": "hack"}, format="json")
        self.assertEqual(resp.status_code, 403)

        # l'auteur peut modifier son message
        client.logout()
        client.login(username="u1", password="pass")
        resp2 = client.patch(url, {"body": "updated"}, format="json")
        self.assertIn(resp2.status_code, (200, 202))
