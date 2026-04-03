from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from org.models import Ship, Service, Sector
from assets.models import AssetType


class AssetRBACTests(TestCase):
    def test_equipier_cannot_create_asset_but_chef_section_can(self):
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        at = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)

        equipier = User.objects.create_user(username="e1", password="pass")
        chef = User.objects.create_user(username="c1", password="pass")

        # Attach roles via profile
        from accounts.models import UserProfile
        UserProfile.objects.create(user=equipier, role="EQUIPIER")
        UserProfile.objects.create(user=chef, role="CHEF_SECTION")

        client = APIClient()
        client.login(username="e1", password="pass")
        r1 = client.post(
            "/api/assets/assets/",
            {
                "ship": ship.id,
                "service": service.id,
                "sector": sector.id,
                "asset_type": at.id,
                "serial_number": "SN1",
                "internal_id": "INT1",
            },
            format="json",
        )
        self.assertIn(r1.status_code, (403, 401))

        client.logout()
        client.login(username="c1", password="pass")
        r2 = client.post(
            "/api/assets/assets/",
            {
                "ship": ship.id,
                "service": service.id,
                "sector": sector.id,
                "asset_type": at.id,
                "serial_number": "SN2",
                "internal_id": "INT2",
            },
            format="json",
        )
        self.assertIn(r2.status_code, (201, 200))
