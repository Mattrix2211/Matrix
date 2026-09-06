"""Non-régression du bug Notion « Précédent/Aujourd'hui/Suivant ne
rafraîchissent pas les événements affichés » : FullCalendar envoie à chaque
navigation des paramètres `start`/`end` frais (même si le `date` transmis par
le gabarit reste figé côté client), et le backend doit leur donner la
priorité plutôt que de recalculer la période à partir de `view`+`date`."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class NavigationCalendrierStartEndTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NAV1")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector)
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Contrôle annuel", every_n_days=365)

        self.jour_initial = timezone.localdate()
        self.jour_navigue = self.jour_initial + timezone.timedelta(days=2)

        self.occ_jour_initial = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.jour_initial, status="PLANNED",
        )
        self.occ_jour_navigue = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.jour_navigue, status="PLANNED",
        )

        self.user = User.objects.create_user(username="marin", password="pass")
        self.occ_jour_initial.assignees.add(self.user)
        self.occ_jour_navigue.assignees.add(self.user)
        self.client.login(username="marin", password="pass")

    def _titres(self, resp):
        return [e["title"] for e in resp.json() if e["extendedProps"]["type"] == "maintenance"]

    def test_start_end_prime_sur_le_date_fige(self):
        """Comme FullCalendar après un clic sur « Suivant » : le paramètre
        `date` de la requête reste figé sur le jour initial (page chargée une
        seule fois), mais `start`/`end` pointent déjà sur le nouveau jour
        navigué — la réponse doit refléter `start`/`end`, pas `date`."""
        url = reverse("calendar-events") + (
            f"?view=day&date={self.jour_initial.isoformat()}"
            f"&start={self.jour_navigue.isoformat()}&end={(self.jour_navigue + timezone.timedelta(days=1)).isoformat()}"
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        titres = self._titres(resp)
        self.assertEqual(len(titres), 1)
        self.assertIn(str(self.asset), titres[0])
        # Vérifie qu'il s'agit bien de l'occurrence du jour navigué et pas de
        # celle du jour initial (même titre générique, on distingue par id).
        ids = [e["id"] for e in resp.json() if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(ids, [f"occ-{self.occ_jour_navigue.id}"])

    def test_repli_sur_view_et_date_si_start_end_absents(self):
        """Sans `start`/`end` (autres appelants éventuels de l'endpoint), le
        comportement historique par `view`+`date` doit rester inchangé."""
        url = reverse("calendar-events") + f"?view=day&date={self.jour_initial.isoformat()}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        ids = [e["id"] for e in resp.json() if e["extendedProps"]["type"] == "maintenance"]
        self.assertEqual(ids, [f"occ-{self.occ_jour_initial.id}"])
