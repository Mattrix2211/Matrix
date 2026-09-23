from django.test import TestCase
from django.contrib.auth.models import User
from org.models import Ship, Service, Sector, Section
from assets.models import AssetType, Asset
from maintenance.models import MaintenancePlan, MaintenanceOccurrence
from maintenance.tasks import generate_occurrences
from datetime import date

class OccurrenceGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Fire", sector=sector)
        self.asset = Asset.objects.create(asset_type=self.asset_type, ship=ship, service=service, sector=sector, status="OK")

    def test_generate_occurrences(self):
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Visuel", every_n_days=30)
        generate_occurrences(days_ahead=60)
        self.assertTrue(MaintenanceOccurrence.objects.filter(plan=plan, asset=self.asset).exists())

    def test_generate_occurrences_scope_asset_type(self):
        """Un plan à l'échelle d'un type d'actif doit générer une occurrence
        pour chaque actif de ce type (et pas seulement pour un actif précis,
        cas déjà couvert par test_generate_occurrences ci-dessus)."""
        autre_asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.asset.ship, service=self.asset.service,
            sector=self.asset.sector, status="OK",
        )
        plan = MaintenancePlan.objects.create(
            scope="ASSET_TYPE", asset_type=self.asset_type, name="Contrôle visuel", every_n_days=30
        )

        generate_occurrences(days_ahead=60)

        self.assertTrue(MaintenanceOccurrence.objects.filter(plan=plan, asset=self.asset).exists())
        self.assertTrue(MaintenanceOccurrence.objects.filter(plan=plan, asset=autre_asset).exists())

    def test_generate_occurrences_scope_asset_type_sans_actif_correspondant(self):
        """Un plan portant sur un type d'actif sans aucun actif rattaché ne doit
        générer aucune occurrence, et ne doit pas lever d'erreur."""
        type_vide = AssetType.objects.create(name="Multimètre", category="Mesure", sector=self.asset.sector)
        plan = MaintenancePlan.objects.create(
            scope="ASSET_TYPE", asset_type=type_vide, name="Étalonnage", every_n_days=30
        )

        generate_occurrences(days_ahead=60)

        self.assertFalse(MaintenanceOccurrence.objects.filter(plan=plan).exists())
