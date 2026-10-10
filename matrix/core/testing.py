"""Outils communs pour les tests."""
import shutil
import tempfile

from django.test import override_settings


class MediaRootTemporaireMixin:
    """Isole les fichiers téléversés pendant les tests dans un dossier temporaire.

    Un MEDIA_ROOT temporaire unique est créé par classe de test puis supprimé à
    la fin : aucun test n'écrit dans le vrai dossier media/. Sûr en exécution
    parallèle (chaque classe a son propre dossier).

    Usage : placer le mixin AVANT TestCase, par exemple
    ``class MesTests(MediaRootTemporaireMixin, TestCase):``.
    """

    @classmethod
    def setUpClass(cls):
        media_root = tempfile.mkdtemp(prefix="matrix_tests_media_")
        cls.addClassCleanup(shutil.rmtree, media_root, ignore_errors=True)
        surcharge = override_settings(MEDIA_ROOT=media_root)
        surcharge.enable()
        cls.addClassCleanup(surcharge.disable)
        super().setUpClass()
