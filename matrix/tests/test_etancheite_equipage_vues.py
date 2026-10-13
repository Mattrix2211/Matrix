"""Double équipage : l'étanchéité s'applique aussi au rendu des vues, pas seulement aux filtres.
Règle : seul l'équipage à terre non commandement est borné ; l'équipage à bord et le commandement lisent tout."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from assets.models import Installation, InstallationMaintenance
from dashboard.aujourdhui_terre import cartes_batiments
from dashboard.web_views import _disponibilite_par_navire
from logistics.models import PartLineItem, PartRequest
from maintenance.models import MaintenanceOccurrence
from org.models import ResponsableClasseNavire
from quarts.tests.test_double_equipage import marin
from reports.services import construire_contexte_periode
from .test_etancheite_equipage_peripherie import PeripherieEquipageBase


class VuesEquipageBase(PeripherieEquipageBase):
    """Complète le décor : un chef de secteur à bord et une installation critique avec une échéance en retard par équipage."""

    def setUp(self):
        super().setUp()
        self.chef_bleu = marin("chef_bleu", "CHEF_SECTEUR", self.ship, self.bleu, self.secteur_bleu)
        self.installation = Installation.objects.create(
            designation="Groupe", ship=self.ship, service=self.service_bleu, sector=self.secteur_bleu, critique=True)
        fiche = InstallationMaintenance.objects.create(installation=self.installation, periodicity="3 mois", title="Vidange")
        self.oi_bleu, self.oi_rouge = (
            MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=self.jour, status="OVERDUE")
            for _ in range(2)
        )
        self.oi_bleu.assignees.add(self.a_bleu)
        self.oi_rouge.assignees.add(self.a_rouge)

    def _connecte(self, user):
        self.client.force_login(user)
        return self.client


class VueFlotteEquipageTests(VuesEquipageBase):
    def _contexte(self, user):
        return self._connecte(user).get(reverse("vue-flotte")).context

    def test_chef_a_terre_borne_a_son_equipage(self):
        contexte = self._contexte(self.chef_rouge)
        self.assertEqual(contexte["maintenances_en_retard"], 2)
        self.assertEqual(contexte["total_tickets_ouverts"], 1)

    def test_bord_et_commandement_lisent_tout(self):
        for user in (self.chef_bleu, self.cdt_rouge):
            with self.subTest(user=user.username):
                contexte = self._contexte(user)
                self.assertEqual(contexte["maintenances_en_retard"], 4)
                self.assertEqual(contexte["total_tickets_ouverts"], 2)


class DashboardClasseNavireEquipageTests(VuesEquipageBase):
    def _contexte(self, user):
        ResponsableClasseNavire.objects.create(classe_navire="FREMM", user=user)
        return self._connecte(user).get(reverse("dashboard-classe-navire", args=["FREMM"])).context

    def test_responsable_a_terre_borne_a_son_equipage(self):
        contexte = self._contexte(self.chef_rouge)
        self.assertEqual(contexte["maintenances_en_retard"], 2)
        self.assertEqual(contexte["total_tickets_ouverts"], 1)
        self.assertEqual(contexte["comparatif_navires"][0]["maintenances_en_retard"], 2)

    def test_responsable_a_bord_lit_tout(self):
        contexte = self._contexte(self.chef_bleu)
        self.assertEqual(contexte["maintenances_en_retard"], 4)
        self.assertEqual(contexte["total_tickets_ouverts"], 2)

    def test_installations_critiques_du_comparatif(self):
        # Sans l'échéance en retard du Bleu, l'installation critique n'est plus « hors service » pour l'équipage à terre.
        self.oi_rouge.status = "PLANNED"
        self.oi_rouge.save()
        self.assertEqual(_disponibilite_par_navire([self.ship], self.chef_rouge)[0]["installations_critiques_hors_service"], 0)
        self.assertEqual(_disponibilite_par_navire([self.ship], self.chef_bleu)[0]["installations_critiques_hors_service"], 1)


class CalendrierPageEquipageTests(VuesEquipageBase):
    def _evenements(self, user):
        reponse = self._connecte(user).get(reverse("calendar-index"), {"view": "day", "date": self.jour.isoformat()})
        types = [e["type"] for e in reponse.context["events"]]
        return types.count("maintenance"), types.count("ticket")

    def test_page_html_bornee_par_equipage(self):
        self.assertEqual(self._evenements(self.a_rouge), (2, 1))
        self.assertEqual(self._evenements(self.a_bleu), (4, 2))
        self.assertEqual(self._evenements(self.cdt_rouge), (4, 2))


class GraphiqueSemainePreventifEquipageTests(VuesEquipageBase):
    def _planifie(self, user):
        donnees = self._connecte(user).get("/api/dashboard/preventive_week/").json()
        return sum(donnees["datasets"][0]["data"])

    def test_preventif_de_la_semaine_borne(self):
        self.assertEqual(self._planifie(self.a_rouge), 2)
        self.assertEqual(self._planifie(self.a_bleu), 4)
        self.assertEqual(self._planifie(self.cdt_rouge), 4)


class CartesBatimentsRetardsEquipageTests(VuesEquipageBase):
    def _badge_retard(self, user):
        badges = cartes_batiments([self.ship], self.jour, user)[0]["badges"]
        return next((b["libelle"] for b in badges if "en retard" in b["libelle"]), None)

    def test_retards_comptes_selon_l_equipage(self):
        # Les occurrences OVERDUE sont bien comptées : 4 au total, 2 pour l'équipage à terre.
        self.assertEqual(self._badge_retard(self.chef_rouge), "2 en retard")
        self.assertEqual(self._badge_retard(self.cdt_rouge), "4 en retard")
        self.assertEqual(self._badge_retard(self.chef_bleu), "4 en retard")


class BilanPeriodeEquipageTests(VuesEquipageBase):
    def setUp(self):
        super().setUp()
        aujourdhui = timezone.localdate()
        for ticket in (self.t_bleu, self.t_rouge):
            demande = PartRequest.objects.create(ticket=ticket)
            PartLineItem.objects.create(
                part_request=demande, reference=f"REF-{ticket.pk}", description="pièce", qty=1,
                status="CONSUMED", received_at=aujourdhui,
            )
        self.fenetre = (aujourdhui, aujourdhui + timedelta(days=2))

    def _contexte(self, user):
        return construire_contexte_periode("sector", self.secteur_bleu.id, user, *self.fenetre)

    def test_equipage_a_terre_ne_lit_pas_l_autre_equipage(self):
        contexte = self._contexte(self.chef_rouge)
        self.assertEqual(contexte["nb_maintenances_planifiees"], 1)
        self.assertEqual({t.pk for t in contexte["tickets_ouverts_periode"]}, {self.t_rouge.pk})
        self.assertEqual({t.pk for t in contexte["tickets_encore_ouverts_fin_periode"]}, {self.t_rouge.pk})
        self.assertEqual([p.part_request.ticket_id for p in contexte["pieces_consommees"]], [self.t_rouge.pk])

    def test_bord_lit_tout(self):
        contexte = self._contexte(self.chef_bleu)
        self.assertEqual(contexte["nb_maintenances_planifiees"], 2)
        self.assertEqual({t.pk for t in contexte["tickets_ouverts_periode"]}, {self.t_bleu.pk, self.t_rouge.pk})
        self.assertEqual(len(contexte["pieces_consommees"]), 2)
