from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType


class CreationAssetSansSecteurTests(TestCase):
    """Soumettre une création sans secteur (ou avec un secteur sans AssetType configuré)
    ne doit JAMAIS créer un matériel fantôme : refus propre côté serveur, aucune création."""

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

    def test_liste_propose_le_catalogue_plutot_que_la_saisie_libre(self):
        # L'ajout passe par le catalogue : plus de modale de création libre sur la liste.
        r = self.client.get("/assets/")
        self.assertContains(r, 'href="/catalogue/"')
        self.assertContains(r, "Ajouter du matériel")
        self.assertNotContains(r, "createAssetModal")
