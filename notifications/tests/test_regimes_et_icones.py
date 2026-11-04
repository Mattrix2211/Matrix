"""D7 : régime d'une notification (MER / QUAI / COMMUNES / TRANSITION) et icône par catégorie.

La couleur dit la priorité, l'icône dit la catégorie ; aucune notification n'est supprimée selon le mode."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from matrix.core.icones import classe_icone
from notifications.categories import categorie_de, enrichir_categorie
from notifications.models import Notification, NotificationLevel, RegimeNotification
from notifications.regimes import repartir
from quarts.mouvements import declarer_mouvement
from quarts.tests.test_activation_liste_quai import BaseActivation


class IconesEtCategoriesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")

    def _n(self, **champs):
        return Notification.objects.create(user=self.user, verb="x", **champs)

    def test_icone_explicite_ou_deduite_de_la_cible(self):
        from django.contrib.contenttypes.models import ContentType
        from taches.models import Tache

        assert classe_icone("echange") == "bi-arrow-left-right"
        self.assertEqual(categorie_de(self._n(categorie="quart")), "quart")
        tache = Tache.objects.create(titre="T", created_by=self.user, assigne=self.user)
        deduite = self._n(content_type=ContentType.objects.get_for_model(Tache), object_id=str(tache.pk))
        self.assertEqual(categorie_de(deduite), "tache")
        self.assertEqual(enrichir_categorie(deduite).icone, "bi-check2-square")

    def test_categorie_inconnue_retombe_sur_la_cloche(self):
        n = enrichir_categorie(self._n(categorie="inventee"))
        self.assertEqual((n.categorie_cle, n.icone), ("notifications", "bi-bell"))

    def test_correspondance_du_catalogue_valide(self):
        attendu = {"quart": "bi-clock", "calendrier": "bi-calendar3", "echange": "bi-arrow-left-right", "maintenance": "bi-tools",
                   "tache": "bi-check2-square", "discussion": "bi-chat-left-text", "document": "bi-file-earmark-text",
                   "anomalie": "bi-exclamation-triangle", "terminee": "bi-check-circle"}
        for cle, icone in attendu.items():
            self.assertEqual(classe_icone(cle), icone)

    def test_regime_par_defaut_communes_pour_programme_et_releves(self):
        self.assertEqual(self._n().regime, RegimeNotification.COMMUNES)


class RepartitionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")
        self.mer = self._n(regime="MER")
        self.quai = self._n(regime="QUAI")
        self.communes = self._n(regime="COMMUNES")
        self.transition = self._n(regime="TRANSITION")
        self.quai_urgente = self._n(regime="QUAI", level=NotificationLevel.DANGER)
        self.quai_action = self._n(regime="QUAI", action_requise=True)
        self.quai_action_traitee = self._n(regime="QUAI", action_requise=True, traitee_le=timezone.now())
        self.toutes = list(Notification.objects.all())

    def _n(self, **champs):
        return Notification.objects.create(user=self.user, verb=champs.get("regime", "x"), **champs)

    def test_en_mode_mer_le_quai_passe_apres_sauf_urgent_et_action_a_traiter(self):
        prioritaires, autres = repartir(self.toutes, "MER")
        self.assertEqual({n.pk for n in prioritaires}, {self.mer.pk, self.communes.pk, self.transition.pk, self.quai_urgente.pk, self.quai_action.pk})
        self.assertEqual({n.pk for n in autres}, {self.quai.pk, self.quai_action_traitee.pk})

    def test_en_mode_quai_le_mer_passe_apres(self):
        prioritaires, autres = repartir(self.toutes, "QUAI")
        self.assertIn(self.quai.pk, {n.pk for n in prioritaires})
        self.assertEqual({n.pk for n in autres}, {self.mer.pk})

    def test_aucune_notification_supprimee_ni_dupliquee(self):
        for mode in ("MER", "QUAI", None):
            prioritaires, autres = repartir(self.toutes, mode)
            self.assertEqual(sorted(n.pk for n in prioritaires + autres), sorted(n.pk for n in self.toutes))

    def test_mode_non_renseigne_ne_regroupe_rien(self):
        prioritaires, autres = repartir(self.toutes, None)
        self.assertEqual((len(prioritaires), autres), (len(self.toutes), []))


class EtiquetageEtAffichageTests(BaseActivation):
    def _regime(self, **filtre):
        return set(Notification.objects.filter(**filtre).values_list("regime", "categorie"))

    def test_activation_et_alertes_sont_quai_et_l_accostage_est_transition(self):
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        self.assertIn(("QUAI", "terminee"), self._regime(user=self.marin, verb__contains="maintenant active"))
        from quarts.mouvements import mode_du_batiment

        self.assertEqual(mode_du_batiment(self.ship), "QUAI")

    def test_alerte_d_accostage_est_transition_et_alerte(self):
        from quarts.models import ServiceGarde

        ServiceGarde.objects.all().delete()
        from quarts.mouvements import initialiser_mode

        Notification.objects.all().delete()
        # un mouvement d'appareillage puis d'accostage : alerte « aucune liste préparée »
        declarer_mouvement(self.comaeq, self.ship, "APPAREILLAGE", timezone.now() - timedelta(hours=2))
        declarer_mouvement(self.comaeq, self.ship, "ACCOSTAGE", timezone.now() - timedelta(minutes=5))
        self.assertIn(("TRANSITION", "anomalie"), self._regime(verb__contains="aucune liste"))

    def test_publication_d_un_quart_est_mer_et_celle_d_un_service_est_quai(self):
        self._previsionnelle()
        self.assertTrue(Notification.objects.filter(user=self.marin, regime="QUAI", categorie="calendrier").exists())

    def test_le_panneau_affiche_l_icone_et_regroupe_sans_masquer(self):
        self._previsionnelle()
        self._poster(self.chef, action="activer")
        Notification.objects.create(user=self.marin, verb="Un quart de la mer", regime="MER", level=NotificationLevel.INFO, categorie="quart")
        self.client.force_login(self.marin)
        page = self.client.get(reverse("notifications-panneau")).content.decode()  # mode QUAI : le MER passe en « Autres régimes »
        self.assertIn("mx-notif__icone", page)
        self.assertIn("bi-clock", page)
        self.assertIn("Autres régimes (1)", page)
        self.assertIn("Un quart de la mer", page)  # jamais masqué
        self.assertIn("maintenant active", page)

    def test_sans_mode_aucun_groupe_autres_regimes(self):
        from quarts.models import MouvementBatiment

        MouvementBatiment.objects.all().delete()
        Notification.objects.create(user=self.marin, verb="Quai", regime="QUAI", categorie="calendrier")
        Notification.objects.create(user=self.marin, verb="Mer", regime="MER", categorie="quart")
        self.client.force_login(self.marin)
        page = self.client.get(reverse("notifications-panneau")).content.decode()
        self.assertNotIn("Autres régimes", page)

    def test_le_centre_affiche_aussi_les_icones(self):
        Notification.objects.create(user=self.marin, verb="Échange", regime="QUAI", categorie="echange")
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("notifications-centre")), "bi-arrow-left-right")
