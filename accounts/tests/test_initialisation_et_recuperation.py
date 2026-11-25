"""AC-09 : initialisation unique des premières autorités ; récupération exceptionnelle d'un administrateur général."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import AuditLog, InitialisationBatiment, UserProfile
from org.models import Ship

User = get_user_model()


def _compte(nom, role="EQUIPIER", navire=None, **drapeaux):
    utilisateur = User.objects.create_user(username=nom, password="pass", **drapeaux)
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role, "ship": navire})
    return User.objects.get(pk=utilisateur.pk)


def _initialiser(**options):
    sortie = StringIO()
    call_command("initialiser_autorites_batiment", stdout=sortie, **options)
    return sortie.getvalue()


class InitialisationTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.cdt = _compte("futur_cdt")
        self.tech = _compte("futur_tech")

    def test_designe_le_commandant_et_le_technique_independamment(self):
        _initialiser(batiment="BRE", commandant="futur_cdt", technique="futur_tech", autorisation="NOTE-001")
        cdt, tech = UserProfile.objects.get(user=self.cdt), UserProfile.objects.get(user=self.tech)
        self.assertEqual((cdt.role, cdt.administrateur_technique, cdt.ship), ("COMMANDANT", False, self.navire))
        self.assertEqual((tech.role, tech.administrateur_technique), ("EQUIPIER", True))
        trace = AuditLog.objects.get(action="initialisation_batiment")
        self.assertIn("NOTE-001", trace.details)
        self.assertNotIn("pass", trace.details)

    def test_usage_unique_par_batiment(self):
        _initialiser(batiment="BRE", commandant="futur_cdt", autorisation="NOTE-001")
        autre = _compte("autre_cdt")
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="autre_cdt", autorisation="NOTE-002")
        self.assertEqual(UserProfile.objects.get(user=autre).role, "EQUIPIER")
        self.assertEqual(InitialisationBatiment.objects.count(), 1)

    def test_refuse_si_un_commandant_existe_deja(self):
        _compte("en_place", "COMMANDANT", self.navire)
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="futur_cdt", autorisation="NOTE-001")
        self.assertFalse(InitialisationBatiment.objects.exists())

    def test_le_cumul_exige_une_option_explicite(self):
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="futur_cdt", technique="futur_cdt", autorisation="NOTE-001")
        self.assertFalse(InitialisationBatiment.objects.exists())
        _initialiser(batiment="BRE", commandant="futur_cdt", technique="futur_cdt", autorisation="NOTE-001", accepter_cumul=True)
        profil = UserProfile.objects.get(user=self.cdt)
        self.assertEqual((profil.role, profil.administrateur_technique), ("COMMANDANT", True))

    def test_autorisation_obligatoire_et_compte_technique_sans_autorite(self):
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="futur_cdt", autorisation="  ")
        chef = _compte("chef", "CHEF_SERVICE")
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="futur_cdt", technique="chef", autorisation="NOTE-001")
        self.assertEqual(UserProfile.objects.get(user=chef).role, "CHEF_SERVICE")
        self.assertEqual(UserProfile.objects.get(user=self.cdt).role, "EQUIPIER")  # rien n'est appliqué à moitié

    def test_un_administrateur_general_n_est_pas_designe_commandant(self):
        _compte("general", "MASTER_ADMIN")
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="general", autorisation="NOTE-001")


class RecuperationTests(TestCase):
    def test_emet_un_mot_de_passe_provisoire_pour_un_administrateur_general_seulement(self):
        general = _compte("general", "MASTER_ADMIN")
        simple = _compte("marin")
        sortie = StringIO()
        call_command("recuperer_acces_administrateur", identifiant="general", autorisation="NOTE-9", stdout=sortie)
        mot_de_passe = sortie.getvalue().split(": ")[-1].strip()
        general.refresh_from_db()
        self.assertTrue(general.check_password(mot_de_passe))
        profil = UserProfile.objects.get(user=general)
        self.assertTrue(profil.mot_de_passe_provisoire and profil.mot_de_passe_provisoire_expire_le)
        trace = AuditLog.objects.get(action="recuperation_acces")
        self.assertNotIn(mot_de_passe, trace.details)
        with self.assertRaises(CommandError):
            call_command("recuperer_acces_administrateur", identifiant="marin", autorisation="NOTE-9", stdout=StringIO())
        self.assertTrue(simple.check_password("pass"))
