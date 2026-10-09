"""Tests UX-0.6 : brouillons enregistrés côté serveur (docs/UX.md §5.4)."""
import json
import shutil
import subprocess
import unittest
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.template import Context, Template
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from matrix.core.brouillons import brouillons_a_reprendre, purger_brouillons_anciens
from matrix.core.models import Brouillon

TESTS = Path(__file__).resolve().parent


def envoyer(client, donnees, **extra):
    return client.post(reverse("brouillon"), data=json.dumps(donnees), content_type="application/json", **extra)


class BrouillonIdentiteTests(TestCase):
    """La page indique son marin (X-Mx-Utilisateur) : un autre marin connecté ne reçoit ni n'écrit rien."""

    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user("alice_id", password="x")
        self.bob = User.objects.create_user("bob_id", password="x")
        self.client.force_login(self.bob)  # Bob s'est connecté dans un autre onglet
        Brouillon.objects.create(user=self.bob, cle="cr:1", contenu={"note": "à Bob"})
        self.entete_alice = {"HTTP_X_MX_UTILISATEUR": str(self.alice.pk)}

    def test_ecriture_refusee_sans_rien_creer(self):
        reponse = envoyer(self.client, {"cle": "cr:2", "contenu": {"note": "secret d'Alice"}}, **self.entete_alice)
        self.assertEqual(reponse.status_code, 409)
        self.assertEqual(reponse.json()["erreur"], "Une autre session est ouverte.")
        self.assertFalse(Brouillon.objects.filter(cle="cr:2").exists())
        reponse = envoyer(self.client, {"cle": "cr:1", "contenu": {"note": "écrasé"}}, **self.entete_alice)
        self.assertEqual(Brouillon.objects.get(cle="cr:1").contenu, {"note": "à Bob"})

    def test_lecture_et_suppression_refusees(self):
        url = reverse("brouillon") + "?cle=cr:1"
        self.assertEqual(self.client.get(url, **self.entete_alice).status_code, 409)
        self.assertEqual(self.client.delete(url, **self.entete_alice).status_code, 409)
        self.assertTrue(Brouillon.objects.filter(cle="cr:1").exists())

    def test_identifiant_correct_comme_avant(self):
        entete = {"HTTP_X_MX_UTILISATEUR": str(self.bob.pk)}
        self.assertEqual(envoyer(self.client, {"cle": "cr:3", "contenu": {"note": "ok"}}, **entete).status_code, 200)
        self.assertTrue(self.client.get(reverse("brouillon") + "?cle=cr:1", **entete).json()["existe"])
        self.assertEqual(self.client.delete(reverse("brouillon") + "?cle=cr:1", **entete).status_code, 200)
        self.assertFalse(Brouillon.objects.filter(cle="cr:1").exists())


class BrouillonApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.client_alice = Client()
        self.client_alice.force_login(self.alice)
        self.client_bob = Client()
        self.client_bob.force_login(self.bob)
        self.url = reverse("brouillon")

    def test_enregistrer_puis_lire(self):
        rep = envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"obs": "texte", "etats": ["a", "b"]}, "url": "/cr/1/"})
        self.assertEqual(rep.status_code, 200)
        lu = self.client_alice.get(self.url, {"cle": "cr:1"}).json()
        self.assertTrue(lu["existe"])
        self.assertEqual(lu["contenu"], {"obs": "texte", "etats": ["a", "b"]})

    def test_lecture_sans_brouillon(self):
        self.assertFalse(self.client_alice.get(self.url, {"cle": "cr:9"}).json()["existe"])

    def test_un_seul_brouillon_par_cle(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"obs": "v1"}})
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"obs": "v2"}})
        self.assertEqual(Brouillon.objects.filter(user=self.alice, cle="cr:1").count(), 1)
        self.assertEqual(Brouillon.objects.get(user=self.alice).contenu, {"obs": "v2"})

    def test_isolation_entre_utilisateurs(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"obs": "secret"}})
        self.assertFalse(self.client_bob.get(self.url, {"cle": "cr:1"}).json()["existe"])
        envoyer(self.client_bob, {"cle": "cr:1", "contenu": {"obs": "autre"}})
        self.assertEqual(Brouillon.objects.count(), 2)
        self.assertEqual(self.client_alice.get(self.url, {"cle": "cr:1"}).json()["contenu"], {"obs": "secret"})
        # Bob ne peut pas supprimer le brouillon d'Alice.
        self.client_bob.delete(self.url + "?cle=cr:1")
        self.assertTrue(Brouillon.objects.filter(user=self.alice, cle="cr:1").exists())
        self.assertFalse(Brouillon.objects.filter(user=self.bob, cle="cr:1").exists())

    def test_supprimer(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"obs": "x"}})
        self.assertEqual(self.client_alice.delete(self.url + "?cle=cr:1").status_code, 200)
        self.assertFalse(Brouillon.objects.exists())

    def test_anonyme_refuse(self):
        anonyme = Client()
        self.assertEqual(anonyme.get(self.url, {"cle": "cr:1"}).status_code, 401)
        self.assertEqual(envoyer(anonyme, {"cle": "cr:1", "contenu": {}}).status_code, 401)
        self.assertEqual(anonyme.delete(self.url + "?cle=cr:1").status_code, 401)
        self.assertFalse(Brouillon.objects.exists())

    def test_csrf_exige(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        self.assertEqual(envoyer(client, {"cle": "cr:1", "contenu": {"a": "b"}}).status_code, 403)
        self.assertEqual(client.delete(self.url + "?cle=cr:1").status_code, 403)
        self.assertFalse(Brouillon.objects.exists())

    @override_settings(BROUILLONS_TAILLE_MAX=200)
    def test_limite_de_taille(self):
        rep = envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"obs": "x" * 500}})
        self.assertEqual(rep.status_code, 413)
        self.assertFalse(Brouillon.objects.exists())

    def test_mots_de_passe_et_jetons_exclus(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {
            "obs": "ok", "password": "a", "new_password1": "b", "csrfmiddlewaretoken": "c", "api_token": "d",
        }})
        self.assertEqual(Brouillon.objects.get().contenu, {"obs": "ok"})

    def test_envoi_formulaire_classique(self):
        rep = self.client_alice.post(self.url, {"cle": "cr:2", "obs": "texte", "mot_de_passe": "x"})
        self.assertEqual(rep.status_code, 200)
        self.assertEqual(Brouillon.objects.get().contenu, {"obs": "texte"})

    def test_entrees_invalides(self):
        for donnees in ({"cle": "", "contenu": {}}, {"cle": "a b", "contenu": {}}, {"cle": "x" * 121, "contenu": {}},
                        {"cle": "cr:1", "contenu": "texte"}, {"cle": "cr:1", "contenu": {"a": 3}}):
            self.assertEqual(envoyer(self.client_alice, donnees).status_code, 400, donnees)
        self.assertEqual(self.client_alice.post(self.url, "pas du json", content_type="application/json").status_code, 400)
        self.assertEqual(self.client_alice.get(self.url, {"cle": "a b"}).status_code, 400)
        self.assertFalse(Brouillon.objects.exists())

    def test_adresse_externe_non_conservee(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {}, "url": "//evil.example/x"})
        self.assertEqual(Brouillon.objects.get().url, "")

    def test_adresses_dangereuses_refusees(self):
        for url in ("/\\evil.example", "/\t/evil.example", "/a\nb", "javascript:alert(1)", "http://x",
                    "//evil.example/x", "/ok\\x"):
            Brouillon.objects.all().delete()
            envoyer(self.client_alice, {"cle": "cr:1", "contenu": {}, "url": url})
            self.assertEqual(Brouillon.objects.get().url, "", repr(url))

    def test_adresse_interne_conservee(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {}, "url": "/cr/1/?a=2"})
        self.assertEqual(Brouillon.objects.get().url, "/cr/1/?a=2")

    def test_noms_proches_de_sensibles_conserves(self):
        envoyer(self.client_alice, {"cle": "cr:1", "contenu": {"passage": "a", "compass": "b", "mot_de_passe": "c"}})
        self.assertEqual(Brouillon.objects.get().contenu, {"passage": "a", "compass": "b"})

    def test_lister_mes_brouillons(self):
        envoyer(self.client_alice, {"cle": "a:1", "contenu": {"x": "1"}})
        envoyer(self.client_alice, {"cle": "b:1", "contenu": {"x": "1"}})
        envoyer(self.client_bob, {"cle": "c:1", "contenu": {"x": "1"}})
        self.assertEqual([b.cle for b in brouillons_a_reprendre(self.alice)], ["b:1", "a:1"])


class BrouillonPurgeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="x")
        self.vieux = Brouillon.objects.create(user=self.user, cle="vieux", contenu={})
        self.recent = Brouillon.objects.create(user=self.user, cle="recent", contenu={})
        Brouillon.objects.filter(pk=self.vieux.pk).update(updated_at=timezone.now() - timedelta(days=40))

    @override_settings(BROUILLONS_CONSERVATION_JOURS=30)
    def test_purge_selon_la_duree_configuree(self):
        self.assertEqual(purger_brouillons_anciens(), 1)
        self.assertEqual(list(Brouillon.objects.values_list("cle", flat=True)), ["recent"])

    @override_settings(BROUILLONS_CONSERVATION_JOURS=60)
    def test_duree_plus_longue_conserve_tout(self):
        self.assertEqual(purger_brouillons_anciens(), 0)

    @override_settings(BROUILLONS_CONSERVATION_JOURS=0)
    def test_zero_jamais_purge(self):
        self.assertEqual(purger_brouillons_anciens(), 0)
        self.assertEqual(Brouillon.objects.count(), 2)

    @override_settings(BROUILLONS_CONSERVATION_JOURS=30)
    def test_commande_de_gestion(self):
        sortie = StringIO()
        call_command("purger_brouillons", stdout=sortie)
        self.assertIn("1 brouillon(s) supprimé(s)", sortie.getvalue())


class GrilleBrouillonRenduTests(SimpleTestCase):
    def rendre(self, **extra):
        contexte = {"colonnes": [{"nom": "etat", "libelle": "État", "type": "conformite"}],
                    "lignes": [{"cle": "1", "libelle": "Extincteur 1"}]}
        contexte.update(extra)
        return Template(
            '{% load composants %}{% grille id="g" libelle="Contrôle" colonnes=colonnes lignes=lignes '
            "brouillon=brouillon lecture_seule=ro %}{% fin_grille %}"
        ).render(Context(contexte))

    def test_attribut_present_avec_cle(self):
        html = self.rendre(brouillon="cr-extincteurs:12", ro=False)
        self.assertIn('data-brouillon="cr-extincteurs:12"', html)
        self.assertIn('data-brouillon-libelle="Contrôle"', html)

    def test_absent_sans_cle_ou_en_lecture_seule(self):
        self.assertNotIn("data-brouillon", self.rendre(brouillon="", ro=False))
        self.assertNotIn("data-brouillon", self.rendre(brouillon="cr:1", ro=True))


@unittest.skipUnless(shutil.which("node"), "node absent : logique JS vérifiée par le QA dans le navigateur")
class BrouillonJsTests(SimpleTestCase):
    def test_logique_pure(self):
        resultat = subprocess.run(
            ["node", str(TESTS / "brouillon.test.js")], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
