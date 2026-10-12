"""Filtre « Mon équipe » du calendrier : les marins sous le chef, et eux seuls, en lecture seule."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from absences.models import Absence
from accounts.models import TypeAbsence
from org.models import Sector, Service, Ship
from taches.models import Tache


class VueEquipeTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Équipe", code="EQ")
        service = Service.objects.create(ship=navire, name="Énergie")
        self.secteur = Sector.objects.create(service=service, name="Propulsion")
        autre = Sector.objects.create(service=service, name="Électricité")
        self.chef = self._marin("chef", self.secteur, "CHEF_SECTION")
        self.marin = self._marin("marin", self.secteur, "EQUIPIER")
        self.voisin = self._marin("voisin", autre, "EQUIPIER")
        self.jour = timezone.localdate()
        self.params = {"user": "equipe", "start": self.jour.isoformat(), "end": (self.jour + timedelta(days=10)).isoformat()}

    def _marin(self, nom, secteur, role):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, secteur.service.ship, secteur.service, secteur
        p.save()
        return user

    def _titres(self, user):
        self.client.force_login(user)
        reponse = self.client.get(reverse("calendar-events"), self.params)
        self.assertEqual(reponse.status_code, 200)
        return reponse.json()

    def test_le_chef_voit_son_equipe_et_seulement_elle(self):
        Tache.objects.create(titre="Contrôler la pompe", assigne=self.marin, created_by=self.chef, echeance=self.jour + timedelta(days=2))
        Tache.objects.create(titre="Tâche du voisin", assigne=self.voisin, created_by=self.chef, echeance=self.jour + timedelta(days=2))
        Tache.objects.create(titre="Perso privée", assigne=self.marin, created_by=self.marin, partagee=False, echeance=self.jour + timedelta(days=2))
        titres = [e["title"] for e in self._titres(self.chef)]
        self.assertEqual(titres, ["marin · Contrôler la pompe"])

    def test_retard_en_evidence_et_absences(self):
        Tache.objects.create(titre="En retard", assigne=self.marin, created_by=self.chef, echeance=self.jour)
        type_absence = TypeAbsence.objects.create(name="Permission")
        Absence.objects.create(marin=self.marin, type_absence=type_absence, date_debut=self.jour + timedelta(days=1),
                               date_fin=self.jour + timedelta(days=2), statut=Absence.STATUT_VALIDEE, created_by=self.chef)
        evenements = self._titres(self.chef)
        self.assertEqual({e["extendedProps"]["type"] for e in evenements}, {"tache", "absence"})
        self.assertTrue(all(not e["editable"] and not e["extendedProps"]["peut_agir"] for e in evenements))

    def test_un_marin_simple_n_a_pas_le_filtre(self):
        self.client.force_login(self.marin)
        self.assertEqual(self.client.get(reverse("calendar-events"), self.params).status_code, 403)
        self.assertNotContains(self.client.get(reverse("calendar-index")), 'value="equipe"')
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(reverse("calendar-index")), 'value="equipe"')
        self.assertEqual(self.client.get(reverse("calendar-index") + "?user=equipe").status_code, 200)
