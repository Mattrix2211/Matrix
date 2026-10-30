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
        self.assertEqual(env["DJANGO_SETTINGS_MODULE"], "matrix.settings")

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

    def test_marqueur_propre_a_chaque_fichier(self):
        (self.dossier / "demo.sqlite3").write_text("x")
        (self.dossier / "autre.sqlite3").write_text("x")
        script.marqueur(self.dossier / "demo.sqlite3").touch()
        script.verifier_chemin(self.dossier / "demo.sqlite3", self.dossier, True)
        self._refus(self.dossier / "autre.sqlite3", reinitialiser=True)

    def test_verification_seule_accepte_une_base_existante(self):
        (self.dossier / "demo.sqlite3").write_text("x")
        self.assertEqual(
            script.verifier_chemin(self.dossier / "demo.sqlite3", self.dossier, lecture_seule=True), self.dossier / "demo.sqlite3"
        )

    def test_lien_symbolique_refuse(self):
        cible = self.dossier.parent / "ailleurs.sqlite3"
        cible.write_text("x")
        script.marqueur(self.dossier / "demo.sqlite3").touch()
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
        script.marqueur(self.dossier / "demo.sqlite3").touch()
        (self.dossier / "demo.sqlite3").write_text("x")
        self.assertEqual(script.verifier_chemin(self.dossier / "demo.sqlite3", self.dossier, True), self.dossier / "demo.sqlite3")


class LancementSecuriseTests(SimpleTestCase):
    """--servir : même environnement isolé que la préparation, écoute locale seulement, refus sinon."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dossier = Path(self.tmp.name).resolve() / "instance_test_marins"
        self.dossier.mkdir()
        self.base = self.dossier / "demo.sqlite3"
        self.appels = []

    def _lancer(self, commande, cwd, env):
        self.appels.append((commande, env))

    def _preparer_la_base(self):
        self.base.write_text("")
        script.marqueur(self.base).touch()

    def _servir(self, **options):
        return script.servir(self.base, dossier_autorise=self.dossier, lancer=self._lancer, **options)

    def test_environnement_en_liste_blanche(self):
        hostile = {**os.environ, "DB_HOST": "prod", "EMAIL_HOST": "smtp.operationnel", "CELERY_BROKER_URL": "redis://prod/0",
                   "VAPID_PRIVATE_KEY": "cle", "DJANGO_ALLOWED_HOSTS": "*", "DJANGO_SECRET_KEY": "secret-prod"}
        ancien, os.environ = os.environ, hostile
        try:
            env = script.environnement_demo(self.base)
        finally:
            os.environ = ancien
        for variable in ("DB_HOST", "EMAIL_HOST", "CELERY_BROKER_URL", "VAPID_PRIVATE_KEY", "DJANGO_SECRET_KEY"):
            self.assertNotIn(variable, env)
        self.assertEqual(env["DJANGO_ALLOWED_HOSTS"], "localhost,127.0.0.1")
        self.assertTrue(set(env) <= set(script.VARIABLES_CONSERVEES) | {
            "MATRIX_SQLITE_PATH", "DJANGO_DEBUG", "DJANGO_SETTINGS_MODULE", "MATRIX_ENV_FILE", "DJANGO_ALLOWED_HOSTS", "EMAIL_BACKEND"})

    def test_serveur_lance_sur_la_boucle_locale_avec_l_environnement_isole(self):
        self._preparer_la_base()
        hostile = {**os.environ, "DB_HOST": "prod", "EMAIL_HOST": "smtp.operationnel", "DJANGO_ALLOWED_HOSTS": "*"}
        ancien, os.environ = os.environ, hostile
        try:
            self._servir(port=8812)
        finally:
            os.environ = ancien
        commande, env = self.appels[0]
        self.assertIn("127.0.0.1:8812", commande)
        self.assertFalse(any(argument.startswith("0.0.0.0") or argument.startswith(":") for argument in commande))
        self.assertEqual(env["MATRIX_SQLITE_PATH"], str(self.base))
        self.assertNotIn("DB_HOST", env)
        self.assertNotIn("EMAIL_HOST", env)

    def test_refus_si_la_base_n_est_pas_preparee(self):
        with self.assertRaises(script.RefusError):
            self._servir()
        self.base.write_text("")  # présente mais sans marqueur du script
        with self.assertRaises(script.RefusError):
            self._servir()
        self.assertEqual(self.appels, [])

    def test_refus_des_ports_et_chemins_invalides(self):
        self._preparer_la_base()
        for port in (0, 80, 1023, 65536, -1, "8800", None):
            with self.assertRaises(script.RefusError, msg=str(port)):
                self._servir(port=port)
        with self.assertRaises(script.RefusError):
            script.servir(settings.BASE_DIR / "db.sqlite3", dossier_autorise=self.dossier, lancer=self._lancer)
        self.assertEqual(self.appels, [])

    def test_refus_si_la_configuration_chargee_n_est_pas_isolee(self):
        sain = {"courriel": "django.core.mail.backends.locmem.EmailBackend", "serveur_courriel": "", "push": False,
                "courtier": "redis://localhost:6379/0 redis://localhost:6379/1", "hotes": ["localhost", "127.0.0.1"]}
        script.verifier_isolement(sain)
        for defaut in (
            {"courriel": "django.core.mail.backends.smtp.EmailBackend"}, {"serveur_courriel": "smtp.operationnel"},
            {"push": True}, {"courtier": "redis://prod.exemple:6379/0 redis://localhost:6379/1"},
            {"hotes": ["*"]}, {"hotes": ["localhost", "exemple.mil"]}, {"hotes": []},
        ):
            with self.assertRaises(script.RefusError, msg=str(defaut)):
                script.verifier_isolement({**sain, **defaut})

    def test_la_commande_n_accepte_aucun_hote(self):
        lignes = (settings.BASE_DIR / "scripts" / "preparer_instance_test.py").read_text(encoding="utf-8")
        self.assertNotIn("--hote", lignes)
        self.assertNotIn("0.0.0.0", lignes)
        self.assertEqual(script.HOTE, "127.0.0.1")
