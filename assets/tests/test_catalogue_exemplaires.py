"""Saisie en grille des informations de suivi des exemplaires : droits, périmètre, tout ou rien."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, SpecialityChoice, UserProfile
from assets.models import ArticleCatalogue, Asset, AssetType, CategorieCatalogue, Location
from org.models import Sector, Service, Ship


class GrilleExemplairesTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="GXA")
        service = Service.objects.create(name="Srv A", ship=self.ship)
        self.secteur = Sector.objects.create(name="Sec A", service=service)
        self.ship_b = Ship.objects.create(name="Navire B", code="GXB")
        service_b = Service.objects.create(name="Srv B", ship=self.ship_b)
        self.secteur_b = Sector.objects.create(name="Sec B", service=service_b)
        self.lieu = Location.objects.create(ship=self.ship, name="Machine")
        self.lieu_b = Location.objects.create(ship=self.ship_b, name="Cale")
        spe = SpecialityChoice.objects.create(name="Électricien grille")
        categorie = CategorieCatalogue.objects.create(nom="Outillage grille", specialite=spe)
        self.article = ArticleCatalogue.objects.create(categorie=categorie, designation="Pince")
        self.chef = self._user("chef_gx", "CHEF_SERVICE", ship=self.ship, service=service, sector=self.secteur)
        self.assets = [self._asset(self.secteur) for _ in range(3)]
        self.autre = self._asset(self.secteur_b)
        self.url = reverse("catalogue-article-exemplaires", args=[self.article.pk])

    def _user(self, nom, role, **rattachement):
        u = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=u, defaults={"role": role, **rattachement})
        return User.objects.get(pk=u.pk)

    def _asset(self, secteur):
        type_ = AssetType.objects.get_or_create(sector=secteur, name="Outil", defaults={"category": "Outil"})[0]
        return Asset.objects.create(
            asset_type=type_, designation="Pince", ship=secteur.service.ship, service=secteur.service,
            sector=secteur, article_catalogue=self.article)

    def _donnees(self, **par_asset):
        """{asset: {colonne: valeur}} -> champs postés « <id>__<colonne> »."""
        champs = {}
        for asset, valeurs in par_asset.items():
            for colonne, valeur in valeurs.items():
                champs[f"{asset}__{colonne}"] = valeur
        return champs

    def _poster(self, lignes, url=None):
        donnees = {}
        for asset, valeurs in lignes:
            donnees.update(self._donnees(**{str(asset.pk): valeurs}))
        return self.client.post(url or self.url, donnees)

    def test_modification_en_lot_en_une_validation(self):
        self.client.force_login(self.chef)
        r = self._poster([
            (self.assets[0], {"serial_number": " SN-1 ", "internal_id": "B1", "emplacement": "machine", "local": "L2", "gisement": "G"}),
            (self.assets[1], {"serial_number": "SN-2", "internal_id": "B2", "emplacement": "", "local": "", "gisement": ""}),
        ])
        self.assertRedirects(r, reverse("catalogue-article", args=[self.article.pk]))
        a, b = Asset.objects.get(pk=self.assets[0].pk), Asset.objects.get(pk=self.assets[1].pk)
        self.assertEqual((a.serial_number, a.internal_id, a.location, a.local, a.gisement), ("SN-1", "B1", self.lieu, "L2", "G"))
        self.assertEqual((b.serial_number, b.location), ("SN-2", None))
        self.assertEqual(a.updated_by, self.chef)
        self.assertEqual(AuditLog.objects.filter(action="catalogue.exemplaire", actor=self.chef).count(), 2)

    def test_ligne_inchangee_non_modifiee_ni_tracee(self):
        self.client.force_login(self.chef)
        self._poster([(self.assets[0], {"serial_number": "", "internal_id": ""})])
        self.assertFalse(AuditLog.objects.filter(action="catalogue.exemplaire").exists())

    def test_tout_ou_rien_une_ligne_invalide_annule_tout(self):
        self.client.force_login(self.chef)
        r = self._poster([
            (self.assets[0], {"serial_number": "SN-OK"}),
            (self.assets[1], {"serial_number": "x" * 300, "emplacement": "Inconnu"}),
        ])
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "Emplacement inconnu", status_code=400)
        self.assertEqual(Asset.objects.get(pk=self.assets[0].pk).serial_number, "")
        self.assertContains(r, "SN-OK", status_code=400)  # saisie conservée dans la grille

    def test_emplacement_d_un_autre_navire_refuse(self):
        self.client.force_login(self.chef)
        r = self._poster([(self.assets[0], {"emplacement": "Cale"})])
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(Asset.objects.get(pk=self.assets[0].pk).location)

    def test_exemplaire_d_un_autre_navire_refuse_et_rien_ecrit(self):
        self.client.force_login(self.chef)
        r = self._poster([(self.assets[0], {"serial_number": "SN-OK"}), (self.autre, {"serial_number": "PIRATE"})])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Asset.objects.get(pk=self.autre.pk).serial_number, "")
        self.assertEqual(Asset.objects.get(pk=self.assets[0].pk).serial_number, "")

    def test_identifiant_forge_refuse(self):
        self.client.force_login(self.chef)
        r = self.client.post(self.url, {"pas-un-uuid__serial_number": "x"})
        self.assertEqual(r.status_code, 400)

    def test_exemplaire_d_un_autre_article_refuse(self):
        autre_article = ArticleCatalogue.objects.create(categorie=self.article.categorie, designation="Autre")
        etranger = self._asset(self.secteur)
        etranger.article_catalogue = autre_article
        etranger.save()
        self.client.force_login(self.chef)
        self.assertEqual(self._poster([(etranger, {"serial_number": "X"})]).status_code, 400)

    def test_perimetre_service_chef_section_hors_secteur(self):
        autre_secteur = Sector.objects.create(name="Sec A2", service=self.secteur.service)
        hors = self._asset(autre_secteur)
        section_chef = self._user("cs_gx", "CHEF_SECTION", ship=self.ship, service=self.secteur.service, sector=self.secteur)
        self.client.force_login(section_chef)
        self.assertEqual(self._poster([(hors, {"serial_number": "X"})]).status_code, 400)
        self.assertEqual(Asset.objects.get(pk=hors.pk).serial_number, "")

    def test_doublon_de_serie_signale_sans_bloquer(self):
        self.client.force_login(self.chef)
        r = self._poster([(self.assets[0], {"serial_number": "SN-9"}), (self.assets[1], {"serial_number": "SN-9"})], url=self.url)
        suivi = self.client.get(r.url)
        self.assertContains(suivi, "SN-9")
        self.assertContains(suivi, "en double")
        self.assertEqual(Asset.objects.filter(serial_number="SN-9").count(), 2)

    def test_meme_serie_sur_un_autre_navire_pas_un_doublon(self):
        self.autre.serial_number = "SN-9"
        self.autre.save()
        self.client.force_login(self.chef)
        r = self._poster([(self.assets[0], {"serial_number": "SN-9"})])
        self.assertNotContains(self.client.get(r.url), "en double")

    def test_lot_incomplets_du_navire(self):
        complet = self.assets[2]
        complet.serial_number, complet.internal_id, complet.location = "S", "B", self.lieu
        complet.save()
        self.client.force_login(self.chef)
        url = reverse("catalogue-exemplaires-incomplets")
        r = self.client.get(url)
        self.assertContains(r, f'name="{self.assets[0].pk}__serial_number"')
        self.assertNotContains(r, f'name="{complet.pk}__serial_number"')
        self.assertNotContains(r, f'name="{self.autre.pk}__serial_number"')
        self.assertRedirects(self._poster([(self.assets[0], {"serial_number": "S0"})], url=url), url)

    def test_page_porte_recopie_brouillon_et_import(self):
        self.client.force_login(self.chef)
        r = self.client.get(self.url)
        self.assertContains(r, "data-grille")
        self.assertContains(r, "Recopier vers le bas")
        self.assertContains(r, f'data-brouillon="catalogue:exemplaires:{self.article.pk}"')
        self.assertContains(r, reverse("asset-import"))

    def test_sans_droit_refuse(self):
        simple = self._user("eq_gx", "EQUIPIER", ship=self.ship, service=self.secteur.service, sector=self.secteur)
        self.client.force_login(simple)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self._poster([(self.assets[0], {"serial_number": "X"})]).status_code, 403)

    def test_equipage_a_terre_refuse(self):
        self.ship.double_equipage = True
        self.ship.equipage_a_bord = "ALPHA"
        self.ship.save()
        self.chef.profile.equipage = "BRAVO"
        self.chef.profile.save()
        self.client.force_login(self.chef)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self._poster([(self.assets[0], {"serial_number": "X"})]).status_code, 403)

    def test_fiche_article_propose_de_completer(self):
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(reverse("catalogue-article", args=[self.article.pk])), self.url)
