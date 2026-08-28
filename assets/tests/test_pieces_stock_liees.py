"""Tests de l'affichage des pièces de stock affiliées sur les fiches
installation et matériel (T-FEAT stock détaillé).

Le lien est défini côté StockPiece (app logistics) ; ces tests vérifient
seulement qu'il est bien répercuté en lecture seule dans le contexte des vues
de détail d'assets, sans dupliquer les tests de gestion du stock lui-même
(voir logistics/tests/test_stock_piece_web_views.py).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from logistics.models import StockPiece
from org.models import Sector, Service, Ship


class PiecesStockLieesTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire Stock", code="NS")
        self.service = Service.objects.create(ship=self.navire, name="Service Stock")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur Stock")

        self.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )

        self.equipier = User.objects.create_user(username="equipier_stock", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.navire})
        self.client.login(username="equipier_stock", password="pass")

    def test_piece_liee_a_une_installation_apparait_dans_sa_fiche(self):
        piece = StockPiece.objects.create(
            reference="REF-INS-01", designation="Bougie", quantite=2, quantite_minimale=1,
            ship=self.navire, service=self.service, sector=self.secteur, installation=self.installation,
        )
        response = self.client.get(reverse("installation-detail", args=[self.installation.id]))
        self.assertIn(piece, list(response.context["pieces_stock"]))

    def test_piece_liee_a_un_materiel_apparait_dans_sa_fiche(self):
        piece = StockPiece.objects.create(
            reference="REF-AST-01", designation="Poudre", quantite=1, quantite_minimale=1,
            ship=self.navire, service=self.service, sector=self.secteur, asset=self.asset,
        )
        response = self.client.get(reverse("asset-detail", args=[self.asset.id]))
        self.assertIn(piece, list(response.context["pieces_stock"]))

    def test_piece_sans_lien_napparait_sur_aucune_fiche(self):
        piece = StockPiece.objects.create(
            reference="REF-LIB-01", designation="Pièce libre", quantite=1, quantite_minimale=1,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        response_installation = self.client.get(reverse("installation-detail", args=[self.installation.id]))
        response_asset = self.client.get(reverse("asset-detail", args=[self.asset.id]))
        self.assertNotIn(piece, list(response_installation.context["pieces_stock"]))
        self.assertNotIn(piece, list(response_asset.context["pieces_stock"]))
