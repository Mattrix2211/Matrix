"""Tests unitaires directs de matrix/core/permissions.py.

Ces classes de permission DRF (RolePermission, IsAuthorOrReadOnly,
ManageUsersPermission) sont la fondation du RBAC de toute l'application, mais
n'étaient jusqu'ici testées qu'indirectement via les tests RBAC de chaque app
(ex. maintenance/tests/test_rbac_occurrence.py). Ce fichier les teste
isolément, sans passer par une vue complète.
"""
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from accounts.models import UserProfile, Roles
from assets.models import Asset, AssetType
from matrix.core.permissions import RolePermission, IsAuthorOrReadOnly, ManageUsersPermission
from matrix.core.roles import RoleLevel
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Ship, Service, Sector


def fake_request(method, user, data=None):
    """Construit un objet minimal imitant les attributs de Request utilisés
    par les classes de permission (method, user, data) — pas besoin d'un
    vrai cycle HTTP DRF pour tester la logique d'autorisation en isolation."""
    return SimpleNamespace(method=method, user=user, data=data or {})


class RolePermissionTests(TestCase):
    def setUp(self):
        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": Roles.EQUIPIER})
        self.equipier.refresh_from_db()

        self.chef_section = User.objects.create_user(username="chef_section", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_section, defaults={"role": Roles.CHEF_SECTION})
        self.chef_section.refresh_from_db()

        self.superuser = User.objects.create_superuser(username="super", password="pass", email="s@s.fr")

        self.permission = RolePermission()
        self.view = SimpleNamespace()  # pas d'override min_role_level_write : utilise CHEF_SECTION par défaut

    def test_lecture_autorisee_pour_tout_utilisateur_connecte(self):
        req = fake_request("GET", self.equipier)
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_lecture_refusee_si_non_connecte(self):
        req = fake_request("GET", AnonymousUser())
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_ecriture_refusee_sous_le_seuil_par_defaut(self):
        req = fake_request("POST", self.equipier)
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_ecriture_autorisee_au_seuil_par_defaut(self):
        req = fake_request("POST", self.chef_section)
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_superutilisateur_toujours_autorise_en_ecriture(self):
        req = fake_request("DELETE", self.superuser)
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_seuil_personnalise_par_vue(self):
        vue_ouverte = SimpleNamespace(min_role_level_write=RoleLevel.EQUIPIER)
        req = fake_request("POST", self.equipier)
        self.assertTrue(self.permission.has_permission(req, vue_ouverte))

    def test_object_permission_lecture_toujours_autorisee(self):
        occ = MaintenanceOccurrence(scheduled_for="2026-01-01")
        req = fake_request("GET", self.equipier)
        self.assertTrue(self.permission.has_object_permission(req, self.view, occ))

    def test_object_permission_maintenanceoccurrence_autorisee_pour_lassigne(self):
        """Cas particulier documenté dans le code : un EQUIPIER assigné à une
        occurrence de maintenance peut la modifier même sous le seuil CHEF_SECTION."""
        ship = Ship.objects.create(name="Navire X", code="NX")
        service = Service.objects.create(ship=ship, name="Service X")
        sector = Sector.objects.create(service=service, name="Secteur X")
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=sector)
        asset = Asset.objects.create(asset_type=asset_type, ship=ship, service=service, sector=sector)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle", every_n_days=365)
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=asset, scheduled_for="2026-01-01")
        occ.assignees.add(self.equipier)

        req = fake_request("POST", self.equipier)
        self.assertTrue(self.permission.has_object_permission(req, self.view, occ))

    def test_object_permission_maintenanceoccurrence_refusee_pour_un_tiers(self):
        ship = Ship.objects.create(name="Navire Y", code="NY")
        service = Service.objects.create(ship=ship, name="Service Y")
        sector = Sector.objects.create(service=service, name="Secteur Y")
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=sector)
        asset = Asset.objects.create(asset_type=asset_type, ship=ship, service=service, sector=sector)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle", every_n_days=365)
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=asset, scheduled_for="2026-01-01")
        # L'équipier n'est pas assigné à cette occurrence.

        req = fake_request("POST", self.equipier)
        self.assertFalse(self.permission.has_object_permission(req, self.view, occ))


class IsAuthorOrReadOnlyTests(TestCase):
    def setUp(self):
        self.auteur = User.objects.create_user(username="auteur", password="pass")
        self.autre = User.objects.create_user(username="autre", password="pass")
        self.permission = IsAuthorOrReadOnly()
        self.view = SimpleNamespace()

    def test_lecture_autorisee_pour_tout_utilisateur_connecte(self):
        req = fake_request("GET", self.autre)
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_lecture_refusee_si_non_connecte(self):
        req = fake_request("GET", AnonymousUser())
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_ecriture_autorisee_pour_lauteur(self):
        obj = SimpleNamespace(author=self.auteur)
        req = fake_request("PATCH", self.auteur)
        self.assertTrue(self.permission.has_object_permission(req, self.view, obj))

    def test_ecriture_refusee_pour_un_tiers(self):
        obj = SimpleNamespace(author=self.auteur)
        req = fake_request("PATCH", self.autre)
        self.assertFalse(self.permission.has_object_permission(req, self.view, obj))


class ManageUsersPermissionTests(TestCase):
    def setUp(self):
        self.commandant = User.objects.create_user(username="cmdt", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": Roles.COMMANDANT})
        self.commandant.refresh_from_db()

        self.chef_section = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_section, defaults={"role": Roles.CHEF_SECTION})
        self.chef_section.refresh_from_db()

        self.admin_navire = User.objects.create_user(username="adm", password="pass")
        UserProfile.objects.update_or_create(user=self.admin_navire, defaults={"role": Roles.ADMIN_NAVIRE})
        self.admin_navire.refresh_from_db()

        self.permission = ManageUsersPermission()
        self.view = SimpleNamespace()

    def test_lecture_autorisee_pour_tout_utilisateur_connecte(self):
        req = fake_request("GET", self.chef_section)
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_lecture_refusee_si_non_connecte(self):
        req = fake_request("GET", AnonymousUser())
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_commandant_peut_attribuer_un_role_dans_sa_matrice(self):
        req = fake_request("POST", self.commandant, {"role": "CHEF_SERVICE"})
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_commandant_ne_peut_pas_attribuer_un_role_hors_matrice(self):
        req = fake_request("POST", self.commandant, {"role": "ADMIN_NAVIRE"})
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_ecriture_refusee_sans_role_dans_la_charge_utile(self):
        req = fake_request("POST", self.commandant, {})
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_admin_navire_peut_tout_attribuer(self):
        req = fake_request("POST", self.admin_navire, {"role": "MASTER_ADMIN"})
        self.assertTrue(self.permission.has_permission(req, self.view))

    def test_sans_profil_ecriture_refusee(self):
        """Cas défensif : un utilisateur sans UserProfile (profil supprimé) ne
        doit jamais pouvoir gérer d'autres comptes."""
        self.chef_section.profile.delete()
        # Re-récupère l'utilisateur en base pour éviter que la relation inverse
        # user.profile ne reste en cache sur l'objet Python déjà supprimé.
        utilisateur_sans_profil = User.objects.get(pk=self.chef_section.pk)
        req = fake_request("POST", utilisateur_sans_profil, {"role": "EQUIPIER"})
        self.assertFalse(self.permission.has_permission(req, self.view))

    def test_object_permission_commandant_sur_cible_dans_sa_matrice(self):
        obj = SimpleNamespace(role=Roles.CHEF_SERVICE)
        req = fake_request("PATCH", self.commandant)
        self.assertTrue(self.permission.has_object_permission(req, self.view, obj))

    def test_object_permission_commandant_sur_cible_hors_matrice(self):
        obj = SimpleNamespace(role=Roles.ADMIN_NAVIRE)
        req = fake_request("PATCH", self.commandant)
        self.assertFalse(self.permission.has_object_permission(req, self.view, obj))
