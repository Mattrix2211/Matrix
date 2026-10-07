"""Dates du matériel (mise en service, dernier contrôle, péremption) : grille, API, fiche."""
import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import ArticleCatalogue, Asset, AssetType, CategorieCatalogue
from accounts.models import SpecialityChoice
from org.models import Sector, Service, Ship


class DatesMaterielTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire dates", code="DAT")
        self.service = Service.objects.create(name="Srv dates", ship=self.ship)
        self.secteur = Sector.objects.create(name="Sec dates", service=self.service)
        self.type = AssetType.objects.create(sector=self.secteur, name="Extincteur", category="Sécurité")
        spe = SpecialityChoice.objects.create(name="Sécurité dates")
        categorie = CategorieCatalogue.objects.create(nom="Extincteurs dates", specialite=spe)
        self.article = ArticleCatalogue.objects.create(categorie=categorie, designation="Extincteur CO2", duree_vie_mois=12)
        self.chef = User.objects.create_user(username="chef_dates", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={
            "role": "CHEF_SERVICE", "ship": self.ship, "service": self.service, "sector": self.secteur})
        self.asset = self._asset()
        self.url = reverse("catalogue-article-exemplaires", args=[self.article.pk])

    def _asset(self):
        return Asset.objects.create(asset_type=self.type, designation="Extincteur", ship=self.ship,
                                    service=self.service, sector=self.secteur, article_catalogue=self.article)

    def _poster(self, asset, **valeurs):
        self.client.force_login(self.chef)
        return self.client.post(self.url, {f"{asset.pk}__{k}": v for k, v in valeurs.items()})

    def test_grille_affiche_les_colonnes_de_date(self):
        self.client.force_login(self.chef)
        r = self.client.get(self.url)
        for nom in ("date_mise_en_service", "date_dernier_controle", "date_peremption"):
            self.assertContains(r, f"__{nom}")
        self.assertContains(r, "JJ/MM/AAAA")

    def test_saisie_au_format_francais(self):
        r = self._poster(self.asset, date_mise_en_service="05/03/2026", date_dernier_controle="1/9/2026",
                         date_peremption="05/03/2028")
        self.assertEqual(r.status_code, 302, getattr(r, "content", b""))
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.date_mise_en_service, datetime.date(2026, 3, 5))
        self.assertEqual(self.asset.date_dernier_controle, datetime.date(2026, 9, 1))
        self.assertEqual(self.asset.date_peremption, datetime.date(2028, 3, 5))
        self.assertEqual(self.client.get(self.url).context["lignes"][0]["valeurs"]["date_mise_en_service"], "05/03/2026")

    def test_date_invalide_erreur_par_cellule_et_tout_ou_rien(self):
        autre = self._asset()
        r = self.client.force_login(self.chef) or self.client.post(self.url, {
            f"{self.asset.pk}__date_peremption": "2026-03-05", f"{autre.pk}__serial_number": "SN-X"})
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "Date invalide", status_code=400)
        autre.refresh_from_db()
        self.assertEqual(autre.serial_number, "")

    def test_peremption_avant_mise_en_service_refusee(self):
        r = self._poster(self.asset, date_mise_en_service="05/03/2026", date_peremption="04/03/2026")
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "antérieure", status_code=400)

    def test_peremption_proposee_depuis_la_duree_de_vie(self):
        r = self._poster(self.asset, date_mise_en_service="31/01/2026")
        self.assertEqual(r.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.date_peremption, datetime.date(2027, 1, 31))

    def test_peremption_saisie_non_ecrasee(self):
        self._poster(self.asset, date_mise_en_service="31/01/2026", date_peremption="01/06/2026")
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.date_peremption, datetime.date(2026, 6, 1))

    def test_vider_une_date_la_supprime(self):
        self.asset.date_dernier_controle = datetime.date(2026, 1, 1)
        self.asset.save()
        self._poster(self.asset, date_dernier_controle="")
        self.asset.refresh_from_db()
        self.assertIsNone(self.asset.date_dernier_controle)

    def test_fiche_affiche_les_dates_et_la_peremption_depassee(self):
        self.asset.date_peremption = datetime.date(2020, 1, 2)
        self.asset.save()
        self.client.force_login(self.chef)
        r = self.client.get(reverse("asset-detail", args=[self.asset.pk]))
        self.assertContains(r, "02/01/2020")
        self.assertContains(r, "Dépassée")

    def test_edition_web_du_materiel(self):
        self.client.force_login(self.chef)
        donnees = {"action": "edit_asset", "pk": str(self.asset.pk), "ship_id": self.ship.pk,
                   "service_id": self.service.pk, "sector_id": self.secteur.pk,
                   "date_mise_en_service": "10/02/2026"}
        self.client.post(reverse("asset-list"), donnees)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.date_mise_en_service, datetime.date(2026, 2, 10))
        self.client.post(reverse("asset-list"), {**donnees, "date_mise_en_service": "31-02"})
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.date_mise_en_service, datetime.date(2026, 2, 10))

    def test_api_lecture_ecriture_et_perimetre(self):
        api = APIClient()
        api.login(username="chef_dates", password="pass")
        r = api.patch(f"/api/assets/assets/{self.asset.pk}/", {"date_peremption": "2027-05-01"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["date_peremption"], "2027-05-01")
        r = api.patch(f"/api/assets/assets/{self.asset.pk}/", {"date_mise_en_service": "2027-06-01"}, format="json")
        self.assertEqual(r.status_code, 400)
        autre_navire = Ship.objects.create(name="Autre dates", code="DAT2")
        service = Service.objects.create(name="S2", ship=autre_navire)
        secteur = Sector.objects.create(name="Sc2", service=service)
        type_ = AssetType.objects.create(sector=secteur, name="T2", category="C")
        etranger = Asset.objects.create(asset_type=type_, ship=autre_navire, service=service, sector=secteur)
        r = api.patch(f"/api/assets/assets/{etranger.pk}/", {"date_peremption": "2027-05-01"}, format="json")
        self.assertEqual(r.status_code, 404)
