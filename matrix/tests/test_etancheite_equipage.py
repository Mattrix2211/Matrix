"""Double équipage : un marin ne lit que les tickets, occurrences et rondes de son équipage ;
un bâtiment à équipage unique garde son comportement."""
from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from maintenance.tournee import charger
from org.models import Sector, Service, Ship
from logistics.perimetre import perimetre_tickets_q
from quarts.tests.test_double_equipage import DoubleEquipageBase, marin
from matrix.core import recherche
from rondes.models import Ronde
from threads.models import Message
from threads.utils import ajouter_commentaire
from rondes.services import rondes_visibles

User = get_user_model()


def _ids(reponse):
    donnees = reponse.json()
    return {str(o["id"]) for o in (donnees["results"] if isinstance(donnees, dict) else donnees)}


class EtancheiteParEquipageTests(DoubleEquipageBase):
    def setUp(self):
        super().setUp()
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=self.secteur_bleu)
        self.asset = Asset.objects.create(
            asset_type=type_asset, internal_id="P-1", designation="Pompe", ship=self.ship,
            service=self.service_bleu, sector=self.secteur_bleu,
        )
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan")
        self.t_bleu, self.t_rouge, self.t_libre = (
            CorrectiveTicket.objects.create(asset=self.asset, description=d) for d in ("bleu", "rouge", "libre")
        )
        self.t_bleu.assignees.add(self.a_bleu)
        self.t_rouge.assignees.add(self.a_rouge)
        self.o_bleu, self.o_rouge, self.o_libre = (
            MaintenanceOccurrence.objects.create(plan=plan, asset=self.asset, scheduled_for=date(2030, 1, j), status="PLANNED")
            for j in (1, 2, 3)
        )
        self.o_bleu.assignees.add(self.a_bleu)
        self.o_rouge.assignees.add(self.a_rouge)
        self.r_bleu, self.r_rouge, self.r_libre = (
            Ronde.objects.create(nom=n, ship=self.ship, sector=self.secteur_bleu, date_prevue=date(2030, 1, 1), assigne_a=a)
            for n, a in (("bleu", self.a_bleu), ("rouge", self.a_rouge), ("libre", None))
        )

    def _api(self, user, url):
        client = APIClient()
        client.force_login(user)
        return client.get(url)

    def test_tickets_api_et_web(self):
        self.assertEqual(_ids(self._api(self.a_bleu, "/api/logistics/tickets/")), {str(self.t_bleu.pk), str(self.t_libre.pk)})
        self.assertEqual(_ids(self._api(self.a_rouge, "/api/logistics/tickets/")), {str(self.t_rouge.pk), str(self.t_libre.pk)})
        self.client.force_login(self.a_bleu)
        self.assertEqual(self.client.get("/logistics/tickets/").status_code, 200)
        self.assertEqual(self.client.get(f"/logistics/tickets/{self.t_rouge.pk}/").status_code, 400)

    def test_occurrences_api(self):
        attendu = {str(self.o_bleu.pk), str(self.o_libre.pk)}
        self.assertEqual(_ids(self._api(self.a_bleu, "/api/maintenance/occurrences/")), attendu)

    def test_rondes_visibles(self):
        self.assertEqual(set(rondes_visibles(self.a_bleu)), {self.r_bleu, self.r_libre})
        self.assertEqual(set(rondes_visibles(self.a_rouge)), {self.r_rouge, self.r_libre})
        self.client.force_login(self.a_bleu)
        self.assertEqual(self.client.get(f"/rondes/{self.r_rouge.pk}/").status_code, 404)

    def test_equipage_a_terre_garde_la_lecture_de_son_equipage(self):
        self.assertIn(str(self.t_rouge.pk), _ids(self._api(self.a_rouge, "/api/logistics/tickets/")))

    def test_objet_multi_assigne_visible_une_seule_fois(self):
        self.t_bleu.assignees.add(self.a_rouge, self.b_bleu)
        self.o_bleu.assignees.add(self.a_rouge, self.b_bleu)
        ids = _ids(self._api(self.a_rouge, "/api/logistics/tickets/"))
        self.assertIn(str(self.t_bleu.pk), ids)
        qs = CorrectiveTicket.objects.filter(perimetre_tickets_q(self.a_rouge))
        self.assertEqual(qs.filter(pk=self.t_bleu.pk).count(), 1)
        self.assertEqual(qs.count(), len(set(qs.values_list("pk", flat=True))))
        self.client.force_login(self.a_rouge)
        reponse = self.client.post(reverse("occurrence-comment-create", args=[self.o_bleu.pk]), {"body": "ok"})
        self.assertNotEqual(reponse.status_code, 500)
        occurrences = _ids(self._api(self.a_rouge, "/api/maintenance/occurrences/"))
        self.assertEqual(occurrences, {str(self.o_bleu.pk), str(self.o_rouge.pk), str(self.o_libre.pk)})

    def test_assigne_sans_equipage_reste_visible(self):
        neutre = marin("neutre", "EQUIPIER", self.ship, "", self.secteur_bleu)
        self.t_libre.assignees.add(neutre)
        self.assertIn(str(self.t_libre.pk), _ids(self._api(self.a_bleu, "/api/logistics/tickets/")))
        self.assertIn(str(self.t_libre.pk), _ids(self._api(self.a_rouge, "/api/logistics/tickets/")))

    def test_discussions_recherche_executions_et_tournee(self):
        ajouter_commentaire(self.o_rouge, self.a_rouge, "secret rouge")
        ajouter_commentaire(self.o_bleu, self.a_bleu, "propre bleu")
        donnees = self._api(self.a_bleu, "/api/threads/messages/").json()
        corps = {m["body"] for m in (donnees["results"] if isinstance(donnees, dict) else donnees)}
        self.assertEqual(corps, {"propre bleu"})
        self.assertEqual(Message.objects.count(), 2)
        self.t_rouge.description = "pompe fuyarde rouge"
        self.t_rouge.save()
        self.assertFalse(recherche.tickets(self.a_bleu, "fuyarde").exists())
        self.assertTrue(recherche.tickets(self.a_rouge, "fuyarde").exists())
        e_bleu = MaintenanceExecution.objects.create(occurrence=self.o_bleu)
        e_rouge = MaintenanceExecution.objects.create(occurrence=self.o_rouge)
        self.assertEqual(_ids(self._api(self.a_bleu, "/api/maintenance/executions/")), {str(e_bleu.pk)})
        self.assertNotIn(str(e_rouge.pk), _ids(self._api(self.a_bleu, "/api/maintenance/executions/")))
        ids = [self.o_bleu.pk, self.o_rouge.pk, self.o_libre.pk]
        self.assertEqual({o.pk for o in charger(self.a_bleu, ids)}, {self.o_bleu.pk, self.o_libre.pk})

    def test_equipage_unique_inchange(self):
        navire = Ship.objects.create(name="Unique", code="UQ")
        service = Service.objects.create(ship=navire, name="Pont")
        secteur = Sector.objects.create(service=service, name="Manœuvre")
        a, b = marin("uq_a", "EQUIPIER", navire, "", secteur), marin("uq_b", "EQUIPIER", navire, "", secteur)
        type_asset = AssetType.objects.create(name="Treuil", category="MCO", sector=secteur)
        asset = Asset.objects.create(asset_type=type_asset, internal_id="T-1", designation="Treuil", ship=navire, service=service, sector=secteur)
        ticket = CorrectiveTicket.objects.create(asset=asset, description="x")
        ticket.assignees.add(b)
        ronde = Ronde.objects.create(nom="r", ship=navire, sector=secteur, date_prevue=date(2030, 1, 1), assigne_a=b)
        self.assertEqual(_ids(self._api(a, "/api/logistics/tickets/")), {str(ticket.pk)})
        self.assertIn(ronde, rondes_visibles(a))
