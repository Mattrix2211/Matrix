"""[FEAT] Modèle de données : ponts et zones cliquables d'un navire.

Fondation pour le futur plan visuel du navire (silhouette/ponts réels). Cette
tâche ne couvre que le modèle de données : Deck (pont) et Zone (zone cliquable
sur le plan d'un pont, reliée à un Emplacement existant).
"""
from django.db import IntegrityError, transaction
from django.test import TestCase

from assets.models import Deck, Location, Zone
from org.models import Ship


class DeckTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment A", code="BATA")

    def test_creation_dun_pont(self):
        pont = Deck.objects.create(ship=self.ship, name="Pont supérieur", order=1)
        self.assertEqual(pont.name, "Pont supérieur")
        self.assertEqual(pont.ship, self.ship)
        self.assertEqual(pont.order, 1)

    def test_ordre_daffichage_des_ponts(self):
        """L'ordre d'affichage (et non l'ordre alphabétique) doit primer dans la
        navigation entre ponts."""
        Deck.objects.create(ship=self.ship, name="Pont principal", order=2)
        Deck.objects.create(ship=self.ship, name="Pont supérieur", order=1)
        Deck.objects.create(ship=self.ship, name="Pont inférieur", order=3)
        noms = list(Deck.objects.filter(ship=self.ship).values_list("name", flat=True))
        self.assertEqual(noms, ["Pont supérieur", "Pont principal", "Pont inférieur"])

    def test_deux_ponts_ne_peuvent_pas_porter_le_meme_nom_sur_un_meme_navire(self):
        Deck.objects.create(ship=self.ship, name="Pont principal", order=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Deck.objects.create(ship=self.ship, name="Pont principal", order=2)

    def test_le_meme_nom_de_pont_est_autorise_sur_deux_navires_differents(self):
        autre_navire = Ship.objects.create(name="Bâtiment B", code="BATB")
        Deck.objects.create(ship=self.ship, name="Pont principal", order=1)
        # Ne doit pas lever d'exception : l'unicité est scopée par navire.
        Deck.objects.create(ship=autre_navire, name="Pont principal", order=1)


class ZoneTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment A", code="BATA")
        self.pont = Deck.objects.create(ship=self.ship, name="Pont principal", order=1)
        self.emplacement = Location.objects.create(ship=self.ship, name="Local machine")

    def test_creation_dune_zone_liee_a_un_emplacement_existant(self):
        zone = Zone.objects.create(
            deck=self.pont,
            name="Local machine avant",
            location=self.emplacement,
            points=[
                {"x": 10, "y": 10}, {"x": 40, "y": 10},
                {"x": 40, "y": 30}, {"x": 10, "y": 30},
            ],
        )
        self.assertEqual(zone.deck, self.pont)
        self.assertEqual(zone.location, self.emplacement)
        self.assertIn(zone, self.emplacement.zones.all())
        self.assertEqual(len(zone.points), 4)

    def test_contour_par_defaut_est_une_liste_vide(self):
        zone = Zone.objects.create(deck=self.pont, name="Zone sans contour", location=self.emplacement)
        self.assertEqual(zone.points, [])

    def test_suppression_dun_emplacement_met_la_zone_a_none_sans_erreur(self):
        """SET_NULL : la suppression d'un emplacement ne doit pas être bloquée
        par une simple zone de plan (donnée de présentation)."""
        zone = Zone.objects.create(deck=self.pont, name="Local machine avant", location=self.emplacement)
        self.emplacement.delete()
        zone.refresh_from_db()
        self.assertIsNone(zone.location)

    def test_creation_dune_zone_brouillon_sans_emplacement(self):
        """Une zone peut être dessinée avant qu'un emplacement lui soit
        assigné (flux brouillon de l'éditeur visuel)."""
        zone = Zone.objects.create(deck=self.pont, name="Zone en cours de rattachement")
        self.assertIsNone(zone.location)

    def test_suppression_du_pont_supprime_ses_zones(self):
        zone = Zone.objects.create(deck=self.pont, name="Local machine avant", location=self.emplacement)
        self.pont.delete()
        self.assertFalse(Zone.objects.filter(pk=zone.pk).exists())
