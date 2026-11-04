"""D11 : inventaire et qualification des désignations historiques ; un chef de liste à quai ne touche jamais aux quarts à la mer."""
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice, UserProfile
from org.models import Service, Ship
from quarts.models import ChefDeListe, CreneauQuart, Quart, peut_gerer_liste


class HabilitationsHistoriquesTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment", code="BAT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.chef_quai = self._user("chef_quai")
        ChefDeListe.objects.create(user=self.chef_quai, service=self.service, type_liste=ChefDeListe.TYPE_QUAI)
        self.chef_historique = self._user("chef_historique")
        self.designation_historique = ChefDeListe.objects.create(user=self.chef_historique, service=self.service)
        self.marin = self._user("marin")
        self.responsable = self._user("resp", "CHEF_SERVICE")
        jour = timezone.localdate()
        self.fonction = FonctionQuartChoice.objects.create(name="Barre")
        self.quart_brouillon = Quart.objects.create(service=self.service, fonction=self.fonction, date_debut=jour, date_fin=jour + timedelta(days=3))
        self.quart_publie = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Veille"), date_debut=jour, date_fin=jour + timedelta(days=3),
            statut=Quart.STATUT_PUBLIEE,
        )
        debut = timezone.now() + timedelta(hours=2)
        self.creneau = CreneauQuart.objects.create(quart=self.quart_publie, poste="Veille", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)

    def _user(self, nom, role="EQUIPIER"):
        u = User.objects.create_user(nom, password="x")
        UserProfile.objects.update_or_create(user=u, defaults={"role": role, "ship": self.ship, "service": self.service})
        return User.objects.get(pk=u.pk)

    def _poster(self, user, quart, **donnees):
        self.client.force_login(user)
        return self.client.post(reverse("quart-detail", args=[quart.pk]), donnees)

    # --- un chef de liste à quai ne peut RIEN modifier sur un quart à la mer (statut, refus, données inchangées) ---
    def test_le_chef_a_quai_ne_modifie_aucun_quart_meme_perimetre(self):
        debut = timezone.localtime(timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        cas = [
            (self.quart_brouillon, {"action": "ajouter_creneau", "poste": "X", "debut": debut}, 404),
            (self.quart_brouillon, {"action": "proposer"}, 404),
            (self.quart_brouillon, {"action": "publier"}, 404),
            (self.quart_publie, {"action": "ajouter_creneau", "poste": "X", "debut": debut}, 404),
            (self.quart_publie, {"action": "supprimer_creneau", "creneau_id": self.creneau.pk, "motif": "x"}, 404),
            (self.quart_publie, {"action": "publier"}, 403),
            (self.quart_publie, {"action": "terminer_creneau", "creneau_id": self.creneau.pk, "nouvelle_fin": debut, "motif": "x"}, 403),
        ]
        fin = self.creneau.fin
        for quart, donnees, statut in cas:
            reponse = self._poster(self.chef_quai, quart, **donnees)
            self.assertEqual(reponse.status_code, statut, donnees["action"])
        self.assertFalse(peut_gerer_liste(self.chef_quai, self.quart_brouillon))
        self.assertFalse(peut_gerer_liste(self.chef_quai, self.quart_publie))
        self.quart_brouillon.refresh_from_db()
        self.assertEqual(self.quart_brouillon.statut, Quart.STATUT_BROUILLON)
        self.quart_publie.refresh_from_db()
        self.assertEqual(self.quart_publie.creneaux.count(), 1)
        self.creneau.refresh_from_db()
        self.assertEqual((self.creneau.fin, self.creneau.fin_initiale), (fin, None))
        self.assertEqual(self.quart_publie.versions.count(), 0)

    def test_aucun_chef_a_quai_n_a_de_droit_apres_qualification_a_quai_seulement(self):
        self.client.force_login(self.responsable)
        self.client.post(reverse("quarts-reglages"), {"action": "preciser", "pk": self.designation_historique.pk, "types": ["QUAI"]})
        chef = User.objects.get(pk=self.chef_historique.pk)
        self.assertFalse(peut_gerer_liste(chef, self.quart_brouillon))
        self.assertFalse(peut_gerer_liste(chef, self.quart_publie))

    # --- inventaire et procédure de qualification ---
    def test_l_inventaire_liste_les_designations_historiques_sans_rien_modifier(self):
        avant = list(ChefDeListe.objects.values_list("pk", "type_liste"))
        sortie = StringIO()
        call_command("analyser_designations_chef_de_liste", stdout=sortie)
        texte = sortie.getvalue()
        self.assertIn("chef_historique", texte)
        self.assertNotIn("chef_quai", texte)  # désignation typée : hors inventaire
        self.assertIn("droits actuels sur les quarts à la mer ET les services à quai", texte)
        self.assertIn("1 désignation(s) historique(s) à qualifier", texte)
        self.assertEqual(list(ChefDeListe.objects.values_list("pk", "type_liste")), avant)

    def test_la_qualification_explicite_n_ajoute_que_les_types_choisis_et_est_auditee(self):
        self.client.force_login(self.responsable)
        self.client.post(reverse("quarts-reglages"), {"action": "preciser", "pk": self.designation_historique.pk, "types": ["QUARTS"]})
        types = list(ChefDeListe.objects.filter(user=self.chef_historique).values_list("type_liste", flat=True))
        self.assertEqual(types, ["QUARTS"])
        self.assertTrue(AuditLog.objects.filter(action="chef_de_liste_precise", target_user=self.chef_historique).exists())

    def test_une_qualification_sans_choix_ne_change_rien(self):
        self.client.force_login(self.responsable)
        self.client.post(reverse("quarts-reglages"), {"action": "preciser", "pk": self.designation_historique.pk})
        self.assertTrue(ChefDeListe.objects.filter(pk=self.designation_historique.pk, type_liste="").exists())

    def test_aucun_elargissement_automatique_une_designation_a_quai_ne_cree_pas_de_droit_quarts(self):
        self.client.force_login(self.responsable)
        nouveau = self._user("nouveau")
        self.client.post(reverse("quarts-reglages"), {"action": "designer", "user_id": nouveau.pk, "perimetre": f"service:{self.service.pk}", "type_liste": "QUAI"})
        self.assertEqual(list(ChefDeListe.objects.filter(user=nouveau).values_list("type_liste", flat=True)), ["QUAI"])
        self.assertFalse(peut_gerer_liste(User.objects.get(pk=nouveau.pk), self.quart_publie))

    def test_une_designation_sans_type_ne_peut_plus_etre_creee_par_l_interface(self):
        self.client.force_login(self.responsable)
        nouveau = self._user("nouveau")
        self.client.post(reverse("quarts-reglages"), {"action": "designer", "user_id": nouveau.pk, "perimetre": f"service:{self.service.pk}"})
        self.assertFalse(ChefDeListe.objects.filter(user=nouveau).exists())

    def test_l_ecart_a_la_decision_d11_est_visible_pour_les_responsables(self):
        self.client.force_login(self.responsable)
        page = self.client.get(reverse("quarts-reglages")).content.decode()
        self.assertIn("1 désignation(s) historique(s) sans type", page)
        self.assertIn("À préciser", page)
