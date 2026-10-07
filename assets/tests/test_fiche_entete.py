"""En-tête de fiche standard : action principale unique, Discussion en panneau, lecture seule à terre."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation, InstallationHourReading
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


class FicheInstallationOngletsTests(FicheEnteteTests):
    """Cinq onglets, blocs repliables et indicateurs à popover (UX §12 et §13)."""

    def test_cinq_onglets_de_premier_niveau(self):
        r = self.client.get(f"/installations/{self.installation.id}/")
        for onglet in ("ensemble", "maintenance", "mesures", "histo", "parts"):
            self.assertContains(r, f'id="tab-{onglet}"')
        self.assertContains(r, 'role="tab"', count=5)

    def test_blocs_repliables_documents_et_sous_equipements(self):
        sous = Installation.objects.create(designation="Moteur", ship=self.navire, service=self.installation.service,
                                           sector=self.installation.sector, parent=self.installation)
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, "<summary>Sous-équipements", count=1)
        self.assertContains(r, "<summary>Documents", count=1)
        self.assertContains(r, f"/installations/{sous.id}/")

    def test_indicateur_popover_avec_ajout_de_releve(self):
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, 'data-mx-contenu="#indicateur-')
        self.assertContains(r, "Ajouter un relevé</button>", count=3)

    def test_popover_affiche_dernier_releve(self):
        InstallationHourReading.objects.create(installation=self.installation, date=timezone.localdate(), hours=12)
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, "Dernier relevé : 12")

    def test_ajout_de_releve_masque_a_terre(self):
        self.navire.double_equipage = True
        self.navire.equipage_a_bord = "A"
        self.navire.save()
        UserProfile.objects.filter(user=self.chef).update(equipage="B")
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, "Dernier relevé", count=0)
        self.assertNotContains(r, "Ajouter un relevé</button>")
