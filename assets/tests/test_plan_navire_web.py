"""[FEAT] Administration : configurer les ponts et zones d'un navire.

Sous-tâche 2/3 du plan visuel du navire : interface web (CHEF_SERVICE+) pour
créer/réordonner les ponts, téléverser leur image de fond, et dessiner/éditer
les zones cliquables dessus. La sous-tâche 1 a livré le modèle de données
(Deck/Zone), la sous-tâche 3 branchera le clic sur une zone vers le matériel.
"""
import json

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Deck, Location, Zone
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


class PlanNavireZoneCRUDTests(TestCase):
    """Positionnement/édition/suppression des zones cliquables d'un pont."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        self.emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        self.chef = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship})
        self.client.login(username="chef_a", password="pass")
        self.url = f"/assets/plan/{self.pont.id}/"
        self.points = json.dumps([
            {"x": 10, "y": 10}, {"x": 40, "y": 10}, {"x": 40, "y": 30}, {"x": 10, "y": 30},
        ])

    def test_creation_dune_zone_avec_emplacement(self):
        r = self.client.post(self.url, {
            "action": "create_zone", "zone_name": "Local machine avant",
            "location_id": self.emplacement.id, "points": self.points,
        })
        self.assertEqual(r.status_code, 302)
        zone = Zone.objects.get(deck=self.pont)
        self.assertEqual(zone.name, "Local machine avant")
        self.assertEqual(zone.location, self.emplacement)
        self.assertEqual(len(zone.points), 4)

    def test_page_editeur_saffiche_avec_image_et_zones_existantes(self):
        """Rendu complet de l'éditeur (image + zones déjà dessinées), pour
        détecter une erreur de template plutôt qu'une simple absence de crash
        sur les vues sans image (cf. tests de périmètre ci-dessus)."""
        self.pont.image = _image_1x1_png()
        self.pont.save(update_fields=["image"])
        Zone.objects.create(
            deck=self.pont, name="Local machine avant", location=self.emplacement,
            points=json.loads(self.points),
        )
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Local machine avant")

    def test_creation_dune_zone_brouillon_sans_emplacement(self):
        r = self.client.post(self.url, {
            "action": "create_zone", "zone_name": "Zone en cours de rattachement",
            "location_id": "", "points": self.points,
        })
        self.assertEqual(r.status_code, 302)
        zone = Zone.objects.get(deck=self.pont)
        self.assertIsNone(zone.location)

    def test_creation_zone_refusee_si_contour_invalide(self):
        r = self.client.post(self.url, {
            "action": "create_zone", "zone_name": "Zone cassée",
            "points": "pas-du-json",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Zone.objects.count(), 0)

    def test_creation_zone_refusee_sans_nom(self):
        r = self.client.post(self.url, {"action": "create_zone", "zone_name": "  ", "points": self.points})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Zone.objects.count(), 0)

    def test_edition_dune_zone_renommage_et_changement_demplacement(self):
        zone = Zone.objects.create(deck=self.pont, name="Zone brute", points=json.loads(self.points))
        nouveau_local = Location.objects.create(ship=self.ship, name="Local machine arrière")
        r = self.client.post(self.url, {
            "action": "update_zone", "zone_id": zone.id, "zone_name": "Local machine arrière",
            "location_id": nouveau_local.id, "points": self.points,
        })
        self.assertEqual(r.status_code, 302)
        zone.refresh_from_db()
        self.assertEqual(zone.name, "Local machine arrière")
        self.assertEqual(zone.location, nouveau_local)

    def test_repositionnement_dune_zone_change_son_contour(self):
        zone = Zone.objects.create(deck=self.pont, name="Zone brute", points=json.loads(self.points))
        nouveaux_points = json.dumps([
            {"x": 50, "y": 50}, {"x": 80, "y": 50}, {"x": 80, "y": 70}, {"x": 50, "y": 70},
        ])
        r = self.client.post(self.url, {
            "action": "update_zone", "zone_id": zone.id, "zone_name": "Zone brute", "points": nouveaux_points,
        })
        self.assertEqual(r.status_code, 302)
        zone.refresh_from_db()
        self.assertEqual(zone.points[0], {"x": 50.0, "y": 50.0})

    def test_suppression_dune_zone(self):
        zone = Zone.objects.create(deck=self.pont, name="Zone brute", points=json.loads(self.points))
        r = self.client.post(self.url, {"action": "delete_zone", "zone_id": zone.id})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Zone.objects.filter(pk=zone.id).exists())


class PlanNavirePerimetreTests(TestCase):
    """Un utilisateur ne doit pouvoir configurer que les ponts/zones du navire
    de son propre périmètre — même logique que le reste du projet
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
            "action": "create_zone", "zone_name": "Intrusion", "points": "[]",
        })
        self.assertEqual(r2.status_code, 403)
        self.assertEqual(Zone.objects.filter(deck=self.pont_b).count(), 0)

    def test_master_admin_peut_choisir_le_navire_via_selecteur(self):
        self.client.login(username="master", password="pass")
        r = self.client.get(f"/assets/plan/?navire={self.ship_b.id}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Pont B")

    def test_master_admin_peut_configurer_un_pont_de_nimporte_quel_navire(self):
        self.client.login(username="master", password="pass")
        r = self.client.get(f"/assets/plan/{self.pont_b.id}/")
        self.assertEqual(r.status_code, 200)
