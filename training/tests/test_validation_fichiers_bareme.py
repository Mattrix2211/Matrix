"""Test d'intégration de la validation serveur des fichiers téléversés
(tâche Notion [SEC]) sur le modèle représentatif de l'app training :
TrainingCourse.bareme, via la vraie vue de création (formation-list,
action="create_course").

Le validateur lui-même est testé en profondeur dans
matrix/core/tests/test_validators.py."""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import Roles, UserProfile
from org.models import Ship
from training.models import TrainingCourse


class ValidationBaremeFormationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire T-SEC-FILE-4", code="TSF4")
        self.admin = User.objects.create_user(username="admin_formation_sec", password="pass")
        UserProfile.objects.update_or_create(user=self.admin, defaults={"role": Roles.ADMIN_NAVIRE, "ship": self.ship})
        self.client.login(username="admin_formation_sec", password="pass")

    def _creer(self, bareme):
        return self.client.post("/formations/", {
            "action": "create_course", "title": "Habilitation électrique",
            "bareme": bareme,
        }, follow=True)

    def test_executable_renomme_en_bareme_refuse(self):
        faux_bareme = SimpleUploadedFile(
            "bareme.pdf", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64, content_type="application/pdf",
        )
        # Renommé avec une extension d'image pour déclencher le contrôle
        # Pillow (un .pdf n'est jamais décodé, seule sa taille/extension compte).
        faux_bareme_image = SimpleUploadedFile(
            "bareme.png", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64, content_type="image/png",
        )
        self._creer(faux_bareme_image)
        self.assertFalse(TrainingCourse.objects.filter(title="Habilitation électrique").exists())

    def test_bareme_document_valide_accepte(self):
        bareme = SimpleUploadedFile("bareme.pdf", b"contenu du bareme", content_type="application/pdf")
        self._creer(bareme)
        course = TrainingCourse.objects.get(title="Habilitation électrique")
        self.assertTrue(course.bareme)
