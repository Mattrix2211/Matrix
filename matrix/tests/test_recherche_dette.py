"""Dette de la recherche : modules désactivés, NUL, identifiant de ticket, personnes."""
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from matrix.core import recherche
from matrix.core.middleware import SansNulMiddleware
from matrix.core.modules import invalidate_cache
from org.models import ModuleActivation, Sector, Service, Ship


class RechercheDetteTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire R", code="NVR")
        service = Service.objects.create(ship=self.navire, name="Service R")
        self.secteur = Sector.objects.create(service=service, name="Secteur R")
        self.autre_secteur = Sector.objects.create(service=service, name="Autre secteur R")
        self.marin = self._marin("marin_r", self.secteur, "Zoé", "Rivière")
        self.collegue = self._marin("collegue_r", self.autre_secteur, "Zélie", "Rivière")
        autre_navire = Ship.objects.create(name="Navire S", code="NVS")
        self.etranger = self._marin("etranger_r", None, "Zita", "Rivière", navire=autre_navire)
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=type_asset, internal_id="POMPE-R", ship=self.navire, service=service, sector=self.secteur)
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite sur la pompe")
        self.addCleanup(invalidate_cache, self.navire.id)

    def _marin(self, nom, secteur, prenom, nom_famille, navire=None):
        user = User.objects.create_user(username=nom, password="pass", first_name=prenom, last_name=nom_famille,
                                        email=f"{nom}@exemple.test")
        profil = user.profile
        profil.role, profil.sector, profil.ship = "EQUIPIER", secteur, navire or self.navire
        if secteur:
            profil.service = secteur.service
        profil.save()
        return user

    def chercher(self, terme, user=None):
        self.client.force_login(user or self.marin)
        return self.client.get(reverse("global-search"), {"q": terme})

    def test_normaliser_nul_largeur_nulle_et_separateurs(self):
        self.assertEqual(recherche.normaliser("ZE\x00BRE"), "ZEBRE")
        self.assertEqual(recherche.normaliser("a​"), "")
        self.assertEqual(recherche.normaliser("pompe\tà\nhuile"), "pompe à huile")

    def test_middleware_retire_le_nul_des_parametres(self):
        capture = {}

        def vue(request):
            capture["get"] = request.GET.get("q")
            return None

        usine = RequestFactory()
        SansNulMiddleware(vue)(usine.get("/x/?q=a%00b"))
        self.assertEqual(capture["get"], "ab")

    def test_page_de_recherche_accepte_un_nul(self):
        self.assertEqual(self.chercher("pompe%00").status_code, 200)
        self.assertContains(self.chercher("pom\x00pe"), "Fuite sur la pompe")

    def test_modules_desactives_exclus_de_la_page_de_recherche(self):
        self.assertContains(self.chercher("pompe"), "Fuite sur la pompe")
        ModuleActivation.objects.create(ship=self.navire, module="logistics", active=False)
        invalidate_cache(self.navire.id)
        self.assertNotContains(self.chercher("pompe"), "Fuite sur la pompe")

    def test_personnes_du_navire_avec_identifiant_et_email_sans_flotte_entiere(self):
        reponse = self.chercher("collegue_r")
        self.assertContains(reponse, "collegue_r@exemple.test")
        self.assertNotContains(self.chercher("etranger_r"), "etranger_r@exemple.test")
        self.assertContains(self.chercher("Rivière"), "collegue_r")

    def test_marin_sans_rattachement_ne_voit_pas_la_flotte(self):
        isole = self._marin("isole_r", None, "Iris", "Isolée")
        isole.profile.ship = None
        isole.profile.save()
        self.assertNotContains(self.chercher("Rivière", user=isole), "@exemple.test")


class DocumentsSansRattachementTests(TestCase):
    def test_marin_sans_rattachement_ne_voit_aucun_document(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from assets.models import AssetDocument
        navire = Ship.objects.create(name="Navire D", code="NVD")
        service = Service.objects.create(ship=navire, name="Service D")
        secteur = Sector.objects.create(service=service, name="Secteur D")
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=secteur)
        asset = Asset.objects.create(asset_type=type_asset, internal_id="POMPE-D", ship=navire, service=service, sector=secteur)
        AssetDocument.objects.create(asset=asset, name="Notice confidentielle", file=SimpleUploadedFile("n.txt", b"texte"))
        isole = User.objects.create_user(username="isole_d", password="pass")
        self.client.force_login(isole)
        self.assertNotContains(self.client.get(reverse("global-search"), {"q": "confidentielle"}), "Notice confidentielle")
        membre = User.objects.create_user(username="membre_d", password="pass")
        membre.profile.ship, membre.profile.service, membre.profile.sector = navire, service, secteur
        membre.profile.role = "EQUIPIER"
        membre.profile.save()
        self.client.force_login(membre)
        self.assertContains(self.client.get(reverse("global-search"), {"q": "confidentielle"}), "Notice confidentielle")
