"""Tâches : action « Attribuer une tâche » en tête de page ; lien d'évitement du gabarit de base."""
from django.urls import reverse

from taches.tests.test_taches import TachesBase


class ErgonomieTachesTests(TachesBase):
    def test_bouton_attribuer_present_pour_qui_attribue(self):
        self.client.login(username="chef", password="pass")
        html = self.client.get(reverse("taches-index")).content.decode()
        self.assertIn('href="#attribuer-tache"', html)
        self.assertIn('id="attribuer-tache"', html)
        # Le bouton précède les blocs de la page.
        self.assertLess(html.index('href="#attribuer-tache"'), html.index('<h2 class="h5">Mes tâches'))

    def test_bouton_attribuer_absent_pour_un_equipier(self):
        self.client.login(username="marin", password="pass")
        html = self.client.get(reverse("taches-index")).content.decode()
        self.assertNotIn("attribuer-tache", html)

    def test_lien_d_evitement_avant_la_navigation_et_cible_main(self):
        self.client.login(username="chef", password="pass")
        html = self.client.get(reverse("taches-index")).content.decode()
        self.assertIn('href="#contenu-principal"', html)
        self.assertIn('<main id="contenu-principal"', html)
        self.assertLess(html.index('href="#contenu-principal"'), html.index("<nav"))
