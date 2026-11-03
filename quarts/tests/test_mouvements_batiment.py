"""Accostage / appareillage : droits, chronologie, correction motivée et alertes d'accostage sans liste applicable."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from notifications.models import Notification
from quarts.models import AlerteAccostage, MouvementBatiment, ServiceGarde
from quarts.mouvements import regime_du_batiment
from quarts.tests.test_activation_liste_quai import BaseActivation


class MouvementsBatimentTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self.url_mv = reverse("mouvements-batiment")

    def _declarer(self, user, type_="ACCOSTAGE", il_y_a=timedelta(minutes=10)):
        instant = (timezone.localtime() - il_y_a).strftime("%Y-%m-%dT%H:%M")
        self.client.force_login(user)
        return self.client.post(self.url_mv, {"action": "declarer", "type": type_, "survenu_le": instant})

    def _alertes(self):
        return AlerteAccostage.objects.filter(fermee_le__isnull=True)

    def test_seuls_comaeq_et_commandant_declarent(self):
        for user in (self.chef, self.marin):
            self.assertEqual(self._declarer(user).status_code, 403)
        self._declarer(self.comaeq)
        mouvement = MouvementBatiment.objects.get()
        self.assertEqual((mouvement.fonction_declarante, mouvement.declare_par), ("COMAEQ", self.comaeq))
        self.assertEqual(regime_du_batiment(self.ship), "QUAI")

    def test_commandant_peut_declarer_un_appareillage(self):
        self._declarer(self.commandant, "APPAREILLAGE")
        self.assertEqual(regime_du_batiment(self.ship), "MER")
        self.assertEqual(MouvementBatiment.objects.get().fonction_declarante, "COMMANDANT")

    def test_chronologie_incoherente_refusee(self):
        self._declarer(self.comaeq, "ACCOSTAGE", timedelta(hours=2))
        self._declarer(self.comaeq, "ACCOSTAGE", timedelta(hours=1))
        self.assertEqual(MouvementBatiment.objects.count(), 1)
        self._declarer(self.comaeq, "APPAREILLAGE", timedelta(hours=3))  # antérieur à l'accostage : alternance respectée
        self.assertEqual(MouvementBatiment.objects.count(), 2)
        self._declarer(self.comaeq, "APPAREILLAGE", timedelta(hours=4))  # suivi d'un appareillage : refusé
        self.assertEqual(MouvementBatiment.objects.count(), 2)

    def test_date_future_refusee(self):
        self._declarer(self.comaeq, "ACCOSTAGE", -timedelta(hours=2))
        self.assertEqual(MouvementBatiment.objects.count(), 0)

    def test_accostage_sans_liste_alerte_chefs_et_comaeq(self):
        self.liste.delete()
        self._declarer(self.comaeq)
        alerte = self._alertes().get()
        self.assertEqual(alerte.genre, AlerteAccostage.GENRE_AUCUNE)
        self.assertEqual(Notification.objects.filter(user=self.chef, verb__contains="aucune liste").count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.comaeq, verb__contains="aucune liste").count(), 1)

    def test_previsionnelle_non_activee_alerte_distincte_et_persistante_au_report(self):
        self._previsionnelle()
        self._declarer(self.comaeq)
        self.assertEqual(self._alertes().get().genre, AlerteAccostage.GENRE_PREVISIONNELLE)
        nouvelle = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self._poster(self.chef, action="reporter", prise_effet_prevue=nouvelle, motif="Report")
        self.assertEqual(self._alertes().get().genre, AlerteAccostage.GENRE_PREVISIONNELLE)

    def test_activation_ferme_l_alerte_d_accostage(self):
        self._previsionnelle()
        self._declarer(self.comaeq)
        self._poster(self.chef, action="activer")
        self.assertFalse(self._alertes().exists())

    def test_publication_previsionnelle_fait_passer_aucune_liste_a_previsionnelle(self):
        self.liste.statut = ServiceGarde.STATUT_BROUILLON
        self.liste.save()
        self._declarer(self.comaeq)
        self.assertEqual(self._alertes().get().genre, AlerteAccostage.GENRE_AUCUNE)
        self.liste.statut = ServiceGarde.STATUT_PROPOSEE
        self.liste.save()
        self._previsionnelle()
        self.assertEqual(self._alertes().get().genre, AlerteAccostage.GENRE_PREVISIONNELLE)

    def test_annulation_motivee_ferme_l_alerte_et_garde_l_historique(self):
        self._previsionnelle()
        self._declarer(self.comaeq)
        mouvement = MouvementBatiment.objects.get()
        self.client.force_login(self.comaeq)
        self.client.post(self.url_mv, {"action": "annuler", "mouvement_id": mouvement.pk})
        mouvement.refresh_from_db()
        self.assertEqual(mouvement.statut, MouvementBatiment.STATUT_VALIDE)  # sans motif : refusé
        self.client.post(self.url_mv, {"action": "annuler", "mouvement_id": mouvement.pk, "motif": "Erreur de saisie"})
        mouvement.refresh_from_db()
        self.assertEqual(mouvement.statut, MouvementBatiment.STATUT_ANNULE)
        self.assertFalse(self._alertes().exists())
        self.assertIsNone(regime_du_batiment(self.ship))
        self.assertTrue(AuditLog.objects.filter(action="mouvement_batiment_annule", details__contains="Erreur de saisie").exists())

    def test_correction_remplace_la_declaration(self):
        self._declarer(self.comaeq, "ACCOSTAGE", timedelta(hours=1))
        ancien = MouvementBatiment.objects.get()
        corrige = (timezone.localtime() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        self.client.post(self.url_mv, {"action": "annuler", "mouvement_id": ancien.pk, "motif": "Heure erronée", "nouveau_survenu_le": corrige})
        self.assertEqual(MouvementBatiment.objects.filter(statut="VALIDE").count(), 1)
        self.assertEqual(MouvementBatiment.objects.get(statut="VALIDE").remplace, ancien)

    def test_non_habilite_ne_peut_pas_annuler(self):
        self._declarer(self.comaeq)
        mouvement = MouvementBatiment.objects.get()
        self.client.force_login(self.chef)
        self.assertEqual(self.client.post(self.url_mv, {"action": "annuler", "mouvement_id": mouvement.pk, "motif": "x"}).status_code, 403)
