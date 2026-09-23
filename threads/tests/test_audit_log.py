"""Tests de l'extension du journal d'audit transverse (AuditLog) à la
suppression d'un message ou d'un fil de discussion complet — action sensible
(un message peut porter une décision ou une consigne, un fil supprimé
entraîne la disparition en cascade de tous ses messages), jusqu'ici
totalement invisible (aucun mécanisme d'audit sur threads). Cf. tâche Notion
« Unifier les modèles d'historique/audit »."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AuditLog, Roles, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from threads.models import Message, Thread


class AuditLogThreadsTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire audit threads", code="NT-AUDTH")
        self.service = Service.objects.create(ship=self.ship, name="Service audit threads")
        self.sector = Sector.objects.create(service=self.service, name="Secteur audit threads")
        self.asset_type = AssetType.objects.create(name="Extincteur audit threads", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite constatée")

        self.chef = User.objects.create_user(username="chef_audit_threads", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": Roles.CHEF_SECTION})

        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        self.thread = Thread.objects.create(content_type=ct, object_id=str(self.ticket.pk))
        self.message = Message.objects.create(thread=self.thread, author=self.chef, body="Un message")

        self.client_api = APIClient()
        self.client_api.login(username="chef_audit_threads", password="pass")

    def test_suppression_dun_message_par_son_auteur_genere_une_entree_daudit(self):
        r = self.client_api.delete(f"/api/threads/messages/{self.message.pk}/")
        self.assertEqual(r.status_code, 204)
        entree = AuditLog.objects.get(action="delete_message")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn(str(self.message.pk), entree.details)
        self.assertIsNotNone(entree.created_at)

    def test_suppression_dun_fil_genere_une_entree_daudit(self):
        r = self.client_api.delete(f"/api/threads/threads/{self.thread.pk}/")
        self.assertEqual(r.status_code, 204)
        entree = AuditLog.objects.get(action="delete_thread")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn(str(self.thread.pk), entree.details)

    def test_suppression_refusee_ne_genere_aucune_entree(self):
        autre = User.objects.create_user(username="autre_audit_threads", password="pass")
        UserProfile.objects.update_or_create(user=autre, defaults={"role": Roles.CHEF_SECTION})
        client_autre = APIClient()
        client_autre.login(username="autre_audit_threads", password="pass")
        r = client_autre.delete(f"/api/threads/messages/{self.message.pk}/")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(AuditLog.objects.filter(action="delete_message").exists())
