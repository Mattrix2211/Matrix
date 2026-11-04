"""Refus serveur sur les actions sensibles : statut réellement renvoyé, refus effectif, données inchangées, tentative tracée.

Politique d'erreurs : 404 pour qui ne voit pas l'objet, 403 pour une action interdite à qui le voit ; les refus métier
(mode, conflit, motif manquant) redirigent vers la fiche avec un message et ne modifient rien."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice
from quarts.models import (
    ChefDeListe, ConfigurationActivation, CreneauQuart, MouvementBatiment, Quart, RemplacementChefDeListe, ServiceGarde,
)
from quarts.tests.test_activation_liste_quai import BaseActivation


def _tentatives():
    return AuditLog.objects.filter(action="tentative_refusee").count()


class RefusServeurTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self._previsionnelle()
        self.second = self._user("csd", "COMMANDANT_EN_SECOND")
        self.chef_quarts = self._user("chef_quarts", "EQUIPIER", service=self.service)
        ChefDeListe.objects.filter(user=self.chef).delete()
        ChefDeListe.objects.create(user=self.chef, service=self.service, type_liste=ChefDeListe.TYPE_QUAI)
        ChefDeListe.objects.create(user=self.chef_quarts, service=self.service, type_liste=ChefDeListe.TYPE_QUARTS)
        self.quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=3),
            statut=Quart.STATUT_PUBLIEE, created_by=self.chef_quarts,
        )
        debut = timezone.now() + timedelta(hours=2)
        self.creneau_quart = CreneauQuart.objects.create(quart=self.quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        self.url_quart = reverse("quart-detail", args=[self.quart.pk])

    def _etat_liste(self):
        self.liste.refresh_from_db()
        return (self.liste.statut, self.liste.application, self.liste.version_prevision, self.liste.prise_effet_prevue, self.liste.active_par_id)

    def _post(self, user, url, **donnees):
        self.client.force_login(user)
        return self.client.post(url, donnees)

    # --- actions d'activation : 403 pour qui voit la liste, trace de la tentative, rien de modifié ---
    def test_activation_refusee_403_et_tracee_pour_commandant_comaeq_second_et_marin(self):
        avant = self._etat_liste()
        for user in (self.commandant, self.comaeq, self.second, self.marin):
            t0 = _tentatives()
            reponse = self._post(user, self.url, action="activer")
            self.assertEqual(reponse.status_code, 403, user.username)
            self.assertEqual(_tentatives(), t0 + 1, user.username)
            self.assertEqual(self._etat_liste(), avant, user.username)
        trace = AuditLog.objects.filter(action="tentative_refusee").last()
        self.assertIn("activer", trace.details)

    def test_report_et_retrait_refuses_403_et_traces(self):
        avant = self._etat_liste()
        nouvelle = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        for user in (self.commandant, self.comaeq, self.second):
            self.assertEqual(self._post(user, self.url, action="reporter", prise_effet_prevue=nouvelle, motif="x").status_code, 403)
            self.assertEqual(self._post(user, self.url, action="retirer_previsionnelle", motif="x").status_code, 403)
        self.assertEqual(self._etat_liste(), avant)
        self.assertEqual(_tentatives(), 6)

    def test_un_utilisateur_qui_ne_voit_pas_la_liste_recoit_404_sans_trace(self):
        from org.models import Service

        autre = Service.objects.create(ship=self.ship, name="Machine")
        etranger = self._user("etranger", "EQUIPIER", service=autre)
        avant, t0 = self._etat_liste(), _tentatives()
        self.assertEqual(self._post(etranger, self.url, action="activer").status_code, 404)
        self.assertEqual(self._etat_liste(), avant)
        self.assertEqual(_tentatives(), t0)

    # --- refus métier : redirection avec message, aucune modification ---
    def test_refus_metier_a_la_mer_redirige_avec_message_sans_rien_modifier(self):
        MouvementBatiment.objects.all().delete()
        from quarts.mouvements import initialiser_mode

        initialiser_mode(self.comaeq, self.ship, "MER", timezone.now() - timedelta(days=1), "Vérifié")
        avant = self._etat_liste()
        reponse = self._post(self.chef, self.url, action="activer")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse["Location"], self.url)
        suite = self.client.get(self.url)
        self.assertContains(suite, "Le bâtiment est à la mer")
        self.assertEqual(self._etat_liste(), avant)

    # --- publication, mouvements, régularisation de quarts ---
    def test_publication_sans_droit_403_et_tracee(self):
        self.liste.statut = ServiceGarde.STATUT_PROPOSEE
        self.liste.save()
        t0 = _tentatives()
        reponse = self._post(self.chef, self.url, action="publier", prise_effet_prevue=timezone.localtime(timezone.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"))
        self.assertEqual(reponse.status_code, 403)
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.statut, ServiceGarde.STATUT_PROPOSEE)
        self.assertEqual(_tentatives(), t0 + 1)

    def test_mouvement_par_un_non_habilite_403_trace_et_aucun_mouvement(self):
        avant = MouvementBatiment.objects.count()
        for user in (self.marin, self.chef, self.second):
            t0 = _tentatives()
            reponse = self._post(user, reverse("mouvements-batiment"), action="declarer", type="ACCOSTAGE", survenu_le=timezone.localtime().strftime("%Y-%m-%dT%H:%M"))
            self.assertEqual(reponse.status_code, 403, user.username)
            self.assertEqual(_tentatives(), t0 + 1)
        self.assertEqual(MouvementBatiment.objects.count(), avant)

    def test_terminer_un_creneau_de_quart_sans_droit_403_trace_donnees_inchangees(self):
        fin = self.creneau_quart.fin
        for user in (self.chef, self.marin):
            t0 = _tentatives()
            reponse = self._post(user, self.url_quart, action="terminer_creneau", creneau_id=self.creneau_quart.pk,
                                 nouvelle_fin=timezone.localtime(self.creneau_quart.debut + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"), motif="x")
            self.assertEqual(reponse.status_code, 403, user.username)
            self.assertEqual(_tentatives(), t0 + 1)
        self.creneau_quart.refresh_from_db()
        self.assertEqual((self.creneau_quart.fin, self.creneau_quart.fin_initiale), (fin, None))
        self.assertEqual(self.quart.versions.count(), 0)

    # --- réglages ---
    def test_delais_d_alerte_modification_refusee_403_tracee(self):
        t0 = _tentatives()
        reponse = self._post(self.second, reverse("quarts-delais-activation"), rappel_minutes=45, alerte_minutes=5, escalade_minutes=20, remplacement_duree_max_heures=48)
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(ConfigurationActivation.objects.exists())
        self.assertEqual(_tentatives(), t0 + 1)

    def test_designation_d_un_remplacant_par_un_non_responsable_403_tracee(self):
        remplacant = self._user("remplacant", "EQUIPIER", service=self.service)
        designation = ChefDeListe.objects.get(user=self.chef)
        t0 = _tentatives()
        for user in (self.marin, self.chef):
            reponse = self._post(user, reverse("quarts-reglages"), action="remplacer", pk=designation.pk, remplacant_id=remplacant.pk,
                                 debut=timezone.localtime().strftime("%Y-%m-%dT%H:%M"), fin=timezone.localtime(timezone.now() + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M"), motif="x")
            self.assertEqual(reponse.status_code, 403, user.username)
        self.assertFalse(RemplacementChefDeListe.objects.exists())
        self.assertGreaterEqual(_tentatives(), t0 + 2)
