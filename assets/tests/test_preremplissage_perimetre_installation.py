from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector


class PreremplissagePerimetreInstallationTests(TestCase):
    """UX : le formulaire de création d'installation pré-sélectionne
    Navire/Service/Secteur à partir du périmètre du profil de l'utilisateur
    connecté, pour éviter de ressaisir à la main ce que l'application connaît
    déjà (principe « plus rapide qu'Excel »)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment A", code="BATA")
        self.service = Service.objects.create(name="Service A", ship=self.ship)
        self.sector = Sector.objects.create(name="Secteur A", service=self.service)
        # Un second navire/service/secteur pour vérifier qu'ils ne sont pas
        # pré-sélectionnés à tort.
        self.autre_ship = Ship.objects.create(name="Bâtiment B", code="BATB")
        self.autre_service = Service.objects.create(name="Service B", ship=self.autre_ship)
        self.autre_sector = Sector.objects.create(name="Secteur B", service=self.autre_service)

    def test_options_du_perimetre_du_profil_preselectionnees(self):
        equipier = User.objects.create_user(username="marin1", password="pass")
        UserProfile.objects.update_or_create(
            user=equipier,
            defaults={"role": "EQUIPIER", "ship": self.ship, "service": self.service, "sector": self.sector},
        )
        self.client.login(username="marin1", password="pass")
        r = self.client.get("/installations/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(f'<option value="{self.ship.id}" selected>', html)
        self.assertIn(f'<option value="{self.service.id}" data-ship="{self.ship.id}" selected>', html)
        self.assertIn(f'<option value="{self.sector.id}" data-service="{self.service.id}" selected>', html)
        # Le navire/service/secteur du profil ne doivent pas apparaître
        # sélectionnés pour les autres.
        self.assertNotIn(f'<option value="{self.autre_ship.id}" selected>', html)

    def test_sans_perimetre_le_formulaire_reste_vide_pas_de_regression(self):
        # Profil auto-créé par le signal post_save sans navire/service/secteur
        # assigné (ex. COMMANDANT sans périmètre restreint) : aucune régression,
        # les menus restent vides comme avant.
        sans_perimetre = User.objects.create_user(username="cmdt1", password="pass")
        UserProfile.objects.update_or_create(user=sans_perimetre, defaults={"role": "COMMANDANT"})
        self.client.login(username="cmdt1", password="pass")
        r = self.client.get("/installations/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertNotIn(f'<option value="{self.ship.id}" selected>', html)
        self.assertNotIn(f'<option value="{self.autre_ship.id}" selected>', html)
