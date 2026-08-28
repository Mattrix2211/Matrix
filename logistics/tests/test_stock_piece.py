from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from org.models import Ship, Service, Sector, Section
from assets.models import Asset, AssetType, Installation
from logistics.models import StockPiece

class StockPieceTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Ship A", code="A")
        self.service = Service.objects.create(ship=self.ship, name="Tech")
        self.sector = Sector.objects.create(service=self.service, name="Elec")
        self.section = Section.objects.create(sector=self.sector, name="Atelier")
        self.autre_sector = Sector.objects.create(service=self.service, name="Autre secteur")

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

    def test_nno_optionnel_par_defaut_vide(self):
        # Rétrocompatibilité : une pièce créée sans NNO (comme toutes celles
        # existant avant l'ajout de ce champ) doit avoir une chaîne vide, pas None.
        piece = StockPiece.objects.create(
            reference="REF-030", designation="Sans NNO",
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.assertEqual(piece.nno, "")

    def test_nno_renseigne(self):
        piece = StockPiece.objects.create(
            reference="REF-031", designation="Avec NNO", nno="5310-14-123-4567",
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.assertEqual(piece.nno, "5310-14-123-4567")

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

    def test_seuil_critique_par_defaut_zero(self):
        # Sans seuil critique renseigné (rétrocompatibilité des pièces déjà
        # existantes) : seul un stock à 0 est considéré critique, comme avant
        # l'ajout de ce champ.
        piece = StockPiece.objects.create(
            reference="REF-010", designation="Fusible", quantite=1, quantite_minimale=5,
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.assertEqual(piece.seuil_critique_effectif, 0)
        self.assertFalse(piece.est_critique)
        self.assertTrue(piece.est_bas)

        piece.quantite = 0
        self.assertTrue(piece.est_critique)
        self.assertFalse(piece.est_bas)

    def test_seuil_critique_renseigne(self):
        piece = StockPiece.objects.create(
            reference="REF-011", designation="Courroie", quantite=2, quantite_minimale=5,
            quantite_critique=3, ship=self.ship, service=self.service, sector=self.sector,
        )
        self.assertTrue(piece.est_critique)

    def test_lien_installation_meme_secteur_valide(self):
        installation = Installation.objects.create(
            designation="Pompe A", ship=self.ship, service=self.service, sector=self.sector,
        )
        piece = StockPiece(
            reference="REF-012", designation="Joint", ship=self.ship, service=self.service,
            sector=self.sector, installation=installation,
        )
        piece.full_clean()  # ne doit pas lever d'exception
        piece.save()
        self.assertEqual(piece.equipement_lie, installation)

    def test_lien_installation_secteur_different_refuse(self):
        installation = Installation.objects.create(
            designation="Pompe B", ship=self.ship, service=self.service, sector=self.autre_sector,
        )
        piece = StockPiece(
            reference="REF-013", designation="Joint", ship=self.ship, service=self.service,
            sector=self.sector, installation=installation,
        )
        with self.assertRaises(ValidationError):
            piece.full_clean()

    def test_lien_installation_et_asset_simultanes_refuse(self):
        installation = Installation.objects.create(
            designation="Pompe C", ship=self.ship, service=self.service, sector=self.sector,
        )
        asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        asset = Asset.objects.create(asset_type=asset_type, ship=self.ship, service=self.service, sector=self.sector)
        piece = StockPiece(
            reference="REF-014", designation="Joint", ship=self.ship, service=self.service,
            sector=self.sector, installation=installation, asset=asset,
        )
        with self.assertRaises(ValidationError):
            piece.full_clean()
