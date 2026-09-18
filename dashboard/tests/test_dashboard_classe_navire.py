"""Tests du dashboard transverse par classe de navire
(dashboard/web_views.py::DashboardClasseNavireView / Choix) — tâche Notion
« Dashboards transverses par spécialité et par classe de navire »."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation, InstallationMaintenance
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import ResponsableClasseNavire, Sector, Service, Ship


class DashboardClasseNavireAccesTests(TestCase):
    def setUp(self):
        self.navire_a = Ship.objects.create(name="Frégate A", code="FA-CN", classe_navire="La Fayette")
        self.navire_b = Ship.objects.create(name="Frégate B", code="FB-CN", classe_navire="La Fayette")
        # Autre classe : ne doit jamais apparaître pour un responsable "La Fayette".
        self.navire_c = Ship.objects.create(name="Sous-marin C", code="SC-CN", classe_navire="Suffren")

    def _creer_utilisateur(self, username, role, ship=None):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship})
        return user

    def test_marin_non_responsable_na_pas_acces(self):
        self._creer_utilisateur("marin1", "EQUIPIER", self.navire_a)
        self.client.login(username="marin1", password="pass")
        response = self.client.get(reverse("dashboard-classe-navire", args=["La Fayette"]))
        self.assertEqual(response.status_code, 403)

    def test_responsable_designe_a_acces(self):
        responsable = self._creer_utilisateur("responsable1", "EQUIPIER")
        ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=responsable)
        self.client.login(username="responsable1", password="pass")
        response = self.client.get(reverse("dashboard-classe-navire", args=["La Fayette"]))
        self.assertEqual(response.status_code, 200)

    def test_responsable_dune_autre_classe_na_pas_acces(self):
        responsable = self._creer_utilisateur("responsable2", "EQUIPIER")
        ResponsableClasseNavire.objects.create(classe_navire="Suffren", user=responsable)
        self.client.login(username="responsable2", password="pass")
        response = self.client.get(reverse("dashboard-classe-navire", args=["La Fayette"]))
        self.assertEqual(response.status_code, 403)

    def test_master_admin_a_acces_sans_etre_designe(self):
        admin = self._creer_utilisateur("master1", "MASTER_ADMIN")
        self.client.login(username="master1", password="pass")
        response = self.client.get(reverse("dashboard-classe-navire", args=["La Fayette"]))
        self.assertEqual(response.status_code, 200)

    def test_choix_redirige_directement_si_une_seule_classe_accessible(self):
        responsable = self._creer_utilisateur("responsable3", "EQUIPIER")
        ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=responsable)
        self.client.login(username="responsable3", password="pass")
        response = self.client.get(reverse("dashboard-classe-navire-choix"))
        self.assertRedirects(response, reverse("dashboard-classe-navire", args=["La Fayette"]))

    def test_choix_refuse_si_aucune_classe_accessible(self):
        self._creer_utilisateur("marin2", "EQUIPIER")
        self.client.login(username="marin2", password="pass")
        response = self.client.get(reverse("dashboard-classe-navire-choix"))
        self.assertEqual(response.status_code, 403)


class DashboardClasseNavireAgregationTests(TestCase):
    """Vérifie que les tickets correctifs sont agrégés sur TOUS LES NAVIRES
    de la classe consultée, sans fuite vers un navire d'une autre classe."""

    def setUp(self):
        self.navire_a = Ship.objects.create(name="Frégate A", code="FA-AG", classe_navire="La Fayette")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.secteur_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )

        self.navire_b = Ship.objects.create(name="Frégate B", code="FB-AG", classe_navire="La Fayette")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.secteur_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        # Navire d'une autre classe : ne doit jamais apparaître.
        self.navire_c = Ship.objects.create(name="Sous-marin C", code="SC-AG", classe_navire="Suffren")
        self.service_c = Service.objects.create(ship=self.navire_c, name="Service C")
        self.secteur_c = Sector.objects.create(service=self.service_c, name="Secteur C")
        self.asset_type_c = AssetType.objects.create(name="TypeC", category="Cat", sector=self.secteur_c)
        self.asset_c = Asset.objects.create(
            asset_type=self.asset_type_c, ship=self.navire_c, service=self.service_c, sector=self.secteur_c,
        )

        self.responsable = User.objects.create_user(username="resp", password="pass")
        UserProfile.objects.update_or_create(user=self.responsable, defaults={"role": "EQUIPIER"})
        ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=self.responsable)
        self.client.login(username="resp", password="pass")
        self.url = reverse("dashboard-classe-navire", args=["La Fayette"])

    def test_tickets_ouverts_agreges_sur_les_deux_navires_de_la_classe(self):
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne A", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset_b, description="Panne B", status="REPORTED")
        # Autre classe : ne doit pas être compté.
        CorrectiveTicket.objects.create(asset=self.asset_c, description="Panne C", status="REPORTED")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_tickets_ouverts"], 2)
        self.assertEqual(len(response.context["navires"]), 2)


class DashboardClasseNavireComparatifTests(TestCase):
    """Vérifie le point 3 du cadrage du 12/09/2026 : le dashboard classe de
    navire propose un COMPARATIF de disponibilité opérationnelle PAR NAVIRE
    (taux de pannes, maintenance en retard, installations critiques hors
    service) — pas seulement un total agrégé de la classe."""

    def setUp(self):
        self.navire_a = Ship.objects.create(name="Frégate A", code="FA-CMP", classe_navire="La Fayette")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.secteur_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )
        self.plan_a = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset_a, name="Plan A", every_n_days=30
        )
        self.installation_critique_a = Installation.objects.create(
            designation="Groupe électrogène A", ship=self.navire_a, service=self.service_a,
            sector=self.secteur_a, critique=True,
        )
        self.entretien_critique_a = InstallationMaintenance.objects.create(
            installation=self.installation_critique_a, periodicity="3 mois", title="Vidange A",
        )

        # Navire B de la même classe : plus disponible que le navire A (aucune
        # panne, aucun retard), pour vérifier le comparatif PAR NAVIRE.
        self.navire_b = Ship.objects.create(name="Frégate B", code="FB-CMP", classe_navire="La Fayette")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.secteur_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        self.responsable = User.objects.create_user(username="resp_cmp", password="pass")
        UserProfile.objects.update_or_create(user=self.responsable, defaults={"role": "EQUIPIER"})
        ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=self.responsable)
        self.client.login(username="resp_cmp", password="pass")
        self.url = reverse("dashboard-classe-navire", args=["La Fayette"])

    def test_comparatif_distingue_le_navire_en_panne_du_navire_disponible(self):
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne A", status="REPORTED")
        MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for="2020-01-01", status="OVERDUE",
        )
        MaintenanceOccurrence.objects.create(
            installation_maintenance=self.entretien_critique_a, scheduled_for="2020-01-01", status="OVERDUE",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        comparatif = {ligne["navire"].id: ligne for ligne in response.context["comparatif_navires"]}
        self.assertEqual(len(comparatif), 2)

        ligne_a = comparatif[self.navire_a.id]
        self.assertEqual(ligne_a["tickets_ouverts"], 1)
        self.assertEqual(ligne_a["taux_pannes_pct"], 100)
        self.assertEqual(ligne_a["maintenances_en_retard"], 2)
        self.assertEqual(ligne_a["installations_critiques_total"], 1)
        self.assertEqual(ligne_a["installations_critiques_hors_service"], 1)

        ligne_b = comparatif[self.navire_b.id]
        self.assertEqual(ligne_b["tickets_ouverts"], 0)
        self.assertEqual(ligne_b["taux_pannes_pct"], 0)
        self.assertEqual(ligne_b["maintenances_en_retard"], 0)
        self.assertEqual(ligne_b["installations_critiques_total"], 0)
        self.assertEqual(ligne_b["installations_critiques_hors_service"], 0)
