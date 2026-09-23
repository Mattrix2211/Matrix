"""Tests de l'extension du journal d'audit transverse (AuditLog) aux actions
de validation sensibles de la formation — jusqu'ici totalement absentes de
tout mécanisme d'audit (ni AuditLog, ni log dédié) — cf. tâche Notion
« Unifier les modèles d'historique/audit (AuditLog générique vs logs ad hoc
par app) » :
- validation qu'un marin a suivi/réussi une formation (TrainingRecord) ;
- validation/refus d'une formation « gérée par un bord » (Circuit C)."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import AuditLog, UserProfile
from org.models import Sector, Section, Service, Ship
from training.models import ReferentFormation, TrainingCourse


class AuditLogValidationFormationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire audit formation", code="NT-AUDF")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.course = TrainingCourse.objects.create(title="Équipier de sécurité incendie", validity_days=365)

        self.chef = User.objects.create_user(username="chef_audit_form", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "sector": self.sector},
        )
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.chef)
        self.marin = User.objects.create_user(username="marin_audit_form", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "sector": self.sector},
        )

    def test_validation_dune_formation_genere_une_entree_daudit_exploitable(self):
        self.client.login(username="chef_audit_form", password="pass")
        self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        entree = AuditLog.objects.get(action="validate_training_record")
        # Acteur (le chef qui valide) et cible (le marin concerné).
        self.assertEqual(entree.actor, self.chef)
        self.assertEqual(entree.target_user, self.marin)
        self.assertIsNotNone(entree.created_at)
        self.assertIn(str(self.course.pk), entree.details)

    def test_validation_refusee_ne_genere_aucune_entree(self):
        equipier_sans_droit = User.objects.create_user(username="equipier_sans_droit_audit", password="pass")
        UserProfile.objects.update_or_create(
            user=equipier_sans_droit, defaults={"role": "EQUIPIER", "sector": self.sector},
        )
        self.client.login(username="equipier_sans_droit_audit", password="pass")
        self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertFalse(AuditLog.objects.filter(action="validate_training_record").exists())


class AuditLogCircuitCFormationBordTests(TestCase):
    """Circuit C — validation/refus d'une formation « gérée par le bord »."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire audit circuit C", code="NT-AUDC")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")
        self.section = Section.objects.create(sector=self.sector, name="Section audit")

        self.chef_secteur = User.objects.create_user(username="chef_secteur_audit_c", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.chef_service = User.objects.create_user(username="chef_service_audit_c", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "service": self.service},
        )
        self.course = TrainingCourse.objects.create(
            title="Habilitation bord audit", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )

    def test_validation_circuit_c_genere_une_entree_daudit(self):
        self.client.login(username="chef_service_audit_c", password="pass")
        self.client.post("/formations/", {"action": "valider_formation_bord", "pk": self.course.id})
        entree = AuditLog.objects.get(action="validate_training_course_bord")
        self.assertEqual(entree.actor, self.chef_service)
        self.assertEqual(entree.target_user, self.chef_secteur)
        self.assertIn(self.course.title, entree.details)

    def test_refus_circuit_c_genere_une_entree_daudit(self):
        self.client.login(username="chef_service_audit_c", password="pass")
        self.client.post("/formations/", {"action": "refuser_formation_bord", "pk": self.course.id})
        entree = AuditLog.objects.get(action="refuse_training_course_bord")
        self.assertEqual(entree.actor, self.chef_service)
        self.assertEqual(entree.target_user, self.chef_secteur)
