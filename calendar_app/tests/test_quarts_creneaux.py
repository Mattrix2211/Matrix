"""Vérifie que les créneaux de quart/service de garde assignés à un marin
apparaissent dans SON calendrier personnel (calendar_app), au même titre que
ses autres événements déjà agrégés (maintenance, formation, personnel) — cf.
tâche Notion « Quarts/services : afficher les créneaux assignés dans le
calendrier personnel du marin ». Seules les listes déjà PUBLIÉES comptent :
une liste encore en BROUILLON reste une préparation interne au chef de
liste, jamais montrée au marin avant publication (cf. Quart.publier,
quarts/models.py)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from icalendar import Calendar

from org.models import Sector, Service, Ship
from quarts.models import CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde


class CreneauxCalendrierPersonnelTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Calendrier Quarts", code="CQT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.sector = Sector.objects.create(service=self.service, name="Manœuvre")

        self.marin = User.objects.create_user(username="marin_quart", password="pass")
        self.autre_marin = User.objects.create_user(username="autre_marin", password="pass")

        self.jour = timezone.localdate()
        self.debut = timezone.make_aware(
            timezone.datetime.combine(self.jour, timezone.datetime.min.time().replace(hour=8))
        )
        self.fin = self.debut + timedelta(hours=4)

        self.quart_publie = Quart.objects.create(
            sector=self.sector, date_debut=self.jour, date_fin=self.jour, statut=Quart.STATUT_PUBLIEE,
        )
        self.creneau_quart = CreneauQuart.objects.create(
            quart=self.quart_publie, poste="Barre", debut=self.debut, fin=self.fin, marin=self.marin,
        )

        self.garde_publiee = ServiceGarde.objects.create(
            sector=self.sector, date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_PUBLIEE,
        )
        self.creneau_garde = CreneauServiceGarde.objects.create(
            service_garde=self.garde_publiee, poste="Garde 24h", debut=self.debut, fin=self.fin, marin=self.marin,
        )

    # --- Cas normal : le marin affecté voit ses créneaux -------------------

    def test_calendar_events_affiche_le_creneau_de_quart_assigne(self):
        self.client.login(username="marin_quart", password="pass")
        url = reverse("calendar-events") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        events = resp.json()
        quart_events = [e for e in events if e["extendedProps"]["type"] == "quart"]
        self.assertEqual(len(quart_events), 1)
        self.assertIn("Barre", quart_events[0]["title"])
        self.assertEqual(quart_events[0]["id"], f"qrt-{self.creneau_quart.pk}")
        self.assertEqual(quart_events[0]["url"], f"/quarts/quart/{self.quart_publie.pk}/")
        self.assertFalse(quart_events[0]["editable"])

    def test_calendar_events_affiche_le_creneau_de_garde_assigne(self):
        self.client.login(username="marin_quart", password="pass")
        url = reverse("calendar-events") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        events = resp.json()
        garde_events = [e for e in events if e["extendedProps"]["type"] == "service_garde"]
        self.assertEqual(len(garde_events), 1)
        self.assertIn("Garde 24h", garde_events[0]["title"])
        self.assertEqual(garde_events[0]["id"], f"svc-{self.creneau_garde.pk}")
        self.assertEqual(garde_events[0]["url"], f"/quarts/garde/{self.garde_publiee.pk}/")

    def test_collect_events_affiche_les_creneaux_assignes(self):
        """Même agrégation côté contexte HTML de CalendarView (_collect_events)."""
        self.client.login(username="marin_quart", password="pass")
        url = reverse("calendar-index") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        events = resp.context["events"]
        types = [e["type"] for e in events]
        self.assertIn("quart", types)
        self.assertIn("service_garde", types)

    def test_ical_feed_inclut_les_creneaux_assignes(self):
        self.client.login(username="marin_quart", password="pass")
        resp = self.client.get(reverse("calendar-ical-my"))
        self.assertEqual(resp.status_code, 200)
        cal = Calendar.from_ical(resp.content)
        summaries = [str(c.get("summary")) for c in cal.walk() if c.name == "VEVENT"]
        self.assertIn("Quart: Barre", summaries)
        self.assertIn("Garde: Garde 24h", summaries)

    # --- Liste non publiée : ne doit PAS apparaître -------------------------

    def test_creneau_dune_liste_brouillon_najamais_affiche(self):
        quart_brouillon = Quart.objects.create(
            sector=self.sector, date_debut=self.jour, date_fin=self.jour, statut=Quart.STATUT_BROUILLON,
        )
        CreneauQuart.objects.create(
            quart=quart_brouillon, poste="Veille", debut=self.debut, fin=self.fin, marin=self.marin,
        )
        self.client.login(username="marin_quart", password="pass")
        url = reverse("calendar-events") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        events = resp.json()
        quart_events = [e for e in events if e["extendedProps"]["type"] == "quart"]
        # Seul le créneau déjà publié dans setUp doit apparaître, pas celui du
        # brouillon fraîchement créé.
        self.assertEqual(len(quart_events), 1)
        self.assertNotIn("Veille", quart_events[0]["title"])

    def test_creneau_dune_garde_brouillon_najamais_affiche_dans_lical(self):
        garde_brouillon = ServiceGarde.objects.create(
            sector=self.sector, date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_BROUILLON,
        )
        CreneauServiceGarde.objects.create(
            service_garde=garde_brouillon, poste="Permanence", debut=self.debut, fin=self.fin, marin=self.marin,
        )
        self.client.login(username="marin_quart", password="pass")
        resp = self.client.get(reverse("calendar-ical-my"))
        cal = Calendar.from_ical(resp.content)
        summaries = [str(c.get("summary")) for c in cal.walk() if c.name == "VEVENT"]
        self.assertNotIn("Garde: Permanence", summaries)

    # --- Marin sans créneau assigné : rien n'apparaît pour lui --------------

    def test_marin_sans_creneau_assigne_ne_voit_rien(self):
        self.client.login(username="autre_marin", password="pass")
        url = reverse("calendar-events") + (
            f"?date={self.jour.isoformat()}&view=day&user={self.autre_marin.pk}"
        )
        resp = self.client.get(url)
        events = resp.json()
        creneaux_events = [e for e in events if e["extendedProps"]["type"] in ("quart", "service_garde")]
        self.assertEqual(len(creneaux_events), 0)

    def test_filtre_utilisateur_najamais_le_creneau_dun_autre_marin(self):
        """Le filtre "Utilisateur" du calendrier ne doit renvoyer que les
        créneaux du marin sélectionné, jamais ceux d'un autre."""
        self.client.login(username="marin_quart", password="pass")
        url = reverse("calendar-events") + (
            f"?date={self.jour.isoformat()}&view=day&user={self.autre_marin.pk}"
        )
        resp = self.client.get(url)
        events = resp.json()
        quart_events = [e for e in events if e["extendedProps"]["type"] == "quart"]
        self.assertEqual(len(quart_events), 0)

    def test_creneau_sans_marin_affecte_najamais_affiche(self):
        """Un créneau pas encore affecté (marin=None) n'est pas une
        affectation personnelle : il ne doit jamais apparaître sur le
        calendrier de qui que ce soit."""
        CreneauQuart.objects.create(
            quart=self.quart_publie, poste="Passerelle", debut=self.debut, fin=self.fin, marin=None,
        )
        self.client.login(username="marin_quart", password="pass")
        url = reverse("calendar-events") + f"?date={self.jour.isoformat()}&view=day"
        resp = self.client.get(url)
        events = resp.json()
        titres = [e["title"] for e in events if e["extendedProps"]["type"] == "quart"]
        self.assertNotIn("⏱ Passerelle", titres)

    # --- Digest quotidien « Ma journée » : mêmes créneaux, même agrégation --

    def test_evenements_utilisateur_jour_inclut_les_creneaux(self):
        from calendar_app.views import evenements_utilisateur_jour

        evenements = evenements_utilisateur_jour(self.marin, self.jour)
        self.assertEqual(len(evenements["creneaux"]), 2)
