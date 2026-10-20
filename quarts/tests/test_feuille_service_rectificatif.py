"""Feuilles publiées figées et versions rectificatives : la version publiée est
immuable, l'écart avec le planning effectif est signalé, un rectificatif suit
le circuit de visa et ne remplace la version qu'à sa publication."""
import threading
import time
from datetime import datetime, timedelta
from unittest import mock, skipUnless

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from notifications.models import Notification
from org.models import Ship
from quarts.models import (
    CreneauServiceGarde,
    FeuilleService,
    FonctionFeuilleService,
    PosteAlerte,
    ScenarioAlerte,
    ServiceGarde,
    peut_lire_feuille_service,
)
from django.core.management import call_command
from quarts.rectificatif import divergences_effectives, signaler_divergence
from quarts.services import feuille_service_du_jour_pour
from quarts.tests.test_feuille_service import FeuilleServiceTestsBase, _utilisateur, jeton_visa_affiche


class RectificatifBase(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.scenario = ScenarioAlerte.objects.create(
            ship=self.ship, libelle="Alerte intrus", famille=ScenarioAlerte.FAMILLE_PROTECTION,
        )
        PosteAlerte.objects.create(scenario=self.scenario, libelle="PC sécu", fonction=self.fonction, obligatoire=True)
        self.relais = _utilisateur("marin_relais", "EQUIPIER", ship=self.ship)
        self.creneau = self._publier_tour(marin=self.marin_service)
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        self.url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.jour:%Y-%m-%d}"])
        self._circuit()

    def _circuit(self):
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        self.feuille.refresh_from_db()

    def _echange(self, marin):
        """Le planning publié change de titulaire (effet d'un échange de service validé)."""
        self.creneau.marin = marin
        self.creneau.save(update_fields=["marin", "updated_at"])

    def _post(self, username, action):
        self.client.force_login(User.objects.get(username=username))
        donnees = {"action": action}
        if action == "viser_comaeq":
            donnees["jeton_visa"] = jeton_visa_affiche(self.client, self.url)
        return self.client.post(self.url, donnees)

    def _circuit_rectificatif(self):
        self._post("bsc", "proposer")
        self._post("chef_secteur", "viser_secteur")
        self._post("chef_service", "viser_service")
        self._post("etat_major", "viser_comaeq")

    def _page(self, username):
        self.client.force_login(User.objects.get(username=username))
        return self.client.get(self.url)


class PublicationFigeeTests(RectificatifBase):
    def test_titulaires_et_alertes_lus_dans_la_version_apres_un_echange(self):
        self._echange(self.relais)
        self.assertEqual(self.feuille.personnel[0]["marin_fige"], "marin_service")
        reponse = self._page("bsc")
        self.assertEqual(reponse.context["personnel"][0]["marin_fige"], "marin_service")
        poste = reponse.context["alertes"][0]["postes"][0]
        self.assertEqual((poste["marin_fige"], poste["arme"]), ("marin_service", True))
        self.assertContains(reponse, "Alerte intrus")

    def test_la_version_n_est_jamais_modifiee(self):
        avant = self.feuille.versions.get().contenu_fige
        self._echange(self.relais)
        self._page("bsc")
        self.assertEqual(self.feuille.versions.get().contenu_fige, avant)
        self.assertEqual(self.feuille.versions.count(), 1)

    def test_le_contenu_figé_porte_les_identifiants_des_marins(self):
        contenu = self.feuille.versions.get().contenu_fige
        self.assertEqual(contenu["personnel"][0]["marin_id"], self.marin_service.pk)
        self.assertEqual(contenu["alertes"][0]["postes"][0]["marin_id"], self.marin_service.pk)

    def test_je_suis_de_service_suit_la_version(self):
        self._echange(self.relais)
        self.assertTrue(feuille_service_du_jour_pour(self.marin_service, self.jour)["je_suis_de_service"])
        self.assertFalse(feuille_service_du_jour_pour(self.relais, self.jour)["je_suis_de_service"])


class DivergenceTests(RectificatifBase):
    def test_aucune_divergence_sans_changement(self):
        self.assertEqual(divergences_effectives(self.feuille), [])
        self.assertNotContains(self._page("bsc"), "ont changé depuis la publication")

    def test_un_changement_de_titulaire_est_signale_sans_annuler_l_echange(self):
        self._echange(self.relais)
        libelles = {d["libelle"] for d in divergences_effectives(self.feuille)}
        self.assertEqual(libelles, {"Officier de garde", "Alerte intrus — PC sécu"})
        page = self._page("bsc").content.decode()
        self.assertIn("Les affectations effectives ont changé depuis la publication", page)
        self.assertIn("reste la référence publiée", page)
        self.assertIn("restent effectifs dans le planning", page)
        self.assertNotIn("annulé", page)
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.marin, self.relais)

    def test_pas_de_rectificatif_sans_difference_effective(self):
        self.assertEqual(self._post("bsc", "ouvrir_rectificatif").status_code, 302)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_rectificatif_ouvert").exists())

    def test_retour_au_titulaire_d_origine_efface_la_divergence(self):
        self._echange(self.relais)
        self._echange(self.marin_service)
        self.assertEqual(divergences_effectives(self.feuille), [])


class RectificatifTests(RectificatifBase):
    def _ouvrir(self):
        self._echange(self.relais)
        self.assertEqual(self._post("bsc", "ouvrir_rectificatif").status_code, 302)
        self.feuille.refresh_from_db()

    def test_ouverture_par_le_redacteur_habilite(self):
        self._ouvrir()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertTrue(self.feuille.rectificatif_en_cours)
        self.assertEqual(self.feuille.rectificatif_ouvert_par, self.equipier)
        self.assertEqual(self.feuille.versions.count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_rectificatif_ouvert").exists())
        # Aucune notification avant la publication.
        self.assertFalse(Notification.objects.filter(verb__icontains="rectificative").exists())

    def test_la_version_publiee_reste_la_reference_et_n_est_pas_remplacee(self):
        self._ouvrir()
        version = self.feuille.versions.get()
        self.assertFalse(version.est_remplacee)
        # Un marin non acteur lit toujours la version publiée, sans 403.
        page = self._page("marin_service")
        self.assertEqual(page.status_code, 200)
        contenu = page.content.decode()
        self.assertIn("Version 1", contenu)
        self.assertEqual(page.context["personnel"][0]["marin_fige"], "marin_service")
        self.assertIn("ont changé depuis la publication", contenu)
        self.assertNotIn("Préparer un rectificatif", contenu)
        self.assertTrue(feuille_service_du_jour_pour(self.marin_service, self.jour)["je_suis_de_service"])

    def test_le_redacteur_voit_la_copie_de_travail_avec_les_nouvelles_affectations(self):
        self._ouvrir()
        contenu = self._page("bsc").content.decode()
        self.assertIn("Rectificatif en cours", contenu)
        self.assertEqual(self.feuille.personnel[0]["creneau"].marin, self.relais)

    def test_circuit_puis_publication_remplace_la_version(self):
        self._ouvrir()
        self._post("bsc", "proposer")
        self._post("chef_secteur", "viser_secteur")
        self._post("chef_service", "viser_service")
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertFalse(self.feuille.versions.get().est_remplacee)
        self._post("etat_major", "viser_comaeq")
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)
        v1, v2 = self.feuille.versions.order_by("numero")
        self.assertTrue(v1.est_remplacee)
        self.assertFalse(v2.est_remplacee)
        self.assertEqual((v2.numero, v2.remplace_numero), (2, 1))
        self.assertTrue(v2.est_rectificative)
        self.assertEqual(v2.contenu_fige["personnel"][0]["marin"], "marin_relais")
        self.assertEqual(v1.contenu_fige["personnel"][0]["marin"], "marin_service")
        self.assertIsNone(self.feuille.rectificatif_ouvert_par)
        self.assertEqual(divergences_effectives(self.feuille), [])

    def test_impression_et_historique_identifient_la_rectification(self):
        self._ouvrir()
        self._circuit_rectificatif()
        page = self._page("marin_service").content.decode()
        self.assertIn("Version rectificative n°2 — remplace la version 1", page)
        self.assertIn("window.print()", page)
        self.assertIn("Remplacée", page)
        self.assertIn("Référence publiée", page)
        self.assertIn("marin_relais", page)

    def test_notifications_a_la_publication_seulement(self):
        self._ouvrir()
        self._post("bsc", "proposer")
        self._post("chef_secteur", "viser_secteur")
        self._post("chef_service", "viser_service")
        self.assertFalse(Notification.objects.filter(verb__icontains="rectificative").exists())
        self._post("etat_major", "viser_comaeq")
        notifies = set(Notification.objects.filter(verb__icontains="rectificative").values_list("user__username", flat=True))
        # Ancien et nouveau titulaires touchés, et rédacteur du rectificatif.
        self.assertEqual(notifies, {"marin_service", "marin_relais", "bsc"})
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_rectificatif_publie").exists())

    def test_plusieurs_echanges_sont_consolides_en_une_version(self):
        autre = _utilisateur("marin_autre", "EQUIPIER", ship=self.ship)
        self._echange(self.relais)
        self._echange(autre)
        self._post("bsc", "ouvrir_rectificatif")
        self._circuit_rectificatif()
        self.assertEqual(self.feuille.versions.count(), 2)
        self.assertEqual(self.feuille.versions.first().contenu_fige["personnel"][0]["marin"], "marin_autre")

    def test_renvoi_garde_la_version_de_reference_et_le_redacteur(self):
        self._ouvrir()
        self._post("bsc", "proposer")
        self.client.force_login(self.chef_secteur)
        self.client.post(self.url, {"action": "renvoyer", "motif": "À revoir"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertTrue(self.feuille.rectificatif_en_cours)
        self.assertTrue(Notification.objects.filter(user=self.equipier, verb__icontains="renvoyée").exists())
        self.assertEqual(self.feuille.versions.count(), 1)

    def test_pas_de_second_rectificatif_pendant_le_premier(self):
        self._ouvrir()
        self.assertEqual(self._post("bsc", "ouvrir_rectificatif").status_code, 403)

    def test_rubrique_saisie_dans_le_rectificatif_ne_change_pas_la_version(self):
        self._ouvrir()
        self.client.force_login(self.equipier)
        self.client.post(self.url, {"action": "enregistrer_entete", f"rubrique_{self.rubrique_quotidienne.uid}": "Lundi"})
        entete = self.feuille.versions.get().contenu_fige["entete"]
        self.assertEqual([e["valeur"] for e in entete if e["libelle"] == "Type de journée"], [""])


class FausseDivergenceEtFuiteTests(RectificatifBase):
    def test_changement_de_grade_ou_de_nom_n_est_pas_une_divergence(self):
        UserProfile.objects.filter(user=self.marin_service).update(grade="CNE")
        User.objects.filter(pk=self.marin_service.pk).update(first_name="Paul", last_name="Durand")
        self.assertEqual(divergences_effectives(self.feuille), [])
        self.assertNotContains(self._page("bsc"), "ont changé depuis la publication")

    def test_ancienne_version_sans_identifiant_compare_le_texte(self):
        version = self.feuille.versions.get()
        for e in version.contenu_fige["personnel"]:
            e.pop("marin_id")
        version.save(update_fields=["contenu_fige"])
        self.assertEqual(divergences_effectives(self.feuille), [])
        self._echange(self.relais)
        self.assertTrue(divergences_effectives(self.feuille))

    def test_motif_de_renvoi_et_structure_invisibles_d_un_non_acteur(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.equipier)
        self.feuille.renvoyer(self.chef_secteur, "MOTIFSECRET")
        self.fonction.libelle = "Fonction modifiée"
        self.fonction.save()
        page = self._page("marin_service")
        self.assertNotContains(page, "MOTIFSECRET")
        self.assertNotContains(page, "ont changé depuis la création")
        self.assertContains(self._page("bsc"), "MOTIFSECRET")

    def test_echec_de_creation_de_version_laisse_la_feuille_inchangee(self):
        feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour + timedelta(days=1), created_by=self.equipier,
        )
        feuille.proposer(self.chef_service)
        feuille.viser_service(self.chef_service)
        with mock.patch.object(FeuilleService, "creer_version", side_effect=RuntimeError("échec")):
            with self.assertRaises(RuntimeError):
                feuille.viser_comaeq(self.etat_major)
        feuille.refresh_from_db()
        self.assertEqual(feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertFalse(feuille.versions.exists())
        self.assertIsNone(feuille.publiee_le)


class SignalementDivergenceTests(RectificatifBase):
    def _notifs(self):
        return Notification.objects.filter(verb__icontains="rectificatif à préparer")

    def test_signal_cible_une_seule_fois(self):
        self._echange(self.relais)
        signaler_divergence(self.feuille)
        signaler_divergence(self.feuille)
        # Rédacteur de la feuille et COMAEQ, pas l'équipage ni les titulaires touchés.
        self.assertEqual(
            sorted(self._notifs().values_list("user__username", flat=True)), ["bsc", "etat_major"]
        )
        notif = self._notifs().first()
        self.assertEqual(notif.url, self.url)
        self.assertFalse(Notification.objects.filter(user=self.marin_service, verb__icontains="rectificatif").exists())
        self.assertNotIn("MOTIF", notif.verb)

    def test_nouveau_signal_si_la_divergence_change_et_aucun_apres_resorption(self):
        self._echange(self.relais)
        signaler_divergence(self.feuille)
        self._echange(self.marin_service)
        signaler_divergence(self.feuille)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.divergence_signalee, "")
        self._echange(self.relais)
        signaler_divergence(self.feuille)
        self.assertEqual(self._notifs().filter(user=self.equipier).count(), 2)

    def test_pas_de_signal_pendant_un_rectificatif_ni_apres_sa_publication(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        signaler_divergence(self.feuille)
        self.assertFalse(self._notifs().exists())
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        signaler_divergence(self.feuille)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.divergence_signalee, "")
        self.assertFalse(self._notifs().exists())

    def test_echange_valide_declenche_le_signal(self):
        from quarts.echanges import accepter_echange, proposer_echange, valider_echange
        garde = self.creneau.service_garde
        debut = self.creneau.debut
        autre = CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Autre poste", debut=debut, fin=self.creneau.fin, marin=self.relais,
        )
        # Tours du jour déjà commencés, chef de liste hors sujet : on neutralise ces seuls contrôles.
        with mock.patch("quarts.echanges.analyser_echange", return_value=[]), \
                mock.patch("quarts.echanges.peut_valider_echange", return_value=True):
            echange = proposer_echange(self.marin_service, self.creneau, autre, "test")
            accepter_echange(echange, self.relais)
            echange.refresh_from_db()
            valider_echange(echange, self.chef_service)
        self.assertEqual(self._notifs().filter(user=self.equipier).count(), 1)


class EchangeValideTests(RectificatifBase):
    """Échanges validés via la vraie procédure (délai et chef de liste neutralisés)."""

    def _valider(self, creneau_a, creneau_b, demandeur, cible):
        from quarts.echanges import accepter_echange, proposer_echange, valider_echange
        with mock.patch("quarts.echanges.analyser_echange", return_value=[]), \
                mock.patch("quarts.echanges.peut_valider_echange", return_value=True):
            echange = proposer_echange(demandeur, creneau_a, creneau_b, "test")
            accepter_echange(echange, cible)
            echange.refresh_from_db()
            valider_echange(echange, self.chef_service)

    def _autre_poste(self):
        return CreneauServiceGarde.objects.create(
            service_garde=self.creneau.service_garde, poste="Autre poste", debut=self.creneau.debut,
            fin=self.creneau.fin, marin=self.relais,
        )

    def _feuille_publiee_autre_navire(self):
        fonction = FonctionFeuilleService.objects.create(ship=self.autre_ship, libelle="Officier de garde", ordre=1)
        redacteur = _utilisateur("redacteur_autre", "EQUIPIER", ship=self.autre_ship)
        titulaire = _utilisateur("titulaire_autre", "EQUIPIER", ship=self.autre_ship)
        relais = _utilisateur("relais_autre", "EQUIPIER", ship=self.autre_ship)
        garde = ServiceGarde.objects.create(
            ship=self.autre_ship, fonction=self.fonction_choice, date_debut=self.jour, date_fin=self.jour,
            statut=ServiceGarde.STATUT_PUBLIEE,
        )
        creneau = CreneauServiceGarde.objects.create(
            service_garde=garde, poste=fonction.libelle, debut=self.creneau.debut, fin=self.creneau.fin, marin=titulaire,
        )
        feuille = FeuilleService.objects.create(ship=self.autre_ship, date=self.jour, created_by=redacteur)
        feuille.creer_version(redacteur)
        FeuilleService.objects.filter(pk=feuille.pk).update(statut=FeuilleService.STATUT_PUBLIEE)
        creneau.marin = relais
        creneau.save(update_fields=["marin", "updated_at"])
        return feuille

    def test_un_echange_n_evalue_pas_les_feuilles_d_un_autre_batiment(self):
        autre = self._feuille_publiee_autre_navire()
        self.assertTrue(divergences_effectives(autre))
        self._valider(self.creneau, self._autre_poste(), self.marin_service, self.relais)
        self.assertEqual(
            sorted(Notification.objects.filter(verb__icontains="rectificatif à préparer").values_list("user__username", flat=True)),
            ["bsc", "etat_major"],
        )
        autre.refresh_from_db()
        self.assertEqual(autre.divergence_signalee, "")

    def test_une_erreur_de_signalement_est_tracee_puis_retentee(self):
        from quarts import rectificatif
        from quarts.models import EchangeService
        reel = rectificatif.signaler_divergence
        appels = []

        def panne_une_fois(feuille):
            appels.append(feuille.pk)
            if len(appels) == 1:
                raise RuntimeError("panne")
            return reel(feuille)

        with mock.patch("quarts.rectificatif.signaler_divergence", side_effect=panne_une_fois):
            self._valider(self.creneau, self._autre_poste(), self.marin_service, self.relais)
            self.assertEqual(EchangeService.objects.get().statut, EchangeService.STATUT_VALIDE)
            self.creneau.refresh_from_db()
            self.assertEqual(self.creneau.marin, self.relais)
            trace = AuditLog.objects.get(action="feuille_service_signalement_echoue")
            self.assertIn("RuntimeError", trace.details)
            self.assertIn(f"{self.jour:%d/%m/%Y}", trace.details)
            self.feuille.refresh_from_db()
            self.assertEqual(self.feuille.divergence_signalee, "")
            self.assertFalse(self._notifs().exists())
            call_command("signaler_divergences_feuilles")
            call_command("signaler_divergences_feuilles")
        self.assertEqual(sorted(self._notifs().values_list("user__username", flat=True)), ["bsc", "etat_major"])

    def test_echange_apres_proposition_puis_apres_visa_service_figé_au_dernier_titulaire(self):
        autre = _utilisateur("marin_autre", "EQUIPIER", ship=self.ship)
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.chef_service)
        self._echange(autre)
        self.feuille.viser_service(self.chef_service)
        self._echange(self.marin_service)
        self.feuille.viser_comaeq(self.etat_major)
        self.assertEqual(self.feuille.versions.first().contenu_fige["personnel"][0]["marin"], "marin_service")

    def test_echange_avant_puis_apres_publication(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        self.assertEqual(divergences_effectives(self.feuille), [])
        # Échange après publication : divergence mesurée contre la NOUVELLE version.
        self._echange(self.marin_service)
        signaler_divergence(self.feuille)
        diff = divergences_effectives(self.feuille)
        self.assertEqual([(d["avant"], d["apres"]) for d in diff][0], ("marin_relais", "marin_service"))
        self.assertEqual(self._notifs().filter(user=self.equipier).count(), 1)
        self.assertIn("version 2", self._notifs().first().verb)

    def _notifs(self):
        return Notification.objects.filter(verb__icontains="rectificatif à préparer")


@skipUnless(connection.vendor == "postgresql", "Verrous de ligne : PostgreSQL requis")
class ConcurrencePublicationTests(TransactionTestCase):
    """Course réelle (threads) entre la publication d'un rectificatif et la validation d'un échange."""

    def setUp(self):
        FeuilleServiceTestsBase.setUp(self)
        self.relais = _utilisateur("marin_relais", "EQUIPIER", ship=self.ship)
        self.autre = _utilisateur("marin_autre", "EQUIPIER", ship=self.ship)
        creneau = FeuilleServiceTestsBase._publier_tour(self, marin=self.marin_service)
        self.creneau = creneau
        self.autre_creneau = CreneauServiceGarde.objects.create(
            service_garde=creneau.service_garde, poste="Autre poste", debut=creneau.debut, fin=creneau.fin,
            marin=self.autre,
        )
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        # Rectificatif prêt pour le visa COMAEQ, titulaire effectif = relais.
        creneau.marin = self.relais
        creneau.save(update_fields=["marin", "updated_at"])
        self.feuille.refresh_from_db()
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        from quarts.echanges import accepter_echange, proposer_echange
        with mock.patch("quarts.echanges.analyser_echange", return_value=[]):
            self.echange = proposer_echange(self.relais, creneau, self.autre_creneau, "test")
            accepter_echange(self.echange, self.autre)
        self.echange.refresh_from_db()
        self.erreurs = []

    def _fil(self, cible):
        def executer():
            try:
                cible()
            except Exception as erreur:  # pragma: no cover
                self.erreurs.append(erreur)
            finally:
                connection.close()
        return threading.Thread(target=executer)

    def _valider_echange(self):
        from quarts.echanges import valider_echange
        with mock.patch("quarts.echanges.analyser_echange", return_value=[]), \
                mock.patch("quarts.echanges.peut_valider_echange", return_value=True):
            valider_echange(self.echange, self.chef_service)

    def _publier(self):
        FeuilleService.objects.get(pk=self.feuille.pk).viser_comaeq(self.etat_major)

    def _notifs(self):
        return Notification.objects.filter(verb__icontains="rectificatif à préparer")

    def test_publication_la_premiere_l_echange_est_signale_avec_la_nouvelle_version(self):
        lu, p = threading.Event(), None
        reel = FeuilleService.contenu_courant

        def contenu_ralenti(feuille):
            resultat = reel(feuille)
            if threading.current_thread() is p:
                lu.set()
                time.sleep(1.5)
            return resultat

        def echange():
            lu.wait(15)
            self._valider_echange()

        p = self._fil(self._publier)
        e = self._fil(echange)
        with mock.patch.object(FeuilleService, "contenu_courant", contenu_ralenti):
            p.start(); e.start(); p.join(60); e.join(60)
        self.assertEqual(self.erreurs, [])
        feuille = FeuilleService.objects.get(pk=self.feuille.pk)
        self.assertEqual(feuille.statut, FeuilleService.STATUT_PUBLIEE)
        # Le titulaire effectif à l'instant de la lecture (relais) est publié ; l'échange validé ensuite est signalé.
        self.assertEqual(feuille.versions.first().contenu_fige["personnel"][0]["marin"], "marin_relais")
        self.assertEqual(feuille.versions.first().numero, 2)
        self.assertEqual(sorted(self._notifs().values_list("user__username", flat=True)), ["bsc", "etat_major"])
        self.assertIn("version 2", self._notifs().first().verb)
        self.assertNotEqual(feuille.divergence_signalee, "")

    def test_echange_le_premier_la_publication_perimee_est_refusee(self):
        verrou_pris = threading.Event()
        reel = __import__("quarts.rectificatif", fromlist=["x"]).signaler_divergence

        def signaler_lentement(feuille):
            reel(feuille)
            verrou_pris.set()
            time.sleep(1.5)

        def publier():
            verrou_pris.wait(15)
            self._publier()

        e = self._fil(self._valider_echange)
        p = self._fil(publier)
        with mock.patch("quarts.rectificatif.signaler_divergence", signaler_lentement):
            e.start(); p.start(); e.join(60); p.join(60)
        self.assertEqual(self.erreurs, [])
        feuille = FeuilleService.objects.get(pk=self.feuille.pk)
        self.assertEqual(feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertEqual(feuille.versions.count(), 1)
        self.assertEqual(feuille.rectificatif_ouvert_par, self.equipier)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_visa_perime").exists())
        # Nouvelle séquence de visa : la version publiée porte le dernier titulaire.
        feuille.proposer(self.chef_service)
        feuille.viser_service(self.chef_service)
        self.assertTrue(feuille.viser_comaeq(self.etat_major))
        self.assertEqual(feuille.versions.first().contenu_fige["personnel"][0]["marin"], "marin_autre")


class VisaPerimeTests(RectificatifBase):
    def _rectificatif_au_visa_comaeq(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)

    def test_echange_apres_le_visa_service_refuse_la_publication_puis_nouvelle_sequence(self):
        self._rectificatif_au_visa_comaeq()
        self._echange(self.commandant)
        self.assertFalse(self.feuille.viser_comaeq(self.etat_major))
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertIsNone(self.feuille.visa_service_le)
        self.assertEqual(self.feuille.empreinte_visee, "")
        self.assertEqual(self.feuille.versions.count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_visa_perime").exists())
        self.assertTrue(Notification.objects.filter(user=self.equipier, verb__icontains="Une information a changé depuis le visa").exists())
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.assertTrue(self.feuille.viser_comaeq(self.etat_major))
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.versions.first().contenu_fige["personnel"][0]["marin"], "commandant")

    def test_echange_avant_le_visa_publie_normalement(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.chef_service)
        self._echange(self.commandant)
        self.feuille.viser_service(self.chef_service)
        self.assertTrue(self.feuille.viser_comaeq(self.etat_major))
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.versions.first().contenu_fige["personnel"][0]["marin"], "commandant")

    def test_la_vue_affiche_le_refus(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self._echange(self.commandant)
        reponse = self._post("etat_major", "viser_comaeq")
        self.assertEqual(reponse.status_code, 302)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertEqual(self.feuille.versions.count(), 1)


class EtatDeDivergencePreserveTests(RectificatifBase):
    """Ni le renvoi, ni le visa périmé, ni une erreur de publication n'effacent l'état nécessaire au rectificatif."""

    def _etat(self):
        self.feuille.refresh_from_db()
        return (
            self.feuille.divergence_signalee, self.feuille.rectificatif_ouvert_par_id,
            self.feuille.versions.count(), [(d["libelle"], d["avant"], d["apres"]) for d in divergences_effectives(self.feuille)],
        )

    def _preparer(self):
        self._echange(self.relais)
        signaler_divergence(self.feuille)
        self.feuille.ouvrir_rectificatif(self.equipier)
        return self._etat()

    def test_renvoi_et_reproposition(self):
        avant = self._preparer()
        self.feuille.proposer(self.equipier)
        self.feuille.renvoyer(self.chef_secteur, "À revoir")
        self.assertEqual(self._etat(), avant)

    def test_annulation_par_visa_perime(self):
        avant = self._preparer()
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self._echange(self.commandant)
        self.assertFalse(self.feuille.viser_comaeq(self.etat_major))
        apres = self._etat()
        self.assertEqual(apres[:3], avant[:3])
        self.assertTrue(apres[3])

    def test_erreur_a_la_publication(self):
        avant = self._preparer()
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        with mock.patch.object(FeuilleService, "creer_version", side_effect=RuntimeError("échec")):
            with self.assertRaises(RuntimeError):
                self.feuille.viser_comaeq(self.etat_major)
        self.assertEqual(self._etat(), avant)
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)

    def test_la_publication_remet_a_zero_seulement_apres_succes(self):
        self._preparer()
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.assertTrue(self.feuille.viser_comaeq(self.etat_major))
        self.feuille.refresh_from_db()
        self.assertEqual((self.feuille.divergence_signalee, self.feuille.rectificatif_ouvert_par_id), ("", None))


class DroitsRectificatifTests(RectificatifBase):
    def test_marin_d_un_autre_navire_ne_peut_ni_lire_ni_ouvrir(self):
        _utilisateur("etranger", "EQUIPIER", ship=self.autre_ship)
        self._echange(self.relais)
        self.assertEqual(self._post("etranger", "ouvrir_rectificatif").status_code, 403)
        self.assertEqual(self._page("etranger").status_code, 403)

    def test_feuille_non_publiee_pas_d_ouverture(self):
        feuille = FeuilleService.objects.create(ship=self.ship, date=self.jour + timezone.timedelta(days=1))
        url = reverse("feuille-service-detail", args=[self.ship.pk, f"{feuille.date:%Y-%m-%d}"])
        self.client.force_login(self.equipier)
        self.assertEqual(self.client.post(url, {"action": "ouvrir_rectificatif"}).status_code, 403)

    def test_lecture_pendant_rectificatif_reservee_au_navire(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.refresh_from_db()
        self.assertTrue(peut_lire_feuille_service(self.marin_service, self.feuille))
        self.assertFalse(peut_lire_feuille_service(User.objects.get(username="etat_major_autre"), self.feuille))


class DoubleEquipageRectificatifTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(
            name="FREMM Rectif", code="FRE", classe_navire="FREMM", double_equipage=True, equipage_a_bord="A",
        )
        self.jour = timezone.localdate()
        self.fonction = FonctionFeuilleService.objects.create(ship=self.ship, libelle="Officier de garde", ordre=1)
        choix = ServiceFunctionChoice.objects.create(name="Officier de garde")
        self.marins = {}
        for e in ("A", "B"):
            for nom, role, coma in ((f"redacteur_{e}", "EQUIPIER", ""), (f"chef_{e}", "COMMANDANT", ""),
                                    (f"comaeq_{e}", "ETAT_MAJOR", "COMAEQ"), (f"titulaire_{e}", "EQUIPIER", ""),
                                    (f"relais_{e}", "EQUIPIER", "")):
                user = User.objects.create_user(username=nom, password="pass")
                UserProfile.objects.update_or_create(user=user, defaults={
                    "role": role, "ship": self.ship, "equipage": e, "fonction_coma": coma})
                self.marins[nom] = User.objects.get(pk=user.pk)
        self.url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.jour:%Y-%m-%d}"])
        garde = ServiceGarde.objects.create(
            ship=self.ship, fonction=choix, date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = timezone.make_aware(datetime.combine(self.jour, datetime.min.time().replace(hour=8)))
        self.creneaux = {
            e: CreneauServiceGarde.objects.create(
                service_garde=garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24),
                marin=self.marins[f"titulaire_{e}"],
            )
            for e in ("A", "B")
        }
        for e in ("A", "B"):
            feuille = FeuilleService.objects.create(
                ship=self.ship, equipage=e, date=self.jour, created_by=self.marins[f"redacteur_{e}"],
            )
            feuille.proposer(self.marins[f"chef_{e}"])
            feuille.viser_service(self.marins[f"chef_{e}"])
            feuille.viser_comaeq(self.marins[f"comaeq_{e}"])

    def _post(self, nom, action, suffixe=""):
        self.client.force_login(self.marins[nom])
        donnees = {"action": action}
        if action == "viser_comaeq":
            donnees["jeton_visa"] = jeton_visa_affiche(self.client, self.url + suffixe)
        return self.client.post(self.url + suffixe, donnees)

    def _echange(self, e):
        c = self.creneaux[e]
        c.marin = self.marins[f"relais_{e}"]
        c.save(update_fields=["marin", "updated_at"])

    def test_l_equipage_a_terre_ouvre_et_publie_le_rectificatif_de_sa_feuille(self):
        self._echange("B")
        self.assertEqual(self._post("redacteur_B", "ouvrir_rectificatif").status_code, 302)
        self._post("chef_B", "proposer")
        self._post("chef_B", "viser_service")
        self._post("comaeq_B", "viser_comaeq")
        feuille = FeuilleService.objects.get(ship=self.ship, equipage="B", date=self.jour)
        self.assertEqual(feuille.versions.count(), 2)
        self.assertEqual(feuille.versions.first().remplace_numero, 1)
        autre = FeuilleService.objects.get(ship=self.ship, equipage="A", date=self.jour)
        self.assertEqual(autre.versions.count(), 1)

    def test_rectificatif_d_un_equipage_refuse_a_l_autre(self):
        self._echange("B")
        # Le paramètre forgé est ignoré : la feuille résolue est celle de l'équipage du rédacteur, sans divergence.
        self._post("redacteur_A", "ouvrir_rectificatif", "?equipage=B")
        self._post("redacteur_A", "ouvrir_rectificatif")
        self.assertFalse(FeuilleService.objects.get(ship=self.ship, equipage="A", date=self.jour).rectificatif_en_cours)
        self.assertFalse(FeuilleService.objects.get(ship=self.ship, equipage="B", date=self.jour).rectificatif_en_cours)

    def test_la_divergence_d_un_equipage_n_apparait_pas_chez_l_autre(self):
        self._echange("B")
        self.client.force_login(self.marins["redacteur_A"])
        self.assertNotContains(self.client.get(self.url), "ont changé depuis la publication")
        self.client.force_login(self.marins["redacteur_B"])
        self.assertContains(self.client.get(self.url), "ont changé depuis la publication")

    def test_le_comaeq_de_l_autre_equipage_ne_vise_pas_le_rectificatif(self):
        self._echange("B")
        self._post("redacteur_B", "ouvrir_rectificatif")
        self._post("chef_B", "proposer")
        self._post("chef_B", "viser_service")
        self.assertEqual(self._post("comaeq_A", "viser_comaeq").status_code, 403)

    def test_signal_cible_sur_l_equipage_concerne(self):
        self._echange("B")
        for e in ("A", "B"):
            signaler_divergence(FeuilleService.objects.get(ship=self.ship, equipage=e, date=self.jour))
        destinataires = set(
            Notification.objects.filter(verb__icontains="rectificatif à préparer").values_list("user__username", flat=True)
        )
        self.assertEqual(destinataires, {"redacteur_B", "comaeq_B"})

    def test_echange_valide_via_la_procedure_ne_signale_que_l_equipage_concerne(self):
        from quarts.echanges import accepter_echange, proposer_echange, valider_echange
        autre = CreneauServiceGarde.objects.create(
            service_garde=self.creneaux["A"].service_garde, poste="Autre poste", debut=self.creneaux["A"].debut,
            fin=self.creneaux["A"].fin, marin=self.marins["relais_A"],
        )
        with mock.patch("quarts.echanges.analyser_echange", return_value=[]), \
                mock.patch("quarts.echanges.peut_valider_echange", return_value=True):
            echange = proposer_echange(self.marins["titulaire_A"], self.creneaux["A"], autre, "test")
            accepter_echange(echange, self.marins["relais_A"])
            echange.refresh_from_db()
            valider_echange(echange, self.marins["chef_A"])
        destinataires = set(
            Notification.objects.filter(verb__icontains="rectificatif à préparer").values_list("user__username", flat=True)
        )
        self.assertEqual(destinataires, {"redacteur_A", "comaeq_A"})
        self.assertEqual(FeuilleService.objects.get(ship=self.ship, equipage="B", date=self.jour).divergence_signalee, "")
