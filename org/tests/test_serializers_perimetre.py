"""Audit des serializers de l'app org (tâche Notion « [SEC] Audit des serializers,
suite 2 ») : champs explicites, références croisées refusées hors périmètre (400),
champs posés par le serveur en lecture seule."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Roles, UserProfile
from org.models import Equipage, Section, Sector, SectorConfig, Service, Ship


def _client(nom, role, **profil):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, **profil})
    client = APIClient()
    client.login(username=nom, password="pass")
    return client


class SerializersOrgPerimetreTests(TestCase):
    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A", code="OA")
        self.ship_b = Ship.objects.create(name="Navire B", code="OB")
        self.service_a1 = Service.objects.create(ship=self.ship_a, name="Pont")
        self.service_a2 = Service.objects.create(ship=self.ship_a, name="Machine")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Pont B")
        self.secteur_a1 = Sector.objects.create(service=self.service_a1, name="Manoeuvre")
        self.secteur_a2 = Sector.objects.create(service=self.service_a2, name="Propulsion")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Manoeuvre B")
        self.admin_a = _client("admin_org_a", Roles.ADMIN_NAVIRE, ship=self.ship_a)
        self.chef_secteur = _client(
            "chef_secteur_org_a", Roles.CHEF_SECTEUR, ship=self.ship_a,
            service=self.service_a1, sector=self.secteur_a1,
        )
        self.master = _client("master_org", Roles.MASTER_ADMIN)

    # --- références croisées hors périmètre ---------------------------------

    def test_secteur_sur_un_service_d_un_autre_navire_refuse(self):
        r = self.admin_a.post("/api/org/sectors/", {"service": self.service_b.pk, "name": "Intrus"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("service", r.data)
        self.assertFalse(Sector.objects.filter(name="Intrus").exists())

    def test_section_sur_un_secteur_d_un_autre_navire_refusee(self):
        r = self.admin_a.post("/api/org/sections/", {"sector": self.secteur_b.pk, "name": "Intrus"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("sector", r.data)

    def test_deplacement_d_une_section_vers_un_autre_navire_refuse(self):
        section = Section.objects.create(sector=self.secteur_a1, name="Quart")
        r = self.admin_a.patch(f"/api/org/sections/{section.pk}/", {"sector": self.secteur_b.pk}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        section.refresh_from_db()
        self.assertEqual(section.sector, self.secteur_a1)

    def test_configuration_sur_un_secteur_d_un_autre_navire_refusee(self):
        r = self.admin_a.post("/api/org/sector-configs/", {"sector": self.secteur_b.pk}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(SectorConfig.objects.exists())

    def test_service_sur_un_autre_navire_refuse(self):
        r = self.admin_a.post("/api/org/services/", {"ship": self.ship_b.pk, "name": "Intrus"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("ship", r.data)

    def test_chef_de_secteur_ne_peut_pas_creer_dans_un_autre_service_de_son_navire(self):
        r = self.chef_secteur.post(
            "/api/org/sections/", {"sector": self.secteur_a2.pk, "name": "Hors service"}, format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        r = self.chef_secteur.post(
            "/api/org/sections/", {"sector": self.secteur_a1.pk, "name": "Dans son secteur"}, format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_administrateur_general_sans_perimetre_non_restreint(self):
        r = self.master.post("/api/org/sectors/", {"service": self.service_b.pk, "name": "Légitime"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    # --- champs posés par le serveur ----------------------------------------

    def test_equipage_du_secteur_et_de_la_section_non_forgeable(self):
        ship = Ship.objects.create(name="FREMM", code="FR", double_equipage=True)
        equipage_bleu = Equipage.objects.create(ship=ship, nom="Bleu")
        equipage_rouge = Equipage.objects.create(ship=ship, nom="Rouge")
        service = Service.objects.create(ship=ship, name="Opérations", equipage=equipage_bleu)
        r = self.master.post(
            "/api/org/sectors/", {"service": service.pk, "name": "Veille", "equipage": equipage_rouge.pk}, format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Sector.objects.get(pk=r.data["id"]).equipage, equipage_bleu)
        r = self.master.post(
            "/api/org/sections/",
            {"sector": r.data["id"], "name": "Quart", "equipage": equipage_rouge.pk}, format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Section.objects.get(pk=r.data["id"]).equipage, equipage_bleu)

    def test_double_equipage_du_navire_non_modifiable_par_l_api(self):
        equipage = Equipage.objects.create(ship=self.ship_a, nom="Bleu")
        r = self.admin_a.patch(
            f"/api/org/ships/{self.ship_a.pk}/",
            {"double_equipage": True, "equipage_a_bord": equipage.pk, "classe_navire": "FDA"}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.ship_a.refresh_from_db()
        self.assertFalse(self.ship_a.double_equipage)
        self.assertIsNone(self.ship_a.equipage_a_bord)
        self.assertEqual(self.ship_a.classe_navire, "FDA")

    # --- champs exposés -----------------------------------------------------

    def test_champs_explicites_exposes(self):
        r = self.admin_a.get(f"/api/org/ships/{self.ship_a.pk}/")
        self.assertEqual(
            set(r.data),
            {"id", "name", "code", "type_unite", "classe_navire", "capacite_aviation", "double_equipage",
             "equipage_a_bord", "equipage_releve", "date_releve", "archived", "created_at", "updated_at"},
        )
        r = self.admin_a.get(f"/api/org/sectors/{self.secteur_a1.pk}/")
        self.assertEqual(
            set(r.data), {"id", "service", "name", "color", "equipage", "archived", "created_at", "updated_at"},
        )
