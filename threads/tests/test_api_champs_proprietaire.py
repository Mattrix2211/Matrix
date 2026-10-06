"""API discussions : auteur, message système, fil et message de rattachement
ne doivent jamais être choisis par l'appelant."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from threads.models import Attachment, Message, Thread


class ApiDiscussionsChampsProprietaireTests(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(CorrectiveTicket)
        self.ticket_a, self.ticket_b = (self._ticket(n) for n in ("A", "B"))
        self.thread_a = Thread.objects.create(content_type=self.ct, object_id=str(self.ticket_a.pk))
        self.thread_b = Thread.objects.create(content_type=self.ct, object_id=str(self.ticket_b.pk))
        self.chef_a = self._marin("chef_a_dsc", self.ticket_a.asset.ship)
        self.chef_b = self._marin("chef_b_dsc", self.ticket_b.asset.ship)
        self.message_a = Message.objects.create(thread=self.thread_a, author=self.chef_a, body="A")
        self.message_b = Message.objects.create(thread=self.thread_b, author=self.chef_b, body="B")
        self.client_a = APIClient()
        self.client_a.login(username="chef_a_dsc", password="pass")

    def _ticket(self, nom):
        navire = Ship.objects.create(name=f"Navire {nom} dsc", code=f"{nom}-DSC")
        service = Service.objects.create(ship=navire, name=f"Service {nom}")
        secteur = Sector.objects.create(service=service, name=f"Secteur {nom}")
        type_ = AssetType.objects.create(name=f"Type {nom}", category="Cat", sector=secteur)
        asset = Asset.objects.create(asset_type=type_, ship=navire, service=service, sector=secteur)
        return CorrectiveTicket.objects.create(asset=asset, description=f"Panne {nom}")

    def _marin(self, username, navire):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "CHEF_SECTION", "ship": navire})
        return user

    def test_auteur_et_message_systeme_non_choisis_par_l_appelant(self):
        r = self.client_a.post(
            "/api/threads/messages/",
            {"thread": self.thread_a.pk, "body": "Faux", "author": self.chef_b.pk,
             "is_system": True, "created_by": self.chef_b.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        message = Message.objects.get(pk=r.data["id"])
        self.assertEqual(message.author, self.chef_a)
        self.assertFalse(message.is_system)
        self.assertEqual(message.created_by, self.chef_a)

    def test_message_sur_un_fil_hors_perimetre_refuse(self):
        r = self.client_a.post(
            "/api/threads/messages/", {"thread": self.thread_b.pk, "body": "Intrus"}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Message.objects.filter(body="Intrus").exists())

    def test_message_ne_peut_pas_changer_de_fil(self):
        r = self.client_a.patch(
            f"/api/threads/messages/{self.message_a.pk}/", {"thread": self.thread_b.pk}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.message_a.refresh_from_db()
        self.assertEqual(self.message_a.thread, self.thread_a)

    def test_message_ne_peut_pas_changer_d_auteur_ni_devenir_systeme(self):
        r = self.client_a.patch(
            f"/api/threads/messages/{self.message_a.pk}/",
            {"body": "Modifié", "author": self.chef_b.pk, "is_system": True},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.message_a.refresh_from_db()
        self.assertEqual(self.message_a.author, self.chef_a)
        self.assertFalse(self.message_a.is_system)

    def test_piece_jointe_sur_le_message_d_un_autre_refusee(self):
        autre = Message.objects.create(thread=self.thread_a, author=self.chef_b, body="Autre")
        r = self.client_a.post(
            "/api/threads/attachments/",
            {"message": autre.pk, "name": "x.txt", "file": SimpleUploadedFile("x.txt", b"x")},
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Attachment.objects.exists())

    def test_piece_jointe_sur_son_propre_message_acceptee(self):
        r = self.client_a.post(
            "/api/threads/attachments/",
            {"message": self.message_a.pk, "name": "x.txt", "file": SimpleUploadedFile("x.txt", b"x")},
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Attachment.objects.get().created_by, self.chef_a)

    def test_fil_sur_un_objet_hors_perimetre_refuse(self):
        Thread.objects.all().delete()
        r = self.client_a.post(
            "/api/threads/threads/", {"content_type": self.ct.pk, "object_id": str(self.ticket_b.pk)}
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Thread.objects.exists())
