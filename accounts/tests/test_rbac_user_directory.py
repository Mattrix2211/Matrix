from django.contrib.auth.models import User
from django.test import TestCase
from accounts.models import UserProfile, Roles
from org.models import Ship


class UserDirectoryRBACTests(TestCase):
    """Vérifie la faille corrigée sur UserDirectoryView.post() : avant correction,
    n'importe quel utilisateur connecté pouvait POST /users/ pour s'auto-promouvoir
    ou agir sur les comptes d'autrui, faute de tout contrôle de rôle.

    Tous les comptes sont rattachés au même navire (self.navire) : ces tests
    portent sur le contrôle de rôle (RBAC), pas sur le périmètre navire (déjà
    couvert par accounts/tests/test_scope_leak_users_web.py) — un COMMANDANT
    ou un ADMIN_NAVIRE sans navire rattaché à son propre profil ne verrait de
    toute façon personne (cf. matrix/core/scopes.py::perimetre_navire_q)."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire RBAC annuaire", code="NV-RBAC")

        self.equipier = User.objects.create_user(username="equipier1", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": Roles.EQUIPIER, "ship": self.navire}
        )

        self.commandant = User.objects.create_user(username="cmdt1", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant, defaults={"role": Roles.COMMANDANT, "ship": self.navire}
        )

        self.admin_navire = User.objects.create_user(username="adm1", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin_navire, defaults={"role": Roles.ADMIN_NAVIRE, "ship": self.navire}
        )

        self.autre = User.objects.create_user(username="autre1", password="pass")
        UserProfile.objects.update_or_create(
            user=self.autre, defaults={"role": Roles.EQUIPIER, "ship": self.navire}
        )

    def test_equipier_ne_peut_pas_sauto_promouvoir_master_admin(self):
        """Scénario d'exploitation trouvé par l'audit : un EQUIPIER poste
        action=bulk_update_role&role=MASTER_ADMIN sur son propre id."""
        self.client.login(username="equipier1", password="pass")
        r = self.client.post("/users/", {
            "action": "bulk_update_role",
            "selected_ids": [self.equipier.id],
            "role": "MASTER_ADMIN",
        })
        self.assertEqual(r.status_code, 403)
        self.equipier.profile.refresh_from_db()
        self.assertEqual(self.equipier.profile.role, Roles.EQUIPIER)

    def test_equipier_ne_peut_pas_creer_un_compte(self):
        self.client.login(username="equipier1", password="pass")
        nb_avant = User.objects.count()
        r = self.client.post("/users/", {
            "action": "create_user",
            "first_name": "Test",
            "last_name": "Intrus",
            "role": "MASTER_ADMIN",
        })
        self.assertEqual(r.status_code, 403)
        self.assertEqual(User.objects.count(), nb_avant)

    def test_equipier_ne_peut_pas_reinitialiser_un_mot_de_passe(self):
        self.client.login(username="equipier1", password="pass")
        ancien_hash = self.autre.password
        r = self.client.post("/users/", {
            "action": "set_password",
            "pk": self.autre.id,
            "password": "NouveauMotDePasse123!",
        })
        self.assertEqual(r.status_code, 403)
        self.autre.refresh_from_db()
        self.assertEqual(self.autre.password, ancien_hash)

    def test_equipier_ne_peut_pas_supprimer_des_comptes_en_masse(self):
        self.client.login(username="equipier1", password="pass")
        r = self.client.post("/users/", {
            "action": "bulk_delete_users",
            "selected_ids": [self.autre.id],
        })
        self.assertEqual(r.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.autre.id).exists())

    def test_equipier_ne_peut_pas_modifier_le_role_via_edit_user(self):
        self.client.login(username="equipier1", password="pass")
        r = self.client.post("/users/", {
            "action": "edit_user",
            "pk": self.autre.id,
            "username": self.autre.username,
            "role": "MASTER_ADMIN",
        })
        self.assertEqual(r.status_code, 403)
        self.autre.profile.refresh_from_db()
        self.assertEqual(self.autre.profile.role, Roles.EQUIPIER)

    def test_equipier_ne_peut_pas_rattacher_un_utilisateur_a_un_autre_navire(self):
        ship = Ship.objects.create(name="Navire test")
        self.client.login(username="equipier1", password="pass")
        r = self.client.post("/users/", {
            "action": "bulk_update_ship",
            "selected_ids": [self.autre.id],
            "ship_id": ship.id,
        })
        self.assertEqual(r.status_code, 403)
        self.autre.profile.refresh_from_db()
        self.assertEqual(self.autre.profile.ship, self.navire)

    def test_commandant_ne_peut_pas_sauto_promouvoir_admin_navire(self):
        """Le COMMANDANT franchit le seuil d'accès à la vue, mais la matrice
        ManageUsersPermission.MANAGE_MAP ne l'autorise pas à attribuer un rôle
        ADMIN_NAVIRE ou MASTER_ADMIN : la tentative doit être rejetée sans effet."""
        self.client.login(username="cmdt1", password="pass")
        r = self.client.post("/users/", {
            "action": "bulk_update_role",
            "selected_ids": [self.commandant.id],
            "role": "ADMIN_NAVIRE",
        })
        self.assertEqual(r.status_code, 302)
        self.commandant.profile.refresh_from_db()
        self.assertEqual(self.commandant.profile.role, Roles.COMMANDANT)

    def test_commandant_peut_gerer_un_role_dans_son_perimetre(self):
        """Le COMMANDANT reste habilité à attribuer un rôle dans son périmètre
        (cf. ManageUsersPermission.MANAGE_MAP), ce qui prouve que la correction
        n'a pas cassé la gestion courante des comptes."""
        self.client.login(username="cmdt1", password="pass")
        r = self.client.post("/users/", {
            "action": "bulk_update_role",
            "selected_ids": [self.autre.id],
            "role": "CHEF_SERVICE",
        })
        self.assertEqual(r.status_code, 302)
        self.autre.profile.refresh_from_db()
        self.assertEqual(self.autre.profile.role, Roles.CHEF_SERVICE)

    def test_admin_navire_peut_attribuer_le_role_master_admin(self):
        """L'ADMIN_NAVIRE conserve une gestion complète des comptes, y compris
        l'attribution du rôle MASTER_ADMIN (cf. ManageUsersPermission.MANAGE_MAP)."""
        self.client.login(username="adm1", password="pass")
        r = self.client.post("/users/", {
            "action": "bulk_update_role",
            "selected_ids": [self.autre.id],
            "role": "MASTER_ADMIN",
        })
        self.assertEqual(r.status_code, 302)
        self.autre.profile.refresh_from_db()
        self.assertEqual(self.autre.profile.role, Roles.MASTER_ADMIN)
