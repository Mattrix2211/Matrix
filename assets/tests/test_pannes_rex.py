"""Tests de la recherche « pannes déjà rencontrées » (REX) sur la fiche d'un actif.

Cette recherche est volontairement « tous navires confondus » : elle ne doit
PAS être filtrée par le périmètre de l'utilisateur (scope_filters_for_user),
contrairement à toutes les autres listes de l'application. Elle est filtrée
uniquement par asset_type, avec les tickets fermés (CLOSED) portant un
diagnostic final et une solution renseignés.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


class PannesDejaRencontreesTests(TestCase):
    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire A REX", code="NA-RX")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A REX")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A REX")
        self.type_pompe = AssetType.objects.create(name="Pompe immergée", category="Méca", sector=self.secteur_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.type_pompe, ship=self.navire_a, service=self.service_a, sector=self.secteur_a
        )

        self.navire_b = Ship.objects.create(name="Navire B REX", code="NB-RX")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B REX")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B REX")
        self.type_pompe_b = AssetType.objects.create(name="Pompe immergée", category="Méca", sector=self.secteur_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.type_pompe_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b
        )

        self.autre_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur_a)
        self.asset_autre_type = Asset.objects.create(
            asset_type=self.autre_type, ship=self.navire_a, service=self.service_a, sector=self.secteur_a
        )

        # Utilisateur cantonné au navire A uniquement : ne doit pas empêcher de voir
        # la panne du navire B, la recherche étant assumée hors périmètre.
        self.equipier_navire_a = User.objects.create_user(username="equipier_a_rex", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier_navire_a, defaults={"role": "EQUIPIER", "ship": self.navire_a})

        self.client.login(username="equipier_a_rex", password="pass")

    def test_panne_fermee_du_meme_type_sur_un_autre_navire_est_visible(self):
        panne_autre_navire = CorrectiveTicket.objects.create(
            asset=self.asset_b, description="Pompe HS", status="CLOSED",
            diagnostic_final="Roulement grippé", solution="Roulement remplacé",
        )
        response = self.client.get(reverse("asset-detail", args=[self.asset_a.id]))
        pannes = list(response.context["pannes_deja_rencontrees"])
        self.assertIn(panne_autre_navire, pannes)

    def test_panne_dun_autre_type_dequipement_est_exclue(self):
        panne_autre_type = CorrectiveTicket.objects.create(
            asset=self.asset_autre_type, description="Extincteur périmé", status="CLOSED",
            diagnostic_final="Péremption", solution="Extincteur remplacé",
        )
        response = self.client.get(reverse("asset-detail", args=[self.asset_a.id]))
        pannes = list(response.context["pannes_deja_rencontrees"])
        self.assertNotIn(panne_autre_type, pannes)

    def test_ticket_non_ferme_est_exclu(self):
        ticket_ouvert = CorrectiveTicket.objects.create(
            asset=self.asset_b, description="Pompe bruyante", status="IN_REPAIR",
            diagnostic_final="Roulement usé", solution="",
        )
        response = self.client.get(reverse("asset-detail", args=[self.asset_a.id]))
        pannes = list(response.context["pannes_deja_rencontrees"])
        self.assertNotIn(ticket_ouvert, pannes)

    def test_ticket_ferme_sans_diagnostic_ni_solution_est_exclu(self):
        # Ticket fermé avant l'introduction du REX obligatoire (donnée historique) :
        # ne doit pas polluer la recherche avec une fiche vide.
        ticket_sans_rex = CorrectiveTicket.objects.create(
            asset=self.asset_b, description="Ancien ticket", status="CLOSED",
        )
        response = self.client.get(reverse("asset-detail", args=[self.asset_a.id]))
        pannes = list(response.context["pannes_deja_rencontrees"])
        self.assertNotIn(ticket_sans_rex, pannes)
