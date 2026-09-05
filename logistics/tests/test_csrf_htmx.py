"""Régression CSRF sur les formulaires htmx de logistics (T-CSRF, bug QA du
05/09/2026) : `_status.html` et `_part_requests.html` envoient des `hx-post`
sans `{% csrf_token %}`, et aucune config htmx globale n'injectait le header
CSRF avant correction — résultat : 403 Forbidden systématique en usage
navigateur réel sur toute transition de ticket (fermeture avec REX, remise en
service) et toute demande/prélèvement de pièces.

Le `Client` Django par défaut CONTOURNE la vérification CSRF, ce qui masquait
le bug côté tests : `Client(enforce_csrf_checks=True)` reproduit le
comportement d'un navigateur réel et permet de le détecter. Le correctif
(matrix/static/js/matrix.js, listener global `htmx:configRequest`) injecte
désormais le header `X-CSRFToken` sur toute requête htmx non-GET, ce que ces
tests simulent en passant explicitement le header."""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, PartRequest
from org.models import Sector, Service, Ship


class CsrfHtmxTicketFormsTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.ship = Ship.objects.create(name="Navire CSRF", code="CSRF")
        self.service = Service.objects.create(ship=self.ship, name="Service CSRF")
        self.sector = Sector.objects.create(service=self.service, name="Secteur CSRF")
        self.asset_type = AssetType.objects.create(name="Type CSRF", category="Cat", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Panne CSRF")
        self.chef = User.objects.create_user(username="chef_csrf", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "sector": self.sector}
        )
        self.client.login(username="chef_csrf", password="pass")
        # Charge une page qui rend {% csrf_token %} pour obtenir le cookie
        # csrftoken, exactement comme un navigateur avant toute requête htmx.
        self.client.get(reverse('ticket-detail', args=[self.ticket.id]))
        self.csrftoken = self.client.cookies['csrftoken'].value

    def test_transition_sans_header_csrf_refusee(self):
        """Sans le header X-CSRFToken (bug constaté en QA), Django refuse la
        requête : c'est ce comportement, invisible avec le Client par défaut,
        qui rendait les tickets correctifs inutilisables en navigateur réel."""
        url = reverse('ticket-transition', args=[self.ticket.id])
        r = self.client.post(url, {"status": "DIAGNOSED"})
        self.assertEqual(r.status_code, 403)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "REPORTED")

    def test_transition_avec_header_csrf_injecte_acceptee(self):
        """Avec le header X-CSRFToken (ce que le listener global htmx:configRequest
        injecte désormais automatiquement), la transition aboutit normalement."""
        url = reverse('ticket-transition', args=[self.ticket.id])
        r = self.client.post(url, {"status": "DIAGNOSED"}, HTTP_X_CSRFTOKEN=self.csrftoken)
        self.assertEqual(r.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "DIAGNOSED")

    def test_creation_demande_de_pieces_sans_header_csrf_refusee(self):
        url = reverse('part-request-create', args=[self.ticket.id])
        r = self.client.post(url, {})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(PartRequest.objects.filter(ticket=self.ticket).exists())

    def test_creation_demande_de_pieces_avec_header_csrf_injecte_acceptee(self):
        url = reverse('part-request-create', args=[self.ticket.id])
        r = self.client.post(url, {}, HTTP_X_CSRFTOKEN=self.csrftoken)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PartRequest.objects.filter(ticket=self.ticket).exists())

    def test_ajout_ligne_piece_avec_header_csrf_injecte_acceptee(self):
        demande = PartRequest.objects.create(ticket=self.ticket)
        url = reverse('part-line-create', args=[demande.id])
        r = self.client.post(
            url, {"reference": "REF-1", "description": "Joint", "qty": "2"},
            HTTP_X_CSRFTOKEN=self.csrftoken,
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(demande.lines.filter(reference="REF-1").exists())
