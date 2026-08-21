from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from org.models import Ship, Service, Sector
from assets.models import (
    Asset,
    AssetType,
    Installation,
    InstallationMaintenance,
    ModeDeclenchement,
)
from maintenance.models import MaintenanceOccurrence


class CalendarEvenementsOccurrenceInstallationTests(TestCase):
    """Vérifie que les occurrences de maintenance liées à une Installation fixe
    (et non à un Asset de matériel mobile) apparaissent correctement dans le
    calendrier, avec le bon titre et sans être exclues par les filtres de
    périmètre (navire/service/secteur)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NT")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.installation = Installation.objects.create(
            designation="Pompe immergée",
            ship=self.ship,
            service=self.service,
            sector=self.sector,
        )
        self.installation_maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
        )
        self.occurrence = MaintenanceOccurrence.objects.create(
            installation_maintenance=self.installation_maintenance,
            scheduled_for=timezone.localdate(),
            status="PLANNED",
        )
        self.user = User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")

    def test_titre_evenement_installation_pas_none(self):
        """Le titre de l'événement doit contenir le nom de l'installation, et
        surtout jamais la chaîne 'None' (régression : occ.asset est toujours
        None pour une occurrence liée à une installation)."""
        response = self.client.get("/calendar/events/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        occ_events = [e for e in data if e["id"] == f"occ-{self.occurrence.id}"]
        self.assertEqual(len(occ_events), 1)
        titre = occ_events[0]["title"]
        self.assertIn("Pompe immergée", titre)
        self.assertNotIn("None", titre)

    def test_titre_evenement_installation_page_web(self):
        """Même vérification côté vue web (CalendarView._collect_events)."""
        response = self.client.get("/calendar/")
        self.assertEqual(response.status_code, 200)
        titres = [e["title"] for e in response.context["events"]]
        self.assertTrue(any("Pompe immergée" in t and "None" not in t for t in titres))

    def test_filtre_perimetre_navire_conserve_occurrence_installation(self):
        """Une occurrence d'installation ne doit pas disparaître silencieusement
        quand on filtre le calendrier par navire/service/secteur."""
        response = self.client.get(f"/calendar/events/?ship={self.ship.id}")
        data = response.json()
        ids = [e["id"] for e in data]
        self.assertIn(f"occ-{self.occurrence.id}", ids)

    def test_filtre_perimetre_secteur_conserve_occurrence_installation(self):
        response = self.client.get(f"/calendar/events/?sector={self.sector.id}")
        data = response.json()
        ids = [e["id"] for e in data]
        self.assertIn(f"occ-{self.occurrence.id}", ids)

    def test_filtre_perimetre_autre_navire_exclut_occurrence_installation(self):
        """À l'inverse, un filtre sur un autre navire doit bien exclure
        l'occurrence (le filtrage de périmètre doit rester actif)."""
        autre_navire = Ship.objects.create(name="Autre navire", code="AN")
        response = self.client.get(f"/calendar/events/?ship={autre_navire.id}")
        data = response.json()
        ids = [e["id"] for e in data]
        self.assertNotIn(f"occ-{self.occurrence.id}", ids)

    def test_titre_evenement_asset_toujours_correct(self):
        """Non-régression : le cas matériel mobile (asset) doit continuer à
        afficher correctement son nom."""
        asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        asset = Asset.objects.create(
            asset_type=asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        from maintenance.models import MaintenancePlan

        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Plan A", every_n_days=30)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        response = self.client.get("/calendar/events/")
        data = response.json()
        occ_events = [e for e in data if e["id"] == f"occ-{occ.id}"]
        self.assertEqual(len(occ_events), 1)
        self.assertNotIn("None", occ_events[0]["title"])
