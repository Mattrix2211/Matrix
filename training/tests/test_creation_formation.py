"""Tests du formulaire web de création d'une formation (TrainingCourse),
remplaçant l'admin Django pour cette opération. Seuil de permission
volontairement plus strict que la gestion des prérequis/catégorie/référents
d'une formation existante (RoleLevel.ADMIN_NAVIRE, cf. NIVEAU_REQUIS_CREATION_FORMATION
dans training/web_views.py) : demande explicite du Product Owner, la création
de nouvelles formations reste réservée à un administrateur pour l'instant."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from training.models import TrainingCourse


class CreationFormationAdminNavireTests(TestCase):
    """Un ADMIN_NAVIRE peut créer une formation dans son périmètre."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Créa", code="CREA")
        self.service = Service.objects.create(ship=self.ship, name="Technique")
        self.sector = Sector.objects.create(service=self.service, name="Électricité")
        self.autre_formation = TrainingCourse.objects.create(
            sector=self.sector, title="Habilitation électrique niveau 1",
        )

        self.admin = User.objects.create_user(username="admin_navire", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin, defaults={"role": "ADMIN_NAVIRE", "ship": self.ship},
        )

    def test_admin_navire_peut_creer_une_formation(self):
        self.client.login(username="admin_navire", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Habilitation électrique niveau 2",
            "sector": self.sector.id,
            "description": "Formation de recyclage annuel.",
            "validity_days": "730",
            "category": "Habilitation électrique",
            "prerequisites": [self.autre_formation.id],
        })
        self.assertEqual(r.status_code, 302)
        formation = TrainingCourse.objects.get(title="Habilitation électrique niveau 2")
        self.assertEqual(formation.sector, self.sector)
        self.assertEqual(formation.description, "Formation de recyclage annuel.")
        self.assertEqual(formation.validity_days, 730)
        self.assertEqual(formation.category, "Habilitation électrique")
        self.assertEqual(list(formation.prerequisites.all()), [self.autre_formation])

    def test_formation_creee_apparait_dans_la_liste_de_son_secteur(self):
        self.client.login(username="admin_navire", password="pass")
        self.client.post("/formations/", {
            "action": "create_course",
            "title": "Levage niveau 1",
            "sector": self.sector.id,
        })
        r = self.client.get(f"/formations/?sector={self.sector.id}")
        titres = [f.title for f in r.context["formations"]]
        self.assertIn("Levage niveau 1", titres)

    def test_validite_par_defaut_si_champ_vide(self):
        self.client.login(username="admin_navire", password="pass")
        self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation sans durée précisée",
            "sector": self.sector.id,
            "validity_days": "",
        })
        formation = TrainingCourse.objects.get(title="Formation sans durée précisée")
        self.assertEqual(formation.validity_days, 365)

    def test_titre_obligatoire(self):
        self.client.login(username="admin_navire", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "",
            "sector": self.sector.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingCourse.objects.filter(sector=self.sector, title="").exists())

    def test_duree_de_validite_invalide_refusee(self):
        self.client.login(username="admin_navire", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation durée invalide",
            "sector": self.sector.id,
            "validity_days": "-5",
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation durée invalide").exists())

    def test_prerequis_dun_autre_secteur_ignore(self):
        autre_sector = Sector.objects.create(service=self.service, name="Autre secteur")
        hors_secteur = TrainingCourse.objects.create(sector=autre_sector, title="Formation hors secteur")
        self.client.login(username="admin_navire", password="pass")
        self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation avec prérequis invalide",
            "sector": self.sector.id,
            "prerequisites": [hors_secteur.id],
        })
        formation = TrainingCourse.objects.get(title="Formation avec prérequis invalide")
        self.assertEqual(formation.prerequisites.count(), 0)


class CreationFormationRefuseeAuxChefsTests(TestCase):
    """Un CHEF_SECTION (ou rôle inférieur) continue d'éditer les formations
    existantes (prérequis/catégorie/référents) mais ne doit pas pouvoir créer
    une toute nouvelle formation : seuil strictement réservé à ADMIN_NAVIRE."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Refus", code="REF")
        self.service = Service.objects.create(ship=self.ship, name="Sécurité")
        self.sector = Sector.objects.create(service=self.service, name="Incendie")

        self.chef_section = User.objects.create_user(username="chef_section_creation", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section, defaults={"role": "CHEF_SECTION", "sector": self.sector},
        )
        self.commandant = User.objects.create_user(username="commandant_creation", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant, defaults={"role": "COMMANDANT", "ship": self.ship},
        )

    def test_chef_section_ne_peut_pas_creer_une_formation(self):
        self.client.login(username="chef_section_creation", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation refusée",
            "sector": self.sector.id,
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation refusée").exists())

    def test_commandant_ne_peut_pas_creer_une_formation(self):
        # ADMIN_NAVIRE est strictement plus élevé que COMMANDANT dans la
        # hiérarchie (RoleLevel) : le seuil de création exclut donc aussi le
        # commandant, cohérent avec la demande explicite du PO de réserver
        # cette action à un administrateur.
        self.client.login(username="commandant_creation", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation refusée bis",
            "sector": self.sector.id,
        })
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


class PerimetreCreationFormationTests(TestCase):
    """Le secteur choisi à la création doit être limité au périmètre visible
    par l'appelant — pas de fuite entre navires même pour un ADMIN_NAVIRE."""

    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire Périmètre A", code="PA")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Technique")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Électricité")

        self.navire_b = Ship.objects.create(name="Navire Périmètre B", code="PB")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Technique")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Électricité")

        # Administrateur navire scopé UNIQUEMENT au navire A : périmètre
        # explicitement restreint (sans quoi scope_filters_for_user() renvoie
        # {} et le test ne détecterait aucune fuite).
        self.admin_a = User.objects.create_user(username="admin_navire_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin_a, defaults={"role": "ADMIN_NAVIRE", "ship": self.navire_a},
        )

    def test_admin_ne_peut_pas_creer_sur_un_secteur_dun_autre_navire(self):
        self.client.login(username="admin_navire_a", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation hors périmètre",
            "sector": self.secteur_b.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingCourse.objects.filter(title="Formation hors périmètre").exists())

    def test_secteur_dun_autre_navire_absent_du_formulaire(self):
        self.client.login(username="admin_navire_a", password="pass")
        r = self.client.get("/formations/")
        secteurs_ids = [s.id for s in r.context["secteurs"]]
        self.assertIn(self.secteur_a.id, secteurs_ids)
        self.assertNotIn(self.secteur_b.id, secteurs_ids)

    def test_admin_peut_creer_sur_un_secteur_de_son_propre_navire(self):
        self.client.login(username="admin_navire_a", password="pass")
        r = self.client.post("/formations/", {
            "action": "create_course",
            "title": "Formation dans le périmètre",
            "sector": self.secteur_a.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TrainingCourse.objects.filter(title="Formation dans le périmètre").exists())
