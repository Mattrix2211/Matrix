"""Rappels, alertes, escalade, report et retrait d'une liste à quai prévisionnelle."""
from quarts.tests.support import designer_chef
from datetime import timedelta

from django.utils import timezone

from accounts.models import AuditLog
from notifications.models import Notification
from quarts.alertes_activation import _creer_alerte, traiter_echeances
from quarts.models import AlerteActivation, ChefDeListe, ConfigurationActivation, ServiceGarde
from quarts.tests.test_activation_liste_quai import BaseActivation


class AlertesActivationTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self.prevue = timezone.now() + timedelta(hours=3)
        self._previsionnelle()
        ServiceGarde.objects.filter(pk=self.liste.pk).update(prise_effet_prevue=self.prevue)
        self.liste.refresh_from_db()

    def _notifs(self, user):
        return Notification.objects.filter(user=user).count()

    def test_rien_avant_l_echeance_du_rappel(self):
        self.assertEqual(traiter_echeances(self.prevue - timedelta(minutes=31)), 0)

    def test_rappel_au_chef_de_liste_seulement_et_une_seule_fois(self):
        avant = self._notifs(self.chef)
        self.assertEqual(traiter_echeances(self.prevue - timedelta(minutes=30)), 1)
        self.assertEqual(traiter_echeances(self.prevue - timedelta(minutes=29)), 0)
        self.assertEqual(self._notifs(self.chef), avant + 1)
        self.assertEqual(self._notifs(self.comaeq), 0)

    def test_alerte_puis_escalade_vers_le_comaeq(self):
        traiter_echeances(self.prevue + timedelta(minutes=1))
        self.assertTrue(AlerteActivation.objects.filter(liste=self.liste, etape="ALERTE").exists())
        self.assertEqual(self._notifs(self.comaeq), 0)
        traiter_echeances(self.prevue + timedelta(minutes=16))
        self.assertEqual(self._notifs(self.comaeq), 1)
        self.assertEqual(self._notifs(self.commandant), 0)

    def test_escalade_vers_le_commandant_en_second_si_comaeq_vacant(self):
        second = self._user("csd", "COMMANDANT_EN_SECOND")
        self.comaeq.profile.fonction_coma = ""
        self.comaeq.profile.save()
        traiter_echeances(self.prevue + timedelta(minutes=1))
        traiter_echeances(self.prevue + timedelta(minutes=16))
        self.assertEqual(self._notifs(second), 1)
        self.assertEqual(self._notifs(self.commandant), 0)  # le commandant n'est plus le repli

    def test_le_commandant_en_second_n_obtient_aucun_droit_d_activer_ni_de_reporter(self):
        second = self._user("csd", "COMMANDANT_EN_SECOND")
        nouvelle = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self._poster(second, action="activer")
        self._poster(second, action="reporter", prise_effet_prevue=nouvelle, motif="Supervision")
        self._poster(second, action="retirer_previsionnelle", motif="Supervision")
        self.liste.refresh_from_db()
        self.assertEqual((self.liste.application, self.liste.statut, self.liste.version_prevision),
                         (ServiceGarde.APPLICATION_PREVISIONNELLE, ServiceGarde.STATUT_PUBLIEE, 1))

    def test_le_commandant_ne_peut_ni_reporter_ni_retirer(self):
        nouvelle = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self._poster(self.commandant, action="reporter", prise_effet_prevue=nouvelle, motif="Supervision")
        self._poster(self.commandant, action="retirer_previsionnelle", motif="Supervision")
        self.liste.refresh_from_db()
        self.assertEqual((self.liste.statut, self.liste.version_prevision), (ServiceGarde.STATUT_PUBLIEE, 1))

    def test_delais_configurables_par_batiment(self):
        ConfigurationActivation.objects.create(ship=self.ship, rappel_minutes=60, alerte_minutes=10, escalade_minutes=5)
        self.assertEqual(traiter_echeances(self.prevue - timedelta(minutes=60)), 1)
        self.assertEqual(traiter_echeances(self.prevue + timedelta(minutes=9)), 0)
        self.assertEqual(traiter_echeances(self.prevue + timedelta(minutes=10)), 1)

    def test_pas_de_doublon_pour_une_personne_cumulant_les_fonctions(self):
        designer_chef(user=self.comaeq, service=self.service)
        traiter_echeances(self.prevue - timedelta(minutes=30))
        traiter_echeances(self.prevue + timedelta(minutes=1))
        traiter_echeances(self.prevue + timedelta(minutes=16))
        # Rappel, alerte (en tant que chef) et escalade (en tant que COMAEQ) : un message par signal, aucun doublon
        self.assertEqual(self._notifs(self.comaeq), 3)
        self.assertEqual(AlerteActivation.objects.filter(liste=self.liste).count(), 3)

    def test_creation_concurrente_protegee_par_l_unicite(self):
        self.assertIsNotNone(_creer_alerte(self.liste, "RAPPEL"))
        self.assertIsNone(_creer_alerte(self.liste, "RAPPEL"))

    def test_activation_ferme_les_alertes(self):
        traiter_echeances(self.prevue + timedelta(minutes=1))
        self._poster(self.chef, action="activer")
        self.assertFalse(AlerteActivation.objects.filter(liste=self.liste, fermee_le__isnull=True).exists())
        self.assertTrue(AlerteActivation.objects.filter(motif_fermeture="liste activée").exists())

    def test_report_exige_motif_et_chef_et_futur(self):
        nouvelle = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self._poster(self.chef, action="reporter", prise_effet_prevue=nouvelle)
        self._poster(self.commandant, action="reporter", prise_effet_prevue=nouvelle, motif="Retard")
        self._poster(self.chef, action="reporter", prise_effet_prevue="2000-01-01T10:00", motif="Passé")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.version_prevision, 1)  # aucun des trois reports invalides n'a été appliqué

    def test_report_decale_les_alertes_et_ferme_les_obsoletes(self):
        traiter_echeances(self.prevue + timedelta(minutes=1))
        nouvelle = timezone.now() + timedelta(days=1)
        self._poster(self.chef, action="reporter", prise_effet_prevue=nouvelle.strftime("%Y-%m-%dT%H:%M"), motif="Accostage retardé")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.version_prevision, 2)
        self.assertFalse(AlerteActivation.objects.filter(liste=self.liste, version_prevision=1, fermee_le__isnull=True).exists())
        self.assertEqual(traiter_echeances(timezone.now()), 0)  # rien de dû avec la nouvelle échéance
        self.assertTrue(AuditLog.objects.filter(action="liste_service_reportee", details__contains="Accostage retardé").exists())

    def test_retrait_de_la_prevision(self):
        traiter_echeances(self.prevue + timedelta(minutes=1))
        self._poster(self.chef, action="retirer_previsionnelle")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.statut, ServiceGarde.STATUT_PUBLIEE)
        self._poster(self.chef, action="retirer_previsionnelle", motif="Erreur de saisie")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.statut, ServiceGarde.STATUT_BROUILLON)
        self.assertFalse(AlerteActivation.objects.filter(liste=self.liste, fermee_le__isnull=True).exists())


class AlertesTardivesTests(BaseActivation):
    """Publication après l'heure prévue de prise d'effet : pas de rappel rétrospectif ni de notifications simultanées."""

    def setUp(self):
        super().setUp()
        self._previsionnelle()
        self.prevue = timezone.now() - timedelta(minutes=40)  # déjà dépassée de 40 min à la publication
        ServiceGarde.objects.filter(pk=self.liste.pk).update(prise_effet_prevue=self.prevue)
        self.liste.refresh_from_db()
        self.maintenant = timezone.now()

    def _etapes(self):
        return sorted(AlerteActivation.objects.filter(liste=self.liste).values_list("etape", flat=True))

    def test_pas_de_rappel_retrospectif_et_pas_d_escalade_immediate(self):
        traiter_echeances(self.maintenant)
        self.assertEqual(self._etapes(), ["ALERTE"])
        verbes = list(Notification.objects.filter(user=self.chef).values_list("verb", flat=True))
        self.assertEqual(len(verbes), 1)
        self.assertIn("devait prendre effet", verbes[0])
        self.assertFalse(any(v.startswith("Rappel") for v in verbes))
        self.assertEqual(Notification.objects.filter(user=self.comaeq).count(), 0)

    def test_l_escalade_attend_le_delai_depuis_le_declenchement_reel_de_l_alerte(self):
        traiter_echeances(self.maintenant)
        traiter_echeances(self.maintenant + timedelta(minutes=14))
        self.assertEqual(self._etapes(), ["ALERTE"])
        traiter_echeances(self.maintenant + timedelta(minutes=15))
        self.assertEqual(self._etapes(), ["ALERTE", "ESCALADE"])
        self.assertEqual(Notification.objects.filter(user=self.comaeq).count(), 1)

    def test_aucune_notification_redondante_en_cas_de_reevaluation(self):
        for minutes in (0, 1, 5, 15, 16, 60):
            traiter_echeances(self.maintenant + timedelta(minutes=minutes))
        self.assertEqual(AlerteActivation.objects.filter(liste=self.liste).count(), 2)
        self.assertEqual(Notification.objects.filter(user=self.chef).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.comaeq).count(), 1)

    def test_le_report_apres_une_alerte_tardive_repart_sur_un_cycle_normal(self):
        traiter_echeances(self.maintenant)
        nouvelle = self.maintenant + timedelta(hours=2)
        self._poster(self.chef, action="reporter", prise_effet_prevue=timezone.localtime(nouvelle).strftime("%Y-%m-%dT%H:%M"), motif="Accostage retardé")
        self.assertFalse(AlerteActivation.objects.filter(liste=self.liste, fermee_le__isnull=True).exists())
        self.liste.refresh_from_db()
        traiter_echeances(self.maintenant + timedelta(minutes=95))  # H-25 : le rappel est de nouveau pertinent
        self.assertEqual(sorted(AlerteActivation.objects.filter(liste=self.liste, fermee_le__isnull=True).values_list("etape", flat=True)), ["RAPPEL"])

    def test_un_retard_de_traitement_ne_declenche_pas_un_rappel_apres_l_heure(self):
        ServiceGarde.objects.filter(pk=self.liste.pk).update(prise_effet_prevue=timezone.now() - timedelta(minutes=5))
        self.liste.refresh_from_db()
        traiter_echeances(timezone.now())  # première évaluation 5 minutes après l'heure prévue
        self.assertEqual(self._etapes(), ["ALERTE"])
