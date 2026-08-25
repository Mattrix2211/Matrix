"""Tests de l'onglet Notification de la page Réglages (/parametre/?tab=notifications).

Bug corrigé (retour QA) : la page entière renvoyait 403 pour tout utilisateur
non-superuser Django, rendant les horaires de digest « Ma journée » / « Ma
journée de demain » impossibles à régler pour l'immense majorité des marins.
Seule la section « Notification quotidienne » doit être ouverte à tout
utilisateur connecté ; le reste des Réglages (rôles, navires, hiérarchie,
journal...) doit rester réservé aux superusers Django.
"""
from datetime import time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile


class OngletNotificationsReglagesTests(TestCase):
    def setUp(self):
        self.equipier = User.objects.create_user(
            username="equipier_test", email="equipier@navy.fr", password="pass",
        )
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER")

        self.autre_equipier = User.objects.create_user(
            username="autre_equipier_test", email="autre@navy.fr", password="pass",
        )
        UserProfile.objects.filter(user=self.autre_equipier).update(role="EQUIPIER")

        self.superuser = User.objects.create_superuser(
            username="admin_test", email="admin@navy.fr", password="pass",
        )

        self.url = reverse("settings")

    def test_equipier_peut_acceder_a_l_onglet_notifications(self):
        self.client.login(username="equipier_test", password="pass")
        response = self.client.get(self.url, {"tab": "notifications"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "notifications")

    def test_equipier_ne_peut_pas_acceder_aux_autres_onglets(self):
        self.client.login(username="equipier_test", password="pass")
        for tab in ("generale", "utilisateurs", "navires", "hierarchie", "installations", "journal"):
            response = self.client.get(self.url, {"tab": tab})
            self.assertEqual(response.status_code, 403, f"onglet {tab} devrait être refusé")

    def test_equipier_sans_tab_est_refuse(self):
        # Sans paramètre tab, le comportement par défaut de la vue vise l'onglet
        # "generale" (réservé superuser) : doit rester refusé.
        self.client.login(username="equipier_test", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_equipier_peut_modifier_ses_propres_horaires(self):
        self.client.login(username="equipier_test", password="pass")
        response = self.client.post(self.url, {
            "action": "update_notification_time",
            "notification_time": "07:30",
            "notification_time_soir": "18:45",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("tab=notifications", response.url)
        self.equipier.profile.refresh_from_db()
        self.assertEqual(self.equipier.profile.notification_time, time(7, 30))
        self.assertEqual(self.equipier.profile.notification_time_soir, time(18, 45))

    def test_equipier_ne_peut_pas_modifier_le_profil_d_un_autre(self):
        # L'action ne prend en compte que l'utilisateur connecté : aucun
        # paramètre ne permet de cibler le profil d'un tiers.
        self.client.login(username="equipier_test", password="pass")
        self.client.post(self.url, {
            "action": "update_notification_time",
            "notification_time": "07:30",
            "notification_time_soir": "18:45",
        })
        self.autre_equipier.profile.refresh_from_db()
        self.assertNotEqual(self.autre_equipier.profile.notification_time, time(7, 30))

    def test_equipier_ne_peut_pas_executer_une_autre_action(self):
        self.client.login(username="equipier_test", password="pass")
        response = self.client.post(self.url, {"action": "toggle_role", "code": "COMMANDANT"})
        self.assertEqual(response.status_code, 403)

    def test_utilisateur_non_authentifie_est_redirige_vers_connexion(self):
        response = self.client.get(self.url, {"tab": "notifications"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_superuser_garde_acces_complet(self):
        self.client.login(username="admin_test", password="pass")
        for tab in ("generale", "utilisateurs", "navires", "hierarchie", "installations", "notifications", "journal"):
            response = self.client.get(self.url, {"tab": tab})
            self.assertEqual(response.status_code, 200, f"onglet {tab} devrait rester accessible au superuser")
