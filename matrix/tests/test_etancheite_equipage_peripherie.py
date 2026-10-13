"""Double équipage : les chemins périphériques (calendrier, tableaux de bord, bilans, fiche matériel,
demandes de pièces) appliquent la même étanchéité que les listes de tickets, d'occurrences et de rondes."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from assets.models import Asset, AssetType
from dashboard.aujourdhui import supervision
from dashboard.aujourdhui_terre import a_faire_terre, cartes_batiments
from dashboard.web_views import _agrege_technique_marins, _disponibilite_par_navire
from logistics.models import CorrectiveTicket, PartLineItem, PartRequest
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from quarts.tests.test_double_equipage import DoubleEquipageBase, marin
from reports.services import construire_contexte_instantane
from .test_etancheite_equipage import _ids


class PeripherieEquipageBase(DoubleEquipageBase):
    def setUp(self):
        super().setUp()
        self.chef_rouge = marin("chef_rouge", "CHEF_SECTEUR", self.ship, self.rouge, self.secteur_rouge)
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=self.secteur_bleu)
        self.asset = Asset.objects.create(
            asset_type=type_asset, internal_id="P-1", designation="Pompe", ship=self.ship,
            service=self.service_bleu, sector=self.secteur_bleu,
        )
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan")
        self.jour = timezone.localdate() + timedelta(days=1)
        self.t_bleu, self.t_rouge = (
            CorrectiveTicket.objects.create(asset=self.asset, description=d, planned_for=self.jour) for d in ("bleu", "rouge")
        )
        self.t_bleu.assignees.add(self.a_bleu)
        self.t_rouge.assignees.add(self.a_rouge)
        self.o_bleu, self.o_rouge = (
            MaintenanceOccurrence.objects.create(plan=plan, asset=self.asset, scheduled_for=self.jour, status=statut)
            for statut in ("OVERDUE", "OVERDUE")
        )
        self.o_bleu.assignees.add(self.a_bleu)
        self.o_rouge.assignees.add(self.a_rouge)


class CalendrierEquipageTests(PeripherieEquipageBase):
    def _evenements(self, user):
        self.client.force_login(user)
        reponse = self.client.get(reverse("calendar-events"), {"start": self.jour.isoformat(), "end": self.jour.isoformat()})
        return {e["id"] for e in reponse.json()}

    def test_evenements_bornes_par_equipage(self):
        self.assertEqual(self._evenements(self.a_rouge), {f"occ-{self.o_rouge.pk}", f"tic-{self.t_rouge.pk}"})
        self.assertEqual(len(self._evenements(self.a_bleu)), 4)
        self.assertEqual(len(self._evenements(self.cdt_rouge)), 4)


class TableauxDeBordEquipageTests(PeripherieEquipageBase):
    def test_supervision_borne(self):
        self.assertEqual(supervision(self.chef_rouge, self.jour)["retards_total"], 1)

    def test_specialite_bornee(self):
        marins = [self.a_bleu.pk, self.a_rouge.pk]
        self.assertEqual(_agrege_technique_marins(marins, self.chef_rouge)["technique_maintenances_en_retard"], 1)
        self.assertEqual(_agrege_technique_marins(marins, self.a_bleu)["technique_maintenances_en_retard"], 2)

    def test_comparatif_classe_borne(self):
        self.assertEqual(_disponibilite_par_navire([self.ship], self.chef_rouge)[0]["maintenances_en_retard_pct"], 100)
        self.o_bleu.status = "PLANNED"
        self.o_bleu.save()
        self.assertEqual(_disponibilite_par_navire([self.ship], self.chef_rouge)[0]["maintenances_en_retard_pct"], 100)
        self.assertEqual(_disponibilite_par_navire([self.ship], self.a_bleu)[0]["maintenances_en_retard_pct"], 50)

    def test_vue_terre(self):
        self.o_bleu.status = self.o_rouge.status = "WAITING_VALIDATION"
        self.o_bleu.save()
        self.o_rouge.save()
        self.t_bleu.status = self.t_rouge.status = "BLOCKED"
        self.t_bleu.save()
        self.t_rouge.save()
        self.assertEqual(len(a_faire_terre([self.ship], self.chef_rouge)), 2)
        self.assertEqual(len(a_faire_terre([self.ship], self.cdt_rouge)), 4)
        badges = cartes_batiments([self.ship], self.jour, self.chef_rouge)[0]["badges"]
        self.assertEqual([b["libelle"] for b in badges], ["1 ticket(s) bloqué(s)"])

    def test_graphiques_api(self):
        self.client.force_login(self.a_rouge)
        donnees = self.client.get("/api/dashboard/corrective_open/").json()
        self.assertEqual(sum(donnees["datasets"][0]["data"]), 1)
        self.client.force_login(self.a_bleu)
        donnees = self.client.get("/api/dashboard/corrective_open/").json()
        self.assertEqual(sum(donnees["datasets"][0]["data"]), 2)


class BilansEtMaterielEquipageTests(PeripherieEquipageBase):
    def test_bilan_instantane_sans_ticket_de_l_autre_equipage(self):
        contexte = construire_contexte_instantane("sector", self.secteur_rouge.id, self.chef_rouge)
        self.assertEqual({t.pk for t in contexte["tickets_ouverts"]}, {self.t_rouge.pk})

    def test_fiche_materiel(self):
        self.t_bleu.status = "CLOSED"
        self.t_bleu.diagnostic_final = "joint"
        self.t_bleu.save()
        self.client.force_login(self.a_rouge)
        contexte = self.client.get(reverse("asset-detail", args=[self.asset.pk])).context
        self.assertEqual(list(contexte["pannes_deja_rencontrees"]), [])
        indicateurs = {i["libelle"]: i["valeur"] for i in contexte["indicateurs_fiche"]}
        self.assertEqual(indicateurs["Maintenances en retard"], 1)
        self.assertEqual(indicateurs["Tickets ouverts"], 1)
        self.client.force_login(self.a_bleu)
        contexte = self.client.get(reverse("asset-detail", args=[self.asset.pk])).context
        self.assertEqual(len(contexte["pannes_deja_rencontrees"]), 1)


class DemandesDePiecesEquipageTests(PeripherieEquipageBase):
    def setUp(self):
        super().setUp()
        self.demande_bleu = PartRequest.objects.create(ticket=self.t_bleu)
        self.demande_rouge = PartRequest.objects.create(ticket=self.t_rouge)
        self.ligne_bleu = PartLineItem.objects.create(part_request=self.demande_bleu, reference="X", description="x", qty=1)
        self.ligne_rouge = PartLineItem.objects.create(part_request=self.demande_rouge, reference="Y", description="y", qty=1)

    def test_api(self):
        api = APIClient()
        api.force_login(self.chef_rouge)
        self.assertEqual(_ids(api.get("/api/logistics/part-requests/")), {str(self.demande_rouge.pk)})
        self.assertEqual(_ids(api.get("/api/logistics/part-lines/")), {str(self.ligne_rouge.pk)})
        api.force_login(self.a_bleu)
        self.assertEqual(len(_ids(api.get("/api/logistics/part-requests/"))), 2)
