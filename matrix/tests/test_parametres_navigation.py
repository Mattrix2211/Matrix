"""Paramètres : navigation verticale par sections, délai de déconnexion affiché sans être modifiable."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from org.models import Ship


class NavigationParametresTests(TestCase):
    def setUp(self):
        self.url = reverse("settings")
        self.root = User.objects.create_superuser(username="root_nav", password="pass", email="r@r.fr")

    def test_superuser_voit_les_quatre_sections_et_tous_les_reglages(self):
        self.client.login(username="root_nav", password="pass")
        page = self.client.get(self.url)
        for titre in ("Organisation", "Utilisateurs et droits", "Application", "Système"):
            self.assertContains(page, f">{titre}</h2>")
        for onglet in ("navires", "hierarchie", "installations", "utilisateurs", "seuils_role",
                       "responsables", "equipage", "generale", "modules", "notifications", "journal"):
            self.assertContains(page, f"/parametre/?tab={onglet}")

    def test_chaque_onglet_repond_et_marque_son_lien_actif(self):
        self.client.login(username="root_nav", password="pass")
        Ship.objects.create(name="Navire param", code="NV-PRM")
        for onglet in ("navires", "hierarchie", "installations", "utilisateurs", "seuils_role",
                       "responsables", "equipage", "generale", "modules", "notifications", "journal"):
            page = self.client.get(self.url, {"tab": onglet})
            self.assertEqual(page.status_code, 200, onglet)
            self.assertContains(page, "mx-parametres__lien--actif")

    def test_responsables_separes_des_referentiels(self):
        self.client.login(username="root_nav", password="pass")
        self.assertContains(self.client.get(self.url, {"tab": "responsables"}), "Responsables de spécialité")
        self.assertNotContains(self.client.get(self.url, {"tab": "responsables"}), "Rôles disponibles")
        self.assertNotContains(self.client.get(self.url, {"tab": "utilisateurs"}), "Responsables de spécialité")

    @override_settings(INACTIVITE_DELAI_SECONDES=1800, INACTIVITE_AVERTISSEMENT_SECONDES=45)
    def test_delai_de_deconnexion_affiche_sans_formulaire(self):
        self.client.login(username="root_nav", password="pass")
        page = self.client.get(self.url, {"tab": "generale"})
        self.assertContains(page, "<strong>30 minutes</strong>")
        self.assertContains(page, "<strong>45 secondes</strong>")
        self.assertNotContains(page, 'name="inactivite')

    def test_marin_simple_ne_voit_que_les_notifications(self):
        marin = User.objects.create_user(username="marin_nav", password="pass")
        UserProfile.objects.update_or_create(user=marin, defaults={"role": "EQUIPIER"})
        self.client.login(username="marin_nav", password="pass")
        page = self.client.get(self.url, {"tab": "notifications"})
        self.assertContains(page, "Mes notifications")
        self.assertNotContains(page, "tab=journal")
        self.assertNotContains(page, ">Organisation</h2>")
        self.assertEqual(self.client.get(self.url, {"tab": "journal"}).status_code, 403)
