"""Test d'intégration de la validation serveur des fichiers téléversés
(tâche Notion [SEC]) sur le modèle représentatif de l'app logistics :
StockPiece.photo, via la vraie vue de création (stock-piece-list,
action="create_piece").

Le validateur lui-même est testé en profondeur dans
matrix/core/tests/test_validators.py."""
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image as PILImage

from accounts.models import UserProfile
from logistics.models import StockPiece
from org.models import Sector, Service, Ship


def _png_1x1():
    # PNG 1x1 généré à la volée par Pillow : doit décoder réellement
    # (Image.open().verify()), même fixture que test_plan_navire_web.py.
    tampon = io.BytesIO()
    PILImage.new("RGB", (1, 1), color=(128, 128, 128)).save(tampon, format="PNG")
    return tampon.getvalue()


_PNG_1X1 = _png_1x1()


class ValidationPhotoStockPieceTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T-SEC-FILE-2")
        self.service = Service.objects.create(ship=self.navire, name="Srv")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur")

        self.chef = User.objects.create_user(username="chef_stock_photo", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION", "sector": self.secteur})
        self.client.login(username="chef_stock_photo", password="pass")
        self.url = reverse("stock-piece-list")

    def _creer(self, photo):
        return self.client.post(self.url, {
            "action": "create_piece", "reference": "REF-SEC", "designation": "Pièce",
            "quantite": "1", "quantite_minimale": "1", "sector_id": self.secteur.id,
            "photo": photo,
        })

    def test_fichier_trop_gros_refuse(self):
        # Dépasse la taille maximale par défaut (10 Mo) pour une image.
        contenu_volumineux = _PNG_1X1 + b"\x00" * (11 * 1024 * 1024)
        fichier = SimpleUploadedFile("photo.png", contenu_volumineux, content_type="image/png")
        self._creer(fichier)
        self.assertFalse(StockPiece.objects.filter(reference="REF-SEC").exists())

    def test_photo_valide_acceptee(self):
        fichier = SimpleUploadedFile("photo.png", _PNG_1X1, content_type="image/png")
        self._creer(fichier)
        piece = StockPiece.objects.get(reference="REF-SEC")
        self.assertTrue(piece.photo)
