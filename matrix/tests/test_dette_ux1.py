"""Dette UX-1 : la barre latérale n'est pas calculée pour un fragment HTMX ; le mode lecture seule reste connu des fragments."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from org.models import Ship


class FragmentsHtmxTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bâtiment double", code="BD", double_equipage=True, equipage_a_bord="A")
        self.terre = User.objects.create_user(username="marin_terre", password="pass")
        self.terre.profile.ship, self.terre.profile.equipage = self.navire, "B"
        self.terre.profile.save()
        self.client.force_login(self.terre)

    def test_page_complete_et_fragment(self):
        complete = self.client.get(reverse("notifications-centre"))
        self.assertIn("navigation_laterale", complete.context)
        fragment = self.client.get(reverse("notifications-panneau"), HTTP_HX_REQUEST="true")
        self.assertNotIn("navigation_laterale", fragment.context)
        self.assertEqual(fragment.context["equipage_a_terre"], "B")
        self.assertNotIn("batiment_courant", fragment.context)


class EntreesTransversesTests(TestCase):
    def test_master_admin_sans_specialite_ni_classe_ne_voit_pas_les_entrees(self):
        from dashboard.templatetags.dashboard_extras import peut_voir_dashboard_classe_navire, peut_voir_dashboard_specialite

        admin = User.objects.create_superuser("root", password="pass")
        self.assertFalse(peut_voir_dashboard_specialite(admin))
        self.assertFalse(peut_voir_dashboard_classe_navire(admin))
        Ship.objects.create(name="Classé", code="CL", classe_navire="FREMM")
        self.assertTrue(peut_voir_dashboard_classe_navire(admin))


class BatimentCourantTests(TestCase):
    """Le bâtiment choisi borne les listes d'un utilisateur à terre ; sans choix, tout son périmètre."""

    def setUp(self):
        from logistics.models import Anomalie
        from matrix.core.contexte_batiment import CLE_SESSION

        self.cle = CLE_SESSION
        self.alsace = Ship.objects.create(name="Alsace", code="D656")
        self.provence = Ship.objects.create(name="Provence", code="D652")
        Anomalie.objects.create(titre="Fuite ALSACE-X", ship=self.alsace)
        Anomalie.objects.create(titre="Fuite PROVENCE-X", ship=self.provence)
        self.admin = User.objects.create_superuser("terre_admin", password="pass")
        self.client.force_login(self.admin)

    def _liste(self):
        return self.client.get(reverse("anomalie-list") + "?vue=perimetre").content.decode()

    def test_sans_choix_toute_la_flotte_puis_filtre_sur_le_batiment_courant(self):
        page = self._liste()
        self.assertTrue("ALSACE-X" in page)
        self.assertTrue("PROVENCE-X" in page)
        session = self.client.session
        session[self.cle] = self.provence.pk
        session.save()
        page = self._liste()
        self.assertTrue("PROVENCE-X" in page)
        self.assertFalse("ALSACE-X" in page)

    def test_choix_hors_perimetre_ignore(self):
        marin = User.objects.create_user("simple", password="pass")
        marin.profile.ship, marin.profile.role = self.alsace, "COMMANDANT"
        marin.profile.save()
        self.client.force_login(marin)
        session = self.client.session
        session[self.cle] = self.provence.pk
        session.save()
        page = self._liste()
        self.assertTrue("ALSACE-X" in page)
        self.assertFalse("PROVENCE-X" in page)


class VisibiliteChefDeServiceTests(TestCase):
    def test_chef_de_service_voit_un_marin_rattache_au_seul_secteur(self):
        from matrix.core.mixins import utilisateurs_visibles_par
        from org.models import Sector, Service

        navire = Ship.objects.create(name="Visibilité", code="VI")
        service = Service.objects.create(ship=navire, name="Énergie")
        secteur = Sector.objects.create(service=service, name="Propulsion")
        autre_service = Service.objects.create(ship=navire, name="Pont")
        chef = User.objects.create_user("chef_vis", password="pass")
        chef.profile.role, chef.profile.ship, chef.profile.service = "CHEF_SERVICE", navire, service
        chef.profile.save()
        marin = User.objects.create_user("marin_secteur", password="pass")
        marin.profile.ship, marin.profile.sector = navire, secteur
        marin.profile.save()
        voisin = User.objects.create_user("marin_pont", password="pass")
        voisin.profile.ship, voisin.profile.service = navire, autre_service
        voisin.profile.save()
        visibles = set(utilisateurs_visibles_par(chef))
        self.assertIn(marin, visibles)
        self.assertNotIn(voisin, visibles)


    def test_marin_rattache_au_seul_navire_ne_voit_pas_tout_le_batiment(self):
        from matrix.core.mixins import utilisateurs_visibles_par
        from org.models import Service

        navire = Ship.objects.create(name="Navire seul", code="NS")
        service = Service.objects.create(ship=navire, name="Pont")
        simple = User.objects.create_user("simple_navire", password="pass")
        simple.profile.role, simple.profile.ship = "CHEF_SECTION", navire
        simple.profile.save()
        autre = User.objects.create_user("autre_service", password="pass")
        autre.profile.service = service  # rattaché au service seul, sans champ navire direct
        autre.profile.save()
        self.assertNotIn(autre, set(utilisateurs_visibles_par(simple)))


class BandeauLectureSeuleTests(TestCase):
    """Le bandeau « Lecture seule » est permanent pour l'équipage à terre, sur toutes les pages."""

    PAGES = ["/", "/assets/", "/logistics/tickets/", "/quarts/", "/formations/", "/calendar/", "/taches/", "/annonces/", "/notifications/"]

    def setUp(self):
        self.navire = Ship.objects.create(name="Bâtiment double", code="BD2", double_equipage=True, equipage_a_bord="A")
        self.terre = User.objects.create_user(username="marin_b", password="pass")
        self.terre.profile.ship, self.terre.profile.equipage = self.navire, "B"
        self.terre.profile.save()
        self.bord = User.objects.create_user(username="marin_a", password="pass")
        self.bord.profile.ship, self.bord.profile.equipage = self.navire, "A"
        self.bord.profile.save()

    def test_bandeau_sur_chaque_page_a_terre_et_absent_a_bord(self):
        for page in self.PAGES:
            with self.subTest(page=page):
                self.client.force_login(self.terre)
                self.assertContains(self.client.get(page, follow=True), "Lecture seule — Équipage B à terre")
                self.client.force_login(self.bord)
                self.assertNotContains(self.client.get(page, follow=True), "Lecture seule — Équipage")


class EffectifsParEquipageTests(TestCase):
    def test_parametres_listent_les_marins_par_equipage(self):
        navire = Ship.objects.create(name="Bâtiment double", code="BD3", double_equipage=True, equipage_a_bord="A")
        admin = User.objects.create_user(username="adm", password="pass")
        admin.profile.role, admin.profile.ship, admin.profile.equipage = "ADMIN_NAVIRE", navire, "A"
        admin.profile.save()
        marin = User.objects.create_user(username="marin_terre_b", password="pass")
        marin.profile.ship, marin.profile.equipage = navire, "B"
        marin.profile.save()
        self.client.force_login(admin)
        page = self.client.get(f"/parametre/?tab=equipage&ship={navire.pk}")
        self.assertContains(page, "Effectifs par équipage")
        self.assertEqual({e["code"]: [m.username for m in e["marins"]] for e in page.context["equipage_effectifs"]},
                         {"A": ["adm"], "B": ["marin_terre_b"]})
