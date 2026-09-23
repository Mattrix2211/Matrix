"""[FIX] Test dédié à la fonction de la migration de données 0028
(bascule des zones vers un positionnement x/y précis par matériel).

Suite au refus du Tech Lead : le code de
`assets/migrations/0028_migrer_zones_vers_positions.py` avait été relu ligne
par ligne et jugé correct sur le fond, mais aucun test ne l'exerçait
réellement — la base de développement était toujours vide de `Zone`, donc la
fonction `migrer_zones_vers_positions` n'avait jamais tourné concrètement.

Le modèle `Zone` est supprimé par cette même migration : il n'existe donc
plus dans le schéma actuel (`assets/models.py`) et ne peut pas être recréé
via l'ORM courant. Comme le projet ne dispose d'aucun précédent de test de
migration historique (pas de `MigratorTestCase`, pas de
`django-test-migrations`), on suit le repli explicitement autorisé pour ce
cas : appeler directement la fonction de migration, avec de vraies données
`Asset`/`Location`/`Deck` (modèles inchangés par cette migration) et un
bouchon minimal pour `Zone` reproduisant juste l'API utilisée par la
migration (`Zone.objects.exclude(location_id=None).iterator()`).
"""
import importlib

from django.test import TestCase

from assets.models import Asset, AssetType, Deck, Location
from org.models import Sector, Service, Ship

# Le nom du module de migration commence par un chiffre : pas un identifiant
# Python valide pour un `import` classique, d'où le chargement dynamique.
_module_migration = importlib.import_module("assets.migrations.0028_migrer_zones_vers_positions")
migrer_zones_vers_positions = _module_migration.migrer_zones_vers_positions


class ZoneFactice:
    """Reproduit une ligne de l'ancien modèle `Zone` (supprimé du schéma
    actuel), avec seulement les attributs lus par la migration."""

    def __init__(self, location_id=None, deck_id=None, points=None):
        self.location_id = location_id
        self.deck_id = deck_id
        self.points = points


class _RequeteZonesFactice:
    """Bouchon minimal de QuerySet, ne couvrant que `.exclude().iterator()`
    tel qu'utilisé par `migrer_zones_vers_positions`."""

    def __init__(self, zones):
        self._zones = list(zones)

    def exclude(self, location_id=None):
        return _RequeteZonesFactice(z for z in self._zones if z.location_id != location_id)

    def iterator(self):
        return iter(self._zones)


class GestionnaireZoneFactice:
    """Tient lieu de `Zone` (la classe modèle) : seul `.objects` est utilisé
    par la migration."""

    def __init__(self, zones):
        self.objects = _RequeteZonesFactice(zones)


class ApplicationsFactices:
    """Bouchon minimal de l'objet `apps` passé par Django aux migrations de
    données : renvoie le vrai modèle `Asset` (inchangé par cette migration)
    et un `Zone` factice construit à partir des zones fournies au test."""

    def __init__(self, zones):
        self._zone_factice = GestionnaireZoneFactice(zones)

    def get_model(self, app_label, model_name):
        if model_name == "Zone":
            return self._zone_factice
        if model_name == "Asset":
            return Asset
        raise LookupError(f"Modèle non prévu par ce bouchon de test : {app_label}.{model_name}")


class MigrerZonesVersPositionsTests(TestCase):
    """Exerce réellement `migrer_zones_vers_positions` avec des données
    construites à la main, plutôt qu'une simple relecture du code."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment A", code="BATA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        self.deck = Deck.objects.create(ship=self.ship, name="Pont principal", order=1)

    def _creer_asset(self, **kwargs):
        return Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector, **kwargs
        )

    def test_calcul_du_centre_geometrique_dun_rectangle(self):
        """Rectangle de points connu : le centre géométrique doit être la
        moyenne des x et des y, vérifiable à la main."""
        emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        zone = ZoneFactice(
            location_id=emplacement.id,
            deck_id=self.deck.id,
            points=[{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 20}, {"x": 0, "y": 20}],
        )
        materiel = self._creer_asset(location=emplacement)

        migrer_zones_vers_positions(ApplicationsFactices([zone]), None)

        materiel.refresh_from_db()
        self.assertEqual(materiel.plan_deck_id, self.deck.id)
        self.assertEqual(materiel.position_x, 5.0)
        self.assertEqual(materiel.position_y, 10.0)

    def test_un_materiel_deja_positionne_nest_pas_ecrase(self):
        """Un matériel déjà positionné avant la migration doit rester
        inchangé (une épingle existante ne doit jamais être écrasée)."""
        emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        autre_pont = Deck.objects.create(ship=self.ship, name="Pont inférieur", order=2)
        zone = ZoneFactice(
            location_id=emplacement.id,
            deck_id=self.deck.id,
            points=[{"x": 40, "y": 40}, {"x": 60, "y": 60}],
        )
        materiel = self._creer_asset(location=emplacement, plan_deck=autre_pont, position_x=1.0, position_y=2.0)

        migrer_zones_vers_positions(ApplicationsFactices([zone]), None)

        materiel.refresh_from_db()
        self.assertEqual(materiel.plan_deck_id, autre_pont.id)
        self.assertEqual(materiel.position_x, 1.0)
        self.assertEqual(materiel.position_y, 2.0)

    def test_une_zone_sans_emplacement_est_ignoree_sans_erreur(self):
        """Une zone sans `location` (Emplacement) n'a aucun matériel à
        positionner : elle doit être ignorée proprement, sans erreur."""
        zone = ZoneFactice(location_id=None, deck_id=self.deck.id, points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}])
        materiel = self._creer_asset(location=None)

        migrer_zones_vers_positions(ApplicationsFactices([zone]), None)

        materiel.refresh_from_db()
        self.assertIsNone(materiel.plan_deck)
        self.assertIsNone(materiel.position_x)
        self.assertIsNone(materiel.position_y)

    def test_points_malformes_ignores_sans_faire_planter_la_migration(self):
        """Points vides, absents, ou au format invalide : la migration ne
        doit jamais planter, et ne doit rien positionner pour ces zones."""
        emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        zones = [
            ZoneFactice(location_id=emplacement.id, deck_id=self.deck.id, points=[]),
            ZoneFactice(location_id=emplacement.id, deck_id=self.deck.id, points=None),
            # Valeur non convertible en nombre.
            ZoneFactice(location_id=emplacement.id, deck_id=self.deck.id, points=[{"x": "abc", "y": 1}]),
            # Clé "y" manquante.
            ZoneFactice(location_id=emplacement.id, deck_id=self.deck.id, points=[{"x": 1}]),
        ]
        materiel = self._creer_asset(location=emplacement)

        # Ne doit lever aucune exception.
        migrer_zones_vers_positions(ApplicationsFactices(zones), None)

        materiel.refresh_from_db()
        self.assertIsNone(materiel.plan_deck)
        self.assertIsNone(materiel.position_x)
        self.assertIsNone(materiel.position_y)

    def test_premier_arrive_lemporte_si_plusieurs_zones_pour_le_meme_emplacement(self):
        """Si le même Emplacement est couvert par plusieurs zones, la
        première zone rencontrée dans l'ordre de parcours doit l'emporter :
        le matériel ne doit pas être déplacé par les zones suivantes."""
        emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        pont_a = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        pont_b = Deck.objects.create(ship=self.ship, name="Pont B", order=2)
        premiere_zone = ZoneFactice(
            location_id=emplacement.id, deck_id=pont_a.id, points=[{"x": 0, "y": 0}, {"x": 20, "y": 20}]
        )
        seconde_zone = ZoneFactice(
            location_id=emplacement.id, deck_id=pont_b.id, points=[{"x": 80, "y": 80}, {"x": 100, "y": 100}]
        )
        materiel = self._creer_asset(location=emplacement)

        migrer_zones_vers_positions(ApplicationsFactices([premiere_zone, seconde_zone]), None)

        materiel.refresh_from_db()
        self.assertEqual(materiel.plan_deck_id, pont_a.id)
        self.assertEqual(materiel.position_x, 10.0)
        self.assertEqual(materiel.position_y, 10.0)
