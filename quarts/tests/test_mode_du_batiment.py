"""Chronologie du mode MER / QUAI : initialisation, transitions, corrections successives, consultation historique, activation."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from quarts.models import MouvementBatiment, ServiceGarde
from quarts.mouvements import (
    MouvementImpossible,
    annuler_mouvement,
    declarer_mouvement,
    initialiser_mode,
    intervalles_par_mode,
    mode_du_batiment,
)
from quarts.tests.test_activation_liste_quai import BaseActivation


class ChronologieDuModeTests(BaseActivation):
    mode_initial = None

    def setUp(self):
        super().setUp()
        self.t0 = timezone.now() - timedelta(days=10)

    def _t(self, jours):
        return self.t0 + timedelta(days=jours)

    def test_mode_non_renseigne_par_defaut_et_jamais_deduit_d_une_liste(self):
        self._previsionnelle()  # une liste publiée existe
        self.assertIsNone(mode_du_batiment(self.ship))

    def test_initialisation_exige_motif_habilitation_et_valeur_valide(self):
        with self.assertRaises(MouvementImpossible):
            initialiser_mode(self.comaeq, self.ship, "QUAI", self._t(0), "")
        with self.assertRaises(MouvementImpossible):
            initialiser_mode(self.chef, self.ship, "QUAI", self._t(0), "Vérifié")
        with self.assertRaises(MouvementImpossible):
            initialiser_mode(self.comaeq, self.ship, "MOUILLAGE", self._t(0), "Vérifié")
        initialiser_mode(self.comaeq, self.ship, "QUAI", self._t(0), "Vérifié sur le journal de bord")
        self.assertEqual(mode_du_batiment(self.ship), "QUAI")
        mouvement = MouvementBatiment.objects.get()
        self.assertEqual((mouvement.type, mouvement.mode_avant, mouvement.mode_apres, mouvement.fonction_declarante), ("INITIALISATION", "", "QUAI", "COMAEQ"))

    def test_transitions_mer_quai_mer_avec_ancien_et_nouveau_mode(self):
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(2))
        declarer_mouvement(self.commandant, self.ship, "APPAREILLAGE", self._t(5))
        chaine = [(m.type, m.mode_avant, m.mode_apres) for m in MouvementBatiment.objects.order_by("survenu_le")]
        self.assertEqual(chaine, [("INITIALISATION", "", "MER"), ("ACCOSTAGE", "MER", "QUAI"), ("APPAREILLAGE", "QUAI", "MER")])
        self.assertEqual(mode_du_batiment(self.ship), "MER")

    def test_consultation_d_un_mode_historique(self):
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(2))
        declarer_mouvement(self.comaeq, self.ship, "APPAREILLAGE", self._t(5))
        self.assertIsNone(mode_du_batiment(self.ship, self._t(-1)))
        self.assertEqual(mode_du_batiment(self.ship, self._t(1)), "MER")
        self.assertEqual(mode_du_batiment(self.ship, self._t(3)), "QUAI")
        self.assertEqual(mode_du_batiment(self.ship, self._t(6)), "MER")

    def test_intervalles_par_mode_decoupent_la_journee_de_transition(self):
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(2) + timedelta(hours=10))
        intervalles = intervalles_par_mode(self.ship, self._t(2), self._t(3))
        self.assertEqual([i[2] for i in intervalles], ["MER", "QUAI"])
        self.assertEqual(intervalles[0][1], self._t(2) + timedelta(hours=10))

    def test_transitions_incoherentes_refusees(self):
        initialiser_mode(self.comaeq, self.ship, "QUAI", self._t(0), "Vérifié")
        with self.assertRaises(MouvementImpossible):
            declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(1))  # déjà à quai
        with self.assertRaises(MouvementImpossible):
            initialiser_mode(self.comaeq, self.ship, "MER", self._t(1), "Encore")  # déjà renseigné
        declarer_mouvement(self.comaeq, self.ship, "APPAREILLAGE", self._t(3))
        with self.assertRaises(MouvementImpossible):
            declarer_mouvement(self.comaeq, self.ship, "APPAREILLAGE", self._t(4))

    def test_accostage_anticipe_ou_retarde_par_correction_motivee(self):
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        accostage = declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(4))
        self.assertEqual(mode_du_batiment(self.ship, self._t(3)), "MER")
        annuler_mouvement(self.comaeq, accostage, "Accostage réel plus tôt", self._t(2))  # anticipé
        self.assertEqual(mode_du_batiment(self.ship, self._t(3)), "QUAI")
        nouveau = MouvementBatiment.objects.get(statut="VALIDE", type="ACCOSTAGE")
        annuler_mouvement(self.comaeq, nouveau, "En fait retardé", self._t(6))  # retardé
        self.assertEqual(mode_du_batiment(self.ship, self._t(3)), "MER")
        self.assertEqual(mode_du_batiment(self.ship, self._t(7)), "QUAI")
        with self.assertRaises(MouvementImpossible):
            annuler_mouvement(self.comaeq, nouveau, "", self._t(2))  # déjà annulé / motif manquant

    def test_corrections_successives_conservent_l_historique_et_recalculent_la_chronologie(self):
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        acc = declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(2))
        app = declarer_mouvement(self.comaeq, self.ship, "APPAREILLAGE", self._t(5))
        with self.assertRaises(MouvementImpossible):  # annuler l'accostage laisserait MER puis MER
            annuler_mouvement(self.comaeq, acc, "Erreur", None)
        annuler_mouvement(self.comaeq, app, "Appareillage non effectué", None)
        annuler_mouvement(self.comaeq, acc, "Accostage non effectué", None)
        self.assertEqual(mode_du_batiment(self.ship), "MER")
        self.assertEqual(MouvementBatiment.objects.count(), 3)  # rien n'est supprimé
        self.assertEqual(MouvementBatiment.objects.filter(statut="ANNULE").count(), 2)
        self.assertEqual(AuditLog.objects.filter(action="mouvement_batiment_annule").count(), 2)

    def test_correction_ne_modifie_aucune_affectation_passee(self):
        creneau = self.liste.creneaux.get()
        avant = (creneau.marin_id, creneau.debut, creneau.fin)
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        acc = declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", self._t(2))
        annuler_mouvement(self.comaeq, acc, "Heure erronée", self._t(3))
        creneau.refresh_from_db()
        self.assertEqual((creneau.marin_id, creneau.debut, creneau.fin), avant)

    def test_activation_refusee_si_mode_non_renseigne_puis_a_la_mer_puis_acceptee_a_quai(self):
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)
        declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", timezone.now() - timedelta(minutes=5))
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)

    def test_messages_metier_explicites_pour_l_activation_refusee(self):
        from quarts.activation import ActivationImpossible, activer_liste

        self._previsionnelle()
        with self.assertRaisesMessage(ActivationImpossible, "n'est pas renseigné"):
            activer_liste(self.chef, self.liste)
        initialiser_mode(self.comaeq, self.ship, "MER", self._t(0), "Vérifié")
        with self.assertRaisesMessage(ActivationImpossible, "est à la mer"):
            activer_liste(self.chef, self.liste)

    def test_le_chef_de_liste_ne_peut_ni_initialiser_ni_declarer(self):
        self.client.force_login(self.chef)
        donnees = {"action": "initialiser", "mode": "QUAI", "survenu_le": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "motif": "x"}
        self.assertEqual(self.client.post(reverse("mouvements-batiment"), donnees).status_code, 403)
        self.assertIsNone(mode_du_batiment(self.ship))

    def test_page_mouvements_invite_a_initialiser_et_consulte_une_date(self):
        self.client.force_login(self.comaeq)
        page = self.client.get(reverse("mouvements-batiment")).content.decode()
        self.assertIn("Non renseigné", page)
        self.assertIn("Initialiser le mode", page)
        initialiser_mode(self.comaeq, self.ship, "QUAI", self._t(0), "Vérifié")
        passe = self._t(2).astimezone().strftime("%Y-%m-%dT%H:%M")
        page = self.client.get(reverse("mouvements-batiment"), {"date": passe}).content.decode()
        self.assertIn("QUAI", page)

    def test_modes_figes_de_la_reprise_des_mouvements_existants(self):
        """Mouvements créés avant la notion de mode : le mode découle du type, jamais d'une liste."""
        import importlib

        from django.apps import apps

        migration = importlib.import_module("quarts.migrations.0019_mode_des_mouvements")
        acc = MouvementBatiment.objects.create(ship=self.ship, type="ACCOSTAGE", survenu_le=self._t(1), declare_par=self.comaeq, fonction_declarante="COMAEQ")
        app = MouvementBatiment.objects.create(ship=self.ship, type="APPAREILLAGE", survenu_le=self._t(3), declare_par=self.comaeq, fonction_declarante="COMAEQ")
        migration.renseigner_les_modes(apps, None)
        acc.refresh_from_db(); app.refresh_from_db()
        self.assertEqual((acc.mode_avant, acc.mode_apres, app.mode_avant, app.mode_apres), ("", "QUAI", "QUAI", "MER"))
        self.assertEqual(mode_du_batiment(self.ship, self._t(2)), "QUAI")


class InitialisationDemonstrationTests(BaseActivation):
    mode_initial = None

    def test_modes_de_demonstration_explicites_traces_et_idempotents(self):
        from quarts.mouvements import MODES_DE_DEMONSTRATION, initialiser_modes_de_demonstration

        self.ship.name = "Bretagne"
        self.ship.save()
        lignes = initialiser_modes_de_demonstration(timezone.now() - timedelta(days=30))
        self.assertEqual(mode_du_batiment(self.ship), MODES_DE_DEMONSTRATION["Bretagne"])
        self.assertTrue(any("Jacques Chevallier : absent" in ligne for ligne in lignes))
        mouvement = MouvementBatiment.objects.get()
        self.assertEqual(mouvement.type, "INITIALISATION")
        self.assertIn("démonstration", mouvement.motif)
        self.assertTrue(AuditLog.objects.filter(action="mouvement_batiment_declare", details__contains="Bretagne").exists())
        initialiser_modes_de_demonstration(timezone.now() - timedelta(days=30))
        self.assertEqual(MouvementBatiment.objects.count(), 1)

    def test_commande_d_initialisation_exige_un_auteur_habilite_et_un_motif(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("initialiser_mode_batiment", batiment=self.ship.code, mode="QUAI", par=self.chef.username, motif="x")
        call_command("initialiser_mode_batiment", batiment=self.ship.code, mode="QUAI", par=self.comaeq.username, motif="Journal de bord")
        self.assertEqual(mode_du_batiment(self.ship), "QUAI")
        with self.assertRaises(CommandError):
            call_command("initialiser_mode_batiment", batiment=self.ship.code, mode="MER", par=self.comaeq.username, motif="Encore")
