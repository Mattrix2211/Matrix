"""Tests de la page d'accueil — espace personnel du marin (mes maintenances
assignées + mes formations), conformément au principe fondamental n°3 de
CLAUDE.md : chaque marin ne voit que ce qui le concerne."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset, AssetType, Installation, InstallationMaintenance
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingSession


class EspacePersonnelTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire test", code="NT-EP")
        self.service = Service.objects.create(ship=self.navire, name="Service test")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur test")

        self.marin = User.objects.create_user(username="marin", password="pass")
        self.autre_marin = User.objects.create_user(username="autre", password="pass")

        self.asset_type = AssetType.objects.create(
            name="Extincteur", category="Incendie", sector=self.secteur
        )
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Contrôle annuel", every_n_days=365
        )

        self.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=self.navire, service=self.service, sector=self.secteur
        )
        self.installation_maintenance = InstallationMaintenance.objects.create(
            installation=self.installation, periodicity="3 mois", title="Vidange"
        )

        self.url = reverse("home")

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_contexte_contient_les_maintenances_assignees_au_marin_connecte(self):
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["mes_maintenances"]), [occ])

    def test_maintenance_assignee_a_un_autre_marin_est_absente_du_contexte(self):
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.autre_marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_maintenances"]), [])

    def test_maintenances_terminees_ou_annulees_sont_exclues(self):
        occ_terminee = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="DONE",
        )
        occ_terminee.assignees.add(self.marin)
        occ_annulee = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="CANCELLED",
        )
        occ_annulee.assignees.add(self.marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_maintenances"]), [])

    def test_maintenance_sur_installation_fixe_affiche_le_bon_titre(self):
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=self.installation_maintenance,
            scheduled_for=timezone.localdate(),
            status="ASSIGNED",
        )
        occ.assignees.add(self.marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        occurrence_affichee = response.context["mes_maintenances"][0]
        self.assertIn("Groupe électrogène", occurrence_affichee.titre_affiche)
        self.assertIn("Vidange", occurrence_affichee.titre_affiche)

    def test_maintenance_en_retard_est_triee_avant_une_maintenance_planifiee(self):
        occ_en_retard = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset,
            scheduled_for=timezone.localdate() - timedelta(days=5), status="OVERDUE",
        )
        occ_en_retard.assignees.add(self.marin)
        occ_planifiee = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset,
            scheduled_for=timezone.localdate() + timedelta(days=5), status="ASSIGNED",
        )
        occ_planifiee.assignees.add(self.marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(
            list(response.context["mes_maintenances"]), [occ_en_retard, occ_planifiee]
        )

    def test_contexte_contient_les_formations_du_marin_connecte(self):
        cours = TrainingCourse.objects.create(sector=self.secteur, title="Sécurité incendie")
        session = TrainingSession.objects.create(
            course=cours, scheduled_at=timezone.now() + timedelta(days=10), status="PLANNED",
        )
        session.attendees.add(self.marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_formations"]), [session])

    def test_formation_d_un_autre_marin_est_absente_du_contexte(self):
        cours = TrainingCourse.objects.create(sector=self.secteur, title="Sécurité incendie")
        session = TrainingSession.objects.create(
            course=cours, scheduled_at=timezone.now() + timedelta(days=10), status="PLANNED",
        )
        session.attendees.add(self.autre_marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_formations"]), [])

    def test_formation_effectuee_est_exclue(self):
        cours = TrainingCourse.objects.create(sector=self.secteur, title="Sécurité incendie")
        session = TrainingSession.objects.create(
            course=cours, scheduled_at=timezone.now() - timedelta(days=10), status="DONE",
        )
        session.attendees.add(self.marin)

        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_formations"]), [])

    def test_espace_personnel_vide_affiche_un_message_clair(self):
        self.client.login(username="marin", password="pass")
        response = self.client.get(self.url)

        self.assertContains(response, "Aucune maintenance ne vous est actuellement assignée.")
        self.assertContains(response, "Aucune formation ne vous est actuellement programmée.")
