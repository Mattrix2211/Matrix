"""Vérifie l'ajout manuel libre d'événements personnels au calendrier : un
marin peut créer/modifier/supprimer son propre événement, il apparaît dans
son calendrier (calendar-events et calendar-index) et reste invisible pour
les autres utilisateurs."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import PersonalEvent


class PersonalEventTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin", password="pass")
        self.autre_marin = User.objects.create_user(username="autre", password="pass")
        self.client.login(username="marin", password="pass")
        self.aujourdhui = timezone.localdate()

    def test_creation_evenement_personnel(self):
        reponse = self.client.post(reverse("calendar-personal-save"), {
            "title": "Récupérer le linge à la buanderie",
            "starts_at": f"{self.aujourdhui.isoformat()}T14:00",
            "note": "Ne pas oublier",
        })
        self.assertRedirects(reponse, reverse("calendar-index"))
        self.assertEqual(PersonalEvent.objects.count(), 1)
        evenement = PersonalEvent.objects.get()
        self.assertEqual(evenement.owner, self.marin)
        self.assertEqual(evenement.title, "Récupérer le linge à la buanderie")

    def test_titre_et_date_obligatoires(self):
        reponse = self.client.post(reverse("calendar-personal-save"), {"title": "", "starts_at": ""})
        self.assertRedirects(reponse, reverse("calendar-index"))
        self.assertEqual(PersonalEvent.objects.count(), 0)

    def test_modification_evenement_personnel(self):
        evenement = PersonalEvent.objects.create(
            owner=self.marin, title="Ancien titre",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        self.client.post(reverse("calendar-personal-save"), {
            "id": evenement.id,
            "title": "Nouveau titre",
            "starts_at": f"{self.aujourdhui.isoformat()}T09:30",
            "note": "",
        })
        evenement.refresh_from_db()
        self.assertEqual(evenement.title, "Nouveau titre")

    def test_impossible_de_modifier_evenement_dun_autre(self):
        evenement = PersonalEvent.objects.create(
            owner=self.autre_marin, title="Événement d'un autre",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        reponse = self.client.post(reverse("calendar-personal-save"), {
            "id": evenement.id,
            "title": "Tentative de vol",
            "starts_at": f"{self.aujourdhui.isoformat()}T09:30",
        })
        self.assertEqual(reponse.status_code, 404)
        evenement.refresh_from_db()
        self.assertEqual(evenement.title, "Événement d'un autre")

    def test_suppression_evenement_personnel(self):
        evenement = PersonalEvent.objects.create(
            owner=self.marin, title="À supprimer",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        reponse = self.client.post(reverse("calendar-personal-delete", args=[evenement.id]))
        self.assertRedirects(reponse, reverse("calendar-index"))
        self.assertFalse(PersonalEvent.objects.filter(pk=evenement.id).exists())

    def test_impossible_de_supprimer_evenement_dun_autre(self):
        evenement = PersonalEvent.objects.create(
            owner=self.autre_marin, title="Protégé",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        reponse = self.client.post(reverse("calendar-personal-delete", args=[evenement.id]))
        self.assertEqual(reponse.status_code, 404)
        self.assertTrue(PersonalEvent.objects.filter(pk=evenement.id).exists())

    def test_evenement_personnel_visible_dans_calendar_events(self):
        PersonalEvent.objects.create(
            owner=self.marin, title="Rappel test",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        url = reverse("calendar-events") + f"?date={self.aujourdhui.isoformat()}&view=day"
        reponse = self.client.get(url)
        evenements = reponse.json()
        perso = [e for e in evenements if e["extendedProps"]["type"] == "personal"]
        self.assertEqual(len(perso), 1)
        self.assertIn("Rappel test", perso[0]["title"])

    def test_evenement_personnel_invisible_pour_un_autre_utilisateur(self):
        PersonalEvent.objects.create(
            owner=self.marin, title="Rappel privé",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        self.client.logout()
        self.client.login(username="autre", password="pass")
        url = reverse("calendar-events") + f"?date={self.aujourdhui.isoformat()}&view=day"
        reponse = self.client.get(url)
        evenements = reponse.json()
        perso = [e for e in evenements if e["extendedProps"]["type"] == "personal"]
        self.assertEqual(len(perso), 0)

    def test_evenement_personnel_visible_dans_calendar_index(self):
        PersonalEvent.objects.create(
            owner=self.marin, title="Rappel index",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        url = reverse("calendar-index") + f"?date={self.aujourdhui.isoformat()}&view=day"
        reponse = self.client.get(url)
        evenements = reponse.context["events"]
        perso = [e for e in evenements if e["type"] == "personal"]
        self.assertEqual(len(perso), 1)
        self.assertIn("Rappel index", perso[0]["title"])

    def test_deplacement_evenement_personnel(self):
        evenement = PersonalEvent.objects.create(
            owner=self.marin, title="À déplacer",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        nouvelle_date = self.aujourdhui + timezone.timedelta(days=3)
        reponse = self.client.post(reverse("calendar-event-move"), {
            "type": "personal",
            "id": evenement.id,
            "date": f"{nouvelle_date.isoformat()}T12:00:00",
        })
        self.assertEqual(reponse.status_code, 200)
        evenement.refresh_from_db()
        self.assertEqual(timezone.localtime(evenement.starts_at).date(), nouvelle_date)

    def test_deplacement_evenement_dun_autre_refuse(self):
        evenement = PersonalEvent.objects.create(
            owner=self.autre_marin, title="Protégé du déplacement",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
        )
        reponse = self.client.post(reverse("calendar-event-move"), {
            "type": "personal",
            "id": evenement.id,
            "date": f"{self.aujourdhui.isoformat()}T00:00:00",
        })
        self.assertEqual(reponse.status_code, 403)

    def test_commentaires_dev_calendrier_non_affiches_en_clair(self):
        """Régression : deux commentaires {# ... #} multi-lignes de
        calendar/index.html (bloc « Ajout libre » et note sur la bibliothèque
        FullCalendar auto-hébergée) s'affichaient en clair, faute d'être
        invisibles avec {% comment %}...{% endcomment %}."""
        reponse = self.client.get(reverse("calendar-index"))
        self.assertNotContains(reponse, "Ajout libre d'un événement personnel")
        self.assertNotContains(reponse, "Bibliothèque auto-hébergée — aucune dépendance CDN")
