"""Un marin sans rattachement organisationnel ne doit lire aucune donnée d'un navire, sur aucune page ni API."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from assets.models import Asset, AssetDocument, AssetType, Installation
from logistics.models import Anomalie, CorrectiveTicket, StockPiece
from maintenance.models import MaintenancePlan
from org.models import Sector, Section, Service, Ship
from rondes.models import Ronde, RondeModele

MARQUEUR = "FUITEZZ"
PAGES = [
    "/", "/assets/", "/installations/", "/logistics/tickets/", "/logistics/anomalies/", "/logistics/stock/",
    "/maintenance/gestion/plans/",
    "/maintenance/gestion/occurrences/", "/rondes/", "/rondes/modeles/", "/quarts/", "/formations/", "/calendar/",
    "/search/?q=FUITE", "/users/", "/absences/", "/taches/", "/notifications/",
    "/assets/plan/", "/catalogue/",
]
RACINES_API = ["accounts", "org", "assets", "maintenance", "logistics", "training", "threads", "notifications", "dashboard"]


class FuitesSansRattachementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        navire = Ship.objects.create(name=f"{MARQUEUR} navire", code="FZZ")
        service = Service.objects.create(ship=navire, name=f"{MARQUEUR} service")
        secteur = Sector.objects.create(service=service, name=f"{MARQUEUR} secteur")
        Section.objects.create(sector=secteur, name=f"{MARQUEUR} section")
        type_asset = AssetType.objects.create(name=f"{MARQUEUR} type", category="MCO", sector=secteur)
        asset = Asset.objects.create(asset_type=type_asset, internal_id=f"{MARQUEUR}-A", designation=f"{MARQUEUR} matériel",
                                     ship=navire, service=service, sector=secteur)
        Installation.objects.create(designation=f"{MARQUEUR} installation", ship=navire, service=service, sector=secteur)
        CorrectiveTicket.objects.create(asset=asset, description=f"{MARQUEUR} ticket")
        auteur = User.objects.create_user(username=f"{MARQUEUR.lower()}_auteur", password="pass", first_name=MARQUEUR)
        auteur.profile.ship, auteur.profile.service, auteur.profile.sector = navire, service, secteur
        auteur.profile.save()
        Anomalie.objects.create(titre=f"{MARQUEUR} anomalie", created_by=auteur, ship=navire, service=service, sector=secteur)
        AssetDocument.objects.create(asset=asset, name=f"{MARQUEUR} document", file=SimpleUploadedFile("d.txt", b"texte"))
        StockPiece.objects.create(reference=f"{MARQUEUR}-S", designation=f"{MARQUEUR} pièce", ship=navire, service=service, sector=secteur)
        MaintenancePlan.objects.create(scope="ASSET", asset=asset, name=f"{MARQUEUR} plan")
        modele = RondeModele.objects.create(nom=f"{MARQUEUR} modèle de ronde", ship=navire, sector=secteur)
        Ronde.objects.create(modele=modele, nom=f"{MARQUEUR} ronde", ship=navire, sector=secteur, date_prevue=date.today())

    def _isole(self, role):
        user = User.objects.create_user(username=f"isole_{role.lower()}", password="pass")
        user.profile.role = role
        user.profile.save()
        return user

    def _autre_navire(self, role):
        navire = Ship.objects.create(name=f"Autre navire {role}", code="A" + role.replace("_", "")[-6:])
        service = Service.objects.create(ship=navire, name="Autre service")
        secteur = Sector.objects.create(service=service, name="Autre secteur")
        section = Section.objects.create(sector=secteur, name="Autre section")
        user = User.objects.create_user(username=f"voisin_{role.lower()}", password="pass")
        profil = user.profile
        profil.role, profil.ship, profil.service, profil.sector, profil.section = role, navire, service, secteur, section
        profil.save()
        return user

    def _contenu(self, url):
        reponse = self.client.get(url)
        return reponse.content.decode("utf-8", "ignore")

    def _urls_api(self):
        urls = []
        for racine in RACINES_API:
            reponse = self.client.get(f"/api/{racine}/")
            if reponse.status_code == 200 and reponse["Content-Type"].startswith("application/json"):
                urls.extend(reponse.json().values())
        return urls

    def _verifier(self, role, utilisateur=None):
        self.client.force_login(utilisateur or self._isole(role))
        fuites = []
        for url in PAGES + self._urls_api():
            contenu = self._contenu(url)
            if MARQUEUR in contenu:
                debut = contenu.index(MARQUEUR)
                fuites.append((url, contenu[max(0, debut - 60):debut + 40].replace("\n", " ")))
        debut, fin = date.today() - timedelta(days=30), date.today() + timedelta(days=30)
        evenements = self._contenu(f"{reverse('calendar-events')}?start={debut}&end={fin}")
        if MARQUEUR in evenements:
            fuites.append("calendar-events")
        self.assertEqual(fuites, [], f"fuites pour {role}")

    def test_equipier_sans_rattachement(self):
        self._verifier("EQUIPIER")

    def test_chef_de_section_sans_rattachement(self):
        self._verifier("CHEF_SECTION")

    def test_chef_de_service_sans_rattachement(self):
        self._verifier("CHEF_SERVICE")

    def test_commandant_sans_navire(self):
        self._verifier("COMMANDANT")

    def test_chefs_d_un_autre_navire(self):
        for role in ("EQUIPIER", "CHEF_SECTION", "CHEF_SECTEUR", "CHEF_SERVICE", "COMMANDANT"):
            with self.subTest(role=role):
                self._verifier(role, self._autre_navire(role))

    def test_administrateur_general_voit_toujours_la_flotte(self):
        self.client.force_login(self._isole("MASTER_ADMIN"))
        for url in ("/assets/", "/installations/", "/logistics/stock/", "/logistics/anomalies/?vue=perimetre"):
            with self.subTest(url=url):
                self.assertIn(MARQUEUR, self._contenu(url))
