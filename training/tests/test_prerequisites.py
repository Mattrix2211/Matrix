"""Tests de l'arbre de compétences : prérequis entre formations (protection
anti-cycle, blocage des validations/inscriptions sans prérequis, calcul des
niveaux de profondeur, état affiché par marin). Formation désormais globale
(cf. tâche Notion « Formation unique et portable entre navires ») : plus de
`sector` sur TrainingCourse."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from training.models import TrainingCourse, TrainingRecord, TrainingSession
from training.services import calculer_carte_competences, calculer_niveaux


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class ProtectionAntiCycleTests(TestCase):
    def setUp(self):
        self.f1 = TrainingCourse.objects.create(title="Habilitation électrique niveau 1")
        self.f2 = TrainingCourse.objects.create(title="Habilitation électrique niveau 2")
        self.f3 = TrainingCourse.objects.create(title="Habilitation électrique niveau 3")

    def test_chaine_de_prerequis_normale_acceptee(self):
        self.f2.prerequisites.set([self.f1])
        self.f3.prerequisites.set([self.f2])
        self.assertEqual(list(self.f2.prerequisites.all()), [self.f1])
        self.assertEqual(list(self.f3.prerequisites.all()), [self.f2])

    def test_formation_ne_peut_pas_etre_son_propre_prerequis(self):
        # transaction.atomic() : le rattachement invalide est refusé à l'intérieur
        # d'un .set() déjà englobé dans une transaction Django (m2m_changed) ; sans
        # cette savepoint explicite, l'exception laisserait la transaction du test
        # dans un état inutilisable pour les requêtes suivantes.
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                self.f1.prerequisites.set([self.f1])
        self.assertEqual(self.f1.prerequisites.count(), 0)

    def test_cycle_indirect_refuse(self):
        # f1 -> f2 -> f3, puis on tente f1 comme prérequis de f3 : boucle.
        self.f2.prerequisites.set([self.f1])
        self.f3.prerequisites.set([self.f2])
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                self.f1.prerequisites.set([self.f3])
        self.assertEqual(self.f1.prerequisites.count(), 0)


class BlocageEnregistrementSansPrerequisTests(TestCase):
    def setUp(self):
        self.base = TrainingCourse.objects.create(title="Sécurité de base", validity_days=365)
        self.avance = TrainingCourse.objects.create(title="Sécurité avancée", validity_days=365)
        self.avance.prerequisites.set([self.base])
        self.marin = User.objects.create_user(username="marin1", password="pass")

    def test_validation_refusee_sans_prerequis(self):
        record = TrainingRecord(
            user=self.marin, course=self.avance,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        with self.assertRaises(ValidationError) as ctx:
            record.full_clean()
        # Message clair en français listant le prérequis manquant.
        self.assertIn("Sécurité de base", str(ctx.exception))

    def test_validation_refusee_si_prerequis_expire(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate() - timedelta(days=400),
            expires_at=timezone.localdate() - timedelta(days=35),
        )
        record = TrainingRecord(
            user=self.marin, course=self.avance,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_validation_acceptee_avec_prerequis_valide(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        record = TrainingRecord(
            user=self.marin, course=self.avance,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        record.full_clean()  # ne doit pas lever d'exception
        record.save()
        self.assertTrue(TrainingRecord.objects.filter(user=self.marin, course=self.avance).exists())

    def test_inscription_a_une_session_refusee_sans_prerequis(self):
        session = TrainingSession.objects.create(
            course=self.avance, scheduled_at=timezone.now() + timedelta(days=10),
        )
        with self.assertRaises(ValidationError) as ctx:
            with transaction.atomic():
                session.attendees.add(self.marin)
        self.assertIn("Sécurité de base", str(ctx.exception))
        self.assertEqual(session.attendees.count(), 0)

    def test_inscription_a_une_session_acceptee_avec_prerequis_valide(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        session = TrainingSession.objects.create(
            course=self.avance, scheduled_at=timezone.now() + timedelta(days=10),
        )
        session.attendees.add(self.marin)
        self.assertEqual(session.attendees.count(), 1)

    def test_validation_sans_prerequis_definis_toujours_acceptee(self):
        record = TrainingRecord(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        record.full_clean()
        record.save()
        self.assertTrue(TrainingRecord.objects.filter(user=self.marin, course=self.base).exists())


class CalculDesNiveauxTests(TestCase):
    def setUp(self):
        self.a = TrainingCourse.objects.create(title="A")
        self.b = TrainingCourse.objects.create(title="B")
        self.c = TrainingCourse.objects.create(title="C")
        self.d = TrainingCourse.objects.create(title="D")
        self.b.prerequisites.set([self.a])
        self.c.prerequisites.set([self.b])
        # D dépend de A et de B : son niveau doit suivre la branche la plus longue (B).
        self.d.prerequisites.set([self.a, self.b])

    def test_formation_sans_prerequis_est_niveau_zero(self):
        niveaux = calculer_niveaux([self.a])
        self.assertEqual(niveaux[self.a.id], 0)

    def test_chaine_lineaire(self):
        niveaux = calculer_niveaux([self.a, self.b, self.c])
        self.assertEqual(niveaux[self.a.id], 0)
        self.assertEqual(niveaux[self.b.id], 1)
        self.assertEqual(niveaux[self.c.id], 2)

    def test_convergence_prend_la_branche_la_plus_profonde(self):
        niveaux = calculer_niveaux([self.a, self.b, self.d])
        self.assertEqual(niveaux[self.d.id], 2)


class EtatsCarteCompetencesTests(TestCase):
    def setUp(self):
        self.f1 = TrainingCourse.objects.create(title="Radar niveau 1")
        self.f2 = TrainingCourse.objects.create(title="Radar niveau 2")
        self.f3 = TrainingCourse.objects.create(title="Radar niveau 3")
        self.f2.prerequisites.set([self.f1])
        self.f3.prerequisites.set([self.f2])
        self.marin = User.objects.create_user(username="marin2", password="pass")

    def test_formation_sans_prerequis_non_validee_est_disponible(self):
        carte = calculer_carte_competences([self.f1], self.marin)
        self.assertEqual(carte[0]["etat"], "DISPONIBLE")

    def test_formation_validee_est_marquee_validee(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.f1,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        carte = calculer_carte_competences([self.f1], self.marin)
        self.assertEqual(carte[0]["etat"], "VALIDE")

    def test_formation_avec_prerequis_non_valide_est_verrouillee(self):
        carte = calculer_carte_competences([self.f2], self.marin)
        self.assertEqual(carte[0]["etat"], "VERROUILLE")

    def test_formation_devient_disponible_une_fois_le_prerequis_valide(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.f1,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        carte = calculer_carte_competences([self.f2], self.marin)
        self.assertEqual(carte[0]["etat"], "DISPONIBLE")

    def test_formation_de_niveau_2_reste_verrouillee_meme_avec_niveau_1_valide(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.f1,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        carte = calculer_carte_competences([self.f3], self.marin)
        self.assertEqual(carte[0]["etat"], "VERROUILLE")


class VueGestionPrerequisTests(TestCase):
    """Catalogue global (T-FORM portabilité) : n'importe quelle formation
    existante peut désormais être choisie comme prérequis, quel que soit le
    navire de son auteur (il n'y a plus de notion de secteur/navire propre à
    une formation)."""

    def setUp(self):
        self.f1 = TrainingCourse.objects.create(title="Amarrage niveau 1")
        self.f2 = TrainingCourse.objects.create(title="Amarrage niveau 2")
        self.autre_formation = TrainingCourse.objects.create(title="Formation d'un autre domaine")

        self.chef = User.objects.create_user(username="chef_form", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION"})
        self.equipier = User.objects.create_user(username="equipier_form", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

    def test_chef_peut_configurer_les_prerequis(self):
        self.client.login(username="chef_form", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.f2.id,
            "prerequisites": [self.f1.id],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(self.f2.prerequisites.all()), [self.f1])

    def test_equipier_ne_peut_pas_configurer_les_prerequis(self):
        self.client.login(username="equipier_form", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.f2.id,
            "prerequisites": [self.f1.id],
        })
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.f2.prerequisites.count(), 0)

    def test_prerequis_de_nimporte_quelle_formation_du_catalogue_accepte(self):
        # Catalogue global : "autre_formation" n'appartient à aucun périmètre
        # particulier, elle reste un candidat prérequis valide.
        self.client.login(username="chef_form", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.f2.id,
            "prerequisites": [self.autre_formation.id],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(self.f2.prerequisites.all()), [self.autre_formation])

    def test_page_arbre_de_competences_accessible(self):
        TrainingRecord.objects.create(
            user=self.chef, course=self.f1,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="chef_form", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Amarrage niveau 1")
        self.assertContains(r, "Validé")
