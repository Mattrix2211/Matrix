"""Étanchéité par équipage de la page « Prêt à appareiller » : les libellés issus
d'occurrences de maintenance ne sont lisibles que par l'équipage à bord et le
commandement ; les autres items restent visibles de tous."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from dashboard.models import ItemAppareillage, SessionAppareillage
from org.models import Ship

LIBELLE_OCCURRENCE = "Essai du groupe tribord — échéance dépassée"
LIBELLE_STOCK = "FILT-01 — Filtre à huile (0/2)"


def _marin(nom, role, ship, equipage=""):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class EtancheiteItemsOccurrencesTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM", code="FR", double_equipage=True, equipage_a_bord="A")
        self.session = SessionAppareillage.objects.create(ship=self.navire)
        self.occurrence = ItemAppareillage.objects.create(
            session=self.session, categorie=ItemAppareillage.CATEGORIE_OCCURRENCE, libelle=LIBELLE_OCCURRENCE
        )
        ItemAppareillage.objects.create(
            session=self.session, categorie=ItemAppareillage.CATEGORIE_STOCK, libelle=LIBELLE_STOCK
        )
        self.a_bord = _marin("a_bord", "EQUIPIER", self.navire, "A")
        self.a_terre = _marin("a_terre", "EQUIPIER", self.navire, "B")
        self.cdt_en_second_terre = _marin("second_terre", "COMMANDANT_EN_SECOND", self.navire, "B")
        self.url_page = reverse("pret-appareillage")
        self.url_detail = reverse("session-appareillage-detail", args=[self.session.pk])

    def _pages(self, user):
        self.client.force_login(user)
        return [self.client.get(self.url_page), self.client.get(self.url_detail)]

    def test_equipage_a_terre_ne_voit_pas_les_occurrences(self):
        for reponse in self._pages(self.a_terre):
            self.assertNotContains(reponse, LIBELLE_OCCURRENCE)
            self.assertContains(reponse, LIBELLE_STOCK)

    def test_equipage_a_terre_ne_peut_pas_cocher_une_occurrence(self):
        self.client.force_login(self.a_terre)
        reponse = self.client.post(reverse("item-appareillage-cocher", args=[self.occurrence.pk]))
        self.assertEqual(reponse.status_code, 403)
        self.occurrence.refresh_from_db()
        self.assertIsNone(self.occurrence.verifie_par)

    def test_equipage_a_bord_voit_les_occurrences(self):
        for reponse in self._pages(self.a_bord):
            self.assertContains(reponse, LIBELLE_OCCURRENCE)

    def test_commandement_a_terre_voit_les_occurrences(self):
        for reponse in self._pages(self.cdt_en_second_terre):
            self.assertContains(reponse, LIBELLE_OCCURRENCE)

    def test_navire_sans_double_equipage_inchange(self):
        self.navire.double_equipage = False
        self.navire.save()
        for reponse in self._pages(self.a_terre):
            self.assertContains(reponse, LIBELLE_OCCURRENCE)

    def test_equipage_unique_sans_equipage_renseigne_inchange(self):
        sans_equipage = _marin("sans_equipage", "EQUIPIER", self.navire)
        for reponse in self._pages(sans_equipage):
            self.assertContains(reponse, LIBELLE_OCCURRENCE)
