"""Sessions de formation et absences du calendrier : un marin ne voit que ses affectations, un chef celles de son équipe."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from absences.models import Absence
from accounts.models import TypeAbsence
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingSession


class PerimetreFormationsTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Périmètre", code="PF")
        service = Service.objects.create(ship=navire, name="Énergie")
        secteur = Sector.objects.create(service=service, name="Propulsion")
        autre = Sector.objects.create(service=service, name="Électricité")
        self.chef = self._marin("chef", secteur, "CHEF_SECTION")
        self.marin = self._marin("marin", secteur, "EQUIPIER")
        self.voisin = self._marin("voisin", autre, "EQUIPIER")
        self.jour = timezone.localdate() + timedelta(days=2)
        cours = TrainingCourse.objects.create(title="Sécurité incendie")
        quand = timezone.now() + timedelta(days=2)
        self.session_marin = TrainingSession.objects.create(course=cours, scheduled_at=quand)
        self.session_marin.attendees.add(self.marin)
        self.session_voisin = TrainingSession.objects.create(course=cours, scheduled_at=quand)
        self.session_voisin.attendees.add(self.voisin)
        type_absence = TypeAbsence.objects.create(name="Permission")
        self.absence_voisin = Absence.objects.create(
            marin=self.voisin, type_absence=type_absence, date_debut=self.jour, date_fin=self.jour,
            statut=Absence.STATUT_VALIDEE, created_by=self.voisin)

    def _marin(self, nom, secteur, role):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, secteur.service.ship, secteur.service, secteur
        p.save()
        return user

    def _ids(self, nom, **extra):
        self.client.force_login(User.objects.get(username=nom))
        params = {"view": "day", "date": self.jour.isoformat(), **extra}
        reponse = self.client.get(reverse("calendar-events"), params)
        self.assertEqual(reponse.status_code, 200)
        return {e["id"] for e in reponse.json()}

    def test_un_marin_ne_voit_pas_la_session_d_un_autre(self):
        ids = self._ids("marin")
        self.assertIn(f"trn-{self.session_marin.pk}", ids)
        self.assertNotIn(f"trn-{self.session_voisin.pk}", ids)
        self.assertNotIn(f"trn-{self.session_voisin.pk}", self._ids("marin", user=self.voisin.pk))

    def test_un_chef_voit_son_equipe_mais_pas_hors_perimetre(self):
        ids = self._ids("chef")
        self.assertIn(f"trn-{self.session_marin.pk}", ids)
        self.assertNotIn(f"trn-{self.session_voisin.pk}", ids)

    def test_absence_hors_perimetre_masquee(self):
        for nom in ("marin", "chef"):
            self.assertNotIn(f"abs-{self.absence_voisin.pk}", self._ids(nom))
            self.assertNotIn(f"abs-{self.absence_voisin.pk}", self._ids(nom, user=self.voisin.pk))
        self.assertIn(f"abs-{self.absence_voisin.pk}", self._ids("voisin"))

    def test_page_calendrier_filtre_aussi(self):
        self.client.force_login(self.marin)
        reponse = self.client.get(reverse("calendar-index"), {"view": "day", "date": self.jour.isoformat()})
        formations = [e for e in reponse.context["events"] if e["type"] == "training"]
        self.assertEqual(len(formations), 1)

    def test_detail_formation_404_hors_perimetre(self):
        def code(nom, session):
            self.client.force_login(User.objects.get(username=nom))
            return self.client.get(reverse("calendar-detail", args=["training", session.pk]), HTTP_HX_REQUEST="true").status_code
        self.assertEqual(code("marin", self.session_marin), 200)
        self.assertEqual(code("marin", self.session_voisin), 404)
        self.assertEqual(code("chef", self.session_marin), 200)
        self.assertEqual(code("chef", self.session_voisin), 404)
