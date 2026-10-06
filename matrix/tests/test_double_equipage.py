"""Double équipage : relève par le commandant, lecture seule centrale, équipage obligatoire."""
import base64
import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.forms import UserProfileForm
from accounts.models import AuditLog, UserProfile
from org.models import Ship


class DoubleEquipageBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM", code="FR-DE", double_equipage=True, equipage_a_bord="A")
        self.cdt = self._marin("cdt", "COMMANDANT", "A")
        self.admin = self._marin("adm", "ADMIN_NAVIRE", "B")
        self.chef_terre = self._marin("chef", "CHEF_SERVICE", "B")
        self.bord = self._marin("bord", "EQUIPIER", "A")

    def _marin(self, nom, role, equipage):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage},
        )
        return user


class RelevePersonnelTests(DoubleEquipageBase):
    def _relever(self, nom, equipage="B"):
        self.client.login(username=nom, password="pass")
        return self.client.post(reverse("settings"), {"action": "changer_equipage", "equipage": equipage})

    def test_le_commandant_fait_la_releve_et_elle_est_tracee(self):
        self._relever("cdt")
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "B")
        trace = AuditLog.objects.get(action="changement_equipage")
        self.assertEqual(trace.actor, self.cdt)
        self.assertIn("equipage_a_bord=A -> B", trace.details)

    def test_les_autres_roles_ne_peuvent_pas(self):
        # L'administrateur d'unité, à terre ici, peut administrer mais pas faire la relève.
        for nom in ("adm", "chef", "bord"):
            self.assertEqual(self._relever(nom).status_code, 403)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "A")

    def test_equipage_inconnu_refuse(self):
        self._relever("cdt", "Z")
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "A")

    def test_le_commandant_d_un_autre_navire_ne_peut_pas(self):
        autre = Ship.objects.create(name="Autre", code="AU", double_equipage=True, equipage_a_bord="A")
        self.cdt.profile.ship = autre
        self.cdt.profile.save()
        self.client.login(username="cdt", password="pass")
        self.client.post(reverse("settings"), {"action": "changer_equipage", "equipage": "B", "ship_id": self.navire.pk})
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "A")

    def test_onglet_visible_commandant_et_admin_seulement(self):
        self.client.login(username="adm", password="pass")
        r = self.client.get(reverse("settings"), {"tab": "equipage"})
        self.assertContains(r, "Seul le commandant du bâtiment fait la relève")
        self.assertNotContains(r, "Faire la relève")
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("settings"), {"tab": "equipage"}), "Faire la relève")
        self.client.login(username="bord", password="pass")
        self.assertEqual(self.client.get(reverse("settings"), {"tab": "equipage"}).status_code, 403)

    def test_alerte_marins_sans_equipage(self):
        self._marin("sans", "EQUIPIER", "")
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("settings"), {"tab": "equipage"}), "1 marin sans équipage")

    def test_api_equipage_a_bord_reserve_au_commandant_et_tracee(self):
        url = reverse("ship-detail", args=[self.navire.pk])
        self.client.login(username="adm", password="pass")
        self.assertEqual(self.client.patch(url, {"equipage_a_bord": "B"}, content_type="application/json").status_code, 403)
        self.client.login(username="cdt", password="pass")
        self.assertEqual(self.client.patch(url, {"equipage_a_bord": "B"}, content_type="application/json").status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="changement_equipage", actor=self.cdt).exists())

    def test_admin_django_trace_le_changement(self):
        root = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self.client.login(username="root", password="pass")
        donnees = {"name": "FREMM", "code": "FR-DE", "type_unite": self.navire.type_unite, "classe_navire": "",
                   "double_equipage": "on", "equipage_a_bord": "B"}
        self.client.post(reverse("admin:org_ship_change", args=[self.navire.pk]), donnees)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "B")
        self.assertTrue(AuditLog.objects.filter(action="changement_equipage", actor=root).exists())


class LectureSeuleCentraleTests(DoubleEquipageBase):
    # Écritures du bâtiment prises dans chaque module : le garde agit avant la vue.
    ECRITURES_WEB = (
        ("ticket-transition", [uuid.uuid4()]),
        ("ticket-assign", [uuid.uuid4()]),
        ("ticket-comment-create", [uuid.uuid4()]),
        ("part-request-create", [uuid.uuid4()]),
        ("anomalie-create", []),
        ("anomalie-transition", [1]),
        ("ronde-lancer", [1]),
        ("ronde-terminer", [1]),
        ("echange-proposer", [1]),
        ("quarts-reglages", []),
        ("formation-valider", []),
        ("formation-list", []),
        ("asset-list", []),
        ("asset-import", []),
        ("pret-appareillage", []),
        ("calendar-event-move", []),
    )

    def test_equipage_a_terre_refuse_toutes_les_ecritures_web(self):
        for nom in ("chef", "adm"):
            self.client.login(username=nom, password="pass")
            for vue, args in self.ECRITURES_WEB:
                with self.subTest(nom=nom, vue=vue):
                    self.assertEqual(self.client.post(reverse(vue, args=args), {}).status_code, 403)

    def test_equipage_a_bord_non_bloque(self):
        self.client.login(username="cdt", password="pass")
        for vue, args in self.ECRITURES_WEB:
            with self.subTest(vue=vue):
                reponse = self.client.post(reverse(vue, args=args), {})
                self.assertNotIn(b"Lecture seule : votre", reponse.content)

    def test_equipage_a_terre_refuse_les_ecritures_api(self):
        self.client.login(username="chef", password="pass")
        for url in ("/api/logistics/tickets/", "/api/maintenance/occurrences/", "/api/threads/messages/", "/api/assets/assets/"):
            with self.subTest(url=url):
                r = self.client.post(url, {}, content_type="application/json")
                self.assertEqual(r.status_code, 403)
                self.assertIn("Lecture seule", r.json()["detail"])

    def test_authentification_basic_ne_contourne_pas_le_garde(self):
        jeton = base64.b64encode(b"chef:pass").decode()
        r = self.client.post("/api/logistics/tickets/", {}, content_type="application/json", HTTP_AUTHORIZATION=f"Basic {jeton}")
        self.assertEqual(r.status_code, 403)
        self.assertIn("Lecture seule", r.json()["detail"])

    def test_lecture_et_reglages_restent_possibles_a_terre(self):
        self.client.login(username="adm", password="pass")
        self.assertEqual(self.client.get("/api/logistics/tickets/").status_code, 200)
        r = self.client.post(reverse("settings"), {"action": "update_notification_time", "notification_time": "07:00", "notification_time_soir": "19:00"})
        self.assertEqual(r.status_code, 302)

    def test_bandeau_sur_toutes_les_pages_a_terre_seulement(self):
        self.client.login(username="chef", password="pass")
        for vue in ("ticket-list", "asset-list", "rondes-index", "formation-list"):
            with self.subTest(vue=vue):
                self.assertContains(self.client.get(reverse(vue)), "Lecture seule — Équipage B à terre")
        self.client.login(username="bord", password="pass")
        self.assertNotContains(self.client.get(reverse("ticket-list")), "Lecture seule")


class EquipageObligatoireTests(DoubleEquipageBase):
    def test_formulaire_exige_l_equipage_sur_double_equipage(self):
        form = UserProfileForm({"role": "EQUIPIER", "ship": self.navire.pk, "equipage": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("equipage", form.errors)

    def test_formulaire_sans_double_equipage_non_concerne(self):
        simple = Ship.objects.create(name="Simple", code="SI")
        form = UserProfileForm({"role": "EQUIPIER", "ship": simple.pk, "equipage": ""})
        self.assertNotIn("equipage", form.errors)

    def test_api_refuse_un_profil_sans_equipage_mais_garde_les_existants(self):
        sans = self._marin("sans", "EQUIPIER", "")
        root = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self.client.login(username="root", password="pass")
        url = reverse("userprofile-detail", args=[sans.profile.pk])
        # Modifier un autre champ d'un profil existant sans équipage reste possible.
        self.assertEqual(self.client.patch(url, {"grade": "QM1"}, content_type="application/json").status_code, 200)
        # Changer d'unité ou d'équipage impose la valeur.
        r = self.client.patch(url, {"ship": self.navire.pk}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("equipage", r.json())

    def test_annuaire_cree_avec_equipage_et_refuse_sans(self):
        self.client.login(username="cdt", password="pass")
        base = {"action": "create_user", "first_name": "Jean", "last_name": "Test", "role": "EQUIPIER", "ship_id": self.navire.pk}
        self.client.post(reverse("user-directory"), base)
        self.assertFalse(User.objects.filter(last_name="Test").exists())
        self.client.post(reverse("user-directory"), {**base, "equipage": "B"})
        self.assertEqual(User.objects.get(last_name="Test").profile.equipage, "B")

    def test_annuaire_signale_les_marins_sans_equipage(self):
        self._marin("sans", "EQUIPIER", "")
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("user-directory")), "1 marin sans équipage")
