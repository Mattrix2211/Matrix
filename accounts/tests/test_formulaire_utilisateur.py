"""Création et édition d'un utilisateur en page complète (plus de modale) ; annuaire en tableau."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Roles, RoleAvailability, UserProfile
from org.models import Ship


class FormulaireUtilisateurTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire formulaire", code="NV-FRM")
        self.autre_navire = Ship.objects.create(name="Autre navire", code="NV-AUT")
        self.cdt = self._marin("cdt_frm", Roles.COMMANDANT, self.navire)
        self.second = self._marin("second_frm", Roles.COMMANDANT_EN_SECOND, self.navire)
        self.chef = self._marin("chef_frm", Roles.CHEF_SERVICE, self.navire)
        self.marin = self._marin("marin_frm", Roles.EQUIPIER, self.navire)
        self.etranger = self._marin("etranger_frm", Roles.EQUIPIER, self.autre_navire)

    @staticmethod
    def _marin(nom, role, navire):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": navire})
        return user

    def test_pages_reservees_aux_commandants(self):
        url = reverse("user-create")
        self.assertEqual(self.client.get(url).status_code, 302)
        for nom in ("second_frm", "chef_frm"):
            self.client.login(username=nom, password="pass")
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.get(reverse("user-edit", args=[self.marin.pk])).status_code, 403)

    def test_creation_en_page_complete_puis_enregistrement_par_l_annuaire(self):
        self.client.login(username="cdt_frm", password="pass")
        page = self.client.get(reverse("user-create") + f"?ship={self.navire.pk}")
        self.assertContains(page, 'value="create_user"')
        self.assertContains(page, f'action="{reverse("user-directory")}"')
        self.assertNotContains(page, "createUserModal")
        self.client.post(reverse("user-directory"), {
            "action": "create_user", "first_name": "Anne", "last_name": "Page",
            "role": Roles.EQUIPIER, "ship_id": self.navire.pk,
        })
        self.assertEqual(User.objects.get(last_name="Page").profile.ship, self.navire)

    def test_edition_preremplie(self):
        UserProfile.objects.filter(user=self.marin).update(matricule="M123")
        self.client.login(username="cdt_frm", password="pass")
        page = self.client.get(reverse("user-edit", args=[self.marin.pk]))
        self.assertContains(page, 'value="edit_user"')
        self.assertContains(page, 'value="M123"')
        self.assertContains(page, f'<option value="{self.navire.pk}" selected>')

    def test_edition_hors_perimetre_introuvable(self):
        self.client.login(username="cdt_frm", password="pass")
        self.assertEqual(self.client.get(reverse("user-edit", args=[self.etranger.pk])).status_code, 404)

    def test_role_hors_liste_propose_sans_etre_modifie(self):
        # Un rôle désactivé n'est pas écrasé par le premier choix de la liste
        RoleAvailability.objects.create(code=Roles.ADMIN_NAVIRE, active=False)
        admin = self._marin("adm_frm", Roles.ADMIN_NAVIRE, self.navire)
        self.client.login(username="cdt_frm", password="pass")
        page = self.client.get(reverse("user-edit", args=[admin.pk]))
        self.assertContains(page, '<option value="" selected>Administrateur d&#x27;unité (inchangé)</option>', html=False)

    def test_equipage_verrouille_pour_soi_meme(self):
        self.client.login(username="cdt_frm", password="pass")
        soi = self.client.get(reverse("user-edit", args=[self.cdt.pk]))
        self.assertTrue(soi.context["equipage_verrouille"])
        autre = self.client.get(reverse("user-edit", args=[self.marin.pk]))
        self.assertFalse(autre.context["equipage_verrouille"])

    def test_anti_elevation_de_role_toujours_applique_par_le_serveur(self):
        self.client.login(username="cdt_frm", password="pass")
        self.client.post(reverse("user-directory"), {
            "action": "edit_user", "pk": self.marin.pk, "role": Roles.ADMIN_NAVIRE, "ship_id": self.navire.pk,
        })
        self.marin.profile.refresh_from_db()
        self.assertEqual(self.marin.profile.role, Roles.EQUIPIER)


class AnnuaireTableauTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire tableau", code="NV-TAB")
        self.cdt = User.objects.create_user(username="cdt_tab", password="pass", first_name="Paul", last_name="Durand")
        UserProfile.objects.update_or_create(user=self.cdt, defaults={"role": Roles.COMMANDANT, "ship": self.navire})
        self.marin = User.objects.create_user(username="marin_tab", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": Roles.EQUIPIER, "ship": self.navire})

    def test_actions_par_ligne_dans_un_menu_et_barre_de_selection_masquee(self):
        self.client.login(username="cdt_tab", password="pass")
        page = self.client.get(reverse("user-directory"))
        self.assertContains(page, "mx-menu__declencheur")
        self.assertContains(page, reverse("user-edit", args=[self.marin.pk]))
        self.assertContains(page, 'id="barreSelection"')
        self.assertContains(page, 'class="mx-barre-selection d-none"')
        self.assertContains(page, "Paul Durand")
        self.assertNotContains(page, 'id="editUserModal"')
        self.assertNotContains(page, 'id="createUserModal"')
        self.assertContains(page, 'data-tri="0"')


class AnnuaireEquipageATerreTests(TestCase):
    def test_commandant_a_terre_consulte_sans_actions_ni_creation(self):
        navire = Ship.objects.create(name="Navire terre", code="NV-TER", double_equipage=True, equipage_a_bord="A")
        cdt = User.objects.create_user(username="cdt_terre", password="pass")
        UserProfile.objects.update_or_create(
            user=cdt, defaults={"role": Roles.COMMANDANT, "ship": navire, "equipage": "B"},
        )
        self.client.login(username="cdt_terre", password="pass")
        page = self.client.get(reverse("user-directory"))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "/users/nouveau/")
        self.assertNotContains(page, "mx-menu__declencheur")
        formulaire = self.client.get(reverse("user-edit", args=[cdt.pk]))
        self.assertContains(formulaire, "Lecture seule")
        self.assertNotContains(formulaire, "Enregistrer")
        self.assertNotContains(formulaire, "Créer")
