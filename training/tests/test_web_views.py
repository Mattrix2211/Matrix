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
from org.models import Sector, Service, Ship
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
