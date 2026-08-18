from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from org.models import Sector, Service, Ship


class QrGenerationTests(TestCase):
    """Le QR d'un équipement (matériel mobile ou installation fixe) doit
    pointer vers la vue web /scan/<uuid>/ (checklist du jour ou fiche
    équipement), pas vers l'API JSON brute — inutilisable au poste de travail
    (cf. CLAUDE.md, workflow « Scan QR → occurrence du jour → checklist »)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        self.installation = Installation.objects.create(
            designation="Pompe A", ship=self.ship, service=self.service, sector=self.sector,
        )

        self.marin = User.objects.create_user(username="marin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship}
        )
        self.client = APIClient()
        self.client.login(username="marin_a", password="pass")

    def test_qr_asset_pointe_vers_la_vue_scan(self):
        response = self.client.get(f"/api/assets/assets/{self.asset.id}/qr/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"/scan/{self.asset.id}/", response.data["url"])

    def test_qr_png_asset_renvoie_une_image(self):
        response = self.client.get(f"/api/assets/assets/{self.asset.id}/qr_png/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_qr_installation_pointe_vers_la_vue_scan(self):
        response = self.client.get(f"/api/assets/installations/{self.installation.id}/qr/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"/scan/{self.installation.id}/", response.json()["url"])

    def test_qr_png_installation_renvoie_une_image(self):
        response = self.client.get(f"/api/assets/installations/{self.installation.id}/qr_png/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
