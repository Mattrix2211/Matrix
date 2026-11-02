from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ConnexionTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="marin", password="pass")

    def test_le_formulaire_se_soumet_au_clavier_et_protege_du_double_envoi(self):
        page = self.client.get(reverse("login"))
        self.assertContains(page, '<button class="btn btn-primary w-100" type="submit" id="bouton-connexion">')
        self.assertContains(page, "formulaire.dataset.envoye")
        self.assertContains(page, 'autocomplete="current-password" required')

    def test_identifiants_valides_connectent(self):
        reponse = self.client.post(reverse("login"), {"username": "marin", "password": "pass"})
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_identifiants_invalides_affichent_l_erreur_sans_connecter(self):
        reponse = self.client.post(reverse("login"), {"username": "marin", "password": "faux"})
        self.assertContains(reponse, "Identifiants invalides")
        self.assertNotIn("_auth_user_id", self.client.session)
