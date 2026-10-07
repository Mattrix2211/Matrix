"""Écran web du catalogue : accès, fil d'Ariane, recherche, droits d'écriture par spécialité."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, ResponsableSpecialite, SpecialityChoice, UserProfile
from assets.models import ArticleCatalogue, CategorieCatalogue


class CatalogueWebTests(TestCase):
    def setUp(self):
        self.elec = SpecialityChoice.objects.create(name="Électricien web")
        self.meca = SpecialityChoice.objects.create(name="Mécanicien web")
        self.resp_elec = self._user("resp_elec_w", "EQUIPIER", self.elec)
        self.bord = self._user("bord_w", "EQUIPIER")
        self.racine = CategorieCatalogue.objects.create(nom="Outillage", specialite=self.elec)
        self.sous = CategorieCatalogue.objects.create(nom="Sertissage", specialite=self.elec, parent=self.racine)
        self.meca_cat = CategorieCatalogue.objects.create(nom="Pompes", specialite=self.meca)
        self.article = ArticleCatalogue.objects.create(
            categorie=self.sous, designation="Pince à sertir", marque="Facom", reference="XR-12",
            caracteristiques={"Capacité": "6 mm²"}, duree_vie_mois=60)

    def _user(self, nom, role, specialite=None):
        u = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=u, defaults={"role": role})
        if specialite:
            ResponsableSpecialite.objects.create(user=u, specialite=specialite)
        return User.objects.get(pk=u.pk)

    def test_anonyme_redirige_vers_connexion(self):
        self.assertEqual(self.client.get(reverse("catalogue")).status_code, 302)

    def test_lecture_pour_tout_connecte_sans_boutons(self):
        self.client.force_login(self.bord)
        r = self.client.get(reverse("catalogue"))
        self.assertContains(r, "Outillage")
        self.assertContains(r, "Pompes")
        self.assertNotContains(r, "Nouvelle catégorie")

    def test_boutons_pour_responsable_de_la_specialite_seulement(self):
        self.client.force_login(self.resp_elec)
        self.assertContains(self.client.get(reverse("catalogue")), "Nouvelle catégorie")
        self.assertContains(self.client.get(reverse("catalogue"), {"categorie": self.sous.pk}), "Nouvel article")
        self.assertNotContains(self.client.get(reverse("catalogue"), {"categorie": self.meca_cat.pk}), "Nouvel article")

    def test_fil_d_ariane(self):
        self.client.force_login(self.bord)
        r = self.client.get(reverse("catalogue"), {"categorie": self.sous.pk})
        self.assertContains(r, f'href="{reverse("catalogue")}?categorie={self.racine.pk}"')
        self.assertContains(r, "Pince à sertir")

    def test_recherche_fragment_htmx(self):
        self.client.force_login(self.bord)
        r = self.client.get(reverse("catalogue"), {"q": "facom"}, headers={"HX-Request": "true"})
        self.assertContains(r, "Pince à sertir")
        self.assertNotContains(r, "<html")
        r = self.client.get(reverse("catalogue"), {"q": "zzz"})
        self.assertContains(r, "Aucun article trouvé")

    def test_filtre_specialite(self):
        self.client.force_login(self.bord)
        r = self.client.get(reverse("catalogue"), {"specialite": self.meca.pk})
        self.assertContains(r, "Pompes")
        self.assertNotContains(r, "Outillage")

    def test_etat_vide(self):
        CategorieCatalogue.objects.update(actif=False)
        self.client.force_login(self.bord)
        self.assertContains(self.client.get(reverse("catalogue")), "Le catalogue est vide")

    def test_fiche_article(self):
        self.client.force_login(self.bord)
        r = self.client.get(reverse("catalogue-article", args=[self.article.pk]))
        self.assertContains(r, "6 mm²")
        self.assertContains(r, "5 ans")
        self.assertContains(r, "Aucune fiche de maintenance")
        self.assertNotContains(r, "Modifier")

    def test_ecriture_refusee_hors_specialite(self):
        self.client.force_login(self.resp_elec)
        self.assertEqual(self.client.get(reverse("catalogue-article-nouveau")).status_code, 200)
        r = self.client.post(reverse("catalogue-categorie-modifier", args=[self.meca_cat.pk]),
                             {"nom": "Piraté", "specialite": self.meca.pk})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.post(reverse("catalogue-categorie-archiver", args=[self.meca_cat.pk])).status_code, 403)
        # Spécialité falsifiée à la création : rien n'est écrit.
        self.client.post(reverse("catalogue-categorie-nouvelle"), {"nom": "Intrus", "specialite": self.meca.pk})
        self.assertFalse(CategorieCatalogue.objects.filter(nom="Intrus").exists())

    def test_marin_sans_droit_refuse(self):
        self.client.force_login(self.bord)
        self.assertEqual(self.client.get(reverse("catalogue-categorie-nouvelle")).status_code, 403)
        self.assertEqual(self.client.post(reverse("catalogue-article-archiver", args=[self.article.pk])).status_code, 403)

    def test_creation_article_et_archivage(self):
        self.client.force_login(self.resp_elec)
        r = self.client.post(reverse("catalogue-article-nouveau"), {
            "designation": "Multimètre", "categorie": self.racine.pk, "caracteristiques_texte": "Tension : 600 V"})
        self.assertEqual(r.status_code, 302)
        art = ArticleCatalogue.objects.get(designation="Multimètre")
        self.assertEqual(art.caracteristiques, {"Tension": "600 V"})
        self.assertEqual(art.created_by, self.resp_elec)
        self.client.post(reverse("catalogue-article-archiver", args=[art.pk]))
        art.refresh_from_db()
        self.assertFalse(art.actif)

    def test_archivage_categorie_non_vide_refuse(self):
        self.client.force_login(self.resp_elec)
        self.client.post(reverse("catalogue-categorie-archiver", args=[self.sous.pk]))
        self.sous.refresh_from_db()
        self.assertTrue(self.sous.actif)

    def test_doublon_racine_refuse(self):
        self.client.force_login(self.resp_elec)
        self.client.post(reverse("catalogue-categorie-nouvelle"), {"nom": "Outillage", "specialite": self.elec.pk})
        self.assertEqual(CategorieCatalogue.objects.filter(nom="Outillage").count(), 1)

    def test_archives_masques_et_ecritures_journalisees(self):
        self.client.force_login(self.resp_elec)
        self.client.post(reverse("catalogue-article-archiver", args=[self.article.pk]))
        self.assertTrue(AuditLog.objects.filter(action="catalogue.archivage", actor=self.resp_elec).exists())
        self.assertNotContains(self.client.get(reverse("catalogue"), {"categorie": self.sous.pk}), "mx-cat-article")
        self.assertNotContains(self.client.get(reverse("catalogue"), {"q": "Pince"}), "XR-12")
        self.client.post(reverse("catalogue-article-nouveau"), {"designation": "Tournevis", "categorie": self.racine.pk})
        self.assertTrue(AuditLog.objects.filter(action="catalogue.creation").exists())
