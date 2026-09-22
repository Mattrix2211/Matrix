"""Vérifie que les absences déclarées apparaissent sur le calendrier
personnel du marin concerné (tâche Notion « Absences et indisponibilités »),
même principe que les créneaux de quart/garde déjà agrégés (cf.
calendar_app/tests/test_quarts_creneaux.py)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from icalendar import Calendar

from accounts.models import TypeAbsence
from absences.models import Absence


class AbsenceCalendrierTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin_absence", password="pass")
        self.autre_marin = User.objects.create_user(username="autre_marin_absence", password="pass")
        self.type_absence = TypeAbsence.objects.create(name="Mission")
        self.jour = timezone.localdate()
        self.absence = Absence.objects.create(
            marin=self.marin, type_absence=self.type_absence,
            date_debut=self.jour, date_fin=self.jour + timedelta(days=1),
        )

    def test_calendar_events_affiche_l_absence(self):
        self.client.login(username="marin_absence", password="pass")
        url = reverse("calendar-events") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        events = [e for e in resp.json() if e["extendedProps"]["type"] == "absence"]
        self.assertEqual(len(events), 1)
        self.assertIn("Mission", events[0]["title"])
        self.assertEqual(events[0]["id"], f"abs-{self.absence.pk}")

    def test_collect_events_affiche_l_absence(self):
        self.client.login(username="marin_absence", password="pass")
        url = reverse("calendar-index") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        types = [e["type"] for e in resp.context["events"]]
        self.assertIn("absence", types)

    def test_evenements_utilisateur_jour_inclut_l_absence(self):
        from calendar_app.views import evenements_utilisateur_jour

        evenements = evenements_utilisateur_jour(self.marin, self.jour)
        self.assertEqual(len(evenements["absences"]), 1)
        self.assertEqual(evenements["absences"][0], self.absence)

    def test_ical_feed_inclut_l_absence(self):
        self.client.login(username="marin_absence", password="pass")
        resp = self.client.get(reverse("calendar-ical-my"))
        cal = Calendar.from_ical(resp.content)
        summaries = [str(c.get("summary")) for c in cal.walk() if c.name == "VEVENT"]
        self.assertIn("Absence: Mission", summaries)

    def test_un_autre_marin_ne_voit_pas_l_absence_via_le_filtre_utilisateur(self):
        self.client.login(username="autre_marin_absence", password="pass")
        url = reverse("calendar-events") + (
            f"?date={self.jour.isoformat()}&view=day&user={self.autre_marin.pk}"
        )
        resp = self.client.get(url)
        events = [e for e in resp.json() if e["extendedProps"]["type"] == "absence"]
        self.assertEqual(len(events), 0)
