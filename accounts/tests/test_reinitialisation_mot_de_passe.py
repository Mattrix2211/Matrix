"""Réinitialisation du mot de passe par l'administrateur du bâtiment : droits, mot de passe provisoire à usage unique."""
import base64

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog
from matrix.core.role_thresholds import invalidate_cache
from org.models import RoleThresholdConfig, Sector, Service, Ship


class ReinitialisationTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire MDP", code="MDP")
        service = Service.objects.create(ship=self.navire, name="Service MDP")
        self.secteur = Sector.objects.create(service=service, name="Secteur MDP")
        self.admin = self._marin("admin_mdp", "ADMIN_NAVIRE")
        self.commandant = self._marin("commandant_mdp", "COMMANDANT")
        self.chef = self._marin("chef_mdp", "CHEF_SERVICE")
        self.marin = self._marin("marin_mdp", "EQUIPIER")
        autre = Ship.objects.create(name="Autre MDP", code="AMD")
        self.etranger = self._marin("etranger_mdp", "EQUIPIER", navire=autre)
        self.url = reverse("user-directory")

    def _marin(self, nom, role, navire=None):
        user = User.objects.create_user(username=nom, password="ancien-mdp-123")
        profil = user.profile
        profil.role, profil.ship = role, navire or self.navire
        if navire is None:
            profil.service, profil.sector = self.secteur.service, self.secteur
        profil.save()
        return user

    def reinitialiser(self, acteur, cible, action="set_password"):
        self.client.force_login(acteur)
        return self.client.post(self.url, {"action": action, "pk": cible.pk})

    def test_l_administrateur_obtient_un_mot_de_passe_provisoire_affiche_une_fois(self):
        reponse = self.reinitialiser(self.admin, self.marin)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Cache-Control"], "no-store")
        (utilisateur, mot_de_passe), = reponse.context["provisoires"]
        self.assertContains(reponse, mot_de_passe)
        self.marin.refresh_from_db()
        self.assertTrue(self.marin.check_password(mot_de_passe))
        self.assertTrue(self.marin.profile.mot_de_passe_provisoire)
        self.assertNotIn(mot_de_passe, self.marin.password)
        journal = AuditLog.objects.get(action="reinitialisation_mot_de_passe")
        self.assertEqual((journal.actor, journal.target_user), (self.admin, self.marin))
        self.assertFalse(any(mot_de_passe in (a.details or "") for a in AuditLog.objects.all()))
        self.assertNotContains(self.client.get(self.url), mot_de_passe)

    def test_commandant_et_chef_de_service_ne_peuvent_pas(self):
        for acteur in (self.commandant, self.chef, self.marin):
            self.assertEqual(self.reinitialiser(acteur, self.etranger).status_code, 403, acteur.username)
        self.assertEqual(self.reinitialiser(self.commandant, self.marin).status_code, 403)
        self.marin.refresh_from_db()
        self.assertTrue(self.marin.check_password("ancien-mdp-123"))
        self.assertFalse(AuditLog.objects.filter(action="reinitialisation_mot_de_passe").exists())

    def test_marin_d_un_autre_navire_et_soi_meme_refuses(self):
        self.assertEqual(self.reinitialiser(self.admin, self.etranger).status_code, 302)
        self.assertEqual(self.reinitialiser(self.admin, self.admin).status_code, 302)
        for user in (self.etranger, self.admin):
            user.refresh_from_db()
            self.assertTrue(user.check_password("ancien-mdp-123"))
        self.assertFalse(AuditLog.objects.filter(action="reinitialisation_mot_de_passe").exists())

    def test_action_groupee_borne_au_batiment(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(self.url, {
            "action": "bulk_reset_passwords", "selected_ids": [self.marin.pk, self.etranger.pk, self.admin.pk]})
        self.assertEqual([u.username for u, _ in reponse.context["provisoires"]], ["marin_mdp"])
        self.etranger.refresh_from_db()
        self.assertTrue(self.etranger.check_password("ancien-mdp-123"))
        refus = self.client.post(self.url, {"action": "bulk_reset_passwords", "selected_ids": [self.etranger.pk]})
        self.assertEqual(refus.status_code, 302)

    def test_seuil_configurable_par_la_flotte(self):
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"mot_de_passe_reinitialisation": "COMMANDANT"})
        invalidate_cache(self.navire.id)
        self.addCleanup(invalidate_cache, self.navire.id)
        self.assertEqual(self.reinitialiser(self.commandant, self.marin).status_code, 200)

    def test_bouton_visible_seulement_pour_qui_peut(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url), "Réinitialiser")
        self.client.force_login(self.commandant)
        self.assertNotContains(self.client.get(self.url), "resetPasswordModal\" data-pk")


class ChangementObligatoireTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="provisoire_mdp", password="Provisoire-123!")
        self.marin.profile.mot_de_passe_provisoire = True
        self.marin.profile.save()
        self.client.force_login(self.marin)

    def test_toute_page_renvoie_vers_le_changement(self):
        for url in ("/", "/taches/", "/notifications/"):
            self.assertRedirects(self.client.get(url), reverse("password_change"), fetch_redirect_response=False)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 403)
        reponse = self.client.get("/", HTTP_HX_REQUEST="true")
        self.assertEqual(reponse["HX-Redirect"], reverse("password_change"))

    def test_l_authentification_basic_de_l_api_n_echappe_pas_a_l_obligation(self):
        self.client.logout()
        jeton = base64.b64encode(b"provisoire_mdp:Provisoire-123!").decode()
        reponse = self.client.get("/api/notifications/", HTTP_AUTHORIZATION=f"Basic {jeton}")
        self.assertEqual(reponse.status_code, 403)
        self.assertIn("mot de passe", reponse.json()["detail"])

    def test_page_de_changement_et_deconnexion_restent_accessibles(self):
        self.assertContains(self.client.get(reverse("password_change")), "Votre mot de passe est provisoire")
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)

    def test_le_changement_leve_l_obligation(self):
        reponse = self.client.post(reverse("password_change"), {
            "old_password": "Provisoire-123!", "new_password1": "Nouveau-mdp-solide-42", "new_password2": "Nouveau-mdp-solide-42"})
        self.assertRedirects(reponse, reverse("home"), fetch_redirect_response=False)
        self.marin.refresh_from_db()
        self.assertFalse(self.marin.profile.mot_de_passe_provisoire)
        self.assertTrue(self.marin.check_password("Nouveau-mdp-solide-42"))
        self.assertEqual(self.client.get("/taches/").status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="changement_mot_de_passe", actor=self.marin).exists())

    def test_un_mot_de_passe_refuse_ne_leve_pas_l_obligation(self):
        self.client.post(reverse("password_change"), {
            "old_password": "Provisoire-123!", "new_password1": "123", "new_password2": "123"})
        self.marin.refresh_from_db()
        self.assertTrue(self.marin.profile.mot_de_passe_provisoire)
