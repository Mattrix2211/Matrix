"""Les autres modules distinguent une liste prévisionnelle d'une liste en vigueur ; échanges différés ; terminaison automatique."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from calendar_app.evenements_sources import _creneaux_garde_assignes
from dashboard.aujourdhui import journee
from notifications.models import Notification
from quarts.alertes_activation import traiter_echeances
from quarts.echanges import accepter_echange, proposer_echange, valider_echange
from quarts.models import CreneauServiceGarde, EchangeService, ServiceGarde
from quarts.services import prochains_tours_de_service
from quarts.tests.test_activation_liste_quai import BaseActivation


class ModulesListePrevisionnelleTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self.autre = self._user("autre", "EQUIPIER", service=self.service)
        debut = self.liste.creneaux.get().debut + timedelta(days=2)
        CreneauServiceGarde.objects.create(service_garde=self.liste, poste="G2", debut=debut, fin=debut + timedelta(hours=24), marin=self.autre)
        self.creneau_marin = self.liste.creneaux.get(marin=self.marin)
        self.creneau_autre = self.liste.creneaux.get(marin=self.autre)
        self._previsionnelle()
        self.jour = timezone.localtime(self.creneau_marin.debut).date()

    def test_calendrier_signale_le_previsionnel_et_les_modules_de_service_l_ignorent(self):
        creneaux = list(_creneaux_garde_assignes(self.jour, self.jour, self.marin))
        self.assertEqual(len(creneaux), 1)
        self.assertTrue(creneaux[0].previsionnel)
        self.assertEqual(list(_creneaux_garde_assignes(self.jour, self.jour, self.marin, previsionnels=False)), [])
        self.assertEqual(prochains_tours_de_service(self.marin), [])
        self.assertFalse(CreneauServiceGarde.applicables().filter(pk=self.creneau_marin.pk).exists())

    def test_ical_marque_prevu_comme_previsionnel(self):
        self.client.force_login(self.marin)
        reponse = self.client.get(reverse("calendar-ical-my"))
        self.assertContains(reponse, "(prévisionnel)")

    def test_apres_activation_le_creneau_est_en_vigueur(self):
        self._poster(self.chef, action="activer")
        self.assertTrue(CreneauServiceGarde.applicables().filter(pk=self.creneau_marin.pk).exists())
        self.assertEqual(len(prochains_tours_de_service(self.marin)), 1)

    def _echange_valide(self):
        echange = proposer_echange(self.marin, self.creneau_marin, self.creneau_autre, "Rendez-vous")
        accepter_echange(echange, self.autre)
        valider_echange(echange, self.chef)
        echange.refresh_from_db()
        return echange

    def test_echange_valide_sur_previsionnelle_reste_differe(self):
        echange = self._echange_valide()
        self.assertEqual(echange.statut, EchangeService.STATUT_VALIDE)
        self.assertTrue(echange.en_attente_application)
        self.creneau_marin.refresh_from_db()
        self.assertEqual(self.creneau_marin.marin, self.marin)

    def test_echange_applique_a_l_activation(self):
        echange = self._echange_valide()
        self._poster(self.chef, action="activer")
        echange.refresh_from_db()
        self.creneau_marin.refresh_from_db()
        self.assertEqual(self.creneau_marin.marin, self.autre)
        self.assertIsNotNone(echange.applique_le)

    def test_echange_devenu_incompatible_n_est_pas_applique_en_silence(self):
        echange = self._echange_valide()
        # le tour de l'autre marin a commencé entre-temps : l'échange n'est plus faisable
        CreneauServiceGarde.objects.filter(pk=self.creneau_autre.pk).update(debut=timezone.now() - timedelta(hours=1))
        self._poster(self.chef, action="activer")
        echange.refresh_from_db()
        self.creneau_marin.refresh_from_db()
        self.assertEqual(self.creneau_marin.marin, self.marin)
        self.assertIsNone(echange.applique_le)
        self.assertIn("déjà commencé", echange.blocage_application)
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="n'a pas pu être appliqué").exists())

    def test_liste_active_echue_devient_terminee_mais_pas_la_previsionnelle(self):
        ServiceGarde.objects.filter(pk=self.liste.pk).update(date_fin=timezone.localdate() - timedelta(days=1))
        traiter_echeances()
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)
        self.liste.application = ServiceGarde.APPLICATION_ACTIVE
        self.liste.save()
        traiter_echeances()
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_TERMINEE)
        self.assertIsNotNone(self.liste.terminee_le)
