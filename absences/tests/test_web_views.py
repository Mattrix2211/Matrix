"""Tests de l'écran web « Mes absences » (déclaration/validation)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import TypeAbsence
from org.models import Sector, Service, Ship
from absences.models import Absence


def _marin(nom, secteur, role="EQUIPIER"):
    user = User.objects.create_user(username=nom, password="pass")
    # cf. absences/tests/test_absences.py::_marin — on mute l'objet déjà mis
    # en cache par le signal post_save plutôt que d'en créer un second.
    profile = user.profile
    profile.role = role
    profile.sector = secteur
    profile.save()
    return user


class MesAbsencesViewTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Absences Web", code="AWB")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.sector = Sector.objects.create(service=self.service, name="Manœuvre")
        self.marin = _marin("marin_web", self.sector)
        self.chef = _marin("chef_web", self.sector, role="CHEF_SECTION")
        self.type_absence = TypeAbsence.objects.create(name="Permission")
        self.aujourdhui = timezone.localdate()

    def test_marin_declare_sa_propre_absence(self):
        self.client.login(username="marin_web", password="pass")
        resp = self.client.post(reverse("absences-index"), {
            "action": "declarer",
            "type_absence": self.type_absence.pk,
            "date_debut": self.aujourdhui.isoformat(),
            "date_fin": (self.aujourdhui + timedelta(days=2)).isoformat(),
        })
        self.assertRedirects(resp, reverse("absences-index"))
        absence = Absence.objects.get(marin=self.marin)
        self.assertEqual(absence.statut, Absence.STATUT_DECLAREE)

    def test_chef_valide_une_absence_declaree(self):
        absence = Absence.objects.create(
            marin=self.marin, type_absence=self.type_absence,
            date_debut=self.aujourdhui, date_fin=self.aujourdhui,
        )
        self.client.login(username="chef_web", password="pass")
        resp = self.client.post(reverse("absences-index"), {"action": "valider", "absence_id": absence.pk})
        self.assertRedirects(resp, reverse("absences-index"))
        absence.refresh_from_db()
        self.assertEqual(absence.statut, Absence.STATUT_VALIDEE)
        self.assertEqual(absence.validee_par, self.chef)

    def test_page_accessible_et_liste_mes_absences(self):
        Absence.objects.create(
            marin=self.marin, type_absence=self.type_absence,
            date_debut=self.aujourdhui, date_fin=self.aujourdhui,
        )
        self.client.login(username="marin_web", password="pass")
        resp = self.client.get(reverse("absences-index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Permission")
