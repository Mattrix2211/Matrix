"""Export tableur (CSV/XLSX) de la liste Stock de pièces.

Vérifie que l'export respecte le périmètre de l'utilisateur (ScopedQuerySetMixin,
déjà en place sur StockPieceListView) et produit un fichier valide.
"""
import io

import openpyxl
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from logistics.models import StockPiece
from org.models import Sector, Service, Ship


class ExportStockPieceTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire export stock")
        self.service = Service.objects.create(ship=self.navire, name="Service export stock")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur export stock")
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre secteur stock")

        self.equipier = User.objects.create_user(username="equipier_stock", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur)
        self.equipier.refresh_from_db()

        self.piece_perimetre = StockPiece.objects.create(
            reference="REF-100", designation="Joint torique", quantite=1, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.piece_hors_perimetre = StockPiece.objects.create(
            reference="REF-200", designation="Roulement", quantite=10, quantite_minimale=2,
            ship=self.navire, service=self.service, sector=self.autre_secteur,
        )

        self.url = reverse("stock-piece-list")

    def test_export_csv_respecte_le_perimetre(self):
        self.client.login(username="equipier_stock", password="pass")
        response = self.client.get(self.url, {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        contenu = response.content.decode("utf-8-sig")
        self.assertIn("REF-100", contenu)
        self.assertNotIn("REF-200", contenu)

    def test_export_xlsx_format_valide_et_scope(self):
        self.client.login(username="equipier_stock", password="pass")
        response = self.client.get(self.url, {"export": "xlsx"})
        classeur = openpyxl.load_workbook(io.BytesIO(response.content))
        feuille = classeur.active
        valeurs = [cell.value for row in feuille.iter_rows() for cell in row]
        self.assertIn("REF-100", valeurs)
        self.assertNotIn("REF-200", valeurs)
