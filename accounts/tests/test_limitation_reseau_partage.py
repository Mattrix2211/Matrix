"""AC-18, AC-21 : limitation des connexions et des codes derrière un mandataire inverse, sur des adresses partagées."""
import time
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

import ipaddress

from accounts import reinitialisation, securite
from accounts.models import CompteurConnexion, DemandeReinitialisation, UserProfile
from matrix import settings as reglages
from org.models import Ship

User = get_user_model()
MAX = settings.TENTATIVES_CONNEXION_MAX
MANDATAIRE = (ipaddress.ip_network("10.1.1.1/32"),)
NOUVEAU = "Nouveau-mdp-solide-42"


def _poster(client, identifiant, mot_de_passe):
    return client.post("/accounts/login/", {"username": identifiant, "password": mot_de_passe})


def _connecte(reponse):
    return reponse.status_code == 302


class SourceDeConfianceTests(TestCase):
    def _source(self, remote, forwarded=None):
        meta = {"REMOTE_ADDR": remote}
        if forwarded is not None:
            meta["HTTP_X_FORWARDED_FOR"] = forwarded
        return securite.source_de(RequestFactory().get("/", **meta))

    def test_par_defaut_l_en_tete_transmis_n_est_jamais_cru(self):
        self.assertEqual(self._source("203.0.113.9", "198.51.100.7"), "203.0.113.9")
        self.assertEqual(self._source("10.1.1.1", "198.51.100.7"), "10.1.1.1")

    @override_settings(MANDATAIRES_DE_CONFIANCE=MANDATAIRE)
    def test_l_en_tete_n_est_cru_que_depuis_un_mandataire_de_confiance(self):
        self.assertEqual(self._source("10.1.1.1", "198.51.100.7"), "198.51.100.7")
        self.assertEqual(self._source("203.0.113.9", "198.51.100.7"), "203.0.113.9")  # client direct : en-tête ignoré

    @override_settings(MANDATAIRES_DE_CONFIANCE=MANDATAIRE + (ipaddress.ip_network("10.2.0.0/16"),))
    def test_la_chaine_est_remontee_depuis_la_droite_jusqu_a_la_premiere_adresse_non_declaree(self):
        # Un client qui forge le début de la chaîne ne choisit pas sa source : seul l'ajout du mandataire fait foi.
        self.assertEqual(self._source("10.1.1.1", "9.9.9.9, 198.51.100.7, 10.2.3.4"), "198.51.100.7")
        self.assertEqual(self._source("10.1.1.1", "10.2.3.4"), "10.1.1.1")  # toute la chaîne est de confiance : adresse du mandataire

    @override_settings(MANDATAIRES_DE_CONFIANCE=MANDATAIRE)
    def test_une_chaine_illisible_ou_absente_n_est_pas_crue(self):
        self.assertEqual(self._source("10.1.1.1", "pas-une-adresse"), "10.1.1.1")
        self.assertEqual(self._source("10.1.1.1", "198.51.100.7, ???"), "10.1.1.1")
        self.assertEqual(self._source("10.1.1.1"), "10.1.1.1")

    def test_les_adresses_ipv6_sont_ramenees_a_leur_prefixe(self):
        self.assertEqual(self._source("2001:db8:1:2:aaaa:bbbb:cccc:dddd"), "2001:db8:1:2::/64")
        self.assertEqual(self._source("2001:db8:1:2:1:2:3:4"), "2001:db8:1:2::/64")  # même réseau, même source

    def test_configuration_des_mandataires_refusee_si_elle_est_trop_large_ou_invalide(self):
        self.assertEqual(reglages._mandataires_de_confiance("10.1.1.1, 192.168.0.0/24"),
                         (ipaddress.ip_network("10.1.1.1/32"), ipaddress.ip_network("192.168.0.0/24")))
        for valeur in ("0.0.0.0/0", "::/0", "pas-une-adresse"):
            with self.assertRaises(ImproperlyConfigured):
                reglages._mandataires_de_confiance(valeur)
        self.assertEqual(settings.MANDATAIRES_DE_CONFIANCE, ())


class AdresseReellementPartageeTests(TestCase):
    """Même adresse pour tous les marins (poste commun ou mandataire non déclaré) : un tiers ne prive pas le titulaire."""

    def setUp(self):
        self.titulaire = User.objects.create_user(username="titulaire", password="bon-mdp-123")
        self.voisin = User.objects.create_user(username="voisin", password="bon-mdp-456")
        premiere = Client(REMOTE_ADDR="192.0.2.1")
        self.assertTrue(_connecte(_poster(premiere, "titulaire", "bon-mdp-123")))  # le titulaire a déjà utilisé son poste
        self.cookie = premiere.cookies[securite.COOKIE_POSTE].value

    @property
    def poste(self):
        """Navigateur du titulaire : il présente son cookie de poste connu, sans session ouverte."""
        client = Client(REMOTE_ADDR="192.0.2.1")
        client.cookies[securite.COOKIE_POSTE] = self.cookie
        return client

    def _attaque(self, identifiant="titulaire", essais=MAX * 3):
        for _ in range(essais):
            _poster(Client(REMOTE_ADDR="192.0.2.1"), identifiant, "mauvais")

    def test_le_titulaire_se_connecte_depuis_son_poste_malgre_le_blocage_de_l_adresse_partagee(self):
        self._attaque()
        self.assertTrue(securite.est_limite("titulaire", "192.0.2.1"))
        self.assertFalse(_connecte(_poster(Client(REMOTE_ADDR="192.0.2.1"), "titulaire", "bon-mdp-123")))  # poste inconnu : attente
        self.assertTrue(_connecte(_poster(self.poste, "titulaire", "bon-mdp-123")))  # poste connu : le titulaire passe

    def test_les_autres_marins_de_la_meme_adresse_ne_sont_pas_atteints(self):
        self._attaque()
        self.assertTrue(_connecte(_poster(Client(REMOTE_ADDR="192.0.2.1"), "voisin", "bon-mdp-456")))

    def test_le_poste_connu_reste_protege_contre_les_essais_repetes(self):
        poste = self.poste
        for _ in range(MAX):
            self.assertFalse(_connecte(_poster(poste, "titulaire", "mauvais")))
        self.assertFalse(_connecte(_poster(poste, "titulaire", "bon-mdp-123")))  # bloqué sur ce poste seul, même avec le bon mot de passe
        self.assertTrue(_connecte(_poster(Client(REMOTE_ADDR="198.51.100.20"), "titulaire", "bon-mdp-123")))  # autre source, non bloquée

    def test_un_tiers_sans_le_cookie_reste_limite_et_ne_peut_pas_deviner(self):
        tiers = Client(REMOTE_ADDR="192.0.2.1")
        for _ in range(MAX):
            _poster(tiers, "titulaire", "mauvais")
        self.assertFalse(_connecte(_poster(tiers, "titulaire", "bon-mdp-123")))

    def test_un_cookie_falsifie_ou_destine_a_un_autre_identifiant_ne_donne_rien(self):
        self._attaque()
        pirate = Client(REMOTE_ADDR="192.0.2.1")
        pirate.cookies[securite.COOKIE_POSTE] = "valeur-forgee"
        self.assertFalse(_connecte(_poster(pirate, "titulaire", "bon-mdp-123")))
        autre = Client(REMOTE_ADDR="192.0.2.1")  # le cookie du voisin ne vaut pas pour le titulaire
        _poster(autre, "voisin", "bon-mdp-456")
        self.assertFalse(_connecte(_poster(autre, "titulaire", "bon-mdp-123")))

    def test_le_poste_est_revocable_par_la_reinitialisation_et_par_la_purge(self):
        self._attaque()
        securite.effacer_compteurs("titulaire")  # réinitialisation du mot de passe : tous les postes sont révoqués
        self.assertFalse(CompteurConnexion.objects.filter(identifiant="titulaire", source__startswith="poste:").exists())
        self.assertTrue(_connecte(_poster(self.poste, "titulaire", "bon-mdp-123")))  # plus de blocage ; un nouveau poste est enregistré
        CompteurConnexion.objects.filter(source__startswith="poste:").update(derniere_activite=timezone.now() - timedelta(days=400))
        self.assertGreater(securite.purger_compteurs(), 0)
        self.assertFalse(CompteurConnexion.objects.filter(source__startswith="poste:").exists())

    def test_les_postes_par_identifiant_sont_bornes(self):
        for i in range(securite.POSTES_PAR_IDENTIFIANT + 5):
            self.assertTrue(_connecte(_poster(Client(REMOTE_ADDR=f"192.0.2.{50 + i}"), "titulaire", "bon-mdp-123")))
        self.assertLessEqual(CompteurConnexion.objects.filter(identifiant="titulaire", source__startswith="poste:").count(),
                             securite.POSTES_PAR_IDENTIFIANT)

    @override_settings(MANDATAIRES_DE_CONFIANCE=MANDATAIRE)
    def test_derriere_un_mandataire_declare_les_clients_ont_chacun_leur_source(self):
        def depuis(client_reel):
            return Client(REMOTE_ADDR="10.1.1.1", HTTP_X_FORWARDED_FOR=client_reel)
        for _ in range(MAX):
            _poster(depuis("198.51.100.5"), "voisin", "mauvais")
        self.assertFalse(_connecte(_poster(depuis("198.51.100.5"), "voisin", "bon-mdp-456")))
        self.assertTrue(_connecte(_poster(depuis("198.51.100.6"), "voisin", "bon-mdp-456")))  # un autre client du même mandataire passe

    def test_blocage_et_identifiant_inexistant_donnent_la_meme_reponse_publique(self):
        self._attaque()
        bloque = _poster(Client(REMOTE_ADDR="192.0.2.1"), "titulaire", "bon-mdp-123")
        inconnu = _poster(Client(REMOTE_ADDR="192.0.2.1"), "fantome", "bon-mdp-123")
        faux = _poster(Client(REMOTE_ADDR="192.0.2.77"), "titulaire", "mauvais")
        self.assertEqual((bloque.status_code, inconnu.status_code, faux.status_code), (200, 200, 200))
        marqueur = lambda r: r.content.decode().count("alert")  # noqa: E731
        self.assertEqual(marqueur(bloque), marqueur(inconnu))
        self.assertEqual(marqueur(faux), marqueur(inconnu))

    def test_un_blocage_n_economise_pas_le_calcul_du_mot_de_passe(self):
        self._attaque()
        with mock.patch("django.contrib.auth.base_user.AbstractBaseUser.set_password") as dummy:
            _poster(Client(REMOTE_ADDR="192.0.2.1"), "titulaire", "bon-mdp-123")
        self.assertTrue(dummy.called)


class CodesDeReinitialisationReseauTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.technique = User.objects.create_user(username="technique", password="x")
        UserProfile.objects.filter(user=self.technique).update(administrateur_technique=True, ship=navire, role="EQUIPIER")
        self.titulaire = User.objects.create_user(username="titulaire", password="bon-mdp-123")
        UserProfile.objects.filter(user=self.titulaire).update(ship=navire, role="EQUIPIER")
        self.poste = Client(REMOTE_ADDR="192.0.2.1")
        _poster(self.poste, "titulaire", "bon-mdp-123")  # poste connu du titulaire
        self.demande, self.code = reinitialisation.initier(
            User.objects.get(username="technique"), User.objects.get(username="titulaire"))

    def _essayer(self, source, code="AAAA-BBBB-CCCC-DDDD", postes=None):
        try:
            reinitialisation.utiliser("titulaire", code, "", NOUVEAU, source=source, postes=postes)
            return True
        except ValidationError:
            return False

    def test_cinq_essais_par_source_puis_blocage_meme_avec_le_bon_code(self):
        for _ in range(settings.TENTATIVES_CODE_MAX):
            self.assertFalse(self._essayer("203.0.113.1"))
        self.assertFalse(self._essayer("203.0.113.1", self.code))  # sixième essai de cette source : refusé
        self.assertTrue(self._essayer("203.0.113.2", self.code))  # le titulaire, autre source, aboutit

    def test_changer_d_adresse_ne_donne_pas_d_essais_illimites(self):
        total = settings.TENTATIVES_CODE_MAX * securite.FACTEUR_GLOBAL
        for i in range(total):
            self.assertFalse(self._essayer(f"203.0.113.{i % 250}-{i}"))
        self.assertFalse(self._essayer("203.0.113.200", self.code))  # source encore inconnue : le plafond de la demande s'applique
        compteur = CompteurConnexion.objects.get(identifiant=f"code:{self.demande.pk}", source=securite.SOURCE_GLOBALE)
        self.assertGreater(compteur.niveau, 0)

    def test_le_titulaire_avec_son_poste_connu_aboutit_malgre_les_essais_d_un_tiers(self):
        total = settings.TENTATIVES_CODE_MAX * securite.FACTEUR_GLOBAL
        for i in range(total):
            self._essayer(f"203.0.113.{i % 250}-{i}")
        postes = securite.postes_de(_requete_avec(self.poste))
        self.assertTrue(self._essayer("203.0.113.200", self.code, postes=postes))
        self.assertTrue(User.objects.get(username="titulaire").check_password(NOUVEAU))

    def test_les_essais_du_poste_connu_sont_limites_a_ce_poste(self):
        postes = securite.postes_de(_requete_avec(self.poste))
        for _ in range(settings.TENTATIVES_CODE_MAX):
            self.assertFalse(self._essayer("192.0.2.1", postes=postes))
        self.assertFalse(self._essayer("192.0.2.1", self.code, postes=postes))

    def test_identifiant_inconnu_ou_sans_demande_ou_code_faux_se_ressemblent(self):
        messages_ = set()
        for identifiant in ("fantome", "technique"):
            with self.assertRaises(ValidationError) as ctx:
                reinitialisation.utiliser(identifiant, "AAAA-BBBB-CCCC-DDDD", "", NOUVEAU, source="203.0.113.1")
            messages_.add(tuple(ctx.exception.messages))
        with self.assertRaises(ValidationError) as ctx:
            reinitialisation.utiliser("titulaire", "AAAA-BBBB-CCCC-DDDD", "", NOUVEAU, source="203.0.113.1")
        messages_.add(tuple(ctx.exception.messages))
        self.assertEqual(len(messages_), 1)
        self.assertFalse(CompteurConnexion.objects.filter(identifiant__in=("fantome", "code:0")).exists())

    def test_les_echecs_sans_demande_valide_coutent_un_calcul_comme_les_autres(self):
        with mock.patch("accounts.reinitialisation.check_password") as calcul:
            self._essayer("203.0.113.9")  # titulaire avec demande : vérification réelle (deux appels au plus)
            reel = calcul.call_count
            calcul.reset_mock()
            with self.assertRaises(ValidationError):
                reinitialisation.utiliser("fantome", "AAAA", "", NOUVEAU)
        self.assertGreaterEqual(reel, 1)
        self.assertEqual(calcul.call_count, 1)

    def test_le_succes_efface_les_compteurs_de_la_demande_et_les_postes(self):
        self._essayer("203.0.113.1")
        self.assertTrue(self._essayer("203.0.113.2", self.code))
        self.assertFalse(CompteurConnexion.objects.filter(identifiant=f"code:{self.demande.pk}").exists())
        self.assertFalse(CompteurConnexion.objects.filter(identifiant="titulaire").exists())


def _requete_avec(client):
    requete = RequestFactory().get("/")
    requete.COOKIES = {k: v.value for k, v in client.cookies.items()}
    return requete


class SourcesParticulieresTests(TestCase):
    def test_un_client_ipv4_vu_en_ipv6_mappe_garde_son_adresse(self):
        source = lambda a: securite.source_de(RequestFactory().get("/", REMOTE_ADDR=a))  # noqa: E731
        self.assertEqual(source("::ffff:203.0.113.9"), "203.0.113.9")
        self.assertNotEqual(source("::ffff:203.0.113.9"), source("::ffff:198.51.100.2"))

    @override_settings(MANDATAIRES_DE_CONFIANCE=MANDATAIRE)
    def test_une_adresse_mappee_transmise_par_le_mandataire_est_lue_comme_ipv4(self):
        requete = RequestFactory().get("/", REMOTE_ADDR="::ffff:10.1.1.1", HTTP_X_FORWARDED_FOR="::ffff:198.51.100.7")
        self.assertEqual(securite.source_de(requete), "198.51.100.7")

    def test_l_authentification_basic_de_l_api_ne_cree_aucun_poste_connu(self):
        import base64
        User.objects.create_user(username="script", password="bon-mdp-123")
        jeton = base64.b64encode(b"script:bon-mdp-123").decode()
        for _ in range(securite.POSTES_PAR_IDENTIFIANT + 3):
            reponse = Client(REMOTE_ADDR="192.0.2.8").get("/api/training/requirements/", HTTP_AUTHORIZATION=f"Basic {jeton}")
            self.assertIn(reponse.status_code, (200, 403))
        self.assertFalse(CompteurConnexion.objects.filter(identifiant="script", source__startswith="poste:").exists())
        self.assertNotIn(securite.COOKIE_POSTE, reponse.cookies)
        # Le navigateur, lui, retient son poste.
        self.assertTrue(_connecte(_poster(Client(REMOTE_ADDR="192.0.2.8"), "script", "bon-mdp-123")))
        self.assertEqual(CompteurConnexion.objects.filter(identifiant="script", source__startswith="poste:").count(), 1)
