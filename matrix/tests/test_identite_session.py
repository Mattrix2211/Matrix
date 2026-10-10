"""Poste partagé : identité des écritures, trace des connexions, nettoyage des sessions."""
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.tasks import purger_sessions


class IdentiteEcrituresTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin_id", password="pass")
        self.url = reverse("notifications-tout-lu")
        self.client.force_login(self.marin)

    def test_ecriture_refusee_si_la_page_est_celle_d_un_autre(self):
        self.assertEqual(self.client.post(self.url, HTTP_X_MX_UTILISATEUR="99999").status_code, 409)
        self.assertEqual(self.client.post(self.url, {"mx_utilisateur": "99999"}).status_code, 409)

    def test_ecriture_acceptee_avec_la_bonne_identite_ou_sans(self):
        for donnees, entetes in (({}, {"HTTP_X_MX_UTILISATEUR": str(self.marin.pk)}),
                                 ({"mx_utilisateur": str(self.marin.pk)}, {}), ({}, {})):
            self.assertEqual(self.client.post(self.url, donnees, **entetes).status_code, 200, (donnees, entetes))

    def test_lecture_deconnexion_et_api_non_concernees(self):
        self.assertEqual(self.client.get(reverse("notifications-centre"), HTTP_X_MX_UTILISATEUR="99999").status_code, 200)
        reponse = self.client.post(reverse("logout"), HTTP_X_MX_UTILISATEUR="99999")
        self.assertEqual(reponse.status_code, 302)

    def test_brouillon_automatique_exige_l_identite(self):
        url = reverse("brouillon")
        self.assertEqual(self.client.get(url + "?cle=x:y", HTTP_X_MX_AUTOMATIQUE="1").status_code, 409)
        self.assertEqual(self.client.get(
            url + "?cle=x:y", HTTP_X_MX_AUTOMATIQUE="1", HTTP_X_MX_UTILISATEUR=str(self.marin.pk)).status_code, 200)

    def test_identite_dans_la_page_et_script_charge(self):
        html = self.client.get(reverse("notifications-centre")).content.decode()
        self.assertIn(f'<body data-utilisateur="{self.marin.pk}"', html)
        self.assertIn("js/identite.js", html)


class TraceConnexionsTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin_tr", password="pass")

    def actions(self):
        return list(AuditLog.objects.filter(actor=self.marin).order_by("pk").values_list("action", flat=True))

    def test_connexion_et_deconnexion_manuelles_tracees(self):
        self.client.post(reverse("login"), {"username": "marin_tr", "password": "pass"})
        self.client.post(reverse("logout"))
        self.assertEqual(self.actions(), ["connexion", "deconnexion"])

    def test_pas_de_trace_si_deja_deconnecte(self):
        self.client.post(reverse("logout"))
        self.assertEqual(self.actions(), [])


class PurgeSessionsTests(TestCase):
    def test_sessions_expirees_supprimees(self):
        Session.objects.create(session_key="vieille", session_data="x", expire_date=timezone.now() - timezone.timedelta(days=1))
        Session.objects.create(session_key="valide", session_data="x", expire_date=timezone.now() + timezone.timedelta(days=1))
        purger_sessions()
        self.assertEqual(list(Session.objects.values_list("session_key", flat=True)), ["valide"])


class MasquageModeBloqueTests(TestCase):
    def test_le_contenu_de_la_page_est_masque_derriere_le_dialogue(self):
        from django.contrib.staticfiles import finders

        css = open(finders.find("css/matrix.css"), encoding="utf-8").read()
        self.assertIn(".mx-inactivite--bloque > :not(.mx-inactivite):not(.modal-backdrop) { visibility: hidden", css)
