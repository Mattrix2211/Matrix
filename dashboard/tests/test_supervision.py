"""Bloc « Supervision » de la page « Aujourd'hui » : visibilité par rôle et bornage au périmètre."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ServiceFunctionChoice
from assets.models import Asset, AssetType, Installation
from dashboard.aujourdhui import peut_superviser, supervision
from logistics.models import Anomalie
from matrix.core.role_thresholds import invalidate_cache
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import RoleThresholdConfig, Sector, Service, Ship
from quarts.models import ChefDeListe, CreneauServiceGarde, EchangeService, ServiceGarde
from training.models import CandidatureFormation, TrainingCourse


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
        self.assertEqual((s["hors_service"], s["defectueux"]), (0, 1))

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

    def _echange_accepte(self, secteur):
        garde = ServiceGarde.objects.create(
            sector=secteur, fonction=ServiceFunctionChoice.objects.get_or_create(name="Permanence")[0],
            date_debut=self.aujourdhui, date_fin=self.aujourdhui + timedelta(days=30), statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = timezone.now() + timedelta(days=5)
        a, b = (CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Permanence", debut=debut + timedelta(days=i), fin=debut + timedelta(days=i, hours=24),
            marin=self._marin(f"garde_{secteur.pk}_{i}_{EchangeService.objects.count()}", "EQUIPIER", secteur),
        ) for i in (0, 1))
        return EchangeService.objects.create(
            creneau_demandeur=a, creneau_cible=b, demandeur=a.marin, cible=b.marin, statut=EchangeService.STATUT_ACCEPTE,
        )

    def test_echange_de_service_a_valider_compte_dans_le_perimetre_seulement(self):
        ChefDeListe.objects.create(user=self.chef_a, sector=self.secteur_a)
        self._echange_accepte(self.secteur_a)
        self._echange_accepte(self.secteur_b)
        s = supervision(self.chef_a, self.aujourdhui)
        self.assertEqual(s["echanges_a_valider"], 1)
        self.assertEqual(s["validations_total"], 1)

    def test_candidature_a_valider_comptee_dans_le_perimetre_seulement(self):
        cours = TrainingCourse.objects.create(title="Secourisme")
        CandidatureFormation.objects.create(course=cours, marin=self.equipier)
        CandidatureFormation.objects.create(course=cours, marin=self._marin("autre_secteur", "EQUIPIER", self.secteur_b))
        s = supervision(self.chef_a, self.aujourdhui)
        self.assertEqual(s["candidatures_a_valider"], 1)
        self.assertEqual(s["validations_total"], 1)

    def test_installation_critique_en_retard_comptee_dans_le_perimetre_seulement(self):
        from assets.models import InstallationMaintenance

        for secteur in (self.secteur_a, self.secteur_b):
            installation = Installation.objects.create(
                designation=f"Groupe {secteur.name}", ship=self.navire, service=self.service, sector=secteur, critique=True,
            )
            fiche = InstallationMaintenance.objects.create(installation=installation, periodicity="3 mois", title="Révision")
            MaintenanceOccurrence.objects.create(
                installation_maintenance=fiche, scheduled_for=self.aujourdhui - timedelta(days=2), status="OVERDUE",
            )
        self.assertEqual(supervision(self.chef_a, self.aujourdhui)["installations_en_retard"], 1)

    def test_indicateurs_renvoient_vers_les_listes_filtrees(self):
        page = self._page(self.chef_a).content.decode()
        for lien in (f"{reverse('maintenance-occurrences')}?retard=1", f"{reverse('asset-list')}?status=OUT_OF_SERVICE",
                     f"{reverse('asset-list')}?status=FAULTY", f"{reverse('anomalie-list')}?statut=ouvertes&amp;vue=perimetre", f"{reverse('installation-list')}?critique=1&amp;retard=1"):
            self.assertIn(lien, page)

    def test_batiments_suivis_calcules_une_seule_fois_par_requete(self):
        from unittest import mock

        with mock.patch("dashboard.web_views.batiments_suivis", return_value=[]) as appel:
            self._page(self.chef_a)
        self.assertEqual(appel.call_count, 1)


class CompteursEtListesCiblesTests(TestCase):
    """Chaque indicateur annonce le nombre de lignes de la liste filtrée vers laquelle il renvoie."""

    _marin, _asset, _occurrence, _echange_accepte = (
        SupervisionTests._marin, SupervisionTests._asset, SupervisionTests._occurrence, SupervisionTests._echange_accepte,
    )

    def setUp(self):
        SupervisionTests.setUp(self)
        self.chef = self._marin("chef_liste_cible", "CHEF_SERVICE", self.secteur_a)
        self.client.force_login(self.chef)

    def _contexte(self, url):
        return self.client.get(url).context

    def test_maintenances_en_retard(self):
        self._occurrence(self.asset_a, -2, "OVERDUE")
        self._occurrence(self.asset_a, -1)
        self._occurrence(self.asset_a, -3, "WAITING_VALIDATION")
        self._occurrence(self.asset_a, 2)
        s = supervision(self.chef, self.aujourdhui)
        liste = self._contexte(f"{reverse('maintenance-occurrences')}?retard=1")["occurrences"]
        self.assertEqual((s["retards_total"], len(liste)), (2, 2))

    def test_anomalies_ouvertes(self):
        for statut in ("SIGNALEE", "TRAITEE"):
            Anomalie.objects.create(titre="A", statut=statut, ship=self.navire, service=self.service, sector=self.secteur_a)
        s = supervision(self.chef, self.aujourdhui)
        liste = self._contexte(s["anomalies_url"])["anomalies"]
        self.assertEqual((s["anomalies_ouvertes"], len(liste)), (1, 1))

    def test_materiels_hors_service_et_defectueux(self):
        self._asset(self.secteur_a, "OUT_OF_SERVICE")
        self._asset(self.secteur_a, "FAULTY")
        s = supervision(self.chef, self.aujourdhui)
        for cle, statut in (("hors_service", "OUT_OF_SERVICE"), ("defectueux", "FAULTY")):
            liste = self._contexte(f"{reverse('asset-list')}?status={statut}")["assets"]
            self.assertEqual((s[cle], len(liste)), (1, 1), cle)

    def test_installations_critiques_en_retard(self):
        from assets.models import InstallationMaintenance

        for designation, critique in (("Critique", True), ("Ordinaire", False)):
            installation = Installation.objects.create(
                designation=designation, ship=self.navire, service=self.service, sector=self.secteur_a, critique=critique,
            )
            fiche = InstallationMaintenance.objects.create(installation=installation, periodicity="3 mois", title="Révision")
            MaintenanceOccurrence.objects.create(
                installation_maintenance=fiche, scheduled_for=self.aujourdhui - timedelta(days=2), status="PLANNED",
            )
        s = supervision(self.chef, self.aujourdhui)
        liste = self._contexte(f"{reverse('installation-list')}?critique=1&retard=1")["installations"]
        self.assertEqual((s["installations_en_retard"], len(liste)), (1, 1))

    def test_echanges_et_candidatures_comme_les_pages_cibles(self):
        ChefDeListe.objects.create(user=self.chef, sector=self.secteur_a)
        self._echange_accepte(self.secteur_a)
        self._echange_accepte(self.secteur_b)
        CandidatureFormation.objects.create(course=TrainingCourse.objects.create(title="Secourisme"), marin=self.equipier)
        s = supervision(self.chef, self.aujourdhui)
        echanges = self._contexte(reverse("echanges-index"))["a_traiter"]
        self.assertEqual((s["echanges_a_valider"], len([e for e in echanges if e.peut_trancher])), (1, 1))
        candidatures = self._contexte(reverse("formation-list"))["candidatures_hierarchie_a_traiter"]
        self.assertEqual((s["candidatures_a_valider"], len(candidatures)), (1, 1))

    def test_requetes_des_echanges_constantes(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        ChefDeListe.objects.create(user=self.chef, sector=self.secteur_a)
        for _ in range(2):
            self._echange_accepte(self.secteur_a)
        with CaptureQueriesContext(connection) as deux_echanges:
            self._valides(2)
        for _ in range(8):
            self._echange_accepte(self.secteur_a)
        with CaptureQueriesContext(connection) as dix_echanges:
            self._valides(10)
        self.assertLessEqual(len(dix_echanges) - len(deux_echanges), 1)

    def _valides(self, attendu):
        from quarts.echanges import echanges_a_valider

        self.assertEqual(len(echanges_a_valider(self.chef)), attendu)
