"""Tests du Circuit C — Circuit d'approbation chef de secteur -> chef de
service pour les formations « gérées par le bord » (tâche Notion du même
nom) : un chef de secteur (CHEF_SECTEUR+) peut créer ou modifier une
formation administrée par son bord, mais elle reste invisible du catalogue
(statut_validation WAITING_VALIDATION, cf. TrainingCourse.gere_par_le_bord)
tant qu'un chef de service de son périmètre (ou supervision globale) ne l'a
pas validée — même pattern d'état explicite que WAITING_VALIDATION sur les
occurrences de maintenance (maintenance/models.py). Un CHEF_SERVICE+ proposant
directement n'a besoin d'aucune validation supplémentaire (statut ACTIVE
immédiat)."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from training.models import (
    CandidatureFormation,
    DemandePlace,
    ReferentFormation,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
)


def _construire_bord(prefixe):
    """Construit une hiérarchie Navire > Service > Secteur > Section complète
    — même helper que training/tests/test_candidature_formation.py."""
    ship = Ship.objects.create(name=f"Navire {prefixe}", code=prefixe[:8])
    service = Service.objects.create(ship=ship, name=f"Service {prefixe}")
    sector = Sector.objects.create(service=service, name=f"Secteur {prefixe}")
    section = Section.objects.create(sector=sector, name=f"Section {prefixe}")
    return ship, service, sector, section


class PropositionCreationTests(TestCase):
    """Un chef de secteur (CHEF_SECTEUR+) propose une nouvelle formation
    « gérée par le bord » : elle reste en attente de validation, invisible du
    catalogue général, tant qu'un chef de service ne l'a pas validée."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("PROP")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_prop", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )

    def test_proposition_reste_en_attente_et_invisible_du_catalogue(self):
        self.client.login(username="chef_secteur_prop", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "title": "Sécurité incendie interne",
            "description": "Formation propre au bord.",
            "category": "Sécurité/Incendie",
            "validity_days": "180",
        })
        self.assertEqual(r.status_code, 302)
        course = TrainingCourse.objects.get(title="Sécurité incendie interne")
        self.assertTrue(course.gere_par_le_bord)
        self.assertEqual(course.statut_validation, "WAITING_VALIDATION")
        self.assertEqual(course.created_by, self.chef_secteur)
        self.assertEqual(course.updated_by, self.chef_secteur)
        self.assertEqual(course.validity_days, 180)
        # Invisible du catalogue général tant que non validée.
        liste = self.client.get("/formations/")
        titres = [f.title for f in liste.context["formations"]]
        self.assertNotIn("Sécurité incendie interne", titres)

    def test_commentaire_dev_modale_circuit_c_non_affiche_en_clair(self):
        """Régression : le commentaire {# ... #} multi-lignes d'en-tête de la
        modale de proposition (Circuit C) s'affichait en clair, faute d'être
        invisible avec {% comment %}...{% endcomment %}."""
        self.client.login(username="chef_secteur_prop", password="pass")
        r = self.client.get("/formations/")
        self.assertTrue(r.context["peut_proposer_formation_bord"])
        self.assertNotContains(r, "Circuit C — Circuit d'approbation chef de secteur")

    def test_apparait_dans_mes_propositions(self):
        self.client.login(username="chef_secteur_prop", password="pass")
        self.client.post("/formations/", {
            "action": "proposer_formation_bord", "title": "Levage bord",
        })
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["mes_propositions_bord"]]
        self.assertIn("Levage bord", titres)

    def test_titre_obligatoire(self):
        self.client.login(username="chef_secteur_prop", password="pass")
        r = self.client.post("/formations/", {"action": "proposer_formation_bord", "title": ""})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingCourse.objects.filter(gere_par_le_bord=True).exists())

    def test_refus_pour_role_inferieur(self):
        chef_section = User.objects.create_user(username="chef_section_prop", password="pass")
        UserProfile.objects.update_or_create(
            user=chef_section, defaults={"role": "CHEF_SECTION", "section": self.section},
        )
        self.client.login(username="chef_section_prop", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord", "title": "Formation refusée",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation refusée").exists())

    def test_bouton_absent_pour_le_chef_section(self):
        chef_section = User.objects.create_user(username="chef_section_bouton", password="pass")
        UserProfile.objects.update_or_create(
            user=chef_section, defaults={"role": "CHEF_SECTION", "section": self.section},
        )
        self.client.login(username="chef_section_bouton", password="pass")
        r = self.client.get("/formations/")
        self.assertFalse(r.context["peut_proposer_formation_bord"])
        self.assertNotContains(r, "proposerFormationBordModal")


class PropositionParChefServiceTests(TestCase):
    """Un chef de service (CHEF_SERVICE+) proposant directement une
    formation « bord » n'a besoin d'aucune validation supplémentaire : son
    propre rôle vaut déjà l'accord requis."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("CS")
        self.chef_service = User.objects.create_user(username="chef_service_prop", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "service": self.service},
        )

    def test_formation_immediatement_active(self):
        self.client.login(username="chef_service_prop", password="pass")
        self.client.post("/formations/", {
            "action": "proposer_formation_bord", "title": "Formation validée d'office",
        })
        course = TrainingCourse.objects.get(title="Formation validée d'office")
        self.assertEqual(course.statut_validation, "ACTIVE")
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Formation validée d'office", titres)


class ValidationPropositionBordTests(TestCase):
    """Validation par un chef de service (CHEF_SERVICE+) du même périmètre
    que le chef de secteur proposeur (filtres_perimetre_marin, même principe
    que le Circuit B), ou par supervision globale (COMMANDANT+)."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("VAL")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_val", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.chef_service = User.objects.create_user(username="chef_service_val", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "service": self.service},
        )
        self.course = TrainingCourse.objects.create(
            title="Habilitation bord", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )

    def test_validation_dans_le_perimetre(self):
        self.client.login(username="chef_service_val", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_formation_bord", "pk": self.course.id,
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut_validation, "ACTIVE")
        notif = Notification.objects.filter(user=self.chef_secteur).first()
        self.assertIsNotNone(notif)
        self.assertIn("validée", notif.verb)

    def test_apparait_dans_le_catalogue_apres_validation(self):
        self.client.login(username="chef_service_val", password="pass")
        self.client.post("/formations/", {"action": "valider_formation_bord", "pk": self.course.id})
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Habilitation bord", titres)

    def test_refus_hors_perimetre(self):
        autre_ship, autre_service, _, _ = _construire_bord("HORSVAL")
        chef_service_hors = User.objects.create_user(username="chef_service_hors_val", password="pass")
        UserProfile.objects.update_or_create(
            user=chef_service_hors, defaults={"role": "CHEF_SERVICE", "service": autre_service},
        )
        self.client.login(username="chef_service_hors_val", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_formation_bord", "pk": self.course.id,
        })
        self.assertEqual(r.status_code, 403)
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut_validation, "WAITING_VALIDATION")

    def test_refus_pour_role_inferieur(self):
        autre_chef_secteur = User.objects.create_user(username="chef_secteur_val_bis", password="pass")
        UserProfile.objects.update_or_create(
            user=autre_chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.client.login(username="chef_secteur_val_bis", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_formation_bord", "pk": self.course.id,
        })
        self.assertEqual(r.status_code, 403)
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut_validation, "WAITING_VALIDATION")

    def test_validation_par_supervision_globale(self):
        commandant = User.objects.create_user(username="commandant_val", password="pass")
        UserProfile.objects.update_or_create(
            user=commandant, defaults={"role": "COMMANDANT", "ship": Ship.objects.create(name="Autre navire", code="AUTVAL")},
        )
        self.client.login(username="commandant_val", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_formation_bord", "pk": self.course.id,
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut_validation, "ACTIVE")

    def test_apparait_a_valider_pour_le_chef_de_service_du_perimetre(self):
        self.client.login(username="chef_service_val", password="pass")
        r = self.client.get("/formations/")
        ids = [f.id for f in r.context["formations_bord_a_valider"]]
        self.assertIn(self.course.id, ids)


class RefusPropositionBordTests(TestCase):
    """Refus par le chef de service : la formation reste hors catalogue
    (REFUSED), le chef de secteur pouvant la reprendre et la soumettre à
    nouveau."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("REF")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_ref", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.chef_service = User.objects.create_user(username="chef_service_ref", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "service": self.service},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation refusable", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )

    def test_refus_par_le_chef_de_service(self):
        self.client.login(username="chef_service_ref", password="pass")
        r = self.client.post("/formations/", {
            "action": "refuser_formation_bord", "pk": self.course.id,
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut_validation, "REFUSED")
        notif = Notification.objects.filter(user=self.chef_secteur).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, "warning")

    def test_reprise_et_nouvelle_soumission_apres_refus(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        self.client.login(username="chef_secteur_ref", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course.id,
            "title": "Formation refusable corrigée",
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Formation refusable corrigée")
        self.assertEqual(self.course.statut_validation, "WAITING_VALIDATION")


class ModificationFormationBordTests(TestCase):
    """Modification d'une formation « bord » déjà ACTIVE par son propre
    proposeur : repasse en attente de validation, invisible du catalogue
    jusqu'à re-validation. Une formation « organisme » (gere_par_le_bord=False)
    reste hors de portée de ce circuit. `updated_by` est TOUJOURS renseigné au
    proposeur d'origine (created_by/updated_by) : une formation bord sans
    proposeur connu (`updated_by` vide) ne peut être modifiée par personne
    d'autre que la supervision globale (cf. peut_modifier_formation_bord)."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("MOD")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_mod", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.course_bord = TrainingCourse.objects.create(
            title="Formation bord active", gere_par_le_bord=True, statut_validation="ACTIVE",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )
        self.course_organisme = TrainingCourse.objects.create(title="Formation organisme")

    def test_modification_repasse_en_attente_et_disparait_du_catalogue(self):
        self.client.login(username="chef_secteur_mod", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course_bord.id,
            "title": "Formation bord modifiée",
        })
        self.assertEqual(r.status_code, 302)
        self.course_bord.refresh_from_db()
        self.assertEqual(self.course_bord.title, "Formation bord modifiée")
        self.assertEqual(self.course_bord.statut_validation, "WAITING_VALIDATION")
        liste = self.client.get("/formations/")
        titres = [f.title for f in liste.context["formations"]]
        self.assertNotIn("Formation bord modifiée", titres)

    def test_impossible_de_modifier_une_formation_organisme(self):
        self.client.login(username="chef_secteur_mod", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course_organisme.id,
            "title": "Tentative de détournement",
        })
        self.assertEqual(r.status_code, 302)
        self.course_organisme.refresh_from_db()
        self.assertEqual(self.course_organisme.title, "Formation organisme")


class FuiteInterNavireModificationBordTests(TestCase):
    """Correction Tech Lead n°2 — un chef de secteur d'un AUTRE navire ne
    peut pas modifier une formation « bord » proposée par un chef de secteur
    d'un navire différent, même si elle est déjà ACTIVE et donc visible du
    catalogue global (formation UNIQUE et portable, CLAUDE.md)."""

    def setUp(self):
        self.ship_a, self.service_a, self.sector_a, self.section_a = _construire_bord("INTERA")
        self.ship_b, self.service_b, self.sector_b, self.section_b = _construire_bord("INTERB")
        self.chef_secteur_a = User.objects.create_user(username="chef_secteur_intera", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_a, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_a},
        )
        self.chef_secteur_b = User.objects.create_user(username="chef_secteur_interb", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_b, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_b},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord du navire A", gere_par_le_bord=True, statut_validation="ACTIVE",
            created_by=self.chef_secteur_a, updated_by=self.chef_secteur_a,
        )

    def test_chef_secteur_autre_navire_ne_peut_pas_modifier(self):
        self.client.login(username="chef_secteur_interb", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course.id,
            "title": "Détournée par le navire B",
        })
        self.assertEqual(r.status_code, 403)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Formation bord du navire A")
        self.assertEqual(self.course.statut_validation, "ACTIVE")
        # Toujours visible normalement dans le catalogue global : la
        # tentative de détournement n'a eu aucun effet.
        liste = self.client.get("/formations/")
        titres = [f.title for f in liste.context["formations"]]
        self.assertIn("Formation bord du navire A", titres)

    def test_proposeur_d_origine_peut_toujours_modifier(self):
        self.client.login(username="chef_secteur_intera", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course.id,
            "title": "Formation modifiée par son propre navire",
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Formation modifiée par son propre navire")

    def test_chef_service_du_meme_perimetre_peut_modifier(self):
        chef_service_a = User.objects.create_user(username="chef_service_intera", password="pass")
        UserProfile.objects.update_or_create(
            user=chef_service_a, defaults={"role": "CHEF_SERVICE", "service": self.service_a},
        )
        self.client.login(username="chef_service_intera", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course.id,
            "title": "Modifiée par le chef de service du même navire",
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Modifiée par le chef de service du même navire")

    def test_commandant_supervision_globale_peut_toujours_modifier(self):
        commandant = User.objects.create_user(username="commandant_inter", password="pass")
        UserProfile.objects.update_or_create(
            user=commandant, defaults={"role": "COMMANDANT", "ship": Ship.objects.create(name="Navire C", code="INTERC")},
        )
        self.client.login(username="commandant_inter", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course.id,
            "title": "Modifiée par supervision globale",
        })
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Modifiée par supervision globale")


class FormationBordEnServiceTests(TestCase):
    """Correction Tech Lead n°3 (option (b) retenue : exclusion plutôt que
    snapshot/rollback) — une formation « bord » déjà ACTIVE et réellement
    utilisée (validation enregistrée, session liée, ou servant de prérequis à
    une autre formation) ne peut plus être modifiée en place : elle
    resterait visible/valide pendant que la modification est en attente de
    revalidation, sans risque de disparition ni de rollback à gérer."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("SERV")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_serv", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord en service", gere_par_le_bord=True, statut_validation="ACTIVE",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )

    def _proposer_modification(self):
        self.client.login(username="chef_secteur_serv", password="pass")
        return self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "pk": self.course.id,
            "title": "Tentative de modification en place",
        })

    def test_modification_refusee_si_validations_existantes(self):
        from datetime import date
        TrainingRecord.objects.create(
            user=self.chef_secteur, course=self.course,
            completed_at=date(2026, 1, 1), expires_at=date(2027, 1, 1),
        )
        r = self._proposer_modification()
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Formation bord en service")
        self.assertEqual(self.course.statut_validation, "ACTIVE")

    def test_modification_refusee_si_session_liee(self):
        from datetime import datetime, timezone as dt_timezone
        TrainingSession.objects.create(
            course=self.course, scheduled_at=datetime(2027, 1, 1, tzinfo=dt_timezone.utc),
        )
        r = self._proposer_modification()
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Formation bord en service")

    def test_modification_refusee_si_prerequis_d_une_autre_formation(self):
        autre = TrainingCourse.objects.create(title="Formation dépendante")
        autre.prerequisites.add(self.course)
        r = self._proposer_modification()
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Formation bord en service")

    def test_modification_autorisee_si_pas_encore_utilisee(self):
        r = self._proposer_modification()
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Tentative de modification en place")
        self.assertEqual(self.course.statut_validation, "WAITING_VALIDATION")


class NonRegressionCatalogueTests(TestCase):
    """Une formation classique (créée par ADMIN_NAVIRE ou déjà existante,
    gere_par_le_bord=False) reste ACTIVE par défaut et visible normalement :
    l'ajout du Circuit C ne change rien pour le catalogue existant."""

    def test_formation_existante_reste_active_et_visible(self):
        course = TrainingCourse.objects.create(title="Formation historique")
        self.assertEqual(course.statut_validation, "ACTIVE")
        self.assertFalse(course.gere_par_le_bord)
        ship = Ship.objects.create(name="Navire Historique", code="HIST")
        admin = User.objects.create_user(username="admin_hist", password="pass")
        UserProfile.objects.update_or_create(user=admin, defaults={"role": "ADMIN_NAVIRE", "ship": ship})
        self.client.login(username="admin_hist", password="pass")
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Formation historique", titres)


class FuiteStatutValidationCandidatureTests(TestCase):
    """Non-régression QA (4e boucle de correction) — une formation « bord »
    WAITING_VALIDATION ou REFUSED doit rester invisible/inutilisable pour
    tout le monde sauf le proposeur/validateur concerné, y compris via
    action=candidater_formation (Circuit B) en devinant son identifiant dans
    le POST : reproduction exacte du scénario signalé par le QA."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("GAPCAND")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_gapcand", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord en attente candidature", gere_par_le_bord=True,
            statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )
        self.equipier = User.objects.create_user(username="equipier_gapcand", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "section": self.section},
        )

    def test_candidature_refusee_si_formation_en_attente(self):
        self.client.login(username="equipier_gapcand", password="pass")
        r = self.client.post("/formations/", {
            "action": "candidater_formation", "course_id": self.course.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(CandidatureFormation.objects.filter(course=self.course).exists())

    def test_candidature_refusee_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        self.client.login(username="equipier_gapcand", password="pass")
        r = self.client.post("/formations/", {
            "action": "candidater_formation", "course_id": self.course.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(CandidatureFormation.objects.filter(course=self.course).exists())


class FuiteStatutValidationDemandePlacesTests(TestCase):
    """Même non-régression que ci-dessus, pour action=demander_places
    (Circuit A) — un chef de secteur ne peut pas formuler de demande de
    places sur une formation « bord » pas encore validée ou refusée."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("GAPDEM")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_gapdem", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord en attente demande", gere_par_le_bord=True,
            statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )

    def test_demande_refusee_si_formation_en_attente(self):
        self.client.login(username="chef_secteur_gapdem", password="pass")
        r = self.client.post("/formations/", {
            "action": "demander_places", "course_id": self.course.id, "nb_places_demandees": 2,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(DemandePlace.objects.filter(course=self.course).exists())

    def test_demande_refusee_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        self.client.login(username="chef_secteur_gapdem", password="pass")
        r = self.client.post("/formations/", {
            "action": "demander_places", "course_id": self.course.id, "nb_places_demandees": 2,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(DemandePlace.objects.filter(course=self.course).exists())


class FuiteStatutValidationAttributionPlacesTests(TestCase):
    """Même non-régression que ci-dessus, pour action=attribuer_places
    (Circuit A) : scénario réaliste où la DemandePlace a été créée quand la
    formation était encore ACTIVE, puis son proposeur d'origine l'a modifiée
    entre-temps (formation pas encore « en service », cf.
    formation_bord_en_service, qui ne tient pas compte des demandes) — le
    statut repasse à WAITING_VALIDATION/REFUSED avant que l'organisme ne
    traite la demande : l'attribution doit être bloquée à ce moment précis,
    pas seulement à la création de la demande."""

    def setUp(self):
        self.ecole = Ship.objects.create(name="École Gap", code="GAPECO", type_unite=Ship.TypeUnite.ECOLE)
        self.ship, self.service, self.sector, _ = _construire_bord("GAPATTR")
        self.chef_secteur_proposeur = User.objects.create_user(
            username="chef_secteur_gapattr_prop", password="pass",
        )
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_proposeur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord attribution", gere_par_le_bord=True, statut_validation="ACTIVE",
            created_by=self.chef_secteur_proposeur, updated_by=self.chef_secteur_proposeur,
        )
        self.referent = User.objects.create_user(username="referent_gapattr", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent, defaults={"role": "EQUIPIER", "ship": self.ecole},
        )
        ReferentFormation.objects.create(course=self.course, ship=self.ecole, user=self.referent)
        self.chef_demandeur = User.objects.create_user(username="chef_secteur_gapattr_dem", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_demandeur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.demande = DemandePlace.objects.create(
            course=self.course, ship=self.ship, nb_places_demandees=2, created_by=self.chef_demandeur,
        )

    def _tenter_attribution(self):
        self.client.login(username="referent_gapattr", password="pass")
        return self.client.post("/formations/", {
            "action": "attribuer_places",
            "demande_id": self.demande.id,
            "nb_places_attribuees": 1,
            "nouvelle_session_date": "2027-01-01T10:00",
        })

    def test_attribution_refusee_si_formation_repassee_en_attente(self):
        self.course.statut_validation = "WAITING_VALIDATION"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter_attribution()
        self.assertEqual(r.status_code, 302)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, "REQUESTED")
        self.assertFalse(TrainingSession.objects.filter(course=self.course).exists())

    def test_attribution_refusee_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter_attribution()
        self.assertEqual(r.status_code, 302)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, "REQUESTED")
        self.assertFalse(TrainingSession.objects.filter(course=self.course).exists())


class FuiteStatutValidationValidationRecordTests(TestCase):
    """Même non-régression que ci-dessus, pour ValiderFormationView (création
    d'un TrainingRecord) : un chef habilité ne peut pas valider une formation
    « bord » pour un marin tant qu'elle n'est pas ACTIVE."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("GAPVAL")
        self.chef = User.objects.create_user(username="chef_section_gapval", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "section": self.section},
        )
        self.marin = User.objects.create_user(username="marin_gapval", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord validation record", gere_par_le_bord=True,
            statut_validation="WAITING_VALIDATION",
            created_by=self.chef, updated_by=self.chef,
        )

    def _tenter_validation(self):
        self.client.login(username="chef_section_gapval", password="pass")
        return self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-01",
        })

    def test_validation_refusee_si_formation_en_attente(self):
        r = self._tenter_validation()
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingRecord.objects.filter(course=self.course).exists())

    def test_validation_refusee_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter_validation()
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingRecord.objects.filter(course=self.course).exists())


class FuiteStatutValidationUpdatePrerequisitesTests(TestCase):
    """Gap supplémentaire trouvé dans le même esprit que les 4 signalés par le
    QA (action=update_prerequisites, réservée à CHEF_SECTION+ pour n'importe
    quelle formation du catalogue global, cf. training/web_views.py) : un chef
    de section d'un autre navire, sans lien avec la proposition, ne peut pas
    éditer les prérequis/catégorie/référents d'une formation « bord » encore
    en attente de validation ou refusée — hors du circuit dédié
    (_proposer_formation_bord)."""

    def setUp(self):
        self.ship_a, self.service_a, self.sector_a, self.section_a = _construire_bord("GAPPRE_A")
        self.ship_b, self.service_b, self.sector_b, self.section_b = _construire_bord("GAPPRE_B")
        self.chef_secteur_a = User.objects.create_user(username="chef_secteur_gappre_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_a, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_a},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord prérequis en attente", gere_par_le_bord=True,
            statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur_a, updated_by=self.chef_secteur_a,
        )
        self.chef_section_b = User.objects.create_user(username="chef_section_gappre_b", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section_b, defaults={"role": "CHEF_SECTION", "section": self.section_b},
        )

    def _tenter_edition(self):
        self.client.login(username="chef_section_gappre_b", password="pass")
        return self.client.post("/formations/", {
            "action": "update_prerequisites", "pk": self.course.id, "category": "Détournement",
        })

    def test_edition_refusee_si_formation_en_attente(self):
        r = self._tenter_edition()
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.category, "")

    def test_edition_refusee_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter_edition()
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.category, "")


class FuiteStatutValidationCandidatureOrganismeTests(TestCase):
    """Même non-régression que ci-dessus, pour action=selectionner_candidature
    et action=refuser_candidature_organisme (Circuit B — deux points oubliés
    lors de la correction des 5 autres, signalés dans une tâche de
    durcissement défensif dédiée : la formation peut être repassée en attente
    ou refusée entre la TRANSMISSION de la candidature et son traitement par
    l'organisme)."""

    def setUp(self):
        self.ecole = Ship.objects.create(name="École Gap Organisme", code="GAPORGE", type_unite=Ship.TypeUnite.ECOLE)
        self.ship, self.service, self.sector, self.section = _construire_bord("GAPORGB")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_gaporg", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.course = TrainingCourse.objects.create(
            title="Formation bord candidature organisme", gere_par_le_bord=True, statut_validation="ACTIVE",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )
        self.referent = User.objects.create_user(username="referent_gaporg", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent, defaults={"role": "EQUIPIER", "ship": self.ecole},
        )
        ReferentFormation.objects.create(course=self.course, ship=self.ecole, user=self.referent)
        self.marin = User.objects.create_user(username="marin_gaporg", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.candidature = CandidatureFormation.objects.create(
            course=self.course, marin=self.marin, statut="TRANSMITTED", created_by=self.marin,
        )

    def _tenter(self, action):
        self.client.login(username="referent_gaporg", password="pass")
        return self.client.post("/formations/", {"action": action, "candidature_id": self.candidature.id})

    def test_selection_refusee_si_formation_repassee_en_attente(self):
        self.course.statut_validation = "WAITING_VALIDATION"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter("selectionner_candidature")
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "TRANSMITTED")

    def test_selection_refusee_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter("selectionner_candidature")
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "TRANSMITTED")

    def test_refus_organisme_refuse_si_formation_repassee_en_attente(self):
        self.course.statut_validation = "WAITING_VALIDATION"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter("refuser_candidature_organisme")
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "TRANSMITTED")

    def test_refus_organisme_refuse_si_formation_refusee(self):
        self.course.statut_validation = "REFUSED"
        self.course.save(update_fields=["statut_validation"])
        r = self._tenter("refuser_candidature_organisme")
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "TRANSMITTED")
