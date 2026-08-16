from django.db import IntegrityError, transaction
from django.test import TestCase
from org.models import Ship, Service, Sector, Section
from logistics.models import StockPiece

class StockPieceTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Ship A", code="A")
        self.service = Service.objects.create(ship=self.ship, name="Tech")
        self.sector = Sector.objects.create(service=self.service, name="Elec")
        self.section = Section.objects.create(sector=self.sector, name="Atelier")

    def test_creation_piece_stock(self):
        piece = StockPiece.objects.create(
            reference="REF-001",
            designation="Joint torique",
            quantite=10,
            quantite_minimale=2,
            emplacement="Magasin bâbord",
            ship=self.ship,
            service=self.service,
            sector=self.sector,
            section=self.section,
        )
        self.assertEqual(str(piece), "REF-001 - Joint torique")
        self.assertEqual(piece.quantite, 10)

    def test_section_optionnelle(self):
        # La section n'est pas obligatoire, contrairement à ship/service/sector.
        piece = StockPiece.objects.create(
            reference="REF-002",
            designation="Roulement",
            ship=self.ship,
            service=self.service,
            sector=self.sector,
        )
        self.assertIsNone(piece.section)

    def test_sector_obligatoire(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StockPiece.objects.create(
                    reference="REF-003",
                    designation="Sans secteur",
                    ship=self.ship,
                    service=self.service,
                    sector=None,
                )
