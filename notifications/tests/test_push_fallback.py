"""Tests du repli quand pywebpush est indisponible (dépendance native
http-ece qui ne compile pas sur tous les postes, cf. requirements.txt).

Contexte du bug corrigé : `notifications/push.py` faisait
`from pywebpush import WebPushException, webpush` au niveau module. Ce module
n'est chargé qu'à la première notification de niveau DANGER enregistrée (import
tardif dans `notifications/signals.py`), mais dès cet instant, si pywebpush
n'est pas installé, l'import lève `ModuleNotFoundError` — qui remonte jusqu'à
l'appelant du `.save()` de la `Notification`. Comme de nombreux workflows
métier (anomalies, tickets correctifs, échéances de formation…) créent des
notifications de niveau DANGER, cela faisait planter des fonctionnalités sans
aucun rapport avec le Web Push.

Ces tests simulent cette absence sans désinstaller pywebpush (qui est bien
fonctionnel dans cet environnement de test) :
- via une copie indépendante du module (n'affecte jamais `notifications.push`
  ni les objets déjà importés ailleurs, notamment le signal déjà connecté)
  pour vérifier le comportement de `push_disponible()` et de
  `envoyer_notification_push()` ;
- via un process Python isolé (subprocess) pour vérifier que la création
  d'une notification critique ne plante plus, du signal jusqu'à l'appel réel
  de `notifications.push`."""
import importlib.abc
import importlib.util
import subprocess
import sys
import textwrap
import unittest

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

import notifications.push as push_module
from notifications.models import Notification, NotificationLevel, PushSubscription


class _ChercheurPywebpushIndisponible(importlib.abc.MetaPathFinder):
    """Finder d'import qui simule l'absence de pywebpush (ModuleNotFoundError),
    comme lorsque sa dépendance native http-ece ne compile pas."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "pywebpush":
            raise ModuleNotFoundError("No module named 'pywebpush'")
        return None


class _SimulationPywebpushIndisponible:
    """Bloque temporairement l'import de pywebpush. N'affecte que ce qui est
    importé/exécuté à l'intérieur du bloc `with` — restaure l'état du système
    d'import à la sortie."""

    def __enter__(self):
        self._chercheur = _ChercheurPywebpushIndisponible()
        self._pywebpush_original = sys.modules.pop("pywebpush", None)
        sys.meta_path.insert(0, self._chercheur)
        return self

    def __exit__(self, *exc_info):
        sys.meta_path.remove(self._chercheur)
        if self._pywebpush_original is not None:
            sys.modules["pywebpush"] = self._pywebpush_original
        return False


def _charger_copie_isolee_de_push():
    """Charge une copie indépendante de notifications/push.py — sans jamais
    passer par `sys.modules['notifications.push']` — pour ne pas perturber le
    signal déjà connecté au démarrage de l'app (cf. notifications/apps.py).

    Le nom donné au module (`notifications.push_copie_test`) le rattache au
    paquet `notifications` déjà chargé, pour que son import relatif
    `from .models import PushSubscription` se résolve normalement — sans
    jamais inscrire la copie elle-même dans `sys.modules`."""
    spec = importlib.util.spec_from_file_location(
        "notifications.push_copie_test", push_module.__file__
    )
    copie = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(copie)
    return copie


class PushDisponibleTests(TestCase):
    """Vérifie `push_disponible()` et le repli de `envoyer_notification_push()`,
    sans jamais toucher au module réellement utilisé par l'appli."""

    def test_push_disponible_faux_si_import_pywebpush_echoue(self):
        with _SimulationPywebpushIndisponible():
            copie = _charger_copie_isolee_de_push()
        self.assertFalse(copie.push_disponible())

    @override_settings(VAPID_PUBLIC_KEY="clé-publique-test", VAPID_PRIVATE_KEY="clé-privée-test")
    def test_envoi_push_ignore_sans_pywebpush_au_lieu_de_planter(self):
        marin = User.objects.create_user(username="marin_fallback_push", password="pass")
        PushSubscription.objects.create(
            user=marin, endpoint="https://push.example.com/fallback", p256dh="p", auth="a"
        )
        notif = Notification(user=marin, verb="Alerte critique", level=NotificationLevel.DANGER)

        with _SimulationPywebpushIndisponible():
            copie = _charger_copie_isolee_de_push()
        try:
            resultat = copie.envoyer_notification_push(notif)
        except Exception as exc:  # pragma: no cover - l'assertion suivante échouerait déjà
            self.fail(f"L'envoi push sans pywebpush ne doit jamais planter : {exc}")
        self.assertIsNone(resultat)


class CreationNotificationSansPywebpushTests(TestCase):
    """Vérifie, dans un process Python isolé (aucune pollution de l'état du
    test runner), que la création d'une notification de niveau DANGER ne
    plante plus si l'import de pywebpush échoue — c'est le bug initialement
    signalé : n'importe quelle notification critique (anomalie, ticket
    correctif, échéance de formation…) faisait planter son appelant."""

    def test_creation_notification_danger_ne_plante_pas_sans_pywebpush(self):
        script = textwrap.dedent(
            """
            import importlib.abc
            import os
            import sys

            class ChercheurPywebpushIndisponible(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path, target=None):
                    if fullname == "pywebpush":
                        raise ModuleNotFoundError("No module named 'pywebpush'")
                    return None

            sys.meta_path.insert(0, ChercheurPywebpushIndisponible())

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
            import django
            django.setup()

            from django.contrib.auth.models import User
            from django.test.utils import setup_test_environment
            from django.test.runner import DiscoverRunner

            runner = DiscoverRunner()
            old_config = runner.setup_databases()
            setup_test_environment()
            try:
                from notifications.models import Notification, NotificationLevel

                marin = User.objects.create_user(username="marin_process_isole", password="pass")
                Notification.objects.create(
                    user=marin, verb="Alerte critique isolée", level=NotificationLevel.DANGER
                )
                print("OK")
            finally:
                runner.teardown_databases(old_config)
            """
        )
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(settings.BASE_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            resultat.returncode,
            0,
            msg=f"Le process a planté sans pywebpush disponible :\n{resultat.stderr}",
        )
        self.assertIn("OK", resultat.stdout)


@unittest.skipUnless(
    push_module.push_disponible(), "pywebpush indisponible sur cette machine"
)
class EnvoiPushNominalInchangeTests(TestCase):
    """En environnement nominal (pywebpush fonctionnel), le correctif ne
    change rien au comportement existant."""

    def test_push_disponible_est_vrai(self):
        self.assertTrue(push_module.push_disponible())
