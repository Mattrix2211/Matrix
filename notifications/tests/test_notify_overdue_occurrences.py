from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from notifications.models import Notification
from notifications.tasks import notify_overdue_occurrences
from org.models import Sector, Service, Ship


class NotifyOverdueOccurrencesTests(TestCase):
    def setUp(self):
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        asset_type = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=ship, service=service, sector=sector
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Plan A", every_n_days=30
        )
        self.users = [
            User.objects.create_user(username=f"marin{i}", password="pass") for i in range(3)
        ]

    def _creer_occurrences_en_retard(self, nombre):
        occurrences = []
        for _ in range(nombre):
            occ = MaintenanceOccurrence.objects.create(
                plan=self.plan,
                asset=self.asset,
                scheduled_for=timezone.now().date(),
                status="OVERDUE",
            )
            occ.assignees.set(self.users)
            occurrences.append(occ)
        return occurrences

    def test_notifications_creees_pour_chaque_destinataire(self):
        occurrences = self._creer_occurrences_en_retard(5)

        notify_overdue_occurrences()

        for occ in occurrences:
            for user in self.users:
                self.assertTrue(
                    Notification.objects.filter(
                        user=user, verb__icontains=str(occ.id)
                    ).exists(),
                    f"Notification attendue pour {user.username} sur l'occurrence {occ.id}",
                )
        self.assertEqual(Notification.objects.count(), len(occurrences) * len(self.users))

    def test_nombre_de_requetes_ne_multiplie_pas_par_le_nombre_doccurrences(self):
        # Avant correction : occ.assignees.all() déclenchait une requête M2M par
        # occurrence en retard (N+1). Avec prefetch_related('assignees'), une seule
        # requête supplémentaire suffit quel que soit le nombre d'occurrences.
        #
        # Les notifications sont pré-créées pour que get_or_create() se résolve par
        # un simple SELECT (pas d'INSERT), afin d'isoler le coût de la lecture des
        # occurrences/assignees de celui, attendu et linéaire, de la création des
        # notifications elles-mêmes.
        occurrences_5 = self._creer_occurrences_en_retard(5)
        for occ in occurrences_5:
            for user in self.users:
                Notification.objects.create(user=user, verb=f"Occurrence en retard: {occ.id}")

        with CaptureQueriesContext(connection) as ctx:
            notify_overdue_occurrences()
        requetes_pour_5 = len(ctx.captured_queries)

        occurrences_15 = self._creer_occurrences_en_retard(10)  # total 15 occurrences en retard
        for occ in occurrences_15:
            for user in self.users:
                Notification.objects.create(user=user, verb=f"Occurrence en retard: {occ.id}")

        with CaptureQueriesContext(connection) as ctx2:
            notify_overdue_occurrences()
        requetes_pour_15 = len(ctx2.captured_queries)

        # Seules les requêtes de vérification des notifications (une par couple
        # occurrence/destinataire, ici +10*3=30) doivent expliquer l'écart : le
        # coût de lecture des occurrences et de leurs destinataires reste constant.
        self.assertEqual(requetes_pour_15 - requetes_pour_5, 30)
