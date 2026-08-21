"""Tests de l'interface web de validation des formations (ValiderFormationView) :
création d'un TrainingRecord pour un marin par un chef, revalidation du
périmètre côté serveur (formation ET marin ciblés), et affichage correct des
badges À jour/Expirée sur la page /formations/."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse, TrainingRecord


class ValidationFormationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Validation", code="VAL")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.course = TrainingCourse.objects.create(
            sector=self.sector, title="Équipier de sécurité incendie", validity_days=365,
        )

        self.chef = User.objects.create_user(username="chef_validation", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "sector": self.sector},
        )
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

    def test_formation_hors_perimetre_refusee(self):
        autre_navire = Ship.objects.create(name="Autre navire", code="AUT")
        autre_service = Service.objects.create(ship=autre_navire, name="Technique")
        autre_secteur = Sector.objects.create(service=autre_service, name="Électricité")
        autre_formation = TrainingCourse.objects.create(sector=autre_secteur, title="Hors périmètre")

        self.client.login(username="chef_validation", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": autre_formation.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(course=autre_formation).exists())

    def test_marin_hors_perimetre_refuse_meme_si_formation_dans_le_perimetre(self):
        # Le marin ciblé est rattaché à une AUTRE section du même secteur que
        # le chef : la formation est bien dans le périmètre du chef, mais le
        # marin n'y est pas — le POST doit être rejeté malgré tout.
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
        formation_expiree = TrainingCourse.objects.create(sector=self.sector, title="Formation expirée")
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


class PerimetreListeFormationsChefDeSectionTests(TestCase):
    """Un CHEF_SECTION dont le profil est rattaché à une SECTION (pas
    directement au secteur) doit voir les formations du secteur parent —
    régression : TrainingCourse n'a pas de champ "section", donc le mapping
    de périmètre doit résoudre section_id vers le secteur parent plutôt que
    de silencieusement ne matcher aucune formation."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Section", code="SEC")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.section = Section.objects.create(sector=self.sector, name="Section A")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Formation du secteur")

        self.chef_section = User.objects.create_user(username="chef_scope_section", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section, defaults={"role": "CHEF_SECTION", "section": self.section},
        )

    def test_chef_de_section_voit_les_formations_du_secteur_parent(self):
        self.client.login(username="chef_scope_section", password="pass")
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Formation du secteur", titres)
