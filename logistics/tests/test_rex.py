"""Tests du retour d'expérience (REX) sur les tickets correctifs.

Vérifie : le passage au statut CLOSED est refusé tant que le diagnostic final
et la solution appliquée ne sont pas renseignés (validation côté vue, pas
seulement au niveau modèle), et qu'il est accepté une fois ces deux champs
remplis. Les autres transitions du cycle de vie ne sont pas concernées par
cette contrainte.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, TicketStatusLog
from org.models import Sector, Service, Ship


class FermetureTicketRexTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire test REX", code="NT-RX")
        self.service = Service.objects.create(ship=self.navire, name="Service test REX")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur test REX")
        self.asset_type = AssetType.objects.create(name="Pompe REX", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite hydraulique")

        self.chef = User.objects.create_user(username="chef_rex", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.url = reverse("ticket-transition", args=[self.ticket.id])
        self.client.login(username="chef_rex", password="pass")

    def test_fermeture_refusee_sans_diagnostic_ni_solution(self):
        response = self.client.post(self.url, {"status": "CLOSED"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertNotEqual(self.ticket.status, "CLOSED")
        self.assertEqual(TicketStatusLog.objects.filter(ticket=self.ticket).count(), 0)

    def test_fermeture_refusee_avec_seulement_le_diagnostic(self):
        response = self.client.post(
            self.url, {"status": "CLOSED", "diagnostic_final": "Joint usé"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertNotEqual(self.ticket.status, "CLOSED")

    def test_fermeture_acceptee_avec_diagnostic_et_solution(self):
        response = self.client.post(
            self.url,
            {"status": "CLOSED", "diagnostic_final": "Joint usé", "solution": "Joint remplacé"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "CLOSED")
        self.assertEqual(self.ticket.diagnostic_final, "Joint usé")
        self.assertEqual(self.ticket.solution, "Joint remplacé")
        self.assertEqual(TicketStatusLog.objects.filter(ticket=self.ticket, new_status="CLOSED").count(), 1)

    def test_diagnostic_et_solution_sauvegardes_meme_si_fermeture_refusee(self):
        # Saisie progressive : le marin peut renseigner le diagnostic avant que la
        # solution ne soit trouvée, sans que ça déclenche la fermeture.
        self.client.post(
            self.url, {"status": "CLOSED", "diagnostic_final": "Joint usé"}, follow=True
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.diagnostic_final, "Joint usé")

    def test_autres_transitions_ne_necessitent_pas_de_rex(self):
        response = self.client.post(self.url, {"status": "DIAGNOSED"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "DIAGNOSED")

    def test_equipier_ne_peut_pas_fermer_le_ticket(self):
        equipier = User.objects.create_user(username="equipier_rex", password="pass")
        UserProfile.objects.filter(user=equipier).update(role="EQUIPIER", sector=self.secteur)
        self.client.logout()
        self.client.login(username="equipier_rex", password="pass")
        response = self.client.post(
            self.url,
            {"status": "CLOSED", "diagnostic_final": "Joint usé", "solution": "Joint remplacé"},
        )
        self.assertEqual(response.status_code, 403)
