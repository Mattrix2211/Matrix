"""Tests de la liste d'attente FIFO sur les sessions de formation complètes
(T-ATTENTE) : quand un marin tente de réserver une place en libre-service
alors que TrainingSession.capacite_max est déjà atteinte, il est mis en fin
de file plutôt que simplement refusé (training/models.py::
TrainingSession.inscrire_liste_attente). Dès qu'une réservation est annulée,
le premier de la file est notifié qu'une place s'est libérée — sans être
inscrit automatiquement, cohérent avec le principe self-service déjà en
place pour les réservations (cf. training/tests/test_reservations.py)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from notifications.models import Notification
from training.models import TrainingCourse, TrainingSession, TrainingWaitlistEntry


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class AjoutListeAttenteTests(TestCase):
    """Un marin tentant de réserver une session complète est mis en liste
    d'attente plutôt que refusé sèchement."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        self.deja_inscrit = User.objects.create_user(username="deja_la", password="pass")
        self.session.reservations.add(self.deja_inscrit)
        self.marin = User.objects.create_user(username="marin_la1", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

    def test_ajout_a_la_liste_dattente_si_session_complete(self):
        self.client.login(username="marin_la1", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin).exists())

    def test_message_indique_la_position(self):
        self.client.login(username="marin_la1", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        }, follow=True)
        self.assertContains(r, "position 1 sur la liste")

    def test_double_tentative_ne_duplique_pas_lentree(self):
        self.client.login(username="marin_la1", password="pass")
        self.client.post("/formations/", {"action": "reserver_session", "session_id": self.session.id})
        self.client.post("/formations/", {"action": "reserver_session", "session_id": self.session.id})
        self.assertEqual(TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin).count(), 1)

    def test_liste_dattente_refusee_sans_prerequis(self):
        avance = TrainingCourse.objects.create(title="Formation avancée LA")
        avance.prerequisites.set([self.course])
        session_avancee = TrainingSession.objects.create(
            course=avance, scheduled_at=timezone.now() + timedelta(days=12), capacite_max=1,
        )
        # Insertion directe (bypass du signal m2m, même principe que
        # test_reservations.py::AnnulationReservationTests) : seul le
        # remplissage de la session nous intéresse ici, pas les prérequis de
        # `deja_inscrit`.
        session_avancee.reservations.through.objects.create(
            trainingsession_id=session_avancee.id, user_id=self.deja_inscrit.id,
        )
        self.client.login(username="marin_la1", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": session_avancee.id,
        })
        self.assertFalse(
            TrainingWaitlistEntry.objects.filter(session=session_avancee, user=self.marin).exists()
        )


class OrdreFifoListeAttenteTests(TestCase):
    """L'ordre de la file respecte strictement l'ordre d'arrivée (FIFO)."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité FIFO")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        self.deja_inscrit = User.objects.create_user(username="deja_fifo", password="pass")
        self.session.reservations.add(self.deja_inscrit)
        self.marin1 = User.objects.create_user(username="marin_fifo1", password="pass")
        self.marin2 = User.objects.create_user(username="marin_fifo2", password="pass")
        self.marin3 = User.objects.create_user(username="marin_fifo3", password="pass")
        for m in (self.marin1, self.marin2, self.marin3):
            UserProfile.objects.update_or_create(user=m, defaults={"role": "EQUIPIER"})

    def test_position_respecte_lordre_darrivee(self):
        e1 = self.session.inscrire_liste_attente(self.marin1)
        e2 = self.session.inscrire_liste_attente(self.marin2)
        e3 = self.session.inscrire_liste_attente(self.marin3)
        self.assertEqual(e1.position(), 1)
        self.assertEqual(e2.position(), 2)
        self.assertEqual(e3.position(), 3)

    def test_le_premier_de_la_file_est_le_plus_ancien(self):
        self.session.inscrire_liste_attente(self.marin1)
        self.session.inscrire_liste_attente(self.marin2)
        premier = self.session.liste_attente.order_by("created_at").first()
        self.assertEqual(premier.user, self.marin1)


class NotificationLiberationPlaceTests(TestCase):
    """Quand une réservation est annulée, le premier de la liste d'attente
    (et lui seul) est notifié qu'une place s'est libérée — il n'est PAS
    inscrit automatiquement."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité notif")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        self.inscrit = User.objects.create_user(username="inscrit_notif", password="pass")
        UserProfile.objects.update_or_create(user=self.inscrit, defaults={"role": "EQUIPIER"})
        self.session.reservations.add(self.inscrit)
        self.marin1 = User.objects.create_user(username="marin_notif1", password="pass")
        self.marin2 = User.objects.create_user(username="marin_notif2", password="pass")
        self.session.inscrire_liste_attente(self.marin1)
        self.session.inscrire_liste_attente(self.marin2)

    def test_le_premier_de_la_file_est_notifie_a_lannulation(self):
        self.client.login(username="inscrit_notif", password="pass")
        self.client.post("/formations/", {
            "action": "annuler_reservation",
            "session_id": self.session.id,
        })
        self.assertTrue(
            Notification.objects.filter(
                user=self.marin1, verb__icontains="place s'est libérée"
            ).exists()
        )

    def test_le_second_de_la_file_nest_pas_notifie(self):
        self.client.login(username="inscrit_notif", password="pass")
        self.client.post("/formations/", {
            "action": "annuler_reservation",
            "session_id": self.session.id,
        })
        self.assertFalse(
            Notification.objects.filter(
                user=self.marin2, verb__icontains="place s'est libérée"
            ).exists()
        )

    def test_le_premier_nest_pas_inscrit_automatiquement(self):
        self.client.login(username="inscrit_notif", password="pass")
        self.client.post("/formations/", {
            "action": "annuler_reservation",
            "session_id": self.session.id,
        })
        self.assertNotIn(self.marin1, self.session.reservations.all())
        # Toujours en liste d'attente : c'est à lui de réserver lui-même.
        self.assertTrue(TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin1).exists())

    def test_annulation_directe_notifie_aussi(self):
        # Le signal m2m est le seul point de passage garanti (annulation
        # directe hors vue web, ex. admin/shell) : la notification doit
        # partir quel que soit l'appelant.
        self.session.reservations.remove(self.inscrit)
        self.assertTrue(
            Notification.objects.filter(user=self.marin1, verb__icontains="place s'est libérée").exists()
        )

    def test_pas_de_notification_si_personne_en_liste_dattente(self):
        autre_course = TrainingCourse.objects.create(title="TP Sécurité sans attente")
        autre_session = TrainingSession.objects.create(
            course=autre_course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        autre_inscrit = User.objects.create_user(username="inscrit_seul", password="pass")
        autre_session.reservations.add(autre_inscrit)
        autre_session.reservations.remove(autre_inscrit)
        # Aucune liste d'attente sur cette session : aucune notification créée.
        self.assertFalse(
            Notification.objects.filter(
                user=autre_inscrit, verb__icontains="place s'est libérée"
            ).exists()
        )


class RetraitListeAttenteTests(TestCase):
    """Retrait de la liste d'attente : automatique quand le marin obtient
    effectivement une place, ou volontaire à sa demande."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité retrait")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        self.inscrit = User.objects.create_user(username="inscrit_retrait", password="pass")
        self.session.reservations.add(self.inscrit)
        self.marin = User.objects.create_user(username="marin_retrait", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})
        self.session.inscrire_liste_attente(self.marin)

    def test_retrait_automatique_quand_le_marin_obtient_une_place(self):
        # Une place se libère (annulation), puis le marin réserve lui-même :
        # son entrée en liste d'attente doit disparaître.
        self.session.reservations.remove(self.inscrit)
        self.client.login(username="marin_retrait", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertIn(self.marin, self.session.reservations.all())
        self.assertFalse(TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin).exists())

    def test_retrait_volontaire(self):
        self.client.login(username="marin_retrait", password="pass")
        r = self.client.post("/formations/", {
            "action": "quitter_liste_attente",
            "session_id": self.session.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin).exists())

    def test_retrait_volontaire_ne_touche_pas_les_autres(self):
        marin2 = User.objects.create_user(username="marin_retrait2", password="pass")
        self.session.inscrire_liste_attente(marin2)
        self.client.login(username="marin_retrait", password="pass")
        self.client.post("/formations/", {
            "action": "quitter_liste_attente",
            "session_id": self.session.id,
        })
        self.assertTrue(TrainingWaitlistEntry.objects.filter(session=self.session, user=marin2).exists())


class InscriptionListeAttenteDirecteTests(TestCase):
    """Contrôles directs de TrainingSession.inscrire_liste_attente (utilisée
    par la vue, testée ici indépendamment)."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité direct")
        self.marin = User.objects.create_user(username="marin_direct", password="pass")

    def test_refuse_si_session_annulee(self):
        session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
            capacite_max=1, status="CANCELLED",
        )
        with self.assertRaises(ValidationError):
            session.inscrire_liste_attente(self.marin)

    def test_idempotent_renvoie_la_meme_entree(self):
        session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        e1 = session.inscrire_liste_attente(self.marin)
        e2 = session.inscrire_liste_attente(self.marin)
        self.assertEqual(e1.pk, e2.pk)
        self.assertEqual(TrainingWaitlistEntry.objects.filter(session=session, user=self.marin).count(), 1)


class NonRegressionReservationNormaleTests(TestCase):
    """Non-régression : une réservation classique (place disponible) n'est
    pas affectée par l'ajout de la liste d'attente."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="Formation avec places libres")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=5,
        )
        self.marin = User.objects.create_user(username="marin_normal", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

    def test_reservation_directe_si_places_disponibles(self):
        self.client.login(username="marin_normal", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn(self.marin, self.session.reservations.all())
        self.assertFalse(TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin).exists())

    def test_aucune_capacite_limitee_jamais_de_liste_dattente(self):
        session_illimitee = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.client.login(username="marin_normal", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": session_illimitee.id,
        })
        self.assertIn(self.marin, session_illimitee.reservations.all())
        self.assertEqual(TrainingWaitlistEntry.objects.count(), 0)


class BoutonReservationApresLiberationTests(TestCase):
    """Régression (refus QA) : quand une place se libère pendant qu'un marin
    est en liste d'attente, le bouton « Réserver ma place » doit apparaître
    sur /formations/ sans qu'il ait d'abord besoin de quitter la liste
    d'attente — le backend (_reserver_session) gère déjà ce cas, seul le
    rendu du template était en cause. Scénario exact du QA : session
    capacite_max=1, marin A réserve, marin B est mis en liste d'attente, A
    annule -> B doit voir le bouton de réservation en un clic."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité bouton")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10), capacite_max=1,
        )
        self.marin_a = User.objects.create_user(username="marin_bouton_a", password="pass")
        self.marin_b = User.objects.create_user(username="marin_bouton_b", password="pass")
        for m in (self.marin_a, self.marin_b):
            UserProfile.objects.update_or_create(user=m, defaults={"role": "EQUIPIER"})
        self.session.reservations.add(self.marin_a)

    def test_reserver_ma_place_visible_apres_liberation_dune_place(self):
        # Marin B tente de réserver la session complète -> mis en liste d'attente.
        self.client.login(username="marin_bouton_b", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertTrue(
            TrainingWaitlistEntry.objects.filter(session=self.session, user=self.marin_b).exists()
        )
        # Marin A annule sa réservation -> une place se libère, B est notifié.
        self.client.logout()
        self.client.login(username="marin_bouton_a", password="pass")
        self.client.post("/formations/", {
            "action": "annuler_reservation",
            "session_id": self.session.id,
        })
        # Marin B recharge la page : le bouton « Réserver ma place » doit être
        # présent et actionnable, pas seulement « Quitter la liste d'attente ».
        self.client.logout()
        self.client.login(username="marin_bouton_b", password="pass")
        r = self.client.get("/formations/")
        self.assertContains(r, "Réserver ma place")
        self.assertContains(r, 'value="reserver_session"')
        self.assertContains(r, "Quitter la liste d'attente")
        # Régression : le commentaire {# ... #} multi-lignes expliquant ce
        # bloc s'affichait en clair, faute d'être invisible avec
        # {% comment %}...{% endcomment %}.
        self.assertNotContains(r, "Une place s'est libérée pendant que le marin était en liste d'attente")

    def test_reserver_ma_place_absent_tant_quaucune_place_ne_sest_liberee(self):
        # Non-régression : tant que la session reste complète, seul « Quitter »
        # doit être proposé (pas de bouton de réservation trompeur).
        self.client.login(username="marin_bouton_b", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        r = self.client.get("/formations/")
        self.assertContains(r, "Quitter la liste d'attente")
        self.assertNotContains(r, "Réserver ma place")
