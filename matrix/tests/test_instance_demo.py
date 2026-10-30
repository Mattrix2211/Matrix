"""Garde-fous de l'instance de démonstration : elle ne doit jamais viser ni supprimer une autre base."""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from matrix import settings as reglages

_SPEC = importlib.util.spec_from_file_location("preparer_instance_test", settings.BASE_DIR / "scripts" / "preparer_instance_test.py")
script = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(script)

POSTGRES_ENV = {"DB_HOST": "127.0.0.1", "DB_PORT": "1", "DB_NAME": "operationnelle", "DB_USER": "x", "DB_PASSWORD": "x"}


class ChoixDeLaBaseTests(SimpleTestCase):
    def test_sqlite_explicite_l_emporte_sur_postgresql(self):
        base = reglages.choisir_base_de_donnees({**POSTGRES_ENV, "MATRIX_SQLITE_PATH": "/tmp/demo.sqlite3"})
        self.assertEqual(base["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(base["default"]["NAME"], "/tmp/demo.sqlite3")

    def test_comportement_habituel_inchange(self):
        self.assertEqual(reglages.choisir_base_de_donnees(POSTGRES_ENV)["default"]["ENGINE"], "django.db.backends.postgresql")
        defaut = reglages.choisir_base_de_donnees({"MATRIX_SQLITE_PATH": ""})["default"]
        self.assertEqual((defaut["ENGINE"], defaut["NAME"]), ("django.db.backends.sqlite3", settings.BASE_DIR / "db.sqlite3"))


class EnvPostgresqlTests(SimpleTestCase):
    """Un .env configurant PostgreSQL ne doit jamais ramener l'instance de démonstration sur PostgreSQL."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dossier = Path(self.tmp.name).resolve()
        self.env_postgres = self.dossier / ".env"
        self.env_postgres.write_text("\n".join(f"{k}={v}" for k, v in POSTGRES_ENV.items()), encoding="utf-8")

    def _environnement_parent(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("DB_", "MATRIX_"))}
        return {**env, "DJANGO_DEBUG": "1", "MATRIX_ENV_FILE": str(self.env_postgres), **extra}

    def test_env_postgresql_sans_base_explicite_vise_postgresql(self):
        # Témoin : le .env est bien pris en compte, sinon les tests suivants ne prouveraient rien.
        sortie = subprocess.run(
            [sys.executable, "-c", "import os;os.environ['DJANGO_SETTINGS_MODULE']='matrix.settings';import django;django.setup();"
             "from django.db import connection;print(connection.vendor)"],
            cwd=settings.BASE_DIR, env=self._environnement_parent(), capture_output=True, text=True,
        )
        self.assertEqual(sortie.stdout.strip(), "postgresql", sortie.stderr)

    def test_env_postgresql_avec_base_explicite_reste_sqlite(self):
        base = self.dossier / "demo.sqlite3"
        sortie = subprocess.run(
            [sys.executable, "-c", "import os;os.environ['DJANGO_SETTINGS_MODULE']='matrix.settings';import django;django.setup();"
             "from django.db import connection;print(connection.vendor, connection.settings_dict['NAME'])"],
            cwd=settings.BASE_DIR, env=self._environnement_parent(MATRIX_SQLITE_PATH=str(base)), capture_output=True, text=True,
        )
        self.assertEqual(sortie.stdout.strip(), f"sqlite {base}", sortie.stderr)

    def test_environnement_du_script_retire_postgresql_et_le_env_du_poste(self):
        base = self.dossier / "demo.sqlite3"
        parent = self._environnement_parent(CELERY_BROKER_URL="redis://operationnel", **POSTGRES_ENV)
        ancien, os.environ = os.environ, parent
        try:
            env = script.environnement_demo(base)
        finally:
            os.environ = ancien
        self.assertEqual(env["MATRIX_SQLITE_PATH"], str(base))
        self.assertTrue(all(cle not in env for cle in POSTGRES_ENV) and "CELERY_BROKER_URL" not in env)
        self.assertEqual(Path(env["MATRIX_ENV_FILE"]).parent, self.dossier)
        self.assertFalse(Path(env["MATRIX_ENV_FILE"]).exists())
        self.assertIn("locmem", env["EMAIL_BACKEND"])

    def test_controle_reussit_malgre_un_env_postgresql(self):
        base = self.dossier / "demo.sqlite3"
        parent = self._environnement_parent(**POSTGRES_ENV)
        ancien, os.environ = os.environ, parent
        try:
            self.assertEqual(script.preparer(base, verifier_seulement=True, dossier_autorise=self.dossier), base)
        finally:
            os.environ = ancien
        self.assertFalse(base.exists())  # le contrôle n'écrit rien

    def test_controle_refuse_si_la_connexion_ne_vise_pas_la_base_attendue(self):
        base = self.dossier / "demo.sqlite3"
        hostile = self._environnement_parent(**POSTGRES_ENV)  # ni MATRIX_SQLITE_PATH ni retrait de DB_HOST
        with self.assertRaises(script.RefusError):
            script.controler_connexion(base, hostile)
        autre = self._environnement_parent(MATRIX_SQLITE_PATH=str(self.dossier / "autre.sqlite3"))
        with self.assertRaises(script.RefusError):
            script.controler_connexion(base, autre)


class CheminsInterditsTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dossier = Path(self.tmp.name).resolve() / "instance_test_marins"
        self.dossier.mkdir()

    def _refus(self, chemin, reinitialiser=False):
        with self.assertRaises(script.RefusError, msg=str(chemin)):
            script.verifier_chemin(chemin, self.dossier, reinitialiser)

    def test_chemins_hors_du_dossier_de_demonstration_refuses(self):
        for chemin in (
            settings.BASE_DIR / "db.sqlite3", "/etc/passwd", "/tmp/demo.sqlite3", self.dossier.parent / "demo.sqlite3",
            self.dossier / "sous" / "demo.sqlite3", self.dossier / ".." / "demo.sqlite3", self.dossier,
            self.dossier / "demo.db", self.dossier / "demo.sqlite3.bak", Path.home() / "demo.sqlite3",
        ):
            self._refus(chemin, reinitialiser=True)

    def test_base_de_developpement_refusee_meme_dans_le_dossier_autorise(self):
        with self.assertRaises(script.RefusError):
            script.verifier_chemin(settings.BASE_DIR / "db.sqlite3", settings.BASE_DIR, reinitialiser=True)

    def test_existant_sans_reinitialiser_refuse(self):
        (self.dossier / "demo.sqlite3").write_text("x")
        self._refus(self.dossier / "demo.sqlite3")

    def test_suppression_refusee_sans_marqueur(self):
        (self.dossier / "demo.sqlite3").write_text("x")
        self._refus(self.dossier / "demo.sqlite3", reinitialiser=True)

    def test_lien_symbolique_refuse(self):
        cible = self.dossier.parent / "ailleurs.sqlite3"
        cible.write_text("x")
        (self.dossier / script.MARQUEUR).touch()
        (self.dossier / "demo.sqlite3").symlink_to(cible)
        self._refus(self.dossier / "demo.sqlite3", reinitialiser=True)

    def test_dossier_en_lien_symbolique_refuse(self):
        vrai = self.dossier.parent / "vrai"
        vrai.mkdir()
        lien = self.dossier.parent / "lien"
        lien.symlink_to(vrai)
        with self.assertRaises(script.RefusError):
            script.verifier_chemin(lien / "demo.sqlite3", lien, False)

    def test_chemin_valide_accepte(self):
        self.assertEqual(script.verifier_chemin(self.dossier / "demo.sqlite3", self.dossier), self.dossier / "demo.sqlite3")
        (self.dossier / script.MARQUEUR).touch()
        (self.dossier / "demo.sqlite3").write_text("x")
        self.assertEqual(script.verifier_chemin(self.dossier / "demo.sqlite3", self.dossier, True), self.dossier / "demo.sqlite3")
