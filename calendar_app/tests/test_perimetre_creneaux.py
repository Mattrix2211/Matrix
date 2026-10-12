"""Quarts, gardes et sessions du calendrier : périmètre des marins visibles et déplacement possible."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from org.models import Sector, Service, Ship
from quarts.models import CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde
from training.models import TrainingCourse, TrainingSession


class PerimetreCreneauxTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Créneaux", code="CR")
        service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=service, name="Propulsion")
        autre = Sector.objects.create(service=service, name="Électricité")
        self.chef = self._marin("chef", self.secteur, "CHEF_SECTION")
        self.marin = self._marin("marin", self.secteur, "EQUIPIER")
        self.voisin = self._marin("voisin", autre, "EQUIPIER")
        self.jour = timezone.localdate()
        debut = timezone.make_aware(timezone.datetime.combine(self.jour, timezone.datetime.min.time().replace(hour=8)))
        quart = Quart.objects.create(sector=self.secteur, date_debut=self.jour, date_fin=self.jour, statut=Quart.STATUT_PUBLIEE)
        garde = ServiceGarde.objects.create(
            sector=self.secteur, date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_PUBLIEE)
        self.quarts, self.gardes = {}, {}
        for marin in (self.marin, self.voisin):
            self.quarts[marin.username] = CreneauQuart.objects.create(
                quart=quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=marin)
            self.gardes[marin.username] = CreneauServiceGarde.objects.create(
                service_garde=garde, poste="Garde", debut=debut, fin=debut + timedelta(hours=4), marin=marin)

    def _marin(self, nom, secteur, role, equipage=""):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector, p.equipage = role, secteur.service.ship, secteur.service, secteur, equipage
        p.save()
        return user

    def _amiral(self, equipage=""):
        # MASTER_ADMIN sans rattachement : flotte entière.
        user = User.objects.create_user(username="amiral", password="pass")
        p = user.profile
        p.role, p.equipage = "MASTER_ADMIN", equipage
        p.save()
        return user

    def _evenements(self, demandeur, **extra):
        self.client.force_login(demandeur)
        params = {"view": "day", "date": self.jour.isoformat(), **extra}
        reponse = self.client.get(reverse("calendar-events"), params)
        self.assertEqual(reponse.status_code, 200)
        return {e["id"]: e for e in reponse.json()}

    def test_marin_ne_voit_que_ses_creneaux(self):
        for extra in ({}, {"user": self.voisin.pk}):
            ids = self._evenements(self.marin, **extra).keys()
            self.assertNotIn(f"qrt-{self.quarts['voisin'].pk}", ids)
            self.assertNotIn(f"svc-{self.gardes['voisin'].pk}", ids)
        ids = self._evenements(self.marin).keys()
        self.assertIn(f"qrt-{self.quarts['marin'].pk}", ids)
        self.assertIn(f"svc-{self.gardes['marin'].pk}", ids)

    def test_chef_voit_son_equipe_mais_pas_hors_perimetre(self):
        for extra in ({}, {"user": self.voisin.pk}):
            ids = self._evenements(self.chef, **extra).keys()
            self.assertNotIn(f"qrt-{self.quarts['voisin'].pk}", ids)
            self.assertNotIn(f"svc-{self.gardes['voisin'].pk}", ids)
        ids = self._evenements(self.chef).keys()
        self.assertIn(f"qrt-{self.quarts['marin'].pk}", ids)
        self.assertIn(f"svc-{self.gardes['marin'].pk}", ids)

    def test_page_calendrier_filtre_aussi(self):
        self.client.force_login(self.marin)
        reponse = self.client.get(
            reverse("calendar-index"), {"view": "day", "date": self.jour.isoformat(), "user": self.voisin.pk})
        types = [e["type"] for e in reponse.context["events"]]
        self.assertNotIn("quart", types)
        self.assertNotIn("service_garde", types)

    def test_master_admin_voit_les_creneaux_de_la_flotte(self):
        admin = self._amiral()
        ids = self._evenements(admin).keys()
        self.assertIn(f"qrt-{self.quarts['voisin'].pk}", ids)
        self.assertIn(f"svc-{self.gardes['voisin'].pk}", ids)

    def test_double_equipage_isole_les_equipages(self):
        self.navire.double_equipage, self.navire.equipage_a_bord = True, "ROUGE"
        self.navire.save()
        for nom, equipage in (("chef", "ROUGE"), ("marin", "ROUGE"), ("voisin", "BLEU")):
            p = User.objects.get(username=nom).profile
            p.equipage, p.sector = equipage, self.secteur
            p.save()
        # Voisin dans le même secteur que le chef : seul l'équipage l'écarte.
        ids = self._evenements(self.chef).keys()
        self.assertIn(f"qrt-{self.quarts['marin'].pk}", ids)
        self.assertNotIn(f"qrt-{self.quarts['voisin'].pk}", ids)
        self.assertNotIn(f"svc-{self.gardes['voisin'].pk}", ids)


class SessionsDeplacablesTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Sessions", code="SE")
        service = Service.objects.create(ship=navire, name="Énergie")
        secteur = Sector.objects.create(service=service, name="Propulsion")
        self.chef = self._marin("chef", secteur, "CHEF_SECTION")
        self.marin = self._marin("marin", secteur, "EQUIPIER")
        self.jour = timezone.localdate() + timedelta(days=1)
        cours = TrainingCourse.objects.create(title="Sécurité incendie")
        quand = timezone.now() + timedelta(days=1)
        self.session_marin = TrainingSession.objects.create(course=cours, scheduled_at=quand)
        self.session_marin.attendees.add(self.marin)
        self.session_chef = TrainingSession.objects.create(course=cours, scheduled_at=quand)
        self.session_chef.reservations.add(self.chef)
        self.session_formateur = TrainingSession.objects.create(course=cours, scheduled_at=quand, instructor=self.chef)

    def _marin(self, nom, secteur, role):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, secteur.service.ship, secteur.service, secteur
        p.save()
        return user

    def _editable(self, user):
        self.client.force_login(user)
        reponse = self.client.get(reverse("calendar-events"), {"view": "day", "date": self.jour.isoformat()})
        return {e["id"]: e["editable"] for e in reponse.json() if e["id"].startswith("trn-")}

    def test_chef_ne_deplace_que_ses_propres_sessions(self):
        editable = self._editable(self.chef)
        # Visible via son équipe mais refusée au déplacement : non glissable.
        self.assertFalse(editable[f"trn-{self.session_marin.pk}"])
        self.assertTrue(editable[f"trn-{self.session_chef.pk}"])
        self.assertTrue(editable[f"trn-{self.session_formateur.pk}"])

    def test_simple_marin_ne_deplace_rien(self):
        self.assertFalse(any(self._editable(self.marin).values()))
