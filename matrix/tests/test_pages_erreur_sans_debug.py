"""Pages d'erreur dans une configuration proche de la production (DEBUG désactivé, hôtes explicites)."""
import re
import uuid

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


def _normalise(html):
    """Retire les éléments variables d'une requête à l'autre (jeton CSRF, adresse demandée)."""
    html = re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', "", html)
    return re.sub(r"\s+", " ", html)


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False)
class PageIntrouvableSansDebugTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne erreurs", code="BE")
        service = Service.objects.create(ship=self.navire, name="Propulsion")
        self.secteur = Sector.objects.create(service=service, name="Moteurs")
        autre_secteur = Sector.objects.create(service=service, name="Auxiliaires")
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=autre_secteur)
        asset = Asset.objects.create(asset_type=type_asset, ship=self.navire, service=service, sector=autre_secteur, internal_id="P-1")
        self.ticket_hors_secteur = CorrectiveTicket.objects.create(asset=asset, description="Panne auxiliaires")
        user = User.objects.create_user(username="chef_secteur_erreurs", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={
            "role": "CHEF_SECTEUR", "ship": self.navire, "service": service, "sector": self.secteur})
        self.client.force_login(user)
        self.client.raise_request_exception = False

    def _page(self, ticket_pk):
        return self.client.get(reverse("ticket-detail", args=[ticket_pk]))

    def test_page_matrix_coherente_et_utile(self):
        page = self._page(uuid.uuid4())
        self.assertEqual(page.status_code, 404)
        self.assertContains(page, "Page introuvable", status_code=404)
        self.assertContains(page, "accessible avec votre compte", status_code=404)
        self.assertContains(page, "Retour à Aujourd", status_code=404)  # action de retour utile
        self.assertContains(page, "mx-barre", status_code=404)  # gabarit de Matrix, pas une page brute

    def test_aucune_fuite_technique(self):
        contenu = self._page(uuid.uuid4()).content.decode()
        for indice in ("Traceback", "Request Method", "URLconf", "DEBUG = True", "Ticket introuvable"):
            self.assertNotIn(indice, contenu, indice)

    def test_objet_hors_perimetre_et_objet_absent_sont_indiscernables(self):
        absent = self._page(uuid.uuid4())
        hors_perimetre = self._page(self.ticket_hors_secteur.pk)
        self.assertEqual((absent.status_code, hors_perimetre.status_code), (404, 404))
        self.assertEqual(_normalise(absent.content.decode()), _normalise(hors_perimetre.content.decode()))
        self.assertNotIn("Panne auxiliaires", hors_perimetre.content.decode())

    def test_une_occurrence_inexistante_donne_la_meme_page(self):
        reponse = self.client.get(reverse("occurrence-execute", args=[999999]))
        self.assertContains(reponse, "Page introuvable", status_code=404)
