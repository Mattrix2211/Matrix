"""Vérifie la faille corrigée sur ThreadViewSet/MessageViewSet/AttachmentViewSet
(threads/views.py) : avant correction, AUCUN filtre de périmètre n'était
appliqué — un utilisateur authentifié pouvait lire, via l'API brute, les fils
de discussion (et pièces jointes) de tickets correctifs d'un AUTRE navire,
alors que la même information est déjà scopée côté web (logistics/web_views.py)
avant d'accéder au fil (threads/utils.py, docstring de module)."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from threads.models import Attachment, Message, Thread


class ScopeLeakThreadsTests(TestCase):
    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire Fil A", code="FLA")
        self.navire_b = Ship.objects.create(name="Navire Fil B", code="FLB")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.type_a = AssetType.objects.create(name="Type A", category="Cat", sector=self.secteur_a)
        self.type_b = AssetType.objects.create(name="Type B", category="Cat", sector=self.secteur_b)
        self.asset_a = Asset.objects.create(
            asset_type=self.type_a, ship=self.navire_a, service=self.service_a, sector=self.secteur_a
        )
        self.asset_b = Asset.objects.create(
            asset_type=self.type_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b
        )
        self.ticket_a = CorrectiveTicket.objects.create(asset=self.asset_a, description="Fuite A")
        self.ticket_b = CorrectiveTicket.objects.create(asset=self.asset_b, description="Fuite B")

        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        self.thread_a = Thread.objects.create(content_type=ct, object_id=str(self.ticket_a.pk))
        self.thread_b = Thread.objects.create(content_type=ct, object_id=str(self.ticket_b.pk))

        self.chef_a = User.objects.create_user(username="chef_fil_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SECTION", "ship": self.navire_a}
        )
        self.message_a = Message.objects.create(thread=self.thread_a, author=self.chef_a, body="Message A")

        self.chef_b = User.objects.create_user(username="chef_fil_b", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_b, defaults={"role": "CHEF_SECTION", "ship": self.navire_b}
        )
        self.message_b = Message.objects.create(thread=self.thread_b, author=self.chef_b, body="Message B")
        self.attachment_b = Attachment.objects.create(
            message=self.message_b, file="thread_attachments/fake.txt", name="fake.txt"
        )

        self.client = APIClient()
        self.client.login(username="chef_fil_a", password="pass")

    # --- Thread -----------------------------------------------------------

    def test_liste_des_fils_ne_contient_pas_celui_dun_autre_navire(self):
        r = self.client.get("/api/threads/threads/")
        self.assertEqual(r.status_code, 200)
        ids = {t["id"] for t in r.data}
        self.assertIn(self.thread_a.id, ids)
        self.assertNotIn(self.thread_b.id, ids)

    def test_ne_peut_pas_lire_un_fil_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/threads/threads/{self.thread_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_ne_peut_pas_supprimer_un_fil_dun_autre_navire(self):
        r = self.client.delete(f"/api/threads/threads/{self.thread_b.id}/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Thread.objects.filter(pk=self.thread_b.id).exists())

    # --- Message ------------------------------------------------------------

    def test_liste_des_messages_ne_contient_pas_celui_dun_autre_navire(self):
        r = self.client.get("/api/threads/messages/")
        self.assertEqual(r.status_code, 200)
        ids = {m["id"] for m in r.data}
        self.assertIn(self.message_a.id, ids)
        self.assertNotIn(self.message_b.id, ids)

    def test_ne_peut_pas_lire_un_message_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/threads/messages/{self.message_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_ne_peut_pas_modifier_un_message_dun_autre_navire(self):
        r = self.client.patch(
            f"/api/threads/messages/{self.message_b.id}/", {"body": "hack"}, format="json"
        )
        self.assertEqual(r.status_code, 404)
        self.message_b.refresh_from_db()
        self.assertEqual(self.message_b.body, "Message B")

    def test_ne_peut_pas_supprimer_un_message_dun_autre_navire(self):
        r = self.client.delete(f"/api/threads/messages/{self.message_b.id}/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Message.objects.filter(pk=self.message_b.id).exists())

    # --- Attachment -----------------------------------------------------

    def test_liste_des_pieces_jointes_ne_contient_pas_celle_dun_autre_navire(self):
        r = self.client.get("/api/threads/attachments/")
        self.assertEqual(r.status_code, 200)
        ids = {a["id"] for a in r.data}
        self.assertNotIn(self.attachment_b.id, ids)

    def test_ne_peut_pas_lire_une_piece_jointe_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/threads/attachments/{self.attachment_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_ne_peut_pas_supprimer_une_piece_jointe_dun_autre_navire(self):
        r = self.client.delete(f"/api/threads/attachments/{self.attachment_b.id}/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Attachment.objects.filter(pk=self.attachment_b.id).exists())
