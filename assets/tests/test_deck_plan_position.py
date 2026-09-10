"""[FEAT] Modèle de données : ponts du navire et positionnement précis du
matériel sur leur plan (épingle x/y).

Fondation pour le plan visuel du navire : Deck (pont), et le positionnement
d'un matériel (Asset.plan_deck/position_x/position_y) dessus. Remplace
l'ancien modèle Zone (zone rectangulaire cliquable reliée à un Emplacement,
groupant plusieurs matériels) : chaque épingle désigne désormais un seul
matériel, à un point précis du plan — décision métier tranchée par
l'utilisateur (cf. tâche Notion « Remplacer les zones du plan navire par un
placement PRÉCIS du matériel »).
"""
from django.db import IntegrityError, transaction
from django.test import TestCase

from assets.models import Asset, AssetType, Deck
from org.models import Sector, Service, Ship


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


class AssetPlanPositionTests(TestCase):
    """Positionnement précis d'un matériel (Asset) sur le plan d'un pont."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment A", code="BATA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.pont = Deck.objects.create(ship=self.ship, name="Pont principal", order=1)
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)

    def _creer_asset(self, **kwargs):
        return Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector, **kwargs
        )

    def test_positionnement_dun_materiel_sur_le_plan_dun_pont(self):
        materiel = self._creer_asset(plan_deck=self.pont, position_x=10.5, position_y=42.25)
        self.assertEqual(materiel.plan_deck, self.pont)
        self.assertIn(materiel, self.pont.assets_positionnes.all())
        self.assertEqual(materiel.position_x, 10.5)
        self.assertEqual(materiel.position_y, 42.25)

    def test_un_materiel_non_positionne_a_une_position_vide_par_defaut(self):
        materiel = self._creer_asset()
        self.assertIsNone(materiel.plan_deck)
        self.assertIsNone(materiel.position_x)
        self.assertIsNone(materiel.position_y)

    def test_suppression_du_pont_retire_le_materiel_du_plan_sans_le_supprimer(self):
        """SET_NULL : la suppression d'un pont ne doit jamais supprimer le
        matériel qui y était positionné (donnée de présentation seulement)."""
        materiel = self._creer_asset(plan_deck=self.pont, position_x=10, position_y=10)
        self.pont.delete()
        materiel.refresh_from_db()
        self.assertIsNone(materiel.plan_deck)
        self.assertTrue(Asset.objects.filter(pk=materiel.pk).exists())

    def test_etat_plan_ok_par_defaut(self):
        materiel = self._creer_asset(plan_deck=self.pont, position_x=10, position_y=10, status="OK")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_OK)

    def test_etat_plan_danger_si_hors_service(self):
        materiel = self._creer_asset(plan_deck=self.pont, position_x=10, position_y=10, status="OUT_OF_SERVICE")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_DANGER)
