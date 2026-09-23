from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from datetime import timedelta
from django.utils import timezone
from assets.models import (
    Installation, InstallationEvent, InstallationVibrationReading, InstallationIsolationReading,
)


class SyntheseFicheInstallationTests(TestCase):
    """La fiche installation affiche une synthèse visuelle et des compteurs sur les onglets."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire S")
        service = Service.objects.create(name="Srv S", ship=ship)
        sector = Sector.objects.create(name="Sec S", service=service)
        user = User.objects.create_user(username="chef_synthese", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "CHEF_SERVICE"})
        self.installation = Installation.objects.create(
            designation="Pompe", ship=ship, service=service, sector=sector, critique=True,
        )
        self.client.login(username="chef_synthese", password="pass")

    def test_synthese_affichee_avec_badge_critique(self):
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, 'id="synthese-installation"')
        self.assertContains(r, "Critique")
        self.assertContains(r, "Aucun relevé")

    def test_compteur_sur_onglet_historique_seulement_si_non_vide(self):
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertNotContains(r, 'Historique <span class="badge')
        InstallationEvent.objects.create(installation=self.installation, label="Anomalie")
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, 'Historique <span class="badge')

    def test_retard_vibratoire_et_isolement_affiches(self):
        ancien = timezone.localdate() - timedelta(days=400)
        InstallationVibrationReading.objects.create(installation=self.installation, date=ancien, state="A")
        InstallationIsolationReading.objects.create(installation=self.installation, date=ancien, ohms=250)
        r = self.client.get(f"/installations/{self.installation.id}/")
        self.assertContains(r, "État A")
        self.assertContains(r, "en retard de")
        self.assertContains(r, "Relevé en retard")
        self.assertContains(r, "250")
