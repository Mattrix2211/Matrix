"""Une liste sans fonction renseignée (champ nullable) n'affiche jamais « None »."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Sector, Service, Ship
from quarts.models import ChefDeListe, Quart, ServiceGarde


class ListesSansFonctionTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Navire sans fonction", code="NSF")
        self.secteur = Sector.objects.create(service=Service.objects.create(ship=navire, name="Pont"), name="Manœuvre")
        self.cdl = User.objects.create_user(username="cdl_sans_fonction", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.secteur)
        debut = timezone.localdate()
        commun = dict(sector=self.secteur, nom="Sans fonction", date_debut=debut, date_fin=debut + timedelta(days=6), fonction=None)
        self.quart = Quart.objects.create(**commun)
        self.garde = ServiceGarde.objects.create(**{**commun, "nom": "Garde sans fonction"})
        self.client.login(username="cdl_sans_fonction", password="pass")

    def _html(self, url):
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        return reponse.content.decode()

    def test_page_des_listes(self):
        html = self._html("/quarts/")
        self.assertIn("Sans fonction", html)
        self.assertNotIn("None", html)

    def test_fiche_d_un_quart_et_d_une_garde(self):
        for url in (f"/quarts/quart/{self.quart.pk}/", f"/quarts/garde/{self.garde.pk}/"):
            self.assertNotIn("None", self._html(url))
