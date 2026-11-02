"""Le module Rondes est retiré : ni route, ni menu, ni module activable, ni tâche planifiée."""
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from matrix.core.modules import REGISTRE_MODULES
from matrix.core.navigation import GROUPES


class ModuleRondesRetireTests(TestCase):
    def test_plus_de_route(self):
        for nom in ("rondes-index", "ronde-detail", "ronde-modeles"):
            with self.assertRaises(NoReverseMatch):
                reverse(nom)
        User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")
        self.assertEqual(self.client.get("/rondes/").status_code, 404)

    def test_plus_dans_le_menu_ni_dans_les_modules(self):
        libelles = [entree.libelle for _, entrees in GROUPES for entree in entrees]
        self.assertNotIn("Rondes", libelles)
        self.assertNotIn("rondes", [module.cle for module in REGISTRE_MODULES])

    def test_plus_de_tache_planifiee(self):
        taches = " ".join(str(valeur) for valeur in settings.CELERY_BEAT_SCHEDULE.values())
        self.assertNotIn("rondes.", taches)
