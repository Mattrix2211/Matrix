"""« À faire » : priorité 5 en tête, et non assignés du périmètre pour les chefs seulement."""
from django.test import TestCase

from dashboard.aujourdhui import a_faire
from dashboard.tests.test_supervision import SupervisionTests
from logistics.models import CorrectiveTicket


class AFaireChefTests(TestCase):
    # Réutilise les fabriques de SupervisionTests sans en rejouer les tests.
    setUp = SupervisionTests.setUp
    _marin = SupervisionTests._marin
    _asset = SupervisionTests._asset
    _occurrence = SupervisionTests._occurrence

    def _objets(self, user):
        return [e["objet"] for e in a_faire(user, self.aujourdhui)]

    def test_chef_voit_les_non_assignes_de_son_perimetre(self):
        dans = self._occurrence(self.asset_a, 2)
        self._occurrence(self.asset_b, 2)
        ticket = CorrectiveTicket.objects.create(asset=self.asset_a, description="Fuite")
        CorrectiveTicket.objects.create(asset=self.asset_b, description="Hors périmètre")
        self.assertCountEqual(self._objets(self.chef_a), [dans, ticket])
        details = [e["detail"] for e in a_faire(self.chef_a, self.aujourdhui)]
        self.assertTrue(all("Non assigné" in d for d in details))

    def test_equipier_ne_voit_que_les_siens(self):
        self._occurrence(self.asset_a, 2)
        CorrectiveTicket.objects.create(asset=self.asset_a, description="Fuite")
        self.assertEqual(self._objets(self.equipier), [])

    def test_occurrence_assignee_a_un_autre_nest_pas_non_assignee(self):
        occ = self._occurrence(self.asset_a, 2)
        occ.assignees.add(self.equipier)
        self.assertEqual(self._objets(self.chef_a), [])
        self.assertEqual(self._objets(self.equipier), [occ])

    def test_chef_sans_perimetre_ne_voit_rien(self):
        self._occurrence(self.asset_a, 2)
        self.assertEqual(self._objets(self._marin("sans", "CHEF_SECTEUR")), [])

    def test_priorite_5_passe_avant_priorite_1(self):
        faible = self._occurrence(self.asset_a, 2)
        critique = self._occurrence(self.asset_a, 5)
        faible.priority, critique.priority = 1, 5
        faible.save()
        critique.save()
        self.assertEqual(self._objets(self.chef_a), [critique, faible])
