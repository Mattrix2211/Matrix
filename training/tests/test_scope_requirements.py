"""Vérifie la faille corrigée sur TrainingRequirementViewSet (training/views.py) :
avant correction, AUCUN contrôle de périmètre n'était appliqué — un
CHEF_SECTION pouvait lire les exigences de formation (TrainingRequirement)
de TOUS les navires, et en créer/modifier pour n'IMPORTE QUEL navire/
service/secteur/section de la flotte en le précisant simplement dans le
payload. Le nouveau TrainingRequirementPermission réutilise
resoudre_affectation_dans_perimetre (matrix/core/scopes.py) pour vérifier
que le rattachement demandé appartient bien au navire de l'appelant."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship
from training.models import TrainingCourse, TrainingRequirement


class ScopeTrainingRequirementTests(TestCase):
    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire Exigence A", code="EXA")
        self.ship_b = Ship.objects.create(name="Navire Exigence B", code="EXB")
        self.course = TrainingCourse.objects.create(title="Sécurité incendie niveau 1")

        self.requirement_a = TrainingRequirement.objects.create(
            course=self.course, applies_to_role="EQUIPIER", applies_to_ship=self.ship_a
        )
        self.requirement_b = TrainingRequirement.objects.create(
            course=self.course, applies_to_role="EQUIPIER", applies_to_ship=self.ship_b
        )
        self.requirement_flotte = TrainingRequirement.objects.create(
            course=self.course, applies_to_role="COMMANDANT"
        )

        self.chef_a = User.objects.create_user(username="chef_exigence_a", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_a, defaults={"role": "CHEF_SECTION", "ship": self.ship_a})

        self.commandant = User.objects.create_user(username="commandant_exigence", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

        self.client.login(username="chef_exigence_a", password="pass")

    def test_liste_contient_son_navire_et_les_exigences_flotte_entiere_pas_lautre_navire(self):
        r = self.client.get("/api/training/requirements/")
        self.assertEqual(r.status_code, 200)
        ids = {req["id"] for req in r.json()}
        self.assertIn(self.requirement_a.id, ids)
        self.assertIn(self.requirement_flotte.id, ids)
        self.assertNotIn(self.requirement_b.id, ids)

    def test_ne_peut_pas_lire_une_exigence_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/training/requirements/{self.requirement_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_ne_peut_pas_modifier_une_exigence_dun_autre_navire(self):
        r = self.client.patch(
            f"/api/training/requirements/{self.requirement_b.id}/",
            data={"required": False},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)
        self.requirement_b.refresh_from_db()
        self.assertTrue(self.requirement_b.required)

    def test_ne_peut_pas_supprimer_une_exigence_dun_autre_navire(self):
        r = self.client.delete(f"/api/training/requirements/{self.requirement_b.id}/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(TrainingRequirement.objects.filter(pk=self.requirement_b.id).exists())

    def test_ne_peut_pas_creer_une_exigence_pour_un_autre_navire(self):
        nombre_avant = TrainingRequirement.objects.filter(applies_to_ship=self.ship_b).count()
        r = self.client.post(
            "/api/training/requirements/",
            # applies_to_role="CHEF_SECTEUR" (distinct de self.requirement_b,
            # déjà "EQUIPIER") pour ne pas confondre une éventuelle création
            # avec la fixture existante lors de la vérification en base.
            data={"course": self.course.id, "applies_to_role": "CHEF_SECTEUR", "applies_to_ship": self.ship_b.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(
            TrainingRequirement.objects.filter(applies_to_ship=self.ship_b).count(), nombre_avant
        )

    def test_ne_peut_pas_creer_une_exigence_flotte_entiere_sans_supervision_globale(self):
        r = self.client.post(
            "/api/training/requirements/",
            data={"course": self.course.id, "applies_to_role": "CHEF_SECTEUR"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403, r.content)

    def test_peut_creer_une_exigence_pour_son_propre_navire(self):
        r = self.client.post(
            "/api/training/requirements/",
            data={"course": self.course.id, "applies_to_role": "CHEF_SECTION", "applies_to_ship": self.ship_a.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_supervision_globale_voit_tout_et_peut_creer_une_exigence_flotte_entiere(self):
        self.client.logout()
        self.client.login(username="commandant_exigence", password="pass")
        r = self.client.get("/api/training/requirements/")
        self.assertEqual(r.status_code, 200)
        ids = {req["id"] for req in r.json()}
        self.assertIn(self.requirement_a.id, ids)
        self.assertIn(self.requirement_b.id, ids)
        self.assertIn(self.requirement_flotte.id, ids)

        r2 = self.client.post(
            "/api/training/requirements/",
            data={"course": self.course.id, "applies_to_role": "CHEF_SERVICE"},
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 201, r2.content)
