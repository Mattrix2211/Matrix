"""Tests du dashboard transverse par spécialité
(dashboard/web_views.py::DashboardSpecialiteView / Choix) — tâche Notion
« Dashboards transverses par spécialité et par classe de navire »."""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import ResponsableSpecialite, SpecialityChoice, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingRecord


class DashboardSpecialiteAccesTests(TestCase):
    def setUp(self):
        self.specialite = SpecialityChoice.objects.create(name="Détection")
        self.navire = Ship.objects.create(name="Navire DS", code="NDS")

    def _creer_utilisateur(self, username, role, specialite=""):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "specialite": specialite, "ship": self.navire}
        )
        return user

    def test_marin_non_responsable_na_pas_acces(self):
        self._creer_utilisateur("marin1", "EQUIPIER")
        self.client.login(username="marin1", password="pass")
        response = self.client.get(reverse("dashboard-specialite", args=[self.specialite.id]))
        self.assertEqual(response.status_code, 403)

    def test_responsable_designe_a_acces(self):
        responsable = self._creer_utilisateur("responsable1", "EQUIPIER")
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=responsable)
        self.client.login(username="responsable1", password="pass")
        response = self.client.get(reverse("dashboard-specialite", args=[self.specialite.id]))
        self.assertEqual(response.status_code, 200)

    def test_master_admin_a_acces_sans_etre_designe(self):
        admin = self._creer_utilisateur("master1", "MASTER_ADMIN")
        self.client.login(username="master1", password="pass")
        response = self.client.get(reverse("dashboard-specialite", args=[self.specialite.id]))
        self.assertEqual(response.status_code, 200)

    def test_choix_redirige_directement_si_une_seule_specialite_accessible(self):
        responsable = self._creer_utilisateur("responsable2", "EQUIPIER")
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=responsable)
        self.client.login(username="responsable2", password="pass")
        response = self.client.get(reverse("dashboard-specialite-choix"))
        self.assertRedirects(response, reverse("dashboard-specialite", args=[self.specialite.id]))

    def test_choix_refuse_si_aucune_specialite_accessible(self):
        self._creer_utilisateur("marin2", "EQUIPIER")
        self.client.login(username="marin2", password="pass")
        response = self.client.get(reverse("dashboard-specialite-choix"))
        self.assertEqual(response.status_code, 403)

    def test_lien_de_navigation_present_pour_un_responsable(self):
        responsable = self._creer_utilisateur("responsable3", "EQUIPIER")
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=responsable)
        self.client.login(username="responsable3", password="pass")
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("dashboard-specialite-choix"))

    def test_lien_de_navigation_absent_pour_un_marin_non_responsable(self):
        self._creer_utilisateur("marin3", "EQUIPIER")
        self.client.login(username="marin3", password="pass")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("dashboard-specialite-choix"))


class DashboardSpecialiteAgregationTests(TestCase):
    """Vérifie que les indicateurs transverses (répartition par unité,
    qualifications) sont bien agrégés sur TOUTE LA FLOTTE, tous navires
    confondus, pour la spécialité consultée."""

    def setUp(self):
        self.specialite = SpecialityChoice.objects.create(name="Mécanique")
        self.navire_a = Ship.objects.create(name="Navire A", code="NA-DS")
        self.navire_b = Ship.objects.create(name="Navire B", code="NB-DS")

        self.marin_a = User.objects.create_user(username="marin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_a, defaults={"role": "EQUIPIER", "specialite": "Mécanique", "ship": self.navire_a}
        )
        self.marin_b = User.objects.create_user(username="marin_b", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_b, defaults={"role": "EQUIPIER", "specialite": "Mécanique", "ship": self.navire_b}
        )
        # Autre spécialité : ne doit jamais apparaître dans les compteurs.
        self.marin_autre = User.objects.create_user(username="marin_autre", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_autre, defaults={"role": "EQUIPIER", "specialite": "Électricité", "ship": self.navire_a}
        )

        self.responsable = User.objects.create_user(username="resp", password="pass")
        UserProfile.objects.update_or_create(user=self.responsable, defaults={"role": "EQUIPIER"})
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=self.responsable)

        self.client.login(username="resp", password="pass")
        self.url = reverse("dashboard-specialite", args=[self.specialite.id])

    def test_total_marins_et_repartition_par_unite(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_marins"], 2)
        self.assertEqual(response.context["nombre_navires"], 2)

    def test_qualifications_expirees_comptees(self):
        cours = TrainingCourse.objects.create(title="Sécurité", validity_days=365)
        TrainingRecord.objects.create(
            user=self.marin_a, course=cours, completed_at=date(2020, 1, 1), expires_at=date(2020, 6, 1),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["qualifications_par_statut"]["Expirée"], 1)


class DashboardSpecialiteVueTechniqueTests(TestCase):
    """Vérifie le point 2 du cadrage du 12/09/2026 : le dashboard spécialité
    combine la vue RH ET une vue technique (maintenance/tickets correctifs
    assignés aux marins de cette spécialité, toute la flotte confondue)."""

    def setUp(self):
        self.specialite = SpecialityChoice.objects.create(name="Électricité")
        self.navire = Ship.objects.create(name="Navire VT", code="NVT-DS")
        self.service = Service.objects.create(ship=self.navire, name="Service VT")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur VT")
        self.asset_type = AssetType.objects.create(name="TypeVT", category="Cat", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Plan VT", every_n_days=30
        )

        self.marin = User.objects.create_user(username="marin_elec", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "specialite": "Électricité", "ship": self.navire}
        )
        # Autre spécialité : ses maintenances/tickets ne doivent jamais compter.
        self.marin_autre = User.objects.create_user(username="marin_meca", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_autre, defaults={"role": "EQUIPIER", "specialite": "Mécanique", "ship": self.navire}
        )

        self.responsable = User.objects.create_user(username="resp_vt", password="pass")
        UserProfile.objects.update_or_create(user=self.responsable, defaults={"role": "EQUIPIER"})
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=self.responsable)

        self.client.login(username="resp_vt", password="pass")
        self.url = reverse("dashboard-specialite", args=[self.specialite.id])

    def test_maintenance_en_retard_assignee_a_un_marin_de_la_specialite_est_comptee(self):
        occurrence_en_retard = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2020-01-01", status="OVERDUE",
        )
        occurrence_en_retard.assignees.add(self.marin)
        # Assignée à un marin d'une autre spécialité : ne doit pas être comptée.
        occurrence_autre = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2020-01-01", status="OVERDUE",
        )
        occurrence_autre.assignees.add(self.marin_autre)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["technique_maintenances_en_retard"], 1)

    def test_tickets_correctifs_assignes_a_un_marin_de_la_specialite_sont_agreges(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Panne électrique", status="REPORTED")
        ticket.assignees.add(self.marin)
        # Assigné à un marin d'une autre spécialité : ne doit pas être compté.
        ticket_autre = CorrectiveTicket.objects.create(asset=self.asset, description="Autre panne", status="REPORTED")
        ticket_autre.assignees.add(self.marin_autre)

        response = self.client.get(self.url)

        self.assertEqual(response.context["technique_total_tickets_ouverts"], 1)
