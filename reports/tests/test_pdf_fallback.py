"""Tests du repli quand WeasyPrint est indisponible (bibliothèques natives GTK
absentes, cas par défaut sous Windows même après `pip install -r requirements.txt`).

Contexte du bug corrigé : `reports/services.py` faisait `import weasyprint` au
niveau module, chargé dès le démarrage de Django via la chaîne
`matrix/urls.py -> reports/web_urls.py -> reports/web_views.py ->
reports/services.py`. Si les bibliothèques natives GTK manquent, cet import
lève une OSError (pas une ImportError) qui faisait planter tout le serveur
(migrate, createsuperuser, runserver — aucune page ne chargeait).

Ces tests simulent cette absence sans désinstaller WeasyPrint (qui est bien
fonctionnel dans cet environnement de test) :
- via une copie indépendante du module (n'affecte jamais `reports.services`
  ni les objets déjà importés ailleurs dans la suite de tests, notamment la
  classe `PerimetreNonAutorise` utilisée par des `except` dans d'autres
  modules) pour vérifier le comportement de `pdf_disponible()` et des
  générateurs PDF ;
- via un process Python isolé (subprocess) pour vérifier que le démarrage
  complet de Django et la résolution des URLs ne plantent plus."""
import importlib.abc
import importlib.util
import subprocess
import sys
import textwrap
import unittest
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import reports.services as services_module
from accounts.models import UserProfile
from org.models import Sector, Service, Ship


class _ChercheurWeasyprintIndisponible(importlib.abc.MetaPathFinder):
    """Finder d'import qui simule l'absence des bibliothèques natives GTK :
    lève une OSError (et non une ImportError) sur `import weasyprint`, comme
    le fait réellement WeasyPrint dans ce cas précis."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "weasyprint":
            raise OSError("cannot load library 'libgobject-2.0-0': error 0x7e")
        return None


class _SimulationWeasyprintIndisponible:
    """Bloque temporairement l'import de weasyprint (OSError). N'affecte que
    ce qui est importé/exécuté à l'intérieur du bloc `with` — restaure l'état
    du système d'import à la sortie."""

    def __enter__(self):
        self._chercheur = _ChercheurWeasyprintIndisponible()
        self._weasyprint_original = sys.modules.pop("weasyprint", None)
        sys.meta_path.insert(0, self._chercheur)
        return self

    def __exit__(self, *exc_info):
        sys.meta_path.remove(self._chercheur)
        if self._weasyprint_original is not None:
            sys.modules["weasyprint"] = self._weasyprint_original
        return False


def _charger_copie_isolee_de_services():
    """Charge une copie indépendante de reports/services.py — sans jamais
    passer par `sys.modules['reports.services']` — pour ne pas polluer l'état
    partagé du test runner (les autres fichiers de tests détiennent déjà des
    références à des objets du vrai module, ex: `PerimetreNonAutorise`)."""
    spec = importlib.util.spec_from_file_location(
        "reports_services_copie_test", services_module.__file__
    )
    copie = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(copie)
    return copie


class PdfDisponibleServiceTests(TestCase):
    """Vérifie `pdf_disponible()` et le repli des générateurs PDF au niveau
    service, sans jamais toucher au module réellement utilisé par l'appli."""

    def test_pdf_disponible_faux_si_import_weasyprint_echoue(self):
        with _SimulationWeasyprintIndisponible():
            copie = _charger_copie_isolee_de_services()
        self.assertFalse(copie.pdf_disponible())

    def test_generation_pdf_instantanee_renvoie_none_au_lieu_de_planter(self):
        navire = Ship.objects.create(name="Navire fallback PDF", code="FBP")
        service = Service.objects.create(ship=navire, name="Service fallback PDF")
        secteur = Sector.objects.create(service=service, name="Secteur fallback PDF")
        chef = User.objects.create_user(username="chef_fallback_pdf", password="pass")
        UserProfile.objects.filter(user=chef).update(role="CHEF_SECTEUR", sector=secteur)
        chef.refresh_from_db()

        with _SimulationWeasyprintIndisponible():
            copie = _charger_copie_isolee_de_services()
        resultat = copie.generer_bilan_instantane_pdf("sector", secteur.id, chef)
        self.assertIsNone(resultat)

    def test_generation_pdf_periode_renvoie_none_au_lieu_de_planter(self):
        navire = Ship.objects.create(name="Navire fallback PDF période", code="FBQ")
        service = Service.objects.create(ship=navire, name="Service fallback PDF période")
        secteur = Sector.objects.create(service=service, name="Secteur fallback PDF période")
        chef = User.objects.create_user(username="chef_fallback_pdf_periode", password="pass")
        UserProfile.objects.filter(user=chef).update(role="CHEF_SECTEUR", sector=secteur)
        chef.refresh_from_db()
        aujourdhui = timezone.localdate()

        with _SimulationWeasyprintIndisponible():
            copie = _charger_copie_isolee_de_services()
        resultat = copie.generer_bilan_periode_pdf(
            "sector", secteur.id, chef, aujourdhui, aujourdhui
        )
        self.assertIsNone(resultat)


class DemarrageSansWeasyprintTests(TestCase):
    """Vérifie, dans un process Python isolé (aucune pollution de l'état du
    test runner), que le démarrage complet de Django et la résolution des URLs
    ne plantent plus si l'import de weasyprint échoue avec une OSError —
    c'est le bug initialement signalé : toute l'application plantait
    (migrate, runserver, aucune page ne chargeait), pas seulement le bilan
    PDF."""

    def test_resolution_des_urls_ne_plante_pas_sans_weasyprint(self):
        script = textwrap.dedent(
            """
            import importlib.abc
            import os
            import sys

            class ChercheurWeasyprintIndisponible(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path, target=None):
                    if fullname == "weasyprint":
                        raise OSError("cannot load library 'libgobject-2.0-0'")
                    return None

            sys.meta_path.insert(0, ChercheurWeasyprintIndisponible())

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
            import django
            django.setup()

            from django.urls import reverse
            print(reverse("rapport-bilan"))
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
            msg=f"Le process a planté sans WeasyPrint disponible :\n{resultat.stderr}",
        )
        self.assertIn("/rapports/bilan/", resultat.stdout)


class MessageErreurParFormatTests(TestCase):
    """Le message d'erreur affiché quand un format d'export est indisponible
    doit être spécifique au format demandé (PDF ou Excel), pas systématiquement
    « Excel », et doit suggérer le repli vers le CSV."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire message format", code="MSF")
        self.service = Service.objects.create(ship=self.navire, name="Service message format")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur message format")
        self.chef = User.objects.create_user(username="chef_message_format", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTEUR", sector=self.secteur)
        self.chef.refresh_from_db()
        self.url = reverse("rapport-bilan")

    def test_message_pdf_indisponible_mentionne_pdf_et_le_repli_csv(self):
        self.client.login(username="chef_message_format", password="pass")
        with patch("reports.web_views.generer_bilan_instantane_pdf", return_value=None):
            response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        contenus_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("PDF" in m and "CSV" in m for m in contenus_messages))

    def test_message_xlsx_indisponible_mentionne_excel_et_le_repli_csv(self):
        self.client.login(username="chef_message_format", password="pass")
        with patch("reports.web_views.generer_bilan_instantane_xlsx", return_value=None):
            response = self.client.get(self.url, {"format": "xlsx"}, follow=True)
        self.assertEqual(response.status_code, 200)
        contenus_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("Excel" in m and "CSV" in m for m in contenus_messages))


@unittest.skipUnless(
    services_module.pdf_disponible(), "WeasyPrint indisponible sur cette machine"
)
class GenerationPdfNominaleInchangeeTests(TestCase):
    """En environnement nominal (WeasyPrint fonctionnel), le correctif ne change
    rien au comportement existant. Sur une machine sans bibliothèques natives
    GTK (ex: Windows sans GTK installé), cette classe est proprement ignorée
    (skip) plutôt que de faire échouer la suite de tests."""

    def test_pdf_disponible_est_vrai(self):
        self.assertTrue(services_module.pdf_disponible())

    def test_generation_pdf_instantanee_fonctionne_toujours(self):
        navire = Ship.objects.create(name="Navire nominal PDF", code="NOM")
        service = Service.objects.create(ship=navire, name="Service nominal PDF")
        secteur = Sector.objects.create(service=service, name="Secteur nominal PDF")
        chef = User.objects.create_user(username="chef_nominal_pdf", password="pass")
        UserProfile.objects.filter(user=chef).update(role="CHEF_SECTEUR", sector=secteur)
        chef.refresh_from_db()

        resultat = services_module.generer_bilan_instantane_pdf("sector", secteur.id, chef)
        self.assertIsNotNone(resultat)
        self.assertTrue(resultat.startswith(b"%PDF"))
