"""Tests de la commande de fusion des formations dupliquées entre navires
(training/management/commands/fusionner_formations.py) — étape 2/3 de la
portabilité des formations (cf. tâche Notion « Formation unique et portable
entre navires »).

Le schéma final de Matrix (après la migration 0008) n'a plus les colonnes
legacy que la commande lit en SQL brut pendant la fenêtre de transition entre
les migrations 0007 et 0008 (TrainingCourse.sector_id, table de jonction
referents — cf. note technique en tête de la commande). Chaque test de ce
fichier recrée ponctuellement ces colonnes/table dans la base de test
(SQLite), exactement comme elles existent en production entre ces deux
migrations, pour valider le comportement réel de la commande — nettoyage
automatique par le rollback transactionnel de TestCase entre chaque test,
aucun tearDown explicite nécessaire."""
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from org.models import Sector, Service, Ship
from training.models import (
    ReferentFormation,
    TrainingCourse,
    TrainingRecord,
    TrainingRequirement,
    TrainingSession,
)


def _recreer_colonnes_legacy():
    """Ajoute à la base de test les colonnes/table retirées par la migration
    0008 (sector_id, table de jonction referents), comme elles existent
    réellement en production entre les migrations 0007 et 0008."""
    with connection.cursor() as cur:
        cur.execute("ALTER TABLE training_trainingcourse ADD COLUMN sector_id bigint NULL")
        cur.execute(
            "CREATE TABLE training_trainingcourse_referents ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "trainingcourse_id bigint NOT NULL, "
            "user_id integer NOT NULL)"
        )


class FusionFormationsNonRegressionTests(TestCase):
    """Fusion automatique de deux formations dupliquées (même titre, même
    catégorie, même durée de validité) : réattribution des objets liés, sans
    aucune FK orpheline après coup (cf. tâche Notion, point 9)."""

    def setUp(self):
        _recreer_colonnes_legacy()

        self.ship1 = Ship.objects.create(name="Navire Fusion 1", code="FUS1")
        self.ship2 = Ship.objects.create(name="Navire Fusion 2", code="FUS2")
        service1 = Service.objects.create(ship=self.ship1, name="Technique")
        service2 = Service.objects.create(ship=self.ship2, name="Technique")
        self.sector1 = Sector.objects.create(service=service1, name="Elec")
        self.sector2 = Sector.objects.create(service=service2, name="Elec")

        self.survivant = TrainingCourse.objects.create(title="Doublon fusionné", category="Secu", validity_days=365)
        self.doublon = TrainingCourse.objects.create(title="Doublon fusionné", category="Secu", validity_days=365)

        self.referent = User.objects.create_user(username="fusion_referent", password="pass")

        with connection.cursor() as cur:
            cur.execute(
                "UPDATE training_trainingcourse SET sector_id=%s WHERE id=%s",
                [self.sector1.id, self.survivant.id],
            )
            cur.execute(
                "UPDATE training_trainingcourse SET sector_id=%s WHERE id=%s",
                [self.sector2.id, self.doublon.id],
            )
            cur.execute(
                "INSERT INTO training_trainingcourse_referents (trainingcourse_id, user_id) VALUES (%s, %s)",
                [self.doublon.id, self.referent.id],
            )

        self.session = TrainingSession.objects.create(course=self.doublon, scheduled_at=timezone.now())
        self.record = TrainingRecord.objects.create(
            user=self.referent, course=self.doublon,
            completed_at=timezone.localdate(), expires_at=timezone.localdate(),
        )

    def test_fusion_reattribue_sessions_et_enregistrements_au_survivant(self):
        call_command("fusionner_formations")
        self.session.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(self.session.course_id, self.survivant.id)
        self.assertEqual(self.record.course_id, self.survivant.id)
        self.assertFalse(TrainingCourse.objects.filter(pk=self.doublon.id).exists())

    def test_fusion_convertit_le_referent_et_lexigence_navire(self):
        call_command("fusionner_formations")
        self.assertTrue(
            ReferentFormation.objects.filter(course=self.survivant, ship=self.ship2, user=self.referent).exists()
        )
        self.assertTrue(
            TrainingRequirement.objects.filter(course=self.survivant, applies_to_ship=self.ship1).exists()
        )
        self.assertTrue(
            TrainingRequirement.objects.filter(course=self.survivant, applies_to_ship=self.ship2).exists()
        )

    def test_aucune_fk_orpheline_apres_fusion(self):
        call_command("fusionner_formations")
        with connection.cursor() as cur:
            cur.execute("PRAGMA foreign_key_check")
            violations = cur.fetchall()
        self.assertEqual(violations, [])

    def test_dry_run_ne_modifie_rien(self):
        call_command("fusionner_formations", "--dry-run")
        self.session.refresh_from_db()
        self.assertEqual(self.session.course_id, self.doublon.id)
        self.assertTrue(TrainingCourse.objects.filter(pk=self.doublon.id).exists())
        self.assertEqual(ReferentFormation.objects.count(), 0)
        self.assertEqual(TrainingRequirement.objects.count(), 0)


class FusionFormationsConflitTests(TestCase):
    """Deux formations de même titre mais de catégorie ou durée de validité
    différente ne doivent JAMAIS être fusionnées automatiquement — elles
    restent deux fiches distinctes, chacune quand même convertie
    individuellement (aucune perte de rattachement navire/référent)."""

    def setUp(self):
        _recreer_colonnes_legacy()
        self.ship1 = Ship.objects.create(name="Navire Conflit 1", code="CFL1")
        self.ship2 = Ship.objects.create(name="Navire Conflit 2", code="CFL2")
        service1 = Service.objects.create(ship=self.ship1, name="Technique")
        service2 = Service.objects.create(ship=self.ship2, name="Technique")
        sector1 = Sector.objects.create(service=service1, name="Elec")
        sector2 = Sector.objects.create(service=service2, name="Elec")

        self.c1 = TrainingCourse.objects.create(title="Conflit", category="Secu", validity_days=365)
        self.c2 = TrainingCourse.objects.create(title="Conflit", category="Autre", validity_days=730)

        with connection.cursor() as cur:
            cur.execute("UPDATE training_trainingcourse SET sector_id=%s WHERE id=%s", [sector1.id, self.c1.id])
            cur.execute("UPDATE training_trainingcourse SET sector_id=%s WHERE id=%s", [sector2.id, self.c2.id])

    def test_conflit_non_fusionne(self):
        call_command("fusionner_formations")
        self.assertTrue(TrainingCourse.objects.filter(pk=self.c1.id).exists())
        self.assertTrue(TrainingCourse.objects.filter(pk=self.c2.id).exists())

    def test_conflit_quand_meme_converti_individuellement(self):
        call_command("fusionner_formations")
        self.assertTrue(TrainingRequirement.objects.filter(course=self.c1, applies_to_ship_id=self.ship1.id).exists())
        self.assertTrue(TrainingRequirement.objects.filter(course=self.c2, applies_to_ship_id=self.ship2.id).exists())
