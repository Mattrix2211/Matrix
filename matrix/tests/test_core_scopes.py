"""Tests unitaires directs de matrix/core/scopes.py.

scope_filters_for_user, is_master_admin et ship_id_for_user sont les briques
de périmètre réutilisées par toutes les apps (via ScopedQuerySetMixin,
build_scope_q, etc.), mais n'étaient testées jusqu'ici qu'indirectement à
travers les tests de fuite de périmètre de chaque app (ex.
assets/tests/test_scope_leak.py). Ce fichier les teste isolément.

Remarque : après UserProfile.objects.update_or_create(user=user, ...), on
appelle systématiquement user.refresh_from_db() avant d'utiliser user.profile.
En effet, le signal post_save qui crée automatiquement le profil à la
création de l'utilisateur met en cache la relation inverse user.profile sur
l'objet Python `user` ; sans ce rafraîchissement, user.profile continuerait
de pointer vers l'ancien profil (auto-créé, role=EQUIPIER) au lieu du profil
mis à jour par update_or_create — un piège classique de test, pas un bug de
scopes.py (déjà géré ailleurs par le même refresh_from_db() dans
accounts/tests/test_rbac_user_directory.py).
"""
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from accounts.models import UserProfile, Roles
from matrix.core.scopes import (
    is_master_admin,
    scope_filters_for_user,
    sector_id_for_user,
    section_id_for_user,
    ship_id_for_user,
)
from org.models import Ship, Service, Sector, Section


class ScopeFiltersForUserTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NTS")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.section = Section.objects.create(sector=self.sector, name="Section test")

    def test_utilisateur_non_connecte_ne_recoit_aucun_filtre(self):
        self.assertEqual(scope_filters_for_user(AnonymousUser()), {})

    def test_profil_rattache_a_une_section_filtre_par_section(self):
        user = User.objects.create_user(username="u_section", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": Roles.EQUIPIER, "ship": self.ship, "service": self.service,
                                  "sector": self.sector, "section": self.section},
        )
        user.refresh_from_db()
        self.assertEqual(scope_filters_for_user(user), {"section_id": self.section.id})

    def test_profil_rattache_a_un_secteur_sans_section_filtre_par_secteur(self):
        user = User.objects.create_user(username="u_secteur", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": Roles.EQUIPIER, "ship": self.ship, "service": self.service,
                                  "sector": self.sector},
        )
        user.refresh_from_db()
        self.assertEqual(scope_filters_for_user(user), {"sector_id": self.sector.id})

    def test_profil_rattache_a_un_service_sans_secteur_filtre_par_service(self):
        user = User.objects.create_user(username="u_service", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": Roles.EQUIPIER, "ship": self.ship, "service": self.service},
        )
        user.refresh_from_db()
        self.assertEqual(scope_filters_for_user(user), {"service_id": self.service.id})

    def test_profil_rattache_a_un_navire_seul_filtre_par_navire(self):
        user = User.objects.create_user(username="u_navire", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": Roles.EQUIPIER, "ship": self.ship},
        )
        user.refresh_from_db()
        self.assertEqual(scope_filters_for_user(user), {"ship_id": self.ship.id})

    def test_profil_sans_aucun_perimetre_ne_recoit_aucun_filtre(self):
        user = User.objects.create_user(username="u_sans_perimetre", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.MASTER_ADMIN})
        user.refresh_from_db()
        self.assertEqual(scope_filters_for_user(user), {})


class IsMasterAdminTests(TestCase):
    def test_superutilisateur_est_toujours_master_admin(self):
        superuser = User.objects.create_superuser(username="super", password="pass", email="s@s.fr")
        self.assertTrue(is_master_admin(superuser))

    def test_role_master_admin_est_master_admin(self):
        user = User.objects.create_user(username="ma", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.MASTER_ADMIN})
        user.refresh_from_db()
        self.assertTrue(is_master_admin(user))

    def test_role_admin_navire_nest_pas_master_admin(self):
        """ADMIN_NAVIRE est un cran en dessous de MASTER_ADMIN (matrix/core/roles.py) :
        rattaché à un navire précis, il ne doit pas obtenir l'accès flotte entière."""
        user = User.objects.create_user(username="an", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.ADMIN_NAVIRE})
        user.refresh_from_db()
        self.assertFalse(is_master_admin(user))

    def test_role_equipier_nest_pas_master_admin(self):
        user = User.objects.create_user(username="eq", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.EQUIPIER})
        user.refresh_from_db()
        self.assertFalse(is_master_admin(user))


class ShipIdForUserTests(TestCase):
    def test_profil_avec_navire_renvoie_lid_du_navire(self):
        ship = Ship.objects.create(name="Navire Z", code="NZ")
        user = User.objects.create_user(username="uz", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.EQUIPIER, "ship": ship})
        user.refresh_from_db()
        self.assertEqual(ship_id_for_user(user), ship.id)


class SectorIdForUserTests(TestCase):
    """sector_id_for_user() : même logique que ShipIdForUserTests, déclinée au
    niveau secteur (utile à la Vue flotte scopée pour un CHEF_SECTEUR)."""

    def test_profil_avec_secteur_renvoie_lid_du_secteur(self):
        ship = Ship.objects.create(name="Navire Secteur", code="NSEC")
        service = Service.objects.create(ship=ship, name="Service Secteur")
        sector = Sector.objects.create(service=service, name="Secteur Y")
        user = User.objects.create_user(username="usec", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": Roles.CHEF_SECTEUR, "ship": ship, "service": service, "sector": sector},
        )
        user.refresh_from_db()
        self.assertEqual(sector_id_for_user(user), sector.id)

    def test_profil_sans_secteur_renvoie_none(self):
        user = User.objects.create_user(username="sans_secteur", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.CHEF_SECTEUR})
        user.refresh_from_db()
        self.assertIsNone(sector_id_for_user(user))


class SectionIdForUserTests(TestCase):
    """section_id_for_user() : même logique que ShipIdForUserTests, déclinée au
    niveau section (utile à la Vue flotte scopée pour un CHEF_SECTION)."""

    def test_profil_avec_section_renvoie_lid_de_la_section(self):
        ship = Ship.objects.create(name="Navire Section", code="NSCT")
        service = Service.objects.create(ship=ship, name="Service Section")
        sector = Sector.objects.create(service=service, name="Secteur Section")
        section = Section.objects.create(sector=sector, name="Section Y")
        user = User.objects.create_user(username="usect", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={
                "role": Roles.CHEF_SECTION, "ship": ship, "service": service,
                "sector": sector, "section": section,
            },
        )
        user.refresh_from_db()
        self.assertEqual(section_id_for_user(user), section.id)

    def test_profil_sans_section_renvoie_none(self):
        user = User.objects.create_user(username="sans_section", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.CHEF_SECTION})
        user.refresh_from_db()
        self.assertIsNone(section_id_for_user(user))

    def test_profil_sans_navire_renvoie_none(self):
        user = User.objects.create_user(username="sans_navire", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": Roles.MASTER_ADMIN})
        user.refresh_from_db()
        self.assertIsNone(ship_id_for_user(user))

    def test_ship_id_reste_le_navire_meme_si_un_perimetre_plus_precis_est_renseigne(self):
        """Contrairement à scope_filters_for_user (qui renvoie le niveau le plus
        précis), ship_id_for_user renvoie toujours le navire, quel que soit le
        service/secteur/section également renseigné sur le profil."""
        ship = Ship.objects.create(name="Navire W", code="NW")
        service = Service.objects.create(ship=ship, name="Service W")
        sector = Sector.objects.create(service=service, name="Secteur W")
        section = Section.objects.create(sector=sector, name="Section W")
        user = User.objects.create_user(username="uw", password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": Roles.EQUIPIER, "ship": ship, "service": service,
                                  "sector": sector, "section": section},
        )
        user.refresh_from_db()
        self.assertEqual(ship_id_for_user(user), ship.id)
