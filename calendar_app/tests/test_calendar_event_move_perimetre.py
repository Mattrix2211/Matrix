"""[SEC] Vérifie que calendar_event_move revalide le périmètre de l'objet
déplacé (ticket correctif ou session de formation), et pas seulement le
niveau de rôle de l'appelant. Sans ce contrôle, un CHEF_SECTION peut
replanifier un ticket ou une session d'un autre navire en devinant son ID."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingSession


class CalendarEventMovePerimetreTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.navire, name="Service A")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur A")

        self.autre_navire = Ship.objects.create(name="Navire B", code="NAV-B")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Service B")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Secteur B")

        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur)
        autre_asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.autre_secteur)

        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.autre_asset = Asset.objects.create(
            asset_type=autre_asset_type, ship=self.autre_navire, service=self.autre_service, sector=self.autre_secteur,
        )

        self.ticket = CorrectiveTicket.objects.create(
            asset=self.asset, description="Fuite hydraulique", planned_for=timezone.localdate(),
        )
        self.ticket_autre_navire = CorrectiveTicket.objects.create(
            asset=self.autre_asset, description="Panne moteur", planned_for=timezone.localdate(),
        )

        self.formation = TrainingCourse.objects.create(sector=self.secteur, title="Sécurité incendie")
        self.autre_formation = TrainingCourse.objects.create(sector=self.autre_secteur, title="Sécurité incendie")

        self.session = TrainingSession.objects.create(
            course=self.formation, scheduled_at=timezone.now(),
        )
        self.session_autre_navire = TrainingSession.objects.create(
            course=self.autre_formation, scheduled_at=timezone.now(),
        )

        self.chef = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.url = reverse("calendar-event-move")
        self.nouvelle_date = (timezone.localdate() + timedelta(days=3)).isoformat()

    def test_chef_section_peut_deplacer_un_ticket_de_son_perimetre(self):
        self.client.login(username="chef", password="pass")
        resp = self.client.post(self.url, {"type": "ticket", "id": str(self.ticket.pk), "date": self.nouvelle_date})
        self.assertEqual(resp.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.planned_for.isoformat(), self.nouvelle_date)

    def test_chef_section_ne_peut_pas_deplacer_un_ticket_hors_perimetre(self):
        """Un CHEF_SECTION ne doit pas pouvoir replanifier le ticket d'un autre
        navire en devinant son identifiant (faille IDOR)."""
        self.client.login(username="chef", password="pass")
        date_initiale = self.ticket_autre_navire.planned_for
        resp = self.client.post(
            self.url, {"type": "ticket", "id": str(self.ticket_autre_navire.pk), "date": self.nouvelle_date}
        )
        self.assertEqual(resp.status_code, 403)
        self.ticket_autre_navire.refresh_from_db()
        self.assertEqual(self.ticket_autre_navire.planned_for, date_initiale)

    def test_chef_section_peut_deplacer_une_session_de_son_perimetre(self):
        self.client.login(username="chef", password="pass")
        resp = self.client.post(
            self.url, {"type": "training", "id": str(self.session.pk), "date": self.nouvelle_date + "T09:00"}
        )
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(timezone.localdate(self.session.scheduled_at).isoformat(), self.nouvelle_date)

    def test_chef_section_ne_peut_pas_deplacer_une_session_hors_perimetre(self):
        """Un CHEF_SECTION ne doit pas pouvoir replanifier la session d'un autre
        navire en devinant son identifiant (faille IDOR)."""
        self.client.login(username="chef", password="pass")
        date_initiale = self.session_autre_navire.scheduled_at
        resp = self.client.post(
            self.url,
            {"type": "training", "id": str(self.session_autre_navire.pk), "date": self.nouvelle_date + "T09:00"},
        )
        self.assertEqual(resp.status_code, 403)
        self.session_autre_navire.refresh_from_db()
        self.assertEqual(self.session_autre_navire.scheduled_at, date_initiale)


from assets.models import Installation
from maintenance.models import MaintenanceOccurrence, MaintenancePlan


class CalendarEventMoveOccurrencePerimetreTests(TestCase):
    """[QA] Verifie si la branche 'maintenance' (occurrences) de
    calendar_event_move revalide elle aussi le perimetre de l'objet deplace,
    comme les branches 'ticket' et 'training' corrigees par le Dev. Un
    CHEF_SECTION+ qui n'est pas assigne a l'occurrence ne devrait pouvoir
    deplacer que les occurrences de son propre perimetre."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="NAV-A2")
        self.service = Service.objects.create(ship=self.navire, name="Service A2")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur A2")

        self.autre_navire = Ship.objects.create(name="Navire B", code="NAV-B2")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Service B2")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Secteur B2")

        self.installation = Installation.objects.create(
            designation="Pompe A", ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.autre_installation = Installation.objects.create(
            designation="Pompe B", ship=self.autre_navire, service=self.autre_service, sector=self.autre_secteur,
        )

        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan A", every_n_days=30)

        autre_asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.autre_secteur)
        self.autre_asset = Asset.objects.create(
            asset_type=autre_asset_type, ship=self.autre_navire, service=self.autre_service, sector=self.autre_secteur,
        )
        self.autre_plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.autre_asset, name="Plan B", every_n_days=30
        )

        self.occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        self.occ_autre_navire = MaintenanceOccurrence.objects.create(
            plan=self.autre_plan, asset=self.autre_asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )

        self.chef = User.objects.create_user(username="chef_occ", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.url = reverse("calendar-event-move")
        self.nouvelle_date = (timezone.localdate() + timedelta(days=3)).isoformat()

    def test_chef_section_non_assigne_ne_peut_pas_deplacer_une_occurrence_hors_perimetre(self):
        """Un CHEF_SECTION du secteur A, non assigne a l'occurrence, ne doit
        pas pouvoir replanifier une occurrence de maintenance rattachee a un
        autre navire en devinant son identifiant (meme faille IDOR que pour
        les tickets/sessions, non corrigee sur cette branche)."""
        self.client.login(username="chef_occ", password="pass")
        date_initiale = self.occ_autre_navire.scheduled_for
        resp = self.client.post(
            self.url, {"type": "maintenance", "id": str(self.occ_autre_navire.pk), "date": self.nouvelle_date}
        )
        self.assertEqual(resp.status_code, 403)
        self.occ_autre_navire.refresh_from_db()
        self.assertEqual(self.occ_autre_navire.scheduled_for, date_initiale)
