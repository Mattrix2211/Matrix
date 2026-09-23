from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation, InstallationMaintenance, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class ScanQRViewTests(TestCase):
    """Vue /scan/<uuid:pk>/ : point d'entrée du QR code apposé sur un
    équipement (matériel mobile ou installation fixe). Couvre le workflow
    « Scan QR → occurrence du jour → checklist » (CLAUDE.md) ainsi que le
    contrôle de périmètre."""

    def setUp(self):
        # Navire A (périmètre de l'utilisateur de test)
        self.ship_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )
        self.installation_a = Installation.objects.create(
            designation="Pompe A", ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )

        # Navire B (hors périmètre)
        self.ship_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )
        self.installation_b = Installation.objects.create(
            designation="Pompe B", ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        self.marin = User.objects.create_user(username="marin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )
        self.client.login(username="marin_a", password="pass")

    def _creer_occurrence_asset(self, asset, assignee, scheduled_for=None):
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Plan", every_n_days=30)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=scheduled_for or timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(assignee)
        return occ

    def _creer_occurrence_installation(self, installation, assignee, scheduled_for=None):
        maintenance = InstallationMaintenance.objects.create(
            installation=installation, periodicity="Mensuel", title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
        )
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=scheduled_for or timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(assignee)
        return occ

    def test_scan_asset_avec_occurrence_du_jour_redirige_vers_checklist(self):
        occ = self._creer_occurrence_asset(self.asset_a, self.marin)
        response = self.client.get(f"/scan/{self.asset_a.id}/")
        self.assertRedirects(response, f"/maintenance/occurrences/{occ.id}/execute/")

    def test_scan_asset_sans_occurrence_affiche_fiche_equipement(self):
        response = self.client.get(f"/scan/{self.asset_a.id}/")
        self.assertRedirects(response, f"/assets/{self.asset_a.id}/")

    def test_scan_installation_avec_occurrence_du_jour_redirige_vers_checklist(self):
        occ = self._creer_occurrence_installation(self.installation_a, self.marin)
        response = self.client.get(f"/scan/{self.installation_a.id}/")
        self.assertRedirects(response, f"/maintenance/occurrences/{occ.id}/execute/")

    def test_scan_installation_sans_occurrence_affiche_fiche_equipement(self):
        response = self.client.get(f"/scan/{self.installation_a.id}/")
        self.assertRedirects(response, f"/installations/{self.installation_a.id}/")

    def test_scan_occurrence_terminee_ne_redirige_pas_vers_checklist(self):
        # Une occurrence déjà DONE aujourd'hui ne doit plus être proposée : le
        # marin retombe sur la fiche de l'équipement.
        self._creer_occurrence_asset(self.asset_a, self.marin).__class__.objects.filter(
            asset=self.asset_a
        ).update(status="DONE")
        response = self.client.get(f"/scan/{self.asset_a.id}/")
        self.assertRedirects(response, f"/assets/{self.asset_a.id}/")

    def test_scan_occurrence_assignee_a_un_autre_marin_ne_redirige_pas(self):
        autre = User.objects.create_user(username="autre_marin", password="pass")
        self._creer_occurrence_asset(self.asset_a, autre)
        response = self.client.get(f"/scan/{self.asset_a.id}/")
        self.assertRedirects(response, f"/assets/{self.asset_a.id}/")

    def test_scan_asset_hors_perimetre_redirige_avec_message_francais(self):
        # Régression : un 404 technique brut (en anglais) ne doit jamais être
        # renvoyé — l'équipement existe mais hors périmètre, donc redirection
        # vers le tableau de bord avec un message d'erreur clair en français.
        response = self.client.get(f"/scan/{self.asset_b.id}/", follow=True)
        self.assertRedirects(response, "/")
        messages_affiches = [str(m) for m in response.context["messages"]]
        self.assertEqual(
            messages_affiches,
            ["Cet équipement n'appartient pas à votre navire, vous ne pouvez pas y accéder."],
        )
        # Aucune information sur l'équipement d'un autre navire ne doit fuiter
        # (ni son nom, ni le nom de son navire).
        contenu = response.content.decode()
        self.assertNotIn("Pompe B", contenu)
        self.assertNotIn("Navire B", contenu)

    def test_scan_installation_hors_perimetre_redirige_avec_message_francais(self):
        response = self.client.get(f"/scan/{self.installation_b.id}/", follow=True)
        self.assertRedirects(response, "/")
        messages_affiches = [str(m) for m in response.context["messages"]]
        self.assertEqual(
            messages_affiches,
            ["Cet équipement n'appartient pas à votre navire, vous ne pouvez pas y accéder."],
        )

    def test_scan_identifiant_inexistant_redirige_avec_message_francais(self):
        import uuid
        response = self.client.get(f"/scan/{uuid.uuid4()}/", follow=True)
        self.assertRedirects(response, "/")
        messages_affiches = [str(m) for m in response.context["messages"]]
        self.assertEqual(messages_affiches, ["QR code invalide ou équipement introuvable."])

    def test_scan_necessite_authentification(self):
        self.client.logout()
        response = self.client.get(f"/scan/{self.asset_a.id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
