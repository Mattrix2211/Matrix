"""Tests de robustesse : une absence de WeasyPrint (bibliothèques GTK natives
manquantes, cas fréquent sous Windows même après `pip install`) ne doit JAMAIS
faire planter le chargement de l'application (import du module, résolution des
URLs, migrate/runserver/test) — seule la génération effective d'un PDF doit
échouer proprement avec un message clair.

Reproduit le bug réel observé : `import weasyprint` lève une OSError (et non
une ImportError) quand le paquet Python est installé mais que GTK est absent.
"""
import builtins
import importlib
from unittest.mock import patch

from django.test import TestCase

import reports.services as reports_services
from reports.services import BilanPdfIndisponible


class ImportWeasyprintProtegeTests(TestCase):
    def tearDown(self):
        # Toujours restaurer l'état normal du module après les tests de reload,
        # pour ne pas impacter les autres tests de la suite qui suivent.
        importlib.reload(reports_services)

    def test_import_module_avec_oserror_ne_plante_pas(self):
        """Cas réel observé sous Windows : OSError (GTK manquant), pas ImportError."""
        import_reel = builtins.__import__

        def import_avec_oserror(nom, *args, **kwargs):
            if nom == "weasyprint":
                raise OSError("cannot load library 'libgobject-2.0-0'")
            return import_reel(nom, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_avec_oserror):
            importlib.reload(reports_services)  # ne doit lever aucune exception

        self.assertFalse(reports_services.WEASYPRINT_DISPONIBLE)

    def test_import_module_avec_importerror_ne_plante_pas(self):
        """Cas où le paquet weasyprint n'est même pas installé (pip)."""
        import_reel = builtins.__import__

        def import_avec_importerror(nom, *args, **kwargs):
            if nom == "weasyprint":
                raise ImportError("No module named 'weasyprint'")
            return import_reel(nom, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_avec_importerror):
            importlib.reload(reports_services)  # ne doit lever aucune exception

        self.assertFalse(reports_services.WEASYPRINT_DISPONIBLE)


class GenerationPdfSansWeasyprintTests(TestCase):
    def test_bilan_instantane_leve_une_exception_claire_sans_weasyprint(self):
        with patch.object(reports_services, "WEASYPRINT_DISPONIBLE", False):
            with self.assertRaises(BilanPdfIndisponible):
                reports_services.generer_bilan_instantane_pdf("ship", 1, None)

    def test_bilan_periode_leve_une_exception_claire_sans_weasyprint(self):
        with patch.object(reports_services, "WEASYPRINT_DISPONIBLE", False):
            with self.assertRaises(BilanPdfIndisponible):
                reports_services.generer_bilan_periode_pdf(
                    "ship", 1, None, "2026-01-01", "2026-01-31"
                )
