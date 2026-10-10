"""Tests des modèles Quart/ServiceGarde et du rôle annexe ChefDeListe."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice, ServiceFunctionChoice, UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from quarts.models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    Quart,
    ServiceGarde,
    peut_gerer_liste,
    peut_publier_liste,
    perimetre_correspond,
    utilisateur_autorise_pour_perimetre,
)


class PerimetreUniqueTests(TestCase):
    """Un Quart, un ServiceGarde ou un ChefDeListe doit être rattaché à
    exactement un des quatre niveaux organisationnels."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Quarts", code="QRT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.fonction_quart = FonctionQuartChoice.objects.create(name="Barre")

    def test_quart_sans_aucun_perimetre_est_invalide(self):
        quart = Quart(fonction=self.fonction_quart, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        with self.assertRaises(ValidationError):
            quart.full_clean()

    def test_quart_avec_deux_niveaux_est_invalide(self):
        quart = Quart(
            fonction=self.fonction_quart, ship=self.ship, service=self.service,
            date_debut=timezone.localdate(), date_fin=timezone.localdate(),
        )
        with self.assertRaises(ValidationError):
            quart.full_clean()

    def test_quart_avec_un_seul_niveau_est_valide(self):
        quart = Quart(fonction=self.fonction_quart, service=self.service, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        quart.full_clean()  # ne doit pas lever

    def test_date_fin_avant_date_debut_est_invalide(self):
        quart = Quart(
            fonction=self.fonction_quart,
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

    def test_quart_sans_fonction_est_invalide(self):
        # Correction de cadrage du 09/09/2026 : la fonction de quart est
        # désormais obligatoire (cf. docstring de quarts/models.py).
        quart = Quart(service=self.service, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        with self.assertRaises(ValidationError):
            quart.full_clean()

    def test_service_garde_sans_fonction_est_invalide(self):
        garde = ServiceGarde(service=self.service, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        with self.assertRaises(ValidationError):
            garde.full_clean()


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

    def test_publication_journalisee_dans_l_audit(self):
        self.quart.publier(self.chef)
        self.assertTrue(AuditLog.objects.filter(actor=self.chef, action="liste_service_publiee").exists())


class VersionnageTests(TestCase):
    """Chaque publication fige une nouvelle version horodatée (cahier des
    charges §31), sans jamais réécrire les précédentes."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Versionnage", code="VER")
        self.chef = User.objects.create_user(username="chef_versionnage", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "COMMANDANT"})
        self.marin = User.objects.create_user(username="marin_versionnage", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.quart = Quart.objects.create(
            ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )
        debut = timezone.now() + timedelta(hours=2)
        self.creneau = CreneauQuart.objects.create(
            quart=self.quart, poste="Passerelle", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin,
        )

    def test_chaque_publication_cree_une_nouvelle_version(self):
        self.quart.publier(self.chef)
        self.quart.publier(self.chef)
        self.assertEqual(self.quart.versions.count(), 2)
        self.assertEqual(sorted(self.quart.versions.values_list("numero", flat=True)), [1, 2])

    def test_version_figee_conserve_l_affectation_meme_apres_correction(self):
        self.quart.publier(self.chef)
        # Correction après publication : le marin est retiré du créneau.
        self.creneau.marin = None
        self.creneau.save(update_fields=["marin"])
        self.quart.publier(self.chef)
        v1 = self.quart.versions.get(numero=1)
        v2 = self.quart.versions.get(numero=2)
        self.assertEqual(v1.creneaux_fige[0]["marin_nom"], self.marin.get_full_name() or self.marin.username)
        self.assertEqual(v2.creneaux_fige[0]["marin_nom"], "")

    def test_version_active_a_une_date_donnee(self):
        hier = timezone.localdate() - timedelta(days=1)
        self.quart.publier(self.chef)
        self.assertIsNone(self.quart.version_a_la_date(hier))
        self.assertEqual(self.quart.version_a_la_date(timezone.localdate()).numero, 1)


class WorkflowPropositionPublicationTests(TestCase):
    """Statut intermédiaire Proposée entre Brouillon et Publiée, avec un rôle
    distinct habilité à publier (cahier des charges §34)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Workflow", code="WKF")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre"
        )
        self.chef_de_liste = User.objects.create_user(username="chef_liste_workflow", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_de_liste, defaults={"role": "EQUIPIER", "sector": self.sector}
        )
        # Recharge : la relation .profile mise en cache par le signal de
        # création (accounts/models.py::create_user_profile, rôle EQUIPIER
        # par défaut) reste sinon périmée après update_or_create ci-dessus.
        self.chef_de_liste.refresh_from_db()
        ChefDeListe.objects.create(user=self.chef_de_liste, sector=self.sector)

        self.publicateur = User.objects.create_user(username="publicateur_workflow", password="pass")
        UserProfile.objects.update_or_create(
            user=self.publicateur, defaults={"role": "CHEF_SERVICE", "sector": self.sector}
        )
        self.publicateur.refresh_from_db()

        self.quart = Quart.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )

    def test_chef_de_liste_seul_ne_peut_pas_publier(self):
        self.assertFalse(peut_publier_liste(self.chef_de_liste, self.quart))

    def test_publicateur_habilite_peut_publier(self):
        self.assertTrue(peut_publier_liste(self.publicateur, self.quart))

    def test_proposer_passe_le_statut_a_proposee_et_journalise(self):
        self.quart.proposer(self.chef_de_liste)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_PROPOSEE)
        self.assertEqual(self.quart.proposee_par, self.chef_de_liste)
        self.assertIsNotNone(self.quart.proposee_le)
        self.assertTrue(AuditLog.objects.filter(actor=self.chef_de_liste, action="liste_service_proposee").exists())

    def test_proposer_notifie_le_publicateur_habilite(self):
        self.quart.proposer(self.chef_de_liste)
        self.assertTrue(
            Notification.objects.filter(user=self.publicateur, verb__icontains="à valider").exists()
        )
        # Le chef de liste, qui n'est pas habilité à publier, n'est pas
        # notifié lui-même (il est déjà à l'origine de la proposition).
        self.assertFalse(Notification.objects.filter(user=self.chef_de_liste).exists())


class CreneauValidationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Créneau", code="CRN")
        self.quart = Quart.objects.create(ship=self.ship, date_debut=timezone.localdate(), date_fin=timezone.localdate())

    def test_fin_avant_debut_est_invalide(self):
        debut = timezone.now()
        creneau = CreneauQuart(quart=self.quart, poste="Barre", debut=debut, fin=debut - timedelta(hours=1))
        with self.assertRaises(ValidationError):
            creneau.full_clean()
