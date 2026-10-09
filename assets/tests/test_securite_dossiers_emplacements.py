from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Asset, AssetFolder, AssetType, Installation, Location
from org.models import Sector, Service, Ship


def _navire(suffixe):
    ship = Ship.objects.create(name=f"Navire {suffixe}", code=f"NAV-{suffixe}")
    service = Service.objects.create(name=f"Service {suffixe}", ship=ship)
    sector = Sector.objects.create(name=f"Secteur {suffixe}", service=service)
    type_ = AssetType.objects.create(name=f"Type {suffixe}", category="Cat", sector=sector)
    return ship, service, sector, type_


def _materiel(ship, service, sector, type_, **kw):
    return Asset.objects.create(asset_type=type_, ship=ship, service=service, sector=sector, **kw)


def _utilisateur(nom, role, ship=None, service=None):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "service": service})
    return user


class EmplacementInterNaviresTests(TestCase):
    def setUp(self):
        self.a = _navire("A")
        self.b = _navire("B")
        self.loc_a = Location.objects.create(ship=self.a[0], name="Poste A")
        self.loc_b = Location.objects.create(ship=self.b[0], name="Poste B")
        _utilisateur("chef_a", "CHEF_SERVICE", self.a[0], self.a[1])
        self.materiel = _materiel(*self.a, internal_id="A-1")
        self.installation = Installation.objects.create(
            designation="Pompe A", ship=self.a[0], service=self.a[1], sector=self.a[2])
        self.client.login(username="chef_a", password="pass")

    def test_groupe_materiel_refuse_emplacement_dun_autre_navire(self):
        self.client.post("/assets/", {
            "action": "bulk_update_location", "selected_ids": [str(self.materiel.id)],
            "location_id": str(self.loc_b.id)})
        self.materiel.refresh_from_db()
        self.assertIsNone(self.materiel.location)

    def test_groupe_materiel_accepte_emplacement_du_meme_navire(self):
        self.client.post("/assets/", {
            "action": "bulk_update_location", "selected_ids": [str(self.materiel.id)],
            "location_id": str(self.loc_a.id)})
        self.materiel.refresh_from_db()
        self.assertEqual(self.materiel.location, self.loc_a)

    def test_groupe_installation_refuse_emplacement_dun_autre_navire(self):
        self.client.post("/installations/", {
            "action": "bulk_update_location", "selected_ids": [str(self.installation.id)],
            "location_id": str(self.loc_b.id)})
        self.installation.refresh_from_db()
        self.assertIsNone(self.installation.location)

    def test_edition_refuse_emplacement_dun_autre_navire(self):
        self.client.post("/assets/", {
            "action": "edit_asset", "pk": str(self.materiel.id),
            "ship_id": str(self.a[0].id), "service_id": str(self.a[1].id), "sector_id": str(self.a[2].id),
            "location_id": str(self.loc_b.id)})
        self.materiel.refresh_from_db()
        self.assertIsNone(self.materiel.location)

    def test_listes_ne_proposent_que_les_emplacements_du_perimetre(self):
        for url in ("/assets/", "/installations/"):
            ctx = self.client.get(url).context
            self.assertEqual(list(ctx["locations"]), [self.loc_a], url)

    def test_fiche_installation_ne_propose_que_les_emplacements_du_perimetre(self):
        ctx = self.client.get(f"/installations/{self.installation.pk}/").context
        self.assertEqual(list(ctx["locations"]), [self.loc_a])

    def test_gestion_flotte_voit_tous_les_emplacements(self):
        _utilisateur("admin_flotte", "MASTER_ADMIN")
        self.client.login(username="admin_flotte", password="pass")
        self.assertEqual(set(self.client.get("/assets/").context["locations"]), {self.loc_a, self.loc_b})


class DossiersPerimetreTests(TestCase):
    def setUp(self):
        self.a = _navire("A")
        self.b = _navire("B")
        _utilisateur("chef_a", "CHEF_SERVICE", self.a[0], self.a[1])
        _utilisateur("chef_b", "CHEF_SERVICE", self.b[0], self.b[1])
        _utilisateur("admin_flotte", "MASTER_ADMIN")
        self.dossier_a = AssetFolder.objects.create(name="Dossier A")
        _materiel(*self.a, folder=self.dossier_a)
        self.dossier_mixte = AssetFolder.objects.create(name="Mixte")
        _materiel(*self.a, folder=self.dossier_mixte)
        _materiel(*self.b, folder=self.dossier_mixte)
        self.dossier_vide = AssetFolder.objects.create(name="Vide")
        self.parent = AssetFolder.objects.create(name="Parent")
        self.enfant = AssetFolder.objects.create(name="Enfant", parent=self.parent)
        _materiel(*self.b, folder=self.enfant)

    def _poster(self, user, **donnees):
        self.client.login(username=user, password="pass")
        return self.client.post("/assets/", donnees)

    def test_renommer_dossier_de_son_navire(self):
        self._poster("chef_a", action="rename_folder", pk=self.dossier_a.pk, name="Renommé")
        self.dossier_a.refresh_from_db()
        self.assertEqual(self.dossier_a.name, "Renommé")

    def test_renommer_dossier_dun_autre_navire_refuse(self):
        self._poster("chef_b", action="rename_folder", pk=self.dossier_a.pk, name="Piraté")
        self.dossier_a.refresh_from_db()
        self.assertEqual(self.dossier_a.name, "Dossier A")

    def test_renommer_dossier_mixte_refuse(self):
        self._poster("chef_a", action="rename_folder", pk=self.dossier_mixte.pk, name="Piraté")
        self.dossier_mixte.refresh_from_db()
        self.assertEqual(self.dossier_mixte.name, "Mixte")

    def test_supprimer_dossier_dun_autre_navire_refuse(self):
        self._poster("chef_b", action="delete_folder", pk=self.dossier_a.pk)
        self.assertTrue(AssetFolder.objects.filter(pk=self.dossier_a.pk).exists())

    def test_supprimer_dossier_contenant_materiel_hors_perimetre_refuse(self):
        self._poster("chef_a", action="delete_folder", pk=self.dossier_mixte.pk)
        self.assertTrue(AssetFolder.objects.filter(pk=self.dossier_mixte.pk).exists())

    def test_supprimer_dossier_dont_un_sous_dossier_est_hors_perimetre_refuse(self):
        self._poster("chef_a", action="delete_folder", pk=self.parent.pk)
        self.assertTrue(AssetFolder.objects.filter(pk=self.enfant.pk).exists())

    def test_supprimer_dossier_de_son_navire(self):
        self._poster("chef_a", action="delete_folder", pk=self.dossier_a.pk)
        self.assertFalse(AssetFolder.objects.filter(pk=self.dossier_a.pk).exists())

    def test_dossier_vide_reserve_a_la_gestion_avancee(self):
        # Un équipier d'écriture simple ne peut pas renommer un dossier vide.
        _utilisateur("chef_section_a", "CHEF_SECTION", self.a[0], self.a[1])
        self._poster("chef_section_a", action="rename_folder", pk=self.dossier_vide.pk, name="X")
        self.dossier_vide.refresh_from_db()
        self.assertEqual(self.dossier_vide.name, "Vide")
        self._poster("chef_a", action="rename_folder", pk=self.dossier_vide.pk, name="Vide bis")
        self.dossier_vide.refresh_from_db()
        self.assertEqual(self.dossier_vide.name, "Vide bis")

    def test_gestion_flotte_garde_tous_les_droits(self):
        self._poster("admin_flotte", action="delete_folder", pk=self.dossier_mixte.pk)
        self.assertFalse(AssetFolder.objects.filter(pk=self.dossier_mixte.pk).exists())

    def test_creation_sous_dossier_hors_perimetre_refusee(self):
        self._poster("chef_a", action="create_folder", name="Intrus", parent_id=self.enfant.pk)
        self.assertFalse(AssetFolder.objects.filter(name="Intrus").exists())


class PeremptionEditionWebTests(TestCase):
    def setUp(self):
        self.a = _navire("A")
        _utilisateur("chef_a", "CHEF_SERVICE", self.a[0], self.a[1])
        self.materiel = _materiel(*self.a, internal_id="A-1")
        self.client.login(username="chef_a", password="pass")

    def _editer(self, mise, peremption):
        self.client.post("/assets/", {
            "action": "edit_asset", "pk": str(self.materiel.id),
            "ship_id": str(self.a[0].id), "service_id": str(self.a[1].id), "sector_id": str(self.a[2].id),
            "date_mise_en_service": mise, "date_peremption": peremption})
        self.materiel.refresh_from_db()

    def test_peremption_anterieure_refusee(self):
        self._editer("01/06/2025", "01/01/2025")
        self.assertIsNone(self.materiel.date_peremption)

    def test_peremption_posterieure_acceptee(self):
        self._editer("01/06/2025", "01/01/2027")
        self.assertEqual(str(self.materiel.date_peremption), "2027-01-01")
