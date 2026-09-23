from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Installation


class EditInstallationCritiqueTests(TestCase):
    """[BUG] La case « Installation critique » du formulaire de la fiche détail
    (InstallationDetailView -> _action_edit_installation) était ignorée à
    l'enregistrement, contrairement au même champ sur la vue liste
    (InstallationListView) : le champ ``critique`` n'était jamais réassigné
    sur l'objet avant la sauvegarde.
    """

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire C")
        self.service = Service.objects.create(name="Srv C", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec C", service=self.service)

        self.chef = User.objects.create_user(username="chef_critique", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE"})

        self.installation = Installation.objects.create(
            designation="Compresseur", ship=self.ship, service=self.service, sector=self.sector,
            critique=False,
        )

    def _payload(self, **extra):
        payload = {
            "action": "edit_installation",
            "pk": str(self.installation.id),
            "designation": self.installation.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
        }
        payload.update(extra)
        return payload

    def test_cocher_critique_depuis_la_fiche_detail_est_bien_enregistre(self):
        self.client.login(username="chef_critique", password="pass")
        r = self.client.post(f"/installations/{self.installation.id}/", self._payload(critique="on"))
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertTrue(self.installation.critique)

    def test_decocher_critique_depuis_la_fiche_detail_est_bien_enregistre(self):
        self.installation.critique = True
        self.installation.save(update_fields=["critique"])
        self.client.login(username="chef_critique", password="pass")
        # Case non cochée : absente du POST, comme le ferait un navigateur.
        r = self.client.post(f"/installations/{self.installation.id}/", self._payload())
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertFalse(self.installation.critique)
