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

    def test_creation_evenement_personnel_avec_date_fin(self):
        reponse = self.client.post(reverse("calendar-personal-save"), {
            "title": "Réunion de bord",
            "starts_at": f"{self.aujourdhui.isoformat()}T09:00",
            "ends_at": f"{self.aujourdhui.isoformat()}T10:30",
        })
        self.assertRedirects(reponse, reverse("calendar-index"))
        evenement = PersonalEvent.objects.get()
        self.assertIsNotNone(evenement.ends_at)
        self.assertEqual(timezone.localtime(evenement.ends_at).strftime("%H:%M"), "10:30")

    def test_creation_evenement_personnel_sans_fin_applique_une_duree_par_defaut(self):
        """Le champ « Heure de fin » du formulaire rapide est facultatif :
        une durée par défaut d'une heure est appliquée côté serveur si
        l'utilisateur ne la renseigne pas (comme le calendrier Apple), pour
        que l'événement dispose toujours d'une durée affichable sur le
        calendrier, sans jamais bloquer la création rapide."""
        reponse = self.client.post(reverse("calendar-personal-save"), {
            "title": "Pause café",
            "starts_at": f"{self.aujourdhui.isoformat()}T15:00",
        })
        self.assertRedirects(reponse, reverse("calendar-index"))
        evenement = PersonalEvent.objects.get()
        self.assertIsNotNone(evenement.ends_at)
        self.assertEqual(evenement.ends_at, evenement.starts_at + timezone.timedelta(hours=1))

    def test_date_fin_anterieure_a_date_debut_refusee(self):
        """Garde-fou côté serveur : même si le JS du formulaire recale
        automatiquement la fin quand le début la dépasse, on ne fait jamais
        confiance au client seul — une fin antérieure au début forcée malgré
        tout est rejetée avec un message français clair."""
        reponse = self.client.post(reverse("calendar-personal-save"), {
            "title": "Réunion de bord",
            "starts_at": f"{self.aujourdhui.isoformat()}T10:00",
            "ends_at": f"{self.aujourdhui.isoformat()}T09:00",
        }, follow=True)
        self.assertRedirects(reponse, reverse("calendar-index"))
        self.assertEqual(PersonalEvent.objects.count(), 0)
        messages_affiches = [str(m) for m in reponse.context["messages"]]
        self.assertIn("La date de fin doit être postérieure à la date de début.", messages_affiches)

    def test_evenement_personnel_avec_fin_expose_end_dans_calendar_events(self):
        PersonalEvent.objects.create(
            owner=self.marin, title="Avec durée",
            starts_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())),
            ends_at=timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time()))
            + timezone.timedelta(hours=2),
        )
        url = reverse("calendar-events") + f"?date={self.aujourdhui.isoformat()}&view=day"
        reponse = self.client.get(url)
        perso = [e for e in reponse.json() if e["extendedProps"]["type"] == "personal"]
        self.assertEqual(len(perso), 1)
        self.assertNotEqual(perso[0]["start"], perso[0]["end"])

    def test_redimensionnement_evenement_personnel_persiste_la_date_de_fin(self):
        debut = timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time()))
        evenement = PersonalEvent.objects.create(owner=self.marin, title="À redimensionner", starts_at=debut)
        nouvelle_fin = debut + timezone.timedelta(hours=1, minutes=30)
        reponse = self.client.post(reverse("calendar-event-move"), {
            "type": "personal",
            "id": evenement.id,
            "date": debut.isoformat(),
            "end_date": nouvelle_fin.isoformat(),
        })
        self.assertEqual(reponse.status_code, 200)
        evenement.refresh_from_db()
        self.assertIsNotNone(evenement.ends_at)
        self.assertEqual(timezone.localtime(evenement.ends_at), timezone.localtime(nouvelle_fin))

    def test_redimensionnement_avec_fin_avant_debut_refuse(self):
        debut = timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time()))
        evenement = PersonalEvent.objects.create(owner=self.marin, title="Protégé", starts_at=debut)
        fin_invalide = debut - timezone.timedelta(hours=1)
        reponse = self.client.post(reverse("calendar-event-move"), {
            "type": "personal",
            "id": evenement.id,
            "date": debut.isoformat(),
            "end_date": fin_invalide.isoformat(),
        })
        self.assertEqual(reponse.status_code, 400)
        evenement.refresh_from_db()
        self.assertIsNone(evenement.ends_at)

    def test_deplacement_conserve_la_duree_existante(self):
        """Régression QA : un déplacement par glisser (eventDrop, sans
        end_date) d'un événement qui a déjà une date de fin ne doit pas
        laisser ends_at figé sur son ancienne valeur — sinon il finit
        antérieur à starts_at, une incohérence persistée en base sans
        aucune erreur renvoyée."""
        debut = timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())) \
            + timezone.timedelta(hours=9)
        fin = debut + timezone.timedelta(hours=1, minutes=30)
        evenement = PersonalEvent.objects.create(
            owner=self.marin, title="Avec durée à déplacer", starts_at=debut, ends_at=fin,
        )
        nouveau_debut = debut + timezone.timedelta(days=2)
        reponse = self.client.post(reverse("calendar-event-move"), {
            "type": "personal",
            "id": evenement.id,
            "date": nouveau_debut.isoformat(),
        })
        self.assertEqual(reponse.status_code, 200)
        evenement.refresh_from_db()
        self.assertEqual(evenement.starts_at, nouveau_debut)
        # La durée (1h30) doit être conservée, pas la date de fin d'origine.
        self.assertEqual(evenement.ends_at, nouveau_debut + timezone.timedelta(hours=1, minutes=30))
        self.assertGreater(evenement.ends_at, evenement.starts_at)

    def test_modification_heure_debut_via_modale_conserve_la_duree(self):
        """Régression QA : la modale d'édition ne propose pas de champ de
        date de fin — modifier uniquement l'heure de début d'un événement
        qui a déjà une durée ne doit pas laisser ends_at figé sur son
        ancienne valeur."""
        debut = timezone.make_aware(timezone.datetime.combine(self.aujourdhui, timezone.datetime.min.time())) \
            + timezone.timedelta(hours=9)
        fin = debut + timezone.timedelta(hours=2)
        evenement = PersonalEvent.objects.create(
            owner=self.marin, title="Avec durée à éditer", starts_at=debut, ends_at=fin,
        )
        nouvelle_heure = debut + timezone.timedelta(hours=3)
        self.client.post(reverse("calendar-personal-save"), {
            "id": evenement.id,
            "title": evenement.title,
            "starts_at": nouvelle_heure.strftime("%Y-%m-%dT%H:%M"),
            "note": "",
        })
        evenement.refresh_from_db()
        self.assertEqual(evenement.starts_at, nouvelle_heure)
        # La durée (2h) doit être conservée, pas la date de fin d'origine.
        self.assertEqual(evenement.ends_at, nouvelle_heure + timezone.timedelta(hours=2))
        self.assertGreater(evenement.ends_at, evenement.starts_at)

    def test_commentaires_dev_calendrier_non_affiches_en_clair(self):
        """Régression : deux commentaires {# ... #} multi-lignes de
        calendar/index.html (bloc « Ajout libre » et note sur la bibliothèque
        FullCalendar auto-hébergée) s'affichaient en clair, faute d'être
        invisibles avec {% comment %}...{% endcomment %}."""
        reponse = self.client.get(reverse("calendar-index"))
        self.assertNotContains(reponse, "Ajout libre d'un événement personnel")
        self.assertNotContains(reponse, "Bibliothèque auto-hébergée — aucune dépendance CDN")
