from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from org.models import Ship, Service, Sector
from assets.models import AssetType, Installation, InstallationEvent, InstallationMaintenance


class AssetRBACTests(TestCase):
    def test_equipier_cannot_create_asset_but_chef_section_can(self):
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        at = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)

        equipier = User.objects.create_user(username="e1", password="pass")
        chef = User.objects.create_user(username="c1", password="pass")

        # Un profil est déjà auto-créé par le signal post_save sur User (rôle EQUIPIER
        # par défaut) : on met à jour le rôle plutôt que de recréer un profil.
        from accounts.models import UserProfile
        UserProfile.objects.update_or_create(user=equipier, defaults={"role": "EQUIPIER"})
        UserProfile.objects.update_or_create(user=chef, defaults={"role": "CHEF_SECTION"})

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


class InstallationMaintenanceRBACTests(TestCase):
    def test_equipier_cannot_write_maintenance_but_chef_service_can(self):
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        installation = Installation.objects.create(designation="Pompe A", ship=ship, service=service, sector=sector)

        equipier = User.objects.create_user(username="e2", password="pass")
        chef_service = User.objects.create_user(username="cs1", password="pass")

        # Un profil est déjà auto-créé par le signal post_save sur User (rôle EQUIPIER
        # par défaut) : on met à jour le rôle plutôt que de recréer un profil.
        from accounts.models import UserProfile
        UserProfile.objects.update_or_create(user=equipier, defaults={"role": "EQUIPIER"})
        UserProfile.objects.update_or_create(user=chef_service, defaults={"role": "CHEF_SERVICE"})

        url = f"/installations/{installation.id}/"

        # Un équipier ne peut pas créer une tâche d'entretien
        self.client.login(username="e2", password="pass")
        r1 = self.client.post(url, {"action": "add_maintenance", "title": "Graissage", "tab": "entretien"})
        self.assertEqual(r1.status_code, 403)
        self.assertEqual(InstallationMaintenance.objects.filter(installation=installation).count(), 0)

        # Un chef de service peut créer une tâche d'entretien
        self.client.logout()
        self.client.login(username="cs1", password="pass")
        r2 = self.client.post(url, {"action": "add_maintenance", "title": "Graissage", "tab": "entretien"})
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(InstallationMaintenance.objects.filter(installation=installation).count(), 1)


class InstallationMaintenanceModeDeclenchementTests(TestCase):
    """T5 : modification du mode de déclenchement + traçabilité InstallationEvent."""

    def setUp(self):
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        self.installation = Installation.objects.create(designation="Pompe A", ship=ship, service=service, sector=sector)
        self.maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="Mensuel",
            title="Graissage",
            mode_declenchement="CALENDRIER",
        )

        from accounts.models import UserProfile
        self.equipier = User.objects.create_user(username="e3", password="pass")
        self.chef_service = User.objects.create_user(username="cs2", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})
        UserProfile.objects.update_or_create(user=self.chef_service, defaults={"role": "CHEF_SERVICE"})
        self.url = f"/installations/{self.installation.id}/"

    def test_equipier_cannot_edit_maintenance(self):
        self.client.login(username="e3", password="pass")
        r = self.client.post(self.url, {
            "action": "edit_maintenance",
            "maintenance_id": self.maintenance.id,
            "title": "Graissage",
            "mode_declenchement": "COMPTEUR",
            "tab": "entretien",
        })
        self.assertEqual(r.status_code, 403)
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.mode_declenchement, "CALENDRIER")
        self.assertEqual(InstallationEvent.objects.filter(installation=self.installation).count(), 0)

    def test_changement_mode_declenchement_est_trace(self):
        self.client.login(username="cs2", password="pass")
        r = self.client.post(self.url, {
            "action": "edit_maintenance",
            "maintenance_id": self.maintenance.id,
            "title": "Graissage",
            "mode_declenchement": "COMPTEUR",
            "seuil_heures": "500",
            "tab": "entretien",
        })
        self.assertEqual(r.status_code, 302)
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.mode_declenchement, "COMPTEUR")
        self.assertEqual(self.maintenance.seuil_heures, 500)

        events = InstallationEvent.objects.filter(installation=self.installation)
        self.assertEqual(events.count(), 1)
        event = events.first()
        self.assertEqual(event.label, "Changement mode de suivi maintenance")
        self.assertIn("Graissage", event.notes)
        self.assertIn("Calendaire", event.notes)
        self.assertIn("Compteur (heures de marche)", event.notes)
        self.assertIn("cs2", event.notes)

    def test_edition_sans_changement_de_mode_ne_cree_pas_devenement(self):
        self.client.login(username="cs2", password="pass")
        r = self.client.post(self.url, {
            "action": "edit_maintenance",
            "maintenance_id": self.maintenance.id,
            "title": "Graissage renforcé",
            "mode_declenchement": "CALENDRIER",
            "tab": "entretien",
        })
        self.assertEqual(r.status_code, 302)
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.title, "Graissage renforcé")
        self.assertEqual(InstallationEvent.objects.filter(installation=self.installation).count(), 0)
