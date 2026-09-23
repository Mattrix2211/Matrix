"""Test d'intégration de la validation serveur des fichiers téléversés
(tâche Notion [SEC]) sur le modèle représentatif de l'app assets : Asset.photo,
via la vraie vue de création (AssetListView.post, action="create_asset").

Le validateur lui-même est testé en profondeur dans
matrix/core/tests/test_validators.py : ce fichier vérifie seulement le
branchement (full_clean() + _afficher_erreur_validation) sur ce point d'entrée
précis, sans dupliquer les scénarios déjà couverts."""
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from org.models import Sector, Service, Ship


def _png_1x1():
    # PNG 1x1 généré à la volée par Pillow : doit décoder réellement
    # (Image.open().verify()), même fixture que test_plan_navire_web.py.
    tampon = io.BytesIO()
    PILImage.new("RGB", (1, 1), color=(128, 128, 128)).save(tampon, format="PNG")
    return tampon.getvalue()


_PNG_1X1 = _png_1x1()


class ValidationPhotoAssetTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire T-SEC-FILE")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Secteur", service=self.service)
        self.asset_type = AssetType.objects.create(name="Multimètre", category="Mesure", sector=self.sector)

        self.chef = User.objects.create_user(username="chef_photo", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE"})
        self.client.login(username="chef_photo", password="pass")

    def _creer(self, photo):
        return self.client.post("/assets/", {
            "action": "create_asset",
            "designation": "Multimètre avec photo",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "photo": photo,
        }, follow=True)

    def test_executable_renomme_en_photo_refuse(self):
        faux_png = SimpleUploadedFile(
            "virus.png", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64, content_type="image/png",
        )
        reponse = self._creer(faux_png)
        self.assertFalse(Asset.objects.filter(designation="Multimètre avec photo").exists())
        messages_affiches = [str(m) for m in reponse.context["messages"]]
        self.assertTrue(any("image valide" in m for m in messages_affiches))

    def test_photo_valide_acceptee(self):
        vraie_photo = SimpleUploadedFile("photo.png", _PNG_1X1, content_type="image/png")
        self._creer(vraie_photo)
        asset = Asset.objects.get(designation="Multimètre avec photo")
        self.assertTrue(asset.photo)
