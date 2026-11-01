"""Reprise d'un brouillon depuis « Aujourd'hui » : le lien mène toujours à une page, et le brouillon n'est jamais perdu."""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from matrix.core.brouillons import adresse_de_reprise
from matrix.core.models import Brouillon

ANCIENNE_ADRESSE = "/anomalies/signaler/"  # adresse enregistrée à tort par l'ancien jeu de démonstration (404)


class RepriseBrouillonTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="martin", password="pass")
        self.client.login(username="martin", password="pass")
        self.accueil = reverse("home")

    def _brouillon(self, **champs):
        valeurs = {"user": self.marin, "cle": "anomalie:nouvelle", "libelle": "Signalement d'anomalie",
                   "url": ANCIENNE_ADRESSE, "contenu": {"titre": "Odeur de brûlé au local machine"}, **champs}
        return Brouillon.objects.create(**valeurs)

    def test_l_ancienne_adresse_est_remplacee_par_la_page_du_formulaire(self):
        self._brouillon()
        page = self.client.get(self.accueil)
        self.assertContains(page, f'href="{reverse("anomalie-create")}"')
        self.assertNotContains(page, f'href="{ANCIENNE_ADRESSE}"')

    def test_le_lien_de_reprise_ouvre_le_formulaire_et_le_brouillon_reste_restituable(self):
        brouillon = self._brouillon()
        avant = (brouillon.contenu, brouillon.url, brouillon.updated_at)
        lien = self.client.get(self.accueil).context["brouillons"][0].adresse
        formulaire = self.client.get(lien)
        self.assertEqual(formulaire.status_code, 200)
        self.assertContains(formulaire, 'data-brouillon="anomalie:nouvelle"')
        restitue = self.client.get(reverse("brouillon"), {"cle": "anomalie:nouvelle"}).json()
        self.assertEqual(restitue["contenu"], {"titre": "Odeur de brûlé au local machine"})
        brouillon.refresh_from_db()
        self.assertEqual((brouillon.contenu, brouillon.url, brouillon.updated_at), avant)  # aucune perte, aucune réécriture

    def test_une_adresse_valide_est_conservee_avec_ses_parametres(self):
        adresse = f"{reverse('anomalie-create')}?asset=12"
        self._brouillon(url=adresse)
        self.assertContains(self.client.get(self.accueil), f'href="{adresse}"')

    def test_adresse_inconnue_sans_route_de_repli_n_affiche_pas_de_lien_mort_et_conserve_le_brouillon(self):
        brouillon = self._brouillon(cle="autre:1", url="/page/disparue/", libelle="Saisie ancienne")
        page = self.client.get(self.accueil)
        self.assertNotContains(page, "/page/disparue/")
        self.assertTrue(Brouillon.objects.filter(pk=brouillon.pk).exists())
        self.assertEqual(adresse_de_reprise(brouillon), "")

    def test_le_brouillon_d_un_autre_marin_n_est_jamais_propose(self):
        autre = User.objects.create_user(username="autre", password="pass")
        self._brouillon(user=autre, libelle="Secret de l'autre")
        self.assertNotContains(self.client.get(self.accueil), "Secret de l'autre")


class BrouillonDeDemonstrationTests(TestCase):
    def test_le_brouillon_du_jeu_de_demonstration_se_reprend_sans_erreur(self):
        call_command("seed_demo", stdout=StringIO())
        self.client.login(username="equipier_a", password="pass")
        brouillons = self.client.get(reverse("home")).context["brouillons"]
        self.assertEqual(len(brouillons), 1)
        self.assertEqual(brouillons[0].url, reverse("anomalie-create"))
        self.assertEqual(self.client.get(brouillons[0].adresse).status_code, 200)
