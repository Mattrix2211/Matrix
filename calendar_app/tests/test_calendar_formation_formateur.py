"""Vérifie que le calendrier central traite le FORMATEUR (instructor) d'une
session de formation comme une affectation personnelle à part entière, au
même titre que le stagiaire (attendees) et l'inscrit en libre-service
(reservations) — cf. tâche Notion « Calendrier de formation piloté par
l'affectation personnelle (stagiaire/formateur) ». Sans ce filtre, un
formateur qui n'est pas lui-même stagiaire de sa propre session ne la
voyait ni sur le calendrier central (filtre "Utilisateur" = lui-même), ni
sur son espace personnel (calendar_app.evenements_utilisateur_jour, digest
« Ma journée », tableau de bord)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from training.models import TrainingCourse, TrainingSession


class FormateurCalendrierTests(TestCase):
    def setUp(self):
        self.formateur = User.objects.create_user(username="formateur", password="pass")
        self.stagiaire = User.objects.create_user(username="stagiaire", password="pass")
        UserProfile.objects.filter(user=self.formateur).update(role="CHEF_SECTION")

        self.cours = TrainingCourse.objects.create(title="Sécurité incendie")
        self.session = TrainingSession.objects.create(
            course=self.cours,
            scheduled_at=timezone.now() + timedelta(days=2),
            instructor=self.formateur,
        )
        # Une session où le formateur n'a aucun rôle, pour vérifier qu'elle
        # n'apparaît PAS quand on filtre sur lui.
        self.autre_session = TrainingSession.objects.create(
            course=self.cours, scheduled_at=timezone.now() + timedelta(days=2),
        )
        self.autre_session.attendees.add(self.stagiaire)

        self.date_filtre = timezone.localdate() + timedelta(days=2)

    def test_calendar_events_json_affiche_la_session_du_formateur(self):
        self.client.login(username="stagiaire", password="pass")
        url = reverse("calendar-events") + (
            f"?view=day&date={self.date_filtre.isoformat()}&user={self.formateur.pk}"
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        events = resp.json()
        training_events = [e for e in events if e["extendedProps"]["type"] == "training"]
        self.assertEqual(len(training_events), 1)
        self.assertEqual(training_events[0]["id"], f"trn-{self.session.pk}")

    def test_calendar_index_affiche_la_session_du_formateur(self):
        self.client.login(username="stagiaire", password="pass")
        url = reverse("calendar-index") + (
            f"?view=day&date={self.date_filtre.isoformat()}&user={self.formateur.pk}"
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        training_events = [e for e in resp.context["events"] if e["type"] == "training"]
        self.assertEqual(len(training_events), 1)

    def test_formateur_peut_deplacer_sa_propre_session_sans_etre_stagiaire(self):
        """_perimetre_session (utilisée par calendar_event_move) doit
        autoriser le formateur au même titre qu'un stagiaire — non seulement
        le filtre d'affichage."""
        self.client.login(username="formateur", password="pass")
        nouvelle_date = self.date_filtre + timedelta(days=1)
        resp = self.client.post(
            reverse("calendar-event-move"),
            {"type": "training", "id": str(self.session.pk), "date": nouvelle_date.isoformat() + "T09:00"},
        )
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(timezone.localdate(self.session.scheduled_at), nouvelle_date)

    def test_export_ical_personnel_inclut_la_session_du_formateur(self):
        """user_ical_feed doit inclure les sessions animées par l'utilisateur
        (instructor), pas seulement celles où il est stagiaire (attendees) ou
        inscrit en libre-service (reservations)."""
        self.client.login(username="formateur", password="pass")
        resp = self.client.get(reverse("calendar-ical-my"))
        self.assertEqual(resp.status_code, 200)
        contenu = resp.content.decode("utf-8")
        self.assertIn(f"Formation: {self.cours.title}", contenu)
        # La session sans lien avec le formateur ne doit pas apparaître.
        self.assertEqual(contenu.count("Formation:"), 1)
