"""Secrets de production (AUD-010, AUD-017) : refus d'une clé ou d'un mot de passe de base insuffisants, développement inchangé."""
import os
import secrets
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase

from matrix import settings as reglages

CLE_VALIDE = secrets.token_urlsafe(50)
DEMARRER = "import os;os.environ['DJANGO_SETTINGS_MODULE']='matrix.settings';import django;django.setup();from django.conf import settings;print(settings.SECRET_KEY==%r)"


class ErreursSecretsProductionTests(SimpleTestCase):
    def test_configuration_acceptable(self):
        self.assertEqual(reglages.erreurs_secrets_production({}, CLE_VALIDE), [])
        self.assertEqual(reglages.erreurs_secrets_production({"DB_HOST": "db", "DB_PASSWORD": secrets.token_urlsafe(20)}, CLE_VALIDE), [])

    def test_cles_refusees(self):
        for cle in ("", "dev-secret-key", "change-me", "CHANGE-ME", "secret", "a" * 31):
            erreurs = reglages.erreurs_secrets_production({}, cle)
            self.assertEqual(len(erreurs), 1, repr(cle))
            self.assertIn("DJANGO_SECRET_KEY", erreurs[0])

    def test_mots_de_passe_de_base_refuses_des_que_postgresql_est_vise(self):
        for mot_de_passe in (None, "", "matrix", "change-me", "Postgres", "ADMIN"):
            env = {"DB_HOST": "db"} if mot_de_passe is None else {"DB_HOST": "db", "DB_PASSWORD": mot_de_passe}
            erreurs = reglages.erreurs_secrets_production(env, CLE_VALIDE)
            self.assertEqual(len(erreurs), 1, repr(mot_de_passe))
            self.assertIn("DB_PASSWORD", erreurs[0])

    def test_pas_de_controle_du_mot_de_passe_sans_postgresql_ni_pour_la_demonstration(self):
        self.assertEqual(reglages.erreurs_secrets_production({"DB_PASSWORD": "matrix"}, CLE_VALIDE), [])  # SQLite : mot de passe sans objet
        self.assertEqual(reglages.erreurs_secrets_production({"DB_HOST": "db", "MATRIX_SQLITE_PATH": "/x/demo.sqlite3"}, CLE_VALIDE), [])

    def test_les_deux_erreurs_sont_cumulees(self):
        self.assertEqual(len(reglages.erreurs_secrets_production({"DB_HOST": "db"}, "change-me")), 2)


class DemarrageReelTests(SimpleTestCase):
    """Démarrage de Django dans un processus neuf, avec un environnement maîtrisé (aucun .env du poste)."""

    def _demarrer(self, cle_attendue=None, **env):
        propre = {k: v for k, v in os.environ.items() if not k.startswith(("DB_", "DJANGO_", "MATRIX_", "POSTGRES_"))}
        propre["MATRIX_ENV_FILE"] = env.pop("MATRIX_ENV_FILE", os.devnull + ".absent")
        sortie = subprocess.run([sys.executable, "-c", DEMARRER % (cle_attendue,)], cwd=settings.BASE_DIR, env={**propre, **env},
                                capture_output=True, text=True, timeout=120)
        return sortie

    def test_production_sans_cle_ou_avec_une_valeur_d_exemple_est_refusee(self):
        for env in ({"DJANGO_DEBUG": "0"}, {"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": ""}, {"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": "change-me"},
                    {"DJANGO_SECRET_KEY": "dev-secret-key"}):  # DEBUG absent = production
            sortie = self._demarrer(**env)
            self.assertNotEqual(sortie.returncode, 0, env)
            self.assertIn("Configuration refusée en production", sortie.stderr)

    def test_production_avec_postgresql_sans_mot_de_passe_reel_est_refusee(self):
        for mot_de_passe in ({}, {"DB_PASSWORD": "matrix"}):
            sortie = self._demarrer(DJANGO_DEBUG="0", DJANGO_SECRET_KEY=CLE_VALIDE, DB_HOST="127.0.0.1", **mot_de_passe)
            self.assertNotEqual(sortie.returncode, 0, mot_de_passe)
            self.assertIn("DB_PASSWORD", sortie.stderr)

    def test_production_correctement_configuree_demarre(self):
        sortie = self._demarrer(CLE_VALIDE, DJANGO_DEBUG="0", DJANGO_SECRET_KEY=CLE_VALIDE, DB_HOST="127.0.0.1", DB_PASSWORD=secrets.token_urlsafe(20))
        self.assertEqual(sortie.returncode, 0, sortie.stderr[-400:])
        self.assertEqual(sortie.stdout.strip(), "True")

    def test_developpement_reste_simple_sans_cle_et_avec_les_valeurs_d_exemple(self):
        for env in ({"DJANGO_DEBUG": "1"}, {"DJANGO_DEBUG": "1", "DJANGO_SECRET_KEY": ""},
                    {"DJANGO_DEBUG": "1", "DJANGO_SECRET_KEY": "change-me", "DB_HOST": "127.0.0.1"}):
            sortie = self._demarrer(env.get("DJANGO_SECRET_KEY") or reglages._CLE_SECRETE_DEV_PAR_DEFAUT, **env)
            self.assertEqual(sortie.returncode, 0, (env, sortie.stderr[-300:]))
            self.assertEqual(sortie.stdout.strip(), "True")

    def test_le_fichier_d_exemple_demarre_en_developpement_et_est_refuse_en_production(self):
        exemple = str(settings.BASE_DIR / ".env.example")
        developpement = self._demarrer(reglages._CLE_SECRETE_DEV_PAR_DEFAUT, MATRIX_ENV_FILE=exemple)
        self.assertEqual(developpement.returncode, 0, developpement.stderr[-300:])
        production = self._demarrer(MATRIX_ENV_FILE=exemple, DJANGO_DEBUG="0")
        self.assertNotEqual(production.returncode, 0)
        self.assertIn("Configuration refusée en production", production.stderr)

    def test_l_exemple_ne_contient_aucune_valeur_acceptee_en_production(self):
        texte = (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8")
        lignes = {l.partition("=")[0]: l.partition("=")[2] for l in texte.splitlines() if "=" in l and not l.startswith("#")}
        self.assertEqual(lignes["DJANGO_SECRET_KEY"], "")
        self.assertNotIn("DB_PASSWORD", lignes)  # commenté : jamais de mot de passe d'exemple actif
