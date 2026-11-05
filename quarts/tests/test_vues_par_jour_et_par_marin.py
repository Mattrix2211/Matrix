"""Vues A (par jour) et B (par marin), indicateur de mode, distinction planifié / applicable."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import FonctionQuartChoice
from quarts.models import CreneauQuart, Quart
from quarts.mouvements import declarer_mouvement
from quarts.tests.test_activation_liste_quai import BaseActivation


class VuesAEtBTests(BaseActivation):
    def _get(self, user, vue, url=None):
        self.client.force_login(user)
        return self.client.get(url or self.url, {"vue": vue})

    def test_vue_a_marque_le_previsionnel_et_ne_le_presente_pas_comme_applicable(self):
        self._previsionnelle()
        page = self._get(self.chef, "jour").content.decode()
        self.assertIn("Prévisionnel", page)
        self.assertIn("non applicable avant activation", page)
        self.assertIn("mx-jour__ligne--previsionnel", page)

    def test_vue_a_apres_activation_applicable_et_a_venir(self):
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        page = self._get(self.marin, "jour").content.decode()
        self.assertIn("Applicable", page)
        self.assertIn("À venir", page)
        self.assertNotIn("En cours", page)

    def test_vue_a_met_en_evidence_mes_creneaux(self):
        self._previsionnelle()
        self.assertIn("mx-jour__ligne--moi", self._get(self.marin, "jour").content.decode())
        self.assertNotIn("mx-jour__ligne--moi", self._get(self.chef, "jour").content.decode())

    def test_vue_b_reservee_aux_responsables_et_heures_reelles_non_renseignees(self):
        self._previsionnelle()
        page = self._get(self.chef, "marin").content.decode()
        self.assertIn("Heures réellement travaillées", page)
        self.assertIn("Non renseigné", page)
        self.assertIn("(planifiée)", page)
        autre = self._get(self.marin, "marin").content.decode()
        self.assertNotIn("Heures réellement travaillées", autre)  # onglet absent : retombe sur le planning

    def test_vue_b_ne_deduit_pas_les_heures_travaillees_des_horaires(self):
        self._previsionnelle()
        page = self._get(self.chef, "marin").content.decode()
        self.assertEqual(page.count('<td class="mx-non-renseigne">Non renseigné</td>'), 1)  # un marin affecté, une valeur jamais calculée

    def test_un_quart_futur_n_est_pas_presente_en_cours(self):
        quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=5),
            statut=Quart.STATUT_PUBLIEE, created_by=self.commandant,
        )
        debut = timezone.now() + timedelta(days=1)
        CreneauQuart.objects.create(quart=quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        self.client.force_login(self.commandant)
        page = self.client.get(reverse("quart-detail", args=[quart.pk]), {"vue": "jour"}).content.decode()
        self.assertIn("À venir", page)
        self.assertNotIn("En cours", page)

    def test_un_quart_passe_pendant_que_le_batiment_etait_a_quai_est_hors_regime(self):
        quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Veille"),
            date_debut=timezone.localdate() - timedelta(days=3), date_fin=timezone.localdate() + timedelta(days=3),
            statut=Quart.STATUT_PUBLIEE, created_by=self.commandant,
        )
        debut = timezone.now() - timedelta(hours=5)  # le bâtiment est à quai depuis J-2 (initialisation)
        CreneauQuart.objects.create(quart=quart, poste="Veille", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        self.client.force_login(self.commandant)
        page = self.client.get(reverse("quart-detail", args=[quart.pk]), {"vue": "jour"}).content.decode()
        self.assertIn("Hors régime", page)

    def test_indicateur_de_mode_sur_la_fiche_l_index_et_l_accueil(self):
        self._previsionnelle()  # liste publiée : lisible par le marin
        self.client.force_login(self.marin)
        for url in (self.url, reverse("quarts-index"), reverse("home")):
            page = self.client.get(url).content.decode()
            self.assertIn("mx-mode--quai", page, url)

    def test_indicateur_non_renseigne_sans_initialisation(self):
        from quarts.models import MouvementBatiment

        MouvementBatiment.objects.all().delete()
        self.client.force_login(self.marin)
        self.assertIn("mx-mode--inconnu", self.client.get(reverse("home")).content.decode())

    def test_indicateur_suit_les_transitions(self):
        declarer_mouvement(self.comaeq, self.ship, "APPAREILLAGE", timezone.now() - timedelta(minutes=5))
        self.client.force_login(self.marin)
        self.assertIn("mx-mode--mer", self.client.get(reverse("home")).content.decode())

    def test_l_index_priorise_les_services_a_quai_en_mode_quai_sans_masquer_les_quarts(self):
        self.client.force_login(self.chef)
        page = self.client.get(reverse("quarts-index"), {"vue": "listes"}).content.decode()
        self.assertLess(page.index("Services à quai"), page.index("Quarts à la mer"))
        self.assertNotIn("mx-qt__prioritaire", page)  # en mode quai, ce sont les services à quai qui passent en premier
        self.assertIn("Quarts à la mer", page)  # sans masquer les quarts
