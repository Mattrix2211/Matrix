"""Tests de la réservation self-service d'une session de formation (T-RESA) :
un marin réserve/annule SA PROPRE place sur une TrainingSession PLANNED, tant
que la capacité n'est pas atteinte et que ses prérequis sont validés. Distinct
de la validation de présence par un référent (TrainingSession.attendees, non
touché par cette fonctionnalité — cf. training/models.py::peut_valider_formation)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from calendar_app.views import calendar_events
from notifications.models import Notification
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingRecord, TrainingSession


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class ReservationSessionTests(TestCase):
    """Réservation réussie : notification de confirmation + apparition dans le
    calendrier personnel (calendar_app, même mécanisme que les occurrences
    assignées)."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Résa", code="RESA")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Sécurité incendie niveau 1")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.marin = User.objects.create_user(username="marin_resa", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

    def test_reservation_reussie(self):
        self.client.login(username="marin_resa", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn(self.marin, self.session.reservations.all())

    def test_reservation_envoie_une_notification_de_confirmation(self):
        self.client.login(username="marin_resa", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        notif = Notification.objects.filter(user=self.marin).first()
        self.assertIsNotNone(notif)
        self.assertIn("Réservation confirmée", notif.verb)
        self.assertIn("Sécurité incendie niveau 1", notif.verb)

    def test_reservation_apparait_dans_le_calendrier_personnel(self):
        self.session.reservations.add(self.marin)
        request = type("Req", (), {
            "user": self.marin,
            "GET": {"user": str(self.marin.id), "view": "month"},
        })()
        response = calendar_events(request)
        import json
        events = json.loads(response.content)
        ids = [e["id"] for e in events]
        self.assertIn(f"trn-{self.session.id}", ids)

    def test_reservation_double_nenvoie_pas_deux_notifications(self):
        self.client.login(username="marin_resa", password="pass")
        self.client.post("/formations/", {"action": "reserver_session", "session_id": self.session.id})
        self.client.post("/formations/", {"action": "reserver_session", "session_id": self.session.id})
        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)
        self.assertEqual(self.session.reservations.count(), 1)


class CapaciteReservationTests(TestCase):
    """Refus (message clair) si la capacité maximale de la session est déjà
    atteinte — pas de liste d'attente pour cette version."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Capa", code="CAPA")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Extinction niveau 1")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=5), capacite_max=1,
        )
        self.deja_inscrit = User.objects.create_user(username="deja_inscrit", password="pass")
        self.session.reservations.add(self.deja_inscrit)
        self.marin = User.objects.create_user(username="marin_capa", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

    def test_reservation_refusee_si_session_complete(self):
        self.client.login(username="marin_capa", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin, self.session.reservations.all())
        self.assertEqual(self.session.reservations.count(), 1)

    def test_places_restantes_correctement_calculees(self):
        self.assertEqual(self.session.places_restantes(), 0)

    def test_reservation_directe_leve_une_erreur_si_complet(self):
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                self.session.reservations.add(self.marin)


class PrerequisReservationTests(TestCase):
    """La réservation respecte les mêmes prérequis que l'inscription par un
    référent (attendees) — réutilise _prerequis_manquants, ne réinvente rien."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Prér", code="PRER")
        service = Service.objects.create(ship=ship, name="Technique")
        self.sector = Sector.objects.create(service=service, name="Électricité")
        self.base = TrainingCourse.objects.create(sector=self.sector, title="Habilitation électrique niveau 1")
        self.avance = TrainingCourse.objects.create(sector=self.sector, title="Habilitation électrique niveau 2")
        self.avance.prerequisites.set([self.base])
        self.session = TrainingSession.objects.create(
            course=self.avance, scheduled_at=timezone.now() + timedelta(days=15),
        )
        self.marin = User.objects.create_user(username="marin_prer", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

    def test_reservation_refusee_sans_prerequis(self):
        self.client.login(username="marin_prer", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin, self.session.reservations.all())

    def test_reservation_refusee_si_prerequis_expire(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate() - timedelta(days=400),
            expires_at=timezone.localdate() - timedelta(days=35),
        )
        self.client.login(username="marin_prer", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertNotIn(self.marin, self.session.reservations.all())

    def test_reservation_acceptee_avec_prerequis_valide(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="marin_prer", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertIn(self.marin, self.session.reservations.all())


class AnnulationReservationTests(TestCase):
    """Annulation possible tant que la session n'a pas encore eu lieu."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Annul", code="ANNUL")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Sécurité de base")
        self.session_future = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.session_passee = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() - timedelta(days=1), status="DONE",
        )
        self.marin = User.objects.create_user(username="marin_annul", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})
        self.session_future.reservations.add(self.marin)

    def test_annulation_reussie(self):
        self.client.login(username="marin_annul", password="pass")
        r = self.client.post("/formations/", {
            "action": "annuler_reservation",
            "session_id": self.session_future.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin, self.session_future.reservations.all())

    def test_annulation_refusee_si_session_deja_passee(self):
        # Réservation directe (contournant le blocage pre_add PLANNED) pour ne
        # tester ici que le blocage à l'annulation d'une session déjà passée.
        self.session_passee.reservations.through.objects.create(
            trainingsession_id=self.session_passee.id, user_id=self.marin.id,
        )
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                self.session_passee.reservations.remove(self.marin)


class SecuriteReservationPourSoiMemeTests(TestCase):
    """Un marin ne peut réserver/annuler une place que pour lui-même : la
    réservation est toujours faite au nom de request.user, jamais d'un
    identifiant posté."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Sécu", code="SECU")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Sécurité")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.marin1 = User.objects.create_user(username="marin_sec1", password="pass")
        UserProfile.objects.update_or_create(user=self.marin1, defaults={"role": "EQUIPIER"})
        self.marin2 = User.objects.create_user(username="marin_sec2", password="pass")
        UserProfile.objects.update_or_create(user=self.marin2, defaults={"role": "EQUIPIER"})

    def test_reservation_ne_prend_pas_en_compte_un_user_id_poste(self):
        self.client.login(username="marin_sec1", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
            "user_id": self.marin2.id,
        })
        self.assertIn(self.marin1, self.session.reservations.all())
        self.assertNotIn(self.marin2, self.session.reservations.all())

    def test_annulation_ne_permet_pas_dannuler_la_reservation_dautrui(self):
        self.session.reservations.add(self.marin2)
        self.client.login(username="marin_sec1", password="pass")
        self.client.post("/formations/", {
            "action": "annuler_reservation",
            "session_id": self.session.id,
        })
        # marin1 n'avait pas de réservation : celle de marin2 reste intacte.
        self.assertIn(self.marin2, self.session.reservations.all())


class PerimetreReservationTests(TestCase):
    """La réservation respecte le même périmètre que la liste des formations
    (ScopedQuerySetMixin) : une session hors périmètre n'est pas réservable."""

    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire Périmètre Résa A", code="PRA")
        service_a = Service.objects.create(ship=self.navire_a, name="Technique")
        self.secteur_a = Sector.objects.create(service=service_a, name="Électricité")

        self.navire_b = Ship.objects.create(name="Navire Périmètre Résa B", code="PRB")
        service_b = Service.objects.create(ship=self.navire_b, name="Technique")
        self.secteur_b = Sector.objects.create(service=service_b, name="Électricité")
        self.course_b = TrainingCourse.objects.create(sector=self.secteur_b, title="Formation navire B")
        self.session_b = TrainingSession.objects.create(
            course=self.course_b, scheduled_at=timezone.now() + timedelta(days=10),
        )

        self.marin_a = User.objects.create_user(username="marin_perim_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_a, defaults={"role": "EQUIPIER", "ship": self.navire_a},
        )

    def test_reservation_refusee_hors_perimetre(self):
        self.client.login(username="marin_perim_a", password="pass")
        r = self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session_b.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin_a, self.session_b.reservations.all())


class NonRegressionAttendeesTests(TestCase):
    """La réservation self-service (reservations) ne doit avoir aucun effet
    sur le système existant de validation de présence par les référents
    (attendees) — les deux listes restent strictement indépendantes."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire NonReg", code="NREG")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Sécurité de base")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.marin = User.objects.create_user(username="marin_nonreg", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

    def test_reservation_ne_touche_pas_attendees(self):
        self.client.login(username="marin_nonreg", password="pass")
        self.client.post("/formations/", {
            "action": "reserver_session",
            "session_id": self.session.id,
        })
        self.assertEqual(self.session.attendees.count(), 0)
        self.assertEqual(self.session.reservations.count(), 1)

    def test_attendees_reste_gere_uniquement_par_les_referents(self):
        # La réservation self-service n'accorde aucun droit de validation :
        # un marin réservé (pas référent) ne peut toujours pas gérer les
        # présences (attendees), même sur sa propre session réservée.
        from training.models import peut_valider_formation
        self.session.reservations.add(self.marin)
        self.assertFalse(peut_valider_formation(self.marin, self.course))
