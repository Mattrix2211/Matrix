"""Tests du filtre de template contrôlant l'affichage du bouton "Générer le
bilan" sur le tableau de bord (T10)."""
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Sector, Service, Ship
from reports.templatetags.reports_extras import peut_generer_bilan


class PeutGenererBilanTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T10bis", code="T10B")
        self.service = Service.objects.create(ship=self.navire, name="Service T10bis")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T10bis")

    def _creer_utilisateur(self, role, avec_perimetre=True):
        user = User.objects.create_user(username=f"u-{role}", password="pass")
        UserProfile.objects.filter(user=user).update(
            role=role, sector=self.secteur if avec_perimetre else None
        )
        user.refresh_from_db()
        return user

    def test_anonyme_refuse(self):
        self.assertFalse(peut_generer_bilan(AnonymousUser()))

    def test_equipier_refuse(self):
        user = self._creer_utilisateur("EQUIPIER")
        self.assertFalse(peut_generer_bilan(user))

    def test_chef_section_autorise(self):
        user = self._creer_utilisateur("CHEF_SECTION")
        self.assertTrue(peut_generer_bilan(user))

    def test_chef_secteur_autorise(self):
        user = self._creer_utilisateur("CHEF_SECTEUR")
        self.assertTrue(peut_generer_bilan(user))

    def test_chef_section_sans_perimetre_refuse(self):
        user = self._creer_utilisateur("CHEF_SECTION", avec_perimetre=False)
        self.assertFalse(peut_generer_bilan(user))
