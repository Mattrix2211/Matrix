"""AC-18 : limitation progressive des connexions — comptage exact, sources, blocage progressif, expiration, purge, concurrence."""
import base64
import threading
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from accounts import securite
from accounts.models import AuditLog, CompteurConnexion

User = get_user_model()
MAX = settings.TENTATIVES_CONNEXION_MAX


def _tenter(identifiant, mot_de_passe, adresse="10.0.0.1"):
    return Client(REMOTE_ADDR=adresse).post("/accounts/login/", {"username": identifiant, "password": mot_de_passe})


def _connecte(identifiant, mot_de_passe, adresse="10.0.0.1"):
    reponse = _tenter(identifiant, mot_de_passe, adresse)
    return reponse.status_code == 302


class LimitationTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin", password="bon-mdp-123")
        self.voisin = User.objects.create_user(username="voisin", password="bon-mdp-456")

    def _couple(self, identifiant, source):
        return CompteurConnexion.objects.get(identifiant=identifiant, source=source)

    def test_un_identifiant_inexistant_n_ouvre_aucun_compteur(self):
        for i in range(30):
            _tenter(f"invente-{i}", "x", adresse=f"10.1.0.{i}")
        self.assertEqual(CompteurConnexion.objects.count(), 0)
        self.assertFalse(_connecte("invente-0", "x"))

    def test_la_date_d_activite_est_indexee_pour_la_purge(self):
        self.assertTrue(CompteurConnexion._meta.get_field("derniere_activite").db_index)

    def test_valeurs_par_defaut_validees(self):
        self.assertEqual(
            (settings.TENTATIVES_CONNEXION_MAX, settings.VERROUILLAGE_CONNEXION_MINUTES, settings.TENTATIVES_CODE_MAX,
             settings.CODE_REINITIALISATION_VALIDITE_MINUTES, settings.CONSERVATION_COMPTEURS_JOURS), (5, 15, 5, 30, 30))

    def test_chaque_echec_est_compte_exactement_une_fois_connexion_et_api(self):
        _tenter("marin", "mauvais")
        self.assertEqual(self._couple("marin", "10.0.0.1").essais, 1)
        jeton = base64.b64encode(b"marin:mauvais").decode()
        Client(REMOTE_ADDR="10.0.0.2").get("/api/notifications/", HTTP_AUTHORIZATION=f"Basic {jeton}")
        self.assertEqual(self._couple("marin", "10.0.0.2").essais, 1)  # une requête d'API ne double pas le compte
        self.assertEqual(self._couple("marin", securite.SOURCE_GLOBALE).essais, 2)

    def test_blocage_du_couple_au_seuil_meme_avec_le_bon_mot_de_passe(self):
        for _ in range(MAX):
            _tenter("marin", "mauvais")
        self.assertFalse(_connecte("marin", "bon-mdp-123"))
        self.assertTrue(AuditLog.objects.filter(action="connexion_limitee").exists())

    def test_un_tiers_depuis_un_autre_poste_ne_bloque_pas_le_marin_depuis_son_poste(self):
        self.assertTrue(_connecte("marin", "bon-mdp-123", "10.0.0.1"))  # poste habituel
        for _ in range(MAX):
            _tenter("marin", "mauvais", "203.0.113.9")  # le tiers
        self.assertTrue(_connecte("marin", "bon-mdp-123", "10.0.0.1"))
        self.assertFalse(_connecte("marin", "bon-mdp-123", "203.0.113.9"))  # le tiers lui-même reste bloqué

    def test_attaque_repartie_sur_plusieurs_postes_bloque_les_sources_inconnues_seulement(self):
        self.assertTrue(_connecte("marin", "bon-mdp-123", "10.0.0.1"))
        for i in range(MAX * securite.FACTEUR_GLOBAL):
            _tenter("marin", "mauvais", f"198.51.100.{i % 250}")
        self.assertTrue(_connecte("marin", "bon-mdp-123", "10.0.0.1"))  # poste connu : jamais privé de son compte
        self.assertFalse(_connecte("marin", "bon-mdp-123", "192.0.2.77"))  # source inconnue : attente progressive

    def test_utilisateurs_legitimes_qui_partagent_une_adresse_sont_independants(self):
        for _ in range(MAX):
            _tenter("marin", "mauvais", "10.0.0.5")
        self.assertTrue(_connecte("voisin", "bon-mdp-456", "10.0.0.5"))  # même poste, autre identifiant
        self.assertFalse(_connecte("marin", "bon-mdp-123", "10.0.0.5"))

    def test_blocage_progressif_puis_expiration(self):
        for _ in range(MAX):
            _tenter("marin", "mauvais")
        premier = self._couple("marin", "10.0.0.1")
        self.assertTrue(timedelta(minutes=14) < premier.bloque_jusqua - timezone.now() <= timedelta(minutes=15))
        CompteurConnexion.objects.filter(pk=premier.pk).update(bloque_jusqua=timezone.now() - timedelta(seconds=1))
        for _ in range(MAX):
            _tenter("marin", "mauvais")
        second = self._couple("marin", "10.0.0.1")
        self.assertTrue(timedelta(minutes=29) < second.bloque_jusqua - timezone.now() <= timedelta(minutes=30))  # la durée double
        CompteurConnexion.objects.filter(pk=second.pk).update(bloque_jusqua=timezone.now() - timedelta(seconds=1))
        self.assertTrue(_connecte("marin", "bon-mdp-123"))  # blocage expiré, compteur remis à zéro par le succès
        self.assertEqual(self._couple("marin", "10.0.0.1").niveau, 0)

    def test_pas_de_blocage_durable_une_periode_calme_retombe_au_niveau_zero(self):
        for _ in range(MAX):
            _tenter("marin", "mauvais")
        CompteurConnexion.objects.filter(identifiant="marin", source="10.0.0.1").update(
            bloque_jusqua=None, derniere_activite=timezone.now() - timedelta(minutes=settings.VERROUILLAGE_CONNEXION_PLAFOND_MINUTES + 1))
        _tenter("marin", "mauvais")
        self.assertEqual(self._couple("marin", "10.0.0.1").niveau, 0)

    def test_la_duree_de_blocage_a_un_plafond(self):
        self.assertEqual(securite._duree_blocage(20), timedelta(minutes=settings.VERROUILLAGE_CONNEXION_PLAFOND_MINUTES))

    def test_purge_des_compteurs_inactifs_sans_toucher_aux_journaux_d_audit(self):
        for _ in range(MAX):
            _tenter("marin", "mauvais")
        traces = AuditLog.objects.count()
        CompteurConnexion.objects.update(derniere_activite=timezone.now() - timedelta(days=31))
        CompteurConnexion.objects.create(identifiant="recent", source="10.0.0.9", derniere_activite=timezone.now())
        self.assertGreater(securite.purger_compteurs(), 0)
        self.assertEqual(list(CompteurConnexion.objects.values_list("identifiant", flat=True)), ["recent"])
        self.assertEqual(AuditLog.objects.count(), traces)  # les preuves d'audit survivent à la purge
        from accounts.tasks import purger_compteurs_connexion
        self.assertEqual(purger_compteurs_connexion(), 0)

    def test_la_tache_de_purge_est_planifiee(self):
        self.assertEqual(settings.CELERY_BEAT_SCHEDULE["purger_compteurs_connexion_daily"]["task"], "accounts.tasks.purger_compteurs_connexion")

    def test_la_source_est_l_adresse_directe_jamais_un_en_tete_du_client(self):
        reponse = Client(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4").post(
            "/accounts/login/", {"username": "marin", "password": "mauvais"})
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(CompteurConnexion.objects.filter(identifiant="marin", source="10.0.0.1").exists())
        self.assertFalse(CompteurConnexion.objects.filter(source="1.2.3.4").exists())


class AtomiciteTests(TransactionTestCase):
    def test_echecs_concurrents_tous_comptes(self):
        User.objects.create_user(username="marin", password="bon-mdp-123")
        erreurs = []

        def rafale():
            try:
                for _ in range(3):
                    securite.enregistrer_echec("marin", "10.0.0.1")
            except Exception as exc:  # noqa: BLE001
                erreurs.append(exc)
            finally:
                connection.close()

        fils = [threading.Thread(target=rafale) for _ in range(4)]
        [f.start() for f in fils]
        [f.join() for f in fils]
        self.assertEqual(erreurs, [])
        total = 12  # 4 fils x 3 échecs ; chaque série de MAX échecs remet l'essai à zéro et monte le niveau
        couple = CompteurConnexion.objects.get(identifiant="marin", source="10.0.0.1")
        self.assertEqual(couple.essais + couple.niveau * MAX, total)
