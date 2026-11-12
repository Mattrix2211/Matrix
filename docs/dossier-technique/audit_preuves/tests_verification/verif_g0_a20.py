"""VÉRIFICATION TEMPORAIRE G0 / A20 — copie isolée de l'état B ; données fictives ; non conservée dans le dépôt."""
from datetime import timedelta
import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Roles, UserProfile
from assets.models import Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate, Installation, InstallationMaintenance, ModeDeclenchement
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from maintenance.perimetre import retard_q
from maintenance.tasks import compute_overdue
from notifications.models import Notification
from notifications import tasks as ntasks
from org.models import Sector, Service, Ship


class A20(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="N A20", code="A20")
        self.service = Service.objects.create(ship=self.ship, name="S")
        self.sector = Sector.objects.create(service=self.service, name="Sec")
        def u(nom, role, **kw):
            x = User.objects.create_user(username=nom, password="pw")
            UserProfile.objects.update_or_create(user=x, defaults={"ship": self.ship, "role": role, "sector": self.sector, "service": self.service, **kw})
            return x
        self.marin = u("marin", Roles.EQUIPIER)
        self.chef_section = u("chef_section", Roles.CHEF_SECTION)
        self.chef_secteur = u("chef_secteur", Roles.CHEF_SECTEUR)
        self.chef_service = u("chef_service", Roles.CHEF_SERVICE)
        t = AssetType.objects.create(name="Ext", category="Inc", sector=self.sector)
        self.asset = Asset.objects.create(asset_type=t, ship=self.ship, service=self.service, sector=self.sector)
        modele = ChecklistTemplate.objects.create(name="G", sector=self.sector)
        self.it = ChecklistItemTemplate.objects.create(template=modele, label="Goupille", field_type="checkbox", order=1)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="C", every_n_days=30, checklist_template=modele)
        self.occ = MaintenanceOccurrence.objects.create(plan=plan, asset=self.asset, scheduled_for=timezone.localdate() - timedelta(days=10), status="ASSIGNED")
        self.occ.assignees.add(self.marin)
        self.url = reverse("occurrence-execute", args=[self.occ.pk])

    def poster(self, user, **extra):
        self.client.logout(); self.client.login(username=user, password="pw")
        d = {f"item_{self.it.pk}": "conforme", "conformity": "CONFORME"}; d.update(extra)
        return self.client.post(self.url, d)

    def statut(self):
        self.occ.refresh_from_db(); return self.occ.status

    def non_conforme(self):
        self.poster("marin", **{"conformity": "NON_CONFORME", f"item_{self.it.pk}": "non_conforme"})
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    # ----- entrée -----
    def test_entree_par_verdict_non_conforme_et_ticket_auto(self):
        self.non_conforme()
        self.assertEqual(CorrectiveTicket.objects.filter(asset=self.asset).count(), 1)

    # ----- sorties par le web -----
    def test_marin_ne_peut_pas_corriger(self):
        self.non_conforme()
        self.poster("marin", motif="x")
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    def test_chef_de_section_ne_peut_pas_corriger(self):
        self.non_conforme()
        r = self.poster("chef_section", motif="x")
        self.assertEqual(self.statut(), "WAITING_VALIDATION", r.status_code)

    def test_chef_de_secteur_corrige_en_conforme_sort(self):
        self.non_conforme()
        self.poster("chef_secteur", motif="Défaut levé")
        self.assertEqual(self.statut(), "DONE")

    def test_chef_de_secteur_corrige_sans_motif_refuse(self):
        self.non_conforme()
        self.poster("chef_secteur")
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    def test_chef_de_secteur_reste_non_conforme_ne_sort_pas(self):
        self.non_conforme()
        self.poster("chef_secteur", motif="Toujours", **{"conformity": "NON_CONFORME", f"item_{self.it.pk}": "non_conforme"})
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    def test_enregistrer_en_direct_refuse_sur_compte_rendu_termine(self):
        self.non_conforme()
        self.poster("chef_secteur", action="enregistrer")
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    # ----- sorties par l'API -----
    def api(self, user, action, data=None):
        self.client.logout(); self.client.login(username=user, password="pw")
        return self.client.post(f"/api/maintenance/occurrences/{self.occ.pk}/{action}/", data or {}, content_type="application/json")

    def test_api_complete_refuse_apres_compte_rendu(self):
        self.non_conforme()
        r = self.api("chef_secteur", "complete", {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    def test_api_start_depuis_en_validation(self):
        """Constat : `start` écrit IN_PROGRESS sans contrôler l'état de départ."""
        self.non_conforme()
        r = self.api("chef_secteur", "start")
        print("\nAPI start depuis WAITING_VALIDATION ->", r.status_code, self.statut())

    def test_api_patch_statut_refuse(self):
        self.non_conforme()
        self.client.logout(); self.client.login(username="chef_service", password="pw")
        r = self.client.patch(f"/api/maintenance/occurrences/{self.occ.pk}/", {"status": "DONE"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    # ----- assignation, annulation, planification -----
    def test_assignation_ne_change_pas_le_statut(self):
        self.non_conforme()
        self.client.logout(); self.client.login(username="chef_section", password="pw")
        self.client.post(reverse("occurrence-self-assign", args=[self.occ.pk]))
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    def test_compute_overdue_ne_touche_pas(self):
        self.non_conforme()
        compute_overdue()
        self.assertEqual(self.statut(), "WAITING_VALIDATION")
        self.assertFalse(MaintenanceOccurrence.objects.filter(retard_q(timezone.localdate()), pk=self.occ.pk).exists())

    def test_notification_retard_ne_la_vise_pas(self):
        self.non_conforme()
        Notification.objects.all().delete()
        ntasks.notify_overdue_occurrences()
        self.assertFalse(Notification.objects.filter(object_id=str(self.occ.pk)).exists())

    # ----- ticket correctif -----
    def test_cloture_du_ticket_ne_change_pas_l_occurrence(self):
        self.non_conforme()
        ticket = CorrectiveTicket.objects.get(asset=self.asset)
        self.client.logout(); self.client.login(username="chef_secteur", password="pw")
        for statut in ("DIAGNOSED", "IN_REPAIR", "TESTING", "RETURNED_TO_SERVICE", "CLOSED"):
            self.client.post(reverse("ticket-transition", args=[ticket.pk]),
                             {"status": statut, "confirmation": "1", "diagnostic_final": "ok", "solution": "ok"})
        ticket.refresh_from_db()
        print("\nticket après transitions ->", ticket.status)
        self.assertEqual(ticket.status, "CLOSED")
        self.assertEqual(self.statut(), "WAITING_VALIDATION")

    # ----- installation : blocage de la génération suivante -----
    def test_installation_en_validation_bloque_la_generation_suivante(self):
        inst = Installation.objects.create(designation="Groupe", ship=self.ship, service=self.service, sector=self.sector)
        m = InstallationMaintenance.objects.create(installation=inst, periodicity="1 mois", title="Ctl", mode_declenchement=ModeDeclenchement.CALENDRIER, intervalle=1, unite_intervalle="M")
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=m, scheduled_for=timezone.localdate() - timedelta(days=40), status="ASSIGNED")
        occ.assignees.add(self.marin)
        self.client.logout(); self.client.login(username="marin", password="pw")
        self.client.post(reverse("occurrence-execute", args=[occ.pk]), {"conformity": "NON_CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "WAITING_VALIDATION")
        avant = MaintenanceOccurrence.objects.filter(installation_maintenance=m).count()
        call_command("generate_installation_occurrences")
        apres = MaintenanceOccurrence.objects.filter(installation_maintenance=m).count()
        print("\ninstallation : occurrences avant/après génération (en validation) ->", avant, apres)
        self.assertEqual(avant, apres)
        self.assertFalse(CorrectiveTicket.objects.filter(installation=inst).exists())
        # après correction en conforme par le chef : la génération reprend
        self.client.logout(); self.client.login(username="chef_secteur", password="pw")
        self.client.post(reverse("occurrence-execute", args=[occ.pk]), {"conformity": "CONFORME", "motif": "ok"})
        occ.refresh_from_db()
        call_command("generate_installation_occurrences")
        print("installation : statut après correction", occ.status, "; occurrences ->", MaintenanceOccurrence.objects.filter(installation_maintenance=m).count())

    def test_api_start_par_chacun_et_etat_incoherent(self):
        self.non_conforme()
        for qui in ("marin", "chef_section", "chef_secteur"):
            self.occ.status = "WAITING_VALIDATION"; self.occ.save()
            r = self.api(qui, "start")
            print(f"\nstart par {qui} -> HTTP {r.status_code}, statut {self.statut()}")
        # état incohérent : en cours alors que le compte rendu est terminé
        ex = MaintenanceExecution.objects.get(occurrence=self.occ)
        print("compte rendu terminé (completed_at) :", ex.completed_at is not None, "; conformité :", ex.conformity)
        self.assertTrue(MaintenanceOccurrence.objects.filter(retard_q(timezone.localdate()), pk=self.occ.pk).exists())
        # la correction par un chef de secteur remet un état cohérent
        self.poster("chef_secteur", motif="Reprise")
        print("après correction CONFORME par chef de secteur ->", self.statut())

    def test_admin_django_peut_ecrire_le_statut(self):
        self.non_conforme()
        su = User.objects.create_superuser("root", "r@x.fr", "pw")
        self.client.logout(); self.client.login(username="root", password="pw")
        r = self.client.post(f"/admin/maintenance/maintenanceoccurrence/{self.occ.pk}/change/", {
            "plan": self.occ.plan_id, "asset": self.asset.pk, "scheduled_for": self.occ.scheduled_for.isoformat(),
            "status": "CANCELLED", "priority": 3, "assignees": [self.marin.pk]})
        print("\nadmin POST ->", r.status_code, self.statut())

    def test_materiel_mobile_la_generation_continue(self):
        from maintenance.tasks import generate_occurrences
        self.non_conforme()
        avant = MaintenanceOccurrence.objects.filter(plan=self.occ.plan).count()
        generate_occurrences(90)
        apres = MaintenanceOccurrence.objects.filter(plan=self.occ.plan).count()
        print("\nmatériel mobile : occurrences avant/après génération ->", avant, apres)
