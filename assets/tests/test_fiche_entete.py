"""En-tête de fiche standard : action principale unique, Discussion en panneau, lecture seule à terre."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from threads.utils import ajouter_commentaire


class FicheEnteteTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire E", code="NVE")
        service = Service.objects.create(name="Srv E", ship=self.navire)
        secteur = Sector.objects.create(name="Sec E", service=service)
        type_actif = AssetType.objects.create(name="Pompe E", category="Méca", sector=secteur)
        self.asset = Asset.objects.create(asset_type=type_actif, ship=self.navire, service=service, sector=secteur)
        self.installation = Installation.objects.create(designation="Pompe incendie", ship=self.navire, service=service, sector=secteur)
        self.ticket = CorrectiveTicket.objects.create(
            asset=self.asset, description="Fuite", severity=4, reported_at=timezone.now(), status="OPEN",
        )
        self.chef = User.objects.create_user(username="chef_e", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=secteur, service=service, ship=self.navire)
        self.client.login(username="chef_e", password="pass")

    def test_fiche_installation_entete_complet(self):
        ajouter_commentaire(self.installation, self.chef, "Vu ce matin")
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, "<h1 class=\"mx-fiche__titre\">Pompe incendie</h1>", html=False)
        self.assertContains(r, "Discussion · 1")
        self.assertContains(r, "Vu ce matin")
        self.assertContains(r, "mx-fiche__tracabilite")
        self.assertContains(r, 'class="btn btn-primary mx-fiche__action"', count=1)

    def test_fiche_materiel_une_seule_action_principale(self):
        r = self.client.get(f"/assets/{self.asset.id}/")
        self.assertContains(r, 'class="btn btn-primary mx-fiche__action"', count=1)
        self.assertContains(r, "Discussion · 0")

    def test_commentaire_depuis_fiche_materiel_et_installation(self):
        self.client.post(f"/assets/{self.asset.id}/commentaire/", {"body": "RAS matériel"})
        self.client.post(f"/installations/{self.installation.id}/commentaire/", {"body": "RAS installation"})
        self.assertContains(self.client.get(f"/assets/{self.asset.id}/"), "RAS matériel")
        self.assertContains(self.client.get(f"/installations/{self.installation.id}/"), "RAS installation")

    def test_fiche_ticket_action_selon_le_droit(self):
        r = self.client.get(f"/logistics/tickets/{self.ticket.id}/")
        self.assertContains(r, "Changer le statut")
        simple = User.objects.create_user(username="marin_e", password="pass")
        UserProfile.objects.filter(user=simple).update(ship=self.navire)
        self.client.login(username="marin_e", password="pass")
        r = self.client.get(f"/logistics/tickets/{self.ticket.id}/")
        self.assertNotContains(r, "btn btn-primary mx-fiche__action")
