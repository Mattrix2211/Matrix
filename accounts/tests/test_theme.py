from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Themes, UserProfile


class ThemeUtilisateurTests(TestCase):
    """Mode clair par défaut, mode sombre activé manuellement par chaque marin
    et mémorisé dans son profil (docs/UX.md §17)."""

    def setUp(self):
        self.marin = User.objects.create_user(username="marin_theme", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})
        self.autre = User.objects.create_user(username="autre_theme", password="pass")
        UserProfile.objects.update_or_create(user=self.autre, defaults={"role": "EQUIPIER"})
        self.url = "/users/theme/"

    def test_theme_clair_par_defaut(self):
        self.assertEqual(self.marin.profile.theme, Themes.CLAIR)
        self.client.login(username="marin_theme", password="pass")
        r = self.client.get("/users/profil/")
        self.assertContains(r, 'data-theme="clair"')
        self.assertNotContains(r, 'data-bs-theme="dark"')
        self.assertContains(r, "Passer en mode sombre")

    def test_bascule_en_un_clic_memorisee_dans_le_profil(self):
        self.client.login(username="marin_theme", password="pass")
        r = self.client.post(self.url, {"next": "/users/profil/"})
        self.assertRedirects(r, "/users/profil/")
        self.marin.profile.refresh_from_db()
        self.assertEqual(self.marin.profile.theme, Themes.SOMBRE)
        r = self.client.get("/users/profil/")
        self.assertContains(r, 'data-theme="sombre"')
        self.assertContains(r, 'data-bs-theme="dark"')
        self.assertContains(r, "Passer en mode clair")

    def test_seconde_bascule_revient_au_clair(self):
        self.client.login(username="marin_theme", password="pass")
        self.client.post(self.url)
        self.client.post(self.url)
        self.marin.profile.refresh_from_db()
        self.assertEqual(self.marin.profile.theme, Themes.CLAIR)

    def test_le_choix_est_propre_a_chaque_marin(self):
        self.client.login(username="marin_theme", password="pass")
        self.client.post(self.url)
        self.autre.profile.refresh_from_db()
        self.assertEqual(self.autre.profile.theme, Themes.CLAIR)

    def test_anonyme_redirige_vers_connexion_sans_changement(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url)

    def test_get_refuse(self):
        self.client.login(username="marin_theme", password="pass")
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_redirection_externe_ignoree(self):
        self.client.login(username="marin_theme", password="pass")
        r = self.client.post(self.url, {"next": "https://exemple.invalide/piege"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)

    def test_variables_css_du_mode_sombre_definies(self):
        from django.contrib.staticfiles import finders
        with open(finders.find("css/matrix.css"), encoding="utf-8") as f:
            css = f.read()
        self.assertIn('[data-theme="sombre"]', css)
        for variable in ("--bg:", "--surface:", "--text:", "--border:"):
            self.assertIn(variable, css.split('[data-theme="sombre"] {')[1].split("}")[0])

    def test_valeur_html_du_theme_sombre_ciblee_par_le_css(self):
        """La valeur émise dans data-theme par base.html doit être un sélecteur de matrix.css."""
        from django.contrib.staticfiles import finders
        self.client.login(username="marin_theme", password="pass")
        self.client.post(self.url)
        html = self.client.get("/users/profil/").content.decode()
        self.assertIn(f'data-theme="{Themes.SOMBRE}"', html)
        with open(finders.find("css/matrix.css"), encoding="utf-8") as f:
            css = f.read()
        self.assertIn(f'[data-theme="{Themes.SOMBRE}"]', css)
