"""Couverture de base sur threads/models.py et threads/views.py — la
protection « seul l'auteur modifie son message » est déjà couverte par
test_permissions.py. Ce fichier couvre le reste du cycle de vie basique :
création d'un fil de discussion générique (GenericForeignKey), ajout de
messages, et le seuil de rôle requis pour créer un Thread.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile, Roles
from logistics.models import CorrectiveTicket
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType
from threads.models import Thread, Message


class ThreadMessageBasicsTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NTT")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector)
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite constatée")

        self.equipier = User.objects.create_user(username="equip_thread", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": Roles.EQUIPIER})
        self.equipier.refresh_from_db()

        self.chef_section = User.objects.create_user(username="chef_thread", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_section, defaults={"role": Roles.CHEF_SECTION})
        self.chef_section.refresh_from_db()

    def test_un_fil_peut_etre_rattache_a_nimporte_quel_objet_via_la_generic_fk(self):
        """Un thread peut être attaché à un CorrectiveTicket (ou tout autre
        modèle) via GenericForeignKey — c'est la raison d'être de l'app."""
        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        thread = Thread.objects.create(content_type=ct, object_id=str(self.ticket.pk))
        self.assertEqual(thread.content_object, self.ticket)

    def test_les_messages_dun_fil_sont_accessibles_via_la_relation_inverse(self):
        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        thread = Thread.objects.create(content_type=ct, object_id=str(self.ticket.pk))
        Message.objects.create(thread=thread, author=self.equipier, body="Première remarque")
        Message.objects.create(thread=thread, author=self.chef_section, body="Réponse")
        self.assertEqual(thread.messages.count(), 2)

    def test_creation_dun_fil_refusee_sous_le_seuil_chef_section(self):
        """ThreadViewSet impose min_role_level_write = CHEF_SECTION."""
        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        client = APIClient()
        client.login(username="equip_thread", password="pass")
        r = client.post("/api/threads/threads/", {"content_type": ct.id, "object_id": str(self.ticket.pk)})
        self.assertEqual(r.status_code, 403)

    def test_creation_dun_fil_autorisee_au_seuil_chef_section(self):
        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        client = APIClient()
        client.login(username="chef_thread", password="pass")
        r = client.post("/api/threads/threads/", {"content_type": ct.id, "object_id": str(self.ticket.pk)})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Thread.objects.filter(content_type=ct, object_id=str(self.ticket.pk)).exists())

    def test_tout_equipier_connecte_peut_poster_un_message_sur_un_fil_existant(self):
        """MessageViewSet utilise IsAuthorOrReadOnly (pas de seuil de rôle) :
        n'importe quel marin connecté peut participer à une discussion."""
        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        thread = Thread.objects.create(content_type=ct, object_id=str(self.ticket.pk))
        client = APIClient()
        client.login(username="equip_thread", password="pass")
        r = client.post(
            "/api/threads/messages/", {"thread": thread.id, "author": self.equipier.id, "body": "Bien reçu"},
        )
        self.assertEqual(r.status_code, 201)
