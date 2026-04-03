from django.test import TestCase
from django.utils import timezone
from org.models import Ship, Service, Sector
from training.models import TrainingCourse, TrainingRecord
from django.contrib.auth.models import User

class TrainingExpiryTests(TestCase):
    def setUp(self):
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        self.sector = Sector.objects.create(service=service, name="Elec")
        self.user = User.objects.create_user(username="u", password="p")

    def test_compute_expiry(self):
        course = TrainingCourse.objects.create(sector=self.sector, title="Sécurité", validity_days=365)
        completed = timezone.localdate()
        expires = TrainingRecord.compute_expiry(completed, course.validity_days)
        self.assertEqual(expires, completed + timezone.timedelta(days=365))
