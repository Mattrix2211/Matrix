from django.test import TestCase
from django.contrib.auth.models import User
from org.models import Ship, Service, Sector
from assets.models import AssetType, Asset
from logistics.models import CorrectiveTicket, TicketStatusLog

class TicketTransitionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        at = AssetType.objects.create(name="Extincteur", category="Fire", sector=sector)
        self.asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector, status="OK")

    def test_transition_logs(self):
        t = CorrectiveTicket.objects.create(asset=self.asset, description="Panne")
        old = t.status
        t.status = "DIAGNOSED"
        t.save()
        TicketStatusLog.objects.create(ticket=t, old_status=old, new_status=t.status, user=self.user)
        self.assertEqual(TicketStatusLog.objects.filter(ticket=t).count(), 1)
