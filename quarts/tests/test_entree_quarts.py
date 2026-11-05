"""Page d'entrée « Quarts et tours de service » : vue quotidienne (A), vue responsable (B), listes ; périmètre et rôles."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import FonctionQuartChoice
from org.models import Ship
from quarts.entree import debut_de_semaine
from quarts.models import CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde
from quarts.tests.test_activation_liste_quai import BaseActivation


class EntreeQuartsTests(BaseActivation):
    def setUp(self):
        super().setUp()
        self.autre = self._user("autre_marin", "EQUIPIER", service=self.service)
        self.liste.statut = ServiceGarde.STATUT_PUBLIEE
        self.liste.application = ServiceGarde.APPLICATION_ACTIVE
        self.liste.date_debut = timezone.localdate() - timedelta(days=1)
        self.liste.save()
        self.liste.creneaux.all().delete()
        self.debut = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
        CreneauServiceGarde.objects.create(service_garde=self.liste, poste="Gradé 1", debut=self.debut, fin=self.debut + timedelta(hours=24), marin=self.marin)
        CreneauServiceGarde.objects.create(service_garde=self.liste, poste="Gradé 2", debut=self.debut, fin=self.debut + timedelta(hours=24), marin=self.autre)
        CreneauServiceGarde.objects.create(service_garde=self.liste, poste="Gradé 3", debut=self.debut, fin=self.debut + timedelta(hours=24), marin=None)
        self.quart = Quart.objects.create(
            nom="Quart machine", service=self.service, fonction=FonctionQuartChoice.objects.create(name="Machine"),
            date_debut=timezone.localdate() - timedelta(days=1), date_fin=timezone.localdate() + timedelta(days=7), statut=Quart.STATUT_PUBLIEE,
        )
        CreneauQuart.objects.create(quart=self.quart, poste="Machine avant", debut=self.debut + timedelta(days=1), fin=self.debut + timedelta(days=1, hours=4), marin=self.marin)

    def _page(self, user, **params):
        self.client.force_login(user)
        return self.client.get(reverse("quarts-index"), params)

    def _semaine(self):
        return debut_de_semaine(self.debut.date().isoformat()).date().isoformat()

    def test_le_marin_voit_la_vue_quotidienne_et_son_prochain_tour(self):
        reponse = self._page(self.marin, semaine=self._semaine())
        self.assertContains(reponse, "Quarts et tours de service")
        self.assertContains(reponse, "Mon prochain tour")
        self.assertContains(reponse, "Gradé 1")
        self.assertContains(reponse, "Machine avant")
        self.assertContains(reponse, "Proposer un échange")

    def test_le_marin_n_a_pas_la_vue_responsable(self):
        reponse = self._page(self.marin, vue="marin", semaine=self._semaine())
        self.assertNotContains(reponse, "Par marin (responsables)")
        self.assertNotContains(reponse, "Planning par marin")

    def test_le_chef_voit_la_grille_par_marin_et_les_postes_a_pourvoir(self):
        reponse = self._page(self.chef, vue="marin", semaine=self._semaine())
        self.assertContains(reponse, "Planning par marin")
        self.assertContains(reponse, "1 poste à pourvoir")
        self.assertContains(reponse, "Gradé 3")

    def test_un_marin_d_un_autre_batiment_ne_voit_rien_de_cette_liste(self):
        ailleurs = Ship.objects.create(name="Autre bâtiment", code="AUT")
        etranger = self._user("etranger", "EQUIPIER")
        etranger.profile.ship = ailleurs
        etranger.profile.save()
        reponse = self._page(etranger, semaine=self._semaine())
        self.assertNotContains(reponse, "Gradé 1")
        self.assertNotContains(reponse, "Machine avant")

    def test_semaine_invalide_sans_erreur(self):
        self.assertEqual(self._page(self.marin, semaine="n'importe quoi").status_code, 200)

    def test_onglet_listes_pour_le_chef(self):
        reponse = self._page(self.chef, vue="listes")
        self.assertContains(reponse, "Services à quai")
        self.assertContains(reponse, "Quarts à la mer")

    def test_le_mode_quai_place_les_tours_avant_les_quarts(self):
        contenu = self._page(self.marin, semaine=self._semaine()).content.decode()
        self.assertLess(contenu.index("Tours à quai"), contenu.index("Quarts à la mer"))

    def test_liste_previsionnelle_signalee_et_sans_echange(self):
        self.liste.application = ServiceGarde.APPLICATION_PREVISIONNELLE
        self.liste.prise_effet_prevue = timezone.now() + timedelta(days=5)
        self.liste.save()
        reponse = self._page(self.marin, semaine=self._semaine())
        self.assertContains(reponse, "prévisionnel")

    def test_aucun_encadre_explicatif_inutile(self):
        self.assertNotContains(self._page(self.marin), "Rapprochez-vous de votre chef de service")

    def test_le_publicateur_retrouve_la_liste_a_publier_depuis_l_entree(self):
        self.liste.statut = ServiceGarde.STATUT_PROPOSEE
        self.liste.nom = "Liste en attente"
        self.liste.save()
        reponse = self._page(self.commandant)
        self.assertContains(reponse, "Liste en attente")
        self.assertContains(reponse, "à publier")
        self.assertNotContains(self._page(self.marin), "à publier")
