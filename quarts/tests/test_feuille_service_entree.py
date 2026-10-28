"""Feuille de service : l'entrée de menu mène à la feuille du bâtiment de l'utilisateur, jamais à un 403."""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase

from accounts.models import UserProfile
from matrix.core.navigation import construire_navigation
from org.models import Service, Ship


def creer_marin(username, role, ship, service=None):
    user = User.objects.create_user(username=username, password="pass", is_superuser=(role == "MASTER_ADMIN"))
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "service": service})
    return User.objects.get(pk=user.pk)


class EntreeFeuilleServiceTests(TestCase):
    def setUp(self):
        # « Aaa » est créé en premier et trié en tête : l'ancien .first() y envoyait tout le monde.
        self.premier = Ship.objects.create(name="Aaa premier", code="AA", classe_navire="FDA")
        self.navire_a = Ship.objects.create(name="Navire A", code="NA", classe_navire="FDA")
        self.navire_b = Ship.objects.create(name="Navire B", code="NB", classe_navire="FDA")
        service = Service.objects.create(ship=self.navire_a, name="Énergie")
        self.marins = {
            "cdt_a": creer_marin("cdt_a", "COMMANDANT", self.navire_a),
            "cdt_b": creer_marin("cdt_b", "COMMANDANT", self.navire_b),
            "chef_service_a": creer_marin("chef_service_a", "CHEF_SERVICE", self.navire_a, service),
            "second_a": creer_marin("second_a", "COMMANDANT_EN_SECOND", self.navire_a),
        }

    def test_le_commandant_arrive_sur_son_batiment(self):
        for nom, navire in (("cdt_a", self.navire_a), ("cdt_b", self.navire_b),
                            ("chef_service_a", self.navire_a), ("second_a", self.navire_a)):
            self.client.login(username=nom, password="pass")
            reponse = self.client.get("/quarts/feuille-service/", follow=True)
            self.assertEqual(reponse.status_code, 200, nom)
            self.assertEqual(reponse.resolver_match.kwargs["ship_id"], navire.pk, nom)

    def test_administrateur_general_sans_batiment_suit_le_batiment_courant(self):
        creer_marin("admin", "MASTER_ADMIN", None)
        self.client.login(username="admin", password="pass")
        session = self.client.session
        session["batiment_courant_id"] = self.navire_b.pk
        session.save()
        reponse = self.client.get("/quarts/feuille-service/", follow=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.resolver_match.kwargs["ship_id"], self.navire_b.pk)

    def test_utilisateur_sans_batiment_n_a_pas_l_entree_de_menu(self):
        sans = creer_marin("sans_navire", "EQUIPIER", None)
        def libelles(user):
            return [e["libelle"] for g in construire_navigation(user, "/") for e in g["entrees"]]

        self.assertNotIn("Feuille de service", libelles(sans))
        self.assertIn("Feuille de service", libelles(self.marins["cdt_a"]))


class EntreeFeuilleServiceComptesDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_chaque_compte_arrive_sur_une_page_200(self):
        for nom in ("cdt_a", "cdt_b", "cdt_nor", "chef_service_a", "coma_comanav", "coma_comaeq", "second_a", "admin"):
            client = Client()
            client.force_login(User.objects.get(username=nom))
            reponse = client.get("/quarts/feuille-service/", follow=True)
            self.assertEqual(reponse.status_code, 200, nom)
            ship = reponse.resolver_match.kwargs["ship_id"]
            profil = User.objects.get(username=nom).profile
            if profil.ship_id:
                self.assertEqual(ship, profil.ship_id, nom)
