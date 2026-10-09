"""Périmètre vide : aucun résultat sur toute l'API, sauf pour un MASTER_ADMIN."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


class PerimetreVideApiTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Navire vide", code="NV-VID")
        service = Service.objects.create(ship=navire, name="Service vide")
        secteur = Sector.objects.create(service=service, name="Secteur vide")
        type_ = AssetType.objects.create(name="Type vide", category="Cat", sector=secteur)
        self.asset = Asset.objects.create(asset_type=type_, ship=navire, service=service, sector=secteur)
        CorrectiveTicket.objects.create(asset=self.asset, description="Panne")
        for username, role in (("chef_vide", "CHEF_SERVICE"), ("maitre_vide", "MASTER_ADMIN")):
            user = User.objects.create_user(username=username, password="pass")
            UserProfile.objects.update_or_create(user=user, defaults={"role": role})

    def _get(self, username, url):
        client = APIClient()
        client.login(username=username, password="pass")
        return client.get(url)

    def test_aucun_resultat_sans_perimetre(self):
        for url in ("/api/assets/assets/", "/api/logistics/tickets/", "/api/assets/types/"):
            r = self._get("chef_vide", url)
            self.assertEqual(r.status_code, 200, url)
            self.assertEqual(len(r.data), 0, url)

    def test_master_admin_voit_la_flotte(self):
        self.assertEqual(len(self._get("maitre_vide", "/api/assets/assets/").data), 1)
        self.assertEqual(len(self._get("maitre_vide", "/api/logistics/tickets/").data), 1)
