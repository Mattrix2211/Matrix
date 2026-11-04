"""D11 : le chef de liste des services à quai n'a aucun droit sur les quarts à la mer, et inversement ;
les désignations historiques sans type sont conservées, signalées, jamais élargies en silence."""
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice, ServiceFunctionChoice, UserProfile
from org.models import Service, Ship
from quarts.designations import situation
from quarts.models import ChefDeListe, Quart, ServiceGarde, peut_gerer_liste


class ChefDeListeParTypeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment", code="BAT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        jour = timezone.localdate()
        self.quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=jour, date_fin=jour + timedelta(days=7),
        )
        self.garde = ServiceGarde.objects.create(
            service=self.service, fonction=ServiceFunctionChoice.objects.create(name="Permanence"),
            date_debut=jour, date_fin=jour + timedelta(days=7),
        )
        self.chef_quai = self._user("chef_quai")
        ChefDeListe.objects.create(user=self.chef_quai, service=self.service, type_liste=ChefDeListe.TYPE_QUAI)
        self.chef_mer = self._user("chef_mer")
        ChefDeListe.objects.create(user=self.chef_mer, service=self.service, type_liste=ChefDeListe.TYPE_QUARTS)
        self.chef_historique = self._user("chef_historique")
        ChefDeListe.objects.create(user=self.chef_historique, service=self.service)

    def _user(self, nom, role="EQUIPIER"):
        user = User.objects.create_user(nom, password="x")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.ship, "service": self.service})
        return User.objects.get(pk=user.pk)

    def test_chef_quai_sans_droit_sur_les_quarts_du_meme_perimetre(self):
        self.assertTrue(peut_gerer_liste(self.chef_quai, self.garde))
        self.assertFalse(peut_gerer_liste(self.chef_quai, self.quart))

    def test_chef_quarts_sans_droit_sur_les_services_a_quai(self):
        self.assertTrue(peut_gerer_liste(self.chef_mer, self.quart))
        self.assertFalse(peut_gerer_liste(self.chef_mer, self.garde))

    def test_designation_historique_non_qualifiee_ne_donne_aucun_droit(self):
        self.assertFalse(peut_gerer_liste(self.chef_historique, self.quart))
        self.assertFalse(peut_gerer_liste(self.chef_historique, self.garde))

    def test_chef_quai_ne_peut_pas_modifier_un_quart_par_requete_directe(self):
        self.client.force_login(self.chef_quai)
        debut = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        reponse = self.client.post(reverse("quart-detail", args=[self.quart.pk]), {"action": "ajouter_creneau", "poste": "X", "debut": debut})
        self.assertEqual(reponse.status_code, 404)
        self.assertFalse(self.quart.creneaux.exists())

    def test_creation_refusee_pour_l_autre_type(self):
        self.client.force_login(self.chef_quai)
        donnees = {"perimetre": f"service:{self.service.pk}", "date_debut": "2030-01-01", "date_fin": "2030-01-07"}
        avant = Quart.objects.count()
        reponse = self.client.post(reverse("quarts-index"), {"action": "creer_quart", **donnees})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(Quart.objects.count(), avant)

    def test_chef_quai_ne_voit_pas_les_quarts_dans_ses_listes_gerees(self):
        self.client.force_login(self.chef_quai)
        page = self.client.get(reverse("quarts-index")).content.decode()
        self.assertIn(reverse("garde-detail", args=[self.garde.pk]), page)
        self.assertNotIn(reverse("quart-detail", args=[self.quart.pk]), page)

    def test_commandant_garde_sa_supervision(self):
        commandant = self._user("cdt", "COMMANDANT")
        self.assertTrue(peut_gerer_liste(commandant, self.quart))
        self.assertTrue(peut_gerer_liste(commandant, self.garde))

    def test_nouvelle_designation_exige_un_type(self):
        responsable = self._user("resp", "CHEF_SERVICE")
        self.client.force_login(responsable)
        self.client.post(reverse("quarts-reglages"), {"action": "designer", "user_id": self.chef_quai.pk, "perimetre": f"service:{self.service.pk}"})
        self.assertEqual(ChefDeListe.objects.filter(user=self.chef_quai).count(), 1)
        self.client.post(reverse("quarts-reglages"), {
            "action": "designer", "user_id": self.chef_quai.pk, "perimetre": f"service:{self.service.pk}", "type_liste": "QUARTS",
        })
        self.assertTrue(ChefDeListe.objects.filter(user=self.chef_quai, type_liste="QUARTS").exists())
        self.assertTrue(AuditLog.objects.filter(action="chef_de_liste_designe").exists())

    def test_qualification_explicite_d_une_designation_historique(self):
        responsable = self._user("resp", "CHEF_SERVICE")
        self.client.force_login(responsable)
        historique = ChefDeListe.objects.get(user=self.chef_historique, type_liste="")
        self.client.post(reverse("quarts-reglages"), {"action": "preciser", "pk": historique.pk})
        historique.refresh_from_db()
        self.assertIsNone(historique.qualifiee_le)  # aucun type choisi : rien ne change
        self.client.post(reverse("quarts-reglages"), {"action": "preciser", "pk": historique.pk, "types": ["QUAI"]})
        historique.refresh_from_db()
        self.assertIsNotNone(historique.qualifiee_le)  # conservée, jamais supprimée
        self.assertTrue(ChefDeListe.objects.filter(user=self.chef_historique, type_liste="QUAI").exists())
        chef = User.objects.get(pk=self.chef_historique.pk)
        self.assertTrue(peut_gerer_liste(chef, self.garde))
        self.assertFalse(peut_gerer_liste(chef, self.quart))
        self.assertTrue(AuditLog.objects.filter(action="chef_de_liste_qualifie").exists())

    def test_un_marin_ne_peut_pas_preciser_ni_designer(self):
        self.client.force_login(self.chef_quai)
        historique = ChefDeListe.objects.get(user=self.chef_historique)
        self.assertEqual(self.client.post(reverse("quarts-reglages"), {"action": "preciser", "pk": historique.pk, "types": ["QUAI"]}).status_code, 403)
        self.assertTrue(ChefDeListe.objects.filter(pk=historique.pk).exists())

    def test_diagnostic_signale_les_designations_ambigues_sans_rien_modifier(self):
        historique = ChefDeListe.objects.get(user=self.chef_historique)
        self.assertEqual(situation(historique), "AMBIGUE")
        sortie = StringIO()
        call_command("analyser_designations_chef_de_liste", stdout=sortie)
        self.assertIn("Ambiguë", sortie.getvalue())
        self.assertIn("aucun droit modifié", sortie.getvalue())
        self.assertTrue(ChefDeListe.objects.filter(pk=historique.pk, type_liste="").exists())

    def test_page_des_reglages_signale_les_designations_a_preciser(self):
        responsable = self._user("resp", "CHEF_SERVICE")
        self.client.force_login(responsable)
        page = self.client.get(reverse("quarts-reglages")).content.decode()
        self.assertIn("À qualifier", page)
        self.assertIn("à qualifier", page)
