"""Fuite de périmètre (IDOR) sur StartVisualCheckView (interface web).

Avant correction, la vue récupérait le matériel par un simple .get(pk=pk),
sans filtrer par périmètre hiérarchique : un chef de secteur connaissant
l'identifiant d'un matériel d'un autre navire pouvait y déclencher un
contrôle visuel, alors même qu'aucun lien n'y menait depuis les vues déjà
scopées (liste, fiche détail). Cf. tâche [SEC] IDOR cross-navire sur 4 vues
web.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence
from org.models import Sector, Service, Ship


class ScopeLeakStartVisualCheckViewTests(TestCase):
    def setUp(self):
        # Navire A (celui de l'utilisateur connecté)
        self.ship_a = Ship.objects.create(name="Navire A visuel", code="NA-VIS")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A visuel")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A visuel")

        # Navire B (hors périmètre de l'utilisateur connecté)
        self.ship_b = Ship.objects.create(name="Navire B visuel", code="NB-VIS")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B visuel")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B visuel")
        self.asset_type_b = AssetType.objects.create(name="TypeB visuel", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        self.chef_a = User.objects.create_user(username="chef_visuel_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SECTION", "sector": self.sector_a}
        )
        self.client.login(username="chef_visuel_a", password="pass")

    def test_controle_visuel_sur_materiel_dun_autre_navire_refuse(self):
        url = reverse("asset-start-visual", args=[self.asset_b.id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(MaintenanceOccurrence.objects.filter(asset=self.asset_b).exists())
