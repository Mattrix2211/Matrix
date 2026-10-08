from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ListeMaterielScriptsTests(TestCase):
    """Le script en ligne de /assets/ cible des éléments : ils doivent être
    présents dans la page avant lui, sinon getElementById renvoie null."""

    def setUp(self):
        User.objects.create_superuser("admin_scripts", password="pass")
        self.client.login(username="admin_scripts", password="pass")

    def test_menu_contextuel_dossiers_avant_le_script(self):
        html = self.client.get(reverse("asset-list")).content.decode()
        debut_script = html.index("var ctx = document.getElementById('folderContextMenu')")
        self.assertIn('id="folderContextMenu"', html[:debut_script])
