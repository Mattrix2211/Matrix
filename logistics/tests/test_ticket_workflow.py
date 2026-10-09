"""Fiche ticket correctif présentée comme un workflow : frise, étape actuelle
et action suivante (docs/UX.md §20.2), affichée selon le droit réel d'agir."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


class TicketWorkflowTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Navire WF", code="WF")
        service = Service.objects.create(ship=navire, name="Service WF")
        self.secteur = Sector.objects.create(service=service, name="Secteur WF")
        type_actif = AssetType.objects.create(name="Pompe WF", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(asset_type=type_actif, ship=navire, service=service, sector=self.secteur)
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite")
        self.chef = self._user("chef_wf", "CHEF_SECTION")
        self.marin = self._user("marin_wf", "EQUIPIER")
        self.url = reverse("ticket-detail", args=[self.ticket.id])

    def _user(self, nom, role):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.filter(user=user).update(role=role, sector=self.secteur)
        return user

    def _page(self, utilisateur="chef_wf"):
        self.client.login(username=utilisateur, password="pass")
        return self.client.get(self.url)

    def _statut(self, statut):
        CorrectiveTicket.objects.filter(pk=self.ticket.pk).update(status=statut)

    def test_frise_et_action_suivante_du_chef(self):
        reponse = self._page()
        self.assertEqual([e["etat"] for e in reponse.context["frise"]], ["actuelle"] + ["avenir"] * 6)
        self.assertEqual(reponse.context["action_suivante"]["cible"], "DIAGNOSED")
        self.assertContains(reponse, "Passer au diagnostic")

    def test_etapes_faites_et_actuelle(self):
        self._statut("IN_REPAIR")
        etats = [e["etat"] for e in self._page().context["frise"]]
        self.assertEqual(etats, ["faite"] * 3 + ["actuelle"] + ["avenir"] * 3)

    def test_statut_hors_frise_sans_etape_actuelle(self):
        self._statut("PLANNED")
        reponse = self._page()
        self.assertEqual([e["etat"] for e in reponse.context["frise"]], ["faite"] * 3 + ["avenir"] * 4)
        self.assertTrue(reponse.context["statut_hors_frise"])

    def test_ticket_ferme_toute_la_frise_faite_sans_action(self):
        self._statut("CLOSED")
        reponse = self._page()
        self.assertEqual({e["etat"] for e in reponse.context["frise"]}, {"faite"})
        self.assertIsNone(reponse.context["action_suivante"])

    def test_ticket_bloque_sans_action_proposee(self):
        self._statut("BLOCKED")
        self.assertIsNone(self._page().context["action_suivante"])

    def test_marin_sans_droit_ne_voit_aucun_formulaire_de_statut(self):
        reponse = self._page("marin_wf")
        self.assertEqual(reponse.status_code, 200)
        self.assertIsNone(reponse.context["action_suivante"])
        self.assertNotContains(reponse, reverse("ticket-transition", args=[self.ticket.id]))
        self.assertNotContains(reponse, "Changer le statut autrement")
        self.assertContains(reponse, "réservé aux chefs de section")

    def test_remise_en_service_demande_le_mot_de_passe(self):
        self._statut("TESTING")
        self.assertContains(self._page(), 'name="mot_de_passe"')

    def test_cloture_demande_le_rex(self):
        self._statut("RETURNED_TO_SERVICE")
        reponse = self._page()
        self.assertContains(reponse, 'id="rex-diagnostic"')
        self.assertEqual(reponse.context["action_suivante"]["cible"], "CLOSED")

    def test_bouton_suivant_conserve_le_rex_deja_saisi(self):
        CorrectiveTicket.objects.filter(pk=self.ticket.pk).update(status="IN_REPAIR", diagnostic_final="Joint usé")
        self.assertContains(self._page(), '<textarea hidden name="diagnostic_final">Joint usé</textarea>', html=False)

    def test_reponse_htmx_reflete_la_nouvelle_etape(self):
        self.client.login(username="chef_wf", password="pass")
        reponse = self.client.post(
            reverse("ticket-transition", args=[self.ticket.id]), {"status": "DIAGNOSED"}, HTTP_HX_REQUEST="true",
        )
        self.assertEqual(reponse.context["action_suivante"]["cible"], "IN_REPAIR")
        self.assertContains(reponse, 'id="ticket-status"')

    def test_reponse_htmx_pour_un_marin_sans_formulaire(self):
        self.client.login(username="marin_wf", password="pass")
        reponse = self.client.post(
            reverse("ticket-transition", args=[self.ticket.id]), {"status": "DIAGNOSED"}, HTTP_HX_REQUEST="true",
        )
        self.assertEqual(reponse.status_code, 403)
