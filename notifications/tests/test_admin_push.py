from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notifications.models import PushSubscription

ENDPOINT = "https://push.exemple.test/" + "a" * 100 + "SECRET-FIN"


class PushSubscriptionAdminTests(TestCase):
    """L'admin ne doit jamais exposer l'endpoint complet ni les clés d'un abonnement."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin1", password="pass", email="a@b.fr")
        self.marin = User.objects.create_user(username="marin1", password="pass")
        self.abonnement = PushSubscription.objects.create(
            user=self.marin, endpoint=ENDPOINT, p256dh="CLE-P256DH-SECRETE", auth="CLE-AUTH-SECRETE"
        )
        self.client.login(username="admin1", password="pass")

    def test_liste_sans_endpoint_complet(self):
        reponse = self.client.get(reverse("admin:notifications_pushsubscription_changelist"))
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, "SECRET-FIN")
        self.assertContains(reponse, ENDPOINT[:40])

    def test_detail_sans_endpoint_ni_cles(self):
        url = reverse("admin:notifications_pushsubscription_change", args=[self.abonnement.pk])
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        for secret in ("SECRET-FIN", "CLE-P256DH-SECRETE", "CLE-AUTH-SECRETE"):
            self.assertNotContains(reponse, secret)

    def test_ajout_interdit_et_suppression_possible(self):
        reponse = self.client.get(reverse("admin:notifications_pushsubscription_add"))
        self.assertEqual(reponse.status_code, 403)
        url = reverse("admin:notifications_pushsubscription_delete", args=[self.abonnement.pk])
        reponse = self.client.post(url, {"post": "yes"})
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(PushSubscription.objects.filter(pk=self.abonnement.pk).exists())

    def test_recherche_par_utilisateur_uniquement(self):
        url = reverse("admin:notifications_pushsubscription_changelist")
        self.assertContains(self.client.get(url, {"q": "marin1"}), ENDPOINT[:40])
        self.assertNotContains(self.client.get(url, {"q": "SECRET-FIN"}), ENDPOINT[:40])
