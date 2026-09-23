"""Tests de l'affectation proactive d'un marin à une session de formation par
un référent (T-FORM affectation) : distinct de la réservation self-service
(ReservationSessionTests, test_reservations.py) où c'est le marin qui réserve
sa propre place — ici c'est le référent qui affecte directement un marin,
équivalent fonctionnellement à une réservation faite en son nom
(TrainingSession.reservations, PAS attendees : la présence/réussite réelle
reste constatée séparément le jour J via ValiderFormationView, non touchée
par cette fonctionnalité). Réutilise l'autorisation existante
(peut_valider_formation, training/models.py) et le signal existant de
contrôle des réservations (_controler_reservation), aucun nouveau seuil de
permission ni nouveau contrôle métier."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from calendar_app.views import calendar_events
from notifications.models import Notification
from org.models import Ship
from training.models import ReferentFormation, TrainingCourse, TrainingRecord, TrainingSession


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class AffectationSessionReferentTests(TestCase):
    """Un référent (même de rang EQUIPIER, désigné pour cette formation
    précise) peut affecter un marin à une session : succès, notification, et
    apparition dans le calendrier personnel du marin."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Affectation", code="AFF")
        self.course = TrainingCourse.objects.create(title="Sécurité incendie niveau 1")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.marin = User.objects.create_user(username="marin_affecte", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship},
        )
        self.referent = User.objects.create_user(username="referent_affecte", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)
        # Rechargé depuis la base pour repartir d'un profil non caché par le
        # signal de création automatique (accounts/models.py).
        self.referent = User.objects.get(pk=self.referent.pk)

    def test_referent_peut_affecter_un_marin(self):
        self.client.login(username="referent_affecte", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_session",
            "session_id": self.session.id,
            "marin_id": self.marin.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn(self.marin, self.session.reservations.all())

    def test_affectation_envoie_une_notification_au_marin(self):
        self.client.login(username="referent_affecte", password="pass")
        self.client.post("/formations/", {
            "action": "affecter_session",
            "session_id": self.session.id,
            "marin_id": self.marin.id,
        })
        notif = Notification.objects.filter(user=self.marin).first()
        self.assertIsNotNone(notif)
        self.assertIn("réservée", notif.verb)
        self.assertIn("Sécurité incendie niveau 1", notif.verb)
        self.assertEqual(notif.level, "info")

    def test_affectation_apparait_dans_le_calendrier_du_marin(self):
        self.session.reservations.add(self.marin)
        request = type("Req", (), {
            "user": self.marin,
            "GET": {
                "user": str(self.marin.id),
                "view": "month",
                "date": self.session.scheduled_at.date().isoformat(),
            },
        })()
        response = calendar_events(request)
        import json
        events = json.loads(response.content)
        ids = [e["id"] for e in events]
        self.assertIn(f"trn-{self.session.id}", ids)

    def test_affectation_double_nenvoie_pas_deux_notifications(self):
        self.client.login(username="referent_affecte", password="pass")
        self.client.post("/formations/", {
            "action": "affecter_session", "session_id": self.session.id, "marin_id": self.marin.id,
        })
        self.client.post("/formations/", {
            "action": "affecter_session", "session_id": self.session.id, "marin_id": self.marin.id,
        })
        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)
        self.assertEqual(self.session.reservations.count(), 1)

    def test_affectation_ne_touche_pas_attendees(self):
        self.client.login(username="referent_affecte", password="pass")
        self.client.post("/formations/", {
            "action": "affecter_session", "session_id": self.session.id, "marin_id": self.marin.id,
        })
        self.assertEqual(self.session.attendees.count(), 0)


class AffectationSessionNonReferentTests(TestCase):
    """Un marin qui n'est ni référent de la formation ni chef habilité ne peut
    pas affecter un tiers à une session."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Affectation Refus", code="AFR")
        self.course = TrainingCourse.objects.create(title="Amarrage niveau 1")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=10),
        )
        self.marin = User.objects.create_user(username="marin_cible_refus", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship},
        )
        self.non_referent = User.objects.create_user(username="equipier_non_referent", password="pass")
        UserProfile.objects.update_or_create(user=self.non_referent, defaults={"role": "EQUIPIER"})

    def test_non_referent_ne_peut_pas_affecter(self):
        self.client.login(username="equipier_non_referent", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_session",
            "session_id": self.session.id,
            "marin_id": self.marin.id,
        })
        self.assertEqual(r.status_code, 403)
        self.assertNotIn(self.marin, self.session.reservations.all())
        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 0)


class AffectationCapaciteTests(TestCase):
    """Les règles métier existantes (capacité) s'appliquent aussi à
    l'affectation par un référent — même signal m2m que la réservation
    self-service, non dupliqué."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Affectation Capa", code="AFC")
        self.course = TrainingCourse.objects.create(title="Extinction niveau 1")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=5), capacite_max=1,
        )
        self.deja_inscrit = User.objects.create_user(username="deja_inscrit_affect", password="pass")
        self.session.reservations.add(self.deja_inscrit)

        self.marin = User.objects.create_user(username="marin_capa_affect", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship},
        )
        self.referent = User.objects.create_user(username="referent_capa_affect", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)
        self.referent = User.objects.get(pk=self.referent.pk)

    def test_affectation_refusee_si_session_complete(self):
        self.client.login(username="referent_capa_affect", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_session",
            "session_id": self.session.id,
            "marin_id": self.marin.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin, self.session.reservations.all())
        self.assertEqual(self.session.reservations.count(), 1)


class AffectationPrerequisTests(TestCase):
    """Les prérequis manquants du marin ciblé bloquent aussi l'affectation par
    un référent — même contrôle que la réservation self-service."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Affectation Prereq", code="AFP")
        self.base = TrainingCourse.objects.create(title="Habilitation électrique niveau 1")
        self.avance = TrainingCourse.objects.create(title="Habilitation électrique niveau 2")
        self.avance.prerequisites.set([self.base])
        self.session = TrainingSession.objects.create(
            course=self.avance, scheduled_at=timezone.now() + timedelta(days=15),
        )
        self.marin = User.objects.create_user(username="marin_prereq_affect", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship},
        )
        self.referent = User.objects.create_user(username="referent_prereq_affect", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.avance, ship=self.ship, user=self.referent)
        self.referent = User.objects.get(pk=self.referent.pk)

    def test_affectation_refusee_sans_prerequis(self):
        self.client.login(username="referent_prereq_affect", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_session",
            "session_id": self.session.id,
            "marin_id": self.marin.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin, self.session.reservations.all())

    def test_affectation_acceptee_avec_prerequis_valide(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.base,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="referent_prereq_affect", password="pass")
        self.client.post("/formations/", {
            "action": "affecter_session",
            "session_id": self.session.id,
            "marin_id": self.marin.id,
        })
        self.assertIn(self.marin, self.session.reservations.all())
