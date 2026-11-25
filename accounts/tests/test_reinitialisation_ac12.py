"""AC-12 : répartition des autorités de réinitialisation, expiration, usage unique, sessions, notification, essais répétés."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from accounts.services import (
    PROTECTION_GENERALE, PROTECTION_RECUPERATION, PROTECTION_TECHNIQUE, niveau_de_protection, peut_reinitialiser_cible,
    reinitialiser_mot_de_passe,
)
from notifications.models import Notification
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


@override_settings(DUREE_MOT_DE_PASSE_PROVISOIRE_HEURES=1, TENTATIVES_CONNEXION_MAX=3)
class MecanismeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.tech = _compte("tech", navire=navire, technique=True)
        self.marin = _compte("marin", navire=navire)

    def test_reinitialisation_tracee_notifiee_sans_secret_et_sessions_revoquees(self):
        session = Client()
        session.force_login(self.marin)
        self.assertEqual(session.get(reverse("mon-profil")).status_code, 200)
        mot_de_passe = reinitialiser_mot_de_passe(self.tech, self.marin)
        self.assertEqual(session.get(reverse("mon-profil")).status_code, 302)  # session ouverte invalidée
        trace = AuditLog.objects.get(action="reinitialisation_mot_de_passe")
        self.assertNotIn(mot_de_passe, trace.details)
        self.assertTrue(Notification.objects.filter(user=self.marin, categorie="securite").exists())
        profil = UserProfile.objects.get(user=self.marin)
        self.assertTrue(profil.mot_de_passe_provisoire)
        self.assertLessEqual(profil.mot_de_passe_provisoire_expire_le, timezone.now() + timedelta(hours=1))

    def test_le_mot_de_passe_provisoire_expire(self):
        mot_de_passe = reinitialiser_mot_de_passe(self.tech, self.marin)
        UserProfile.objects.filter(user=self.marin).update(mot_de_passe_provisoire_expire_le=timezone.now() - timedelta(minutes=1))
        self.assertFalse(Client().login(username="marin", password=mot_de_passe))
        UserProfile.objects.filter(user=self.marin).update(mot_de_passe_provisoire_expire_le=timezone.now() + timedelta(minutes=5))
        self.assertTrue(Client().login(username="marin", password=mot_de_passe))

    def test_usage_unique_apres_changement_le_provisoire_ne_sert_plus(self):
        mot_de_passe = reinitialiser_mot_de_passe(self.tech, self.marin)
        client = Client()
        client.login(username="marin", password=mot_de_passe)
        reponse = client.post(reverse("password_change"), {
            "old_password": mot_de_passe, "new_password1": "Nouveau-mdp-solide-42", "new_password2": "Nouveau-mdp-solide-42"})
        self.assertEqual(reponse.status_code, 302)
        profil = UserProfile.objects.get(user=self.marin)
        self.assertFalse(profil.mot_de_passe_provisoire)
        self.assertIsNone(profil.mot_de_passe_provisoire_expire_le)
        self.assertFalse(Client().login(username="marin", password=mot_de_passe))

    def test_essais_repetes_verrouillent_meme_avec_le_bon_mot_de_passe(self):
        for _ in range(3):
            self.assertFalse(Client().login(username="marin", password="mauvais"))
        self.assertFalse(Client().login(username="marin", password="ancien-mdp-123"))
        cache.clear()
        self.assertTrue(Client().login(username="marin", password="ancien-mdp-123"))
