"""[SEC] Les photos affectées directement (`objet.photo = fichier`) dans les vues
web doivent être contrôlées côté serveur (extension + contenu réel + taille) :
le contrôle passe par les validateurs du champ, déclenchés par `full_clean()`
avant `save()`. Ces tests verrouillent ce branchement sur les trois chemins
concernés : création d'installation, édition d'installation (fiche détail) et
édition de matériel. Le validateur lui-même est testé dans
matrix/core/tests/test_validators.py."""
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from matrix.core.testing import MediaRootTemporaireMixin
from org.models import Sector, Service, Ship


def _png():
    tampon = io.BytesIO()
    PILImage.new("RGB", (1, 1), color=(10, 20, 30)).save(tampon, format="PNG")
    return tampon.getvalue()


_FAUX_EXE = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64


class PhotosAffecteesDirectementTests(MediaRootTemporaireMixin, TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Photos")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.asset_type = AssetType.objects.create(name="Type", category="Cat", sector=self.sector)
        chef = User.objects.create_user(username="chef_photos", password="pass")
        UserProfile.objects.update_or_create(user=chef, defaults={"role": "CHEF_SERVICE"})
        self.client.login(username="chef_photos", password="pass")
        self.installation = Installation.objects.create(
            designation="Pompe", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.asset = Asset.objects.create(
            designation="Multimètre", asset_type=self.asset_type, ship=self.ship,
            service=self.service, sector=self.sector,
        )

    def _org(self):
        return {"ship_id": self.ship.id, "service_id": self.service.id, "sector_id": self.sector.id}

    def _messages(self, reponse):
        return [str(m) for m in reponse.context["messages"]]

    # --- Création d'installation -------------------------------------------
    def _creer_installation(self, photo):
        return self.client.post("/installations/", {
            "action": "create_installation", "designation": "Nouvelle pompe", "photo": photo, **self._org(),
        }, follow=True)

    def test_creation_installation_photo_valide(self):
        self._creer_installation(SimpleUploadedFile("p.png", _png(), content_type="image/png"))
        self.assertTrue(Installation.objects.get(designation="Nouvelle pompe").photo)

    def test_creation_installation_executable_renomme_refuse(self):
        r = self._creer_installation(SimpleUploadedFile("virus.jpg", _FAUX_EXE, content_type="image/jpeg"))
        self.assertFalse(Installation.objects.filter(designation="Nouvelle pompe").exists())
        self.assertTrue(any("image valide" in m for m in self._messages(r)))

    def test_creation_installation_fichier_vide_refuse(self):
        r = self._creer_installation(SimpleUploadedFile("vide.png", b"", content_type="image/png"))
        self.assertFalse(Installation.objects.filter(designation="Nouvelle pompe").exists())
        self.assertTrue(self._messages(r))

    # --- Édition d'installation (fiche détail) -----------------------------
    def _editer_installation(self, photo):
        return self.client.post(f"/installations/{self.installation.id}/", {
            "action": "edit_installation", "pk": self.installation.id,
            "designation": "Pompe", "photo": photo, **self._org(),
        }, follow=True)

    def test_edition_installation_photo_valide(self):
        self._editer_installation(SimpleUploadedFile("p.png", _png(), content_type="image/png"))
        self.installation.refresh_from_db()
        self.assertTrue(self.installation.photo)

    def test_edition_installation_executable_renomme_refuse(self):
        r = self._editer_installation(SimpleUploadedFile("virus.jpg", _FAUX_EXE, content_type="image/jpeg"))
        self.installation.refresh_from_db()
        self.assertFalse(self.installation.photo)
        self.assertTrue(any("image valide" in m for m in self._messages(r)))

    def test_edition_installation_fichier_vide_refuse(self):
        r = self._editer_installation(SimpleUploadedFile("vide.png", b"", content_type="image/png"))
        self.installation.refresh_from_db()
        self.assertFalse(self.installation.photo)
        self.assertTrue(self._messages(r))

    # --- Création de matériel ----------------------------------------------
    def _creer_asset(self, photo):
        return self.client.post("/assets/", {
            "action": "create_asset", "designation": "Nouveau multimètre", "photo": photo, **self._org(),
        }, follow=True)

    def test_creation_materiel_photo_valide(self):
        self._creer_asset(SimpleUploadedFile("p.png", _png(), content_type="image/png"))
        self.assertTrue(Asset.objects.get(designation="Nouveau multimètre").photo)

    def test_creation_materiel_executable_renomme_refuse(self):
        r = self._creer_asset(SimpleUploadedFile("virus.jpg", _FAUX_EXE, content_type="image/jpeg"))
        self.assertFalse(Asset.objects.filter(designation="Nouveau multimètre").exists())
        self.assertTrue(any("image valide" in m for m in self._messages(r)))

    # --- Édition de matériel -----------------------------------------------
    def _editer_asset(self, photo):
        return self.client.post("/assets/", {
            "action": "edit_asset", "pk": self.asset.id, "designation": "Multimètre",
            "photo": photo, **self._org(),
        }, follow=True)

    def test_edition_materiel_photo_valide(self):
        self._editer_asset(SimpleUploadedFile("p.png", _png(), content_type="image/png"))
        self.asset.refresh_from_db()
        self.assertTrue(self.asset.photo)

    def test_edition_materiel_executable_renomme_refuse(self):
        r = self._editer_asset(SimpleUploadedFile("virus.jpg", _FAUX_EXE, content_type="image/jpeg"))
        self.asset.refresh_from_db()
        self.assertFalse(self.asset.photo)
        self.assertTrue(any("image valide" in m for m in self._messages(r)))

    def test_edition_materiel_fichier_vide_refuse(self):
        r = self._editer_asset(SimpleUploadedFile("vide.png", b"", content_type="image/png"))
        self.asset.refresh_from_db()
        self.assertFalse(self.asset.photo)
        self.assertTrue(self._messages(r))
