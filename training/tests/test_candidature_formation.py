"""Tests du Circuit B — Candidature individuelle à un stage (sélection
ASCENDANTE) : un marin dépose lui-même sa candidature sur une formation, sa
hiérarchie (CHEF_SECTION+ dont le périmètre le couvre, cf.
filtres_perimetre_marin) ET un personnel BRH désigné pour son navire
(PersonnelBRH) valident indépendamment, dans n'importe quel ordre. Dès que
les DEUX validations sont réunies, le statut passe automatiquement à
TRANSMITTED (jamais avant, une seule validation ne suffit pas) — sans action
manuelle de transmission. L'organisme de formation (référent de la formation
POUR SON PROPRE NAVIRE, ou COMMANDANT+, cf. peut_valider_formation, réutilisé
tel quel) sélectionne ou refuse ensuite la candidature transmise."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from training.models import CandidatureFormation, PersonnelBRH, TrainingCourse


def _construire_bord(prefixe):
    """Construit une hiérarchie Navire > Service > Secteur > Section complète,
    pour disposer d'un navire résolvable via training.models.navire_de à
    partir de la section (cas le plus courant d'un équipier) — même helper
    que training/tests/test_demande_places.py."""
    ship = Ship.objects.create(name=f"Navire {prefixe}", code=prefixe[:8])
    service = Service.objects.create(ship=ship, name=f"Service {prefixe}")
    sector = Sector.objects.create(service=service, name=f"Secteur {prefixe}")
    section = Section.objects.create(sector=sector, name=f"Section {prefixe}")
    return ship, service, sector, section


class DepotCandidatureTests(TestCase):
    """N'importe quel marin connecté peut déposer sa propre candidature sur
    une formation du catalogue."""

    def setUp(self):
        self.ship, _, self.sector, self.section = _construire_bord("CAND")
        self.course = TrainingCourse.objects.create(title="Stage Plongée")
        self.marin = User.objects.create_user(username="marin_candidat", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )

    def test_depot_reussi(self):
        self.client.login(username="marin_candidat", password="pass")
        r = self.client.post("/formations/", {
            "action": "candidater_formation",
            "course_id": self.course.id,
        })
        self.assertEqual(r.status_code, 302)
        candidature = CandidatureFormation.objects.get(course=self.course, marin=self.marin)
        self.assertEqual(candidature.statut, "PENDING_APPROVAL")
        self.assertEqual(candidature.created_by, self.marin)
        self.assertIsNone(candidature.hierarchie_validee_par)
        self.assertIsNone(candidature.brh_validee_par)

    def test_double_depot_bloque(self):
        CandidatureFormation.objects.create(course=self.course, marin=self.marin, created_by=self.marin)
        self.client.login(username="marin_candidat", password="pass")
        self.client.post("/formations/", {"action": "candidater_formation", "course_id": self.course.id})
        self.assertEqual(CandidatureFormation.objects.filter(course=self.course, marin=self.marin).count(), 1)


class ValidationHierarchieTests(TestCase):
    """Validation de la candidature par la hiérarchie du candidat
    (CHEF_SECTION+, borné à filtres_perimetre_marin)."""

    def setUp(self):
        self.ship, _, self.sector, self.section = _construire_bord("HIER")
        self.course = TrainingCourse.objects.create(title="Stage Hiérarchie")
        self.marin = User.objects.create_user(username="marin_hier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.chef = User.objects.create_user(username="chef_section_hier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "section": self.section},
        )
        self.candidature = CandidatureFormation.objects.create(
            course=self.course, marin=self.marin, created_by=self.marin,
        )

    def test_validation_dans_le_perimetre(self):
        self.client.login(username="chef_section_hier", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_candidature_hierarchie",
            "candidature_id": self.candidature.id,
        })
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.hierarchie_validee_par, self.chef)
        self.assertIsNotNone(self.candidature.date_validation_hierarchie)
        # Une seule des deux validations : le statut ne bascule pas encore.
        self.assertEqual(self.candidature.statut, "PENDING_APPROVAL")

    def test_refus_hors_perimetre(self):
        autre_ship, _, autre_sector, autre_section = _construire_bord("HORS")
        chef_hors_perimetre = User.objects.create_user(username="chef_hors_perimetre", password="pass")
        UserProfile.objects.update_or_create(
            user=chef_hors_perimetre, defaults={"role": "CHEF_SECTION", "section": autre_section},
        )
        self.client.login(username="chef_hors_perimetre", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_candidature_hierarchie",
            "candidature_id": self.candidature.id,
        })
        self.assertEqual(r.status_code, 403)
        self.candidature.refresh_from_db()
        self.assertIsNone(self.candidature.hierarchie_validee_par)

    def test_refus_par_la_hierarchie(self):
        self.client.login(username="chef_section_hier", password="pass")
        self.client.post("/formations/", {
            "action": "refuser_candidature_hierarchie",
            "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "REJECTED_HIERARCHIE")
        notif = Notification.objects.filter(user=self.marin).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, "warning")
        self.assertIn("hiérarchie", notif.verb)


class ValidationBRHTests(TestCase):
    """Validation de la candidature par un personnel BRH désigné pour le
    navire du candidat (PersonnelBRH)."""

    def setUp(self):
        self.ship, _, self.sector, self.section = _construire_bord("BRH")
        self.course = TrainingCourse.objects.create(title="Stage BRH")
        self.marin = User.objects.create_user(username="marin_brh", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.brh = User.objects.create_user(username="personnel_brh", password="pass")
        UserProfile.objects.update_or_create(user=self.brh, defaults={"role": "EQUIPIER", "ship": self.ship})
        PersonnelBRH.objects.create(ship=self.ship, user=self.brh)
        self.non_brh = User.objects.create_user(username="non_brh", password="pass")
        UserProfile.objects.update_or_create(user=self.non_brh, defaults={"role": "CHEF_SERVICE", "ship": self.ship})
        self.candidature = CandidatureFormation.objects.create(
            course=self.course, marin=self.marin, created_by=self.marin,
        )

    def test_validation_par_brh_designe(self):
        self.client.login(username="personnel_brh", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_candidature_brh",
            "candidature_id": self.candidature.id,
        })
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.brh_validee_par, self.brh)
        self.assertIsNotNone(self.candidature.date_validation_brh)
        self.assertEqual(self.candidature.statut, "PENDING_APPROVAL")

    def test_refus_non_designe(self):
        self.client.login(username="non_brh", password="pass")
        r = self.client.post("/formations/", {
            "action": "valider_candidature_brh",
            "candidature_id": self.candidature.id,
        })
        self.assertEqual(r.status_code, 403)
        self.candidature.refresh_from_db()
        self.assertIsNone(self.candidature.brh_validee_par)

    def test_refus_par_le_brh(self):
        self.client.login(username="personnel_brh", password="pass")
        self.client.post("/formations/", {
            "action": "refuser_candidature_brh",
            "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "REJECTED_BRH")
        notif = Notification.objects.filter(user=self.marin).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, "warning")
        self.assertIn("BRH", notif.verb)


class DoubleValidationTransmissionTests(TestCase):
    """La candidature passe automatiquement à TRANSMITTED dès que les DEUX
    validations (hiérarchie et BRH) sont réunies, quel que soit l'ordre —
    jamais avant, une seule des deux ne suffit pas."""

    def setUp(self):
        self.ship, _, self.sector, self.section = _construire_bord("DBL")
        self.course = TrainingCourse.objects.create(title="Stage Double Validation")
        self.marin = User.objects.create_user(username="marin_double", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.chef = User.objects.create_user(username="chef_double", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "section": self.section},
        )
        self.brh = User.objects.create_user(username="brh_double", password="pass")
        UserProfile.objects.update_or_create(user=self.brh, defaults={"role": "EQUIPIER", "ship": self.ship})
        PersonnelBRH.objects.create(ship=self.ship, user=self.brh)
        self.candidature = CandidatureFormation.objects.create(
            course=self.course, marin=self.marin, created_by=self.marin,
        )

    def test_hierarchie_puis_brh_transmet(self):
        self.client.login(username="chef_double", password="pass")
        self.client.post("/formations/", {
            "action": "valider_candidature_hierarchie", "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "PENDING_APPROVAL")
        self.client.logout()
        self.client.login(username="brh_double", password="pass")
        self.client.post("/formations/", {
            "action": "valider_candidature_brh", "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "TRANSMITTED")

    def test_brh_puis_hierarchie_transmet(self):
        self.client.login(username="brh_double", password="pass")
        self.client.post("/formations/", {
            "action": "valider_candidature_brh", "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "PENDING_APPROVAL")
        self.client.logout()
        self.client.login(username="chef_double", password="pass")
        self.client.post("/formations/", {
            "action": "valider_candidature_hierarchie", "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "TRANSMITTED")

    def test_notification_de_transmission_envoyee_une_fois_les_deux_reunies(self):
        self.client.login(username="chef_double", password="pass")
        self.client.post("/formations/", {
            "action": "valider_candidature_hierarchie", "candidature_id": self.candidature.id,
        })
        self.assertFalse(Notification.objects.filter(user=self.marin, verb__icontains="transmise").exists())
        self.client.logout()
        self.client.login(username="brh_double", password="pass")
        self.client.post("/formations/", {
            "action": "valider_candidature_brh", "candidature_id": self.candidature.id,
        })
        notif = Notification.objects.filter(user=self.marin, verb__icontains="transmise").first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, "info")


class SelectionOrganismeTests(TestCase):
    """Sélection/refus par l'organisme de formation (référent de la
    formation POUR SON PROPRE NAVIRE, ou COMMANDANT+) d'une candidature déjà
    TRANSMITTED."""

    def setUp(self):
        self.ecole = Ship.objects.create(
            name="École Plongée", code="ECOLEB", type_unite=Ship.TypeUnite.ECOLE,
        )
        self.ship, _, self.sector, self.section = _construire_bord("ORGB")
        self.course = TrainingCourse.objects.create(title="Stage Organisme")
        self.marin = User.objects.create_user(username="marin_organisme", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.referent = User.objects.create_user(username="referent_organisme", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent, defaults={"role": "EQUIPIER", "ship": self.ecole},
        )
        from training.models import ReferentFormation
        ReferentFormation.objects.create(course=self.course, ship=self.ecole, user=self.referent)
        self.candidature = CandidatureFormation.objects.create(
            course=self.course, marin=self.marin, created_by=self.marin, statut="TRANSMITTED",
        )

    def test_selection_par_le_referent(self):
        self.client.login(username="referent_organisme", password="pass")
        r = self.client.post("/formations/", {
            "action": "selectionner_candidature",
            "candidature_id": self.candidature.id,
        })
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "SELECTED")
        notif = Notification.objects.filter(user=self.marin).first()
        self.assertIsNotNone(notif)
        self.assertIn("sélectionné", notif.verb)

    def test_refus_par_le_referent(self):
        self.client.login(username="referent_organisme", password="pass")
        r = self.client.post("/formations/", {
            "action": "refuser_candidature_organisme",
            "candidature_id": self.candidature.id,
        })
        self.assertEqual(r.status_code, 302)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "REJECTED_ORGANISME")
        notif = Notification.objects.filter(user=self.marin).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, "warning")

    def test_selection_avant_transmission_impossible(self):
        self.candidature.statut = "PENDING_APPROVAL"
        self.candidature.save(update_fields=["statut"])
        self.client.login(username="referent_organisme", password="pass")
        self.client.post("/formations/", {
            "action": "selectionner_candidature",
            "candidature_id": self.candidature.id,
        })
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, "PENDING_APPROVAL")


class MonProfilCandidaturesTests(TestCase):
    """Le marin voit le statut de ses propres candidatures sur « Mon
    profil » (accounts/web_views.py::MonProfilView)."""

    def setUp(self):
        self.ship, _, self.sector, self.section = _construire_bord("PROFB")
        self.course = TrainingCourse.objects.create(title="Stage Mon Profil")
        self.marin = User.objects.create_user(username="marin_monprofil", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "section": self.section},
        )
        self.candidature = CandidatureFormation.objects.create(
            course=self.course, marin=self.marin, created_by=self.marin,
        )

    def test_affichage_de_ma_candidature(self):
        self.client.login(username="marin_monprofil", password="pass")
        r = self.client.get("/users/profil/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.candidature, list(r.context["mes_candidatures"]))
        self.assertContains(r, "Stage Mon Profil")


class GestionPersonnelBRHTests(TestCase):
    """Désignation/retrait d'un PersonnelBRH par navire, réservé à
    COMMANDANT+ (même seuil que la désignation du référent formation
    navire)."""

    def setUp(self):
        self.ship, _, self.sector, self.section = _construire_bord("GESTBRH")
        self.commandant = User.objects.create_user(username="commandant_brh", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant, defaults={"role": "COMMANDANT", "ship": self.ship},
        )
        self.candidat_brh = User.objects.create_user(username="candidat_brh", password="pass")
        UserProfile.objects.update_or_create(
            user=self.candidat_brh, defaults={"role": "EQUIPIER", "ship": self.ship},
        )
        self.chef_service = User.objects.create_user(username="chef_service_brh", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "ship": self.ship},
        )

    def test_designation_par_commandant(self):
        self.client.login(username="commandant_brh", password="pass")
        r = self.client.post("/formations/", {"action": "set_brh", "brh_id": self.candidat_brh.id})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PersonnelBRH.objects.filter(ship=self.ship, user=self.candidat_brh).exists())
        notif = Notification.objects.filter(user=self.candidat_brh).first()
        self.assertIsNotNone(notif)

    def test_refus_pour_role_inferieur(self):
        self.client.login(username="chef_service_brh", password="pass")
        r = self.client.post("/formations/", {"action": "set_brh", "brh_id": self.candidat_brh.id})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(PersonnelBRH.objects.filter(ship=self.ship, user=self.candidat_brh).exists())

    def test_retrait_par_commandant(self):
        brh = PersonnelBRH.objects.create(ship=self.ship, user=self.candidat_brh)
        self.client.login(username="commandant_brh", password="pass")
        self.client.post("/formations/", {"action": "retirer_brh", "brh_id": brh.id})
        self.assertFalse(PersonnelBRH.objects.filter(pk=brh.pk).exists())
