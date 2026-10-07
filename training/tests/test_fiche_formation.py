"""Catalogue en tuiles et fiche formation : états personnels, action principale
selon le droit réel d'agir, lecture seule à terre, discussion."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Ship
from threads.utils import commentaires_de
from training.models import TrainingCourse, TrainingRecord, TrainingSession


def _marin(nom, role="EQUIPIER", **profil):
    u = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=u, defaults={"role": role, **profil})
    return u


class CatalogueTuilesTests(TestCase):
    def setUp(self):
        self.marin = _marin("marin_cat")
        self.client.login(username="marin_cat", password="pass")
        self.a_jour = TrainingCourse.objects.create(title="Incendie N1", category="Sécurité")
        self.expiree = TrainingCourse.objects.create(title="Levage", category="Sécurité")
        self.libre = TrainingCourse.objects.create(title="Secourisme")
        today = timezone.localdate()
        TrainingRecord.objects.create(user=self.marin, course=self.a_jour, completed_at=today, expires_at=today + timedelta(days=300))
        TrainingRecord.objects.create(user=self.marin, course=self.expiree, completed_at=today - timedelta(days=400), expires_at=today - timedelta(days=5))

    def test_etats_personnels_et_groupes(self):
        r = self.client.get("/formations/")
        etats = {f.title: f.mon_etat_libelle for f in r.context["formations"]}
        self.assertEqual(etats, {"Incendie N1": "À jour", "Levage": "Expirée", "Secourisme": "Non suivie"})
        noms = [nom for nom, _ in r.context["groupes_formations"]]
        self.assertEqual(noms, ["Sécurité", "Non catégorisées"])
        self.assertEqual(r.context["synthese_personnelle"]["taux"], 33)
        self.assertContains(r, reverse("formation-detail", args=[self.a_jour.pk]))

    def test_catalogue_vide(self):
        TrainingCourse.objects.all().delete()
        self.assertContains(self.client.get("/formations/"), "Le catalogue est vide")


class FicheFormationTests(TestCase):
    def setUp(self):
        self.course = TrainingCourse.objects.create(title="Incendie N1")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=5,
        )
        self.marin = _marin("marin_fiche")

    def test_action_principale_reserver(self):
        self.client.login(username="marin_fiche", password="pass")
        r = self.client.get(reverse("formation-detail", args=[self.course.pk]))
        self.assertContains(r, "Réserver une place")
        self.assertContains(r, f'id="reserver-{self.session.id}"')

    def test_prerequis_manquant_pas_de_reservation(self):
        prerequis = TrainingCourse.objects.create(title="Base")
        self.course.prerequisites.add(prerequis)
        self.client.login(username="marin_fiche", password="pass")
        r = self.client.get(reverse("formation-detail", args=[self.course.pk]))
        self.assertNotContains(r, f'id="reserver-{self.session.id}"')
        self.assertContains(r, "Prérequis à valider")

    def test_action_validation_pour_le_valideur(self):
        _marin("cdt_fiche", role="COMMANDANT")
        self.session.delete()
        self.client.login(username="cdt_fiche", password="pass")
        r = self.client.get(reverse("formation-detail", args=[self.course.pk]))
        self.assertContains(r, "Valider une formation")

    def test_formation_inconnue_ou_en_attente(self):
        self.client.login(username="marin_fiche", password="pass")
        self.assertEqual(self.client.get("/formations/99999/").status_code, 404)
        bord = TrainingCourse.objects.create(title="Bord", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION")
        self.assertEqual(self.client.get(reverse("formation-detail", args=[bord.pk])).status_code, 404)

    def test_lecture_seule_a_terre(self):
        navire = Ship.objects.create(name="Double", code="DBL", double_equipage=True, equipage_a_bord="A")
        _marin("terre", ship=navire, equipage="B")
        self.client.login(username="terre", password="pass")
        r = self.client.get(reverse("formation-detail", args=[self.course.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Réserver une place")
        self.assertNotContains(r, 'name="action"')

    def test_discussion(self):
        self.client.login(username="marin_fiche", password="pass")
        r = self.client.post(reverse("formation-commentaire", args=[self.course.pk]), {"body": "Question"})
        self.assertRedirects(r, reverse("formation-detail", args=[self.course.pk]))
        self.assertEqual([m.body for m in commentaires_de(self.course)], ["Question"])
