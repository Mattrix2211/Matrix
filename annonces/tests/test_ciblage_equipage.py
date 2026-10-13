"""Ciblage par équipage : marin sans équipage, équipages A/B, isolation entre bâtiments.

Doit aussi passer sur PostgreSQL (qui refuse les valeurs NUL dans les filtres).
"""
from django.urls import reverse

from annonces import services
from annonces.models import Annonce
from annonces.tests.test_annonces import AnnoncesBase
from org.models import Ship


class CiblageEquipageTests(AnnoncesBase):
    def setUp(self):
        super().setUp()
        self.marin_a = self._marin("marin_a", self.energie, None, "EQUIPIER")
        self.marin_b = self._marin("marin_b", self.energie, None, "EQUIPIER")
        for user, equipage in ((self.marin_a, "A"), (self.marin_b, "B")):
            user.profile.equipage = equipage
            user.profile.save()
        self.pour_tous = self._annonce("Pour tous")
        self.pour_a = self._annonce("Équipage A", "A")
        self.pour_b = self._annonce("Équipage B", "B")

    def _annonce(self, titre, equipage=""):
        return Annonce.objects.create(
            titre=titre, corps="x", ship=self.navire, equipage=equipage, auteur=self.cdt)

    def _visibles(self, user):
        return set(services.annonces_visibles(user).exclude(auteur=user))

    def test_marin_sans_equipage_ne_voit_que_les_annonces_sans_ciblage(self):
        self.assertEqual(self._visibles(self.marin), {self.pour_tous})

    def test_equipages_a_et_b_sont_cloisonnes(self):
        self.assertEqual(self._visibles(self.marin_a), {self.pour_tous, self.pour_a})
        self.assertEqual(self._visibles(self.marin_b), {self.pour_tous, self.pour_b})

    def test_isolation_entre_batiments(self):
        normandie = Ship.objects.create(name="Normandie", code="NOR")
        marin_nor = self._marin("marin_nor", None, None, "EQUIPIER", navire=normandie)
        self.assertEqual(self._visibles(marin_nor), set())
        autre = Annonce.objects.create(titre="Normandie", corps="x", ship=normandie, auteur=marin_nor)
        self.assertEqual(set(services.annonces_visibles(self.marin_a).filter(pk=autre.pk)), set())

    def test_pages_repondent_200_pour_marin_sans_equipage(self):
        self.client.force_login(self.marin)
        for adresse in (reverse("home"), reverse("annonces-index"), reverse("recherche-rapide") + "?q=annonce"):
            with self.subTest(adresse=adresse):
                self.assertEqual(self.client.get(adresse).status_code, 200)
        self.assertContains(self.client.get(reverse("annonces-index")), "Pour tous")
        self.assertNotContains(self.client.get(reverse("annonces-index")), "Équipage A")
