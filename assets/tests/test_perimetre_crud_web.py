from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType, Installation


class PerimetreCrudAssetWebTests(TestCase):
    """Vérifie que les actions CRUD/groupées de AssetListView.post et
    InstallationListView.post revalident bien le périmètre posté (ship/service/
    sector/section) et l'objet ciblé (pk), pas seulement le rôle de l'appelant."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(name="Srv A", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec A", service=self.service)

        self.autre_ship = Ship.objects.create(name="Navire B", code="NAV-B")
        self.autre_service = Service.objects.create(name="Srv B", ship=self.autre_ship)
        self.autre_sector = Sector.objects.create(name="Sec B", service=self.autre_service)

        self.asset_type = AssetType.objects.create(name="Extincteur", category="EPI", sector=self.sector)

        self.chef = User.objects.create_user(username="chef_perim", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship, "service": self.service}
        )

        self.equipier = User.objects.create_user(username="equipier_perim", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship}
        )

        self.materiel = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            serial_number="SN-A", internal_id="A-1",
        )
        self.materiel_hors_perimetre = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Multimètre", category="Outillage", sector=self.autre_sector),
            ship=self.autre_ship, service=self.autre_service, sector=self.autre_sector,
            serial_number="SN-B", internal_id="B-1",
        )

        self.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.installation_hors_perimetre = Installation.objects.create(
            designation="Pompe hors périmètre", ship=self.autre_ship, service=self.autre_service, sector=self.autre_sector,
        )

    def test_equipier_rejete_sur_bulk_delete_assets(self):
        self.client.login(username="equipier_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "bulk_delete_assets",
            "selected_ids": [str(self.materiel.id)],
        })
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Asset.objects.filter(pk=self.materiel.id).exists())

    def test_equipier_rejete_sur_bulk_update_ship(self):
        self.client.login(username="equipier_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "bulk_update_ship",
            "selected_ids": [str(self.materiel.id)],
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 403)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.ship_id, self.ship.id)

    def test_chef_service_ne_peut_pas_deplacer_un_asset_vers_un_navire_hors_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(self.materiel.id),
            "internal_id": self.materiel.internal_id,
            "serial_number": self.materiel.serial_number,
            "designation": "Extincteur modifié",
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.ship_id, self.ship.id)
        self.assertNotEqual(self.materiel.designation, "Extincteur modifié")

    def test_chef_service_ne_peut_pas_editer_un_asset_hors_de_son_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(self.materiel_hors_perimetre.id),
            "internal_id": self.materiel_hors_perimetre.internal_id,
            "serial_number": self.materiel_hors_perimetre.serial_number,
            "designation": "Modifié frauduleusement",
        })
        self.assertEqual(r.status_code, 302)
        self.materiel_hors_perimetre.refresh_from_db()
        self.assertNotEqual(self.materiel_hors_perimetre.designation, "Modifié frauduleusement")

    def test_chef_service_ne_peut_pas_supprimer_un_asset_hors_de_son_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        self.client.post("/assets/", {
            "action": "delete_asset",
            "pk": str(self.materiel_hors_perimetre.id),
        })
        self.assertTrue(Asset.objects.filter(pk=self.materiel_hors_perimetre.id).exists())

    def test_equipier_rejete_sur_bulk_delete_installations(self):
        self.client.login(username="equipier_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "bulk_delete_installations",
            "selected_ids": [str(self.installation.id)],
        })
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Installation.objects.filter(pk=self.installation.id).exists())

    def test_chef_service_ne_peut_pas_deplacer_une_installation_vers_un_navire_hors_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "edit_installation",
            "pk": str(self.installation.id),
            "designation": "Groupe modifié",
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.ship_id, self.ship.id)
        self.assertNotEqual(self.installation.designation, "Groupe modifié")

    def test_chef_service_ne_peut_pas_supprimer_une_installation_hors_de_son_perimetre_via_le_detail(self):
        self.client.login(username="chef_perim", password="pass")
        self.client.post(f"/installations/{self.installation_hors_perimetre.id}/", {
            "action": "delete_installation",
            "pk": str(self.installation_hors_perimetre.id),
        })
        self.assertTrue(Installation.objects.filter(pk=self.installation_hors_perimetre.id).exists())
