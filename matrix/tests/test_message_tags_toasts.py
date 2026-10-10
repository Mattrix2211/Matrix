"""Bug corrigé (constat visuel du 05/09/2026) : les toasts affichant un message
d'erreur (messages.error) restaient d'une couleur neutre au lieu du rouge
attendu. Cause : matrix/templates/base.html construit la classe CSS du toast
via "text-bg-{{ message.tags }}", et Django tague par défaut les messages de
niveau ERROR avec le mot "error" — qui n'est pas une classe Bootstrap 5 valide
(Bootstrap utilise "danger"). Corrigé en ajoutant MESSAGE_TAGS dans
matrix/settings.py pour faire correspondre le niveau ERROR à la classe
"danger" (et DEBUG à "secondary", pour la même raison).
"""
from django.contrib.auth.models import User
from django.test import TestCase


class ToastMessageErreurTests(TestCase):
    """Vérifie que le rendu HTML des toasts utilise bien "text-bg-danger" pour
    un message.error, et jamais l'ancien tag Django invalide "text-bg-error"."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_toast_test", email="admin_toast@navy.fr", password="pass",
        )

    def test_message_error_rend_le_toast_en_danger_pas_en_error(self):
        # update_all_vibration_params déclenche messages.error(...) dans
        # matrix/views.py::SettingsView.post lorsque les valeurs postées ne
        # sont pas des entiers valides — chemin de code réel, pas un test
        # isolé du template.
        self.client.login(username="admin_toast_test", password="pass")
        response = self.client.post(
            "/parametre/",
            {
                "action": "update_all_vibration_params",
                "vib_days_a": "invalide",
                "vib_days_b": "invalide",
                "vib_days_c": "invalide",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("text-bg-danger", html)
        self.assertNotIn("text-bg-error", html)

    def test_message_success_reste_en_success(self):
        # Non-régression : le tag "success" correspond déjà à une classe
        # Bootstrap valide, il ne doit pas être affecté par MESSAGE_TAGS.
        self.client.login(username="admin_toast_test", password="pass")
        response = self.client.post(
            "/parametre/",
            {
                "action": "update_all_vibration_params",
                "vib_days_a": "180",
                "vib_days_b": "90",
                "vib_days_c": "30",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("text-bg-success", html)
