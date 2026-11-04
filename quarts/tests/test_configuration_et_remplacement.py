"""Écran des délais d'alerte (droits D5) et remplacement temporaire du chef de liste (D4)."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from notifications.models import Notification
from quarts.models import ChefDeListe, ConfigurationActivation, RemplacementChefDeListe, ServiceGarde
from quarts.tests.test_activation_liste_quai import BaseActivation


def _fmt(dt):
    return timezone.localtime(dt).strftime("%Y-%m-%dT%H:%M")


class DelaisActivationTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self.url_delais = reverse("quarts-delais-activation")
        self.second = self._user("csd", "COMMANDANT_EN_SECOND")
        self.admin_unite = self._user("adm", "ADMIN_NAVIRE")
        self.autre = self._user("autre", "CHEF_SERVICE", service=self.service)
        self.valides = {"rappel_minutes": 45, "alerte_minutes": 5, "escalade_minutes": 20, "remplacement_duree_max_heures": 48}

    def test_droits_de_lecture_et_de_modification(self):
        modifier = (self.commandant, self.comaeq)
        lire = (self.second, self.admin_unite, self.chef)
        for user in (*modifier, *lire):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url_delais).status_code, 200, user.username)
        for user in lire:
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.url_delais, self.valides).status_code, 403, user.username)
        self.assertFalse(ConfigurationActivation.objects.exists())
        self.client.force_login(self.autre)  # aucun droit particulier
        self.assertEqual(self.client.get(self.url_delais).status_code, 404)
        self.assertEqual(self.client.post(self.url_delais, self.valides).status_code, 404)

    def test_modification_validee_et_auditee(self):
        self.client.force_login(self.comaeq)
        self.client.post(self.url_delais, self.valides)
        reglage = ConfigurationActivation.objects.get(ship=self.ship)
        self.assertEqual((reglage.rappel_minutes, reglage.alerte_minutes, reglage.escalade_minutes), (45, 5, 20))
        trace = AuditLog.objects.get(action="delais_activation_modifies")
        self.assertIn("30 → 45", trace.details)
        self.assertEqual(trace.actor, self.comaeq)

    def test_bornes_refusees_cote_serveur(self):
        self.client.force_login(self.commandant)
        for champ, valeur in (("rappel_minutes", 1441), ("alerte_minutes", 121), ("escalade_minutes", 0), ("escalade_minutes", 241), ("rappel_minutes", "abc")):
            reponse = self.client.post(self.url_delais, dict(self.valides, **{champ: valeur}))
            self.assertEqual(reponse.status_code, 400, (champ, valeur))
        self.assertFalse(ConfigurationActivation.objects.exists())
        self.assertEqual(self.client.post(self.url_delais, dict(self.valides, rappel_minutes=1440, alerte_minutes=120, escalade_minutes=240)).status_code, 302)

    def test_valeurs_par_defaut_affichees(self):
        self.client.force_login(self.commandant)
        page = self.client.get(self.url_delais).content.decode()
        self.assertIn('name="rappel_minutes" value="30"', page)
        self.assertIn('name="escalade_minutes" value="15"', page)

    def test_lien_visible_seulement_des_profils_habilites(self):
        self.client.force_login(self.autre)
        self.assertNotContains(self.client.get(reverse("quarts-index")), self.url_delais)
        self.client.force_login(self.second)
        self.assertContains(self.client.get(reverse("quarts-index")), self.url_delais)


class RemplacementChefDeListeTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self.remplacant = self._user("remplacant", "EQUIPIER", service=self.service)
        self.responsable = self._user("resp", "CHEF_SERVICE", service=self.service)
        self.designation = ChefDeListe.objects.get(user=self.chef)
        self.url_reglages = reverse("quarts-reglages")
        self.debut = timezone.now() + timedelta(minutes=1)

    def _designer(self, user, heures=24, **extra):
        self.client.force_login(user)
        donnees = {
            "action": "remplacer", "pk": self.designation.pk, "remplacant_id": self.remplacant.pk,
            "debut": _fmt(self.debut), "fin": _fmt(self.debut + timedelta(hours=heures)), "motif": "Permission du titulaire",
        }
        donnees.update(extra)
        return self.client.post(self.url_reglages, donnees)

    def _remplacement_en_cours(self):
        self.debut = timezone.now() - timedelta(minutes=2)
        self._designer(self.responsable)
        return RemplacementChefDeListe.objects.get()

    def test_designation_historisee_avec_auteur_motif_titulaire_et_dates(self):
        self._designer(self.responsable)
        r = RemplacementChefDeListe.objects.get()
        self.assertEqual((r.remplacant, r.titulaire, r.designe_par, r.motif), (self.remplacant, self.chef, self.responsable, "Permission du titulaire"))
        self.assertEqual(r.type_liste, "QUAI")
        self.assertTrue(AuditLog.objects.filter(action="remplacement_chef_de_liste_designe", details__contains="Permission du titulaire").exists())
        self.assertTrue(Notification.objects.filter(user=self.remplacant, verb__contains="Vous remplacez").exists())

    def test_duree_maximale_72_heures_par_defaut_sans_renouvellement(self):
        self._designer(self.responsable, heures=73)
        self.assertFalse(RemplacementChefDeListe.objects.exists())
        self._designer(self.responsable, heures=72)
        self.assertEqual(RemplacementChefDeListe.objects.count(), 1)
        self._designer(self.responsable, heures=10)  # chevauchement du même titulaire : refusé
        self.assertEqual(RemplacementChefDeListe.objects.count(), 1)

    def test_duree_maximale_configurable(self):
        ConfigurationActivation.objects.create(ship=self.ship, remplacement_duree_max_heures=12)
        self._designer(self.responsable, heures=13)
        self.assertFalse(RemplacementChefDeListe.objects.exists())

    def test_garde_fous_motif_remplacant_et_passe(self):
        self._designer(self.responsable, motif="")
        self._designer(self.responsable, remplacant_id=self.chef.pk)  # le titulaire lui-même
        self.debut = timezone.now() - timedelta(hours=2)
        self._designer(self.responsable)  # début dans le passé
        self.assertFalse(RemplacementChefDeListe.objects.exists())

    def test_seul_un_responsable_du_perimetre_designe_un_remplacant(self):
        for user in (self.marin, self.chef, self.remplacant):
            self.assertEqual(self._designer(user).status_code, 403, user.username)
        self.assertFalse(RemplacementChefDeListe.objects.exists())

    def test_le_remplacant_active_pendant_la_periode_et_la_capacite_est_tracee(self):
        self._remplacement_en_cours()
        self._previsionnelle()
        self._poster(self.remplacant, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)
        trace = AuditLog.objects.get(action="liste_service_activee")
        self.assertIn("remplaçant temporaire de", trace.details)
        self.assertEqual(trace.actor, self.remplacant)

    def test_le_remplacant_peut_reporter_et_retirer(self):
        self._remplacement_en_cours()
        self._previsionnelle()
        nouvelle = _fmt(timezone.now() + timedelta(days=1))
        self._poster(self.remplacant, action="reporter", prise_effet_prevue=nouvelle, motif="Accostage retardé")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.version_prevision, 2)
        self._poster(self.remplacant, action="retirer_previsionnelle", motif="Erreur")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.statut, ServiceGarde.STATUT_BROUILLON)

    def test_pas_de_droit_avant_apres_ou_apres_revocation(self):
        self._previsionnelle()
        self._designer(self.responsable)  # commence dans une minute
        self._poster(self.remplacant, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)
        RemplacementChefDeListe.objects.update(debut=timezone.now() - timedelta(minutes=5))
        remplacement = RemplacementChefDeListe.objects.get()
        self.client.force_login(self.responsable)
        self.client.post(self.url_reglages, {"action": "revoquer_remplacement", "pk": remplacement.pk, "motif": ""})
        remplacement.refresh_from_db()
        self.assertIsNone(remplacement.revoque_le)  # motif obligatoire
        self.client.post(self.url_reglages, {"action": "revoquer_remplacement", "pk": remplacement.pk, "motif": "Titulaire de retour"})
        self._poster(self.remplacant, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)

    def test_pas_de_droit_apres_la_fin(self):
        self._remplacement_en_cours()
        RemplacementChefDeListe.objects.update(fin=timezone.now() - timedelta(minutes=1))
        self._previsionnelle()
        self._poster(self.remplacant, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)

    def test_le_remplacant_n_a_aucun_autre_droit_du_chef_de_liste(self):
        from quarts.models import peut_gerer_liste

        self._remplacement_en_cours()
        self.assertFalse(peut_gerer_liste(self.remplacant, self.liste))  # ni créneaux, ni proposition
        self.client.force_login(self.remplacant)
        debut = _fmt(timezone.now() + timedelta(days=2))
        reponse = self.client.post(self.url, {"action": "ajouter_creneau", "poste": "X", "debut": debut})
        self.assertEqual(reponse.status_code, 404)
        self.assertEqual(self.liste.creneaux.count(), 1)

    def test_remplacement_limite_a_son_perimetre_et_a_son_type(self):
        from accounts.models import FonctionQuartChoice
        from org.models import Service
        from quarts.models import Quart

        self._remplacement_en_cours()
        quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=3), statut=Quart.STATUT_PUBLIEE,
        )
        from quarts.models import peut_gerer_liste
        from quarts.activation import peut_activer_liste

        self.assertFalse(peut_activer_liste(self.remplacant, quart))  # un quart n'est jamais concerné
        autre_service = Service.objects.create(ship=self.ship, name="Machine")
        autre = ServiceGarde.objects.create(
            service=autre_service, fonction=self.liste.fonction, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=3),
            statut=ServiceGarde.STATUT_PUBLIEE, application=ServiceGarde.APPLICATION_PREVISIONNELLE,
        )
        self.assertFalse(peut_activer_liste(self.remplacant, autre))
        self.assertFalse(peut_gerer_liste(self.remplacant, quart))

    def test_le_remplacant_recoit_les_rappels(self):
        from quarts.alertes_activation import traiter_echeances

        self._remplacement_en_cours()
        self._previsionnelle()
        prevue = timezone.now() + timedelta(hours=3)
        ServiceGarde.objects.filter(pk=self.liste.pk).update(prise_effet_prevue=prevue)
        traiter_echeances(prevue - timedelta(minutes=30))
        self.assertTrue(Notification.objects.filter(user=self.remplacant, verb__contains="Rappel").exists())

    def test_la_fiche_indique_la_capacite_d_activation_et_un_creneau_sur_deux_jours(self):
        self._remplacement_en_cours()
        self._previsionnelle()
        self._poster(self.remplacant, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.active_en_qualite, "remplacant")
        self.client.force_login(self.chef)
        page = self.client.get(self.url).content.decode()
        self.assertIn("remplaçant temporaire du chef de liste", page)
        self.assertNotIn("par remplacant (chef de liste)", page)

    def test_activation_par_le_chef_indique_chef_de_liste(self):
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.active_en_qualite, "chef")
        self.client.force_login(self.chef)
        self.assertIn(", chef de liste", self.client.get(self.url).content.decode())
