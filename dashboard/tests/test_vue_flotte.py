"""Tests de la Vue flotte (dashboard/web_views.py::VueFlotteView) : vue agrégée
réservée à CHEF_SECTION et aux rôles supérieurs, scopée au périmètre effectif
du chef connecté — navire pour CHEF_SERVICE+, secteur pour CHEF_SECTEUR,
section pour CHEF_SECTION (cf. tâche [FEAT] Vue d'équipe pour CHEF_SECTEUR et
CHEF_SECTION)."""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation, InstallationMaintenance
from logistics.models import CorrectiveTicket, StockPiece
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Section, Sector, Service, Ship


class VueFlotteAccesTests(TestCase):
    """Contrôle d'accès : la Vue flotte n'est visible qu'à partir de CHEF_SECTION."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire test", code="NT-VF")
        self.service = Service.objects.create(ship=self.navire, name="Service test")
        self.url = reverse("vue-flotte")

    def _creer_utilisateur(self, username, role, **scope):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **scope})
        return user

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_equipier_na_pas_acces(self):
        self._creer_utilisateur("equipier", "EQUIPIER", ship=self.navire)
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_chef_section_a_acces(self):
        secteur = Sector.objects.create(service=self.service, name="Secteur test")
        section = Section.objects.create(sector=secteur, name="Section test")
        self._creer_utilisateur(
            "chef_section", "CHEF_SECTION", ship=self.navire, service=self.service, sector=secteur, section=section,
        )
        self.client.login(username="chef_section", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_chef_secteur_a_acces(self):
        secteur = Sector.objects.create(service=self.service, name="Secteur test 2")
        self._creer_utilisateur(
            "chef_secteur", "CHEF_SECTEUR", ship=self.navire, service=self.service, sector=secteur,
        )
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_chef_service_a_acces(self):
        self._creer_utilisateur("chef_service", "CHEF_SERVICE", ship=self.navire)
        self.client.login(username="chef_service", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_commandant_a_acces(self):
        self._creer_utilisateur("commandant", "COMMANDANT", ship=self.navire)
        self.client.login(username="commandant", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_admin_navire_a_acces(self):
        self._creer_utilisateur("admin_navire", "ADMIN_NAVIRE", ship=self.navire)
        self.client.login(username="admin_navire", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_lien_de_navigation_absent_pour_un_equipier(self):
        self._creer_utilisateur("equipier2", "EQUIPIER", ship=self.navire)
        self.client.login(username="equipier2", password="pass")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, self.url)

    def test_lien_de_navigation_present_pour_un_chef_de_service(self):
        self._creer_utilisateur("chef_service2", "CHEF_SERVICE", ship=self.navire)
        self.client.login(username="chef_service2", password="pass")
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.url)

    def test_lien_de_navigation_present_pour_un_chef_de_section(self):
        secteur = Sector.objects.create(service=self.service, name="Secteur nav")
        section = Section.objects.create(sector=secteur, name="Section nav")
        self._creer_utilisateur(
            "chef_section3", "CHEF_SECTION", ship=self.navire, service=self.service, sector=secteur, section=section,
        )
        self.client.login(username="chef_section3", password="pass")
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.url)


class VueFlotteAgregationTests(TestCase):
    """Vérifie que les indicateurs affichés sont correctement agrégés et scopés
    au navire du chef connecté, sans fuite vers un autre navire de la flotte."""

    def setUp(self):
        # Navire A : celui du chef de service connecté.
        self.navire_a = Ship.objects.create(name="Navire A", code="NA-VF")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.secteur_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )
        self.plan_a = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset_a, name="Plan A", every_n_days=30
        )
        self.installation_a = Installation.objects.create(
            designation="Groupe électrogène A", ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )
        self.installation_maintenance_a = InstallationMaintenance.objects.create(
            installation=self.installation_a, periodicity="3 mois", title="Vidange A",
        )

        # Navire B : ne doit jamais apparaître dans les indicateurs du navire A.
        self.navire_b = Ship.objects.create(name="Navire B", code="NB-VF")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.secteur_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )
        self.plan_b = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset_b, name="Plan B", every_n_days=30
        )

        self.chef_service_a = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service_a, defaults={"role": "CHEF_SERVICE", "ship": self.navire_a}
        )

        self.url = reverse("vue-flotte")
        self.client.login(username="chef_a", password="pass")

    def test_maintenances_en_retard_comptees_pour_le_navire_du_chef(self):
        MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for="2020-01-01", status="OVERDUE"
        )
        MaintenanceOccurrence.objects.create(
            installation_maintenance=self.installation_maintenance_a,
            scheduled_for="2020-01-01", status="OVERDUE",
        )
        # En retard mais sur le navire B : ne doit pas être compté.
        MaintenanceOccurrence.objects.create(
            plan=self.plan_b, asset=self.asset_b, scheduled_for="2020-01-01", status="OVERDUE"
        )
        # Pas en retard sur le navire A : ne doit pas être compté non plus.
        MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for="2099-01-01", status="PLANNED"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["maintenances_en_retard"], 2)

    def test_tickets_ouverts_par_statut_scopes_au_navire(self):
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne 1", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne 2", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne 3", status="IN_REPAIR")
        # Ticket clos : hors du périmètre des tickets "ouverts".
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne 4", status="CLOSED")
        # Ticket ouvert mais sur le navire B : ne doit pas apparaître.
        CorrectiveTicket.objects.create(asset=self.asset_b, description="Panne B", status="REPORTED")

        response = self.client.get(self.url)

        tickets_par_statut = {item["statut"]: item["total"] for item in response.context["tickets_par_statut"]}
        self.assertEqual(tickets_par_statut["REPORTED"], 2)
        self.assertEqual(tickets_par_statut["IN_REPAIR"], 1)
        self.assertEqual(tickets_par_statut["WAITING_PARTS"], 0)
        self.assertEqual(response.context["total_tickets_ouverts"], 3)

    def test_pieces_de_stock_sous_seuil_scopees_au_navire(self):
        StockPiece.objects.create(
            reference="REF-A1", designation="Joint A", quantite=1, quantite_minimale=5,
            ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )
        # Au-dessus du seuil : ne doit pas apparaître.
        StockPiece.objects.create(
            reference="REF-A2", designation="Filtre A", quantite=10, quantite_minimale=5,
            ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )
        # Sous le seuil mais sur le navire B : ne doit pas apparaître.
        StockPiece.objects.create(
            reference="REF-B1", designation="Joint B", quantite=1, quantite_minimale=5,
            ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        response = self.client.get(self.url)

        references = {piece.reference for piece in response.context["pieces_sous_seuil"]}
        self.assertEqual(references, {"REF-A1"})

    def test_profil_sans_navire_affiche_un_message_clair(self):
        chef_sans_navire = User.objects.create_user(username="chef_sans_navire", password="pass")
        UserProfile.objects.update_or_create(
            user=chef_sans_navire, defaults={"role": "CHEF_SERVICE"}
        )
        self.client.login(username="chef_sans_navire", password="pass")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["aucun_perimetre"])
        self.assertContains(response, "Aucune unité n'est associée à votre profil")
        # Les jauges (principe n°5 CLAUDE.md) doivent rester à 0, pas planter,
        # même sans aucune donnée à agréger.
        self.assertEqual(response.context["maintenances_en_retard_pct"], 0)
        self.assertEqual(response.context["pieces_sous_seuil_pct"], 0)

    def test_jauge_maintenances_en_retard_est_un_pourcentage_des_actives(self):
        # 1 en retard sur 2 actives (OVERDUE + PLANNED ; DONE exclu du
        # dénominateur, même logique que _STATUTS_MAINTENANCE_TERMINES) = 50 %.
        MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for="2020-01-01", status="OVERDUE"
        )
        MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for="2099-01-01", status="PLANNED"
        )
        MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for="2020-01-01", status="DONE"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.context["maintenances_en_retard"], 1)
        self.assertEqual(response.context["maintenances_en_retard_pct"], 50)

    def test_jauge_pieces_sous_seuil_est_un_pourcentage_du_perimetre(self):
        StockPiece.objects.create(
            reference="REF-A1", designation="Joint A", quantite=1, quantite_minimale=5,
            ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )
        StockPiece.objects.create(
            reference="REF-A2", designation="Filtre A", quantite=10, quantite_minimale=5,
            ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.context["pieces_sous_seuil_pct"], 50)

    def test_donnees_json_du_graphique_tickets_par_statut(self):
        # Alimente le doughnut Chart.js réutilisé de dashboard/index.html : les
        # deux listes JSON doivent correspondre exactement à tickets_par_statut.
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne 1", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne 2", status="IN_REPAIR")

        response = self.client.get(self.url)

        labels = json.loads(response.context["tickets_chart_labels_json"])
        values = json.loads(response.context["tickets_chart_values_json"])
        self.assertEqual(len(labels), len(values))
        self.assertEqual(sum(values), response.context["total_tickets_ouverts"])
        self.assertEqual(sum(values), 2)


class VueFlotteScopeSecteurEtSectionTests(TestCase):
    """Un CHEF_SECTEUR ou un CHEF_SECTION voit l'agrégat de son secteur/section
    uniquement — même navire, mais secteurs/sections différents ne doivent
    jamais se mélanger (cf. tâche [FEAT] Vue d'équipe pour CHEF_SECTEUR et
    CHEF_SECTION)."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire commun", code="NC-SEC")
        self.service = Service.objects.create(ship=self.navire, name="Service commun")

        # Secteur 1 / Section 1 : celui des chefs connectés dans les tests.
        self.secteur_1 = Sector.objects.create(service=self.service, name="Secteur 1")
        self.section_1 = Section.objects.create(sector=self.secteur_1, name="Section 1")
        self.asset_type_1 = AssetType.objects.create(name="Type1", category="Cat", sector=self.secteur_1)
        self.asset_1 = Asset.objects.create(
            asset_type=self.asset_type_1, ship=self.navire, service=self.service,
            sector=self.secteur_1, section=self.section_1,
        )

        # Secteur 2 / Section 2 : ne doit jamais apparaître pour les chefs du secteur/section 1.
        self.secteur_2 = Sector.objects.create(service=self.service, name="Secteur 2")
        self.section_2 = Section.objects.create(sector=self.secteur_2, name="Section 2")
        self.asset_type_2 = AssetType.objects.create(name="Type2", category="Cat", sector=self.secteur_2)
        self.asset_2 = Asset.objects.create(
            asset_type=self.asset_type_2, ship=self.navire, service=self.service,
            sector=self.secteur_2, section=self.section_2,
        )

        self.chef_secteur = User.objects.create_user(username="chef_secteur_scope", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur,
            defaults={"role": "CHEF_SECTEUR", "ship": self.navire, "service": self.service, "sector": self.secteur_1},
        )

        self.chef_section = User.objects.create_user(username="chef_section_scope", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section,
            defaults={
                "role": "CHEF_SECTION", "ship": self.navire, "service": self.service,
                "sector": self.secteur_1, "section": self.section_1,
            },
        )

        self.url = reverse("vue-flotte")

    def test_chef_secteur_ne_voit_que_les_tickets_de_son_secteur(self):
        CorrectiveTicket.objects.create(asset=self.asset_1, description="Panne secteur 1", status="REPORTED")
        # Même navire, autre secteur : ne doit pas apparaître.
        CorrectiveTicket.objects.create(asset=self.asset_2, description="Panne secteur 2", status="REPORTED")

        self.client.login(username="chef_secteur_scope", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_tickets_ouverts"], 1)
        self.assertEqual(response.context["niveau_perimetre"], "secteur")
        self.assertFalse(response.context["flotte_entiere"])
        self.assertContains(response, "Vue de mon secteur")

    def test_chef_section_ne_voit_que_les_tickets_de_sa_section(self):
        # Même secteur (secteur_1), mais une autre section : ne doit pas apparaître
        # pour le chef de section 1.
        self.asset_type_1b = AssetType.objects.create(name="Type1b", category="Cat", sector=self.secteur_1)
        section_1b = Section.objects.create(sector=self.secteur_1, name="Section 1b")
        asset_1b = Asset.objects.create(
            asset_type=self.asset_type_1b, ship=self.navire, service=self.service,
            sector=self.secteur_1, section=section_1b,
        )
        CorrectiveTicket.objects.create(asset=self.asset_1, description="Panne section 1", status="REPORTED")
        CorrectiveTicket.objects.create(asset=asset_1b, description="Panne section 1b", status="REPORTED")

        self.client.login(username="chef_section_scope", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_tickets_ouverts"], 1)
        self.assertEqual(response.context["niveau_perimetre"], "section")
        self.assertContains(response, "Vue de ma section")

    def test_chef_secteur_sans_secteur_affiche_un_message_clair(self):
        chef_sans_secteur = User.objects.create_user(username="chef_sans_secteur", password="pass")
        UserProfile.objects.update_or_create(user=chef_sans_secteur, defaults={"role": "CHEF_SECTEUR"})
        self.client.login(username="chef_sans_secteur", password="pass")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["aucun_perimetre"])
        self.assertContains(response, "Aucun secteur n'est associé à votre profil")

    def test_chef_section_sans_section_affiche_un_message_clair(self):
        chef_sans_section = User.objects.create_user(username="chef_sans_section", password="pass")
        UserProfile.objects.update_or_create(user=chef_sans_section, defaults={"role": "CHEF_SECTION"})
        self.client.login(username="chef_sans_section", password="pass")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["aucun_perimetre"])
        self.assertContains(response, "Aucune section n'est associée à votre profil")


class VueFlotteMasterAdminTests(TestCase):
    """Un MASTER_ADMIN (accès multi-navires) voit l'agrégat de la flotte entière,
    pas seulement d'un navire précis."""

    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire A", code="NA-MA")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.secteur_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )

        self.navire_b = Ship.objects.create(name="Navire B", code="NB-MA")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.secteur_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        self.master_admin = User.objects.create_user(username="master", password="pass")
        UserProfile.objects.update_or_create(user=self.master_admin, defaults={"role": "MASTER_ADMIN"})

        self.url = reverse("vue-flotte")

    def test_master_admin_voit_les_tickets_de_tous_les_navires(self):
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne A", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset_b, description="Panne B", status="REPORTED")

        self.client.login(username="master", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["flotte_entiere"])
        self.assertEqual(response.context["total_tickets_ouverts"], 2)
