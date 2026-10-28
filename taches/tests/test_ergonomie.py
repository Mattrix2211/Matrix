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


class FicheTacheOrdreTests(TachesBase):
    def _html(self, user, tache):
        self.client.login(username=user, password="pass")
        return self.client.get(reverse("tache-detail", args=[tache.pk])).content.decode()

    def test_action_et_fil_avant_checklist_et_pieces(self):
        html = self._html("marin", self._tache())
        self.assertLess(html.index("Terminer et rendre compte"), html.index("Fil de la tâche"))
        self.assertLess(html.index("Répondre dans le fil"), html.index('id="titre-checklist"'))
        self.assertLess(html.index('id="titre-checklist"'), html.index("Pièces jointes"))

    def test_blocs_vides_replies_et_remplis_ouverts(self):
        tache = self._tache()
        self.assertNotIn("<details class=\"card card-body mb-3\" open>", self._html("marin", tache))
        tache.elements_checklist.create(texte="Vérifier la vanne")
        self.assertIn("<details class=\"card card-body mb-3\" open>", self._html("marin", tache))

    def test_lecteur_sans_droit_ne_voit_aucun_bloc_vide(self):
        html = self._html("terre", self._tache())
        self.assertNotIn("titre-checklist", html)
        self.assertNotIn("Pièces jointes", html)

    def test_bloc_probleme_avec_aide_sur_les_destinataires(self):
        html = self._html("marin", self._tache())
        self.assertIn("Un problème sur cette tâche ?", html)
        self.assertIn("Je suis bloqué", html)
        self.assertIn("participants du fil sont prévenus", html)
        self.assertIn("lui seul est prévenu au départ", html)
        self.assertNotIn("btn-outline-warning", html)
