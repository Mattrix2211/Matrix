"""Tests de base sur la hiérarchie navale Ship -> Service -> Sector -> Section
(org/models.py). L'app org ne portait aucun test de modèle avant cette tâche
(la fuite de périmètre RBAC est déjà couverte par test_scope_navire.py)."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from org.models import Ship, Service, Sector, Section


class HierarchieOrganisationnelleTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire Jean Bart", code="JB")
        self.service = Service.objects.create(ship=self.navire, name="Service Machines")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur Propulsion")
        self.section = Section.objects.create(sector=self.secteur, name="Section Diesel")

    def test_la_chaine_de_rattachement_est_correcte(self):
        self.assertEqual(self.service.ship, self.navire)
        self.assertEqual(self.secteur.service, self.service)
        self.assertEqual(self.section.sector, self.secteur)

    def test_les_relations_inverses_remontent_toute_la_hierarchie(self):
        self.assertIn(self.service, self.navire.services.all())
        self.assertIn(self.secteur, self.service.sectors.all())
        self.assertIn(self.section, self.secteur.sections.all())

    def test_representation_textuelle_qualifiee(self):
        """Le __str__ de chaque niveau inclut son parent, pour rester lisible
        dans les listes déroulantes des formulaires (principe « plus rapide
        qu'Excel » : pas d'ambiguïté entre deux secteurs de même nom sur deux
        navires différents)."""
        self.assertEqual(str(self.navire), "Navire Jean Bart")
        self.assertEqual(str(self.service), "Navire Jean Bart / Service Machines")
        self.assertEqual(str(self.secteur), "Navire Jean Bart / Service Machines / Secteur Propulsion")
        self.assertEqual(
            str(self.section), "Navire Jean Bart / Service Machines / Secteur Propulsion / Section Diesel"
        )

    def test_suppression_du_navire_supprime_toute_la_hierarchie_en_cascade(self):
        self.navire.delete()
        self.assertFalse(Service.objects.filter(pk=self.service.pk).exists())
        self.assertFalse(Sector.objects.filter(pk=self.secteur.pk).exists())
        self.assertFalse(Section.objects.filter(pk=self.section.pk).exists())

    def test_deux_navires_peuvent_avoir_un_service_de_meme_nom(self):
        """unique_together porte sur (ship, name), pas sur name seul : deux
        navires distincts peuvent chacun avoir un « Service Machines »."""
        autre_navire = Ship.objects.create(name="Navire Surcouf", code="SUR")
        Service.objects.create(ship=autre_navire, name="Service Machines")
        self.assertEqual(Service.objects.filter(name="Service Machines").count(), 2)

    def test_deux_services_du_meme_navire_ne_peuvent_pas_avoir_le_meme_nom(self):
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Service.objects.create(ship=self.navire, name="Service Machines")

    def test_deux_navires_ne_peuvent_pas_avoir_le_meme_code(self):
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Ship.objects.create(name="Autre navire", code="JB")

    def test_navire_archive_reste_par_defaut_visible_dans_le_flag(self):
        """Le champ 'archived' démarre à False : un navire nouvellement créé
        n'est jamais archivé par défaut."""
        self.assertFalse(self.navire.archived)
