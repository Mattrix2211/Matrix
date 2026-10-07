import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import AuditLog, SpecialityChoice
from assets.models import ArticleCatalogue, Asset, AssetFolder, AssetType, CategorieCatalogue
from org.models import Sector, Service, Ship


class CatalogueRepriseTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        service = Service.objects.create(name="Service A", ship=self.ship)
        sector = Sector.objects.create(name="Secteur A", service=service)
        self.type = AssetType.objects.create(name="Type", category="Cat", sector=sector)
        self.base = dict(asset_type=self.type, ship=self.ship, service=service, sector=sector)
        self.specialite = SpecialityChoice.objects.create(name="Sécurité")
        self.racine = AssetFolder.objects.create(name="Incendie")
        self.sous = AssetFolder.objects.create(name="Extincteurs", parent=self.racine)
        self.m1 = Asset.objects.create(designation="Extincteur CO2", marque="Sicli", reference="C5", folder=self.sous, **self.base)
        self.m2 = Asset.objects.create(designation="Extincteur CO2", marque="Sicli", reference="C5", folder=self.sous, **self.base)
        self.m3 = Asset.objects.create(designation="Extincteur eau", folder=self.sous, **self.base)
        self.sans_designation = Asset.objects.create(folder=self.racine, **self.base)
        self.hors_dossier = Asset.objects.create(designation="Libre", **self.base)

    def _lancer(self, *args):
        sortie = StringIO()
        call_command("catalogue_reprise", *args, stdout=sortie)
        return sortie.getvalue()

    def test_sans_specialite_liste_les_dossiers_et_n_ecrit_rien(self):
        sortie = self._lancer("--appliquer")
        self.assertIn("À qualifier", sortie)
        self.assertIn("Incendie", sortie)
        self.assertEqual(CategorieCatalogue.objects.count(), 0)
        self.assertEqual(ArticleCatalogue.objects.count(), 0)

    def test_dry_run_n_ecrit_rien_et_rapporte(self):
        sortie = self._lancer("--dry-run", "--specialite", "Sécurité")
        self.assertIn("Incendie / Extincteurs", sortie)
        self.assertEqual(CategorieCatalogue.objects.count(), 0)
        self.assertEqual(ArticleCatalogue.objects.count(), 0)
        self.assertFalse(AuditLog.objects.filter(action="catalogue_reprise").exists())

    def test_par_defaut_c_est_un_dry_run(self):
        self._lancer("--specialite", "Sécurité")
        self.assertEqual(CategorieCatalogue.objects.count(), 0)

    def test_specialite_inconnue(self):
        with self.assertRaises(CommandError):
            self._lancer("--specialite", "Inexistante")

    def test_appliquer_reproduit_l_arborescence_et_cree_les_articles(self):
        self._lancer("--appliquer", "--specialite", "Sécurité")
        racine = CategorieCatalogue.objects.get(nom="Incendie")
        sous = CategorieCatalogue.objects.get(nom="Extincteurs")
        self.assertIsNone(racine.parent)
        self.assertEqual(sous.parent, racine)
        self.assertEqual(sous.specialite, self.specialite)
        self.assertEqual(ArticleCatalogue.objects.filter(categorie=sous).count(), 2)
        for m in (self.m1, self.m2, self.m3):
            m.refresh_from_db()
        self.assertEqual(self.m1.article_catalogue, self.m2.article_catalogue)
        self.assertNotEqual(self.m1.article_catalogue, self.m3.article_catalogue)
        self.assertEqual(self.m1.article_catalogue.categorie, sous)
        self.assertEqual(self.m1.article_catalogue.marque, "Sicli")
        self.assertTrue(AuditLog.objects.filter(action="catalogue_reprise").exists())

    def test_rien_n_est_perdu(self):
        avant = {m.pk: (m.folder_id, m.designation, m.ship_id) for m in Asset.objects.all()}
        self._lancer("--appliquer", "--specialite", "Sécurité")
        self.assertEqual(AssetFolder.objects.count(), 2)
        self.assertEqual(Asset.objects.count(), len(avant))
        for m in Asset.objects.all():
            self.assertEqual((m.folder_id, m.designation, m.ship_id), avant[m.pk])
        self.sans_designation.refresh_from_db()
        self.hors_dossier.refresh_from_db()
        self.assertIsNone(self.sans_designation.article_catalogue)
        self.assertIsNone(self.hors_dossier.article_catalogue)

    def test_idempotent(self):
        self._lancer("--appliquer", "--specialite", "Sécurité")
        etat = (CategorieCatalogue.objects.count(), ArticleCatalogue.objects.count())
        self._lancer("--appliquer", "--specialite", "Sécurité")
        self.assertEqual((CategorieCatalogue.objects.count(), ArticleCatalogue.objects.count()), etat)

    def test_ne_remplace_pas_un_article_deja_rattache(self):
        categorie = CategorieCatalogue.objects.create(nom="Autre", specialite=self.specialite)
        article = ArticleCatalogue.objects.create(categorie=categorie, designation="Choix manuel")
        Asset.objects.filter(pk=self.m1.pk).update(article_catalogue=article)
        self._lancer("--appliquer", "--specialite", "Sécurité")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.article_catalogue, article)

    def test_correspondance_csv_par_dossier(self):
        autre = SpecialityChoice.objects.create(name="Machine")
        moteur = AssetFolder.objects.create(name="Moteurs")
        Asset.objects.create(designation="Turbo", folder=moteur, **self.base)
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "correspondance.csv")
            with open(chemin, "w", encoding="utf-8") as f:
                f.write("dossier;specialite\nIncendie;Sécurité\nMoteurs;Machine\n")
            self._lancer("--appliquer", "--correspondance", chemin)
        self.assertEqual(CategorieCatalogue.objects.get(nom="Moteurs").specialite, autre)
        self.assertEqual(CategorieCatalogue.objects.get(nom="Extincteurs").specialite, self.specialite)

    def test_dossier_non_qualifie_ignore_en_application(self):
        moteur = AssetFolder.objects.create(name="Moteurs")
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "correspondance.csv")
            with open(chemin, "w", encoding="utf-8") as f:
                f.write("dossier;specialite\nIncendie;Sécurité\n")
            sortie = self._lancer("--appliquer", "--correspondance", chemin)
        self.assertIn("Moteurs", sortie)
        self.assertFalse(CategorieCatalogue.objects.filter(nom="Moteurs").exists())
        self.assertTrue(CategorieCatalogue.objects.filter(nom="Incendie").exists())
        self.assertTrue(AssetFolder.objects.filter(pk=moteur.pk).exists())
