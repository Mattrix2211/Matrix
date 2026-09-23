"""Tests de l'extension du journal d'audit transverse (AuditLog) au
déplacement d'événements partagés depuis le calendrier central — colonne
vertébrale de Matrix (CLAUDE.md) — par un chef qui n'est pas l'assigné
personnel de l'objet déplacé : action à enjeu de traçabilité, jusqu'ici
totalement invisible (aucun mécanisme d'audit sur calendar_app). Cf. tâche
Notion « Unifier les modèles d'historique/audit ».

Le déplacement d'un événement PERSONNEL (PersonalEvent, privé, propre à son
seul créateur) reste hors du périmètre de l'audit — pas plus qu'un marin qui
modifie son propre agenda Excel."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType, Installation
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingSession


class AuditLogCalendarMoveTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire audit calendrier", code="NT-AUDCAL")
        self.service = Service.objects.create(ship=self.navire, name="Service audit calendrier")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur audit calendrier")

        asset_type = AssetType.objects.create(name="Extincteur audit", category="Incendie", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.ticket = CorrectiveTicket.objects.create(
            asset=self.asset, description="Fuite", planned_for=timezone.localdate(),
        )

        self.installation = Installation.objects.create(
            designation="Pompe audit calendrier", ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan audit", every_n_days=30)
        self.occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )

        self.formation = TrainingCourse.objects.create(title="Formation audit calendrier")
        self.session = TrainingSession.objects.create(course=self.formation, scheduled_at=timezone.now())

        self.chef = User.objects.create_user(username="chef_audit_cal", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)
        # Le chef doit être personnellement affecté à la session pour pouvoir
        # la déplacer (règle métier existante de calendar_event_move).
        self.session.attendees.add(self.chef)

        self.url = reverse("calendar-event-move")
        self.nouvelle_date = (timezone.localdate() + timedelta(days=3)).isoformat()

    def test_deplacement_dun_ticket_genere_une_entree_daudit(self):
        self.client.login(username="chef_audit_cal", password="pass")
        self.client.post(self.url, {"type": "ticket", "id": str(self.ticket.pk), "date": self.nouvelle_date})
        entree = AuditLog.objects.get(action="calendar_move_ticket")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn(str(self.ticket.pk), entree.details)
        self.assertIsNotNone(entree.created_at)

    def test_deplacement_dune_occurrence_par_un_chef_non_assigne_genere_une_entree(self):
        self.client.login(username="chef_audit_cal", password="pass")
        self.client.post(self.url, {"type": "maintenance", "id": str(self.occ.pk), "date": self.nouvelle_date})
        entree = AuditLog.objects.get(action="calendar_move_occurrence")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn(str(self.occ.pk), entree.details)

    def test_deplacement_dune_session_de_formation_genere_une_entree(self):
        self.client.login(username="chef_audit_cal", password="pass")
        self.client.post(
            self.url, {"type": "training", "id": str(self.session.pk), "date": self.nouvelle_date + "T09:00"}
        )
        entree = AuditLog.objects.get(action="calendar_move_training_session")
        self.assertEqual(entree.actor, self.chef)
        self.assertIn(str(self.session.pk), entree.details)
