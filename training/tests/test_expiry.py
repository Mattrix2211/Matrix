from django.test import TestCase
from django.utils import timezone
from training.models import TrainingCourse, TrainingRecord
from django.contrib.auth.models import User

class TrainingExpiryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")

    def test_compute_expiry(self):
        course = TrainingCourse.objects.create(title="Sécurité", validity_days=365)
        completed = timezone.localdate()
        expires = TrainingRecord.compute_expiry(completed, course.validity_days)
        self.assertEqual(expires, completed + timezone.timedelta(days=365))
