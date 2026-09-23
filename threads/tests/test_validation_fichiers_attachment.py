"""Test d'intégration de la validation serveur des fichiers téléversés
(tâche Notion [SEC]) sur le modèle représentatif de l'app threads :
Attachment.file, via l'API REST (AttachmentViewSet) — seul point d'entrée de
création d'une pièce jointe de discussion dans ce module.

Le validateur lui-même est testé en profondeur dans
matrix/core/tests/test_validators.py."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Roles, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from threads.models import Attachment, Message, Thread


class ValidationFichierAttachmentTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire T-SEC-FILE-3", code="TSF3")
        self.service = Service.objects.create(ship=self.ship, name="Service")
        self.sector = Sector.objects.create(service=self.service, name="Secteur")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector)
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite constatée")

        ct = ContentType.objects.get_for_model(CorrectiveTicket)
        self.thread = Thread.objects.create(content_type=ct, object_id=str(self.ticket.pk))

        self.equipier = User.objects.create_user(username="equip_attachment", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": Roles.EQUIPIER, "ship": self.ship})
        self.message = Message.objects.create(thread=self.thread, author=self.equipier, body="Voir pièce jointe")

        self.client_api = APIClient()
        self.client_api.login(username="equip_attachment", password="pass")

    def test_executable_renomme_refuse_par_l_api(self):
        faux_document = SimpleUploadedFile(
            "notice.pdf", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64, content_type="application/pdf",
        )
        # .pdf n'est jamais décodé par Pillow : on force une extension
        # d'image pour déclencher le contrôle de contenu.
        faux_image = SimpleUploadedFile(
            "virus.png", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64, content_type="image/png",
        )
        reponse = self.client_api.post(
            "/api/threads/attachments/",
            {"message": self.message.id, "file": faux_image, "name": "virus.png"},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Attachment.objects.filter(message=self.message).exists())

    def test_document_valide_accepte_par_l_api(self):
        document = SimpleUploadedFile("notice.pdf", b"contenu du document", content_type="application/pdf")
        reponse = self.client_api.post(
            "/api/threads/attachments/",
            {"message": self.message.id, "file": document, "name": "notice.pdf"},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 201)
        self.assertTrue(Attachment.objects.filter(message=self.message).exists())
