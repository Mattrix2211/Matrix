"""Tests de l'extension du journal d'audit transverse (AuditLog) aux actions
sensibles de la logistique corrective : création d'un ticket, transition de
statut, remise en service (validation critique) — cf. tâche Notion « Unifier
les modèles d'historique/audit (AuditLog générique vs logs ad hoc par app) ».

TicketStatusLog reste le modèle dédié (historique structuré propre au
ticket) ; AuditLog est alimenté EN PLUS, à chaque même point de passage, pour
la vue transverse (onglet Réglages > Journal)."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


class AuditLogTicketTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire audit ticket", code="NT-AUD")
        self.service = Service.objects.create(ship=self.navire, name="Service audit")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur audit")
        self.asset_type = AssetType.objects.create(name="Pompe audit", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.chef = User.objects.create_user(username="chef_audit_ticket", password="MotDePasseCorrect1")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)
        self.client.login(username="chef_audit_ticket", password="MotDePasseCorrect1")

    def test_creation_ticket_genere_une_entree_daudit_exploitable(self):
        self.client.post(
            f"/logistics/tickets/creer/{self.asset.id}/",
            {"description": "Fuite constatée", "severity": "3"},
        )
        ticket = CorrectiveTicket.objects.get(asset=self.asset)
        entree = AuditLog.objects.get(action="create_ticket")
        # Acteur : identifie précisément qui a déclenché l'action.
        self.assertEqual(entree.actor, self.chef)
        # Horodatage : hérité de TimeStampedModel, renseigné automatiquement.
        self.assertIsNotNone(entree.created_at)
        # Contexte : permet de retrouver l'objet concerné sans ambiguïté.
        self.assertIn(str(ticket.pk), entree.details)
        self.assertIn(str(self.asset), entree.details)

    def test_transition_de_statut_genere_une_entree_daudit(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite", status="REPORTED")
        url = reverse("ticket-transition", args=[ticket.id])
        self.client.post(url, {"status": "DIAGNOSED"}, follow=True)
        entree = AuditLog.objects.get(action="ticket_status_change")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn("REPORTED -> DIAGNOSED", entree.details)

    def test_remise_en_service_genere_une_entree_daudit_distincte_de_validation(self):
        # La remise en service (transition engageante, mot de passe requis)
        # doit être identifiable dans le journal comme une VALIDATION,
        # distincte d'un simple changement de statut — même logique que la
        # signature de validation déjà appliquée au ticket lui-même.
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite", status="TESTING")
        url = reverse("ticket-transition", args=[ticket.id])
        self.client.post(
            url, {"status": "RETURNED_TO_SERVICE", "mot_de_passe": "MotDePasseCorrect1"}, follow=True,
        )
        entree = AuditLog.objects.get(action="ticket_validation_critique")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn(str(ticket.pk), entree.details)

    def test_mot_de_passe_incorrect_ne_genere_aucune_entree_daudit(self):
        # Sans écriture effective en base, aucune entrée d'audit ne doit être
        # créée : une entrée d'audit doit toujours correspondre à une action
        # réellement appliquée.
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite", status="TESTING")
        url = reverse("ticket-transition", args=[ticket.id])
        self.client.post(
            url, {"status": "RETURNED_TO_SERVICE", "mot_de_passe": "faux"}, follow=True,
        )
        self.assertFalse(AuditLog.objects.filter(action__startswith="ticket_").exists())
