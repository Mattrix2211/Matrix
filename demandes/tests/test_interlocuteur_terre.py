"""Interlocuteur à terre : dossier reçu « à traiter » jusqu'à sa première réponse ou la clôture, sans accès élargi."""
from django.urls import reverse

from dashboard.aujourdhui import demandes_a_traiter
from demandes import services
from demandes.models import Demande
from demandes.tests.test_demandes import DemandesBase
from notifications.models import Notification


class DossierRecuTests(DemandesBase):
    def setUp(self):
        super().setUp()
        services.ajouter_interlocuteur(self.demande, self.chef, self.expert)

    def _index(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("demandes-index")).context

    def test_ajout_cree_une_alerte_d_action(self):
        self.assertTrue(Notification.objects.filter(
            user=self.expert, action_requise=True, traitee_le__isnull=True, verb__contains="vous a ajouté").exists())

    def test_dossier_recu_a_traiter_liste_et_accueil(self):
        contexte = self._index(self.expert)
        self.assertEqual(contexte["a_traiter"], [self.demande])
        self.assertEqual(contexte["suivies"], [])
        self.assertEqual(demandes_a_traiter(self.expert), [self.demande])

    def test_premiere_reponse_sort_de_a_traiter(self):
        self.client.force_login(self.expert)
        r = self.client.post(reverse("demande-commentaire", args=[self.demande.pk]), {"body": "Reçu."})
        self.assertEqual(r.status_code, 302)
        contexte = self._index(self.expert)
        self.assertEqual(contexte["a_traiter"], [])
        self.assertEqual(contexte["suivies"], [self.demande])
        self.assertEqual(demandes_a_traiter(self.expert), [])

    def test_reponse_sort_aussi_quand_le_dossier_est_resolu(self):
        services.changer_etat(self.demande, self.chef, Demande.ETAT_RESOLU)
        self.assertEqual(demandes_a_traiter(self.expert), [self.demande])
        services.repondre(self.demande, self.expert, "Vu.")
        self.assertEqual(demandes_a_traiter(self.expert), [])

    def test_cloture_solde_l_alerte(self):
        services.changer_etat(self.demande, self.chef, Demande.ETAT_RESOLU)
        services.changer_etat(self.demande, self.marin, Demande.ETAT_CLOS)
        self.assertEqual(demandes_a_traiter(self.expert), [])
        self.assertEqual(self._index(self.expert)["a_traiter"], [])

    def test_non_acteur_ne_voit_rien(self):
        for autre in (self.voisin, self.etranger):
            contexte = self._index(autre)
            self.assertEqual(contexte["a_traiter"], [])
            self.assertEqual(contexte["suivies"], [])
            self.assertEqual(demandes_a_traiter(autre), [])
            self.assertEqual(self.client.get(reverse("demande-detail", args=[self.demande.pk])).status_code, 404)

    def test_alerte_sans_etre_interlocuteur_n_ouvre_rien(self):
        Notification.objects.create(user=self.voisin, verb="x", target=self.demande, action_requise=True)
        self.assertEqual(demandes_a_traiter(self.voisin), [])
        self._index(self.voisin)
        self.assertEqual(self.client.get(reverse("demande-detail", args=[self.demande.pk])).status_code, 404)


class EquipageATerreDemandesTests(DemandesBase):
    def test_a_terre_ne_peut_que_repondre(self):
        services.ajouter_interlocuteur(self.demande, self.chef, self.expert)
        self.client.force_login(self.expert)
        detail = self.client.get(reverse("demande-detail", args=[self.demande.pk])).content.decode()
        self.assertNotIn("Ajouter un interlocuteur", detail)
        self.assertNotIn("Assigner une action", detail)
        r = self.client.post(reverse("demande-action", args=[self.demande.pk]), {"action": "etat", "etat": Demande.ETAT_RESOLU}, follow=True)
        self.assertEqual([m for m in r.context["messages"] if m.level_tag == "success"], [])
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.etat, Demande.ETAT_OUVERT)

    def test_a_terre_ne_peut_pas_creer_de_tache_ni_modifier(self):
        self.client.force_login(self.expert)
        self.assertEqual(self.client.post(reverse("taches-index"), {"titre": "T", "assigne": self.marin.pk}).status_code, 403)
