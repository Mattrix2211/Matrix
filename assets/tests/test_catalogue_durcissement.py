"""Catalogue : paramètres d'URL invalides, recherche normalisée, photos (liste blanche d'images)."""
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import ResponsableSpecialite, SpecialityChoice, UserProfile
from assets.models import CategorieCatalogue


def _png(nom="p.png"):
    tampon = io.BytesIO()
    Image.new("RGB", (2, 2)).save(tampon, "PNG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/png")


class CatalogueDurcissementTests(TestCase):
    def setUp(self):
        self.spe = SpecialityChoice.objects.create(name="Spé durcie")
        self.resp = User.objects.create_user(username="resp_dur", password="pass")
        UserProfile.objects.update_or_create(user=self.resp, defaults={"role": "EQUIPIER"})
        ResponsableSpecialite.objects.create(user=self.resp, specialite=self.spe)
        self.client.force_login(self.resp)

    def test_parametres_invalides_ne_font_pas_d_erreur_serveur(self):
        for url, params in (
            ("catalogue", {"categorie": "abc"}), ("catalogue", {"specialite": "abc"}),
            ("catalogue", {"q": "\x00ab\x00"}),
            ("catalogue-categorie-nouvelle", {"parent": "abc"}),
            ("catalogue-categorie-nouvelle", {"specialite": "abc"}),
            ("catalogue-article-nouveau", {"categorie": "abc"}),
        ):
            self.assertEqual(self.client.get(reverse(url), params).status_code, 200, (url, params))

    def _poster_categorie(self, fichier):
        return self.client.post(reverse("catalogue-categorie-nouvelle"), {
            "nom": "Avec photo", "specialite": self.spe.pk, "ordre": 0, "photo": fichier})

    def test_photo_html_et_svg_refusees(self):
        for nom, contenu in (("x.html", b"<script>1</script>"), ("x.svg", b"<svg onload='1'/>"), ("x.png", b"pas une image")):
            r = self._poster_categorie(SimpleUploadedFile(nom, contenu))
            self.assertEqual(r.status_code, 200, nom)
        self.assertFalse(CategorieCatalogue.objects.filter(nom="Avec photo").exists())

    def test_photo_png_acceptee(self):
        self.assertEqual(self._poster_categorie(_png()).status_code, 302)
        self.assertTrue(CategorieCatalogue.objects.filter(nom="Avec photo").exists())

    def test_photo_refusee_par_l_api(self):
        r = self.client.post("/api/assets/catalogue-categories/", {
            "nom": "Api", "specialite": self.spe.pk, "photo": SimpleUploadedFile("x.svg", b"<svg/>")})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/assets/catalogue-categories/", {
            "nom": "Api", "specialite": self.spe.pk, "photo": _png()})
        self.assertEqual(r.status_code, 201)
