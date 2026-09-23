"""Tests de matrix/core/checks.py et de la valeur par défaut de DEBUG.

Contexte (durcissement config prod, Phase 0) : DEBUG doit valoir False par
défaut en l'absence de DJANGO_DEBUG dans l'environnement — un DEBUG=True
oublié en production expose des informations sensibles (traces d'erreur
détaillées, requêtes SQL). Le développement local reste inchangé grâce au
fichier .env du poste (voir .env.example, jamais commité).
"""
import importlib
import os
import sys
from unittest import mock

from django.test import SimpleTestCase

from matrix import settings as matrix_settings
from matrix.core import checks as matrix_checks


class DebugDesactiveParDefautTests(SimpleTestCase):
    """Vérifie que le calcul réel de DEBUG dans matrix/settings.py retombe
    bien sur False quand DJANGO_DEBUG n'est pas positionné."""

    def test_debug_est_desactive_sans_variable_environnement(self):
        # Une clé secrète explicite est fournie pour ce recalcul isolé, afin
        # de ne pas déclencher le garde-fou SECRET_KEY (qui exige une clé de
        # production dès que DEBUG=False) : seul le défaut de DEBUG est
        # testé ici, pas ce garde-fou déjà couvert par ailleurs.
        # Le fichier .env du poste (s'il existe) est ignoré pour ce test : on
        # veut vérifier le défaut du code lui-même, pas le confort de dev
        # apporté par .env (déjà couvert par le test de la classe suivante).
        environnement_sans_debug = {
            k: v for k, v in os.environ.items() if k != "DJANGO_DEBUG"
        }
        environnement_sans_debug["DJANGO_SECRET_KEY"] = "cle-de-test-non-utilisee-en-prod"
        with mock.patch.dict(os.environ, environnement_sans_debug, clear=True):
            with mock.patch("pathlib.Path.exists", return_value=False):
                importlib.reload(matrix_settings)
        try:
            self.assertFalse(matrix_settings.DEBUG)
        finally:
            # Recharge le module avec l'environnement réel du poste pour ne
            # pas impacter les autres tests qui s'appuient dessus.
            importlib.reload(matrix_settings)


class VerifierDebugDesactiveHorsDeveloppementLocalTests(SimpleTestCase):
    """Vérifie le nouveau garde-fou de démarrage matrix.W002."""

    def _executer_check(self):
        return matrix_checks.verifier_debug_desactive_hors_developpement_local(None)

    def test_avertit_si_debug_actif_hors_runserver(self):
        with mock.patch.object(sys, "argv", ["manage.py", "migrate"]):
            with self.settings(DEBUG=True):
                avertissements = self._executer_check()
        self.assertEqual(len(avertissements), 1)
        self.assertEqual(avertissements[0].id, "matrix.W002")

    def test_aucun_avertissement_pendant_runserver_local(self):
        with mock.patch.object(sys, "argv", ["manage.py", "runserver"]):
            with self.settings(DEBUG=True):
                avertissements = self._executer_check()
        self.assertEqual(avertissements, [])

    def test_aucun_avertissement_si_debug_desactive(self):
        with mock.patch.object(sys, "argv", ["manage.py", "migrate"]):
            with self.settings(DEBUG=False):
                avertissements = self._executer_check()
        self.assertEqual(avertissements, [])
