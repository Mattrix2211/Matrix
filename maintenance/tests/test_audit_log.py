"""Tests de l'extension du journal d'audit transverse (AuditLog) aux
transitions de statut d'une occurrence de maintenance, et de la mise en
service effective d'OccurrenceStatusLog (jusqu'ici défini mais jamais
alimenté par le code applicatif) — cf. tâche Notion « Unifier les modèles
d'historique/audit (AuditLog générique vs logs ad hoc par app) ».

OccurrenceStatusLog reste le modèle dédié (historique structuré propre à
l'occurrence, symétrique de TicketStatusLog côté logistique) ; AuditLog est
alimenté EN PLUS, au même point de passage, pour la vue transverse."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from assets.models import Installation, InstallationMaintenance, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence, OccurrenceStatusLog
from org.models import Sector, Service, Ship


class AuditLogOccurrenceTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire audit occurrence", code="NT-AUDO")
        self.service = Service.objects.create(ship=self.ship, name="Service audit occurrence")
        self.sector = Sector.objects.create(service=self.service, name="Secteur audit occurrence")
        self.installation_critique = Installation.objects.create(
            designation="Groupe électrogène critique audit",
            ship=self.ship, service=self.service, sector=self.sector,
            critique=True,
        )
        self.installation_normale = Installation.objects.create(
            designation="Groupe électrogène standard audit",
            ship=self.ship, service=self.service, sector=self.sector,
            critique=False,
        )
        self.tech = User.objects.create_user(username="tech_audit_occ", password="MotDePasseCorrect1")
        self.client.login(username="tech_audit_occ", password="MotDePasseCorrect1")

    def _creer_occurrence(self, installation):
        maintenance = InstallationMaintenance.objects.create(
            installation=installation,
            periodicity="1 mois",
            title="Contrôle général",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)
        return occ

    def test_execution_sur_installation_normale_alimente_historique_et_audit(self):
        occ = self._creer_occurrence(self.installation_normale)
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME"})

        # Historique structuré propre à l'occurrence (jusqu'ici jamais rempli).
        historique = OccurrenceStatusLog.objects.get(occurrence=occ)
        self.assertEqual(historique.old_status, "ASSIGNED")
        self.assertEqual(historique.new_status, "DONE")
        self.assertEqual(historique.user, self.tech)

        # Journal transverse : acteur, action, horodatage, contexte.
        entree = AuditLog.objects.get(action="occurrence_status_change")
        self.assertEqual(entree.actor, self.tech)
        self.assertIsNotNone(entree.created_at)
        self.assertIn(str(occ.pk), entree.details)
        self.assertIn("ASSIGNED -> DONE", entree.details)

    def test_execution_sur_installation_critique_distingue_la_validation(self):
        # Geste engageant (signature de validation par mot de passe) :
        # identifiable séparément dans le journal, même logique que la
        # remise en service d'un ticket correctif.
        occ = self._creer_occurrence(self.installation_critique)
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME", "mot_de_passe": "MotDePasseCorrect1"})

        entree = AuditLog.objects.get(action="occurrence_validation_critique")
        self.assertEqual(entree.actor, self.tech)
        self.assertIn(str(occ.pk), entree.details)
        self.assertFalse(AuditLog.objects.filter(action="occurrence_status_change").exists())

    def test_mot_de_passe_incorrect_ne_genere_aucune_entree(self):
        occ = self._creer_occurrence(self.installation_critique)
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME", "mot_de_passe": "faux-mot-de-passe"})
        self.assertFalse(OccurrenceStatusLog.objects.filter(occurrence=occ).exists())
        self.assertFalse(AuditLog.objects.filter(action__startswith="occurrence_").exists())
