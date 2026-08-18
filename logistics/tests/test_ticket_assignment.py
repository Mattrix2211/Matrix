"""Tests de l'assignation des tickets correctifs (« mes tickets »).

Vérifie : le contexte "mes_tickets" du tableau de bord (principe fondamental
n°3 de CLAUDE.md), le scoping par périmètre ET par assignation de la nouvelle
liste web des tickets, et le contrôle de rôle sur l'assignation depuis la
fiche détail.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


class TableauDeBordMesTicketsTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire test", code="NT-TK")
        self.service = Service.objects.create(ship=self.navire, name="Service test")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur test")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )

        self.marin = User.objects.create_user(username="marin_tk", password="pass")
        self.autre_marin = User.objects.create_user(username="autre_tk", password="pass")

        self.url = reverse("home")

    def test_ticket_assigne_apparait_dans_mes_tickets(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite hydraulique")
        ticket.assignees.add(self.marin)

        self.client.login(username="marin_tk", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_tickets"]), [ticket])

    def test_ticket_dun_autre_marin_est_absent_du_contexte(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite hydraulique")
        ticket.assignees.add(self.autre_marin)

        self.client.login(username="marin_tk", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_tickets"]), [])

    def test_ticket_ferme_ou_annule_est_exclu(self):
        ticket_ferme = CorrectiveTicket.objects.create(asset=self.asset, description="Fermé", status="CLOSED")
        ticket_ferme.assignees.add(self.marin)
        ticket_annule = CorrectiveTicket.objects.create(asset=self.asset, description="Annulé", status="CANCELLED")
        ticket_annule.assignees.add(self.marin)

        self.client.login(username="marin_tk", password="pass")
        response = self.client.get(self.url)

        self.assertEqual(list(response.context["mes_tickets"]), [])


class TicketListViewTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T-LIST", code="TL")
        self.service = Service.objects.create(ship=self.navire, name="Service T-LIST")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T-LIST")
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre secteur")

        self.autre_navire = Ship.objects.create(name="Navire B", code="NB-LIST")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Service B")
        self.secteur_autre_navire = Sector.objects.create(service=self.autre_service, name="Secteur B")

        self.asset_type = AssetType.objects.create(name="Pompe", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.asset_autre_secteur = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Pompe B", category="Méca", sector=self.autre_secteur),
            ship=self.navire, service=self.service, sector=self.autre_secteur,
        )
        self.asset_autre_navire = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Pompe C", category="Méca", sector=self.secteur_autre_navire),
            ship=self.autre_navire, service=self.autre_service, sector=self.secteur_autre_navire,
        )

        self.equipier = User.objects.create_user(username="equipier_tk", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur)

        self.chef = User.objects.create_user(username="chef_tk", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.ticket_equipier = CorrectiveTicket.objects.create(asset=self.asset, description="Assigné équipier")
        self.ticket_equipier.assignees.add(self.equipier)

        self.ticket_non_assigne = CorrectiveTicket.objects.create(asset=self.asset, description="Non assigné")

        self.ticket_hors_perimetre = CorrectiveTicket.objects.create(
            asset=self.asset_autre_secteur, description="Hors périmètre"
        )
        self.ticket_hors_perimetre.assignees.add(self.chef)

        self.ticket_autre_navire = CorrectiveTicket.objects.create(
            asset=self.asset_autre_navire, description="Autre navire"
        )

        self.url = reverse("ticket-list")

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_equipier_ne_voit_que_ses_propres_tickets_par_defaut(self):
        self.client.login(username="equipier_tk", password="pass")
        response = self.client.get(self.url)
        tickets = list(response.context["tickets"])
        self.assertIn(self.ticket_equipier, tickets)
        self.assertNotIn(self.ticket_non_assigne, tickets)

    def test_equipier_ne_peut_pas_basculer_sur_la_vue_perimetre(self):
        self.client.login(username="equipier_tk", password="pass")
        response = self.client.get(self.url, {"vue": "perimetre"})
        self.assertEqual(response.context["vue"], "mes")
        self.assertFalse(response.context["peut_voir_perimetre"])

    def test_chef_peut_voir_tout_le_perimetre(self):
        self.client.login(username="chef_tk", password="pass")
        response = self.client.get(self.url, {"vue": "perimetre"})
        tickets = list(response.context["tickets"])
        self.assertIn(self.ticket_equipier, tickets)
        self.assertIn(self.ticket_non_assigne, tickets)

    def test_ticket_hors_perimetre_jamais_visible_meme_en_vue_perimetre(self):
        self.client.login(username="chef_tk", password="pass")
        response = self.client.get(self.url, {"vue": "perimetre"})
        tickets = list(response.context["tickets"])
        self.assertNotIn(self.ticket_hors_perimetre, tickets)
        self.assertNotIn(self.ticket_autre_navire, tickets)

    def test_chef_vue_mes_tickets_ne_voit_pas_le_ticket_hors_perimetre_meme_assigne(self):
        # Le chef est assigné à ticket_hors_perimetre, mais ce ticket est hors de
        # son périmètre (autre secteur) : le scope l'exclut avant même le filtre
        # d'assignation.
        self.client.login(username="chef_tk", password="pass")
        response = self.client.get(self.url)
        tickets = list(response.context["tickets"])
        self.assertNotIn(self.ticket_hors_perimetre, tickets)


class TicketAssignViewTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T-ASS", code="TA")
        self.service = Service.objects.create(ship=self.navire, name="Service T-ASS")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T-ASS")
        self.asset_type = AssetType.objects.create(name="Élingue", category="Levage", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Élingue usée")

        self.marin = User.objects.create_user(username="marin_ass", password="pass")
        UserProfile.objects.filter(user=self.marin).update(role="EQUIPIER", ship=self.navire)

        self.equipier = User.objects.create_user(username="equipier_ass", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur)

        self.chef = User.objects.create_user(username="chef_ass", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.url = reverse("ticket-assign", args=[self.ticket.id])

    def test_equipier_ne_peut_pas_assigner(self):
        self.client.login(username="equipier_ass", password="pass")
        response = self.client.post(self.url, {"assignees": [str(self.marin.id)]})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(list(self.ticket.assignees.all()), [])

    def test_chef_peut_assigner_un_marin(self):
        self.client.login(username="chef_ass", password="pass")
        response = self.client.post(self.url, {"assignees": [str(self.marin.id)]}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(list(self.ticket.assignees.all()), [self.marin])

    def test_chef_peut_desassigner_en_repostant_une_liste_vide(self):
        self.ticket.assignees.add(self.marin)
        self.client.login(username="chef_ass", password="pass")
        response = self.client.post(self.url, {}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(list(self.ticket.assignees.all()), [])

    def test_page_detail_affiche_le_formulaire_dassignation_pour_un_chef(self):
        self.client.login(username="chef_ass", password="pass")
        response = self.client.get(reverse("ticket-detail", args=[self.ticket.id]))
        self.assertContains(response, "Assigner")
        self.assertContains(response, self.marin.username)

    def test_marin_scope_secteur_apparait_dans_les_assignables(self):
        """Régression QA : un profil scopé au secteur (donc sans ship
        renseigné directement) doit quand même apparaître comme assignable,
        pas seulement les profils qui ont ship en direct."""
        self.client.login(username="chef_ass", password="pass")
        response = self.client.get(reverse("ticket-detail", args=[self.ticket.id]))
        self.assertContains(response, self.equipier.username)

    def test_chef_peut_assigner_un_marin_scope_secteur(self):
        self.client.login(username="chef_ass", password="pass")
        response = self.client.post(self.url, {"assignees": [str(self.equipier.id)]}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(list(self.ticket.assignees.all()), [self.equipier])

    def test_page_detail_naffiche_pas_le_formulaire_pour_un_equipier(self):
        self.client.login(username="equipier_ass", password="pass")
        response = self.client.get(reverse("ticket-detail", args=[self.ticket.id]))
        self.assertNotContains(response, 'name="assignees"')
