"""Reprise conservatrice des listes à quai publiées (situations temporelles) et diagnostic des chevauchements."""
import importlib
from datetime import timedelta
from io import StringIO

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import FonctionQuartChoice, ServiceFunctionChoice
from org.models import Service, Ship
from quarts.models import CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde

migration = importlib.import_module("quarts.migrations.0014_reprise_listes_quai_publiees")


class RepriseListesQuaiTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Bâtiment", code="BAT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.fonction = ServiceFunctionChoice.objects.create(name="Permanence")
        self.auj = timezone.localdate()

    def _liste(self, debut, fin, statut=ServiceGarde.STATUT_PUBLIEE):
        return ServiceGarde.objects.create(
            service=self.service, fonction=self.fonction, date_debut=self.auj + timedelta(days=debut),
            date_fin=self.auj + timedelta(days=fin), statut=statut,
        )

    def _migrer(self):
        migration.reprendre_listes_publiees(apps, None)

    def test_liste_echue_devient_terminee(self):
        liste = self._liste(-20, -10)
        self._migrer()
        liste.refresh_from_db()
        self.assertEqual(liste.application, ServiceGarde.APPLICATION_TERMINEE)
        self.assertTrue(liste.activation_historique)
        self.assertEqual(liste.situation_affichee, "Terminée")

    def test_liste_en_cours_reste_active(self):
        liste = self._liste(-2, 5)
        self._migrer()
        liste.refresh_from_db()
        self.assertEqual(liste.application, ServiceGarde.APPLICATION_ACTIVE)
        self.assertEqual(liste.situation_affichee, "Active")

    def test_liste_future_applicable_mais_pas_affichee_active(self):
        liste = self._liste(5, 12)
        self._migrer()
        liste.refresh_from_db()
        self.assertEqual(liste.application, ServiceGarde.APPLICATION_ACTIVE)
        self.assertEqual(liste.situation_affichee, "Applicable à venir")

    def test_brouillon_et_proposee_non_touches_et_rien_supprime(self):
        brouillon = self._liste(1, 3, ServiceGarde.STATUT_BROUILLON)
        proposee = self._liste(1, 3, ServiceGarde.STATUT_PROPOSEE)
        self._liste(-2, 5)
        avant = ServiceGarde.objects.count()
        self._migrer()
        self.assertEqual(ServiceGarde.objects.count(), avant)
        for liste in (brouillon, proposee):
            liste.refresh_from_db()
            self.assertFalse(liste.activation_historique)
            self.assertIsNone(liste.prise_effet)

    def test_reprise_rejouable_sans_effet_supplementaire(self):
        liste = self._liste(-2, 5)
        self._migrer()
        liste.refresh_from_db()
        premiere = liste.prise_effet
        self._migrer()
        liste.refresh_from_db()
        self.assertEqual(liste.prise_effet, premiere)


class DiagnosticChevauchementsTests(TestCase):
    def test_diagnostic_signale_sans_rien_modifier(self):
        ship = Ship.objects.create(name="Bâtiment", code="BAT")
        service = Service.objects.create(ship=ship, name="Pont")
        marin = User.objects.create_user("marin", password="x")
        debut = timezone.now() + timedelta(days=1)
        garde = ServiceGarde.objects.create(
            service=service, fonction=ServiceFunctionChoice.objects.create(name="P"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=3), statut=ServiceGarde.STATUT_PUBLIEE,
        )
        quart = Quart.objects.create(
            service=service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=3), statut=Quart.STATUT_PUBLIEE,
        )
        CreneauServiceGarde.objects.create(service_garde=garde, poste="G", debut=debut, fin=debut + timedelta(hours=24), marin=marin)
        CreneauQuart.objects.create(quart=quart, poste="B", debut=debut + timedelta(hours=2), fin=debut + timedelta(hours=6), marin=marin)
        sortie = StringIO()
        call_command("analyser_chevauchements_mer_quai", stdout=sortie)
        self.assertIn("1 chevauchement(s)", sortie.getvalue())
        self.assertIn("aucune donnée modifiée", sortie.getvalue())
        self.assertEqual(CreneauQuart.objects.count() + CreneauServiceGarde.objects.count(), 2)
