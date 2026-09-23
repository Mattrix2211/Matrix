"""Tests de base sur accounts/models.py — l'app accounts portait 0 test de
modèle avant cette tâche (RBAC de UserDirectoryView exclu, déjà couvert par
test_rbac_user_directory.py). Vérifie la création automatique du profil,
la cohérence rôle/périmètre (UserProfile.scope) et les propriétés dérivées.
"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile, Roles
from org.models import Ship, Service, Sector, Section


class CreationAutomatiqueDuProfilTests(TestCase):
    def test_un_profil_est_cree_automatiquement_a_la_creation_de_lutilisateur(self):
        """Le signal post_save (accounts/models.py::create_user_profile) doit
        créer un UserProfile pour tout nouvel utilisateur, sans action manuelle."""
        user = User.objects.create_user(username="nouveau", password="pass")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_le_role_par_defaut_du_profil_auto_cree_est_equipier(self):
        user = User.objects.create_user(username="nouveau2", password="pass")
        self.assertEqual(user.profile.role, Roles.EQUIPIER)

    def test_la_sauvegarde_dun_utilisateur_existant_ne_duplique_pas_le_profil(self):
        """get_or_create() dans le signal doit être idempotent : un save()
        ultérieur sur un utilisateur existant ne doit pas créer un second profil."""
        user = User.objects.create_user(username="existant", password="pass")
        user.first_name = "Modifié"
        user.save()
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)


class ScopeUserProfileTests(TestCase):
    """Cohérence rôle/périmètre : UserProfile.scope doit toujours renvoyer le
    niveau le plus précis renseigné (section > secteur > service > navire)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Richelieu", code="RIC")
        self.service = Service.objects.create(ship=self.ship, name="Service Machines")
        self.sector = Sector.objects.create(service=self.service, name="Secteur Propulsion")
        self.section = Section.objects.create(sector=self.sector, name="Section Diesel")

    def test_profil_sans_perimetre_renvoie_none_none(self):
        user = User.objects.create_user(username="sans_perimetre", password="pass")
        self.assertEqual(user.profile.scope, (None, None))

    def test_profil_avec_uniquement_le_navire_renvoie_le_niveau_navire(self):
        user = User.objects.create_user(username="niveau_navire", password="pass")
        user.profile.ship = self.ship
        user.profile.save()
        self.assertEqual(user.profile.scope, ("ship", self.ship.id))

    def test_profil_avec_secteur_et_navire_renvoie_le_niveau_le_plus_precis(self):
        user = User.objects.create_user(username="niveau_secteur", password="pass")
        user.profile.ship = self.ship
        user.profile.service = self.service
        user.profile.sector = self.sector
        user.profile.save()
        self.assertEqual(user.profile.scope, ("sector", self.sector.id))

    def test_profil_complet_jusqua_la_section_renvoie_le_niveau_section(self):
        user = User.objects.create_user(username="niveau_section", password="pass")
        user.profile.ship = self.ship
        user.profile.service = self.service
        user.profile.sector = self.sector
        user.profile.section = self.section
        user.profile.save()
        self.assertEqual(user.profile.scope, ("section", self.section.id))


class ProfilAgeTests(TestCase):
    def test_age_none_si_date_de_naissance_absente(self):
        user = User.objects.create_user(username="sans_date", password="pass")
        self.assertIsNone(user.profile.age)

    def test_age_calcule_correctement_a_partir_de_la_date_de_naissance(self):
        user = User.objects.create_user(username="avec_date", password="pass")
        aujourdhui = date.today()
        # Anniversaire déjà passé cette année : l'âge est exactement 30 ans.
        user.profile.date_naissance = aujourdhui.replace(year=aujourdhui.year - 30) - timedelta(days=1)
        user.profile.save()
        self.assertEqual(user.profile.age, 30)

    def test_age_nest_pas_encore_incremente_si_lanniversaire_nest_pas_encore_passe(self):
        user = User.objects.create_user(username="pas_encore", password="pass")
        aujourdhui = date.today()
        user.profile.date_naissance = aujourdhui.replace(year=aujourdhui.year - 30) + timedelta(days=1)
        user.profile.save()
        self.assertEqual(user.profile.age, 29)
