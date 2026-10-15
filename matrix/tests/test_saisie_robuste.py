"""Saisies hostiles ou mal formées : NUL, textes trop longs, identifiants non numériques.

PostgreSQL les refuse avec une erreur serveur là où SQLite les accepte : chaque cas doit donner
un message à l'utilisateur (ou une réponse 400), jamais une erreur 500."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import DataError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from absences.models import Absence
from accounts.models import TypeAbsence
from annonces.models import Annonce
from demandes import services as demandes_services
from documentation.models import Document
from matrix.core.middleware import ErreurSaisieMiddleware
from matrix.core.saisie import verifier_longueurs
from org.models import Ship
from taches.models import Tache
from taches.tests.test_taches import TachesBase

LONG = "x" * 201


class SaisieBase(TachesBase):
    def setUp(self):
        super().setUp()
        self.cdt = self._marin("cdt", None, "COMMANDANT", "A")
        self.type_absence = TypeAbsence.objects.create(name="Permission")

    def poster(self, user, nom, donnees, args=None, **extra):
        self.client.force_login(user)
        return self.client.post(reverse(nom, args=args), donnees, **extra)

    def messages(self, reponse):
        return [str(m) for m in reponse.wsgi_request._messages]


class NulDansLesFormulairesTests(SaisieBase):
    def test_creation_de_tache_avec_nul(self):
        reponse = self.poster(self.chef, "taches-index", {"titre": "Contr\x00ôle", "assigne": self.marin.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Tache.objects.filter(titre="Contrôle").exists())

    def test_blocage_avec_nul(self):
        tache = self._tache()
        reponse = self.poster(self.marin, "tache-action", {"action": "bloquer", "motif": "Pièce\x00 absente"}, args=[tache.pk])
        self.assertEqual(reponse.status_code, 302)
        tache.refresh_from_db()
        self.assertEqual(tache.motif_blocage, "Pièce absente")

    def test_absence_avec_nul(self):
        jour = timezone.localdate()
        reponse = self.poster(self.marin, "absences-index", {
            "action": "declarer", "type_absence": self.type_absence.pk, "date_debut": jour.isoformat(),
            "date_fin": (jour + timedelta(days=1)).isoformat(), "motif": "Famille\x00"})
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Absence.objects.get(marin=self.marin).motif, "Famille")

    def test_annonce_avec_nul(self):
        reponse = self.poster(self.cdt, "annonce-nouvelle", {
            "titre": "Exer\x00cice", "corps": "Jeudi\x00", "niveau": "info", "cible": f"ship:{self.navire.pk}"})
        self.assertEqual(reponse.status_code, 302)
        annonce = Annonce.objects.get()
        self.assertEqual((annonce.titre, annonce.corps), ("Exercice", "Jeudi"))

    def test_nouveau_document_avec_nul(self):
        reponse = self.poster(self.cdt, "document-nouveau", {
            "titre": "Consi\x00gnes", "cible": f"ship:{self.navire.pk}", "contenu": "Ouvrir\x00 la vanne"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Document.objects.filter(titre="Consignes").exists())

    def test_modification_de_compte_avec_nul(self):
        reponse = self.poster(self.cdt, "user-directory", {
            "action": "edit_user", "pk": self.marin.pk, "first_name": "Jean\x00", "last_name": "Dupont",
            "role": "EQUIPIER", "equipage": "A", "ship_id": self.navire.pk})
        self.assertEqual(reponse.status_code, 302)
        self.marin.refresh_from_db()
        self.assertEqual(self.marin.first_name, "Jean")


class TextesTropLongsTests(SaisieBase):
    def test_creation_de_tache_trop_longue(self):
        reponse = self.poster(self.chef, "taches-index", {"titre": LONG, "assigne": self.marin.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(Tache.objects.exists())

    def test_annonce_trop_longue_reaffiche_le_formulaire_avec_la_saisie(self):
        reponse = self.poster(self.cdt, "annonce-nouvelle", {
            "titre": LONG, "corps": "Message à conserver", "niveau": "info", "cible": f"ship:{self.navire.pk}"})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "limité à 200 caractères")
        self.assertContains(reponse, "Message à conserver")
        self.assertContains(reponse, LONG)
        self.assertFalse(Annonce.objects.exists())

    def test_equipage_d_annonce_trop_long(self):
        reponse = self.poster(self.cdt, "annonce-nouvelle", {
            "titre": "Ordre", "corps": "x", "niveau": "info", "cible": f"ship:{self.navire.pk}", "equipage": "ABCDEFGHIJ"})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "limité à 8 caractères")
        self.assertFalse(Annonce.objects.exists())

    def test_document_trop_long_reaffiche_le_formulaire_avec_la_saisie(self):
        reponse = self.poster(self.cdt, "document-nouveau", {
            "titre": LONG, "domaine": "Sécurité", "cible": f"ship:{self.navire.pk}", "contenu": "Contenu à conserver"})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "limité à 200 caractères")
        self.assertContains(reponse, "Contenu à conserver")
        self.assertContains(reponse, "Sécurité")
        self.assertFalse(Document.objects.exists())

    def test_modification_de_compte_trop_longue(self):
        reponse = self.poster(self.cdt, "user-directory", {
            "action": "edit_user", "pk": self.marin.pk, "first_name": "J" * 151, "last_name": "Dupont",
            "role": "EQUIPIER", "equipage": "A", "ship_id": self.navire.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("limité à 150 caractères", " ".join(self.messages(reponse)))
        self.marin.refresh_from_db()
        self.assertEqual(self.marin.last_name, "")

    def test_creation_de_compte_trop_longue(self):
        reponse = self.poster(self.cdt, "user-directory", {
            "action": "create_user", "first_name": "Jean", "last_name": "D" * 151, "role": "EQUIPIER",
            "equipage": "A", "ship_id": self.navire.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(User.objects.filter(first_name="Jean").exists())

    def test_creation_de_compte_au_nom_tres_long_garde_un_identifiant_valide(self):
        self.poster(self.cdt, "user-directory", {
            "action": "create_user", "first_name": "J" * 150, "last_name": "D" * 150, "role": "EQUIPIER",
            "equipage": "A", "ship_id": self.navire.pk})
        self.assertLessEqual(len(User.objects.get(first_name="J" * 150).username), 150)

    def test_verifier_longueurs_nomme_le_champ(self):
        with self.assertRaises(ValidationError) as ctx:
            verifier_longueurs(Tache, titre=LONG)
        self.assertEqual(ctx.exception.messages, ["« Titre » est limité à 200 caractères (201 saisis)."])


class IdentifiantsNonNumeriquesTests(SaisieBase):
    def test_tache_assigne_non_numerique(self):
        reponse = self.poster(self.chef, "taches-index", {"titre": "Tâche", "assigne": "abc"})
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(Tache.objects.exists())

    def test_tache_actions_avec_identifiant_non_numerique(self):
        tache = self._tache()
        for action, champ in (("modifier", "assigne"), ("interlocuteur", "interlocuteur")):
            reponse = self.poster(self.chef, "tache-action", {"action": action, champ: "abc"}, args=[tache.pk])
            self.assertEqual(reponse.status_code, 302, action)

    def test_absence_identifiants_non_numeriques(self):
        jour = timezone.localdate().isoformat()
        base = {"action": "declarer", "date_debut": jour, "date_fin": jour}
        for variante in ({"marin_id": "abc", "type_absence": self.type_absence.pk}, {"type_absence": "abc"}):
            reponse = self.poster(self.chef, "absences-index", {**base, **variante})
            self.assertEqual(reponse.status_code, 302)
        reponse = self.poster(self.chef, "absences-index", {"action": "valider", "absence_id": "abc"})
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(Absence.objects.exists())

    def test_demande_identifiants_non_numeriques(self):
        demande = demandes_services.creer_demande(self.marin, self._tache(), "Pompe", "Bruit", self.chef)
        for action, champ in (("reaffecter", "responsable"), ("interlocuteur", "interlocuteur"), ("creer_action", "assigne")):
            reponse = self.poster(self.chef, "demande-action", {"action": action, champ: "abc"}, args=[demande.pk])
            self.assertEqual(reponse.status_code, 302, action)

    def test_formation_marin_non_numerique(self):
        reponse = self.poster(self.chef, "formation-valider", {"marin_id": "abc", "course_id": "abc", "completed_at": "2026-01-01"})
        self.assertEqual(reponse.status_code, 302)

    def test_calendrier_periode_invalide(self):
        self.client.force_login(self.marin)
        for parametres in ({"start": "abc"}, {"start": "2026-10-01"}, {"end": "2026-10-01"}, {"start": "abc", "end": "def"},
                           {"date": "abc"}, {"ship": "abc"}, {"user": "abc"}):
            reponse = self.client.get(reverse("calendar-events"), parametres)
            self.assertLess(reponse.status_code, 500, parametres)


class AutresSaisiesMalFormeesTests(SaisieBase):
    def test_entier_non_numerique_dans_un_formulaire_donne_un_message(self):
        reponse = self.poster(self.cdt, "asset-list", {"action": "create_asset", "criticality": "abc", "internal_id": "A1"})
        self.assertEqual(reponse.status_code, 302)

    def test_retour_relatif_du_changement_de_theme(self):
        reponse = self.poster(self.marin, "basculer-theme", {"next": "abc"})
        self.assertEqual((reponse.status_code, reponse["Location"]), (302, "abc"))

    def test_abonnement_push_aux_cles_mal_formees(self):
        reponse = self.poster(self.marin, "push-subscribe", {"endpoint": "https://push.example/1", "keys": "abc"})
        self.assertEqual(reponse.status_code, 400)

    def test_nul_dans_une_requete_api(self):
        reponse = self.poster(self.marin, "push-unsubscribe", {"endpoint": "https://push.example/\x001"})
        self.assertLess(reponse.status_code, 500)


class ProgrammeSansBatimentTests(TestCase):
    def test_page_de_saisie_ne_cree_rien_pour_un_administrateur_sans_batiment(self):
        admin = User.objects.create_user(username="admin_sans_navire", password="pass")
        admin.profile.role = "MASTER_ADMIN"
        admin.profile.save()
        Ship.objects.create(name="Bâtiment programme", code="BP")
        self.client.force_login(admin)
        reponse = self.client.get(reverse("evenement-nouveau"))
        self.assertLess(reponse.status_code, 500)
        self.assertFalse(admin.profile.ship_id)


class FiletSaisieTests(SimpleTestCase):
    """Le filet commun convertit les erreurs de saisie non contrôlées par une vue."""

    def reponse(self, exception, methode="post", chemin="/taches/", **entetes):
        requete = getattr(RequestFactory(), methode)(chemin, **entetes)
        requete._messages = type("Stock", (), {"add": lambda self, *a, **k: None})()  # le filet n'y ajoute qu'un message
        return ErreurSaisieMiddleware(lambda r: None).process_exception(requete, exception)

    def test_erreurs_de_saisie_redirigees_avec_message(self):
        for exception in (
            DataError("value too long"), ValidationError("Date invalide"), OverflowError("trop grand"),
            ValueError("Field 'id' expected a number but got 'abc'."),
        ):
            reponse = self.reponse(exception, HTTP_REFERER="http://testserver/taches/")
            self.assertEqual((reponse.status_code, reponse["Location"]), (302, "http://testserver/taches/"))

    def test_retour_externe_ignore(self):
        self.assertEqual(self.reponse(DataError("x"), HTTP_REFERER="http://pirate.example/")["Location"], "/")

    def test_lecture_et_api_donnent_400(self):
        self.assertEqual(self.reponse(DataError("x"), "get").status_code, 400)
        self.assertEqual(self.reponse(DataError("x"), chemin="/api/assets/").status_code, 400)

    def test_autres_erreurs_non_masquees(self):
        for exception in (ValueError("autre"), KeyError("x"), RuntimeError("panne")):
            self.assertIsNone(self.reponse(exception))
