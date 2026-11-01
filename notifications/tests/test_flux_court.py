"""Panneau de notifications : flux court (non lues et actions à traiter), historique complet dans le centre."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification, NotificationLevel


class FluxCourtTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")
        self.non_lue = Notification.objects.create(user=self.marin, verb="Nouvelle information", level=NotificationLevel.INFO)
        self.lue = Notification.objects.create(user=self.marin, verb="Ancienne information lue", level=NotificationLevel.INFO, is_read=True)
        self.action_lue = Notification.objects.create(
            user=self.marin, verb="Accusé à donner", level=NotificationLevel.WARNING, is_read=True, action_requise=True)
        self.action_traitee = Notification.objects.create(
            user=self.marin, verb="Action déjà traitée", level=NotificationLevel.WARNING, is_read=True, action_requise=True,
            traitee_le=timezone.now())

    def _panneau(self):
        return self.client.get(reverse("notifications-panneau")).content.decode()

    def test_le_panneau_retire_les_lues_mais_garde_les_actions_a_traiter(self):
        page = self._panneau()
        self.assertIn("Nouvelle information", page)
        self.assertIn("Accusé à donner", page)  # lue mais pas traitée : toujours identifiable
        self.assertIn("À traiter", page)
        self.assertNotIn("Ancienne information lue", page)
        self.assertNotIn("Action déjà traitée", page)

    def test_marquer_lue_retire_du_flux_court_sans_perdre_l_historique(self):
        reponse = self.client.post(reverse("notifications-lue", args=[self.non_lue.pk]))
        self.assertNotContains(reponse, "Nouvelle information")
        self.assertTrue(Notification.objects.filter(pk=self.non_lue.pk, is_read=True).exists())
        centre = self.client.get(reverse("notifications-centre")).content.decode()
        for texte in ("Nouvelle information", "Ancienne information lue", "Accusé à donner", "Action déjà traitée"):
            self.assertIn(texte, centre)

    def test_lue_ne_vaut_pas_traitee(self):
        self.client.post(reverse("notifications-tout-lu"))
        self.assertIn("Accusé à donner", self._panneau())

    def test_le_panneau_ne_montre_que_mes_notifications(self):
        autre = User.objects.create_user(username="autre", password="pass")
        Notification.objects.create(user=autre, verb="Secret de l'autre", level=NotificationLevel.DANGER)
        self.assertNotIn("Secret de l'autre", self._panneau())

    def test_historique_accessible_depuis_le_panneau(self):
        self.assertIn(reverse("notifications-centre"), self._panneau())


class AlertesUrgentesAppareilTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")

    @override_settings(VAPID_PUBLIC_KEY="")
    def test_instance_sans_cle_d_envoi_explique_l_indisponibilite(self):
        page = self.client.get(reverse("notifications-panneau")).content.decode()
        self.assertRegex(page, r'id="push-toggle"[^>]*disabled')
        self.assertIn("Non activées sur cette instance", page)

    @override_settings(VAPID_PUBLIC_KEY="cle-publique-d-essai")
    def test_instance_autorisee_garde_l_interrupteur_actif(self):
        page = self.client.get(reverse("notifications-panneau")).content.decode()
        self.assertNotRegex(page, r'id="push-toggle"[^>]*disabled')
        self.assertNotIn("Non activées sur cette instance", page)
