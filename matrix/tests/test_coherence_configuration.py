"""Cohérence multi-processus des seuils de rôle et des modules : une révocation
est vue dès la lecture suivante par tous les processus, par tous les chemins
de modification (version de configuration, matrix/core/config_version.py)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.db.models.signals import pre_save
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from matrix.core.config_version import _contexte, cle_modules, cle_seuils, fermer_contexte, ouvrir_contexte
from matrix.core.modules import module_actif
from matrix.core.role_thresholds import seuil_role
from matrix.core.roles import RoleLevel
from org.models import ModuleActivation, RoleThresholdConfig, Ship, VersionConfiguration

ACTION = "module_gestion"  # défaut : NIVEAU_VISION_COMMANDEMENT (6)


class ProcessusIndependant:
    """Pilote un vrai processus Python/Django, avec son propre cache local."""

    def __init__(self):
        self.processus = subprocess.Popen(
            [sys.executable, "-m", "matrix.tests.processus_config"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=settings.BASE_DIR,
        )

    def __call__(self, nom, *args, en_tache=False):
        self.processus.stdin.write(json.dumps([nom, args, en_tache]) + "\n")
        self.processus.stdin.flush()
        statut, resultat = json.loads(self.processus.stdout.readline())
        if statut != "ok":
            raise AssertionError(resultat)
        return resultat

    def arreter(self):
        self.processus.stdin.write(json.dumps(["arreter", [], False]) + "\n")
        self.processus.stdin.close()
        self.processus.wait(30)
        self.processus.stdout.close()


class DeuxProcessusTests(SimpleTestCase):
    """Preuve de l'anomalie d'origine : A met un seuil en cache, B le relève, A doit le voir."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dossier = tempfile.TemporaryDirectory()
        cls.addClassCleanup(dossier.cleanup)
        env = {
            "DJANGO_SETTINGS_MODULE": "matrix.tests.reglages_deux_processus",
            "MATRIX_DB_FICHIER": str(Path(dossier.name) / "deux_processus.sqlite3"),
            "MATRIX_DB_NOM": str(connection.settings_dict["NAME"]),
        }
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        cls.addClassCleanup(patch.stop)
        cls.a = ProcessusIndependant()
        cls.b = ProcessusIndependant()
        cls.addClassCleanup(cls.a.arreter)
        cls.addClassCleanup(cls.b.arreter)
        cls.b("preparer")

    def setUp(self):
        self.ship_id = self.b("creer_navire")
        self.addCleanup(self.b, "nettoyer", self.ship_id)

    def test_releve_de_seuil_vu_par_l_autre_processus(self):
        self.assertEqual(self.a("lire_seuil", self.ship_id, ACTION), "COMMANDANT_EN_SECOND")
        self.b("ecrire_seuil", self.ship_id, ACTION, "COMMANDANT")
        self.assertEqual(self.b("lire_seuil", self.ship_id, ACTION), "COMMANDANT")
        self.assertEqual(self.a("lire_seuil", self.ship_id, ACTION), "COMMANDANT")

    def test_abaissement_et_revocations_successives(self):
        for nom in ("CHEF_SERVICE", "COMMANDANT", "ADMIN_NAVIRE"):
            self.assertNotEqual(self.a("lire_seuil", self.ship_id, ACTION), nom)
            self.b("ecrire_seuil", self.ship_id, ACTION, nom)
            self.assertEqual(self.a("lire_seuil", self.ship_id, ACTION), nom)

    def test_desactivation_de_module_vue_par_l_autre_processus(self):
        self.assertTrue(self.a("lire_module", self.ship_id, "assets"))
        self.b("basculer_module", self.ship_id, "assets", False)
        self.assertFalse(self.a("lire_module", self.ship_id, "assets"))
        self.b("basculer_module", self.ship_id, "assets", True)
        self.assertTrue(self.a("lire_module", self.ship_id, "assets"))

    def test_worker_celery_simule(self):
        self.assertEqual(self.a("lire_seuil", self.ship_id, ACTION, en_tache=True), "COMMANDANT_EN_SECOND")
        self.b("ecrire_seuil", self.ship_id, ACTION, "COMMANDANT")
        self.b("basculer_module", self.ship_id, "assets", False)
        self.assertEqual(self.a("lire_seuil", self.ship_id, ACTION, en_tache=True), "COMMANDANT")
        self.assertFalse(self.a("lire_module", self.ship_id, "assets", en_tache=True))


@shared_task
def tache_double_lecture(ship_id):
    """Lit le seuil deux fois : le mémo de la tâche fige les versions entre les deux."""
    premier = seuil_role(ACTION, ship_id)
    RoleThresholdConfig.objects.update_or_create(ship_id=ship_id, defaults={"thresholds": {ACTION: "COMMANDANT"}})
    return premier.name, seuil_role(ACTION, ship_id).name


class ContexteTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Contexte", code="CTX")

    def test_une_seule_requete_de_version_par_contexte(self):
        jeton = ouvrir_contexte()
        self.addCleanup(fermer_contexte, jeton)
        seuil_role(ACTION, self.ship.id)  # remplit le cache local
        module_actif("assets", self.ship.id)
        with self.assertNumQueries(0):
            for _ in range(5):
                seuil_role(ACTION, self.ship.id)
                module_actif("assets", self.ship.id)

    def test_hors_contexte_validation_a_chaque_lecture(self):
        seuil_role(ACTION, self.ship.id)
        with self.assertNumQueries(3):
            for _ in range(3):
                seuil_role(ACTION, self.ship.id)

    def test_ecriture_dans_le_contexte_est_vue_immediatement(self):
        jeton = ouvrir_contexte()
        self.addCleanup(fermer_contexte, jeton)
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT_EN_SECOND)
        RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT)

    def test_tache_celery_ouvre_un_contexte_et_voit_ses_ecritures(self):
        self.assertEqual(tache_double_lecture.apply(args=[self.ship.id]).get(), ("COMMANDANT_EN_SECOND", "COMMANDANT"))


class CheminsDeModificationTests(TestCase):
    """Chaque chemin d'écriture doit invalider le cache déjà chauffé du processus."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Chemins", code="CHM")
        self.autre = Ship.objects.create(name="Autre", code="AUT")

    def chauffer(self):
        for ship in (self.ship, self.autre):
            seuil_role(ACTION, ship.id)
            module_actif("assets", ship.id)

    def seuil(self, ship=None):
        return seuil_role(ACTION, (ship or self.ship).id)

    def test_creation_modification_suppression_instance(self):
        self.chauffer()
        config = RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)
        config.thresholds = {ACTION: "ADMIN_NAVIRE"}
        config.save()
        self.assertEqual(self.seuil(), RoleLevel.ADMIN_NAVIRE)
        config.delete()
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT_EN_SECOND)

    def test_queryset_update_bulk_et_suppression(self):
        self.chauffer()
        RoleThresholdConfig.objects.bulk_create([RoleThresholdConfig(ship=self.ship, thresholds={ACTION: "COMMANDANT"})])
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)
        RoleThresholdConfig.objects.filter(ship=self.ship).update(thresholds={ACTION: "ADMIN_NAVIRE"})
        self.assertEqual(self.seuil(), RoleLevel.ADMIN_NAVIRE)
        config = RoleThresholdConfig.objects.get(ship=self.ship)
        config.thresholds = {ACTION: "ETAT_MAJOR"}
        RoleThresholdConfig.objects.bulk_update([config], ["thresholds"])
        self.assertEqual(self.seuil(), RoleLevel.ETAT_MAJOR)
        RoleThresholdConfig.objects.filter(ship=self.ship).delete()
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT_EN_SECOND)

    def test_modules_instance_queryset_et_cascade(self):
        self.chauffer()
        activation = ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        self.assertFalse(module_actif("assets", self.ship.id))
        activation.active = True
        activation.save()
        self.assertTrue(module_actif("assets", self.ship.id))
        ModuleActivation.objects.filter(pk=activation.pk).update(active=False)
        self.assertFalse(module_actif("assets", self.ship.id))
        ModuleActivation.objects.bulk_create([ModuleActivation(ship=self.autre, module="assets", active=False)])
        self.assertFalse(module_actif("assets", self.autre.id))
        self.ship.delete()  # suppression en cascade
        self.assertTrue(module_actif("assets", self.ship.id))

    def test_changement_de_navire_invalide_l_ancien_et_le_nouveau(self):
        config = RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        self.chauffer()
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)
        config.ship = self.autre
        config.save()
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT_EN_SECOND)
        self.assertEqual(self.seuil(self.autre), RoleLevel.COMMANDANT)
        RoleThresholdConfig.objects.filter(pk=config.pk).update(ship=self.ship)
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)
        self.assertEqual(self.seuil(self.autre), RoleLevel.COMMANDANT_EN_SECOND)

    def test_lecteur_intercale_avant_l_ecriture_d_un_changement_de_navire(self):
        # Un lecteur passe entre le pre_save et l'UPDATE : il ne doit pas figer l'ancienne
        # donnée de l'ancien navire sous une version déjà incrémentée.
        config = RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)

        def lecteur(sender, instance, **kwargs):
            self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)  # base encore inchangée

        pre_save.connect(lecteur, sender=RoleThresholdConfig)
        self.addCleanup(pre_save.disconnect, lecteur, sender=RoleThresholdConfig)
        config.ship = self.autre
        config.save()
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT_EN_SECOND)
        self.assertEqual(self.seuil(self.autre), RoleLevel.COMMANDANT)

    def test_bulk_update_avec_changement_de_navire(self):
        config = RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        self.chauffer()
        config.ship = self.autre
        RoleThresholdConfig.objects.bulk_update([config], ["ship"])
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT_EN_SECOND)
        self.assertEqual(self.seuil(self.autre), RoleLevel.COMMANDANT)

    def test_chargement_de_fixture(self):
        self.chauffer()
        fixture = [{
            "model": "org.rolethresholdconfig", "pk": 9001,
            "fields": {
                "ship": self.ship.pk, "thresholds": {ACTION: "COMMANDANT"},
                "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
            },
        }]
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "seuils.json"
            chemin.write_text(json.dumps(fixture), encoding="utf-8")
            call_command("loaddata", str(chemin), verbosity=0)
        self.assertEqual(self.seuil(), RoleLevel.COMMANDANT)

    def test_isolation_entre_navires(self):
        self.chauffer()
        avant = dict(VersionConfiguration.objects.values_list("cle", "valeur"))
        RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        apres = dict(VersionConfiguration.objects.values_list("cle", "valeur"))
        self.assertEqual(apres[cle_seuils(self.ship.id)], 1)
        self.assertEqual(apres[cle_modules(self.ship.id)], 1)
        for cle in (cle_seuils(self.autre.id), cle_modules(self.autre.id), cle_seuils(None)):
            self.assertEqual(apres.get(cle), avant.get(cle))
        self.assertEqual(self.seuil(self.autre), RoleLevel.COMMANDANT_EN_SECOND)
        self.assertTrue(module_actif("assets", self.autre.id))

    def test_incrementation_atomique_et_compteur(self):
        for _ in range(3):
            RoleThresholdConfig.objects.update_or_create(ship=self.ship, defaults={"thresholds": {ACTION: "COMMANDANT"}})
        self.assertEqual(VersionConfiguration.objects.get(cle=cle_seuils(self.ship.id)).valeur, 3)


class CheminsWebTests(TestCase):
    """Vue Réglages (Sécurité et Modules) et administration Django."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Web", code="WEB")
        self.admin = User.objects.create_superuser(username="admin_coh", password="pass", email="a@a.fr")
        UserProfile.objects.update_or_create(user=self.admin, defaults={"role": "MASTER_ADMIN", "ship": self.ship})
        self.client.login(username="admin_coh", password="pass")

    def test_vue_reglages_seuil_puis_reinitialisation(self):
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT_EN_SECOND)
        donnees = {"action": "update_role_threshold", "cle_action": ACTION, "nouveau_role": "COMMANDANT", "ship_id": self.ship.id}
        self.client.post(reverse("settings"), donnees)
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT)
        self.client.post(reverse("settings"), {**donnees, "action": "reset_role_threshold"})
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT_EN_SECOND)

    def test_vue_reglages_bascule_de_module(self):
        self.assertTrue(module_actif("assets", self.ship.id))
        donnees = {"action": "toggle_module", "cle_module": "assets", "ship_id": self.ship.id}
        self.client.post(reverse("settings"), donnees)
        self.assertFalse(module_actif("assets", self.ship.id))
        self.client.post(reverse("settings"), donnees)
        self.assertTrue(module_actif("assets", self.ship.id))

    def test_admin_django_modification_et_suppression(self):
        config = RoleThresholdConfig.objects.create(ship=self.ship, thresholds={ACTION: "COMMANDANT"})
        activation = ModuleActivation.objects.create(ship=self.ship, module="assets", active=True)
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT)
        self.assertTrue(module_actif("assets", self.ship.id))
        self.client.post(
            reverse("admin:org_rolethresholdconfig_change", args=[config.pk]),
            {"ship": self.ship.pk, "thresholds": json.dumps({ACTION: "ADMIN_NAVIRE"}), "_save": "Enregistrer"},
        )
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.ADMIN_NAVIRE)
        self.client.post(
            reverse("admin:org_moduleactivation_change", args=[activation.pk]),
            {"ship": self.ship.pk, "module": "assets", "_save": "Enregistrer"},  # case décochée : désactivé
        )
        self.assertFalse(module_actif("assets", self.ship.id))
        self.client.post(reverse("admin:org_rolethresholdconfig_delete", args=[config.pk]), {"post": "yes"})
        self.client.post(reverse("admin:org_moduleactivation_delete", args=[activation.pk]), {"post": "yes"})
        self.assertEqual(seuil_role(ACTION, self.ship.id), RoleLevel.COMMANDANT_EN_SECOND)
        self.assertTrue(module_actif("assets", self.ship.id))

    def test_le_contexte_est_ferme_apres_la_requete(self):
        self.client.get(reverse("settings"))
        self.assertIsNone(_contexte.get())


class IsolationEntreTestsTests(TestCase):
    """Les identifiants de navire se réutilisent d'un test à l'autre (SQLite) : le cache
    local d'un test annulé ne doit jamais fuiter dans le suivant (jeton de version)."""

    def test_a_configure_et_met_en_cache(self):
        ship = Ship.objects.create(name="Isolation", code="ISO")
        RoleThresholdConfig.objects.create(ship=ship, thresholds={ACTION: "COMMANDANT"})
        ModuleActivation.objects.create(ship=ship, module="assets", active=False)
        self.assertEqual(seuil_role(ACTION, ship.id), RoleLevel.COMMANDANT)
        self.assertFalse(module_actif("assets", ship.id))

    def test_b_ne_retrouve_pas_les_valeurs_du_test_precedent(self):
        ship = Ship.objects.create(name="Isolation", code="ISO")
        RoleThresholdConfig.objects.create(ship=ship, thresholds={ACTION: "ADMIN_NAVIRE"})
        ModuleActivation.objects.create(ship=ship, module="assets", active=True)
        self.assertEqual(seuil_role(ACTION, ship.id), RoleLevel.ADMIN_NAVIRE)
        self.assertTrue(module_actif("assets", ship.id))
