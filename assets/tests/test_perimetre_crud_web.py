from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType, Installation, Location


class PerimetreCrudAssetWebTests(TestCase):
    """Vérifie que les actions CRUD/groupées de AssetListView.post et
    InstallationListView.post revalident bien le périmètre posté (ship/service/
    sector/section) et l'objet ciblé (pk), pas seulement le rôle de l'appelant."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(name="Srv A", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec A", service=self.service)

        self.autre_ship = Ship.objects.create(name="Navire B", code="NAV-B")
        self.autre_service = Service.objects.create(name="Srv B", ship=self.autre_ship)
        self.autre_sector = Sector.objects.create(name="Sec B", service=self.autre_service)

        self.asset_type = AssetType.objects.create(name="Extincteur", category="EPI", sector=self.sector)

        self.chef = User.objects.create_user(username="chef_perim", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship, "service": self.service}
        )

        self.equipier = User.objects.create_user(username="equipier_perim", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship}
        )

        self.materiel = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            serial_number="SN-A", internal_id="A-1",
        )
        self.materiel_hors_perimetre = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Multimètre", category="Outillage", sector=self.autre_sector),
            ship=self.autre_ship, service=self.autre_service, sector=self.autre_sector,
            serial_number="SN-B", internal_id="B-1",
        )

        self.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.installation_hors_perimetre = Installation.objects.create(
            designation="Pompe hors périmètre", ship=self.autre_ship, service=self.autre_service, sector=self.autre_sector,
        )

    def test_chef_service_peut_editer_un_asset_en_postant_son_propre_navire(self):
        """Cas nominal : le formulaire poste toute la chaîne ship/service/
        sector, y compris le navire (ancêtre du niveau 'service' de l'appelant)
        — _org_dans_perimetre doit reconnaître que ce navire est bien celui
        auquel appartient déjà le service de l'appelant, pas le rejeter."""
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(self.materiel.id),
            "internal_id": self.materiel.internal_id,
            "serial_number": self.materiel.serial_number,
            "designation": "Extincteur révisé",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
        })
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.designation, "Extincteur révisé")

    def test_chef_service_peut_creer_un_asset_dans_son_propre_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "internal_id": "A-2",
            "serial_number": "SN-A2",
            "designation": "Nouvel extincteur",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "asset_type_id": str(self.asset_type.id),
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Asset.objects.filter(internal_id="A-2").exists())

    def test_chef_service_peut_editer_une_installation_en_postant_son_propre_navire(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "edit_installation",
            "pk": str(self.installation.id),
            "designation": "Groupe électrogène révisé",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
        })
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.designation, "Groupe électrogène révisé")

    def test_equipier_rejete_sur_bulk_delete_assets(self):
        self.client.login(username="equipier_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "bulk_delete_assets",
            "selected_ids": [str(self.materiel.id)],
        })
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Asset.objects.filter(pk=self.materiel.id).exists())

    def test_equipier_rejete_sur_bulk_update_ship(self):
        self.client.login(username="equipier_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "bulk_update_ship",
            "selected_ids": [str(self.materiel.id)],
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 403)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.ship_id, self.ship.id)

    def test_chef_service_ne_peut_pas_deplacer_un_asset_vers_un_navire_hors_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(self.materiel.id),
            "internal_id": self.materiel.internal_id,
            "serial_number": self.materiel.serial_number,
            "designation": "Extincteur modifié",
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 302)
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.ship_id, self.ship.id)
        self.assertNotEqual(self.materiel.designation, "Extincteur modifié")

    def test_chef_service_ne_peut_pas_editer_un_asset_hors_de_son_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(self.materiel_hors_perimetre.id),
            "internal_id": self.materiel_hors_perimetre.internal_id,
            "serial_number": self.materiel_hors_perimetre.serial_number,
            "designation": "Modifié frauduleusement",
        })
        self.assertEqual(r.status_code, 302)
        self.materiel_hors_perimetre.refresh_from_db()
        self.assertNotEqual(self.materiel_hors_perimetre.designation, "Modifié frauduleusement")

    def test_chef_service_ne_peut_pas_supprimer_un_asset_hors_de_son_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        self.client.post("/assets/", {
            "action": "delete_asset",
            "pk": str(self.materiel_hors_perimetre.id),
        })
        self.assertTrue(Asset.objects.filter(pk=self.materiel_hors_perimetre.id).exists())

    def test_equipier_rejete_sur_bulk_delete_installations(self):
        self.client.login(username="equipier_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "bulk_delete_installations",
            "selected_ids": [str(self.installation.id)],
        })
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Installation.objects.filter(pk=self.installation.id).exists())

    def test_chef_service_ne_peut_pas_deplacer_une_installation_vers_un_navire_hors_perimetre(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "edit_installation",
            "pk": str(self.installation.id),
            "designation": "Groupe modifié",
            "ship_id": str(self.autre_ship.id),
        })
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.ship_id, self.ship.id)
        self.assertNotEqual(self.installation.designation, "Groupe modifié")

    def test_chef_service_ne_peut_pas_supprimer_une_installation_hors_de_son_perimetre_via_le_detail(self):
        self.client.login(username="chef_perim", password="pass")
        self.client.post(f"/installations/{self.installation_hors_perimetre.id}/", {
            "action": "delete_installation",
            "pk": str(self.installation_hors_perimetre.id),
        })
        self.assertTrue(Installation.objects.filter(pk=self.installation_hors_perimetre.id).exists())

    # --- Emplacement (Location) sélectionnable et créable à la volée depuis les
    # formulaires matériel/installation, remplaçant l'ancienne page dédiée /locations/.

    def test_chef_service_peut_creer_un_asset_avec_un_emplacement_existant(self):
        emplacement = Location.objects.create(name="Local A", ship=self.ship)
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "internal_id": "A-3",
            "serial_number": "SN-A3",
            "designation": "Extincteur avec emplacement",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "asset_type_id": str(self.asset_type.id),
            "location_id": str(emplacement.id),
        })
        self.assertEqual(r.status_code, 302)
        asset = Asset.objects.get(internal_id="A-3")
        self.assertEqual(asset.location_id, emplacement.id)

    def test_chef_service_peut_creer_un_nouvel_emplacement_a_la_volee_pour_un_asset(self):
        """Option "+ Ajouter un nouvel emplacement…" du formulaire matériel :
        location_id="__new__" + new_location_name crée l'emplacement rattaché
        au navire déjà validé, sans passer par une page dédiée."""
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "internal_id": "A-4",
            "serial_number": "SN-A4",
            "designation": "Extincteur avec nouvel emplacement",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "asset_type_id": str(self.asset_type.id),
            "location_id": "__new__",
            "new_location_name": "Coursive bâbord",
        })
        self.assertEqual(r.status_code, 302)
        asset = Asset.objects.get(internal_id="A-4")
        self.assertIsNotNone(asset.location)
        self.assertEqual(asset.location.name, "Coursive bâbord")
        self.assertEqual(asset.location.ship_id, self.ship.id)

    def test_creer_un_nouvel_emplacement_a_la_volee_ne_duplique_pas_un_emplacement_existant(self):
        Location.objects.create(name="Coursive tribord", ship=self.ship)
        self.client.login(username="chef_perim", password="pass")
        self.client.post("/assets/", {
            "action": "create_asset",
            "internal_id": "A-5",
            "serial_number": "SN-A5",
            "designation": "Extincteur",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "asset_type_id": str(self.asset_type.id),
            "location_id": "__new__",
            "new_location_name": "Coursive tribord",
        })
        self.assertEqual(Location.objects.filter(ship=self.ship, name="Coursive tribord").count(), 1)

    def test_chef_service_peut_creer_une_installation_avec_un_nouvel_emplacement_a_la_volee(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "create_installation",
            "designation": "Pompe avec nouvel emplacement",
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "location_id": "__new__",
            "new_location_name": "Local machine avant",
        })
        self.assertEqual(r.status_code, 302)
        installation = Installation.objects.get(designation="Pompe avec nouvel emplacement")
        self.assertIsNotNone(installation.location)
        self.assertEqual(installation.location.name, "Local machine avant")
        self.assertEqual(installation.location.ship_id, self.ship.id)

    def test_chef_service_peut_editer_une_installation_avec_un_nouvel_emplacement_a_la_volee_depuis_la_fiche(self):
        """Chemin réellement utilisé par l'écran (modale d'édition de la fiche
        installation, cf. _modales_fiche_installation.html), géré par
        _action_edit_installation dans installation_actions.py — distinct du
        handler de la liste testé ci-dessus."""
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post(f"/installations/{self.installation.id}/", {
            "action": "edit_installation",
            "pk": str(self.installation.id),
            "designation": self.installation.designation,
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "location_id": "__new__",
            "new_location_name": "Local machine bâbord",
        })
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertIsNotNone(self.installation.location)
        self.assertEqual(self.installation.location.name, "Local machine bâbord")

    def test_consultation_fiche_materiel_hors_perimetre_est_introuvable(self):
        """Régression : la fiche détail d'un matériel (AssetDetailView) n'était
        pas filtrée par périmètre (contrairement à InstallationDetailView), ce
        qui permettait de consulter un matériel hors de son périmètre en
        connaissant son UUID, même sans lien y menant depuis la liste."""
        self.client.login(username="chef_perim", password="pass")
        r = self.client.get(f"/assets/{self.materiel_hors_perimetre.id}/")
        self.assertEqual(r.status_code, 404)

    def test_consultation_fiche_materiel_dans_le_perimetre_reste_accessible(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.get(f"/assets/{self.materiel.id}/")
        self.assertEqual(r.status_code, 200)

    def test_chef_service_peut_editer_une_installation_avec_un_nouvel_emplacement_a_la_volee(self):
        self.client.login(username="chef_perim", password="pass")
        r = self.client.post("/installations/", {
            "action": "edit_installation",
            "pk": str(self.installation.id),
            "designation": self.installation.designation,
            "ship_id": str(self.ship.id),
            "service_id": str(self.service.id),
            "sector_id": str(self.sector.id),
            "location_id": "__new__",
            "new_location_name": "Local machine arrière",
        })
        self.assertEqual(r.status_code, 302)
        self.installation.refresh_from_db()
        self.assertIsNotNone(self.installation.location)
        self.assertEqual(self.installation.location.name, "Local machine arrière")
