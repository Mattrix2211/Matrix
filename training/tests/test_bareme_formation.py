"""Tests du barème/référentiel de notation associé à une formation
(TrainingCourse.bareme, retour de test PO : « pour chaque formation il
faudrait qu'on puisse y affilier une fiche avec le barème de la formation si
il y en a un »). Simple FileField optionnel, même pattern que
TrainingRecord.attachment (training/models.py) : téléversé/remplacé/retiré
depuis les mêmes formulaires que la création/l'édition d'une formation."""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Sector, Section, Service, Ship
from training.models import TrainingCourse


def _fichier(nom="bareme.pdf"):
    return SimpleUploadedFile(nom, b"contenu factice du bareme", content_type="application/pdf")


class BaremeCreationFormationTests(TestCase):
    """Un ADMIN_NAVIRE peut associer un barème dès la création d'une
    formation (formulaire « Nouvelle formation »)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Bareme", code="BAR")
        self.admin = User.objects.create_user(username="admin_bareme", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin, defaults={"role": "ADMIN_NAVIRE", "ship": self.ship},
        )

    def test_bareme_associe_a_la_creation(self):
        self.client.login(username="admin_bareme", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Habilitation électrique niveau 3",
            "bareme": _fichier(),
        })
        self.assertEqual(r.status_code, 302)
        formation = TrainingCourse.objects.get(title="Habilitation électrique niveau 3")
        self.assertTrue(formation.bareme)
        self.assertIn("bareme", formation.bareme.name)

    def test_creation_sans_bareme_reste_possible(self):
        self.client.login(username="admin_bareme", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation sans barème",
        })
        self.assertEqual(r.status_code, 302)
        formation = TrainingCourse.objects.get(title="Formation sans barème")
        self.assertFalse(formation.bareme)

    def test_carte_de_formation_affiche_le_lien_du_bareme(self):
        formation = TrainingCourse.objects.create(title="Amarrage avancé", bareme=_fichier())
        self.client.login(username="admin_bareme", password="pass")
        r = self.client.get("/formations/")
        self.assertContains(r, "Voir le barème")
        self.assertContains(r, formation.bareme.url)

    def test_carte_de_formation_sans_bareme_naffiche_aucun_lien(self):
        TrainingCourse.objects.create(title="Formation vierge de barème")
        self.client.login(username="admin_bareme", password="pass")
        r = self.client.get("/formations/")
        self.assertNotContains(r, "Voir le barème")


class BaremeEditionFormationTests(TestCase):
    """Un CHEF_SECTION+ peut remplacer ou retirer le barème d'une formation
    existante depuis le formulaire d'édition (action update_prerequisites,
    même modale que la catégorie/les prérequis/les référents)."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = self._construire_bord()
        self.formation = TrainingCourse.objects.create(title="Levage niveau 1", bareme=_fichier("ancien.pdf"))
        self.chef = User.objects.create_user(username="chef_bareme", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION"})

    @staticmethod
    def _construire_bord():
        ship = Ship.objects.create(name="Navire Bareme Edition", code="BARE")
        service = Service.objects.create(ship=ship, name="Service")
        sector = Sector.objects.create(service=service, name="Secteur")
        section = Section.objects.create(sector=sector, name="Section")
        return ship, service, sector, section

    def test_remplacement_du_bareme(self):
        self.client.login(username="chef_bareme", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.formation.id,
            "bareme": _fichier("nouveau.pdf"),
        })
        self.assertEqual(r.status_code, 302)
        self.formation.refresh_from_db()
        self.assertIn("nouveau", self.formation.bareme.name)

    def test_retrait_du_bareme(self):
        self.client.login(username="chef_bareme", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.formation.id,
            "retirer_bareme": "1",
        })
        self.assertEqual(r.status_code, 302)
        self.formation.refresh_from_db()
        self.assertFalse(self.formation.bareme)

    def test_aucune_modification_du_bareme_si_ni_fichier_ni_retrait(self):
        self.client.login(username="chef_bareme", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.formation.id,
            "category": "Levage",
        })
        self.assertEqual(r.status_code, 302)
        self.formation.refresh_from_db()
        self.assertTrue(self.formation.bareme)
        self.assertIn("ancien", self.formation.bareme.name)


class BaremeFormationBordTests(TestCase):
    """Le barème peut aussi être associé lors de la proposition d'une
    formation « gérée par le bord » (Circuit C)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Bareme Bord", code="BARB")
        self.service = Service.objects.create(ship=self.ship, name="Service")
        self.sector = Sector.objects.create(service=self.service, name="Secteur")
        self.chef_secteur = User.objects.create_user(username="chef_secteur_bareme", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )

    def test_bareme_associe_lors_de_la_proposition_bord(self):
        self.client.login(username="chef_secteur_bareme", password="pass")
        r = self.client.post("/formations/", {
            "action": "proposer_formation_bord",
            "title": "Sécurité incendie interne avec barème",
            "bareme": _fichier(),
        })
        self.assertEqual(r.status_code, 302)
        course = TrainingCourse.objects.get(title="Sécurité incendie interne avec barème")
        self.assertTrue(course.bareme)
