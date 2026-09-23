from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile


class AnnuaireUtilisateursPermissionsTests(TestCase):
    """[BUG SEC] L'annuaire (/users/) doit être réservé aux administrateurs
    (COMMANDANT et au-dessus) : aucun seuil n'était appliqué auparavant, ce qui
    permettait à n'importe quel utilisateur connecté (y compris un CHEF_SECTEUR)
    de consulter et de gérer les comptes de tous les marins."""

    def setUp(self):
        self.chef_secteur = User.objects.create_user(username="cs_annuaire", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR"})
        self.commandant = User.objects.create_user(username="cmd_annuaire", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

    def test_chef_secteur_ne_peut_pas_consulter_annuaire(self):
        self.client.login(username="cs_annuaire", password="pass")
        r = self.client.get("/users/")
        self.assertEqual(r.status_code, 403)

    def test_commandant_peut_consulter_annuaire(self):
        self.client.login(username="cmd_annuaire", password="pass")
        r = self.client.get("/users/")
        self.assertEqual(r.status_code, 200)

    def test_anonyme_redirige_vers_connexion(self):
        r = self.client.get("/users/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url)
