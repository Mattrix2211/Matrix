"""Publication à titre prévisionnel et activation d'une liste à quai (décisions PO mer/quai)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from org.models import Service, Ship
from quarts.models import ChefDeListe, CreneauServiceGarde, ServiceGarde


class ActivationListeQuaiTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment", code="BAT")
        self.service = Service.objects.create(ship=self.ship, name="Pont", commandant_adjoint="COMAEQ")
        self.chef = self._user("chef", "EQUIPIER", service=self.service)
        ChefDeListe.objects.create(user=self.chef, service=self.service)
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
        ChefDeListe.objects.create(user=self.comaeq, service=self.service)
        self._previsionnelle()
        self._poster(self.comaeq, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, ServiceGarde.APPLICATION_ACTIVE)
        trace = AuditLog.objects.get(action="liste_service_activee")
        self.assertIn("en qualité de chef de liste désigné", trace.details)

    def test_chef_d_un_autre_perimetre_ne_peut_pas_activer(self):
        autre = Service.objects.create(ship=self.ship, name="Machine")
        intrus = self._user("intrus", "EQUIPIER", service=autre)
        ChefDeListe.objects.create(user=intrus, service=autre)
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
