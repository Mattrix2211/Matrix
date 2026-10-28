"""Double soumission des étapes du circuit de visa et reprise périodique des signalements de rectificatif."""
import threading
import time
from unittest import mock, skipUnless

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from accounts.models import AuditLog
from matrix.celery import app as celery_app
from notifications.models import Notification
from quarts.models import FeuilleService, TransitionDejaEffectuee
from quarts.rectificatif import signaler_divergence
from quarts.tasks import signaler_divergences_feuilles
from quarts.tests.test_feuille_service import FeuilleServiceTestsBase, _utilisateur, jeton_visa_affiche


def _compte():
    return Notification.objects.count(), AuditLog.objects.count()


class DoubleSoumissionTests(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self._publier_tour(marin=self.marin_service)
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        self.url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.jour:%Y-%m-%d}"])

    def _copie(self):
        return FeuilleService.objects.get(pk=self.feuille.pk)

    def _rejoue(self, etape, *args):
        """La seconde soumission détient une copie périmée de la feuille, lue avant la première."""
        perimee = self._copie()
        getattr(self._copie(), etape)(*args)
        avant = _compte()
        with self.assertRaises(TransitionDejaEffectuee):
            getattr(perimee, etape)(*args)
        self.assertEqual(_compte(), avant)

    def test_proposer_deux_fois(self):
        self._rejoue("proposer", self.equipier)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_proposee").count(), 1)

    def test_viser_secteur_deux_fois(self):
        self.feuille.proposer(self.equipier)
        self._rejoue("viser_secteur", self.chef_secteur)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_visa_secteur").count(), 1)

    def test_viser_service_deux_fois(self):
        self.feuille.proposer(self.chef_secteur)
        self._rejoue("viser_service", self.chef_service)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_visa_service").count(), 1)

    def test_renvoyer_deux_fois(self):
        self.feuille.proposer(self.chef_secteur)
        self._rejoue("renvoyer", self.chef_service, "Motif")
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_renvoyee").count(), 1)

    def test_viser_comaeq_deux_fois_une_seule_version(self):
        self.feuille.proposer(self.chef_secteur)
        self.feuille.viser_service(self.chef_service)
        perimee = self._copie()
        self.assertTrue(self._copie().viser_comaeq(self.etat_major))
        avant = _compte()
        with self.assertRaises(TransitionDejaEffectuee):
            perimee.viser_comaeq(self.etat_major)
        self.assertEqual(_compte(), avant)
        self.assertEqual(self.feuille.versions.count(), 1)

    def _vue_apres_course(self, action, preparation, etape_concurrente):
        """La première soumission passe l'étape pendant que la seconde est dans la vue."""
        preparation()
        self.client.force_login(User.objects.get(username="etat_major" if action == "viser_comaeq" else "chef_service"))
        donnees = {"action": action, "motif": "x"}
        if action == "viser_comaeq":
            donnees["jeton_visa"] = jeton_visa_affiche(self.client, self.url)

        reel = getattr(FeuilleService, action)

        def concurrente(*args, **kwargs):
            etape_concurrente(reel)
            raise TransitionDejaEffectuee("déjà fait")

        with mock.patch.object(FeuilleService, action, side_effect=concurrente):
            reponse = self.client.post(self.url, donnees)
        return reponse, [str(m) for m in get_messages(reponse.wsgi_request)]

    def test_vue_viser_comaeq_deja_publiee_affiche_un_message_non_alarmant(self):
        def preparer():
            self.feuille.proposer(self.chef_secteur)
            self.feuille.viser_service(self.chef_service)

        reponse, messages_ = self._vue_apres_course(
            "viser_comaeq", preparer, lambda reel: reel(self._copie(), self.etat_major)
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(messages_, ["Cette feuille est déjà publiée."])
        self.assertEqual(self.feuille.versions.count(), 1)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_vue_autre_etape_deja_faite_redirige_sans_erreur(self):
        reponse, messages_ = self._vue_apres_course(
            "renvoyer", lambda: self.feuille.proposer(self.chef_secteur),
            lambda reel: reel(self._copie(), self.chef_service, "Motif"),
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(messages_, ["Cette étape a déjà été effectuée : la feuille est à jour ci-dessous."])


@skipUnless(connection.vendor == "postgresql", "Verrous de ligne : PostgreSQL requis")
class DoubleSoumissionConcurrenteTests(TransactionTestCase):
    """Deux soumissions réellement simultanées (threads) de la même étape."""

    def setUp(self):
        FeuilleServiceTestsBase.setUp(self)
        FeuilleServiceTestsBase._publier_tour(self, marin=self.marin_service)
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )

    def _course(self, etape, *args):
        barriere, resultats = threading.Barrier(2), []
        reel = FeuilleService._notifier_prochain_visa

        def lent(feuille):
            reel(feuille)
            time.sleep(1)  # garde le verrou le temps que la seconde soumission l'attende

        def soumettre():
            try:
                barriere.wait(10)
                getattr(FeuilleService.objects.get(pk=self.feuille.pk), etape)(*args)
                resultats.append("ok")
            except TransitionDejaEffectuee:
                resultats.append("deja")
            except Exception as erreur:  # pragma: no cover
                resultats.append(erreur)
            finally:
                connection.close()

        fils = [threading.Thread(target=soumettre) for _ in range(2)]
        with mock.patch.object(FeuilleService, "_notifier_prochain_visa", lent):
            for fil in fils:
                fil.start()
            for fil in fils:
                fil.join(60)
        self.assertEqual(sorted(resultats), ["deja", "ok"])

    def test_proposer(self):
        self._course("proposer", self.equipier)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_proposee").count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.chef_secteur).count(), 1)

    def test_viser_service(self):
        self.feuille.proposer(self.chef_secteur)
        notifications = Notification.objects.filter(user=self.etat_major).count()
        self._course("viser_service", self.chef_service)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_visa_service").count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.etat_major).count(), notifications + 1)

    def test_renvoyer(self):
        self.feuille.proposer(self.chef_secteur)
        self._course("renvoyer", self.chef_service, "Motif")
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_renvoyee").count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.equipier, verb__icontains="renvoyée").count(), 1)

    def test_viser_comaeq(self):
        self.feuille.proposer(self.chef_secteur)
        self.feuille.viser_service(self.chef_service)
        barriere, resultats = threading.Barrier(2), []

        def soumettre():
            try:
                barriere.wait(10)
                FeuilleService.objects.get(pk=self.feuille.pk).viser_comaeq(self.etat_major)
                resultats.append("ok")
            except TransitionDejaEffectuee:
                resultats.append("deja")
            except Exception as erreur:  # pragma: no cover
                resultats.append(erreur)
            finally:
                connection.close()

        fils = [threading.Thread(target=soumettre) for _ in range(2)]
        for fil in fils:
            fil.start()
        for fil in fils:
            fil.join(60)
        self.assertEqual(sorted(resultats), ["deja", "ok"])
        self.assertEqual(self.feuille.versions.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_publiee").count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.marin_service, verb__icontains="publiée").count(), 1)


class ReprisePeriodiqueTests(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.relais = _utilisateur("marin_relais", "EQUIPIER", ship=self.ship)
        self.creneau = self._publier_tour(marin=self.marin_service)
        self.feuille = self._publiee(self.ship)

    def _publiee(self, ship, jour=None):
        feuille = FeuilleService.objects.create(
            ship=ship, date=jour or self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        feuille.proposer(self.chef_service)
        feuille.viser_service(self.chef_service)
        feuille.viser_comaeq(self.etat_major)
        return feuille

    def _echange(self, marin):
        self.creneau.marin = marin
        self.creneau.save(update_fields=["marin", "updated_at"])

    def _signaux(self):
        return Notification.objects.filter(verb__icontains="rectificatif à préparer")

    def test_entree_du_planificateur(self):
        entree = celery_app.conf.beat_schedule["signaler_divergences_feuilles_15min"]
        self.assertEqual(entree["task"], "quarts.tasks.signaler_divergences_feuilles")
        self.assertEqual(entree["schedule"], 900)
        self.assertEqual(celery_app.conf.beat_schedule["appliquer_releves_echues_minute"]["schedule"], 60)
        self.assertIn(entree["task"], celery_app.tasks)

    def test_deux_passages_un_seul_signal(self):
        self._echange(self.relais)
        self.assertEqual(signaler_divergences_feuilles(), 1)
        signaler_divergences_feuilles()
        self.assertEqual(sorted(self._signaux().values_list("user__username", flat=True)), ["bsc", "etat_major"])

    def test_divergence_resorbee_pas_de_signal(self):
        self._echange(self.relais)
        self._echange(self.marin_service)
        signaler_divergences_feuilles()
        self.assertFalse(self._signaux().exists())

    def test_sans_divergence_rien(self):
        signaler_divergences_feuilles()
        self.assertFalse(self._signaux().exists())

    def test_deja_signalee_pas_de_doublon_avec_le_signalement_immediat(self):
        self._echange(self.relais)
        signaler_divergence(self.feuille)
        signaler_divergences_feuilles()
        self.assertEqual(self._signaux().count(), 2)

    def test_feuille_passee_ou_sans_version_ignoree(self):
        brouillon = FeuilleService.objects.create(
            ship=self.ship, date=self.jour.replace(year=self.jour.year + 1), created_by=self.equipier,
        )
        self._echange(self.relais)
        FeuilleService.objects.filter(pk=self.feuille.pk).update(date=self.jour.replace(year=self.jour.year - 1))
        self.assertEqual(signaler_divergences_feuilles(), 0)
        self.assertFalse(self._signaux().exists())
        self.assertEqual(brouillon.versions.count(), 0)

    def test_feuille_d_un_autre_batiment_non_touchee(self):
        autre = self._publiee(self.autre_ship)
        self._echange(self.relais)
        signaler_divergences_feuilles()
        autre.refresh_from_db()
        self.assertEqual(autre.divergence_signalee, "")
        self.assertEqual(self._signaux().filter(url__contains=f"/{self.autre_ship.pk}/").count(), 0)
        self.feuille.refresh_from_db()
        self.assertNotEqual(self.feuille.divergence_signalee, "")

    def test_erreur_sur_une_feuille_n_empeche_pas_les_autres(self):
        autre = self._publiee(self.autre_ship)
        self._echange(self.relais)
        reel = signaler_divergence

        def panne_sur_la_premiere(feuille):
            if feuille.pk == self.feuille.pk:
                raise RuntimeError("panne")
            return reel(feuille)

        with mock.patch("quarts.rectificatif.signaler_divergence", side_effect=panne_sur_la_premiere) as signaler:
            self.assertEqual(signaler_divergences_feuilles(), 2)
        self.assertEqual(signaler.call_count, 2)
        trace = AuditLog.objects.get(action="feuille_service_signalement_echoue")
        self.assertIn("RuntimeError", trace.details)
        self.assertIn("reprise périodique", trace.details)
        autre.refresh_from_db()
        self.assertEqual(autre.divergence_signalee, "")
        # L'erreur laisse l'empreinte non marquée : le passage suivant retente.
        signaler_divergences_feuilles()
        self.assertEqual(self._signaux().count(), 2)
