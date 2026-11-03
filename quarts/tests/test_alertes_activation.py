"""Rappels, alertes, escalade, report et retrait d'une liste à quai prévisionnelle."""
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

    def test_escalade_vers_le_commandant_si_comaeq_vacant(self):
        self.comaeq.profile.fonction_coma = ""
        self.comaeq.profile.save()
        traiter_echeances(self.prevue + timedelta(minutes=16))
        self.assertEqual(self._notifs(self.commandant), 1)

    def test_delais_configurables_par_batiment(self):
        ConfigurationActivation.objects.create(ship=self.ship, rappel_minutes=60, alerte_minutes=10, escalade_minutes=5)
        self.assertEqual(traiter_echeances(self.prevue - timedelta(minutes=60)), 1)
        self.assertEqual(traiter_echeances(self.prevue + timedelta(minutes=9)), 0)
        self.assertEqual(traiter_echeances(self.prevue + timedelta(minutes=10)), 1)

    def test_pas_de_doublon_pour_une_personne_cumulant_les_fonctions(self):
        ChefDeListe.objects.create(user=self.comaeq, service=self.service)
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
