"""Fuite de périmètre (IDOR) sur TicketTransitionView, TicketAssignView,
PartRequestCreateView, PartLineItemCreateView et PartLineItemUpdateStatusView
(interface web).

Avant correction, ces vues récupéraient le ticket/la demande/la ligne par un
simple .get(pk=...), sans filtrer par périmètre hiérarchique : un chef de
secteur connaissant l'identifiant d'un objet d'un autre navire pouvait le
faire transitionner (y compris le remettre en service), modifier ses
assignés, lui créer une demande de pièces, ajouter une ligne à une demande
existante ou en changer le statut — alors même qu'aucun lien n'y menait
depuis les vues déjà scopées (liste, fiche détail). Cf. tâche [SEC] IDOR
cross-navire sur la chaîne « demandes de pièces ».
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, PartRequest, PartLineItem
from org.models import Sector, Service, Ship


class ScopeLeakTicketTransitionAssignViewsTests(TestCase):
    def setUp(self):
        # Navire A (celui de l'utilisateur connecté)
        self.ship_a = Ship.objects.create(name="Navire A web ticket", code="NA-WTIK")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A web ticket")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A web ticket")
        self.asset_type_a = AssetType.objects.create(name="TypeA web ticket", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )

        # Navire B (hors périmètre de l'utilisateur connecté)
        self.ship_b = Ship.objects.create(name="Navire B web ticket", code="NB-WTIK")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B web ticket")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B web ticket")
        self.asset_type_b = AssetType.objects.create(name="TypeB web ticket", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        self.ticket_b = CorrectiveTicket.objects.create(asset=self.asset_b, description="Panne B", status="TESTING")

        self.chef_a = User.objects.create_user(username="chef_ticket_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SECTION", "sector": self.sector_a}
        )
        self.client.login(username="chef_ticket_a", password="pass")

    def test_transition_dun_ticket_dun_autre_navire_refusee(self):
        url = reverse("ticket-transition", args=[self.ticket_b.id])
        r = self.client.post(url, {"status": "DIAGNOSED"})
        self.assertEqual(r.status_code, 400)
        self.ticket_b.refresh_from_db()
        self.assertEqual(self.ticket_b.status, "TESTING")

    def test_assignation_dun_ticket_dun_autre_navire_refusee(self):
        url = reverse("ticket-assign", args=[self.ticket_b.id])
        r = self.client.post(url, {"assignees": [str(self.chef_a.id)]})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.ticket_b.assignees.exists())

    def test_creation_demande_de_pieces_dun_ticket_dun_autre_navire_refusee(self):
        url = reverse("part-request-create", args=[self.ticket_b.id])
        r = self.client.post(url, {})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(PartRequest.objects.filter(ticket=self.ticket_b).exists())

    def test_ajout_ligne_sur_demande_dun_ticket_dun_autre_navire_refuse(self):
        demande_b = PartRequest.objects.create(ticket=self.ticket_b)
        url = reverse("part-line-create", args=[demande_b.id])
        r = self.client.post(url, {"reference": "REF-B", "description": "Joint", "qty": "2"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(PartLineItem.objects.filter(part_request=demande_b).exists())

    def test_changement_statut_ligne_dun_ticket_dun_autre_navire_refuse(self):
        demande_b = PartRequest.objects.create(ticket=self.ticket_b)
        ligne_b = PartLineItem.objects.create(part_request=demande_b, reference="REF-B", description="Joint", qty=1)
        url = reverse("part-line-status", args=[ligne_b.id])
        r = self.client.post(url, {"status": "RECEIVED"})
        self.assertEqual(r.status_code, 400)
        ligne_b.refresh_from_db()
        self.assertNotEqual(ligne_b.status, "RECEIVED")
