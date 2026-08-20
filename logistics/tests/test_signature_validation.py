"""Tests de la signature de validation sur la transition RETURNED_TO_SERVICE.

Le passage d'un ticket correctif au statut "Remis en service" est un geste
engageant : il exige une ré-authentification légère (mot de passe courant de
l'appelant) avant d'être appliqué. Vérifie : refus si le mot de passe est
incorrect (aucune modification du ticket), acceptation si le mot de passe est
correct (valide_par/date_validation renseignés), et absence de régression sur
les autres transitions du cycle de vie (pas de mot de passe exigé).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, TicketStatusLog
from org.models import Sector, Service, Ship


class SignatureValidationRemiseEnServiceTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire test signature", code="NT-SIG")
        self.service = Service.objects.create(ship=self.navire, name="Service test signature")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur test signature")
        self.asset_type = AssetType.objects.create(name="Pompe signature", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.ticket = CorrectiveTicket.objects.create(
            asset=self.asset, description="Fuite hydraulique", status="TESTING"
        )

        self.chef = User.objects.create_user(username="chef_signature", password="MotDePasseCorrect1")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.url = reverse("ticket-transition", args=[self.ticket.id])
        self.client.login(username="chef_signature", password="MotDePasseCorrect1")

    def test_remise_en_service_refusee_avec_mauvais_mot_de_passe(self):
        response = self.client.post(
            self.url, {"status": "RETURNED_TO_SERVICE", "mot_de_passe": "faux-mot-de-passe"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")
        self.assertIsNone(self.ticket.valide_par)
        self.assertIsNone(self.ticket.date_validation)
        self.assertEqual(TicketStatusLog.objects.filter(ticket=self.ticket).count(), 0)

    def test_remise_en_service_refusee_sans_mot_de_passe(self):
        response = self.client.post(self.url, {"status": "RETURNED_TO_SERVICE"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")
        self.assertIsNone(self.ticket.valide_par)

    def test_remise_en_service_acceptee_avec_bon_mot_de_passe(self):
        response = self.client.post(
            self.url,
            {"status": "RETURNED_TO_SERVICE", "mot_de_passe": "MotDePasseCorrect1"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "RETURNED_TO_SERVICE")
        self.assertEqual(self.ticket.valide_par, self.chef)
        self.assertIsNotNone(self.ticket.date_validation)
        self.assertEqual(
            TicketStatusLog.objects.filter(ticket=self.ticket, new_status="RETURNED_TO_SERVICE").count(), 1
        )

    def test_autres_transitions_ne_necessitent_pas_de_mot_de_passe(self):
        response = self.client.post(self.url, {"status": "IN_REPAIR"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "IN_REPAIR")
        self.assertIsNone(self.ticket.valide_par)
