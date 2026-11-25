"""Réinitialisation du mot de passe : droits de l'initiateur et code à usage unique (AC-12, AC-16)."""
import base64

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts import reinitialisation
from accounts.models import AuditLog, UserProfile
from matrix.core.role_thresholds import invalidate_cache
from org.models import RoleThresholdConfig, Sector, Service, Ship


class ReinitialisationTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire MDP", code="MDP")
        service = Service.objects.create(ship=self.navire, name="Service MDP")
        self.secteur = Sector.objects.create(service=service, name="Secteur MDP")
        self.admin = self._marin("admin_mdp", "ADMIN_TECHNIQUE")
        self.commandant = self._marin("commandant_mdp", "COMMANDANT")
        self.chef = self._marin("chef_mdp", "CHEF_SERVICE")
        self.marin = self._marin("marin_mdp", "EQUIPIER")
        autre = Ship.objects.create(name="Autre MDP", code="AMD")
        self.etranger = self._marin("etranger_mdp", "EQUIPIER", navire=autre)
        self.url = reverse("user-directory")

    def _marin(self, nom, role, navire=None):
        user = User.objects.create_user(username=nom, password="ancien-mdp-123")
        profil = user.profile
        # « ADMIN_TECHNIQUE » : droits techniques seuls, rôle métier d'équipier (L06).
        profil.administrateur_technique = role == "ADMIN_TECHNIQUE"
        profil.role, profil.ship = ("EQUIPIER" if role == "ADMIN_TECHNIQUE" else role), navire or self.navire
        if navire is None:
            profil.service, profil.sector = self.secteur.service, self.secteur
        profil.save()
        return user

    def reinitialiser(self, acteur, cible, action="set_password"):
        self.client.force_login(acteur)
        return self.client.post(self.url, {"action": action, "pk": cible.pk})

    def test_l_administrateur_obtient_un_code_a_usage_unique_affiche_une_fois(self):
        reponse = self.reinitialiser(self.admin, self.marin)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Cache-Control"], "no-store")
        (utilisateur, demande, code), = reponse.context["codes"]
        self.assertContains(reponse, code)
        self.marin.refresh_from_db()
        self.assertTrue(self.marin.check_password("ancien-mdp-123"))  # rien n'est changé tant que le titulaire n'a pas agi
        self.assertFalse(Client().login(username="marin_mdp", password=code))  # le code n'authentifie jamais
        demande.refresh_from_db()
        for champ in (demande.code_initiateur, demande.code_verificateur):
            self.assertNotIn(code.replace("-", ""), champ.upper())
        journal = AuditLog.objects.get(action="reinitialisation_demandee")
        self.assertEqual((journal.actor, journal.target_user), (self.admin, self.marin))
        self.assertFalse(any(code in (a.details or "") for a in AuditLog.objects.all()))
        self.assertNotContains(self.client.get(self.url), code)

    def test_commandant_et_chef_de_service_ne_peuvent_pas(self):
        for acteur in (self.commandant, self.chef, self.marin):
            self.assertEqual(self.reinitialiser(acteur, self.etranger).status_code, 403, acteur.username)
        self.assertEqual(self.reinitialiser(self.commandant, self.marin).status_code, 403)
        self.marin.refresh_from_db()
        self.assertTrue(self.marin.check_password("ancien-mdp-123"))
        self.assertFalse(AuditLog.objects.filter(action="reinitialisation_demandee").exists())

    def test_marin_d_un_autre_navire_et_soi_meme_refuses(self):
        self.assertEqual(self.reinitialiser(self.admin, self.etranger).status_code, 302)
        self.assertEqual(self.reinitialiser(self.admin, self.admin).status_code, 302)
        for user in (self.etranger, self.admin):
            user.refresh_from_db()
            self.assertTrue(user.check_password("ancien-mdp-123"))
        self.assertFalse(AuditLog.objects.filter(action="reinitialisation_demandee").exists())

    def test_action_groupee_borne_au_batiment(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(self.url, {
            "action": "bulk_reset_passwords", "selected_ids": [self.marin.pk, self.etranger.pk, self.admin.pk]})
        self.assertEqual([u.username for u, _, _ in reponse.context["codes"]], ["marin_mdp"])
        self.etranger.refresh_from_db()
        self.assertTrue(self.etranger.check_password("ancien-mdp-123"))
        refus = self.client.post(self.url, {"action": "bulk_reset_passwords", "selected_ids": [self.etranger.pk]})
        self.assertEqual(refus.status_code, 302)

    def test_seuil_configurable_par_la_flotte(self):
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"mot_de_passe_reinitialisation": "COMMANDANT"})
        invalidate_cache(self.navire.id)
        self.addCleanup(invalidate_cache, self.navire.id)
        # Le seuil se règle, mais n'habilite pas une autorité métier : le commandant ne réinitialise pas (AC-12).
        self.assertEqual(self.reinitialiser(self.commandant, self.marin).status_code, 302)
        self.assertEqual(self.reinitialiser(self.admin, self.marin).status_code, 200)

    def test_bouton_visible_seulement_pour_qui_peut(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url), "Réinitialiser")
        self.client.force_login(self.commandant)
        self.assertNotContains(self.client.get(self.url), "resetPasswordModal\" data-pk")


class CodeEtConnexionTests(TestCase):
    """Le code de réinitialisation n'est pas un mot de passe : aucune session ni authentification par API ne l'accepte."""

    def setUp(self):
        navire = Ship.objects.create(name="Navire code", code="COD")
        self.technique = User.objects.create_user(username="tech_code", password="ancien-mdp-123")
        UserProfile.objects.filter(user=self.technique).update(administrateur_technique=True, ship=navire)
        self.marin = User.objects.create_user(username="marin_code", password="ancien-mdp-123")
        UserProfile.objects.filter(user=self.marin).update(ship=navire)
        self.technique, self.marin = User.objects.get(pk=self.technique.pk), User.objects.get(pk=self.marin.pk)

    def test_le_code_ne_permet_pas_de_se_connecter_ni_d_appeler_l_api(self):
        _, code = reinitialisation.initier(self.technique, self.marin)
        self.assertFalse(Client().login(username="marin_code", password=code))
        self.assertFalse(Client().login(username="marin_code", password=code.replace("-", "")))
        jeton = base64.b64encode(f"marin_code:{code}".encode()).decode()
        self.assertIn(Client().get("/api/notifications/", HTTP_AUTHORIZATION=f"Basic {jeton}").status_code, (401, 403))

    def test_changer_son_mot_de_passe_depuis_le_profil_reste_possible(self):
        self.client.force_login(self.marin)
        reponse = self.client.post(reverse("password_change"), {
            "old_password": "ancien-mdp-123", "new_password1": "Nouveau-mdp-solide-42", "new_password2": "Nouveau-mdp-solide-42"})
        self.assertRedirects(reponse, reverse("home"), fetch_redirect_response=False)
        self.assertTrue(AuditLog.objects.filter(action="changement_mot_de_passe", actor=self.marin).exists())


class RoutesExposeesTests(TestCase):
    def test_reinitialisation_par_courriel_retiree_connexion_et_changement_conservees(self):
        for chemin in ("/accounts/password_reset/", "/accounts/password_reset/done/", "/accounts/reset/x/y/", "/accounts/reset/done/"):
            self.assertEqual(self.client.get(chemin).status_code, 404, chemin)
        self.assertEqual(self.client.get("/accounts/login/").status_code, 200)
        self.assertEqual(reverse("password_change"), "/accounts/password_change/")

    def test_formulaire_de_changement_style(self):
        User.objects.create_user(username="m1", password="pass")
        self.client.login(username="m1", password="pass")
        page = self.client.get(reverse("password_change"))
        self.assertContains(page, 'class="form-control"', count=3)
