"""Calendrier : plafond de pastilles par jour, avec « +N autres » menant à la vue Jour."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PlafondPastillesTests(TestCase):
    def test_gabarit_plafonne_et_renvoie_vers_la_vue_jour(self):
        self.client.force_login(User.objects.create_user("marin_cal", password="pass"))
        page = self.client.get(reverse("calendar-index")).content.decode()
        self.assertIn("dayMaxEvents: 4", page)
        self.assertIn("' autres'", page)
        self.assertIn("searchParams.set('view', 'day')", page)
