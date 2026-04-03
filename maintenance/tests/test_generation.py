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
