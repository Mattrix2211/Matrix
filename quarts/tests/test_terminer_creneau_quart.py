"""D6 : terminer un créneau de quart à l'heure effective — droits, motif, période écoulée préservée, versions, notifications."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice
from notifications.models import Notification
from quarts.models import ChefDeListe, CreneauQuart, Quart
from quarts.tests.test_activation_liste_quai import BaseActivation


def _fmt(dt):
    return timezone.localtime(dt).strftime("%Y-%m-%dT%H:%M")


class TerminerCreneauQuartTests(BaseActivation):
    def setUp(self):
        super().setUp()
        # Le chef à quai est explicitement désigné pour les services à quai seulement (D11).
        ChefDeListe.objects.filter(user=self.chef).delete()
        ChefDeListe.objects.create(user=self.chef, service=self.service, type_liste=ChefDeListe.TYPE_QUAI)
        self.chef_quarts = self._user("chef_quarts", "EQUIPIER", service=self.service)
        ChefDeListe.objects.create(user=self.chef_quarts, service=self.service, type_liste=ChefDeListe.TYPE_QUARTS)
        self.quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate() - timedelta(days=1), date_fin=timezone.localdate() + timedelta(days=3),
            statut=Quart.STATUT_PUBLIEE, created_by=self.chef_quarts,
        )
        debut = timezone.now() - timedelta(hours=1)
        self.creneau = CreneauQuart.objects.create(quart=self.quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=6), marin=self.marin)
        self.url_quart = reverse("quart-detail", args=[self.quart.pk])

    def _terminer(self, user, fin, motif="Accostage"):
        self.client.force_login(user)
        return self.client.post(self.url_quart, {"action": "terminer_creneau", "creneau_id": self.creneau.pk, "nouvelle_fin": _fmt(fin), "motif": motif})

    def test_le_responsable_des_quarts_termine_le_creneau_et_tout_est_trace(self):
        ancienne = self.creneau.fin
        nouvelle = timezone.now() + timedelta(hours=1)
        self._terminer(self.chef_quarts, nouvelle)
        self.creneau.refresh_from_db()
        self.assertLess(self.creneau.fin, ancienne)
        self.assertEqual(self.creneau.fin_initiale, ancienne)
        self.assertEqual(self.creneau.marin, self.marin)  # affectation conservée sur la partie restante
        self.assertEqual(self.quart.versions.count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="quart_creneau_termine", details__contains="Accostage").exists())
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="prend fin plus tôt").exists())

    def test_la_supervision_du_commandant_peut_aussi(self):
        self._terminer(self.commandant, timezone.now() + timedelta(hours=1))
        self.creneau.refresh_from_db()
        self.assertIsNotNone(self.creneau.fin_initiale)

    def test_le_chef_de_liste_a_quai_n_a_jamais_ce_droit(self):
        ancienne = self.creneau.fin
        reponse = self._terminer(self.chef, timezone.now() + timedelta(hours=1))
        self.assertEqual(reponse.status_code, 403)  # il voit le quart mais l'action lui est interdite
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.fin, ancienne)
        self.assertIsNone(self.creneau.fin_initiale)

    def test_comaeq_marin_et_remplacant_a_quai_sans_droit(self):
        ancienne = self.creneau.fin
        for user in (self.comaeq, self.marin):
            self._terminer(user, timezone.now() + timedelta(hours=1))
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.fin, ancienne)

    def test_motif_obligatoire(self):
        ancienne = self.creneau.fin
        self._terminer(self.chef_quarts, timezone.now() + timedelta(hours=1), motif="")
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.fin, ancienne)

    def test_la_periode_deja_ecoulee_est_preservee(self):
        ancienne = self.creneau.fin
        self._terminer(self.chef_quarts, timezone.now() - timedelta(minutes=10))  # fin dans le passé
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.fin, ancienne)

    def test_fin_hors_bornes_refusee(self):
        ancienne = self.creneau.fin
        self._terminer(self.chef_quarts, ancienne + timedelta(hours=1))  # rallonger n'est pas terminer
        self._terminer(self.chef_quarts, self.creneau.debut - timedelta(hours=1))
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.fin, ancienne)

    def test_un_creneau_deja_termine_ne_peut_plus_etre_modifie(self):
        CreneauQuart.objects.filter(pk=self.creneau.pk).update(fin=timezone.now() - timedelta(minutes=1))
        ancienne = CreneauQuart.objects.get(pk=self.creneau.pk).fin
        self._terminer(self.chef_quarts, timezone.now() + timedelta(hours=1))
        self.assertEqual(CreneauQuart.objects.get(pk=self.creneau.pk).fin, ancienne)

    def test_liste_non_publiee_refusee(self):
        Quart.objects.filter(pk=self.quart.pk).update(statut=Quart.STATUT_BROUILLON)
        ancienne = self.creneau.fin
        self._terminer(self.chef_quarts, timezone.now() + timedelta(hours=1))
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.fin, ancienne)

    def test_la_regularisation_leve_le_conflit_d_activation_sans_raccourcissement_automatique(self):
        from quarts.activation import conflits_activation

        garde = self.liste.creneaux.get()
        garde.debut, garde.fin = timezone.now() - timedelta(minutes=30), timezone.now() + timedelta(hours=20)
        garde.save()
        self.assertEqual(len(conflits_activation(self.liste)), 1)  # quart en cours + service en cours : bloquant
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.liste.refresh_from_db()
        self.assertEqual(self.liste.application, "PREVISIONNELLE")  # Matrix n'a rien raccourci
        self.creneau.refresh_from_db()
        self.assertIsNone(self.creneau.fin_initiale)
        self._terminer(self.chef_quarts, timezone.now() + timedelta(seconds=90))
        self.assertEqual(len(conflits_activation(self.liste, timezone.now() + timedelta(minutes=3))), 0)

    def test_ancienne_fin_visible_dans_la_fiche(self):
        self._terminer(self.chef_quarts, timezone.now() + timedelta(hours=1))
        self.client.force_login(self.chef_quarts)
        self.assertContains(self.client.get(self.url_quart), "Terminé plus tôt")
