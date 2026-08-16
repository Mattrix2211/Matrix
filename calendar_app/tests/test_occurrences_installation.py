"""Vérifie que le calendrier et l'export iCal gèrent correctement les occurrences
de maintenance liées à une installation fixe (installation_maintenance), au même
titre que celles liées à du matériel mobile (asset) — non-régression du bug où le
titre affichait "None" et où les occurrences d'installation disparaissaient dès
qu'un filtre de périmètre (navire/service/secteur) était appliqué."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from icalendar import Calendar

from assets.models import Asset, AssetType, Installation, InstallationMaintenance, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Ship, Service, Sector
from calendar_app.views import _titre_occurrence


class OccurrencesInstallationCalendrierTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NTC1")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        # Un second secteur, sur un autre navire, pour vérifier l'exclusion du filtre.
        self.autre_ship = Ship.objects.create(name="Autre navire", code="NTC2")
        self.autre_service = Service.objects.create(ship=self.autre_ship, name="Autre service")
        self.autre_sector = Sector.objects.create(service=self.autre_service, name="Autre secteur")

        self.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        self.occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=self.maintenance,
            scheduled_for=timezone.localdate(),
            status="PLANNED",
        )

        self.user = User.objects.create_user(username="marin", password="pass")
        self.occ.assignees.add(self.user)
        self.client.login(username="marin", password="pass")

    def test_titre_occurrence_installation(self):
        """Le libellé d'une occurrence d'installation n'est jamais 'None'."""
        titre = _titre_occurrence(self.occ)
        self.assertEqual(titre, f"{self.installation} - Graissage")
        self.assertNotIn("None", titre)

    def test_calendar_events_affiche_le_bon_titre(self):
        url = reverse("calendar-events") + f"?date={timezone.localdate().isoformat()}&view=day"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        events = resp.json()
        maint_events = [e for e in events if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(len(maint_events), 1)
        self.assertNotIn("None", maint_events[0]["title"])
        self.assertIn("Graissage", maint_events[0]["title"])

    def test_collect_events_affiche_le_bon_titre(self):
        url = reverse("calendar-index") + f"?date={timezone.localdate().isoformat()}&view=day"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        events = resp.context["events"]
        maint_events = [e for e in events if e["type"] == "maintenance"]
        self.assertEqual(len(maint_events), 1)
        self.assertNotIn("None", maint_events[0]["title"])
        self.assertIn("Graissage", maint_events[0]["title"])

    def test_ical_feed_affiche_le_bon_titre(self):
        url = reverse("calendar-ical-my")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        cal = Calendar.from_ical(resp.content)
        summaries = [str(c.get("summary")) for c in cal.walk() if c.name == "VEVENT"]
        self.assertEqual(len(summaries), 1)
        self.assertNotIn("None", summaries[0])
        self.assertIn("Graissage", summaries[0])

    def test_filtre_secteur_inclut_occurrence_installation_du_bon_secteur(self):
        url = reverse("calendar-events") + (
            f"?date={timezone.localdate().isoformat()}&view=day&sector={self.sector.id}"
        )
        resp = self.client.get(url)
        events = resp.json()
        maint_events = [e for e in events if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(len(maint_events), 1)

    def test_filtre_secteur_exclut_occurrence_installation_dun_autre_secteur(self):
        url = reverse("calendar-events") + (
            f"?date={timezone.localdate().isoformat()}&view=day&sector={self.autre_sector.id}"
        )
        resp = self.client.get(url)
        events = resp.json()
        maint_events = [e for e in events if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(len(maint_events), 0)

    def test_filtre_navire_inclut_occurrence_installation_du_bon_navire(self):
        url = reverse("calendar-events") + (
            f"?date={timezone.localdate().isoformat()}&view=day&ship={self.ship.id}"
        )
        resp = self.client.get(url)
        events = resp.json()
        maint_events = [e for e in events if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(len(maint_events), 1)

    def test_filtre_navire_exclut_occurrence_installation_dun_autre_navire(self):
        url = reverse("calendar-events") + (
            f"?date={timezone.localdate().isoformat()}&view=day&ship={self.autre_ship.id}"
        )
        resp = self.client.get(url)
        events = resp.json()
        maint_events = [e for e in events if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(len(maint_events), 0)

    def test_non_regression_occurrence_asset_toujours_affichee(self):
        """Une occurrence de matériel mobile (asset) reste correctement affichée
        et filtrée, sans régression du comportement existant."""
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        asset = Asset.objects.create(asset_type=asset_type, ship=self.ship, service=self.service, sector=self.sector)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle annuel", every_n_days=365)
        occ_asset = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        occ_asset.assignees.add(self.user)

        url = reverse("calendar-events") + (
            f"?date={timezone.localdate().isoformat()}&view=day&sector={self.sector.id}"
        )
        resp = self.client.get(url)
        events = resp.json()
        maint_events = [e for e in events if e["extendedProps"]["type"] == "maintenance"]
        # L'occurrence d'installation (créée dans setUp) et celle d'asset sont toutes
        # les deux dans le même secteur : les deux doivent apparaître.
        self.assertEqual(len(maint_events), 2)
