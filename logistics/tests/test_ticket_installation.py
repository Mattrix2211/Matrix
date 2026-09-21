"""Tickets correctifs visant une installation fixe (et non un matériel mobile) :
périmètre, workflow (mot de passe à la remise en service, REX à la fermeture),
listes, rapports et tableaux de bord."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from dashboard.web_views import _agrege_maintenance_ticket_stock
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from reports.services import _q_perimetre_tickets, _nom_equipement_ticket, _type_equipement_ticket


class _JeuDeDonnees(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.installation = Installation.objects.create(
            designation="Propulseur", ship=self.ship, service=self.service, sector=self.sector, critique=True,
        )
        self.asset = Asset.objects.create(
            asset_type=AssetType.objects.create(name="T", category="C", sector=self.sector),
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.ticket = CorrectiveTicket.objects.create(
            installation=self.installation, description="Vibrations", status="TESTING",
        )
        self.ticket_materiel = CorrectiveTicket.objects.create(asset=self.asset, description="Panne")

        self.chef = User.objects.create_user(username="chef", password="Motdepasse1")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.sector)
        autre_ship = Ship.objects.create(name="Navire B", code="NB")
        self.etranger = User.objects.create_user(username="etranger", password="Motdepasse1")
        UserProfile.objects.filter(user=self.etranger).update(role="CHEF_SERVICE", ship=autre_ship)


class TicketInstallationTests(_JeuDeDonnees):
    def test_clean_exige_un_equipement_et_un_seul(self):
        with self.assertRaises(ValidationError):
            CorrectiveTicket(description="x").clean()
        with self.assertRaises(ValidationError):
            CorrectiveTicket(description="x", asset=self.asset, installation=self.installation).clean()
        CorrectiveTicket(description="x", installation=self.installation).clean()

    def test_equipement_et_ticket_existant_inchange(self):
        self.assertEqual(self.ticket.equipement, self.installation)
        self.assertEqual(self.ticket_materiel.equipement, self.asset)
        self.assertIsNone(self.ticket_materiel.installation)

    def test_fiche_et_liste_dans_le_perimetre(self):
        self.client.login(username="chef", password="Motdepasse1")
        fiche = self.client.get(reverse("ticket-detail", args=[self.ticket.pk]))
        self.assertContains(fiche, "Propulseur")
        self.assertContains(fiche, f"/installations/{self.installation.pk}/")
        liste = self.client.get(reverse("ticket-list") + "?vue=perimetre")
        self.assertEqual(set(liste.context["tickets"]), {self.ticket, self.ticket_materiel})
        self.assertContains(liste, "Propulseur")

    def test_hors_perimetre_introuvable(self):
        self.client.login(username="etranger", password="Motdepasse1")
        self.assertEqual(self.client.get(reverse("ticket-detail", args=[self.ticket.pk])).status_code, 400)
        self.client.post(reverse("ticket-transition", args=[self.ticket.pk]), {"status": "CANCELLED"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")

    def test_remise_en_service_exige_le_mot_de_passe(self):
        self.client.login(username="chef", password="Motdepasse1")
        url = reverse("ticket-transition", args=[self.ticket.pk])
        self.client.post(url, {"status": "RETURNED_TO_SERVICE", "mot_de_passe": "faux"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "TESTING")
        self.client.post(url, {"status": "RETURNED_TO_SERVICE", "mot_de_passe": "Motdepasse1"})
        self.ticket.refresh_from_db()
        self.assertEqual((self.ticket.status, self.ticket.valide_par), ("RETURNED_TO_SERVICE", self.chef))

    def test_fermeture_exige_le_rex(self):
        self.client.login(username="chef", password="Motdepasse1")
        url = reverse("ticket-transition", args=[self.ticket.pk])
        self.client.post(url, {"status": "CLOSED"})
        self.ticket.refresh_from_db()
        self.assertNotEqual(self.ticket.status, "CLOSED")
        self.client.post(url, {"status": "CLOSED", "diagnostic_final": "Roulement", "solution": "Remplacé"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "CLOSED")

    def test_assignation_limitee_a_l_equipage_du_navire(self):
        self.client.login(username="chef", password="Motdepasse1")
        self.client.post(reverse("ticket-assign", args=[self.ticket.pk]), {"assignees": [self.chef.pk, self.etranger.pk]})
        self.assertEqual(list(self.ticket.assignees.all()), [self.chef])

    def test_api_scope(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.login(username="chef", password="Motdepasse1")
        ids = {t["id"] for t in client.get("/api/logistics/tickets/").json()}
        self.assertIn(str(self.ticket.pk), ids)
        client.login(username="etranger", password="Motdepasse1")
        ids = {t["id"] for t in client.get("/api/logistics/tickets/").json()}
        self.assertNotIn(str(self.ticket.pk), ids)

    def test_agregats_tableau_de_bord_comptent_les_installations(self):
        from django.db.models import Q
        contexte = _agrege_maintenance_ticket_stock(
            Q(pk__in=[]), Q(installation__ship_id=self.ship.id) | Q(asset__ship_id=self.ship.id), Q(),
        )
        self.assertEqual(contexte["total_tickets_ouverts"], 2)

    def test_rapports_perimetre_et_libelles(self):
        filtre = _q_perimetre_tickets({"ship_id": self.ship.id})
        self.assertEqual(set(CorrectiveTicket.objects.filter(filtre)), {self.ticket, self.ticket_materiel})
        self.assertEqual(_nom_equipement_ticket(self.ticket), "Propulseur")
        self.assertEqual(_type_equipement_ticket(self.ticket), "Installation")
        self.assertEqual(_type_equipement_ticket(self.ticket_materiel), "T")

    def test_recherche_globale(self):
        self.client.login(username="chef", password="Motdepasse1")
        reponse = self.client.get("/search/", {"q": "Vibrations"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(list(reponse.context["tickets"]), [self.ticket])


class TicketSerializerEtBilanTests(_JeuDeDonnees):
    """Validation API asset XOR installation et rendu des bilans avec un ticket
    sur installation (jeu de données partagé _JeuDeDonnees)."""

    def _api(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.login(username="chef", password="Motdepasse1")
        return client

    def test_api_refuse_un_ticket_sans_equipement(self):
        reponse = self._api().post("/api/logistics/tickets/", {"description": "x"}, format="json")
        self.assertEqual(reponse.status_code, 400)

    def test_api_refuse_un_ticket_avec_deux_equipements(self):
        reponse = self._api().post(
            "/api/logistics/tickets/",
            {"description": "x", "asset": str(self.asset.pk), "installation": str(self.installation.pk)},
            format="json",
        )
        self.assertEqual(reponse.status_code, 400)

    def test_api_accepte_un_ticket_sur_installation_ou_materiel(self):
        client = self._api()
        for donnees in ({"installation": str(self.installation.pk)}, {"asset": str(self.asset.pk)}):
            reponse = client.post("/api/logistics/tickets/", {"description": "x", **donnees}, format="json")
            self.assertEqual(reponse.status_code, 201, reponse.content)

    def test_api_mise_a_jour_partielle_conserve_l_equipement(self):
        reponse = self._api().patch(
            f"/api/logistics/tickets/{self.ticket.pk}/", {"description": "Nouveau"}, format="json",
        )
        self.assertEqual(reponse.status_code, 200, reponse.content)

    def test_bilans_html_affichent_l_installation(self):
        from datetime import date, timedelta
        from django.template.loader import render_to_string
        from logistics.models import PartRequest, PartLineItem
        from reports.services import construire_contexte_instantane, construire_contexte_periode

        chef = User.objects.get(username="chef")
        chef.refresh_from_db()
        demande = PartRequest.objects.create(ticket=self.ticket)
        PartLineItem.objects.create(
            part_request=demande, reference="R1", description="Roulement", status="CONSUMED",
            received_at=date.today(),
        )
        instantane = render_to_string(
            "reports/bilan_instantane.html", construire_contexte_instantane("sector", self.sector.id, chef),
        )
        periode = render_to_string(
            "reports/bilan_periode.html",
            construire_contexte_periode(
                "sector", self.sector.id, chef, date.today() - timedelta(days=7), date.today() + timedelta(days=1),
            ),
        )
        self.assertIn("Propulseur", instantane)
        self.assertIn("Propulseur", periode)
        self.assertNotIn(">None<", instantane + periode)
