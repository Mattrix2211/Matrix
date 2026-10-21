"""Relèves datées du double équipage : date d'effet, planification, application, annulation, périodes, fuseau."""
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from matrix.core.equipage import (
    annuler_releve_planifiee, appliquer_releves_echues, changer_fuseau, decider_releve, equipage_a_bord,
    equipage_a_bord_le, proposer_releve, releve_planifiee, valider_releve_secours,
)
from matrix.core.fuseau import champ_local, libelle_fuseau, local_vers_utc, lire_champ_local
from matrix.core.role_thresholds import invalidate_cache
from notifications.models import Notification
from org.models import PeriodeEquipage, ReleveEquipage, RoleThresholdConfig, Ship, SynthesePassation

User = get_user_model()
UTC = dt_timezone.utc


def marin(nom, role, navire, equipage=""):
    utilisateur = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role, "ship": navire, "equipage": equipage})
    return User.objects.get(pk=utilisateur.pk)


def a_l_instant(instant):
    return mock.patch("django.utils.timezone.now", return_value=instant)


class Base(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(
            name="Bretagne", code="BRE", double_equipage=True, equipage_a_bord="A", fuseau_horaire="Europe/Paris"
        )
        self.cdt_a = marin("cdt_a", "COMMANDANT", self.navire, "A")
        self.second_a = marin("second_a", "COMMANDANT_EN_SECOND", self.navire, "A")
        self.cdt_b = marin("cdt_b", "COMMANDANT", self.navire, "B")
        self.second_b = marin("second_b", "COMMANDANT_EN_SECOND", self.navire, "B")
        self.equipier_a = marin("equipier_a", "EQUIPIER", self.navire, "A")
        self.equipier_b = marin("equipier_b", "EQUIPIER", self.navire, "B")
        self.admin_navire = marin("admin_navire", "ADMIN_NAVIRE", self.navire)
        self.master = marin("master", "MASTER_ADMIN", None)
        self.maintenant = timezone.now().replace(microsecond=0)

    def recharger(self):
        self.navire.refresh_from_db()
        return self.navire

    def proposer(self, dans=timedelta(hours=2), auteur=None, equipage="B"):
        proposition, erreur = proposer_releve(auteur or self.cdt_a, self.navire, equipage, self.maintenant + dans)
        self.assertEqual(erreur, "")
        return proposition

    def planifier(self, dans=timedelta(hours=2)):
        """Relève A -> B proposée par le commandant A, validée par le commandant B, à la date d'effet donnée."""
        proposition = self.proposer(dans)
        self.assertEqual(decider_releve(self.cdt_b, proposition, True), "")
        proposition.refresh_from_db()
        return proposition


class FuseauTests(Base):
    def test_fuseau_herite_distingue_d_un_choix_du_bord(self):
        herite = Ship.objects.create(name="Normandie", code="NOR")
        self.assertEqual(libelle_fuseau(herite), "Fuseau par défaut hérité : Europe/Paris")
        self.assertEqual(libelle_fuseau(self.navire), "Fuseau du bâtiment : Europe/Paris")

    def test_saisie_convertie_en_utc_selon_le_fuseau_du_batiment(self):
        naif = datetime(2026, 7, 1, 12, 0)
        self.assertEqual(local_vers_utc(self.navire, naif)[0], datetime(2026, 7, 1, 10, 0, tzinfo=UTC))
        noumea = Ship.objects.create(name="Noumea", code="NOU", fuseau_horaire="Pacific/Noumea")
        self.assertEqual(local_vers_utc(noumea, naif)[0], datetime(2026, 7, 1, 1, 0, tzinfo=UTC))

    def test_heure_ambigue_ou_inexistante_refusee(self):
        utc, erreur = local_vers_utc(self.navire, datetime(2026, 10, 25, 2, 30))
        self.assertIsNone(utc)
        self.assertIn("ambiguë", erreur)
        utc, erreur = local_vers_utc(self.navire, datetime(2026, 3, 29, 2, 30))
        self.assertIsNone(utc)
        self.assertIn("n'existe pas", erreur)

    def test_champ_illisible_refuse(self):
        self.assertIn("Indiquez", lire_champ_local(self.navire, "demain")[1])
        self.assertEqual(lire_champ_local(self.navire, "2026-07-01T12:00")[1], "")

    def test_changer_de_fuseau_ne_recalcule_pas_les_instants_enregistres(self):
        releve = self.planifier()
        avant = releve.date_effet
        self.assertEqual(changer_fuseau(self.admin_navire, self.navire, "Pacific/Noumea"), "")
        releve.refresh_from_db()
        self.assertEqual(releve.date_effet, avant)
        self.assertEqual(self.recharger().fuseau_horaire, "Pacific/Noumea")
        self.assertEqual(champ_local(self.navire, avant), (avant + timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M"))
        audit = AuditLog.objects.get(action="fuseau_horaire_modifie")
        self.assertIn("instants deja enregistres inchanges", audit.details)

    def test_droits_et_validation_du_changement_de_fuseau(self):
        for auteur in (self.cdt_a, self.equipier_a):
            self.assertIn("réservé", changer_fuseau(auteur, self.navire, "Pacific/Noumea"))
        self.assertIn("inconnu", changer_fuseau(self.admin_navire, self.navire, "Mars/Olympus"))
        self.assertIn("inconnu", changer_fuseau(self.admin_navire, self.navire, ""))
        self.assertEqual(changer_fuseau(self.master, self.navire, "Pacific/Noumea"), "")
        autre = Ship.objects.create(name="Autre", code="AUT")
        self.assertIn("réservé", changer_fuseau(self.admin_navire, autre, "Pacific/Noumea"))
        self.assertEqual(Ship.objects.get(pk=autre.pk).fuseau_horaire, "")

    def test_le_seuil_unite_administration_reste_configurable_par_batiment(self):
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"unite_administration": "COMMANDANT"})
        invalidate_cache(self.navire.pk)
        self.addCleanup(invalidate_cache, self.navire.pk)
        self.assertEqual(changer_fuseau(self.cdt_a, self.navire, "Pacific/Noumea"), "")
        self.assertIn("réservé", changer_fuseau(self.equipier_a, self.navire, "Europe/Paris"))

    def test_un_fuseau_inconnu_ne_passe_pas_la_validation_du_modele(self):
        self.navire.fuseau_horaire = "Mars/Olympus"
        with self.assertRaises(ValidationError):
            self.navire.full_clean()


class ProposerTests(Base):
    def test_date_d_effet_obligatoire(self):
        proposition, erreur = proposer_releve(self.cdt_a, self.navire, "B", None)
        self.assertIsNone(proposition)
        self.assertIn("date et l'heure", erreur)

    def test_date_passee_refusee_mais_la_minute_courante_est_permise(self):
        proposition, erreur = proposer_releve(self.cdt_a, self.navire, "B", timezone.now() - timedelta(minutes=2))
        self.assertIsNone(proposition)
        self.assertIn("passé", erreur)
        self.assertFalse(ReleveEquipage.objects.exists())
        proposition, erreur = proposer_releve(self.cdt_a, self.navire, "B", timezone.now())
        self.assertEqual(erreur, "")

    def test_date_future_stockee_et_proposee(self):
        proposition = self.proposer(timedelta(days=3))
        self.assertEqual(proposition.statut, ReleveEquipage.Statut.EN_ATTENTE)
        self.assertEqual(proposition.date_effet, self.maintenant + timedelta(days=3))
        self.assertIsNone(proposition.decide_le)
        self.assertEqual(self.recharger().equipage_a_bord, "A")
        notification = Notification.objects.get(user=self.cdt_b)
        self.assertIn("à compter du", notification.verb)

    def test_une_seule_releve_ouverte_en_attente_ou_planifiee(self):
        self.proposer()
        _, erreur = proposer_releve(self.cdt_a, self.navire, "B", self.maintenant + timedelta(days=1))
        self.assertIn("déjà en attente", erreur)

    def test_une_releve_planifiee_bloque_une_nouvelle_proposition(self):
        self.planifier()
        _, erreur = proposer_releve(self.cdt_b, self.navire, "B", self.maintenant + timedelta(days=1))
        self.assertIn("déjà", erreur)
        _, erreur = proposer_releve(self.cdt_a, self.navire, "B", self.maintenant + timedelta(days=1))
        self.assertIn("déjà planifiée", erreur)
        self.assertEqual(ReleveEquipage.objects.count(), 1)

    def test_seul_un_commandant_propose(self):
        _, erreur = proposer_releve(self.equipier_a, self.navire, "B", self.maintenant + timedelta(hours=1))
        self.assertIn("Seul un commandant", erreur)


class ValidationTests(Base):
    def test_validation_avant_la_date_planifie_sans_modifier_l_equipage(self):
        releve = self.planifier()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.PLANIFIEE)
        self.assertIsNotNone(releve.decide_le)
        self.assertIsNone(releve.appliquee_le)
        self.assertEqual(self.recharger().equipage_a_bord, "A")
        self.assertFalse(PeriodeEquipage.objects.exists())
        self.assertFalse(SynthesePassation.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action__in=("changement_equipage", "releve_appliquee")).exists())
        self.assertEqual(releve_planifiee(self.navire).pk, releve.pk)
        notification = Notification.objects.get(user=self.cdt_a)
        self.assertIn("sera à bord", notification.verb)

    def test_date_atteinte_entre_la_proposition_et_la_validation_applique_tout_de_suite(self):
        proposition = self.proposer(timedelta(minutes=5))
        with a_l_instant(self.maintenant + timedelta(minutes=10)):
            self.assertEqual(decider_releve(self.cdt_b, proposition, True), "")
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, ReleveEquipage.Statut.VALIDEE)
        self.assertEqual(self.recharger().equipage_a_bord, "B")
        self.assertEqual(proposition.appliquee_le, self.maintenant + timedelta(minutes=10))
        periode = PeriodeEquipage.objects.get()
        self.assertEqual((periode.equipage, periode.debut, periode.fin), ("B", self.maintenant + timedelta(minutes=5), None))
        self.assertTrue(SynthesePassation.objects.filter(releve=proposition).exists())

    def test_refus_inchange(self):
        proposition = self.proposer()
        self.assertEqual(decider_releve(self.cdt_b, proposition, False), "")
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, ReleveEquipage.Statut.REFUSEE)
        self.assertEqual(self.recharger().equipage_a_bord, "A")

    def test_validation_de_secours_future_planifie_et_previent_les_deux_equipages(self):
        proposition = self.proposer()
        UserProfile.objects.filter(user__in=(self.cdt_b, self.second_b)).update(equipage="")
        self.assertEqual(valider_releve_secours(self.master, proposition, "Plus de commandant"), "")
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, ReleveEquipage.Statut.PLANIFIEE)
        self.assertEqual(self.recharger().equipage_a_bord, "A")
        verbes = set(Notification.objects.filter(user__in=(self.equipier_a, self.equipier_b)).values_list("verb", flat=True))
        self.assertEqual(len(verbes), 1)
        self.assertIn("sera à bord", verbes.pop())


class ApplicationTests(Base):
    def test_rien_avant_la_date_puis_application_unique(self):
        releve = self.planifier()
        with a_l_instant(releve.date_effet - timedelta(minutes=1)):
            self.assertEqual(appliquer_releves_echues(), [])
            self.assertEqual(equipage_a_bord(self.navire), "A")
        with a_l_instant(releve.date_effet + timedelta(seconds=30)):
            self.assertEqual([r.pk for r in appliquer_releves_echues()], [releve.pk])
            self.assertEqual(appliquer_releves_echues(), [])
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.VALIDEE)
        self.assertEqual(self.recharger().equipage_a_bord, "B")
        self.assertEqual(PeriodeEquipage.objects.count(), 1)
        self.assertEqual(SynthesePassation.objects.filter(releve=releve).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="releve_appliquee").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="changement_equipage").count(), 1)

    def test_l_accesseur_applique_la_releve_echue_sans_la_tache(self):
        releve = self.planifier()
        navire_en_memoire = Ship.objects.get(pk=self.navire.pk)
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            self.assertEqual(equipage_a_bord(navire_en_memoire), "B")
        self.assertEqual(navire_en_memoire.equipage_a_bord, "B")
        self.assertEqual(self.recharger().equipage_a_bord, "B")

    def test_trois_dates_distinctes_et_aucun_antidatage_en_cas_de_rattrapage(self):
        releve = self.planifier()
        # Tâche indisponible : l'application technique se fait longtemps après la date d'effet.
        ReleveEquipage.objects.filter(pk=releve.pk).update(date_effet=self.maintenant - timedelta(days=3))
        Notification.objects.all().delete()
        appliquer_releves_echues()
        releve.refresh_from_db()
        reel = timezone.now()
        self.assertEqual(releve.date_effet, self.maintenant - timedelta(days=3))
        self.assertGreater(releve.appliquee_le, reel - timedelta(minutes=5))
        periode = PeriodeEquipage.objects.get()
        self.assertEqual(periode.debut, releve.date_effet)
        notifications = Notification.objects.all()
        self.assertTrue(notifications.exists())
        for notification in notifications:
            self.assertGreater(notification.created_at, reel - timedelta(minutes=5))
        for audit in AuditLog.objects.filter(action__in=("releve_appliquee", "changement_equipage")):
            self.assertGreater(audit.created_at, reel - timedelta(minutes=5))
        self.assertGreater(SynthesePassation.objects.get(releve=releve).created_at, reel - timedelta(minutes=5))

    def test_notifications_a_l_application_reelle(self):
        releve = self.planifier()
        Notification.objects.all().delete()
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            appliquer_releves_echues()
        destinataires = set(Notification.objects.filter(verb__startswith="Relève appliquée").values_list("user__username", flat=True))
        self.assertEqual(destinataires, {"cdt_a", "second_a", "cdt_b", "second_b"})

    def test_seul_le_batiment_demande_est_traite(self):
        releve = self.planifier()
        autre = Ship.objects.create(name="Normandie", code="NOR", double_equipage=True, equipage_a_bord="A")
        cdt_a2, cdt_b2 = marin("n_cdt_a", "COMMANDANT", autre, "A"), marin("n_cdt_b", "COMMANDANT", autre, "B")
        proposition, _ = proposer_releve(cdt_a2, autre, "B", self.maintenant + timedelta(hours=1))
        decider_releve(cdt_b2, proposition, True)
        with a_l_instant(self.maintenant + timedelta(days=1)):
            appliquer_releves_echues(autre)
        self.assertEqual(Ship.objects.get(pk=autre.pk).equipage_a_bord, "B")
        self.assertEqual(self.recharger().equipage_a_bord, "A")
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.PLANIFIEE)

    def test_deux_relèves_successives_enchainent_les_periodes(self):
        premiere = self.planifier(timedelta(hours=1))
        with a_l_instant(premiere.date_effet + timedelta(minutes=1)):
            appliquer_releves_echues()
            suivante, erreur = proposer_releve(self.cdt_b, self.navire, "A", premiere.date_effet + timedelta(days=1))
            self.assertEqual(erreur, "")
            self.assertEqual(decider_releve(self.cdt_a, suivante, True), "")
        with a_l_instant(suivante.date_effet + timedelta(minutes=1)):
            appliquer_releves_echues()
        self.assertEqual(self.recharger().equipage_a_bord, "A")
        premiere_periode, seconde = PeriodeEquipage.objects.order_by("debut")
        self.assertEqual((premiere_periode.equipage, premiere_periode.fin), ("B", seconde.debut))
        self.assertEqual((seconde.equipage, seconde.fin), ("A", None))


class EquipageALInstantTests(Base):
    def test_passe_inconnu_jamais_reconstitue(self):
        hier = self.maintenant - timedelta(days=1)
        self.assertIsNone(equipage_a_bord_le(self.navire, hier))
        self.assertEqual(equipage_a_bord_le(self.navire, timezone.now()), "A")

    def test_periodes_planification_et_futur(self):
        releve = self.planifier(timedelta(hours=2))
        effet = releve.date_effet
        self.assertEqual(equipage_a_bord_le(self.navire, effet - timedelta(minutes=1)), "A")
        self.assertEqual(equipage_a_bord_le(self.navire, effet), "B")
        self.assertEqual(equipage_a_bord_le(self.navire, effet + timedelta(days=30)), "B")
        with a_l_instant(effet + timedelta(hours=1)):
            appliquer_releves_echues()
            self.assertEqual(equipage_a_bord_le(self.navire, effet + timedelta(minutes=10)), "B")
            self.assertEqual(equipage_a_bord_le(self.navire, effet), "B")
            # Avant la première période enregistrée : inconnu, même si A était probablement à bord.
            self.assertIsNone(equipage_a_bord_le(self.navire, effet - timedelta(minutes=1)))


class AnnulationTests(Base):
    def test_annulation_par_le_second_d_un_des_deux_equipages_avec_notification_immediate(self):
        releve = self.planifier()
        Notification.objects.all().delete()
        self.assertEqual(annuler_releve_planifiee(self.second_b, releve, "Reportée de 24 h"), "")
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.ANNULEE)
        self.assertEqual((releve.annulee_par, releve.motif_annulation), (self.second_b, "Reportée de 24 h"))
        self.assertIsNotNone(releve.annulee_le)
        self.assertEqual(self.recharger().equipage_a_bord, "A")
        self.assertEqual(
            set(Notification.objects.values_list("user__username", flat=True)), {"cdt_a", "second_a"}
        )
        self.assertIn("Reportée de 24 h", Notification.objects.first().verb)
        audit = AuditLog.objects.get(action="releve_planifiee_annulee")
        self.assertEqual(audit.actor, self.second_b)
        self.assertIn("Reportée de 24 h", audit.details)

    def test_l_equipage_a_bord_peut_annuler_et_l_autre_commandement_est_prevenu(self):
        releve = self.planifier()
        Notification.objects.all().delete()
        self.assertEqual(annuler_releve_planifiee(self.cdt_a, releve, "Panne"), "")
        self.assertEqual(set(Notification.objects.values_list("user__username", flat=True)), {"cdt_b", "second_b"})

    def test_report_par_annulation_puis_nouvelle_proposition(self):
        releve = self.planifier()
        annuler_releve_planifiee(self.cdt_a, releve, "Report")
        nouvelle = self.proposer(timedelta(days=2))
        self.assertEqual(nouvelle.statut, ReleveEquipage.Statut.EN_ATTENTE)
        self.assertEqual(ReleveEquipage.objects.count(), 2)

    def test_justification_obligatoire_et_droits(self):
        releve = self.planifier()
        self.assertIn("justification", annuler_releve_planifiee(self.cdt_a, releve, "  "))
        for intrus in (self.equipier_a, self.admin_navire, self.master):
            self.assertIn("Seul", annuler_releve_planifiee(intrus, releve, "Motif"), intrus.username)
        autre = Ship.objects.create(name="Autre", code="AUT", double_equipage=True, equipage_a_bord="A")
        etranger = marin("cdt_etranger", "COMMANDANT", autre, "A")
        self.assertIn("Seul", annuler_releve_planifiee(etranger, releve, "Motif"))
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.PLANIFIEE)
        self.assertFalse(AuditLog.objects.filter(action="releve_planifiee_annulee").exists())

    def test_une_releve_deja_appliquee_ne_s_annule_pas(self):
        releve = self.planifier()
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            self.assertIn("déjà appliquée", annuler_releve_planifiee(self.cdt_a, releve, "Trop tard"))
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.VALIDEE)
        self.assertEqual(self.recharger().equipage_a_bord, "B")

    def test_une_proposition_en_attente_n_est_pas_une_releve_planifiee(self):
        proposition = self.proposer()
        self.assertIn("pas planifiée", annuler_releve_planifiee(self.cdt_b, proposition, "Motif"))


class MigrationReleveTests(TransactionTestCase):
    """Migration additive : les relèves déjà validées sont considérées comme appliquées, sans période reconstituée."""

    avant = [("org", "0013_parametres_passation")]
    apres = [("org", "0014_releve_date_effet_periodes")]

    def tearDown(self):
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_migration_des_releves_existantes_puis_retour_arriere(self):
        executeur = MigrationExecutor(connection)
        executeur.migrate(self.avant)
        apps = executeur.loader.project_state(self.avant).apps
        navire = apps.get_model("org", "Ship").objects.create(name="Migr", code="MIG", double_equipage=True, equipage_a_bord="B")
        Releve = apps.get_model("org", "ReleveEquipage")
        decide = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        validee = Releve.objects.create(ship=navire, equipage_propose="B", statut="validee", decide_le=decide)
        attente = Releve.objects.create(ship=navire, equipage_propose="A", statut="en_attente")

        executeur = MigrationExecutor(connection)
        executeur.migrate(self.apres)
        apps = executeur.loader.project_state(self.apres).apps
        Releve = apps.get_model("org", "ReleveEquipage")
        validee, attente = Releve.objects.get(pk=validee.pk), Releve.objects.get(pk=attente.pk)
        self.assertEqual((validee.date_effet, validee.appliquee_le), (decide, decide))
        self.assertEqual((attente.date_effet, attente.appliquee_le), (None, None))
        self.assertEqual(apps.get_model("org", "PeriodeEquipage").objects.count(), 0)
        self.assertEqual(apps.get_model("org", "Ship").objects.get(pk=navire.pk).fuseau_horaire, "")

        executeur = MigrationExecutor(connection)
        executeur.migrate(self.avant)
        apps = executeur.loader.project_state(self.avant).apps
        self.assertEqual(apps.get_model("org", "ReleveEquipage").objects.count(), 2)


class DecisionSansDateTests(Base):
    """Une proposition antérieure à la migration (sans date d'effet) s'applique à sa validation."""

    def test_proposition_sans_date_d_effet_appliquee_a_la_validation(self):
        ancienne = ReleveEquipage.objects.create(ship=self.navire, equipage_propose="B", propose_par=self.cdt_a)
        self.assertEqual(decider_releve(self.cdt_b, ancienne, True), "")
        ancienne.refresh_from_db()
        self.assertEqual(ancienne.statut, ReleveEquipage.Statut.VALIDEE)
        self.assertEqual(ancienne.date_effet, ancienne.appliquee_le)
        self.assertEqual(self.recharger().equipage_a_bord, "B")
        self.assertEqual(PeriodeEquipage.objects.get().debut, ancienne.date_effet)

