"""AC-09 : initialisation unique des premières autorités ; récupération exceptionnelle d'un administrateur général."""
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts import recuperation, reinitialisation
from accounts.models import AuditLog, DemandeReinitialisation, InitialisationBatiment, OperateurRecuperation, UserProfile
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
    """AC-17 : deux opérateurs habilités, authentifiés séparément, exécutions distinctes, justification, délai, double code."""

    def setUp(self):
        self.operateur1 = recuperation.habiliter_operateur("Opérateur Un", "systeme-un", "phrase-secrete-un-1")
        self.operateur2 = recuperation.habiliter_operateur("Opérateur Deux", "systeme-deux", "phrase-secrete-deux-2")
        self.general = _compte("general")
        UserProfile.objects.filter(user=self.general).update(administrateur_general=True)
        self.simple = _compte("marin")

    def _parcours(self, compte="general", attribuer=False):
        demande, a = recuperation.ouvrir(self.operateur1, compte, "perte du mot de passe, accord du chef d'installation", attribuer)
        _, b = recuperation.valider(self.operateur2, demande.pk)
        return demande, a, b

    def test_deux_codes_et_deux_operateurs_distincts_permettent_la_recuperation(self):
        demande, a, b = self._parcours()
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("general", a, "", "Nouveau-mdp-solide-42")  # un seul code ne suffit pas
        reinitialisation.utiliser("general", a, b, "Nouveau-mdp-solide-42")
        self.assertTrue(User.objects.get(pk=self.general.pk).check_password("Nouveau-mdp-solide-42"))
        textes = " ".join(t.details for t in AuditLog.objects.all())
        self.assertNotIn(a, textes)
        self.assertNotIn(b, textes)
        for action in ("recuperation_ouverte", "recuperation_validee", "reinitialisation_effectuee"):
            self.assertTrue(AuditLog.objects.filter(action=action, target_user=self.general).exists(), action)

    def test_un_seul_operateur_ne_peut_pas_valider_sa_propre_demande(self):
        demande, _ = recuperation.ouvrir(self.operateur1, "general", "justification", False)
        with self.assertRaises(PermissionDenied):
            recuperation.valider(self.operateur1, demande.pk)
        # même identité système sous un autre nom d'opérateur : refusée aussi
        faux = OperateurRecuperation.objects.create(nom="Alias", identifiant_systeme="systeme-un-bis", phrase="x")
        faux.identifiant_systeme = self.operateur1.identifiant_systeme
        with self.assertRaises(PermissionDenied):
            recuperation.valider(faux, demande.pk)
        demande.refresh_from_db()
        self.assertEqual(demande.statut, DemandeReinitialisation.Statut.EN_ATTENTE_VERIFICATION)

    def test_authentification_independante_de_chaque_operateur(self):
        with self.assertRaises(PermissionDenied):
            recuperation.authentifier_operateur("systeme-un", "mauvaise-phrase")
        with self.assertRaises(PermissionDenied):
            recuperation.authentifier_operateur("inconnu", "phrase-secrete-un-1")
        with self.assertRaises(PermissionDenied):
            recuperation.authentifier_operateur("systeme-un", "phrase-secrete-deux-2")  # la phrase d'un autre ne vaut pas
        self.assertEqual(recuperation.authentifier_operateur("systeme-deux", "phrase-secrete-deux-2"), self.operateur2)
        self.assertTrue(AuditLog.objects.filter(action="recuperation_authentification_refusee").exists())

    def test_justification_obligatoire_compte_cible_et_delai(self):
        with self.assertRaises(ValidationError):
            recuperation.ouvrir(self.operateur1, "general", "   ", False)
        with self.assertRaises(ValidationError):
            recuperation.ouvrir(self.operateur1, "marin", "justification", False)  # pas un administrateur général
        demande, _ = recuperation.ouvrir(self.operateur1, "general", "justification", False)
        DemandeReinitialisation.objects.filter(pk=demande.pk).update(expire_le=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValidationError):
            recuperation.valider(self.operateur2, demande.pk)

    def test_aucun_administrateur_general_disponible_les_operateurs_en_designent_un(self):
        UserProfile.objects.filter(user=self.general).update(administrateur_general=False)
        with self.assertRaises(ValidationError):
            recuperation.ouvrir(self.operateur1, "marin", "justification", False)
        demande, a, b = self._parcours("marin", attribuer=True)
        reinitialisation.utiliser("marin", a, b, "Nouveau-mdp-solide-42")
        self.assertTrue(UserProfile.objects.get(user=self.simple).administrateur_general)
        with self.assertRaises(ValidationError):  # un administrateur général existe désormais
            recuperation.ouvrir(self.operateur1, "general", "justification", True)

    def test_habilitation_limitee_a_deux_operateurs_et_phrase_solide(self):
        with self.assertRaises(ValidationError):
            recuperation.habiliter_operateur("Troisième", "systeme-trois", "phrase-secrete-trois-3")
        OperateurRecuperation.objects.all().delete()
        with self.assertRaises(ValidationError):
            recuperation.habiliter_operateur("Court", "systeme-court", "court")
        self.assertFalse(any("phrase-secrete" in a.details for a in AuditLog.objects.all()))

    def test_les_sessions_anterieures_sont_revoquees(self):
        session = Client()
        session.force_login(self.general)
        _, a, b = self._parcours()
        reinitialisation.utiliser("general", a, b, "Nouveau-mdp-solide-42")
        self.assertEqual(session.get(reverse("mon-profil")).status_code, 302)

    def test_commande_en_deux_executions_avec_phrases_saisies_et_identites_distinctes(self):
        sortie = StringIO()
        with mock.patch("getpass.getpass", return_value="phrase-secrete-un-1"), \
                mock.patch("accounts.recuperation.identite_systeme", return_value="systeme-un"):
            call_command("recuperer_acces_administrateur", "ouvrir", "--identifiant", "general", "--justification", "perte", stdout=sortie)
        demande = DemandeReinitialisation.objects.get(user=self.general)
        with mock.patch("getpass.getpass", return_value="phrase-secrete-un-1"), \
                mock.patch("accounts.recuperation.identite_systeme", return_value="systeme-un"):
            with self.assertRaises(CommandError):  # même opérateur : refusé
                call_command("recuperer_acces_administrateur", "valider", "--demande", str(demande.pk), stdout=StringIO())
        with mock.patch("getpass.getpass", return_value="phrase-secrete-deux-2"), \
                mock.patch("accounts.recuperation.identite_systeme", return_value="systeme-deux"):
            call_command("recuperer_acces_administrateur", "valider", "--demande", str(demande.pk), stdout=sortie)
        demande.refresh_from_db()
        self.assertEqual(demande.statut, DemandeReinitialisation.Statut.ACTIVE)
        with mock.patch("getpass.getpass", return_value="phrase-secrete-un-1"), \
                mock.patch("accounts.recuperation.identite_systeme", return_value="inconnu"):
            with self.assertRaises(CommandError):  # identité système non habilitée
                call_command("recuperer_acces_administrateur", "ouvrir", "--identifiant", "general", "--justification", "x", stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_la_procedure_simplifiee_est_impossible_en_production(self):
        with self.assertRaises(CommandError):
            call_command("recuperer_acces_administrateur", "simplifie", "--identifiant", "general", stdout=StringIO())
        self.assertFalse(DemandeReinitialisation.objects.exists())

    @override_settings(DEBUG=True)
    def test_la_procedure_simplifiee_en_developpement_reste_tracee_et_ne_laisse_aucun_operateur(self):
        OperateurRecuperation.objects.all().delete()
        sortie = StringIO()
        call_command("recuperer_acces_administrateur", "simplifie", "--identifiant", "general", stdout=sortie)
        self.assertIn("Codes de développement", sortie.getvalue())
        self.assertFalse(OperateurRecuperation.objects.exists())
        self.assertTrue(AuditLog.objects.filter(action="recuperation_simplifiee_developpement").exists())


class ContraintesTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne", code="BRE")

    def test_la_contrainte_d_unicite_verrouille_meme_sans_commandant_actif(self):
        premier = _compte("premier")
        _initialiser(batiment="BRE", commandant="premier", autorisation="NOTE-001")
        User.objects.filter(pk=premier.pk).update(is_active=False)  # plus de commandant actif : seul le verrou en base reste
        _compte("second_essai")
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="second_essai", autorisation="NOTE-002")
        self.assertEqual(InitialisationBatiment.objects.count(), 1)

    def test_un_compte_deja_technique_n_est_pas_commandant_sans_cumul_explicite(self):
        _compte("technique_existant").profile  # noqa: B018
        UserProfile.objects.filter(user__username="technique_existant").update(administrateur_technique=True)
        _compte("autre")
        with self.assertRaises(CommandError):
            _initialiser(batiment="BRE", commandant="technique_existant", technique="autre", autorisation="NOTE-001")
        self.assertFalse(InitialisationBatiment.objects.exists())
