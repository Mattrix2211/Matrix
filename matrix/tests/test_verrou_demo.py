"""Verrou des commandes de démonstration (AUD-009) : refus hors base dédiée, aucun profil modifié, mots de passe non prévisibles."""
import os
import stat
import tempfile
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock, skipIf

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command
from django.core.checks import run_checks
from django.test import SimpleTestCase, TestCase, override_settings

from accounts.models import InstanceDemo
from matrix.core import instance_demo
from matrix.core.instance_demo import COMPTES_DEMO

User = get_user_model()
GENERATEURS = ("seed_demo", "seed_demo_mer_quai", "seed_demo_dense", "seed_demo_metier")
COMMANDES = Path(settings.BASE_DIR) / "matrix" / "core" / "management" / "commands"


@contextmanager
def conditions_reelles(base=None, debug=True, activation="1", vendor=None):
    """Conditions d'un vrai processus (hors tests) : DEBUG, variable d'activation, moteur et fichier voisin au choix."""
    patches = [mock.patch.object(instance_demo, "en_test", return_value=False), override_settings(DEBUG=debug),
               mock.patch.dict(os.environ, {instance_demo.VARIABLE_ACTIVATION: activation or ""})]
    if base is not None:
        patches.append(mock.patch.object(instance_demo, "chemin_base", return_value=base))
    if vendor is not None:
        patches.append(mock.patch.object(instance_demo, "connection", SimpleNamespace(vendor=vendor, settings_dict={"NAME": "x"})))
    for patch in patches:
        patch.__enter__()
    try:
        yield
    finally:
        for patch in reversed(patches):
            patch.__exit__(None, None, None)


class RefusHorsBaseDedieeTests(TestCase):
    """Chaque condition manquante suffit à refuser, sans rien écrire."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "demo.sqlite3"

    def _refus(self, commande="seed_demo", **options):
        with self.assertRaises(CommandError) as ctx:
            call_command(commande, stdout=StringIO())
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(InstanceDemo.objects.exists())
        return str(ctx.exception)

    @skipIf(settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3", "chemin de base simulé : SQLite seulement")
    def test_refus_hors_debug(self):
        self.base.with_name(self.base.name + instance_demo.SUFFIXE_MARQUEUR).touch()
        for commande in GENERATEURS:
            with conditions_reelles(self.base, debug=False):
                self.assertIn("DEBUG", self._refus(commande))

    @skipIf(settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3", "chemin de base simulé : SQLite seulement")
    def test_refus_sans_variable_d_activation_meme_en_debug(self):
        self.base.with_name(self.base.name + instance_demo.SUFFIXE_MARQUEUR).touch()
        for commande in GENERATEURS:
            with conditions_reelles(self.base, activation=None):
                self.assertIn(instance_demo.VARIABLE_ACTIVATION, self._refus(commande))

    @skipIf(settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3", "chemin de base simulé : SQLite seulement")
    def test_refus_sans_fichier_voisin_de_base_dediee(self):
        with conditions_reelles(self.base):
            self.assertIn(instance_demo.SUFFIXE_MARQUEUR, self._refus())

    def test_refus_sur_postgresql(self):
        with conditions_reelles(vendor="postgresql"):
            self.assertIn("postgresql", self._refus())

    def test_toutes_les_conditions_manquantes_sont_signalees(self):
        with conditions_reelles(self.base, debug=False, activation=None):
            message = self._refus()
        for attendu in ("DEBUG", instance_demo.VARIABLE_ACTIVATION):
            self.assertIn(attendu, message)

    def test_base_non_vide_et_non_marquee_est_refusee_sans_rien_modifier(self):
        reel = User.objects.create_user(username="equipier_a", password="un-vrai-mot-de-passe")
        profil = reel.profile
        profil.role, profil.grade = "COMMANDANT", "CF"
        profil.save()
        avant = (User.objects.count(), reel.password, profil.role, profil.grade, profil.ship_id)
        for commande in GENERATEURS:
            with self.assertRaises(CommandError):
                call_command(commande, stdout=StringIO())
        reel.refresh_from_db()
        profil.refresh_from_db()
        self.assertEqual((User.objects.count(), reel.password, profil.role, profil.grade, profil.ship_id), avant)
        self.assertFalse(InstanceDemo.objects.exists())

    def test_les_commandes_dependantes_refusent_une_base_vide_non_marquee(self):
        for commande in GENERATEURS[1:]:
            with self.assertRaises(CommandError):
                call_command(commande, stdout=StringIO())
        self.assertEqual(User.objects.count(), 0)


class RemplissageEtMotsDePasseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        instance_demo.oublier_mots_de_passe()
        cls.sortie = StringIO()
        call_command("seed_demo", stdout=cls.sortie)

    def test_le_marqueur_est_ecrit_une_fois_et_la_commande_reste_rejouable(self):
        self.assertEqual(InstanceDemo.objects.count(), 1)
        nombre = User.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual((InstanceDemo.objects.count(), User.objects.count()), (1, nombre))

    def test_aucun_compte_n_a_un_mot_de_passe_previsible(self):
        self.assertEqual(instance_demo.comptes_a_mot_de_passe_herite(), [])
        self.assertFalse(User.objects.get(username="equipier_a").check_password("pass"))
        self.assertFalse(User.objects.get(username="admin").check_password("admin"))

    def test_les_comptes_utilisent_les_mots_de_passe_attendus(self):
        self.assertTrue(User.objects.get(username="equipier_a").check_password(instance_demo.mot_de_passe_commun()))
        self.assertTrue(User.objects.get(username="admin").check_password(instance_demo.mot_de_passe_admin()))
        self.assertNotEqual(instance_demo.mot_de_passe_commun(), instance_demo.mot_de_passe_admin())

    def test_aucun_secret_dans_la_sortie_de_la_commande(self):
        sortie = self.sortie.getvalue()
        self.assertNotIn(instance_demo.mot_de_passe_commun(), sortie)
        self.assertNotIn(instance_demo.mot_de_passe_admin(), sortie)
        self.assertNotIn("« pass »", sortie)

    def test_les_comptes_crees_sont_des_comptes_de_demonstration_connus(self):
        self.assertLessEqual(set(User.objects.values_list("username", flat=True)), COMPTES_DEMO)
        self.assertEqual(instance_demo.comptes_etrangers(), [])


class ProtectionDeLaProductionTests(TestCase):
    def test_une_base_marquee_ne_sert_pas_hors_debug(self):
        InstanceDemo.objects.create(commande="seed_demo")
        with mock.patch.object(instance_demo, "en_test", return_value=False):
            with override_settings(DEBUG=False):
                self.assertIn("démonstration", instance_demo.erreur_base_de_demonstration_en_production())
                with self.assertRaises(ImproperlyConfigured):
                    instance_demo.exiger_pas_de_base_de_demo_en_production()
                self.assertTrue([e for e in run_checks() if e.id == "matrix.E001"])
            with override_settings(DEBUG=True):
                self.assertEqual(instance_demo.erreur_base_de_demonstration_en_production(), "")
                self.assertFalse([e for e in run_checks() if e.id == "matrix.E001"])

    def test_une_base_non_marquee_n_est_pas_bloquee(self):
        with mock.patch.object(instance_demo, "en_test", return_value=False), override_settings(DEBUG=False):
            self.assertEqual(instance_demo.erreur_base_de_demonstration_en_production(), "")


class MarquerInstanceDemoTests(TestCase):
    def test_refus_si_un_compte_n_est_pas_fictif_et_rien_n_est_modifie(self):
        User.objects.create_user(username="equipier_a", password="pass")
        User.objects.create_user(username="vrai_marin", password="x")
        with self.assertRaises(CommandError):
            call_command("marquer_instance_demo", "--regenerer-mots-de-passe", stdout=StringIO())
        self.assertFalse(InstanceDemo.objects.exists())
        self.assertTrue(User.objects.get(username="equipier_a").check_password("pass"))

    def test_marque_et_remplace_seulement_les_anciens_mots_de_passe_previsibles(self):
        User.objects.create_user(username="equipier_a", password="pass")
        User.objects.create_user(username="admin", password="admin")
        User.objects.create_user(username="cdt_a", password="choisi-par-le-testeur")
        sortie = StringIO()
        call_command("marquer_instance_demo", "--regenerer-mots-de-passe", stdout=sortie)
        self.assertTrue(InstanceDemo.objects.exists())
        self.assertTrue(User.objects.get(username="equipier_a").check_password(instance_demo.mot_de_passe_commun()))
        self.assertTrue(User.objects.get(username="admin").check_password(instance_demo.mot_de_passe_admin()))
        self.assertTrue(User.objects.get(username="cdt_a").check_password("choisi-par-le-testeur"))
        self.assertNotIn(instance_demo.mot_de_passe_commun(), sortie.getvalue())

    @skipIf(settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3", "moteur simulé : SQLite seulement")
    def test_refus_hors_debug(self):
        with conditions_reelles(debug=False):
            with self.assertRaises(CommandError):
                call_command("marquer_instance_demo", stdout=StringIO())
        self.assertFalse(InstanceDemo.objects.exists())


class VerifierInstanceTests(TestCase):
    def test_signale_les_mots_de_passe_previsibles_sans_rien_modifier(self):
        User.objects.create_user(username="equipier_a", password="pass")
        User.objects.create_user(username="admin", password="admin")
        User.objects.create_user(username="sain", password="un-mot-de-passe-solide-1234")
        avant = list(User.objects.order_by("pk").values_list("password", flat=True))
        with self.assertRaises(CommandError) as ctx:
            call_command("verifier_instance", stdout=StringIO())
        self.assertIn("equipier_a", str(ctx.exception))
        self.assertIn("admin", str(ctx.exception))
        self.assertNotIn("sain", str(ctx.exception))
        self.assertEqual(list(User.objects.order_by("pk").values_list("password", flat=True)), avant)
        self.assertFalse(InstanceDemo.objects.exists())

    def test_instance_saine(self):
        User.objects.create_user(username="sain", password="un-mot-de-passe-solide-1234")
        sortie = StringIO()
        call_command("verifier_instance", stdout=sortie)
        self.assertIn("Aucun compte", sortie.getvalue())


class MotsDePasseDeDemonstrationTests(SimpleTestCase):
    def setUp(self):
        instance_demo.oublier_mots_de_passe()
        self.addCleanup(instance_demo.oublier_mots_de_passe)

    def test_mots_de_passe_fournis_par_l_operateur(self):
        with mock.patch.dict(os.environ, {"MATRIX_DEMO_PASSWORD": "fourni-commun-1", "MATRIX_DEMO_ADMIN_PASSWORD": "fourni-admin-2"}):
            self.assertEqual((instance_demo.mot_de_passe_commun(), instance_demo.mot_de_passe_admin()), ("fourni-commun-1", "fourni-admin-2"))

    def test_mots_de_passe_generes_aleatoires_et_non_previsibles(self):
        with mock.patch.dict(os.environ, {"MATRIX_DEMO_PASSWORD": "", "MATRIX_DEMO_ADMIN_PASSWORD": ""}):
            premiers = (instance_demo.mot_de_passe_commun(), instance_demo.mot_de_passe_admin())
            instance_demo.oublier_mots_de_passe()
            seconds = (instance_demo.mot_de_passe_commun(), instance_demo.mot_de_passe_admin())
        for valeur in (*premiers, *seconds):
            self.assertGreaterEqual(len(valeur), 12)
            self.assertNotIn(valeur, instance_demo.MOTS_DE_PASSE_HERITES)
        self.assertNotEqual(premiers, seconds)
        self.assertNotEqual(premiers[0], premiers[1])

    def test_fichier_d_identifiants_cree_une_fois_lisible_par_le_proprietaire_seul(self):
        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / "sous" / "identifiants_demo.txt"
            env = {"MATRIX_DEMO_PASSWORD": "", "MATRIX_DEMO_ADMIN_PASSWORD": "", "MATRIX_DEMO_IDENTIFIANTS": str(fichier)}
            with mock.patch.dict(os.environ, env), mock.patch.object(instance_demo, "en_test", return_value=False):
                commun, admin = instance_demo.mot_de_passe_commun(), instance_demo.mot_de_passe_admin()
                self.assertTrue(fichier.is_file())
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(fichier.stat().st_mode), 0o600)
                self.assertIn(commun, fichier.read_text(encoding="utf-8"))
                instance_demo.oublier_mots_de_passe()
                self.assertEqual((instance_demo.mot_de_passe_commun(), instance_demo.mot_de_passe_admin()), (commun, admin))
                self.assertIn(str(fichier), instance_demo.description_mots_de_passe())
                self.assertNotIn(commun, instance_demo.description_mots_de_passe())

    def test_pas_de_fichier_dans_un_processus_de_tests(self):
        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / "identifiants_demo.txt"
            with mock.patch.dict(os.environ, {"MATRIX_DEMO_PASSWORD": "", "MATRIX_DEMO_ADMIN_PASSWORD": "", "MATRIX_DEMO_IDENTIFIANTS": str(fichier)}):
                instance_demo.mot_de_passe_commun()
            self.assertFalse(fichier.exists())


class SourcesDesGenerateursTests(SimpleTestCase):
    def test_aucun_generateur_ne_contient_de_mot_de_passe_previsible(self):
        for nom in GENERATEURS:
            source = (COMMANDES / f"{nom}.py").read_text(encoding="utf-8")
            for interdit in ('"pass"', "'pass'", 'mdp="admin"', 'MOT_DE_PASSE = '):
                self.assertNotIn(interdit, source, f"{nom} : {interdit}")

    def test_chaque_generateur_appelle_le_verrou_en_premier(self):
        for nom in GENERATEURS:
            source = (COMMANDES / f"{nom}.py").read_text(encoding="utf-8")
            self.assertIn("exiger_base_demo(", source, nom)


@skipIf(settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3", "chemin de base simulé : SQLite seulement")
class PreuveDePreparationTests(TestCase):
    """Le marquage repose sur la preuve écrite par la préparation de l'instance, jamais sur les seuls noms de comptes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "demo.sqlite3"
        self.preuve = self.base.with_name(self.base.name + instance_demo.SUFFIXE_MARQUEUR)
        instance_demo.oublier_mots_de_passe()
        self.addCleanup(instance_demo.oublier_mots_de_passe)

    def _marquer(self, *args):
        with conditions_reelles(self.base):
            call_command("marquer_instance_demo", *args, stdout=StringIO())

    def test_un_vrai_compte_admin_sans_preuve_de_preparation_n_est_jamais_marque(self):
        User.objects.create_user(username="admin", password="mot-de-passe-reel-1234")
        with self.assertRaises(CommandError):
            self._marquer()
        self.assertFalse(InstanceDemo.objects.exists())
        self.assertFalse(self.preuve.exists())  # la commande ne fabrique jamais la preuve

    def test_des_noms_de_demonstration_ne_suffisent_pas(self):
        for nom in ("admin", "commandant", "cdt_a"):
            User.objects.create_user(username=nom, password="x")
        with self.assertRaises(CommandError):
            self._marquer("--regenerer-mots-de-passe")
        self.assertFalse(InstanceDemo.objects.exists())
        self.assertTrue(User.objects.get(username="cdt_a").check_password("x"))

    def test_avec_la_preuve_et_des_comptes_fictifs_la_base_est_marquee_avec_l_identifiant(self):
        self.preuve.write_text("instance : abc123\n", encoding="utf-8")
        User.objects.create_user(username="equipier_a", password="pass")
        self._marquer()
        self.assertEqual(InstanceDemo.objects.get().identifiant, "abc123")
        self.assertEqual(self.preuve.read_text(encoding="utf-8"), "instance : abc123\n")  # preuve intacte

    def test_la_preuve_ne_dispense_pas_de_la_liste_des_comptes_fictifs(self):
        self.preuve.write_text("instance : abc123\n", encoding="utf-8")
        User.objects.create_user(username="vrai_marin", password="x")
        with self.assertRaises(CommandError):
            self._marquer()
        self.assertFalse(InstanceDemo.objects.exists())

    def test_la_preuve_d_une_autre_instance_est_refusee(self):
        self.preuve.write_text("instance : instance-b\n", encoding="utf-8")
        InstanceDemo.objects.create(commande="seed_demo", identifiant="instance-a")
        User.objects.create_user(username="equipier_a", password="x")
        with conditions_reelles(self.base):
            for commande in GENERATEURS:
                with self.assertRaises(CommandError) as ctx:
                    call_command(commande, stdout=StringIO())
                self.assertIn("autre instance", str(ctx.exception))
        self.assertEqual(User.objects.count(), 1)

    def test_premier_remplissage_enregistre_l_identifiant_de_l_instance(self):
        self.preuve.write_text("instance : xyz789\n", encoding="utf-8")
        with conditions_reelles(self.base):
            instance_demo.exiger_base_demo("seed_demo", creation=True)
        self.assertEqual(InstanceDemo.objects.get().identifiant, "xyz789")

    def test_mots_de_passe_par_defaut_dans_un_fichier_propre_a_chaque_base(self):
        autre = Path(self.tmp.name) / "autre.sqlite3"
        with mock.patch.dict(os.environ, {"MATRIX_DEMO_IDENTIFIANTS": ""}):
            with mock.patch.object(instance_demo, "chemin_base", return_value=self.base):
                premier = instance_demo._fichier_identifiants()
            with mock.patch.object(instance_demo, "chemin_base", return_value=autre):
                second = instance_demo._fichier_identifiants()
        self.assertEqual((premier.name, second.name), ("demo.sqlite3.identifiants", "autre.sqlite3.identifiants"))
        self.assertNotEqual(premier, second)

    def test_un_fichier_d_identifiants_d_une_autre_instance_n_est_ni_utilise_ni_ecrase(self):
        self.preuve.write_text("instance : instance-b\n", encoding="utf-8")
        fichier = Path(self.tmp.name) / "demo.sqlite3.identifiants"
        contenu = "comptes : secret-a\nadmin : secret-admin-a\ninstance : instance-a\n"
        fichier.write_text(contenu, encoding="utf-8")
        env = {"MATRIX_DEMO_PASSWORD": "", "MATRIX_DEMO_ADMIN_PASSWORD": "", "MATRIX_DEMO_IDENTIFIANTS": str(fichier)}
        with mock.patch.dict(os.environ, env), conditions_reelles(self.base):
            with self.assertRaises(CommandError):
                instance_demo.mot_de_passe_commun()
        self.assertEqual(fichier.read_text(encoding="utf-8"), contenu)

    def test_le_fichier_d_identifiants_porte_l_identifiant_de_l_instance_et_se_relit(self):
        self.preuve.write_text("instance : abc123\n", encoding="utf-8")
        fichier = Path(self.tmp.name) / "demo.sqlite3.identifiants"
        env = {"MATRIX_DEMO_PASSWORD": "", "MATRIX_DEMO_ADMIN_PASSWORD": "", "MATRIX_DEMO_IDENTIFIANTS": str(fichier)}
        with mock.patch.dict(os.environ, env), conditions_reelles(self.base):
            commun = instance_demo.mot_de_passe_commun()
            self.assertIn("instance : abc123", fichier.read_text(encoding="utf-8"))
            instance_demo.oublier_mots_de_passe()
            self.assertEqual(instance_demo.mot_de_passe_commun(), commun)
