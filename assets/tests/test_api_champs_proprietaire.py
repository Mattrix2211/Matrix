"""API matériel : auteur posé par le serveur, rattachement dans le périmètre de l'appelant."""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetDocument, AssetType
from org.models import Sector, Service, Ship


class ApiMaterielChampsProprietaireTests(TestCase):
    def setUp(self):
        self.a = self._navire("A")
        self.b = self._navire("B")
        self.chef = User.objects.create_user(username="chef_a_amc", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION", "ship": self.a[0]})
        self.autre = User.objects.create_user(username="autre_amc", password="pass")
        self.client = APIClient()
        self.client.login(username="chef_a_amc", password="pass")

    def _navire(self, nom):
        navire = Ship.objects.create(name=f"Navire {nom} amc", code=f"{nom}-AMC")
        service = Service.objects.create(ship=navire, name=f"Service {nom}")
        secteur = Sector.objects.create(service=service, name=f"Secteur {nom}")
        type_ = AssetType.objects.create(name=f"Type {nom}", category="Cat", sector=secteur)
        return navire, service, secteur, type_

    def _payload(self, groupe, **extra):
        navire, service, secteur, type_ = groupe
        return {"asset_type": type_.pk, "ship": navire.pk, "service": service.pk, "sector": secteur.pk, **extra}

    def test_auteur_pose_par_le_serveur(self):
        r = self.client.post("/api/assets/assets/", self._payload(self.a, created_by=self.autre.pk), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        asset = Asset.objects.get(pk=r.data["id"])
        self.assertEqual(asset.created_by, self.chef)
        r = self.client.patch(f"/api/assets/assets/{asset.pk}/", {"updated_by": self.autre.pk, "serial_number": "SN-1"}, format="json")
        asset.refresh_from_db()
        self.assertEqual(asset.updated_by, self.chef)

    def test_creation_sur_un_autre_navire_refusee(self):
        r = self.client.post("/api/assets/assets/", self._payload(self.b), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Asset.objects.exists())

    def test_deplacement_vers_un_autre_navire_refuse(self):
        asset = Asset.objects.create(asset_type=self.a[3], ship=self.a[0], service=self.a[1], sector=self.a[2])
        r = self.client.patch(
            f"/api/assets/assets/{asset.pk}/", {"ship": self.b[0].pk, "service": self.b[1].pk, "sector": self.b[2].pk},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        asset.refresh_from_db()
        self.assertEqual(asset.ship, self.a[0])

    def test_document_sur_un_materiel_hors_perimetre_refuse(self):
        asset_b = Asset.objects.create(asset_type=self.b[3], ship=self.b[0], service=self.b[1], sector=self.b[2])
        r = self.client.post(
            "/api/assets/asset-docs/",
            {"asset": asset_b.pk, "name": "Doc", "file": SimpleUploadedFile("d.txt", b"d")},
            format="multipart",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(AssetDocument.objects.exists())
