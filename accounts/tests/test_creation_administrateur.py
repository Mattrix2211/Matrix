"""Création du compte administrateur : aucun identifiant prédéfini, validation Django conservée."""
import io
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase

User = get_user_model()
RACINE = Path(__file__).resolve().parents[2]
SECRET_FORT = "Zx9!vQ7#mTe4Lw2p"


class _Terminal(io.StringIO):
    """Entrée simulant un terminal : requis par createsuperuser en mode interactif."""

    def isatty(self):
        return True


class CodeActifSansIdentifiants(TestCase):
    def test_scripts_a_identifiants_codes_en_dur_supprimes(self):
        self.assertFalse((RACINE / "scripts" / "create_superuser.py").exists())
        self.assertFalse((RACINE / "reset_admin.bat").exists())

    def test_aucun_script_de_lancement_ne_cree_un_admin_avec_mot_de_passe_en_clair(self):
        fichiers = list(RACINE.glob("*.bat")) + list((RACINE / "scripts").glob("*.py"))
        self.assertTrue(fichiers)
        for f in fichiers:
            texte = f.read_text(encoding="utf-8", errors="replace")
            self.assertNotRegex(texte, r"create_superuser\s*\(", f.name)
            self.assertNotRegex(texte, r"(?i)mot de passe\s*:\s*\S*\s*$|password\s*=\s*['\"][^'\"]{4,}['\"]", f.name)

    def test_le_script_windows_utilise_la_commande_native(self):
        texte = (RACINE / "create_admin.bat").read_text(encoding="utf-8")
        self.assertIn("python manage.py createsuperuser", texte)
        self.assertNotIn("--noinput", texte)


class ValidationDuMotDePasse(TestCase):
    def test_les_validateurs_sont_configures_et_refusent_les_secrets_faibles(self):
        for faible in ("12345678", "password", "azerty", "court1"):
            with self.assertRaises(ValidationError, msg=faible):
                validate_password(faible)
        validate_password(SECRET_FORT)

    def _creer_en_interactif(self, mot_de_passe, reponse_contournement="n"):
        saisies = iter(["adm_test", "adm@example.test"])
        with mock.patch("builtins.input", side_effect=lambda *a, **k: next(saisies, reponse_contournement)), \
             mock.patch("getpass.getpass", side_effect=[mot_de_passe, mot_de_passe, KeyboardInterrupt]):
            sortie = io.StringIO()
            call_command("createsuperuser", stdin=_Terminal(), stdout=sortie, stderr=sortie)
        return sortie.getvalue()

    def test_creation_interactive_refusee_avec_un_secret_faible(self):
        with self.assertRaises(SystemExit):  # Django abandonne quand la saisie est interrompue
            self._creer_en_interactif("12345678")
        self.assertFalse(User.objects.filter(username="adm_test").exists())

    def test_creation_interactive_legitime_sans_affichage_du_secret(self):
        sortie = self._creer_en_interactif(SECRET_FORT)
        u = User.objects.get(username="adm_test")
        self.assertTrue(u.is_superuser and u.is_staff and u.is_active)
        self.assertTrue(u.check_password(SECRET_FORT))
        self.assertNotIn(SECRET_FORT, sortie)


class CompteExistant(TestCase):
    def test_un_compte_existant_n_est_ni_reinitialise_ni_modifie(self):
        u = User.objects.create_superuser("adm_exist", "e@example.test", SECRET_FORT)
        avant = User.objects.get(pk=u.pk).password
        sortie = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("createsuperuser", interactive=False, username="adm_exist",
                         email="autre@example.test", stdout=sortie, stderr=sortie)
        u.refresh_from_db()
        self.assertEqual(u.password, avant)
        self.assertEqual(u.email, "e@example.test")
        self.assertEqual(User.objects.filter(username="adm_exist").count(), 1)

    def test_sans_secret_le_mode_non_interactif_ne_donne_aucun_acces_connu(self):
        call_command("createsuperuser", interactive=False, username="adm_sans", email="s@example.test",
                     stdout=io.StringIO())
        self.assertFalse(User.objects.get(username="adm_sans").has_usable_password())
