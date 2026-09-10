"""[FEAT] Administration : configurer les ponts et positionner le matériel
sur le plan d'un navire.

Sous-tâche 2/3 du plan visuel du navire : interface web (CHEF_SERVICE+) pour
créer/réordonner les ponts, téléverser leur image de fond, et positionner le
matériel dessus par épingle précise (x/y). Remplace l'ancien éditeur de zones
rectangulaires (Zone, supprimé), décision métier tranchée par l'utilisateur
(cf. tâche Notion « Remplacer les zones du plan navire par un placement
PRÉCIS du matériel »).
"""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Deck
from org.models import Sector, Service, Ship


def _image_1x1_png():
    # PNG 1x1 minimal valide, suffisant pour valider le champ FileField (aucune
    # dépendance à une vraie bibliothèque d'images côté test).
    contenu = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c4944415478da6360606060000000050001a5f645400000000049454e44ae426082"
    )
    return SimpleUploadedFile("plan.png", contenu, content_type="image/png")


class PlanNavireRBACTests(TestCase):
    """Seuls les CHEF_SERVICE et rôles supérieurs accèdent à la configuration
    du plan visuel du navire (cohérent avec les autres actions de
    configuration du matériel, cf. _peut_gerer_rattachement_parent)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.ship, name="Service A")

        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship}
        )
        self.chef_service = User.objects.create_user(username="chef_service", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "ship": self.ship, "service": self.service}
        )

    def test_equipier_ne_peut_pas_acceder_a_la_liste_des_ponts(self):
        self.client.login(username="equipier", password="pass")
        r = self.client.get("/assets/plan/")
        self.assertEqual(r.status_code, 403)

    def test_equipier_ne_peut_pas_creer_de_pont(self):
        self.client.login(username="equipier", password="pass")
        r = self.client.post("/assets/plan/", {"action": "create_deck", "name": "Pont supérieur"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Deck.objects.count(), 0)

    def test_chef_service_peut_acceder_a_la_liste_des_ponts(self):
        self.client.login(username="chef_service", password="pass")
        r = self.client.get("/assets/plan/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Plan du navire")


class PlanNavireDeckCRUDTests(TestCase):
    """Création/réordonnancement/suppression des ponts, dans le périmètre du
    navire de l'utilisateur connecté."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.chef = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship})
        self.client.login(username="chef_a", password="pass")

    def test_creation_dun_pont(self):
        r = self.client.post("/assets/plan/", {"action": "create_deck", "name": "Pont supérieur"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Deck.objects.filter(ship=self.ship, name="Pont supérieur").exists())

    def test_creation_sans_nom_naboutit_pas(self):
        r = self.client.post("/assets/plan/", {"action": "create_deck", "name": "   "})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Deck.objects.count(), 0)

    def test_reordonnancement_des_ponts(self):
        p1 = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        p2 = Deck.objects.create(ship=self.ship, name="Pont B", order=2)
        r = self.client.post("/assets/plan/", {"action": "move_up", "pk": p2.id})
        self.assertEqual(r.status_code, 302)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p2.order, 1)
        self.assertEqual(p1.order, 2)

    def test_renommage_dun_pont(self):
        pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        r = self.client.post("/assets/plan/", {"action": "rename_deck", "pk": pont.id, "name": "Pont supérieur"})
        self.assertEqual(r.status_code, 302)
        pont.refresh_from_db()
        self.assertEqual(pont.name, "Pont supérieur")

    def test_suppression_dun_pont(self):
        pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        r = self.client.post("/assets/plan/", {"action": "delete_deck", "pk": pont.id})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Deck.objects.filter(pk=pont.id).exists())

    def test_upload_image_dun_pont(self):
        pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        r = self.client.post(
            f"/assets/plan/{pont.id}/",
            {"action": "upload_image", "image": _image_1x1_png()},
        )
        self.assertEqual(r.status_code, 302)
        pont.refresh_from_db()
        self.assertTrue(bool(pont.image))


class PlanNavireEpingleCRUDTests(TestCase):
    """Positionnement/repositionnement/retrait des épingles de matériel sur
    le plan d'un pont."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        self.pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        self.materiel = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            internal_id="EXT-01",
        )
        self.chef = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship})
        self.client.login(username="chef_a", password="pass")
        self.url = f"/assets/plan/{self.pont.id}/"

    def test_positionnement_dun_materiel(self):
        r = self.client.post(self.url, {"action": "place_pin", "asset_id": str(self.materiel.id), "x": "25", "y": "60"})
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.plan_deck, self.pont)
        self.assertEqual(self.materiel.position_x, 25)
        self.assertEqual(self.materiel.position_y, 60)

    def test_page_editeur_saffiche_avec_image_et_materiel_positionne(self):
        """Rendu complet de l'éditeur (image + épingles déjà positionnées),
        pour détecter une erreur de template plutôt qu'une simple absence de
        crash sur les vues sans image (cf. tests de périmètre ci-dessus)."""
        self.pont.image = _image_1x1_png()
        self.pont.save(update_fields=["image"])
        self.materiel.plan_deck = self.pont
        self.materiel.position_x = 25
        self.materiel.position_y = 60
        self.materiel.save(update_fields=["plan_deck", "position_x", "position_y"])
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "EXT-01")

    def test_positionnement_refuse_si_materiel_hors_unite(self):
        autre_navire = Ship.objects.create(name="Navire B", code="NAV-B")
        autre_service = Service.objects.create(ship=autre_navire, name="Service B")
        autre_sector = Sector.objects.create(service=autre_service, name="Secteur B")
        materiel_etranger = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Casque", category="EPI", sector=autre_sector),
            ship=autre_navire, service=autre_service, sector=autre_sector, internal_id="ETR-01",
        )
        r = self.client.post(self.url, {"action": "place_pin", "asset_id": str(materiel_etranger.id), "x": "10", "y": "10"})
        self.assertEqual(r.status_code, 302)
        materiel_etranger.refresh_from_db()
        self.assertIsNone(materiel_etranger.plan_deck)

    def test_positionnement_refuse_si_coordonnees_invalides(self):
        r = self.client.post(self.url, {"action": "place_pin", "asset_id": str(self.materiel.id), "x": "150", "y": "10"})
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertIsNone(self.materiel.plan_deck)

    def test_repositionnement_dun_materiel_deja_positionne(self):
        self.materiel.plan_deck = self.pont
        self.materiel.position_x = 10
        self.materiel.position_y = 10
        self.materiel.save(update_fields=["plan_deck", "position_x", "position_y"])
        r = self.client.post(self.url, {"action": "place_pin", "asset_id": str(self.materiel.id), "x": "80", "y": "90"})
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.position_x, 80)
        self.assertEqual(self.materiel.position_y, 90)

    def test_retrait_dun_materiel_du_plan(self):
        self.materiel.plan_deck = self.pont
        self.materiel.position_x = 10
        self.materiel.position_y = 10
        self.materiel.save(update_fields=["plan_deck", "position_x", "position_y"])
        r = self.client.post(self.url, {"action": "remove_pin", "asset_id": str(self.materiel.id)})
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertIsNone(self.materiel.plan_deck)
        self.assertIsNone(self.materiel.position_x)
        self.assertIsNone(self.materiel.position_y)
        # Le matériel n'est jamais supprimé, seule sa position sur le plan l'est.
        self.assertTrue(Asset.objects.filter(pk=self.materiel.pk).exists())


class PlanNavirePerimetreTests(TestCase):
    """Un utilisateur ne doit pouvoir configurer que les ponts/matériel du
    navire de son propre périmètre — même logique que le reste du projet
    (cf. assets/tests/test_perimetre_crud_web.py)."""

    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A", code="NAV-A")
        self.ship_b = Ship.objects.create(name="Navire B", code="NAV-B")
        self.pont_b = Deck.objects.create(ship=self.ship_b, name="Pont B", order=1)

        self.chef_a = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_a, defaults={"role": "CHEF_SERVICE", "ship": self.ship_a})

        self.master_admin = User.objects.create_superuser(username="master", password="pass", email="m@example.com")

    def test_chef_service_ne_voit_pas_les_ponts_dun_autre_navire_dans_la_liste(self):
        self.client.login(username="chef_a", password="pass")
        r = self.client.get("/assets/plan/")
        self.assertNotContains(r, "Pont B")

    def test_chef_service_ne_peut_pas_configurer_un_pont_dun_autre_navire(self):
        self.client.login(username="chef_a", password="pass")
        r = self.client.get(f"/assets/plan/{self.pont_b.id}/")
        self.assertEqual(r.status_code, 403)

        r2 = self.client.post(f"/assets/plan/{self.pont_b.id}/", {
            "action": "upload_image", "image": _image_1x1_png(),
        })
        self.assertEqual(r2.status_code, 403)

    def test_master_admin_peut_choisir_le_navire_via_selecteur(self):
        self.client.login(username="master", password="pass")
        r = self.client.get(f"/assets/plan/?navire={self.ship_b.id}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Pont B")

    def test_master_admin_peut_configurer_un_pont_de_nimporte_quel_navire(self):
        self.client.login(username="master", password="pass")
        r = self.client.get(f"/assets/plan/{self.pont_b.id}/")
        self.assertEqual(r.status_code, 200)
