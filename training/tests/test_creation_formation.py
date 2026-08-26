"""Tests du formulaire web de création d'une formation (TrainingCourse),
remplaçant l'admin Django pour cette opération. Seuil de permission
volontairement plus strict que la gestion des prérequis/catégorie/référents
d'une formation existante (RoleLevel.ADMIN_NAVIRE, cf. NIVEAU_REQUIS_CREATION_FORMATION
dans training/web_views.py) : demande explicite du Product Owner, la création
de nouvelles formations reste réservée à un administrateur pour l'instant.

Catalogue devenu global (tâche Notion « Formation unique et portable entre
navires ») : la création ne demande plus de secteur — une formation créée
par un ADMIN_NAVIRE est immédiatement visible par tous les navires."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship
from training.models import TrainingCourse


class CreationFormationAdminNavireTests(TestCase):
    """Un ADMIN_NAVIRE peut créer une formation, immédiatement visible par
    tout le catalogue global."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Créa", code="CREA")
        self.autre_formation = TrainingCourse.objects.create(title="Habilitation électrique niveau 1")

        self.admin = User.objects.create_user(username="admin_navire", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin, defaults={"role": "ADMIN_NAVIRE", "ship": self.ship},
        )

    def test_admin_navire_peut_creer_une_formation(self):
        self.client.login(username="admin_navire", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Habilitation électrique niveau 2",
            "description": "Formation de recyclage annuel.",
            "validity_days": "730",
            "category": "Habilitation électrique",
            "prerequisites": [self.autre_formation.id],
        })
        self.assertEqual(r.status_code, 302)
        formation = TrainingCourse.objects.get(title="Habilitation électrique niveau 2")
        self.assertEqual(formation.description, "Formation de recyclage annuel.")
        self.assertEqual(formation.validity_days, 730)
        self.assertEqual(formation.category, "Habilitation électrique")
        self.assertEqual(list(formation.prerequisites.all()), [self.autre_formation])

    def test_formation_creee_apparait_dans_le_catalogue_global(self):
        self.client.login(username="admin_navire", password="pass")
        self.client.post("/formations/", {"action": "create_course", "title": "Levage niveau 1"})
        r = self.client.get("/formations/")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Levage niveau 1", titres)

    def test_validite_par_defaut_si_champ_vide(self):
        self.client.login(username="admin_navire", password="pass")
        self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation sans durée précisée",
            "validity_days": "",
        })
        formation = TrainingCourse.objects.get(title="Formation sans durée précisée")
        self.assertEqual(formation.validity_days, 365)

    def test_titre_obligatoire(self):
        self.client.login(username="admin_navire", password="pass")
        r = self.client.post("/formations/", {"action": "create_course", "title": ""})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingCourse.objects.filter(title="").exists())

    def test_duree_de_validite_invalide_refusee(self):
        self.client.login(username="admin_navire", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation durée invalide",
            "validity_days": "-5",
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation durée invalide").exists())


class CreationFormationRefuseeAuxChefsTests(TestCase):
    """Un CHEF_SECTION (ou rôle inférieur) continue d'éditer les formations
    existantes (prérequis/catégorie/référents) mais ne doit pas pouvoir créer
    une toute nouvelle formation : seuil strictement réservé à ADMIN_NAVIRE."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Refus", code="REF")

        self.chef_section = User.objects.create_user(username="chef_section_creation", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section, defaults={"role": "CHEF_SECTION", "ship": self.ship},
        )
        self.commandant = User.objects.create_user(username="commandant_creation", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant, defaults={"role": "COMMANDANT", "ship": self.ship},
        )

    def test_chef_section_ne_peut_pas_creer_une_formation(self):
        self.client.login(username="chef_section_creation", password="pass")
        r = self.client.post("/formations/", {"action": "create_course", "title": "Formation refusée"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation refusée").exists())

    def test_commandant_ne_peut_pas_creer_une_formation(self):
        # ADMIN_NAVIRE est strictement plus élevé que COMMANDANT dans la
        # hiérarchie (RoleLevel) : le seuil de création exclut donc aussi le
        # commandant, cohérent avec la demande explicite du PO de réserver
        # cette action à un administrateur.
        self.client.login(username="commandant_creation", password="pass")
        r = self.client.post("/formations/", {"action": "create_course", "title": "Formation refusée bis"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation refusée bis").exists())

    def test_bouton_de_creation_absent_pour_le_chef_section(self):
        self.client.login(username="chef_section_creation", password="pass")
        r = self.client.get("/formations/")
        self.assertFalse(r.context["peut_creer_formation"])
        self.assertNotContains(r, "createCourseModal")
        self.assertNotContains(r, "Nouvelle formation")

    def test_bouton_de_modification_toujours_visible_pour_le_chef_section(self):
        # Le CHEF_SECTION garde l'accès au formulaire d'édition d'une formation
        # existante (prérequis/catégorie/référents), seule la création d'une
        # toute nouvelle formation lui est désormais interdite.
        self.client.login(username="chef_section_creation", password="pass")
        r = self.client.get("/formations/")
        self.assertTrue(r.context["peut_gerer_prerequis"])
