from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Asset, AssetFolder, AssetType, Installation
from org.models import Sector, Service, Ship


def _creer_hierarchie(suffixe="X"):
    ship = Ship.objects.create(name=f"Navire{suffixe}", code=f"NAV{suffixe}")
    service = Service.objects.create(name=f"Service{suffixe}", ship=ship)
    sector = Sector.objects.create(name=f"Secteur{suffixe}", service=service)
    asset_type = AssetType.objects.create(name=f"Type{suffixe}", category="Cat", sector=sector)
    return ship, service, sector, asset_type


class SeuilsEcritureMaterielTests(TestCase):
    """[BUG SEC] point 3/4 : un ÉQUIPIER ne doit pas pouvoir créer un dossier, un
    matériel ou une installation ; un CHEF_SECTEUR, lui, le doit (le seuil ne
    doit pas être réglé trop haut, cf. _peut_gerer_materiel = CHEF_SECTION)."""

    def setUp(self):
        self.ship, self.service, self.sector, self.asset_type = _creer_hierarchie("A")
        self.equipier = User.objects.create_user(username="equipier_mat", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})
        self.chef_secteur = User.objects.create_user(username="chef_secteur_mat", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR"})

    def test_equipier_ne_peut_pas_creer_de_dossier(self):
        self.client.login(username="equipier_mat", password="pass")
        r = self.client.post("/assets/", {"action": "create_folder", "name": "Dossier interdit"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(AssetFolder.objects.count(), 0)

    def test_chef_secteur_peut_creer_un_dossier(self):
        self.client.login(username="chef_secteur_mat", password="pass")
        r = self.client.post("/assets/", {"action": "create_folder", "name": "Dossier autorisé"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(AssetFolder.objects.count(), 1)

    def test_equipier_ne_peut_pas_creer_de_materiel(self):
        self.client.login(username="equipier_mat", password="pass")
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "asset_type_id": str(self.asset_type.id),
            "internal_id": "INT-EQ",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
        })
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Asset.objects.count(), 0)

    def test_equipier_ne_peut_pas_creer_dinstallation(self):
        self.client.login(username="equipier_mat", password="pass")
        r = self.client.post("/installations/", {
            "action": "create_installation",
            "designation": "Pompe interdite",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
        })
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Installation.objects.count(), 0)

    def test_chef_secteur_peut_creer_une_installation(self):
        self.client.login(username="chef_secteur_mat", password="pass")
        r = self.client.post("/installations/", {
            "action": "create_installation",
            "designation": "Pompe autorisée",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Installation.objects.count(), 1)


class AffichageSousDossierTests(TestCase):
    """[BUG SEC] point 5 : un matériel classé dans un sous-dossier doit apparaître
    dans ce sous-dossier (et uniquement là, pas mélangé à la racine)."""

    def setUp(self):
        self.ship, self.service, self.sector, self.asset_type = _creer_hierarchie("B")
        self.chef = User.objects.create_user(username="chef_dossier", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE"})
        self.root = AssetFolder.objects.create(name="Racine")
        self.sub = AssetFolder.objects.create(name="SousDossier", parent=self.root)
        self.asset_range = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            folder=self.sub, internal_id="RANGE",
        )
        self.asset_racine = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            internal_id="NON-RANGE",
        )

    def test_materiel_du_sous_dossier_apparait_dans_le_sous_dossier(self):
        self.client.login(username="chef_dossier", password="pass")
        r = self.client.get(f"/assets/?folder={self.sub.id}")
        ids = {a.id for a in r.context["assets"]}
        self.assertEqual(ids, {self.asset_range.id})

    def test_racine_naffiche_pas_le_materiel_range_dans_un_sous_dossier(self):
        self.client.login(username="chef_dossier", password="pass")
        r = self.client.get("/assets/")
        ids = {a.id for a in r.context["assets"]}
        self.assertEqual(ids, {self.asset_racine.id})

    def test_redirection_apres_creation_conserve_le_sous_dossier_courant(self):
        self.client.login(username="chef_dossier", password="pass")
        r = self.client.post(f"/assets/?folder={self.sub.id}", {
            "action": "create_asset",
            "asset_type_id": str(self.asset_type.id),
            "internal_id": "NOUVEAU",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn(f"folder={self.sub.id}", r.url)
        nouveau = Asset.objects.get(internal_id="NOUVEAU")
        self.assertEqual(nouveau.folder_id, self.sub.id)


class PreRemplissagePerimetreTests(TestCase):
    """[BUG SEC] point 6 : le formulaire de création de matériel/installation doit
    être pré-rempli avec le périmètre (navire/service/secteur) du chef connecté."""

    def setUp(self):
        self.ship, self.service, self.sector, self.asset_type = _creer_hierarchie("C")
        self.chef = User.objects.create_user(username="chef_perimetre", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef,
            defaults={"role": "CHEF_SERVICE", "ship": self.ship, "service": self.service, "sector": self.sector},
        )

    def test_contexte_liste_materiel_contient_le_perimetre_du_chef(self):
        self.client.login(username="chef_perimetre", password="pass")
        r = self.client.get("/assets/")
        self.assertEqual(r.context["user_ship_id"], self.ship.id)
        self.assertEqual(r.context["user_service_id"], self.service.id)
        self.assertEqual(r.context["user_sector_id"], self.sector.id)

    def test_contexte_liste_installations_contient_le_perimetre_du_chef(self):
        self.client.login(username="chef_perimetre", password="pass")
        r = self.client.get("/installations/")
        self.assertEqual(r.context["user_ship_id"], self.ship.id)
        self.assertEqual(r.context["user_service_id"], self.service.id)
        self.assertEqual(r.context["user_sector_id"], self.sector.id)
