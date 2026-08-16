from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType, Installation


class InstallationHierarchieParentTests(TestCase):
    """T2 : rattachement parent/enfant (self-FK) sur Installation."""

    def setUp(self):
        self.ship = Ship.objects.create(name="S1")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.user = User.objects.create_user(username="u1", password="pass")

    def test_creation_avec_parent(self):
        groupe = Installation.objects.create(
            designation="Groupe propulsion", ship=self.ship, service=self.service, sector=self.sector,
        )
        moteur = Installation.objects.create(
            designation="Moteur bâbord", ship=self.ship, service=self.service, sector=self.sector, parent=groupe,
        )
        self.assertEqual(moteur.parent, groupe)
        self.assertIn(moteur, groupe.sous_ensembles.all())

    def test_parent_optionnel(self):
        installation = Installation.objects.create(
            designation="Pompe A", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.assertIsNone(installation.parent)

    def test_suppression_du_parent_ne_supprime_pas_lenfant(self):
        groupe = Installation.objects.create(
            designation="Groupe propulsion", ship=self.ship, service=self.service, sector=self.sector,
        )
        moteur = Installation.objects.create(
            designation="Moteur bâbord", ship=self.ship, service=self.service, sector=self.sector, parent=groupe,
        )
        # Retrait de la fiche parente via l'action existante du bordereau installations
        # (SET_NULL doit préserver l'enfant, sans le retirer lui aussi).
        self.client.login(username="u1", password="pass")
        self.client.post("/installations/", {"action": "delete_installation", "pk": groupe.pk})
        self.assertFalse(Installation.objects.filter(pk=groupe.pk).exists())
        moteur.refresh_from_db()
        self.assertIsNone(moteur.parent)

    def test_cycle_direct_refuse(self):
        installation = Installation.objects.create(
            designation="Pompe A", ship=self.ship, service=self.service, sector=self.sector,
        )
        installation.parent = installation
        with self.assertRaises(ValidationError):
            installation.clean()

    def test_cycle_indirect_refuse(self):
        a = Installation.objects.create(designation="A", ship=self.ship, service=self.service, sector=self.sector)
        b = Installation.objects.create(designation="B", ship=self.ship, service=self.service, sector=self.sector, parent=a)
        a.parent = b
        with self.assertRaises(ValidationError):
            a.clean()


class AssetHierarchieParentTests(TestCase):
    """T2 : rattachement parent/enfant (self-FK) sur Asset (matériel mobile)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="S1")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.asset_type = AssetType.objects.create(name="Multimètre", category="Mesure", sector=self.sector)
        self.user = User.objects.create_user(username="u2", password="pass")

    def test_creation_avec_parent(self):
        caisse = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        outil = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector, parent=caisse,
        )
        self.assertEqual(outil.parent, caisse)
        self.assertIn(outil, caisse.sous_ensembles.all())

    def test_parent_optionnel(self):
        asset = Asset.objects.create(asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector)
        self.assertIsNone(asset.parent)

    def test_suppression_du_parent_ne_supprime_pas_lenfant(self):
        caisse = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        outil = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector, parent=caisse,
        )
        # Retrait de la fiche parente via l'action existante du bordereau matériel
        # (SET_NULL doit préserver l'enfant, sans le retirer lui aussi).
        self.client.login(username="u2", password="pass")
        self.client.post("/assets/", {"action": "delete_asset", "pk": caisse.pk})
        self.assertFalse(Asset.objects.filter(pk=caisse.pk).exists())
        outil.refresh_from_db()
        self.assertIsNone(outil.parent)

    def test_cycle_direct_refuse(self):
        asset = Asset.objects.create(asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector)
        asset.parent = asset
        with self.assertRaises(ValidationError):
            asset.clean()
