from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Location


class PerimetreLocationWebTests(TestCase):
    """Vérifie que LocationListView.post revalide bien le périmètre posté
    (ship_id) et l'emplacement ciblé (pk), et que la liste ne plante pas
    pour un utilisateur scopé en dessous du niveau navire (service/secteur/
    section) alors que Location n'a qu'un champ ship direct."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="LOC-A")
        self.service = Service.objects.create(name="Srv A", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec A", service=self.service)

        self.autre_ship = Ship.objects.create(name="Navire B", code="LOC-B")

        self.chef = User.objects.create_user(username="chef_loc", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship, "sector": self.sector}
        )

        self.equipier = User.objects.create_user(username="equipier_loc", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.emplacement = Location.objects.create(name="Local A", ship=self.ship)
        self.emplacement_hors_perimetre = Location.objects.create(name="Local B", ship=self.autre_ship)

    def test_liste_ne_plante_pas_pour_un_utilisateur_scope_au_secteur(self):
        """Location n'a qu'un champ ship direct — un utilisateur scopé au
        secteur (donc plus fin que ship) ne doit pas faire planter
        ScopedQuerySetMixin (ImproperlyConfigured), grâce à la traduction de
        périmètre via ship__services__sectors__id."""
        self.client.login(username="chef_loc", password="pass")
        r = self.client.get("/locations/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.emplacement, list(r.context["locations"]))
        self.assertNotIn(self.emplacement_hors_perimetre, list(r.context["locations"]))

    def test_chef_peut_creer_un_emplacement_en_postant_son_propre_navire(self):
        """Cas nominal : le chef est scopé au secteur (plus fin que ship) mais
        le formulaire poste toujours le ship_id — doit être reconnu comme
        l'ancêtre de son propre périmètre, pas rejeté."""
        self.client.login(username="chef_loc", password="pass")
        r = self.client.post("/locations/", {
            "action": "create_location",
            "name": "Nouveau local",
            "ship_id": str(self.ship.id),
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Location.objects.filter(name="Nouveau local").exists())

    def test_chef_ne_peut_pas_creer_un_emplacement_hors_de_son_navire(self):
        self.client.login(username="chef_loc", password="pass")
        r = self.client.post("/locations/", {
            "action": "create_location",
            "name": "Local frauduleux",
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Location.objects.filter(name="Local frauduleux").exists())

    def test_chef_ne_peut_pas_editer_un_emplacement_hors_de_son_perimetre(self):
        self.client.login(username="chef_loc", password="pass")
        r = self.client.post("/locations/", {
            "action": "edit_location",
            "pk": str(self.emplacement_hors_perimetre.id),
            "name": "Renommé frauduleusement",
        })
        self.assertEqual(r.status_code, 302)
        self.emplacement_hors_perimetre.refresh_from_db()
        self.assertEqual(self.emplacement_hors_perimetre.name, "Local B")

    def test_chef_service_ne_peut_pas_supprimer_un_emplacement_hors_de_son_perimetre(self):
        self.client.login(username="chef_loc", password="pass")
        self.client.post("/locations/", {
            "action": "delete_location",
            "pk": str(self.emplacement_hors_perimetre.id),
        })
        self.assertTrue(Location.objects.filter(pk=self.emplacement_hors_perimetre.id).exists())
