"""Contrôle d'accès à l'arbre de compétences (CompetencyTreeView) : chaque
marin doit voir SON arbre (celui de son secteur), quel que soit le niveau de
son profil (navire/service/secteur/section), et un référent de formation
(TrainingCourse.referents, système déjà livré — cf. training/models.py) doit
en plus voir les arbres des secteurs où il forme, même hors de son propre
périmètre hiérarchique."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector, Section
from training.models import TrainingCourse


class EquipierRattacheAUneSectionTests(TestCase):
    """Cas le plus courant pour un équipier : profil rattaché à une section,
    pas directement à un secteur. Avant correctif, _secteurs_visibles ne
    traduisait pas ce niveau de périmètre et l'arbre était totalement
    inaccessible (aucun secteur proposé)."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Section", code="SEC")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.section = Section.objects.create(sector=self.sector, name="Équipe A")
        TrainingCourse.objects.create(sector=self.sector, title="Extinction niveau 1")

        self.equipier = User.objects.create_user(username="equipier_section", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "section": self.section},
        )

    def test_equipier_voit_son_propre_secteur(self):
        self.client.login(username="equipier_section", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["secteur"], self.sector)
        self.assertIn(self.sector, list(r.context["secteurs"]))

    def test_arbre_affiche_bien_les_formations_du_secteur(self):
        self.client.login(username="equipier_section", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertContains(r, "Extinction niveau 1")


class ReferentHorsPerimetreTests(TestCase):
    """Un référent désigné sur une formation d'un secteur hors de son propre
    périmètre doit quand même pouvoir accéder à l'arbre de ce secteur."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Référent Arbre", code="RAR")
        service = Service.objects.create(ship=ship, name="Technique")
        self.mon_secteur = Sector.objects.create(service=service, name="Mon secteur")
        self.secteur_forme = Sector.objects.create(service=service, name="Secteur formé")
        TrainingCourse.objects.create(sector=self.mon_secteur, title="Formation de mon secteur")
        self.formation_a_referer = TrainingCourse.objects.create(
            sector=self.secteur_forme, title="Formation encadrée",
        )

        self.referent = User.objects.create_user(username="referent_arbre", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent, defaults={"role": "EQUIPIER", "sector": self.mon_secteur},
        )
        self.formation_a_referer.referents.add(self.referent)

    def test_referent_voit_le_secteur_quil_forme_en_plus_du_sien(self):
        self.client.login(username="referent_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertEqual(r.status_code, 200)
        secteurs = list(r.context["secteurs"])
        self.assertIn(self.mon_secteur, secteurs)
        self.assertIn(self.secteur_forme, secteurs)

    def test_referent_peut_afficher_larbre_du_secteur_forme(self):
        self.client.login(username="referent_arbre", password="pass")
        r = self.client.get(f"/formations/arbre-competences/?secteur={self.secteur_forme.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["secteur"], self.secteur_forme)
        self.assertContains(r, "Formation encadrée")

    def test_marin_non_referent_ne_voit_pas_le_secteur_forme_par_un_autre(self):
        marin = User.objects.create_user(username="marin_non_referent", password="pass")
        UserProfile.objects.update_or_create(
            user=marin, defaults={"role": "EQUIPIER", "sector": self.mon_secteur},
        )
        self.client.login(username="marin_non_referent", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        secteurs = list(r.context["secteurs"])
        self.assertIn(self.mon_secteur, secteurs)
        self.assertNotIn(self.secteur_forme, secteurs)
