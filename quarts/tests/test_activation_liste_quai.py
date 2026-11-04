"""Publication à titre prévisionnel et activation d'une liste à quai (décisions PO mer/quai)."""
from quarts.tests.support import designer_chef
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from org.models import Service, Ship
from quarts.models import ChefDeListe, CreneauServiceGarde, ServiceGarde
from quarts.mouvements import initialiser_mode


class BaseActivation(TestCase):
    mode_initial = "QUAI"  # None : mode du bâtiment non renseigné

    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment", code="BAT")
        self.service = Service.objects.create(ship=self.ship, name="Pont", commandant_adjoint="COMAEQ")
        self.chef = self._user("chef", "EQUIPIER", service=self.service)
        designer_chef(user=self.chef, service=self.service)
        self.commandant = self._user("cdt", "COMMANDANT")
        self.comaeq = self._user("coma", "ETAT_MAJOR", fonction_coma="COMAEQ")
        self.marin = self._user("marin", "EQUIPIER", service=self.service)
        self.liste = ServiceGarde.objects.create(
            service=self.service, fonction=ServiceFunctionChoice.objects.create(name="Permanence"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=7),
            statut=ServiceGarde.STATUT_PROPOSEE, created_by=self.chef,
        )
        debut = timezone.now() + timedelta(days=1)
        CreneauServiceGarde.objects.create(service_garde=self.liste, poste="G", debut=debut, fin=debut + timedelta(hours=24), marin=self.marin)
        self.url = reverse("garde-detail", args=[self.liste.pk])
        if self.mode_initial:
            initialiser_mode(self.comaeq, self.ship, self.mode_initial, timezone.now() - timedelta(days=2), "Situation vérifiée (test)")

    def _user(self, nom, role, **champs):
        user = User.objects.create_user(nom, password="x")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.ship, **champs})
        return User.objects.get(pk=user.pk)

    def _poster(self, user, **donnees):
        self.client.force_login(user)
        return self.client.post(self.url, donnees)

    def _previsionnelle(self):
        prevue = (timezone.now() + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M")
        self._poster(self.commandant, action="publier", prise_effet_prevue=prevue)
        self.liste.refresh_from_db()


class ActivationListeQuaiTests(BaseActivation):
    def test_publication_sans_prise_effet_prevue_refusee(self):
        self._poster(self.commandant, action="publier")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.statut, ServiceGarde.STATUT_PROPOSEE)

    def test_previsionnelle_jamais_active_toute_seule(self):
        self._previsionnelle()
        self.assertEqual(self.liste.statut, ServiceGarde.STATUT_PUBLIEE)
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)
        self.assertIsNone(self.liste.prise_effet)
        self.assertEqual(self.liste.situation_affichee, "Prévisionnelle")

    def test_chef_de_liste_active_sans_retroactivite(self):
        self._previsionnelle()
        avant = timezone.now()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)
        self.assertGreaterEqual(self.liste.prise_effet, avant)
        self.assertEqual(self.liste.active_par, self.chef)
        self.assertTrue(AuditLog.objects.filter(action="liste_service_activee", actor=self.chef, details__contains="chef de liste désigné").exists())

    def test_commandant_comaeq_et_marin_ne_peuvent_pas_activer(self):
        self._previsionnelle()
        for user in (self.commandant, self.comaeq, self.marin):
            self._poster(user, action="activer")
            self.liste.refresh_from_db()
            self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE, user.username)

    def test_comaeq_designe_chef_de_liste_active_en_tant_que_chef(self):
        designer_chef(user=self.comaeq, service=self.service)
        self._previsionnelle()
        self._poster(self.comaeq, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)
        trace = AuditLog.objects.get(action="liste_service_activee")
        self.assertIn("en qualité de chef de liste désigné", trace.details)

    def test_chef_d_un_autre_perimetre_ne_peut_pas_activer(self):
        autre = Service.objects.create(ship=self.ship, name="Machine")
        intrus = self._user("intrus", "EQUIPIER", service=autre)
        designer_chef(user=intrus, service=autre)
        self._previsionnelle()
        self._poster(intrus, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)

    def test_activation_impossible_sur_brouillon_ou_deja_active(self):
        self.liste.statut = ServiceGarde.STATUT_BROUILLON
        self.liste.save()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)  # défaut inchangé, aucune trace d'activation
        self.assertFalse(AuditLog.objects.filter(action="liste_service_activee").exists())

    def test_bouton_activer_visible_du_seul_chef_de_liste(self):
        self._previsionnelle()
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(self.url), "Activer la liste")
        self.client.force_login(self.commandant)
        self.assertNotContains(self.client.get(self.url), "Activer la liste")


class ConflitsActivationTests(BaseActivation):
    def _quart_en_conflit(self, decalage_heures=2, en_cours=True):
        from accounts.models import FonctionQuartChoice
        from quarts.models import CreneauQuart, Quart

        quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=7), statut=Quart.STATUT_PUBLIEE,
        )
        garde = self.liste.creneaux.get()
        if en_cours:
            garde.debut, garde.fin = timezone.now() - timedelta(hours=1), timezone.now() + timedelta(hours=23)
            garde.save()
            debut = timezone.now() - timedelta(minutes=30)
        else:
            debut = garde.debut + timedelta(hours=decalage_heures)
        return CreneauQuart.objects.create(quart=quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)

    def test_quart_a_la_mer_recouvrant_bloque_l_activation_sans_le_modifier(self):
        creneau_mer = self._quart_en_conflit()
        debut, fin = creneau_mer.debut, creneau_mer.fin
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)
        creneau_mer.refresh_from_db()
        self.assertEqual((creneau_mer.debut, creneau_mer.fin), (debut, fin))
        self.assertFalse(AuditLog.objects.filter(action="liste_service_activee").exists())

    def test_conflit_affiche_aux_responsables_pas_a_un_marin(self):
        self._quart_en_conflit()
        self._previsionnelle()
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(self.url), "Activation bloquée")
        self.client.force_login(self.marin)
        self.assertNotContains(self.client.get(self.url), "Activation bloquée")

    def test_activation_possible_une_fois_le_conflit_resolu(self):
        creneau_mer = self._quart_en_conflit()
        self._previsionnelle()
        creneau_mer.delete()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)

    def test_quart_futur_recouvrant_est_un_avertissement_non_bloquant(self):
        from quarts.activation import avertissements_activation, conflits_activation

        self._quart_en_conflit(en_cours=False)
        self._previsionnelle()
        self.assertEqual(conflits_activation(self.liste), [])
        self.assertEqual(len(avertissements_activation(self.liste)), 1)
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(self.url), "Recouvrements à confirmer lors de la transition")
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)

    def test_deux_services_a_quai_en_vigueur_qui_se_recouvrent_bloquent_meme_dans_le_futur(self):
        autre = ServiceGarde.objects.create(
            service=self.service, fonction=self.liste.fonction, date_debut=self.liste.date_debut, date_fin=self.liste.date_fin,
            statut=ServiceGarde.STATUT_PUBLIEE,  # application ACTIVE par défaut : en vigueur
        )
        garde = self.liste.creneaux.get()
        CreneauServiceGarde.objects.create(service_garde=autre, poste="Autre", debut=garde.debut + timedelta(hours=2), fin=garde.fin, marin=self.marin)
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)

    def test_quart_termine_avant_le_service_n_est_pas_un_faux_conflit(self):
        from quarts.activation import recouvrements_activation

        quart = self._quart_en_conflit(en_cours=False)
        garde = self.liste.creneaux.get()
        quart.fin = garde.debut - timedelta(minutes=1)
        quart.debut = quart.fin - timedelta(hours=4)
        quart.save()
        self.assertEqual(recouvrements_activation(self.liste), [])

    def test_recouvrement_anterieur_a_l_activation_n_est_pas_retroactif(self):
        from quarts.activation import recouvrements_activation

        quart = self._quart_en_conflit(en_cours=True)
        quart.debut, quart.fin = timezone.now() - timedelta(hours=3), timezone.now() - timedelta(minutes=10)
        quart.save()  # le quart s'est terminé avant l'activation
        self.assertEqual(recouvrements_activation(self.liste), [])

    def test_quart_deja_termine_ne_bloque_pas(self):
        from quarts.activation import conflits_activation

        creneau_mer = self._quart_en_conflit()
        creneau_garde = self.liste.creneaux.get()
        creneau_garde.debut = timezone.now() - timedelta(hours=30)
        creneau_garde.fin = timezone.now() - timedelta(hours=6)
        creneau_garde.save()
        creneau_mer.debut, creneau_mer.fin = creneau_garde.debut + timedelta(hours=1), creneau_garde.debut + timedelta(hours=5)
        creneau_mer.save()
        self.assertEqual(conflits_activation(self.liste), [])

    def test_liste_previsionnelle_ne_cree_pas_de_faux_conflit_ailleurs(self):
        from quarts.echanges import conflits_marin

        self._previsionnelle()
        autre = ServiceGarde.objects.create(
            service=self.service, fonction=self.liste.fonction, date_debut=self.liste.date_debut, date_fin=self.liste.date_fin,
            statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = self.liste.creneaux.get().debut
        creneau = CreneauServiceGarde.objects.create(service_garde=autre, poste="X", debut=debut, fin=debut + timedelta(hours=2), marin=self.marin)
        self.assertEqual(conflits_marin(self.marin, creneau, [creneau.pk]), [])


class ActivationParTypeDeDesignationTests(BaseActivation):
    def test_chef_des_quarts_seulement_ne_peut_pas_activer_un_service_a_quai(self):
        ChefDeListe.objects.filter(user=self.chef).delete()
        ChefDeListe.objects.create(user=self.chef, service=self.service, type_liste=ChefDeListe.TYPE_QUARTS)
        self.liste.refresh_from_db()
        self.liste.statut = ServiceGarde.STATUT_PUBLIEE
        self.liste.application = ServiceGarde.APPLICATION_PREVISIONNELLE
        self.liste.save()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_PREVISIONNELLE)

    def test_chef_des_services_a_quai_active(self):
        ChefDeListe.objects.filter(user=self.chef).delete()
        ChefDeListe.objects.create(user=self.chef, service=self.service, type_liste=ChefDeListe.TYPE_QUAI)
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)
