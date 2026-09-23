from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, TicketStatusLog
from maintenance.models import MaintenanceOccurrence, MaintenanceExecution, MaintenancePlan
from notifications.models import Notification, NotificationLevel


class CorrectiveTicketSignalTests(TestCase):
    """Vérifie le chemin nominal du workflow phare documenté dans CLAUDE.md :
    « inspection NON_CONFORME → création auto d'un CorrectiveTicket »
    (maintenance/models.py, signal create_corrective_on_non_conform).

    Le cas installation (création volontairement bloquée, faute d'équivalent
    CorrectiveTicket côté installation fixe) est déjà couvert par
    maintenance/tests/test_execution_installation.py. Ici, on couvre le cas
    nominal du matériel mobile (Asset), qui est le seul cas où CorrectiveTicket
    est réellement créé.
    """

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NT5")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Contrôle annuel", every_n_days=365,
        )
        self.tech = User.objects.create_user(username="tech2", password="pass")

    def test_execution_non_conforme_sur_asset_cree_un_ticket_correctif(self):
        """Le signal post_save crée automatiquement un CorrectiveTicket dès qu'une
        MaintenanceExecution liée à un Asset passe en conformity=NON_CONFORME."""
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2026-01-15", status="ASSIGNED",
        )
        self.assertEqual(CorrectiveTicket.objects.count(), 0)

        MaintenanceExecution.objects.create(
            occurrence=occ, executed_by=self.tech, conformity="NON_CONFORME",
        )

        self.assertEqual(CorrectiveTicket.objects.count(), 1)
        ticket = CorrectiveTicket.objects.get()
        self.assertEqual(ticket.asset, self.asset)
        self.assertEqual(ticket.description, f"Anomalie détectée sur maintenance {occ.id}")
        self.assertEqual(ticket.severity, 3)
        self.assertEqual(ticket.status, "REPORTED")

        # Le journal d'historique du ticket est initialisé en cohérence avec sa création.
        log = TicketStatusLog.objects.get(ticket=ticket)
        self.assertEqual(log.old_status, "REPORTED")
        self.assertEqual(log.new_status, "REPORTED")

    def test_execution_conforme_ne_cree_aucun_ticket(self):
        """Non-régression : une exécution conforme sur du matériel mobile ne doit
        déclencher aucune création de ticket correctif."""
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2026-01-15", status="ASSIGNED",
        )
        MaintenanceExecution.objects.create(occurrence=occ, executed_by=self.tech, conformity="CONFORME")
        self.assertEqual(CorrectiveTicket.objects.count(), 0)

    def test_deux_sauvegardes_non_conformes_sur_la_meme_execution_ne_dupliquent_pas_le_ticket(self):
        """get_or_create() est basé sur (asset, description) : un second save() de la
        même exécution (ex. ajout de notes après coup) ne doit pas créer un second
        ticket pour la même occurrence."""
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2026-01-15", status="ASSIGNED",
        )
        execution = MaintenanceExecution.objects.create(
            occurrence=occ, executed_by=self.tech, conformity="NON_CONFORME",
        )
        execution.notes = "Complément après inspection"
        execution.save()

        self.assertEqual(CorrectiveTicket.objects.count(), 1)

    def test_chemin_complet_via_lapi_complete(self):
        """Vérifie le workflow bout en bout tel que déclenché par l'endpoint web
        /api/maintenance/occurrences/<id>/complete/ (utilisé par la checklist guidée
        de scan QR), pas uniquement le signal en isolation."""
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2026-01-15", status="ASSIGNED",
        )
        occ.assignees.add(self.tech)
        client = APIClient()
        client.login(username="tech2", password="pass")

        r = client.post(
            f"/api/maintenance/occurrences/{occ.id}/complete/",
            {"conformity": "NON_CONFORME", "notes": "Fuite constatée"},
        )
        self.assertEqual(r.status_code, 200)
        occ.refresh_from_db()
        self.assertEqual(occ.status, "WAITING_VALIDATION")

        ticket = CorrectiveTicket.objects.get(asset=self.asset)
        self.assertEqual(ticket.status, "REPORTED")
        self.assertIn(str(occ.id), ticket.description)


class CorrectiveTicketSignalNotificationTests(TestCase):
    """Le chemin de création automatique (inspection QR non conforme) doit
    informer les chefs du périmètre au même titre que le signalement manuel
    (tâche Notion « Élargir les notifications au-delà du seul niveau DANGER »)
    — c'est le même événement métier (anomalie détectée sur un actif), seul
    le déclencheur diffère."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Notif QR", code="NQR")
        self.service = Service.objects.create(ship=self.ship, name="Service Notif QR")
        self.sector = Sector.objects.create(service=self.service, name="Secteur Notif QR")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Contrôle annuel", every_n_days=365,
        )
        self.tech = User.objects.create_user(username="tech_notif_qr", password="pass")

        self.chef_secteur = User.objects.create_user(username="chef_secteur_notif_qr", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector}
        )

    def _executer_inspection_non_conforme(self):
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2026-01-15", status="ASSIGNED",
        )
        MaintenanceExecution.objects.create(
            occurrence=occ, executed_by=self.tech, conformity="NON_CONFORME",
        )
        return occ

    def test_chef_du_perimetre_est_notifie_a_la_creation_automatique(self):
        self._executer_inspection_non_conforme()
        ticket = CorrectiveTicket.objects.get(asset=self.asset)
        notif = Notification.objects.get(user=self.chef_secteur)
        # Ticket auto-créé avec severity=3 (valeur par défaut) → niveau WARNING,
        # même mapping que la création manuelle (severity == 3).
        self.assertEqual(notif.level, NotificationLevel.WARNING)
        self.assertIn(str(self.asset), notif.verb)
        self.assertIn(ticket.description, notif.verb)

    def test_technicien_executant_nest_pas_notifie_en_double(self):
        # Si le technicien qui a exécuté l'inspection est aussi un chef du
        # périmètre (ici du secteur, seul niveau scopé par l'actif dans ce
        # test), il n'a pas besoin d'être notifié de sa propre inspection.
        UserProfile.objects.update_or_create(
            user=self.tech, defaults={"role": "CHEF_SECTEUR", "sector": self.sector}
        )
        self._executer_inspection_non_conforme()
        self.assertFalse(Notification.objects.filter(user=self.tech).exists())

    def test_pas_de_notification_si_aucun_ticket_nest_cree(self):
        # Non-régression : une exécution conforme ne crée ni ticket ni
        # notification (le garde "if created_ticket" ne doit pas se déclencher
        # sur un get_or_create qui récupère un ticket déjà existant).
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for="2026-01-15", status="ASSIGNED",
        )
        MaintenanceExecution.objects.create(occurrence=occ, executed_by=self.tech, conformity="CONFORME")
        self.assertFalse(Notification.objects.exists())
