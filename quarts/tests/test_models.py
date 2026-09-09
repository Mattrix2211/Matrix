"""Tests des modèles Quart/ServiceGarde et du rôle annexe ChefDeListe."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from quarts.models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    Quart,
    ServiceGarde,
    peut_gerer_liste,
    perimetre_correspond,
    utilisateur_autorise_pour_perimetre,
)


class PerimetreUniqueTests(TestCase):
    """Un Quart, un ServiceGarde ou un ChefDeListe doit être rattaché à
    exactement un des quatre niveaux organisationnels."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Quarts", code="QRT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")

    def test_quart_sans_aucun_perimetre_est_invalide(self):
        quart = Quart(date_debut=timezone.localdate(), date_fin=timezone.localdate())
        with self.assertRaises(ValidationError):
            quart.full_clean()

    def test_quart_avec_deux_niveaux_est_invalide(self):
        quart = Quart(ship=self.ship, service=self.service, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        with self.assertRaises(ValidationError):
            quart.full_clean()

    def test_quart_avec_un_seul_niveau_est_valide(self):
        quart = Quart(service=self.service, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        quart.full_clean()  # ne doit pas lever

    def test_date_fin_avant_date_debut_est_invalide(self):
        quart = Quart(
            service=self.service,
            date_debut=timezone.localdate(),
            date_fin=timezone.localdate() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            quart.full_clean()

    def test_chef_de_liste_sans_perimetre_est_invalide(self):
        user = User.objects.create_user(username="marin_cdl", password="pass")
        cdl = ChefDeListe(user=user)
        with self.assertRaises(ValidationError):
            cdl.full_clean()


class ModelesDistinctsTests(TestCase):
    """Vérifie que Quart et ServiceGarde sont bien deux modèles concrets
    distincts, chacun avec sa propre table et son propre modèle de créneau
    (cadrage du 09/09/2026 : PAS un modèle générique unique avec champ type)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Distinct", code="DST")

    def test_quart_et_service_garde_sont_deux_tables_separees(self):
        self.assertNotEqual(Quart._meta.db_table, ServiceGarde._meta.db_table)

    def test_creneau_quart_et_creneau_service_garde_sont_distincts(self):
        self.assertNotEqual(CreneauQuart._meta.db_table, CreneauServiceGarde._meta.db_table)

    def test_duree_par_defaut_differente_et_configurable(self):
        quart = Quart.objects.create(ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        garde = ServiceGarde.objects.create(ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        # Valeurs par défaut distinctes (4h / 24h), mais restent de simples
        # champs éditables — aucune règle de code n'impose ces nombres.
        self.assertEqual(quart.duree_creneau_heures, 4)
        self.assertEqual(garde.duree_creneau_heures, 24)
        quart.duree_creneau_heures = 6
        quart.save()
        self.assertEqual(Quart.objects.get(pk=quart.pk).duree_creneau_heures, 6)


class AutorisationPerimetreTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Autorisation", code="AUT")
        self.autre_ship = Ship.objects.create(name="Autre navire autorisation", code="AAUT")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Machine"), name="Propulsion"
        )

        self.equipier = User.objects.create_user(username="equipier_quarts", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

        self.chef_de_liste = User.objects.create_user(username="cdl_secteur", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_de_liste, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.chef_de_liste, sector=self.sector)

        self.commandant = User.objects.create_user(username="commandant_quarts", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})
        # Le signal de création automatique du profil (accounts/models.py) met en
        # cache un profil EQUIPIER par défaut sur l'instance créée dans ce même
        # process ; on recharge depuis la base pour repartir d'un profil non
        # caché, comme le ferait une requête HTTP réelle (même précaution que
        # training/tests/test_referents.py).
        self.commandant = User.objects.get(pk=self.commandant.pk)

    def test_chef_de_liste_autorise_sur_son_perimetre_exact(self):
        self.assertTrue(utilisateur_autorise_pour_perimetre(self.chef_de_liste, sector=self.sector))

    def test_chef_de_liste_non_autorise_sur_un_autre_perimetre(self):
        self.assertFalse(utilisateur_autorise_pour_perimetre(self.chef_de_liste, ship=self.ship))
        self.assertFalse(utilisateur_autorise_pour_perimetre(self.chef_de_liste, ship=self.autre_ship))

    def test_equipier_non_designe_nest_jamais_autorise(self):
        self.assertFalse(utilisateur_autorise_pour_perimetre(self.equipier, sector=self.sector))

    def test_commandant_passe_outre_sans_designation(self):
        self.assertTrue(utilisateur_autorise_pour_perimetre(self.commandant, ship=self.autre_ship))

    def test_peut_gerer_liste_reutilise_la_meme_regle(self):
        quart = Quart.objects.create(sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        self.assertTrue(peut_gerer_liste(self.chef_de_liste, quart))
        self.assertFalse(peut_gerer_liste(self.equipier, quart))
        self.assertTrue(peut_gerer_liste(self.commandant, quart))

    def test_perimetre_correspond_est_strict(self):
        quart_meme_secteur = Quart.objects.create(sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        cdl = ChefDeListe.objects.get(user=self.chef_de_liste)
        self.assertTrue(perimetre_correspond(cdl, quart_meme_secteur))
        quart_ship = Quart.objects.create(ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        self.assertFalse(perimetre_correspond(cdl, quart_ship))


class PublicationTests(TestCase):
    """La publication d'une liste notifie chaque marin affecté, une seule
    fois (pas de nouvelle notification si la liste est republiée après une
    correction)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Publication", code="PUB")
        self.chef = User.objects.create_user(username="chef_publication", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "COMMANDANT"})
        self.marin = User.objects.create_user(username="marin_publication", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.quart = Quart.objects.create(
            ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )
        debut = timezone.now() + timedelta(hours=2)
        CreneauQuart.objects.create(quart=self.quart, poste="Passerelle", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        CreneauQuart.objects.create(quart=self.quart, poste="Machine", debut=debut, fin=debut + timedelta(hours=4))  # non affecté

    def test_publication_passe_le_statut_a_publiee(self):
        self.quart.publier(self.chef)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_PUBLIEE)
        self.assertEqual(self.quart.publiee_par, self.chef)
        self.assertIsNotNone(self.quart.publiee_le)

    def test_publication_notifie_uniquement_les_marins_affectes(self):
        self.quart.publier(self.chef)
        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)
        self.assertFalse(Notification.objects.exclude(user=self.marin).exists())

    def test_republier_ne_renvoie_pas_de_nouvelle_notification(self):
        self.quart.publier(self.chef)
        self.quart.publier(self.chef)
        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)

    def test_service_garde_utilise_le_meme_mecanisme_de_publication(self):
        garde = ServiceGarde.objects.create(
            ship=self.ship, type_service="Garde 24h",
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=1),
        )
        debut = timezone.now() + timedelta(hours=2)
        CreneauServiceGarde.objects.create(service_garde=garde, poste="Garde 24h", debut=debut, fin=debut + timedelta(hours=24), marin=self.marin)
        garde.publier(self.chef)
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__icontains="service de garde").exists())


class CreneauValidationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Créneau", code="CRN")
        self.quart = Quart.objects.create(ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate())

    def test_fin_avant_debut_est_invalide(self):
        debut = timezone.now()
        creneau = CreneauQuart(quart=self.quart, poste="Barre", debut=debut, fin=debut - timedelta(hours=1))
        with self.assertRaises(ValidationError):
            creneau.full_clean()
