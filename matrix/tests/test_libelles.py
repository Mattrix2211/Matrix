"""Libellés lisibles par un marin : aucune mention de développeur, vocabulaire de formulaire et de menu arrêté."""
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from demandes.tests.test_demandes import DemandesBase
from matrix.core.navigation import construire_navigation


class LibellesTests(DemandesBase):
    def test_aucun_gabarit_ne_cite_claude(self):
        racine = Path(settings.BASE_DIR) / "matrix" / "templates"
        fautifs = [str(f) for f in racine.rglob("*.html") if "CLAUDE" in f.read_text(encoding="utf-8")]
        self.assertEqual(fautifs, [])

    def test_menu_difficultes_signalees(self):
        libelles = [e["libelle"] for g in construire_navigation(self.marin, "/") for e in g["entrees"]]
        self.assertIn("Difficultés signalées", libelles)
        self.assertNotIn("Demandes bord–terre", libelles)

    def test_titres_des_difficultes(self):
        self.client.login(username="chef", password="pass")
        index = self.client.get(reverse("demandes-index"))
        self.assertContains(index, '<h1 class="h3 mb-3">Difficultés signalées</h1>', html=True)
        self.assertNotContains(index, "bord–terre")
        detail = self.client.get(reverse("demande-detail", args=[self.demande.pk]))
        self.assertNotContains(detail, "bord–terre")
        self.assertContains(detail, "Actions à mener")
        self.assertNotContains(detail, "Actions décidées")

    def test_formulaires_de_taches_et_d_annonces(self):
        profil = self.chef.profile
        profil.role = "COMMANDANT"
        profil.save()
        self.client.login(username="chef", password="pass")
        taches = self.client.get(reverse("taches-index"))
        for attendu in ("Tâches de mon équipe et fils où je suis interlocuteur", "Liste de contrôle (facultatif"):
            self.assertContains(taches, attendu)
        self.assertNotContains(taches, "Checklist")
        annonce = self.client.get(reverse("annonce-nouvelle"))
        self.assertContains(annonce, "Destinataires")
        self.assertNotContains(annonce, "Public visé")
