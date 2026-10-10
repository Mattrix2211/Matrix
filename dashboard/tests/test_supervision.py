"""Bloc « Supervision » de la page « Aujourd'hui » : visibilité par rôle et bornage au périmètre."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset, AssetType
from dashboard.aujourdhui import peut_superviser, supervision
from logistics.models import Anomalie
from matrix.core.role_thresholds import invalidate_cache
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import RoleThresholdConfig, Sector, Service, Ship
from training.models import TrainingCourse


class SupervisionTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Frégate test", code="FT-SU")
        self.service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur_a = Sector.objects.create(service=self.service, name="Propulsion")
        self.secteur_b = Sector.objects.create(service=self.service, name="Auxiliaires")
        self.aujourdhui = timezone.localdate()
        self.asset_a = self._asset(self.secteur_a)
        self.asset_b = self._asset(self.secteur_b)
        invalidate_cache(self.navire.pk)
        self.equipier = self._marin("equipier", "EQUIPIER", self.secteur_a)
        self.chef_a = self._marin("chef_a", "CHEF_SECTEUR", self.secteur_a)

    def _marin(self, nom, role, secteur=None):
        user = User.objects.create_user(username=nom, password="pass", last_name=nom.capitalize())
        profil = user.profile
        profil.role = role
        if secteur:
            profil.ship, profil.service, profil.sector = self.navire, self.service, secteur
        profil.save()
        return user

    def _asset(self, secteur, statut="OK"):
        type_ = AssetType.objects.create(name=f"Pompe {secteur.name}{statut}", category="Incendie", sector=secteur)
        return Asset.objects.create(
            asset_type=type_, ship=self.navire, service=self.service, sector=secteur, status=statut,
        )

    def _occurrence(self, asset, jours, statut="PLANNED"):
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle", every_n_days=30)
        return MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=self.aujourdhui + timedelta(days=jours), status=statut,
        )

    def _page(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("home"))

    def test_equipier_ne_voit_pas_le_bloc(self):
        self._occurrence(self.asset_a, -2, "OVERDUE")
        r = self._page(self.equipier)
        self.assertIsNone(r.context["supervision"])
        self.assertNotContains(r, "Validations en attente")

    def test_chef_de_section_ne_voit_pas_le_bloc(self):
        chef_section = self._marin("chef_section", "CHEF_SECTION", self.secteur_a)
        self.assertFalse(peut_superviser(chef_section))

    def test_chef_voit_le_bloc(self):
        r = self._page(self.chef_a)
        self.assertIsNotNone(r.context["supervision"])
        self.assertContains(r, "Validations en attente")

    def test_chef_sans_perimetre_ne_voit_pas_le_bloc(self):
        sans_perimetre = self._marin("sans", "CHEF_SECTEUR")
        self.assertFalse(peut_superviser(sans_perimetre))

    def test_master_admin_sans_perimetre_voit_tout(self):
        admin = self._marin("admin", "MASTER_ADMIN")
        self._occurrence(self.asset_a, -2, "OVERDUE")
        self._occurrence(self.asset_b, -2, "OVERDUE")
        self.assertEqual(supervision(admin, self.aujourdhui)["retards_total"], 2)

    def test_seuil_configurable_par_navire(self):
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"supervision_aujourdhui": "CHEF_SERVICE"})
        invalidate_cache(self.navire.pk)
        self.assertFalse(peut_superviser(self.chef_a))

    def test_indicateurs_bornes_au_perimetre_du_chef(self):
        self._occurrence(self.asset_a, -2, "OVERDUE")
        self._occurrence(self.asset_a, -1)
        self._occurrence(self.asset_a, 3)
        self._occurrence(self.asset_b, -5, "OVERDUE")
        self._asset(self.secteur_a, "FAULTY")
        self._asset(self.secteur_b, "OUT_OF_SERVICE")
        for secteur in (self.secteur_a, self.secteur_b):
            Anomalie.objects.create(titre="Fuite", ship=self.navire, service=self.service, sector=secteur)
        Anomalie.objects.create(
            titre="Traitée", statut="TRAITEE", ship=self.navire, service=self.service, sector=self.secteur_a,
        )
        s = supervision(self.chef_a, self.aujourdhui)
        self.assertEqual(s["retards_total"], 2)
        self.assertEqual(s["retards_pct"], 67)
        self.assertEqual(s["anomalies_ouvertes"], 1)
        self.assertEqual(s["indisponibles"], 1)

    def test_validations_en_attente_du_perimetre(self):
        attente = self._occurrence(self.asset_a, 1, "WAITING_VALIDATION")
        self._occurrence(self.asset_b, 1, "WAITING_VALIDATION")
        s = supervision(self.chef_a, self.aujourdhui)
        self.assertEqual(s["validations_total"], 1)
        self.assertEqual(s["validations"][0]["url"], reverse("occurrence-execute", args=[attente.pk]))
        self.assertEqual(s["retards_total"], 0)

    def test_formation_bord_a_valider_comptee_pour_son_validateur(self):
        chef_service = self._marin("chef_service", "CHEF_SERVICE", self.secteur_a)
        TrainingCourse.objects.create(
            title="Habilitation bord", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            updated_by=self.chef_a,
        )
        self.assertEqual(supervision(chef_service, self.aujourdhui)["validations_total"], 1)
        self.assertEqual(supervision(self.chef_a, self.aujourdhui)["validations_total"], 0)

    def test_retards_listes_avec_les_assignes(self):
        occ = self._occurrence(self.asset_a, -3, "OVERDUE")
        occ.assignees.add(self.equipier)
        self._occurrence(self.asset_b, -3, "OVERDUE")
        retards = supervision(self.chef_a, self.aujourdhui)["retards"]
        self.assertEqual(len(retards), 1)
        self.assertIn("Equipier", retards[0]["detail"])

    def test_valider_reserve_aux_habilites(self):
        occ = self._occurrence(self.asset_a, 1, "WAITING_VALIDATION")
        self.assertTrue(supervision(self.chef_a, self.aujourdhui)["validations"][0]["peut_valider"])
        # Seuil de gestion des maintenances d'autrui relevé au-dessus du chef de secteur.
        RoleThresholdConfig.objects.create(
            ship=self.navire, thresholds={"maintenance_occurrence_gestion_tiers": "CHEF_SERVICE"},
        )
        invalidate_cache(self.navire.pk)
        # La config est annulée en fin de test : on purge aussi le cache pour ne pas fausser les autres tests.
        self.addCleanup(invalidate_cache, self.navire.pk)
        self.assertFalse(supervision(self.chef_a, self.aujourdhui)["validations"][0]["peut_valider"])
        occ.assignees.add(self.chef_a)
        self.assertTrue(supervision(self.chef_a, self.aujourdhui)["validations"][0]["peut_valider"])

    def test_formation_d_un_autre_navire_non_comptee(self):
        autre = Ship.objects.create(name="Autre navire", code="AN-SU")
        proposeur = self._marin("proposeur", "CHEF_SECTEUR")
        proposeur.profile.ship = autre
        proposeur.profile.save()
        TrainingCourse.objects.create(
            title="Ailleurs", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION", updated_by=proposeur,
        )
        commandant = self._marin("commandant", "COMMANDANT", self.secteur_a)
        self.assertEqual(supervision(commandant, self.aujourdhui)["formations_a_valider"], 0)
