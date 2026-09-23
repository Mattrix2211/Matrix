"""Vérifie le booléen `peut_agir` exposé par calendar_events dans les
extendedProps de chaque événement (calendar_app/views.py) : il doit
reproduire EXACTEMENT la même règle de permission/périmètre que la vue cible
(OccurrenceExecuteView pour la maintenance, TicketTransitionView pour les
tickets), pour que le popover de détail rapide du calendrier (calendar/
index.html) sache afficher ou non des actions rapides sans dupliquer cette
logique côté JavaScript. Vérifie aussi qu'un événement personnel n'expose
peut_agir qu'à son propriétaire, et que la page calendrier continue de se
charger normalement après la mise en place du popover."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from calendar_app.models import PersonalEvent
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


def _evenement(evenements, type_attendu):
    trouves = [e for e in evenements if e["extendedProps"]["type"] == type_attendu]
    assert trouves, f"Aucun événement de type {type_attendu} trouvé dans la réponse"
    return trouves[0]


class CalendarIndexChargementTests(TestCase):
    """Non-régression : la page calendrier doit continuer à se charger (200)
    après le remplacement du rechargement de page par un popover JS."""

    def test_calendar_index_se_charge(self):
        marin = User.objects.create_user(username="marin_index", password="pass")
        self.client.login(username="marin_index", password="pass")
        reponse = self.client.get(reverse("calendar-index"))
        self.assertEqual(reponse.status_code, 200)


class PeutAgirMaintenanceTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="NAV-PA")
        self.service = Service.objects.create(ship=self.navire, name="Service A")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur A")
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan A", every_n_days=30)
        self.occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        self.url = reverse("calendar-events") + f"?date={timezone.localdate().isoformat()}&view=day"

    def test_peut_agir_vrai_si_assigne(self):
        """Un équipier assigné à l'occurrence peut l'exécuter (même règle que
        OccurrenceExecuteView), même sans rôle particulier."""
        equipier = User.objects.create_user(username="equipier_assigne", password="pass")
        UserProfile.objects.filter(user=equipier).update(role="EQUIPIER", sector=self.secteur)
        self.occ.assignees.add(equipier)
        self.client.login(username="equipier_assigne", password="pass")
        evenements = self.client.get(self.url).json()
        occ_event = _evenement(evenements, "maintenance")
        self.assertTrue(occ_event["extendedProps"]["peut_agir"])

    def test_peut_agir_faux_si_ni_assigne_ni_chef(self):
        """Un équipier non assigné et sans rôle de chef ne peut pas exécuter
        l'occurrence : aucune action rapide ne doit lui être proposée."""
        equipier = User.objects.create_user(username="equipier_non_assigne", password="pass")
        UserProfile.objects.filter(user=equipier).update(role="EQUIPIER", sector=self.secteur)
        self.client.login(username="equipier_non_assigne", password="pass")
        evenements = self.client.get(self.url).json()
        occ_event = _evenement(evenements, "maintenance")
        self.assertFalse(occ_event["extendedProps"]["peut_agir"])

    def test_peut_agir_vrai_si_chef_section_du_perimetre(self):
        """Un CHEF_SECTION du même périmètre peut agir, même non assigné."""
        chef = User.objects.create_user(username="chef_perimetre", password="pass")
        UserProfile.objects.filter(user=chef).update(role="CHEF_SECTION", sector=self.secteur)
        self.client.login(username="chef_perimetre", password="pass")
        evenements = self.client.get(self.url).json()
        occ_event = _evenement(evenements, "maintenance")
        self.assertTrue(occ_event["extendedProps"]["peut_agir"])

    def test_peut_agir_faux_si_chef_section_hors_perimetre(self):
        """Un CHEF_SECTION d'un autre secteur, non assigné, ne doit pas
        pouvoir agir : le périmètre prime sur le seul niveau de rôle, comme
        pour OccurrenceExecuteView."""
        autre_secteur = Sector.objects.create(
            service=Service.objects.create(ship=Ship.objects.create(name="Navire B", code="NAV-PB"), name="Service B"),
            name="Secteur B",
        )
        chef_ailleurs = User.objects.create_user(username="chef_ailleurs", password="pass")
        UserProfile.objects.filter(user=chef_ailleurs).update(role="CHEF_SECTION", sector=autre_secteur)
        self.client.login(username="chef_ailleurs", password="pass")
        evenements = self.client.get(self.url).json()
        occ_event = _evenement(evenements, "maintenance")
        self.assertFalse(occ_event["extendedProps"]["peut_agir"])


class PeutAgirTicketTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire C", code="NAV-PC")
        self.service = Service.objects.create(ship=self.navire, name="Service C")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur C")
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.ticket = CorrectiveTicket.objects.create(
            asset=self.asset, description="Fuite", planned_for=timezone.localdate(),
        )
        self.url = reverse("calendar-events") + f"?date={timezone.localdate().isoformat()}&view=day"

    def test_peut_agir_vrai_pour_chef_section_du_perimetre(self):
        chef = User.objects.create_user(username="chef_ticket", password="pass")
        UserProfile.objects.filter(user=chef).update(role="CHEF_SECTION", sector=self.secteur)
        self.client.login(username="chef_ticket", password="pass")
        evenements = self.client.get(self.url).json()
        ticket_event = _evenement(evenements, "ticket")
        self.assertTrue(ticket_event["extendedProps"]["peut_agir"])

    def test_peut_agir_faux_pour_simple_equipier(self):
        """Un équipier (rôle insuffisant) ne peut pas faire transitionner un
        ticket, même de son propre périmètre — même seuil que
        TicketTransitionView (CHEF_SECTION et au-dessus)."""
        equipier = User.objects.create_user(username="equipier_ticket", password="pass")
        UserProfile.objects.filter(user=equipier).update(role="EQUIPIER", sector=self.secteur)
        self.client.login(username="equipier_ticket", password="pass")
        evenements = self.client.get(self.url).json()
        ticket_event = _evenement(evenements, "ticket")
        self.assertFalse(ticket_event["extendedProps"]["peut_agir"])


class PeutAgirPersonnelTests(TestCase):
    def test_peut_agir_vrai_pour_le_proprietaire(self):
        marin = User.objects.create_user(username="proprietaire", password="pass")
        aujourdhui = timezone.localdate()
        PersonalEvent.objects.create(
            owner=marin, title="Rappel",
            starts_at=timezone.make_aware(timezone.datetime.combine(aujourdhui, timezone.datetime.min.time())),
        )
        self.client.login(username="proprietaire", password="pass")
        url = reverse("calendar-events") + f"?date={aujourdhui.isoformat()}&view=day"
        evenements = self.client.get(url).json()
        perso_event = _evenement(evenements, "personal")
        self.assertTrue(perso_event["extendedProps"]["peut_agir"])
