"""Durcissement de TrainingCourseListView.post contre une valeur non
numérique dans un champ normalement issu d'un <select> HTML (identifiant de
formation, prérequis, référents). Sans validation explicite, ces valeurs
remontaient directement dans un filtre `pk=` ou `pk__in=` Django, qui lève un
ValueError non attrapé (erreur 500) plutôt qu'un refus propre. Inatteignable
via l'interface normale, corrigé par hygiène de sécurité.

Catalogue devenu global (tâche Notion « Formation unique et portable entre
navires ») : les anciens tests de durcissement sur le paramètre "sector" ne
s'appliquent plus (le champ a été retiré) — seuls les identifiants numériques
(pk, prérequis, référents) restent à durcir."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship
from training.models import TrainingCourse


class UpdatePrerequisitesIdentifiantsNonNumeriquesTests(TestCase):
    """action=update_prerequisites avec un pk, des prérequis ou des référents
    non numériques."""

    def setUp(self):
        self.f1 = TrainingCourse.objects.create(title="Extincteur niveau 1")
        self.f2 = TrainingCourse.objects.create(title="Extincteur niveau 2")

        self.ship = Ship.objects.create(name="Navire Durcissement 2", code="DUR2")
        self.chef = User.objects.create_user(username="chef_durcissement", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION", "ship": self.ship})

    def test_pk_non_numerique_refuse_proprement(self):
        self.client.login(username="chef_durcissement", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": "abc",
            "prerequisites": [self.f1.id],
        })
        # Redirect propre (formation introuvable), pas une erreur 500.
        self.assertEqual(r.status_code, 302)

    def test_prerequis_non_numerique_refuse_proprement(self):
        self.client.login(username="chef_durcissement", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.f2.id,
            "prerequisites": ["xyz"],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.f2.prerequisites.count(), 0)

    def test_referent_non_numerique_refuse_proprement(self):
        self.client.login(username="chef_durcissement", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.f2.id,
            "referents": ["xyz"],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.f2.referents.count(), 0)

    def test_pk_numerique_valide_toujours_accepte(self):
        # Aucune régression sur le cas nominal.
        self.client.login(username="chef_durcissement", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": str(self.f2.id),
            "prerequisites": [self.f1.id],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(self.f2.prerequisites.all()), [self.f1])
