"""Déplacement d'événements du calendrier : même bornage par service que les fiches et l'API.

Règle : un commandant adjoint ne replanifie que les occurrences et tickets des services rattachés à sa fonction ;
chef de service et de secteur, dans leur périmètre ; refus 403 pour une action interdite sur un objet visible,
404 pour un objet absent ou hors périmètre ; l'assigné garde la main sur sa propre occurrence."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from matrix.tests.test_ecriture_commandants_adjoints import BaseDroitsEcriture


class DeplacementCalendrierParServiceTests(BaseDroitsEcriture):
    def setUp(self):
        super().setUp()
        self.aujourdhui = timezone.localdate()
        self.cible = self.aujourdhui + timedelta(days=9)
        self.occurrences = {}
        for nom in self.services:
            plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.assets[nom], name=f"Plan {nom}", every_n_days=30)
            self.occurrences[nom] = MaintenanceOccurrence.objects.create(
                plan=plan, asset=self.assets[nom], scheduled_for=self.aujourdhui, status="PLANNED")
            CorrectiveTicket.objects.filter(pk=self.tickets[nom].pk).update(planned_for=self.aujourdhui)

    def _reinitialiser(self):
        MaintenanceOccurrence.objects.update(scheduled_for=self.aujourdhui)
        CorrectiveTicket.objects.update(planned_for=self.aujourdhui)

    def _deplacer(self, qui, type_evenement, objet):
        pk = objet.pk
        return self._post(qui, reverse("calendar-event-move"), {"type": type_evenement, "id": pk, "date": self.cible.isoformat()})

    def _a_bouge(self, type_evenement, nom):
        if type_evenement == "maintenance":
            return MaintenanceOccurrence.objects.get(pk=self.occurrences[nom].pk).scheduled_for == self.cible
        return CorrectiveTicket.objects.get(pk=self.tickets[nom].pk).planned_for == self.cible

    def _objet(self, type_evenement, nom):
        return self.occurrences[nom] if type_evenement == "maintenance" else self.tickets[nom]

    def test_chaque_commandant_adjoint_deplace_ses_services_seulement(self):
        for type_evenement in ("maintenance", "ticket"):
            for qui, propre, autres in (("comanav_a", "Navigation", ("Operations", "Vie a bord")),
                                        ("comops_a", "Operations", ("Navigation", "Vie a bord")),
                                        ("comaeq_a", "Vie a bord", ("Navigation", "Operations"))):
                self._reinitialiser()
                reponse = self._deplacer(qui, type_evenement, self._objet(type_evenement, propre))
                self.assertEqual(reponse.status_code, 200, f"{qui} {type_evenement} {propre}")
                self.assertTrue(self._a_bouge(type_evenement, propre))
                for autre in autres:
                    reponse = self._deplacer(qui, type_evenement, self._objet(type_evenement, autre))
                    self.assertEqual(reponse.status_code, 403, f"{qui} {type_evenement} {autre}")
                    self.assertFalse(self._a_bouge(type_evenement, autre), f"{qui} ne replanifie pas {autre}")

    def test_etat_major_sans_fonction_ne_replanifie_rien(self):
        for type_evenement in ("maintenance", "ticket"):
            for nom in self.services:
                reponse = self._deplacer("etat_major_sans_fonction", type_evenement, self._objet(type_evenement, nom))
                self.assertEqual(reponse.status_code, 403, f"{type_evenement} {nom}")
                self.assertFalse(self._a_bouge(type_evenement, nom))

    def test_chef_de_service_et_de_secteur_dans_leur_perimetre_seulement(self):
        for qui in ("chef_service_nav", "chef_secteur_nav"):
            for type_evenement in ("maintenance", "ticket"):
                self.assertEqual(self._deplacer(qui, type_evenement, self._objet(type_evenement, "Navigation")).status_code, 200, f"{qui} {type_evenement}")
                self.assertTrue(self._a_bouge(type_evenement, "Navigation"))
                reponse = self._deplacer(qui, type_evenement, self._objet(type_evenement, "Operations"))
                self.assertEqual(reponse.status_code, 404, f"{qui} {type_evenement} hors périmètre")
                self.assertFalse(self._a_bouge(type_evenement, "Operations"))

    def test_le_commandant_replanifie_tout_le_batiment(self):
        for type_evenement in ("maintenance", "ticket"):
            for nom in self.services:
                self.assertEqual(self._deplacer("commandant", type_evenement, self._objet(type_evenement, nom)).status_code, 200)
                self.assertTrue(self._a_bouge(type_evenement, nom))

    def test_equipage_b_a_terre_ne_replanifie_rien_meme_dans_son_service(self):
        for type_evenement in ("maintenance", "ticket"):
            reponse = self._deplacer("comaeq_b", type_evenement, self._objet(type_evenement, "Vie a bord"))
            self.assertEqual(reponse.status_code, 403)
            self.assertFalse(self._a_bouge(type_evenement, "Vie a bord"))

    def test_l_assigne_garde_la_main_sur_sa_propre_occurrence(self):
        occurrence = self.occurrences["Operations"]
        occurrence.assignees.add(self.profils["comanav_a"])  # exception métier : l'assigné replanifie sa propre occurrence
        reponse = self._deplacer("comanav_a", "maintenance", occurrence)
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(self._a_bouge("maintenance", "Operations"))

    def test_objet_absent_donne_une_404(self):
        self.client.force_login(self.profils["comanav_a"])
        for type_evenement in ("maintenance", "ticket"):
            reponse = self.client.post(reverse("calendar-event-move"), {"type": type_evenement, "id": "00000000-0000-0000-0000-000000000000" if type_evenement == "ticket" else 999999, "date": self.cible.isoformat()})
            self.assertEqual(reponse.status_code, 404, type_evenement)

    def test_le_calendrier_n_affiche_comme_deplacable_que_ce_qui_l_est(self):
        self.client.force_login(self.profils["comanav_a"])
        reponse = self.client.get(reverse("calendar-events"), {"start": self.aujourdhui.isoformat(), "end": (self.aujourdhui + timedelta(days=1)).isoformat()})
        self.assertEqual(reponse.status_code, 200)
        evenements = reponse.json()
        par_id = {e["id"]: e for e in evenements}
        propre_occ, autre_occ = f"occ-{self.occurrences['Navigation'].pk}", f"occ-{self.occurrences['Operations'].pk}"
        propre_tic, autre_tic = f"tic-{self.tickets['Navigation'].pk}", f"tic-{self.tickets['Operations'].pk}"
        self.assertTrue(par_id[propre_occ]["editable"] and par_id[propre_tic]["editable"])
        self.assertFalse(par_id[autre_occ]["editable"] or par_id[autre_tic]["editable"])
        self.assertFalse(par_id[autre_occ]["extendedProps"]["peut_agir"] or par_id[autre_tic]["extendedProps"]["peut_agir"])
