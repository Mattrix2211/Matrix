from django.test import TestCase

from org.models import Ship, Service, Sector
from assets.models import Installation


class InstallationStrTests(TestCase):
    """[BUG] Installation.__str__ ne doit pas dupliquer les segments navire/service.

    Service.__str__ et Sector.__str__ remontent déjà toute la chaîne
    hiérarchique (ex: "Navire / Service / Secteur"). Installation.__str__ doit
    donc utiliser le nom brut de chaque niveau, sans jamais répéter un
    segment déjà inclus.
    """

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire QA")
        self.service = Service.objects.create(name="Service QA", ship=self.ship)
        self.sector = Sector.objects.create(name="Secteur QA", service=self.service)

    def _verifier_aucun_doublon(self, libelle):
        segments = libelle.split(" / ")
        self.assertEqual(len(segments), len(set(segments)), f"Segments dupliqués dans : {libelle}")

    def test_installation_racine_sans_doublon(self):
        installation = Installation.objects.create(
            designation="Pompe de cale", ship=self.ship, service=self.service, sector=self.sector,
        )
        libelle = str(installation)
        self.assertEqual(libelle, "Pompe de cale (Navire QA / Service QA / Secteur QA)")
        self._verifier_aucun_doublon(libelle)

    def test_installation_avec_parent_direct_sans_doublon(self):
        groupe = Installation.objects.create(
            designation="Groupe propulsion", ship=self.ship, service=self.service, sector=self.sector,
        )
        moteur = Installation.objects.create(
            designation="Moteur bâbord", ship=self.ship, service=self.service, sector=self.sector, parent=groupe,
        )
        libelle = str(moteur)
        self.assertEqual(libelle, "Moteur bâbord (Navire QA / Service QA / Secteur QA)")
        self._verifier_aucun_doublon(libelle)

    def test_installation_imbriquee_plusieurs_niveaux_sans_doublon(self):
        groupe = Installation.objects.create(
            designation="Groupe propulsion", ship=self.ship, service=self.service, sector=self.sector,
        )
        moteur = Installation.objects.create(
            designation="Moteur bâbord", ship=self.ship, service=self.service, sector=self.sector, parent=groupe,
        )
        turbo = Installation.objects.create(
            designation="Turbocompresseur", ship=self.ship, service=self.service, sector=self.sector, parent=moteur,
        )
        libelle = str(turbo)
        self.assertEqual(libelle, "Turbocompresseur (Navire QA / Service QA / Secteur QA)")
        self._verifier_aucun_doublon(libelle)
