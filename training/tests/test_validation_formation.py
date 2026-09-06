"""Tests de l'interface web de validation des formations (ValiderFormationView) :
création d'un TrainingRecord pour un marin par un chef, revalidation du
périmètre côté serveur (le marin ciblé — le catalogue de formations, devenu
global, n'a plus de périmètre propre), et affichage correct des badges
À jour/Expirée sur la page /formations/.

Depuis le correctif de sécurité (tâche Notion « Sécurité : la validation de
formation contourne le contrôle par référent (seuil générique CHEF_SECTION+) »),
seul le contrôle par référent (training.models.peut_valider_formation) fait
foi : un chef ne peut valider une formation pour un marin que s'il en est
désigné référent (ou référent formation du navire, ou COMMANDANT+), plus
jamais par le seul effet de son rang — cf. SeuilGeneriqueChefNePermetPlusDeValiderTests
ci-dessous pour la non-régression de ce point précis."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship
from training.models import ReferentFormation, TrainingCourse, TrainingRecord


class ValidationFormationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Validation", code="VAL")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.course = TrainingCourse.objects.create(title="Équipier de sécurité incendie", validity_days=365)

        self.chef = User.objects.create_user(username="chef_validation", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "sector": self.sector},
        )
        # Référent désigné de la formation (depuis le correctif de sécurité,
        # le seul rang CHEF_SECTION ne suffit plus, cf. docstring du module) :
        # sans cette désignation, ce chef ne pourrait plus valider la
        # formation ci-dessous pour un marin, même de son propre périmètre.
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.chef)
        self.marin = User.objects.create_user(username="marin_valide", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "sector": self.sector},
        )
        self.equipier = User.objects.create_user(username="equipier_sans_droit", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "sector": self.sector},
        )

    def test_chef_peut_valider_une_formation_pour_un_marin(self):
        self.client.login(username="chef_validation", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 302)
        record = TrainingRecord.objects.get(user=self.marin, course=self.course)
        self.assertEqual(record.completed_at, date(2026, 1, 15))
        self.assertEqual(record.expires_at, date(2027, 1, 15))
        self.assertEqual(record.validated_by, self.chef)

    def test_equipier_ne_peut_pas_valider(self):
        self.client.login(username="equipier_sans_droit", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_bouton_valider_absent_pour_un_equipier(self):
        self.client.login(username="equipier_sans_droit", password="pass")
        r = self.client.get("/formations/")
        self.assertFalse(r.context["peut_valider"])
        self.assertNotContains(r, "validerFormationModal")

    def test_marin_hors_perimetre_refuse_meme_si_formation_dans_le_catalogue(self):
        # Le marin ciblé est rattaché à une AUTRE section du même secteur que
        # le chef : le catalogue de formations est global (accessible à
        # tous), mais le marin n'est pas dans le périmètre du chef — le POST
        # doit être rejeté malgré tout.
        autre_section = Section.objects.create(sector=self.sector, name="Autre section")
        marin_hors_perimetre = User.objects.create_user(username="marin_autre_section", password="pass")
        UserProfile.objects.update_or_create(
            user=marin_hors_perimetre, defaults={"role": "EQUIPIER", "section": autre_section},
        )
        chef_de_section = User.objects.create_user(username="chef_dune_section", password="pass")
        section_du_chef = Section.objects.create(sector=self.sector, name="Section du chef")
        UserProfile.objects.update_or_create(
            user=chef_de_section, defaults={"role": "CHEF_SECTION", "section": section_du_chef},
        )

        self.client.login(username="chef_dune_section", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": marin_hors_perimetre.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=marin_hors_perimetre).exists())

    def test_badge_a_jour_et_expiree_affiches_correctement(self):
        aujourdhui = date.today()
        TrainingRecord.objects.create(
            user=self.marin, course=self.course,
            completed_at=aujourdhui, expires_at=aujourdhui + timedelta(days=30),
            validated_by=self.chef, created_by=self.chef,
        )
        formation_expiree = TrainingCourse.objects.create(title="Formation expirée")
        marin_expire = User.objects.create_user(username="marin_expire", password="pass")
        UserProfile.objects.update_or_create(
            user=marin_expire, defaults={"role": "EQUIPIER", "sector": self.sector},
        )
        TrainingRecord.objects.create(
            user=marin_expire, course=formation_expiree,
            completed_at=aujourdhui - timedelta(days=400), expires_at=aujourdhui - timedelta(days=35),
            validated_by=self.chef, created_by=self.chef,
        )

        self.client.login(username="chef_validation", password="pass")
        r = self.client.get("/formations/")
        # ctx["aujourdhui"] doit être un objet date (pas une chaîne isoformat),
        # sans quoi la comparaison r.expires_at >= aujourdhui échoue
        # silencieusement dans le template et affiche toujours "Expirée".
        self.assertIsInstance(r.context["aujourdhui"], date)
        self.assertContains(r, "À jour")
        self.assertContains(r, "Expirée")


class SeuilGeneriqueChefNePermetPlusDeValiderTests(TestCase):
    """Non-régression : le seuil générique CHEF_SECTION+ (NIVEAU_REQUIS_VALIDATION)
    ne doit plus, à lui seul, autoriser la validation d'une formation
    (ValiderFormationView) — seul le contrôle par référent
    (training.models.peut_valider_formation) fait foi : référent désigné de
    cette formation précise, référent formation du navire, ou COMMANDANT+.
    Faille corrigée, tâche Notion « Sécurité : la validation de formation
    contourne le contrôle par référent (seuil générique CHEF_SECTION+) »,
    campagne de tests QA du 06/09/2026 (reproduction : un compte CHEF_SECTION
    non référent de la formation TP6 avait pu la valider pour un autre
    marin)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Sécurité Validation", code="SECVAL")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.course = TrainingCourse.objects.create(title="TP6", validity_days=365)

        self.marin = User.objects.create_user(username="marin_tp6", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "sector": self.sector},
        )

        # Trois niveaux de chefs, tous dans le périmètre organisationnel du
        # marin ciblé (même secteur), AUCUN désigné référent de la formation :
        # avant le correctif, leur seul rang suffisait à contourner le
        # contrôle par référent.
        self.chef_section = self._creer_chef("chef_section_non_ref", "CHEF_SECTION")
        self.chef_secteur = self._creer_chef("chef_secteur_non_ref", "CHEF_SECTEUR")
        self.chef_service = self._creer_chef("chef_service_non_ref", "CHEF_SERVICE")

        self.referent = User.objects.create_user(username="referent_tp6", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)

        self.commandant = User.objects.create_user(username="commandant_tp6", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

    def _creer_chef(self, username, role):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "sector": self.sector})
        return user

    def _valider(self, username):
        self.client.login(username=username, password="pass")
        return self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })

    def test_chef_section_non_referent_refuse(self):
        r = self._valider("chef_section_non_ref")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_chef_secteur_non_referent_refuse(self):
        r = self._valider("chef_secteur_non_ref")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_chef_service_non_referent_refuse(self):
        r = self._valider("chef_service_non_ref")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_referent_designe_peut_valider(self):
        r = self._valider("referent_tp6")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_commandant_peut_toujours_valider(self):
        r = self._valider("commandant_tp6")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_bouton_valider_absent_pour_un_chef_non_referent(self):
        # La logique de visibilité du bouton (ctx["peut_valider"]) est
        # explicitement visée par la tâche Notion au même titre que
        # ValiderFormationView : elle ne doit plus s'appuyer sur le seul rang.
        self.client.login(username="chef_section_non_ref", password="pass")
        r = self.client.get("/formations/")
        self.assertFalse(r.context["peut_valider"])


class CatalogueGlobalListeFormationsTests(TestCase):
    """Le catalogue de formations est désormais global (tâche Notion
    « Formation unique et portable entre navires ») : n'importe quel marin
    connecté, quel que soit son rattachement organisationnel, voit
    l'ensemble des formations existantes sur /formations/."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Catalogue", code="CAT")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.section = Section.objects.create(sector=self.sector, name="Section A")
        TrainingCourse.objects.create(title="Formation du catalogue")

        self.chef_section = User.objects.create_user(username="chef_scope_section", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section, defaults={"role": "CHEF_SECTION", "section": self.section},
        )

    def test_marin_scope_section_voit_le_catalogue_complet(self):
        self.client.login(username="chef_scope_section", password="pass")
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Formation du catalogue", titres)
