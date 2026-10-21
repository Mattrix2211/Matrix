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
    "/maintenance/gestion/occurrences/", "/quarts/reglages/", "/rondes/", "/rondes/modeles/", "/quarts/", "/formations/", "/calendar/",
    "/search/?q=FUITE", "/users/", "/absences/", "/taches/", "/demandes/", "/annonces/", "/programme/", "/postes/", "/documentation/", "/retex/", "/notifications/",
    "/assets/plan/", "/catalogue/", "/dashboard/comanav/",
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


class PerimetreATerreTests(TestCase):
    """Un utilisateur à terre (responsable de classe, sans navire) lit les bâtiments qu'il suit, jamais les autres."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.contenttypes.models import ContentType
        from org.models import ResponsableClasseNavire
        from threads.models import Thread

        def navire(code, classe):
            n = Ship.objects.create(name=f"Bât {code}", code=code, classe_navire=classe)
            s = Service.objects.create(ship=n, name=f"Serv {code}")
            sec = Sector.objects.create(service=s, name=f"Sect {code}")
            t = AssetType.objects.create(name=f"Type {code}", category="MCO", sector=sec)
            a = Asset.objects.create(asset_type=t, internal_id=f"A-{code}", designation=f"Mat {code}", ship=n, service=s, sector=sec)
            tk = CorrectiveTicket.objects.create(asset=a, description=f"Ticket {code}")
            fil = Thread.objects.create(content_type=ContentType.objects.get_for_model(CorrectiveTicket), object_id=str(tk.pk))
            piece = StockPiece.objects.create(reference=f"P-{code}", designation=f"Pièce {code}", quantite=3, ship=n, service=s, sector=sec)
            return n, a, tk, fil, piece, t

        cls.suivi = navire("SUI", "FREMM")
        cls.autre = navire("AUT", "FLO")
        cls.terre = User.objects.create_user(username="terre_classe", password="pass")
        cls.terre.profile.role = "CHEF_SECTION"
        cls.terre.profile.save()
        ResponsableClasseNavire.objects.create(classe_navire="FREMM", user=cls.terre)

    def _ids(self, url):
        self.client.force_login(self.terre)
        donnees = self.client.get(url).json()
        return {str(e["id"]) for e in (donnees["results"] if isinstance(donnees, dict) else donnees)}

    def test_api_materiel_borne_aux_batiments_suivis(self):
        ids = self._ids("/api/assets/assets/")
        self.assertIn(str(self.suivi[1].pk), ids)
        self.assertNotIn(str(self.autre[1].pk), ids)

    def test_api_fils_de_discussion_bornes_aux_batiments_suivis(self):
        ids = self._ids("/api/threads/threads/")
        self.assertIn(str(self.suivi[3].pk), ids)
        self.assertNotIn(str(self.autre[3].pk), ids)

    def test_stock_borne_aux_batiments_suivis_et_sans_prelevement_a_terre(self):
        self.client.force_login(self.terre)
        page = self.client.get(reverse("stock-piece-list")).content.decode()
        self.assertIn("Pièce SUI", page)
        self.assertNotIn("Pièce AUT", page)
        contexte = self.client.get(reverse("correctif-compte-rendu", args=[self.suivi[2].pk])).context
        self.assertEqual(list(contexte["pieces"]), [])

    def test_creation_de_materiel_refuse_hors_batiments_suivis(self):
        from assets.web_views import _org_dans_perimetre
        self.assertTrue(_org_dans_perimetre(self.terre, Ship, self.suivi[0].pk))
        self.assertFalse(_org_dans_perimetre(self.terre, Ship, self.autre[0].pk))
        self.assertFalse(_org_dans_perimetre(self._sans_rattachement(), Ship, self.suivi[0].pk))

    def test_emplacements_visibles_bornes_aux_batiments_suivis(self):
        from assets.models import Location
        from assets.web_views import _emplacements_visibles

        Location.objects.create(ship=self.suivi[0], name="Local suivi")
        Location.objects.create(ship=self.autre[0], name="Local autre")
        self.assertEqual(list(_emplacements_visibles(self.terre).values_list("name", flat=True)), ["Local suivi"])
        self.assertFalse(_emplacements_visibles(self._sans_rattachement()).exists())

    def test_dossier_de_materiel_d_un_autre_batiment_hors_perimetre(self):
        from assets.models import AssetFolder
        from assets.web_views import _materiel_hors_perimetre

        dossier = AssetFolder.objects.create(name="Dossier")
        Asset.objects.filter(pk=self.autre[1].pk).update(folder=dossier)
        self.assertTrue(_materiel_hors_perimetre(self.terre, dossier))
        self.assertTrue(_materiel_hors_perimetre(self._sans_rattachement(), dossier))

    def _sans_rattachement(self):
        return User.objects.create_user(username="sans_rattachement", password="pass")

    def test_utilisateurs_visibles_d_un_commandement_a_terre_sans_navire(self):
        from matrix.core.mixins import utilisateurs_visibles_par

        marin = User.objects.create_user(username="marin_suivi", password="pass")
        marin.profile.ship = self.suivi[0]
        marin.profile.save()
        etranger = User.objects.create_user(username="marin_autre", password="pass")
        etranger.profile.ship = self.autre[0]
        etranger.profile.save()
        self.terre.profile.role = "COMMANDANT"
        self.terre.profile.save()
        visibles = set(utilisateurs_visibles_par(self.terre).values_list("username", flat=True))
        self.assertIn("marin_suivi", visibles)
        self.assertNotIn("marin_autre", visibles)


class AssetTypeAutreBatimentTests(TestCase):
    """Un type de matériel est propre à un secteur : celui d'un autre bâtiment est refusé à la création et à la modification."""

    def setUp(self):
        def navire(code):
            n = Ship.objects.create(name=f"Bât {code}", code=code)
            s = Service.objects.create(ship=n, name=f"Serv {code}")
            sec = Sector.objects.create(service=s, name=f"Sect {code}")
            return n, s, sec, AssetType.objects.create(name=f"Type {code}", category="MCO", sector=sec)

        self.mien, self.voisin = navire("MIE"), navire("VOI")
        self.chef = User.objects.create_user(username="chef_mien", password="pass")
        profil = self.chef.profile
        profil.role, profil.ship = "ADMIN_NAVIRE", self.mien[0]
        profil.save()
        self.client.force_login(self.chef)

    def _poster(self, action, type_materiel, **extra):
        donnees = {
            "action": action, "asset_type_id": type_materiel.pk, "internal_id": "X-1", "designation": "Matériel test",
            "ship_id": self.mien[0].pk, "service_id": self.mien[1].pk, "sector_id": self.mien[2].pk, "status": "OK", "criticality": 1,
        }
        donnees.update(extra)
        return self.client.post(reverse("asset-list"), donnees)

    def test_creation_avec_type_d_un_autre_batiment_refusee(self):
        self._poster("create_asset", self.voisin[3])
        self.assertFalse(Asset.objects.filter(internal_id="X-1").exists())
        self._poster("create_asset", self.mien[3])
        self.assertTrue(Asset.objects.filter(internal_id="X-1", asset_type=self.mien[3]).exists())

    def test_modification_avec_type_d_un_autre_batiment_refusee(self):
        self._poster("create_asset", self.mien[3])
        asset = Asset.objects.get(internal_id="X-1")
        self._poster("edit_asset", self.voisin[3], pk=asset.pk)
        asset.refresh_from_db()
        self.assertEqual(asset.asset_type, self.mien[3])
