from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from org.models import Ship, Service, Sector
from assets.models import AssetType, Asset
from logistics.models import CorrectiveTicket


class LogisticsRBACTests(TestCase):
    def test_only_chef_section_can_transition_ticket(self):
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        at = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector)

        # Create ticket
        ticket = CorrectiveTicket.objects.create(asset=asset, description="Pb")

        # Users
        equipier = User.objects.create_user(username="equ", password="pass")
        chef = User.objects.create_user(username="chef", password="pass")

        from accounts.models import UserProfile
        UserProfile.objects.create(user=equipier, role="EQUIPIER")
        UserProfile.objects.create(user=chef, role="CHEF_SECTION")

        client = APIClient()
        # Equipier cannot transition
        client.login(username="equ", password="pass")
        url = f"/api/logistics/tickets/{ticket.pk}/transition/"
        resp = client.post(url, {"status": "DIAGNOSED"}, format="json")
        self.assertIn(resp.status_code, (403, 404))

        # Chef can transition
        client.logout()
        client.login(username="chef", password="pass")
        resp3 = client.post(url, {"status": "DIAGNOSED"}, format="json")
        self.assertIn(resp3.status_code, (200, 202))
