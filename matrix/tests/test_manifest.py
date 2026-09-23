"""Tests du manifest.json (installation de Matrix sur l'écran d'accueil des
tablettes du bord — lancement en plein écran, sans barre d'adresse).

Le fichier est servi comme un fichier statique classique (via `runserver` en
DEBUG, comme le reste de `static/`) : on vérifie ici sa présence et sa
validité via les finders staticfiles plutôt que par une requête HTTP, le
client de test ne rejouant pas le montage automatique de `/static/` fait par
`runserver` (pas de route dédiée, contrairement à service-worker.js qui doit
être à la racine pour son scope).
"""
import json

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import TestCase


class ManifestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")

    def test_manifest_accessible_et_bien_forme(self):
        chemin_manifest = finders.find("manifest.json")
        self.assertIsNotNone(chemin_manifest, "manifest.json introuvable dans les fichiers statiques")
        with open(chemin_manifest, encoding="utf-8") as f:
            contenu = json.load(f)
        self.assertEqual(contenu["name"], "Matrix")
        self.assertEqual(contenu["short_name"], "Matrix")
        self.assertEqual(contenu["display"], "standalone")
        self.assertEqual(contenu["theme_color"], "#00B4D8")
        tailles = {icone["sizes"] for icone in contenu["icons"]}
        self.assertEqual(tailles, {"192x192", "512x512"})
        for icone in contenu["icons"]:
            chemin_relatif = icone["src"].replace("/static/", "", 1)
            self.assertIsNotNone(
                finders.find(chemin_relatif), f"icône introuvable : {icone['src']}"
            )

    def test_manifest_lie_dans_le_head_des_pages(self):
        response = self.client.get("/")
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, "manifest.json")
        self.assertContains(response, 'name="theme-color" content="#00B4D8"')
