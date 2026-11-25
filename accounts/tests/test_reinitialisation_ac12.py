"""AC-12 : répartition des autorités de réinitialisation (le mécanisme à code est dans test_reinitialisation_codes)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from accounts.services import (
    PROTECTION_GENERALE, PROTECTION_RECUPERATION, PROTECTION_TECHNIQUE, niveau_de_protection, peut_reinitialiser_cible,
)
from org.models import Ship

User = get_user_model()


def _compte(nom, role="EQUIPIER", navire=None, technique=False, fonction="", **drapeaux):
    utilisateur = User.objects.create_user(username=nom, password="ancien-mdp-123", **drapeaux)
    UserProfile.objects.update_or_create(user=utilisateur, defaults={
        "role": role, "ship": navire, "administrateur_technique": technique, "fonction_coma": fonction})
    return User.objects.get(pk=utilisateur.pk)


class RepartitionTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.tech = _compte("tech", navire=navire, technique=True)
        self.general = _compte("general", "MASTER_ADMIN", is_superuser=True)
        self.comptes = {
            "equipier": _compte("equipier", navire=navire), "section": _compte("section", "CHEF_SECTION", navire),
            "secteur": _compte("secteur", "CHEF_SECTEUR", navire), "service": _compte("service", "CHEF_SERVICE", navire),
            "adjoint": _compte("adjoint", "ETAT_MAJOR", navire, fonction="COMAEQ"), "second": _compte("second", "COMMANDANT_EN_SECOND", navire),
            "commandant": _compte("commandant", "COMMANDANT", navire), "autre_tech": _compte("autre_tech", navire=navire, technique=True),
            "chef_service_cumul": _compte("chef_service_cumul", "CHEF_SERVICE", navire, technique=True),
        }

    def test_tableau_des_autorites(self):
        attendu = {
            "equipier": PROTECTION_TECHNIQUE, "section": PROTECTION_TECHNIQUE, "secteur": PROTECTION_TECHNIQUE, "service": PROTECTION_TECHNIQUE,
            "adjoint": PROTECTION_GENERALE, "second": PROTECTION_GENERALE, "commandant": PROTECTION_GENERALE,
            "autre_tech": PROTECTION_GENERALE, "chef_service_cumul": PROTECTION_GENERALE,  # cumul : protection la plus élevée
        }
        for nom, niveau in attendu.items():
            self.assertEqual(niveau_de_protection(self.comptes[nom]), niveau, nom)
            self.assertEqual(peut_reinitialiser_cible(self.tech, self.comptes[nom]), niveau == PROTECTION_TECHNIQUE, nom)
            self.assertTrue(peut_reinitialiser_cible(self.general, self.comptes[nom]), nom)
        self.assertEqual(niveau_de_protection(self.general), PROTECTION_RECUPERATION)
        self.assertFalse(peut_reinitialiser_cible(self.tech, self.general))
        self.assertFalse(peut_reinitialiser_cible(self.general, self.general))

    def test_le_commandant_ne_reinitialise_personne(self):
        for nom in ("equipier", "section"):
            self.assertFalse(peut_reinitialiser_cible(self.comptes["commandant"], self.comptes[nom]))
