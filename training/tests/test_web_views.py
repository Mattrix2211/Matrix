"""Tests de la page web « Formations » : liste + formulaire de validation.

Vérifie que la validation d'une formation (création d'un TrainingRecord)
est accessible depuis l'interface web, réservée aux chefs (CHEF_SECTION et
au-dessus, même seuil que la création via l'API), et calcule bien la date
d'expiration via TrainingRecord.compute_expiry.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse, TrainingRecord


class FormationsWebViewsTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T", code="T")
        self.service = Service.objects.create(ship=self.navire, name="Service T")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T")

        self.course = TrainingCourse.objects.create(
            sector=self.secteur, title="Sécurité incendie", validity_days=365,
        )

        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur)

        self.chef = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.liste_url = reverse("formations")
        self.valider_url = reverse("formation-valider")

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.liste_url)
        self.assertEqual(response.status_code, 302)

    def test_equipier_voit_la_liste_sans_bouton_de_validation(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.liste_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["peut_valider"])
        self.assertNotIn("Valider une formation", response.content.decode())

    def test_equipier_ne_peut_pas_valider_une_formation(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.equipier.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-10",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TrainingRecord.objects.exists())

    def test_chef_peut_valider_une_formation_et_lexpiration_est_calculee(self):
        self.client.login(username="chef", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.equipier.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-10",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        record = TrainingRecord.objects.get(user=self.equipier, course=self.course)
        self.assertEqual(record.completed_at.isoformat(), "2026-01-10")
        self.assertEqual(record.expires_at.isoformat(), "2027-01-10")
        self.assertEqual(record.validated_by, self.chef)

    def test_champs_obligatoires_sans_creation(self):
        self.client.login(username="chef", password="pass")
        response = self.client.post(self.valider_url, {"marin_id": self.equipier.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TrainingRecord.objects.exists())

    def test_formation_validee_apparait_dans_la_liste(self):
        TrainingRecord.objects.create(
            user=self.equipier, course=self.course,
            completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=365),
            validated_by=self.chef,
        )
        self.client.login(username="chef", password="pass")
        response = self.client.get(self.liste_url)
        courses = list(response.context["courses"])
        self.assertEqual(courses[0].nb_a_jour, 1)


class FormationsPerimetreSectionTests(TestCase):
    """TrainingCourse n'a qu'un champ ``sector`` (pas de champ ``section``) :
    un chef scope au niveau section (profile.section renseigné,
    profile.sector non renseigné, cas normal de ce rôle) ne doit voir et ne
    doit pouvoir valider que les formations de son propre secteur, pas
    celles des autres secteurs du navire."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T", code="T")
        self.service = Service.objects.create(ship=self.navire, name="Service T")

        self.secteur_a = Sector.objects.create(service=self.service, name="Secteur A")
        self.section_a = Section.objects.create(sector=self.secteur_a, name="Section A1")
        self.formation_a = TrainingCourse.objects.create(
            sector=self.secteur_a, title="Formation secteur A", validity_days=365,
        )

        self.secteur_b = Sector.objects.create(service=self.service, name="Secteur B")
        self.formation_b = TrainingCourse.objects.create(
            sector=self.secteur_b, title="Formation secteur B", validity_days=365,
        )

        # Chef de section scope à la section A1 (donc au secteur A), pas de
        # profile.sector renseigné : configuration normale pour ce rôle.
        self.chef_section = User.objects.create_user(username="chef_section", password="pass")
        UserProfile.objects.filter(user=self.chef_section).update(
            role="CHEF_SECTION", section=self.section_a,
        )

        self.marin_a = User.objects.create_user(username="marin_a", password="pass")
        UserProfile.objects.filter(user=self.marin_a).update(role="EQUIPIER", section=self.section_a)

        self.liste_url = reverse("formations")
        self.valider_url = reverse("formation-valider")

    def test_la_liste_ne_montre_que_les_formations_du_secteur_de_la_section(self):
        self.client.login(username="chef_section", password="pass")
        response = self.client.get(self.liste_url)
        courses = list(response.context["courses"])
        self.assertEqual(courses, [self.formation_a])

    def test_impossible_de_valider_une_formation_dun_autre_secteur(self):
        self.client.login(username="chef_section", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.marin_a.id,
            "course_id": self.formation_b.id,
            "completed_at": "2026-01-10",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TrainingRecord.objects.exists())

    def test_validation_dune_formation_du_bon_secteur_fonctionne(self):
        self.client.login(username="chef_section", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.marin_a.id,
            "course_id": self.formation_a.id,
            "completed_at": "2026-01-10",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            TrainingRecord.objects.filter(user=self.marin_a, course=self.formation_a).exists()
        )


class FormationsPerimetreServiceEtNavireTests(TestCase):
    """Non-régression : filtres_perimetre_formation() doit résoudre TOUS les
    niveaux de périmètre vers des filtres compatibles avec le champ
    ``sector`` de TrainingCourse, pas seulement le niveau section.

    Avant correction, un utilisateur scope au niveau service ou navire
    provoquait un plantage serveur (code 500, champ ``service`` ou ``ship``
    inexistant sur TrainingCourse) lors de la validation, et une fuite de
    périmètre côté liste (le filtre __in généré n'était pas appliqué par
    ScopedQuerySetMixin, exposant tout le navire)."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T", code="T")

        self.service_1 = Service.objects.create(ship=self.navire, name="Service 1")
        self.secteur_a = Sector.objects.create(service=self.service_1, name="Secteur A")
        self.secteur_b = Sector.objects.create(service=self.service_1, name="Secteur B")

        self.service_2 = Service.objects.create(ship=self.navire, name="Service 2")
        self.secteur_c = Sector.objects.create(service=self.service_2, name="Secteur C")

        self.formation_a = TrainingCourse.objects.create(
            sector=self.secteur_a, title="Formation secteur A", validity_days=365,
        )
        self.formation_b = TrainingCourse.objects.create(
            sector=self.secteur_b, title="Formation secteur B", validity_days=365,
        )
        self.formation_c = TrainingCourse.objects.create(
            sector=self.secteur_c, title="Formation secteur C", validity_days=365,
        )

        self.chef_secteur = User.objects.create_user(username="chef_secteur", password="pass")
        UserProfile.objects.filter(user=self.chef_secteur).update(role="CHEF_SECTEUR", sector=self.secteur_a)

        self.chef_service = User.objects.create_user(username="chef_service", password="pass")
        UserProfile.objects.filter(user=self.chef_service).update(role="CHEF_SERVICE", service=self.service_1)

        self.etat_major = User.objects.create_user(username="etat_major", password="pass")
        UserProfile.objects.filter(user=self.etat_major).update(role="ETAT_MAJOR", ship=self.navire)

        self.marin = User.objects.create_user(username="marin", password="pass")
        UserProfile.objects.filter(user=self.marin).update(role="EQUIPIER", sector=self.secteur_a)

        self.liste_url = reverse("formations")
        self.valider_url = reverse("formation-valider")

    def test_chef_secteur_ne_voit_que_les_formations_de_son_secteur(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.get(self.liste_url)
        courses = list(response.context["courses"])
        self.assertEqual(courses, [self.formation_a])

    def test_chef_secteur_ne_peut_pas_valider_une_formation_dun_autre_secteur(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.marin.id,
            "course_id": self.formation_b.id,
            "completed_at": "2026-01-10",
        })
        self.assertEqual(response.status_code, 403)

    def test_chef_service_voit_les_formations_des_deux_secteurs_de_son_service(self):
        self.client.login(username="chef_service", password="pass")
        response = self.client.get(self.liste_url)
        courses = list(response.context["courses"])
        self.assertCountEqual(courses, [self.formation_a, self.formation_b])
        self.assertNotIn(self.formation_c, courses)

    def test_chef_service_peut_valider_une_formation_dun_secteur_de_son_service(self):
        self.client.login(username="chef_service", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.marin.id,
            "course_id": self.formation_b.id,
            "completed_at": "2026-01-10",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            TrainingRecord.objects.filter(user=self.marin, course=self.formation_b).exists()
        )

    def test_chef_service_ne_peut_pas_valider_une_formation_dun_autre_service(self):
        self.client.login(username="chef_service", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.marin.id,
            "course_id": self.formation_c.id,
            "completed_at": "2026-01-10",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TrainingRecord.objects.exists())

    def test_etat_major_voit_toutes_les_formations_du_navire(self):
        self.client.login(username="etat_major", password="pass")
        response = self.client.get(self.liste_url)
        courses = list(response.context["courses"])
        self.assertCountEqual(courses, [self.formation_a, self.formation_b, self.formation_c])

    def test_etat_major_peut_valider_nimporte_quelle_formation_du_navire_sans_erreur(self):
        self.client.login(username="etat_major", password="pass")
        response = self.client.post(self.valider_url, {
            "marin_id": self.marin.id,
            "course_id": self.formation_c.id,
            "completed_at": "2026-01-10",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            TrainingRecord.objects.filter(user=self.marin, course=self.formation_c).exists()
        )
