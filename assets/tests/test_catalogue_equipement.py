"""Équiper le navire depuis le catalogue : exemplaires pré-remplis, droits, périmètre, compteur."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog, SpecialityChoice, UserProfile
from assets.models import ArticleCatalogue, Asset, AssetFolder, AssetType, CategorieCatalogue, Location
from org.models import Sector, Service, Ship


class EquiperNavireTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="EQA")
        self.service = Service.objects.create(name="Srv A", ship=self.ship)
        self.secteur = Sector.objects.create(name="Sec A", service=self.service)
        self.autre_ship = Ship.objects.create(name="Navire B", code="EQB")
        self.autre_service = Service.objects.create(name="Srv B", ship=self.autre_ship)
        self.autre_secteur = Sector.objects.create(name="Sec B", service=self.autre_service)
        self.lieu = Location.objects.create(ship=self.ship, name="Local 1")
        self.lieu_b = Location.objects.create(ship=self.autre_ship, name="Local B")
        spe = SpecialityChoice.objects.create(name="Électricien équip")
        self.categorie = CategorieCatalogue.objects.create(nom="Outillage équip", specialite=spe)
        self.dossier = AssetFolder.objects.create(name="outillage équip")
        self.article = ArticleCatalogue.objects.create(
            categorie=self.categorie, designation="Pince à sertir", marque="Facom", reference="XR-12", nno="1234")
        self.chef = self._user("chef_eq", "CHEF_SERVICE", ship=self.ship, service=self.service, sector=self.secteur)
        self.url = reverse("catalogue-article-equiper", args=[self.article.pk])

    def _user(self, nom, role, **rattachement):
        u = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=u, defaults={"role": role, **rattachement})
        return User.objects.get(pk=u.pk)

    def _poster(self, quantite="3", secteur=None, etape="2", **plus):
        return self.client.post(self.url, {
            "etape": etape, "action": "suivant", "quantite": quantite,
            "secteur": str((secteur or self.secteur).pk), **plus})

    def test_creation_de_n_exemplaires_pre_remplis(self):
        self.client.force_login(self.chef)
        r = self._poster("3", emplacement=str(self.lieu.pk))
        self.assertRedirects(r, reverse("catalogue-article", args=[self.article.pk]))
        assets = Asset.objects.filter(article_catalogue=self.article)
        self.assertEqual(assets.count(), 3)
        a = assets.first()
        self.assertEqual((a.designation, a.marque, a.reference, a.nno), ("Pince à sertir", "Facom", "XR-12", "1234"))
        self.assertEqual((a.ship, a.service, a.sector, a.location, a.folder), (self.ship, self.service, self.secteur, self.lieu, self.dossier))
        self.assertEqual((a.serial_number, a.internal_id), ("", ""))
        self.assertEqual(a.created_by, self.chef)
        self.assertEqual(AssetType.objects.get(pk=a.asset_type_id).sector, self.secteur)
        self.assertTrue(AuditLog.objects.filter(action="catalogue.equipement", actor=self.chef).exists())

    def test_etape_1_affiche_la_verification_sans_creer(self):
        self.client.force_login(self.chef)
        r = self._poster("2", etape="1")
        self.assertContains(r, "exemplaire 2")
        self.assertEqual(Asset.objects.count(), 0)

    def test_quantites_invalides_refusees(self):
        self.client.force_login(self.chef)
        for q in ("0", "-2", "abc", "", "201", "99999999"):
            self.assertEqual(self._poster(q).status_code, 400, q)
        self.assertEqual(Asset.objects.count(), 0)

    @override_settings(CATALOGUE_QUANTITE_MAX=5)
    def test_plafond_configurable(self):
        self.client.force_login(self.chef)
        self.assertEqual(self._poster("6").status_code, 400)
        self.assertEqual(self._poster("5").status_code, 302)

    def test_secteur_hors_perimetre_refuse(self):
        self.client.force_login(self.chef)
        self.assertEqual(self._poster(secteur=self.autre_secteur).status_code, 400)
        self.assertEqual(Asset.objects.count(), 0)

    def test_emplacement_d_un_autre_navire_refuse(self):
        self.client.force_login(self.chef)
        self.assertEqual(self._poster(emplacement=str(self.lieu_b.pk)).status_code, 400)
        self.assertEqual(Asset.objects.count(), 0)

    def test_sans_droit_refuse(self):
        simple = self._user("equipier_eq", "EQUIPIER", ship=self.ship, service=self.service, sector=self.secteur)
        self.client.force_login(simple)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self._poster().status_code, 403)
        self.assertEqual(Asset.objects.count(), 0)

    def test_article_archive_refuse(self):
        self.article.actif = False
        self.article.save()
        self.client.force_login(self.chef)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self._poster().status_code, 404)

    def test_equipage_a_terre_refuse_et_bouton_masque(self):
        self.ship.double_equipage = True
        self.ship.equipage_a_bord = "ALPHA"
        self.ship.save()
        self.chef.profile.equipage = "BRAVO"
        self.chef.profile.save()
        self.client.force_login(self.chef)
        self.assertEqual(self._poster().status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertNotContains(self.client.get(reverse("catalogue-article", args=[self.article.pk])), "Équiper le navire")
        self.assertEqual(Asset.objects.count(), 0)

    def test_bouton_visible_pour_qui_peut_equiper(self):
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(reverse("catalogue-article", args=[self.article.pk])), "Équiper le navire")

    def test_compteur_a_bord_sans_fuite_entre_navires(self):
        self.client.force_login(self.chef)
        self._poster("4")
        autre = self._user("chef_b", "CHEF_SERVICE", ship=self.autre_ship, service=self.autre_service, sector=self.autre_secteur)
        self.client.force_login(autre)
        self._poster("1", secteur=self.autre_secteur)
        r = self.client.get(reverse("catalogue-article", args=[self.article.pk]))
        self.assertContains(r, "1 exemplaire à bord")
        r = self.client.get(reverse("catalogue"), {"categorie": self.categorie.pk})
        self.assertContains(r, "1 à bord")
        self.assertNotContains(r, "4 à bord")

    def test_api_ne_permet_pas_de_poser_le_lien_catalogue(self):
        self.client.force_login(self.chef)
        r = self.client.post("/api/assets/assets/", {
            "asset_type": AssetType.objects.create(name="T", category="C", sector=self.secteur).pk,
            "ship": self.ship.pk, "service": self.service.pk, "sector": self.secteur.pk,
            "article_catalogue": str(self.article.pk)})
        self.assertIn(r.status_code, (201, 400, 404))
        self.assertFalse(Asset.objects.filter(article_catalogue=self.article).exists())
