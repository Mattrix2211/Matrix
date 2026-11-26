"""Concurrence réelle (fils d'exécution, une connexion par fil) : ouverture de demandes, codes et compteurs.

Couverture réelle : le comptage des essais est exécuté sur SQLite et sur PostgreSQL 16 ; l'ouverture simultanée de demandes et
l'utilisation concurrente d'un code ne sont exécutées que sur PostgreSQL 16 (SQLite, réservé au développement, verrouille toute
la base en écriture : ces deux scénarios n'y sont pas validés et ne doivent pas être présentés comme tels)."""
import threading

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from unittest import skipUnless

from django.test import TransactionTestCase

from accounts import reinitialisation, securite
from accounts.models import CompteurConnexion, DemandeReinitialisation, UserProfile
from org.models import Ship

User = get_user_model()
FILS = 6


def _en_parallele(travail, fils=FILS):
    erreurs, resultats = [], []

    def lancer(i):
        try:
            resultats.append(travail(i))
        except (ValidationError, PermissionDenied) as exc:
            resultats.append(exc)  # refus métier toléré : jamais une erreur serveur
        except Exception as exc:  # noqa: BLE001
            erreurs.append(exc)
        finally:
            connection.close()

    groupe = [threading.Thread(target=lancer, args=(i,)) for i in range(fils)]
    [t.start() for t in groupe]
    [t.join() for t in groupe]
    return erreurs, resultats


class ConcurrenceTests(TransactionTestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.technique = User.objects.create_user(username="technique", password="x")
        UserProfile.objects.filter(user=self.technique).update(administrateur_technique=True, ship=navire, role="EQUIPIER")
        self.marin = User.objects.create_user(username="marin", password="bon-mdp-123")
        UserProfile.objects.filter(user=self.marin).update(ship=navire, role="EQUIPIER")

    @skipUnless(connection.vendor == "postgresql", "scénario validé sur PostgreSQL seulement")
    def test_ouvertures_simultanees_pour_le_meme_compte_laissent_une_seule_demande_ouverte(self):
        technique, marin = User.objects.get(username="technique"), User.objects.get(username="marin")
        erreurs, _ = _en_parallele(lambda i: reinitialisation.initier(technique, marin))
        self.assertEqual(erreurs, [])
        self.assertEqual(DemandeReinitialisation.objects.filter(user=marin, statut__in=DemandeReinitialisation.OUVERTES).count(), 1)

    @skipUnless(connection.vendor == "postgresql", "scénario validé sur PostgreSQL seulement")
    def test_une_seule_utilisation_concurrente_du_meme_code_aboutit(self):
        technique, marin = User.objects.get(username="technique"), User.objects.get(username="marin")
        _, code = reinitialisation.initier(technique, marin)
        erreurs, resultats = _en_parallele(
            lambda i: reinitialisation.utiliser("marin", code, "", f"Nouveau-mdp-solide-{i}9", source=f"203.0.113.{i}"))
        self.assertEqual(erreurs, [])
        self.assertEqual(sum(1 for r in resultats if not isinstance(r, Exception)), 1)

    def test_essais_de_code_concurrents_sont_tous_comptes_sur_la_meme_source(self):
        technique, marin = User.objects.get(username="technique"), User.objects.get(username="marin")
        demande, _ = reinitialisation.initier(technique, marin)
        erreurs, _ = _en_parallele(
            lambda i: [securite.enregistrer_echec(f"code:{demande.pk}", "203.0.113.1", seuil=5, existe=True) for _ in range(3)], fils=4)
        self.assertEqual(erreurs, [])
        compteur = CompteurConnexion.objects.get(identifiant=f"code:{demande.pk}", source="203.0.113.1")
        self.assertEqual(compteur.essais + compteur.niveau * 5, 12)  # 4 fils x 3 essais, aucun perdu ni compté deux fois
