"""Le commandant adjoint d'un service (routage des visas) ne se modifie pas par l'API."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import CommandantAdjoint, Service, Ship


class CommandantAdjointApiTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="A")
        self.service = Service.objects.create(ship=self.navire, name="Service A")
        self.chef = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "ship": self.navire}
        )
        self.client = APIClient()
        self.client.login(username="chef_a", password="pass")

    def test_patch_ne_change_pas_le_commandant_adjoint(self):
        self.client.patch(
            f"/api/org/services/{self.service.pk}/",
            {"commandant_adjoint": CommandantAdjoint.COMANAV},
            format="json",
        )
        self.service.refresh_from_db()
        self.assertEqual(self.service.commandant_adjoint, "")
