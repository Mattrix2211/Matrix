from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from org.models import Ship, Service, Sector


class ListesSelectionMultipleTests(TestCase):
    """Listes des matériels et des installations : sélection multiple, menu ⋯ par carte,
    ajout depuis le catalogue, droits et équipage à terre."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.type = AssetType.objects.create(name="Pompe", category="Méca", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.type, ship=self.ship, service=self.service, sector=self.sector,
            internal_id="A1", designation="Pompe de cale",
        )
        self.installation = Installation.objects.create(
            designation="Groupe froid", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.chef = self._marin("chef", "CHEF_SERVICE", "A")
        self.equipier = self._marin("equipier", "EQUIPIER", "A")
        self.a_terre = self._marin("terre", "CHEF_SERVICE", "B")

    def _marin(self, nom, role, equipage):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "ship": self.ship, "service": self.service, "equipage": equipage},
        )
        return user

    def _get(self, nom, url):
        self.client.login(username=nom, password="pass")
        return self.client.get(url).content.decode()

    def test_entete_compteur_et_action_principale_catalogue(self):
        html = self._get("chef", "/assets/")
        self.assertIn("Matériels — 1 matériel", html)
        self.assertIn("Ajouter du matériel", html)
        self.assertNotIn("createAssetModal", html)
        self.assertIn("Installations — 1 installation", self._get("chef", "/installations/"))

    def test_chef_voit_cases_barre_masquee_et_menu(self):
        for url in ("/assets/", "/installations/"):
            html = self._get("chef", url)
            self.assertIn('class="mx-barre-selection d-none"', html)
            self.assertIn("row-select", html)
            self.assertIn("mx-liste-carte__menu", html)

    def test_equipier_sans_actions_de_gestion(self):
        for url in ("/assets/", "/installations/"):
            html = self._get("equipier", url)
            self.assertNotIn("row-select", html)
            self.assertNotIn("mx-liste-carte__menu", html)
            self.assertNotIn('id="barreSelection"', html)

    def test_equipage_a_terre_actions_masquees(self):
        for url in ("/assets/", "/installations/"):
            html = self._get("terre", url)
            self.assertNotIn("row-select", html)
            self.assertNotIn("mx-liste-carte__menu", html)
            self.assertNotIn("Ajouter du matériel", html)

    def test_filtre_actif_en_etiquette_supprimable(self):
        html = self._get("chef", f"/assets/?status=FAULTY&ship={self.ship.id}")
        self.assertIn("Statut : Défectueux ×", html)
        self.assertIn(f"Unité : {self.ship.name} ×", html)

    def test_action_groupee_ignore_les_ids_hors_perimetre(self):
        autre_navire = Ship.objects.create(name="Navire B", code="NAV-B")
        service = Service.objects.create(name="Srv B", ship=autre_navire)
        secteur = Sector.objects.create(name="Sec B", service=service)
        type_b = AssetType.objects.create(name="Pompe B", category="Méca", sector=secteur)
        etranger = Asset.objects.create(
            asset_type=type_b, ship=autre_navire, service=service, sector=secteur, internal_id="B1",
        )
        self.client.login(username="chef", password="pass")
        self.client.post("/assets/", {
            "action": "bulk_update_status", "status": "FAULTY",
            "selected_ids": [str(self.asset.id), str(etranger.id)],
        })
        self.asset.refresh_from_db()
        etranger.refresh_from_db()
        self.assertEqual(self.asset.status, "FAULTY")
        self.assertEqual(etranger.status, "OK")

    def test_menu_dossiers_rendu_avant_le_script_qui_l_utilise(self):
        # Le script ne doit jamais chercher le menu avant qu'il existe dans la page.
        html = self._get("chef", "/assets/")
        self.assertLess(html.index('id="folderContextMenu"'), html.index("getElementById('folderContextMenu')"))
