"""Tests de la couche Python qui prépare les nouvelles jauges visuelles ajoutées
au principe fondamental n°5 de CLAUDE.md (« Priorité au visuel ») : niveau de
stock (StockPieceListView) et sévérité des tickets correctifs (TicketListView).
Le rendu CSS de la barre lui-même n'est pas testé ici, seul le pourcentage
transmis au contexte."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, StockPiece
from org.models import Sector, Service, Ship


class JaugeStockTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire J", code="NJ-VIZ")
        self.service = Service.objects.create(ship=self.navire, name="Srv")
        self.secteur = Sector.objects.create(service=self.service, name="Sec")
        self.user = User.objects.create_user(username="u_stock", password="pass")
        UserProfile.objects.filter(user=self.user).update(role="CHEF_SECTION", sector=self.secteur)
        self.client.login(username="u_stock", password="pass")
        self.url = reverse("stock-piece-list")

    def _piece_par_reference(self, response, reference):
        return next(p for p in response.context["pieces"] if p.reference == reference)

    def test_jauge_pct_calculee_a_partir_du_seuil_minimal(self):
        StockPiece.objects.create(
            reference="R1", designation="D1", quantite=2, quantite_minimale=10,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        response = self.client.get(self.url)
        self.assertEqual(self._piece_par_reference(response, "R1").jauge_pct, 20)

    def test_jauge_pct_plafonnee_a_100(self):
        StockPiece.objects.create(
            reference="R2", designation="D2", quantite=50, quantite_minimale=10,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        response = self.client.get(self.url)
        self.assertEqual(self._piece_par_reference(response, "R2").jauge_pct, 100)

    def test_jauge_pct_pleine_sans_seuil_minimal_defini(self):
        # Sans seuil minimal renseigné (0), la pièce n'a pas d'exigence à
        # respecter : jauge pleine par convention plutôt qu'une division par 0.
        StockPiece.objects.create(
            reference="R3", designation="D3", quantite=0, quantite_minimale=0,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        response = self.client.get(self.url)
        self.assertEqual(self._piece_par_reference(response, "R3").jauge_pct, 100)


class JaugeSeveriteTicketTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire S", code="NS-VIZ")
        self.service = Service.objects.create(ship=self.navire, name="Srv")
        self.secteur = Sector.objects.create(service=self.service, name="Sec")
        self.asset_type = AssetType.objects.create(name="Type", category="Cat", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.user = User.objects.create_user(username="u_ticket", password="pass")
        UserProfile.objects.filter(user=self.user).update(role="CHEF_SECTION", sector=self.secteur)
        self.client.login(username="u_ticket", password="pass")
        self.url = reverse("ticket-list") + "?vue=perimetre"

    def _ticket_par_pk(self, response, pk):
        return next(t for t in response.context["tickets"] if t.pk == pk)

    def test_severite_pct_proportionnelle_sur_5(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Panne", severity=4)
        response = self.client.get(self.url)
        self.assertEqual(self._ticket_par_pk(response, ticket.pk).severite_pct, 80)

    def test_severite_pct_plafonnee_a_100_au_dela_de_5(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Panne", severity=9)
        response = self.client.get(self.url)
        self.assertEqual(self._ticket_par_pk(response, ticket.pk).severite_pct, 100)
