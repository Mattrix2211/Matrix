from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase

from matrix.core.retour import destination_retour


class DestinationRetourTests(SimpleTestCase):
    def _requete(self, **params):
        return RequestFactory().get("/page/", params)

    def test_sans_parametre_le_parent_logique_est_utilise(self):
        self.assertEqual(destination_retour(self._requete(), "/parent/"), "/parent/")

    def test_chemin_local_accepte(self):
        self.assertEqual(destination_retour(self._requete(retour="/maintenance/?x=1"), "/parent/"), "/maintenance/?x=1")

    def test_adresses_externes_ou_exotiques_ignorees(self):
        for dangereux in ("https://exemple.test/", "//exemple.test/", "javascript:alert(1)", "http:/\\exemple.test", "maintenance/"):
            self.assertEqual(destination_retour(self._requete(retour=dangereux), "/parent/"), "/parent/", dangereux)


class BaliseRetourTests(SimpleTestCase):
    def _rendu(self, **params):
        requete = RequestFactory().get("/page/", params)
        gabarit = Template('{% load composants %}{% retour "/parent/" "Rondes" %}')
        return gabarit.render(Context({"request": requete}))

    def test_lien_vers_le_parent_avec_libelle_et_navigation_nommee(self):
        html = self._rendu()
        self.assertIn('href="/parent/"', html)
        self.assertIn("Rondes", html)
        self.assertIn('aria-label="Retour"', html)

    def test_l_origine_demandee_prime_sur_le_parent(self):
        html = self._rendu(retour="/difficultes/?page=2")
        self.assertIn('href="/difficultes/?page=2"', html)
        self.assertNotIn("Rondes", html)
