"""Test de non-régression pour le lien de navigation « Formations ».

Bug corrigé précédemment (même classe de bug que le lien « Maintenance ») :
le lien de nav pointait vers /api/training/ (racine brute du routeur DRF,
JSON) au lieu de la page web dédiée /formations/. On vérifie ici à la fois
que le lien dans la barre de navigation pointe vers la bonne route, et que
suivre ce lien renvoie bien la page web HTML (et non la réponse JSON de
l'API).
"""
from django.contrib.auth.models import User
from django.test import TestCase


class NavigationFormationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")

    def test_lien_nav_formations_pointe_vers_la_page_web(self):
        response = self.client.get("/")
        self.assertContains(response, 'href="/formations/"')
        self.assertNotContains(response, 'href="/api/training/"')

    def test_page_formations_renvoie_du_html_et_non_du_json_api(self):
        response = self.client.get("/formations/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/html"))
        # Racine brute DRF : un titre de page absent du template web dédié.
        self.assertNotContains(response, "Django REST framework")
        self.assertContains(response, "Formations")
