"""Tests de la confirmation explicite sur la transition RETURNED_TO_SERVICE.

Le passage d'un ticket correctif au statut "Remis en service" exige une
confirmation avant d'être appliqué. Vérifie : refus sans confirmation (aucune
modification du ticket), acceptation avec confirmation (valide_par/date_validation
posés par le serveur, audit avec texte et version), droit contrôlé avant la
confirmation, et absence de régression sur les autres transitions.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, TicketStatusLog
from matrix.core.confirmations import texte_confirmation
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

    def test_page_affiche_identite_et_texte_non_precoche(self):
        r = self.client.get(reverse("ticket-detail", args=[self.ticket.id]))
        self.assertContains(r, "Vous validez en tant que")
        self.assertContains(r, texte_confirmation("remise_en_service")[1])
        self.assertNotRegex(r.content.decode(), r'name="confirmation"[^>]*checked')
        self.assertNotContains(r, 'name="mot_de_passe"')

    def test_remise_en_service_refusee_sans_confirmation(self):
        for charge in ({}, {"confirmation": "0"}, {"mot_de_passe": "MotDePasseCorrect1"}):
            with self.subTest(charge=charge):
                response = self.client.post(self.url, {"status": "RETURNED_TO_SERVICE", **charge}, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Confirmation requise")
                self.ticket.refresh_from_db()
                self.assertEqual(self.ticket.status, "TESTING")
                self.assertIsNone(self.ticket.valide_par)
                self.assertIsNone(self.ticket.date_validation)
                self.assertEqual(TicketStatusLog.objects.filter(ticket=self.ticket).count(), 0)
        self.assertFalse(AuditLog.objects.filter(action="ticket_validation_critique").exists())
        self.assertTrue(AuditLog.objects.filter(action="validation_critique_refusee").exists())

    def test_remise_en_service_refusee_sans_droit_avant_la_confirmation(self):
        marin = User.objects.create_user(username="marin_signature", password="MotDePasseCorrect1")
        UserProfile.objects.filter(user=marin).update(role="EQUIPIER", sector=self.secteur)
        self.client.login(username="marin_signature", password="MotDePasseCorrect1")
        r = self.client.post(self.url, {"status": "RETURNED_TO_SERVICE", "confirmation": "1"})
        self.assertEqual(r.status_code, 403)
        r = self.client.post(self.url, {"status": "RETURNED_TO_SERVICE"})
        self.assertEqual(r.status_code, 403)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")
        self.assertFalse(AuditLog.objects.filter(action="validation_critique_refusee").exists())

    def test_remise_en_service_acceptee_avec_confirmation(self):
        response = self.client.post(
            self.url, {"status": "RETURNED_TO_SERVICE", "confirmation": "1", "valide_par": "999"}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "RETURNED_TO_SERVICE")
        self.assertEqual(self.ticket.valide_par, self.chef)
        self.assertIsNotNone(self.ticket.date_validation)
        self.assertEqual(
            TicketStatusLog.objects.filter(ticket=self.ticket, new_status="RETURNED_TO_SERVICE").count(), 1
        )
        version, texte = texte_confirmation("remise_en_service")
        entree = AuditLog.objects.get(action="ticket_validation_critique")
        self.assertIn("canal=web", entree.details)
        self.assertIn(f"confirmation_version={version}", entree.details)
        self.assertIn(texte, entree.details)

    def test_autres_transitions_ne_necessitent_pas_de_confirmation(self):
        response = self.client.post(self.url, {"status": "IN_REPAIR"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "IN_REPAIR")
        self.assertIsNone(self.ticket.valide_par)


class SignatureValidationAPIRemiseEnServiceTests(TestCase):
    """Mêmes règles que SignatureValidationRemiseEnServiceTests ci-dessus, mais
    via l'action DRF CorrectiveTicketViewSet.transition : l'API ne doit pas
    offrir un moyen de contourner la confirmation exigée par l'interface web."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire test signature API", code="NT-SIG-API")
        self.service = Service.objects.create(ship=self.navire, name="Service test signature API")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur test signature API")
        self.asset_type = AssetType.objects.create(name="Pompe signature API", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.ticket = CorrectiveTicket.objects.create(
            asset=self.asset, description="Fuite hydraulique", status="TESTING"
        )

        self.chef = User.objects.create_user(username="chef_signature_api", password="MotDePasseCorrect1")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.client = APIClient()
        self.client.login(username="chef_signature_api", password="MotDePasseCorrect1")
        self.url = f"/api/logistics/tickets/{self.ticket.id}/transition/"

    def test_remise_en_service_refusee_sans_confirmation_ou_non_booleenne(self):
        for charge in ({}, {"confirmation": False}, {"confirmation": "true"}, {"mot_de_passe": "MotDePasseCorrect1"}):
            with self.subTest(charge=charge):
                r = self.client.post(self.url, {"status": "RETURNED_TO_SERVICE", **charge}, format="json")
                self.assertEqual(r.status_code, 400)
                self.assertIn("Confirmation requise", r.json()["detail"])
                self.ticket.refresh_from_db()
                self.assertEqual(self.ticket.status, "TESTING")
                self.assertIsNone(self.ticket.valide_par)
                self.assertIsNone(self.ticket.date_validation)
                self.assertEqual(TicketStatusLog.objects.filter(ticket=self.ticket).count(), 0)
        self.assertFalse(AuditLog.objects.filter(action="ticket_validation_critique").exists())

    def test_remise_en_service_refusee_sans_droit_avant_la_confirmation(self):
        marin = User.objects.create_user(username="marin_signature_api", password="MotDePasseCorrect1")
        UserProfile.objects.filter(user=marin).update(role="EQUIPIER", sector=self.secteur)
        client = APIClient()
        client.login(username="marin_signature_api", password="MotDePasseCorrect1")
        for charge in ({"confirmation": True}, {}):
            r = client.post(self.url, {"status": "RETURNED_TO_SERVICE", **charge}, format="json")
            self.assertEqual(r.status_code, 403)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")

    def test_remise_en_service_acceptee_avec_confirmation(self):
        r = self.client.post(
            self.url, {"status": "RETURNED_TO_SERVICE", "confirmation": True, "valide_par": 999}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "RETURNED_TO_SERVICE")
        self.assertEqual(self.ticket.valide_par, self.chef)
        self.assertIsNotNone(self.ticket.date_validation)
        self.assertEqual(
            TicketStatusLog.objects.filter(ticket=self.ticket, new_status="RETURNED_TO_SERVICE").count(), 1
        )
        version, texte = texte_confirmation("remise_en_service")
        entree = AuditLog.objects.get(action="ticket_validation_critique")
        self.assertIn("canal=api", entree.details)
        self.assertIn(f"confirmation_version={version}", entree.details)
        self.assertIn(texte, entree.details)

    def test_patch_generique_ne_permet_pas_de_contourner_la_confirmation(self):
        """Régression (contre-vérification sécurité) : le statut ne doit pas
        pouvoir être modifié via le endpoint générique du ViewSet, qui ne passe
        pas par transition() et donc pas par la confirmation."""
        detail_url = f"/api/logistics/tickets/{self.ticket.id}/"
        r = self.client.patch(detail_url, {"status": "RETURNED_TO_SERVICE"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")
        self.assertIsNone(self.ticket.valide_par)
        self.assertIsNone(self.ticket.date_validation)
