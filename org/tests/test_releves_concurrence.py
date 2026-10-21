"""Relèves datées : courses réelles (threads) entre applications, annulations, propositions et validations."""
import threading
import time
from datetime import timedelta
from unittest import mock, skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from matrix.core import equipage
from matrix.core.equipage import (
    annuler_releve_planifiee, appliquer_releves_echues, decider_releve, equipage_a_bord, proposer_releve,
)
from notifications.models import Notification
from org.models import PeriodeEquipage, ReleveEquipage, Ship, SynthesePassation

User = get_user_model()


def marin(nom, role, navire, equipage_code):
    utilisateur = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(
        user=utilisateur, defaults={"role": role, "ship": navire, "equipage": equipage_code}
    )
    return User.objects.get(pk=utilisateur.pk)


@skipUnless(connection.vendor == "postgresql", "Verrous de ligne : PostgreSQL requis")
class ConcurrenceReleveTests(TransactionTestCase):
    def setUp(self):
        self.navire = Ship.objects.create(
            name="Bretagne", code="BRE", double_equipage=True, equipage_a_bord="A", fuseau_horaire="Europe/Paris"
        )
        self.cdt_a = marin("cdt_a", "COMMANDANT", self.navire, "A")
        self.second_a = marin("second_a", "COMMANDANT_EN_SECOND", self.navire, "A")
        self.cdt_b = marin("cdt_b", "COMMANDANT", self.navire, "B")
        self.second_b = marin("second_b", "COMMANDANT_EN_SECOND", self.navire, "B")
        self.erreurs = []
        self.resultats = {}

    def _planifier(self, dans):
        """Relève A -> B planifiée, avec une date d'effet à `dans` de maintenant."""
        proposition, erreur = proposer_releve(self.cdt_a, self.navire, "B", timezone.now() + timedelta(hours=1))
        self.assertEqual(erreur, "")
        self.assertEqual(decider_releve(self.cdt_b, proposition, True), "")
        ReleveEquipage.objects.filter(pk=proposition.pk).update(date_effet=timezone.now() + dans)
        return proposition

    def _fil(self, nom, cible):
        def executer():
            try:
                self.resultats[nom] = cible()
            except Exception as erreur:  # pragma: no cover
                self.erreurs.append(erreur)
            finally:
                connection.close()
        return threading.Thread(target=executer)

    def _lancer(self, *fils):
        for fil in fils:
            fil.start()
        for fil in fils:
            fil.join(60)
        self.assertEqual(self.erreurs, [])

    def test_deux_executions_simultanees_appliquent_une_seule_fois(self):
        releve = self._planifier(timedelta(seconds=-5))
        en_cours = threading.Event()
        reel = equipage._appliquer

        def appliquer_lentement(*args):
            en_cours.set()
            time.sleep(1.5)
            return reel(*args)

        def premier():
            return len(appliquer_releves_echues())

        def second():
            en_cours.wait(15)
            return len(appliquer_releves_echues())

        Notification.objects.all().delete()
        with mock.patch.object(equipage, "_appliquer", appliquer_lentement):
            self._lancer(self._fil("1", premier), self._fil("2", second))
        self.assertEqual(sorted(self.resultats.values()), [0, 1])
        self.assertEqual(Ship.objects.get(pk=self.navire.pk).equipage_a_bord, "B")
        self.assertEqual(PeriodeEquipage.objects.count(), 1)
        self.assertEqual(SynthesePassation.objects.filter(releve=releve).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="releve_appliquee").count(), 1)
        self.assertEqual(Notification.objects.filter(verb__startswith="Relève appliquée").count(), 4)

    def test_acces_et_tache_simultanes_appliquent_une_seule_fois(self):
        self._planifier(timedelta(seconds=-5))
        en_cours = threading.Event()
        reel = equipage._appliquer

        def appliquer_lentement(*args):
            en_cours.set()
            time.sleep(1.5)
            return reel(*args)

        def tache():
            return len(appliquer_releves_echues())

        def acces():
            en_cours.wait(15)
            return equipage_a_bord(Ship.objects.get(pk=self.navire.pk))

        with mock.patch.object(equipage, "_appliquer", appliquer_lentement):
            self._lancer(self._fil("tache", tache), self._fil("acces", acces))
        self.assertEqual(self.resultats, {"tache": 1, "acces": "B"})
        self.assertEqual(PeriodeEquipage.objects.count(), 1)

    def test_annulation_pendant_l_application_la_releve_est_appliquee_et_non_annulable(self):
        self._planifier(timedelta(seconds=-5))
        en_cours = threading.Event()
        reel = equipage._appliquer

        def appliquer_lentement(*args):
            en_cours.set()
            time.sleep(1.5)
            return reel(*args)

        def appliquer():
            return len(appliquer_releves_echues())

        def annuler():
            en_cours.wait(15)
            releve = ReleveEquipage.objects.get()
            return annuler_releve_planifiee(self.cdt_a, releve, "Trop tard")

        with mock.patch.object(equipage, "_appliquer", appliquer_lentement):
            self._lancer(self._fil("appliquer", appliquer), self._fil("annuler", annuler))
        self.assertEqual(self.resultats["appliquer"], 1)
        self.assertIn("déjà appliquée", self.resultats["annuler"])
        self.assertEqual(ReleveEquipage.objects.get().statut, ReleveEquipage.Statut.VALIDEE)
        self.assertFalse(AuditLog.objects.filter(action="releve_planifiee_annulee").exists())

    def test_annulation_en_cours_la_date_arrive_la_releve_n_est_pas_appliquee(self):
        releve = self._planifier(timedelta(seconds=3))
        en_cours = threading.Event()
        reel = equipage.commandants_equipage
        premiere = []

        def commandants_lentement(*args):
            if threading.current_thread().name == "annuler" and not premiere:
                premiere.append(1)
                en_cours.set()
                time.sleep(5)
            return reel(*args)

        def annuler():
            return annuler_releve_planifiee(self.cdt_a, ReleveEquipage.objects.get(), "Report")

        def appliquer():
            en_cours.wait(15)
            time.sleep(3.5)  # la date d'effet est atteinte pendant que l'annulation tient le verrou
            return len(appliquer_releves_echues())

        fil_annuler = self._fil("annuler", annuler)
        fil_annuler.name = "annuler"
        with mock.patch.object(equipage, "commandants_equipage", commandants_lentement):
            self._lancer(fil_annuler, self._fil("appliquer", appliquer))
        self.assertEqual(self.resultats["annuler"], "")
        self.assertEqual(self.resultats["appliquer"], 0)
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.ANNULEE)
        self.assertEqual(Ship.objects.get(pk=self.navire.pk).equipage_a_bord, "A")
        self.assertFalse(PeriodeEquipage.objects.exists())

    def test_deux_propositions_simultanees_une_seule_releve_ouverte(self):
        en_cours = threading.Event()
        reel = equipage.commandants_equipage
        premiere = []

        def commandants_lentement(*args):
            if not premiere:
                premiere.append(1)
                en_cours.set()
                time.sleep(1.5)
            return reel(*args)

        date = timezone.now() + timedelta(hours=1)

        def par_a():
            return proposer_releve(self.cdt_a, Ship.objects.get(pk=self.navire.pk), "B", date)[1]

        def par_b():
            en_cours.wait(15)
            return proposer_releve(self.cdt_b, Ship.objects.get(pk=self.navire.pk), "B", date)[1]

        with mock.patch.object(equipage, "commandants_equipage", commandants_lentement):
            self._lancer(self._fil("a", par_a), self._fil("b", par_b))
        self.assertEqual(ReleveEquipage.objects.count(), 1)
        self.assertEqual(sorted(self.resultats.values())[0], "")
        self.assertIn("déjà", sorted(self.resultats.values())[1])

    def test_double_validation_simultanee_une_seule_application(self):
        proposition, erreur = proposer_releve(self.cdt_a, self.navire, "B", timezone.now())
        self.assertEqual(erreur, "")
        en_cours = threading.Event()
        reel = equipage._appliquer

        def appliquer_lentement(*args):
            en_cours.set()
            time.sleep(1.5)
            return reel(*args)

        def valider(auteur, attendre):
            def corps():
                if attendre:
                    en_cours.wait(15)
                return decider_releve(auteur, ReleveEquipage.objects.get(), True)
            return corps

        with mock.patch.object(equipage, "_appliquer", appliquer_lentement):
            self._lancer(
                self._fil("cdt", valider(self.cdt_b, False)), self._fil("second", valider(self.second_b, True))
            )
        self.assertEqual(sorted(self.resultats.values())[0], "")
        self.assertIn("n'est plus en attente", sorted(self.resultats.values())[1])
        self.assertEqual(PeriodeEquipage.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="releve_appliquee").count(), 1)
        self.assertEqual(SynthesePassation.objects.count(), 1)
