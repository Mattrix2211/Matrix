"""Double équipage (décision du 30/09/2026) : une feuille de service par
équipage ; personnel, validateurs à notifier et feuille du jour bornés à
l'équipage ; équipage unique inchangé ; équipage à terre en lecture seule."""
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import ServiceFunctionChoice, UserProfile
from org.models import CommandantAdjoint, Equipage, Ship
from quarts.models import (
    CreneauServiceGarde,
    FeuilleService,
    FonctionFeuilleService,
    ServiceGarde,
    peut_viser_comaeq,
    personnel_du_jour,
)
from quarts.services import feuille_service_du_jour_pour


class FeuilleServiceParEquipageTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="FREMM Feuille", code="FF", classe_navire="FREMM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.ship, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.ship, nom="Rouge")
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        self.fonction = FonctionFeuilleService.objects.create(ship=self.ship, libelle="Officier de garde", ordre=1)
        self.fonction_choice = ServiceFunctionChoice.objects.create(name="Officier de garde")
        self.jour = timezone.localdate()
        self.marin_bleu = self._marin("marin_bleu", "EQUIPIER", self.bleu)
        self.marin_rouge = self._marin("marin_rouge", "EQUIPIER", self.rouge)
        self.comaeq_bleu = self._marin("comaeq_bleu", "ETAT_MAJOR", self.bleu)
        self.comaeq_rouge = self._marin("comaeq_rouge", "ETAT_MAJOR", self.rouge)
        CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMAEQ", titulaire=self.comaeq_bleu)
        CommandantAdjoint.objects.create(ship=self.ship, equipage=self.rouge, sigle="COMAEQ", titulaire=self.comaeq_rouge)
        self.url = f"/quarts/feuille-service/{self.ship.pk}/{self.jour.isoformat()}/"

    def _marin(self, username, role, equipage):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "ship": self.ship, "equipage": equipage}
        )
        return User.objects.get(pk=user.pk)

    def _tour(self, marin):
        garde = ServiceGarde.objects.create(
            ship=self.ship, fonction=self.fonction_choice, date_debut=self.jour, date_fin=self.jour,
            statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = timezone.make_aware(datetime.combine(self.jour, datetime.min.time().replace(hour=8)))
        return CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24), marin=marin,
        )

    def test_personnel_borne_a_l_equipage(self):
        self._tour(self.marin_rouge)
        self.assertIsNone(personnel_du_jour(self.ship, self.jour, self.bleu)[0]["creneau"])
        self.assertEqual(personnel_du_jour(self.ship, self.jour, self.rouge)[0]["creneau"].marin, self.marin_rouge)

    def test_une_feuille_par_equipage_et_par_jour(self):
        FeuilleService.objects.create(ship=self.ship, equipage=self.bleu, date=self.jour)
        FeuilleService.objects.create(ship=self.ship, equipage=self.rouge, date=self.jour)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FeuilleService.objects.create(ship=self.ship, equipage=self.bleu, date=self.jour)

    def test_equipage_unique_une_seule_feuille_par_jour(self):
        unique = Ship.objects.create(name="BRF Unique", code="BRU")
        FeuilleService.objects.create(ship=unique, date=self.jour)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FeuilleService.objects.create(ship=unique, date=self.jour)

    def test_equipage_unique_creation_sans_equipage(self):
        unique = Ship.objects.create(name="BRF Unique", code="BRU")
        marin = User.objects.create_user(username="unique", password="pass")
        UserProfile.objects.update_or_create(user=marin, defaults={"role": "EQUIPIER", "ship": unique})
        self.client.force_login(marin)
        self.client.post(f"/quarts/feuille-service/{unique.pk}/{self.jour.isoformat()}/", {"action": "creer"})
        self.assertIsNone(FeuilleService.objects.get().equipage)

    def test_creation_via_la_vue_rattache_a_l_equipage_du_redacteur(self):
        self.ship.equipage_a_bord = self.rouge
        self.ship.save()
        self.client.force_login(self.marin_rouge)
        self.client.post(self.url, {"action": "creer"})
        self.assertEqual(FeuilleService.objects.get().equipage, self.rouge)

    def test_la_vue_ne_montre_jamais_la_feuille_de_l_autre_equipage(self):
        FeuilleService.objects.create(
            ship=self.ship, equipage=self.rouge, date=self.jour, statut=FeuilleService.STATUT_PUBLIEE,
        )
        self.client.force_login(self.marin_bleu)
        reponse = self.client.get(self.url)
        self.assertIsNone(reponse.context["feuille"])
        self.assertContains(reponse, "équipage Bleu")

    def test_validateurs_a_notifier_limites_a_l_equipage(self):
        feuille = FeuilleService.objects.create(
            ship=self.ship, equipage=self.bleu, date=self.jour, statut=FeuilleService.STATUT_VISA_COMAEQ,
            created_by=self.marin_bleu,
        )
        destinataires = feuille.validateurs_a_notifier()
        self.assertIn(self.comaeq_bleu, destinataires)
        self.assertNotIn(self.comaeq_rouge, destinataires)

    def test_visa_comaeq_refuse_a_l_etat_major_de_l_autre_equipage(self):
        feuille = FeuilleService.objects.create(
            ship=self.ship, equipage=self.bleu, date=self.jour, statut=FeuilleService.STATUT_VISA_COMAEQ,
        )
        self.assertTrue(peut_viser_comaeq(self.comaeq_bleu, feuille))
        self.assertFalse(peut_viser_comaeq(self.comaeq_rouge, feuille))

    def test_feuille_du_jour_publiee_propre_a_l_equipage(self):
        self._tour(self.marin_bleu)
        FeuilleService.objects.create(
            ship=self.ship, equipage=self.bleu, date=self.jour, statut=FeuilleService.STATUT_PUBLIEE,
        )
        self.assertTrue(feuille_service_du_jour_pour(self.marin_bleu, self.jour)["je_suis_de_service"])
        self.assertIsNone(feuille_service_du_jour_pour(self.marin_rouge, self.jour))

    def test_equipage_a_terre_ne_peut_pas_creer_de_feuille(self):
        self.client.force_login(self.marin_rouge)
        reponse = self.client.post(self.url, {"action": "creer"})
        self.assertEqual(reponse.status_code, 302)  # refus par le mode lecture seule
        self.assertFalse(FeuilleService.objects.exists())


from django.db import connection  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402
from django.test import TransactionTestCase  # noqa: E402


class MigrationFeuillesExistantesTests(TransactionTestCase):
    """Migration quarts 0006 : les feuilles déjà rédigées sur un bâtiment à
    double équipage sont rattachées à l'équipage à bord ; celles d'un
    bâtiment à équipage unique restent sans équipage."""

    avant = [("quarts", "0005_feuilleservice_fonctionfeuilleservice_and_more"), ("org", "0013_synthese_passation")]
    apres = [("quarts", "0006_feuille_service_par_equipage"), ("org", "0013_synthese_passation")]

    def tearDown(self):
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_feuilles_preexistantes_rattachees_a_l_equipage_a_bord(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.avant)
        anciennes = executor.loader.project_state(self.avant).apps
        Ship_ = anciennes.get_model("org", "Ship")
        Equipage_ = anciennes.get_model("org", "Equipage")
        Feuille_ = anciennes.get_model("quarts", "FeuilleService")
        double = Ship_.objects.create(name="D", code="DD", classe_navire="FREMM", double_equipage=True)
        bleu = Equipage_.objects.create(ship=double, nom="Bleu")
        double.equipage_a_bord = bleu
        double.save()
        simple = Ship_.objects.create(name="S", code="SS", classe_navire="FREMM")
        jour = timezone.localdate()
        f_double = Feuille_.objects.create(ship=double, date=jour)
        f_simple = Feuille_.objects.create(ship=simple, date=jour)

        executor = MigrationExecutor(connection)
        executor.migrate(self.apres)
        nouvelles = executor.loader.project_state(self.apres).apps
        Feuille_ = nouvelles.get_model("quarts", "FeuilleService")
        self.assertEqual(Feuille_.objects.get(pk=f_double.pk).equipage_id, bleu.pk)
        self.assertIsNone(Feuille_.objects.get(pk=f_simple.pk).equipage_id)
