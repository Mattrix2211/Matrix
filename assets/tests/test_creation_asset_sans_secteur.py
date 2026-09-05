from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType


class CreationAssetSansSecteurTests(TestCase):
    """Bug Phase 6 : soumettre la modale « Nouveau matériel » sans secteur (ou avec
    un secteur sans aucun AssetType configuré) ne doit JAMAIS créer un matériel
    fantôme ni faire disparaître le formulaire sans explication — verrouille le
    comportement serveur actuel (refus propre, aucune création) et vérifie que le
    correctif côté client (champ obligatoire) est bien en place dans le template."""

    def setUp(self):
        self.ship = Ship.objects.create(name="S1")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec avec type", service=self.service)
        self.sector_sans_type = Sector.objects.create(name="Sec sans type", service=self.service)
        AssetType.objects.create(name="Multimètre", category="Mesure", sector=self.sector)

        self.chef = User.objects.create_user(username="chef_sans_secteur", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE"})
        self.client.login(username="chef_sans_secteur", password="pass")

    def test_aucun_secteur_ni_type_fournis_ne_cree_pas_de_materiel(self):
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "designation": "Matériel fantôme",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
        }, follow=True)
        self.assertFalse(Asset.objects.filter(designation="Matériel fantôme").exists())
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("type" in m.lower() for m in messages_affiches))

    def test_secteur_sans_aucun_type_configure_ne_cree_pas_de_materiel(self):
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "designation": "Matériel fantôme 2",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector_sans_type.id,
        }, follow=True)
        self.assertFalse(Asset.objects.filter(designation="Matériel fantôme 2").exists())
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("type" in m.lower() for m in messages_affiches))

    def test_secteur_avec_type_configure_cree_bien_le_materiel(self):
        # Cas nominal : ne doit pas être cassé par le correctif.
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "designation": "Multimètre n°9",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Asset.objects.filter(designation="Multimètre n°9").exists())

    def test_champ_secteur_obligatoire_cote_client_sans_type_preselectionne(self):
        # Ouvrir « Nouveau matériel » sans filtre ?type= : le secteur doit être
        # marqué obligatoire (attribut HTML required) pour empêcher la soumission
        # silencieuse d'un formulaire incomplet.
        r = self.client.get("/assets/")
        self.assertContains(r, 'id="createSector" required')

    def test_champ_secteur_non_obligatoire_si_type_preselectionne_via_filtre(self):
        # Quand le type est déjà imposé par le filtre ?type=, le secteur reste
        # facultatif (le type n'a pas besoin d'en être déduit).
        asset_type = AssetType.objects.first()
        r = self.client.get(f"/assets/?type={asset_type.id}")
        self.assertNotContains(r, 'id="createSector" required')
