"""Tests du context processor installations_notifications (matrix/context_processors.py).

Corrige un N+1 : le context processor récupérait le dernier relevé de vibration
et le dernier relevé d'isolement via .order_by('-date').first() sur des managers
déjà prefetch_related, ce qui cassait le cache de prefetch et déclenchait
2 requêtes supplémentaires par installation. Comme ce context processor est
enregistré globalement (matrix/settings.py, TEMPLATES > context_processors),
il s'exécutait ainsi sur CHAQUE page du site, pas seulement /installations/.

Le correctif utilise des requêtes groupées (installation_id__in=) — même pattern
que reports/services.py::_dernier_par_installation et le correctif déjà appliqué
sur assets/web_views.py::InstallationListView.get_context_data.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from assets.models import Installation, InstallationIsolationReading, InstallationVibrationReading
from matrix.context_processors import installations_notifications
from org.models import Sector, Service, Ship


class InstallationsNotificationsRequetesTests(TestCase):
    """Vérifie que le nombre de requêtes du context processor est borné, quel
    que soit le nombre d'installations (plus de N+1)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAVA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="marin", password="pass")

    def _creer_installations_en_retard(self, nombre):
        """Crée `nombre` installations avec un relevé de vibration et un relevé
        d'isolement anciens, pour que chacune déclenche une notification de
        vibration ET une notification d'isolement (échéances dépassées)."""
        today = timezone.localdate()
        installations = []
        for i in range(nombre):
            inst = Installation.objects.create(
                designation=f"Pompe {i}", ship=self.ship, service=self.service, sector=self.sector,
                vib_days_a=1, vib_days_b=1, vib_days_c=1, iso_periodicity="M",
            )
            # Relevé le plus ancien : ne doit jamais être retenu comme "dernier".
            InstallationVibrationReading.objects.create(
                installation=inst, date=today - timedelta(days=90), state="A",
            )
            InstallationVibrationReading.objects.create(
                installation=inst, date=today - timedelta(days=30), state="C",
            )
            InstallationIsolationReading.objects.create(
                installation=inst, date=today - timedelta(days=90), ohms=200,
            )
            InstallationIsolationReading.objects.create(
                installation=inst, date=today - timedelta(days=60), ohms=100,
            )
            installations.append(inst)
        return installations

    def _requetes_et_resultat(self, nombre_installations, utilisateur_connecte=True):
        self._creer_installations_en_retard(nombre_installations)
        request = self.factory.get("/")
        request.user = self.user if utilisateur_connecte else None
        with CaptureQueriesContext(connection) as queries:
            resultat = installations_notifications(request)
        return len(queries), resultat

    def test_nombre_de_requetes_ne_depend_pas_du_nombre_dinstallations(self):
        nb_requetes_1, resultat_1 = self._requetes_et_resultat(1)
        Installation.objects.all().delete()
        nb_requetes_10, resultat_10 = self._requetes_et_resultat(10)
        self.assertEqual(
            nb_requetes_1, nb_requetes_10,
            "Le nombre de requêtes ne doit pas dépendre du nombre d'installations (N+1)."
        )
        # 10 installations en retard -> 1 notification vibration + 1 notification
        # isolement par installation = 20 notifications.
        self.assertEqual(resultat_10["notifications_count"], 20)

    def test_dernier_releve_correctement_selectionne(self):
        """Le relevé le plus récent doit être retenu (pas un relevé plus ancien),
        exactement comme avec .order_by('-date').first() avant correctif."""
        installations = self._creer_installations_en_retard(1)
        inst = installations[0]
        request = self.factory.get("/")
        request.user = self.user
        resultat = installations_notifications(request)
        notif_vibration = next(
            n for n in resultat["notifications"] if n["title"] == f"Vibration — {inst.designation}"
        )
        # Le relevé retenu est celui d'il y a 30 j (état C), pas celui d'il y a 90 j (état A).
        echeance_attendue = timezone.localdate() - timedelta(days=30) + timedelta(days=inst.vib_days_c)
        self.assertIn(echeance_attendue.strftime("%d/%m/%Y"), notif_vibration["subtitle"])

    def test_pas_de_notification_sans_releve(self):
        Installation.objects.create(
            designation="Sans relevé", ship=self.ship, service=self.service, sector=self.sector,
        )
        request = self.factory.get("/")
        request.user = self.user
        resultat = installations_notifications(request)
        self.assertEqual(resultat["notifications_count"], 0)


class InstallationsNotificationsPagesTests(TestCase):
    """Le context processor est enregistré globalement : vérifie qu'il ne casse
    aucune vue, y compris des pages autres que /installations/."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAVA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.user = User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")

    def _creer_installations_avec_releves(self, nombre):
        today = timezone.localdate()
        for i in range(nombre):
            inst = Installation.objects.create(
                designation=f"Pompe {i}", ship=self.ship, service=self.service, sector=self.sector,
            )
            InstallationVibrationReading.objects.create(installation=inst, date=today, state="A")
            InstallationIsolationReading.objects.create(installation=inst, date=today, ohms=500)

    def test_page_accueil_fonctionne_avec_plusieurs_installations(self):
        self._creer_installations_avec_releves(5)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_page_installations_fonctionne_avec_plusieurs_installations(self):
        self._creer_installations_avec_releves(5)
        response = self.client.get("/installations/")
        self.assertEqual(response.status_code, 200)

    def test_page_recherche_fonctionne_avec_plusieurs_installations(self):
        self._creer_installations_avec_releves(5)
        response = self.client.get("/search/?q=Pompe")
        self.assertEqual(response.status_code, 200)
