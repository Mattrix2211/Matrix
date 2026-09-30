"""Double équipage, tranche 5 : notifications, préférences de l'équipage à terre,
calendrier d'équipe et rondes par équipage ; un navire à équipage unique se
comporte exactement comme avant."""
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import Installation, InstallationVibrationReading
from calendar_app.evenements_sources import _creneaux_garde_assignes
from notifications.models import Notification
from org.models import Sector, Service, Ship
from quarts.tests.test_double_equipage import DoubleEquipageBase, marin
from rondes.models import Ronde
from rondes.services import rondes_du_marin


class TranchePreferencesEtVuesTests(DoubleEquipageBase):
    def test_equipage_a_terre_regle_ses_preferences_de_notification(self):
        self.client.force_login(self.a_rouge)
        reponse = self.client.post(reverse("settings"), {
            "action": "update_notification_time", "notification_time": "07:30", "notification_time_soir": "18:45",
        })
        self.assertEqual(reponse.status_code, 302)
        self.a_rouge.profile.refresh_from_db()
        self.assertEqual(self.a_rouge.profile.notification_time.strftime("%H:%M"), "07:30")

    def test_equipage_a_terre_ne_peut_rien_d_autre_dans_parametre(self):
        self.client.force_login(self.a_rouge)
        self.client.post(reverse("settings"), {"action": "add_grade", "name": "Grade interdit"})
        from accounts.models import GradeChoice
        self.assertFalse(GradeChoice.objects.filter(name="Grade interdit").exists())

    def test_calendrier_d_equipe_borne_par_equipage(self):
        garde = self.garde(self.cdt_bleu, ship=self.ship)
        c_bleu = self.creneau(garde, self.a_bleu)
        c_rouge = self.creneau(garde, self.a_rouge, jours=6)
        debut, fin = self.aujourdhui, self.aujourdhui + timedelta(days=30)
        vus = set(_creneaux_garde_assignes(debut, fin, None, self.a_bleu))
        self.assertEqual(vus, {c_bleu})
        self.assertNotIn(c_rouge, vus)

    def test_ronde_non_assignee_reservee_a_l_equipage_a_bord(self):
        ronde = Ronde.objects.create(nom="Ronde pont", ship=self.ship, date_prevue=self.aujourdhui)
        self.assertIn(ronde, rondes_du_marin(self.a_bleu))
        self.assertNotIn(ronde, rondes_du_marin(self.a_rouge))


class NotificationsEcheancesParEquipageTests(DoubleEquipageBase):
    def _installation(self, ship, service, secteur):
        installation = Installation.objects.create(
            designation="Propulseur", ship=ship, service=service, sector=secteur, vib_days_a=10,
        )
        InstallationVibrationReading.objects.create(
            installation=installation, date=self.aujourdhui - timedelta(days=20), state="A",
        )
        return installation

    def _heure_de_notification(self, *marins):
        maintenant = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
        for m in marins:
            m.profile.notification_time = maintenant
            m.profile.save()

    def test_alerte_installation_seulement_pour_l_equipage_a_bord(self):
        self._installation(self.ship, self.service_bleu, self.secteur_bleu)
        self._heure_de_notification(self.a_bleu, self.a_rouge)
        call_command("generate_installation_notifications")
        self.assertTrue(Notification.objects.filter(user=self.a_bleu).exists())
        self.assertFalse(Notification.objects.filter(user=self.a_rouge).exists())

    def test_apres_la_releve_l_equipage_montant_est_alerte(self):
        self._installation(self.ship, self.service_bleu, self.secteur_bleu)
        self.ship.equipage_a_bord = self.rouge
        self.ship.save()
        self._heure_de_notification(self.a_bleu, self.a_rouge)
        call_command("generate_installation_notifications")
        self.assertTrue(Notification.objects.filter(user=self.a_rouge).exists())
        self.assertFalse(Notification.objects.filter(user=self.a_bleu).exists())

    def test_equipage_unique_inchange(self):
        navire = Ship.objects.create(name="Unique", code="UN")
        service = Service.objects.create(ship=navire, name="Pont")
        secteur = Sector.objects.create(service=service, name="Manœuvre")
        equipier = marin("unique1", "EQUIPIER", navire, None, secteur)
        self._installation(navire, service, secteur)
        self._heure_de_notification(equipier)
        call_command("generate_installation_notifications")
        self.assertTrue(Notification.objects.filter(user=equipier).exists())


class CouvertureQaTranche5Tests(DoubleEquipageBase):
    """Parcours complémentaires (QA) : absences, quarts, équipage unique, maintenance."""

    def test_absences_et_quarts_d_equipe_bornes_par_equipage(self):
        from absences.models import Absence
        from calendar_app.evenements_sources import _absences_periode, _creneaux_quart_assignes
        champs = {f.name for f in Absence._meta.get_fields()}
        self.assertIn("marin", champs)
        debut, fin = self.aujourdhui - timedelta(days=1), self.aujourdhui + timedelta(days=30)
        self.assertEqual(set(_creneaux_quart_assignes(debut, fin, None, self.a_rouge)), set())
        self.assertEqual(set(_absences_periode(debut, fin, None, self.a_rouge)), set())

    def test_equipage_a_terre_voit_uniquement_son_equipage_dans_le_calendrier(self):
        garde = self.garde(self.cdt_bleu, ship=self.ship)
        c_bleu = self.creneau(garde, self.a_bleu)
        c_rouge = self.creneau(garde, self.a_rouge, jours=6)
        debut, fin = self.aujourdhui, self.aujourdhui + timedelta(days=30)
        self.assertIn(c_rouge, set(_creneaux_garde_assignes(debut, fin, None, self.a_rouge)))
        self.assertNotIn(c_bleu, set(_creneaux_garde_assignes(debut, fin, None, self.a_rouge)))

    def test_equipage_unique_calendrier_et_rondes_inchanges(self):
        navire = Ship.objects.create(name="Unique2", code="U2")
        service = Service.objects.create(ship=navire, name="Pont")
        secteur = Sector.objects.create(service=service, name="Manœuvre")
        a = marin("uniq_a", "EQUIPIER", navire, None, secteur)
        b = marin("uniq_b", "EQUIPIER", navire, None, secteur)
        garde = self.garde(a, ship=navire)
        c = self.creneau(garde, b)
        debut, fin = self.aujourdhui, self.aujourdhui + timedelta(days=30)
        self.assertIn(c, set(_creneaux_garde_assignes(debut, fin, None, a)))
        ronde = Ronde.objects.create(nom="Ronde", ship=navire, date_prevue=self.aujourdhui)
        self.assertIn(ronde, rondes_du_marin(a))

    def test_equipage_unique_preferences_de_notification_inchangees(self):
        navire = Ship.objects.create(name="Unique3", code="U3")
        service = Service.objects.create(ship=navire, name="Pont")
        secteur = Sector.objects.create(service=service, name="Manœuvre")
        a = marin("uniq_c", "EQUIPIER", navire, None, secteur)
        self.client.force_login(a)
        reponse = self.client.post(reverse("settings"), {
            "action": "update_notification_time", "notification_time": "06:15", "notification_time_soir": "19:00",
        })
        self.assertEqual(reponse.status_code, 302)
        a.profile.refresh_from_db()
        self.assertEqual(a.profile.notification_time.strftime("%H:%M"), "06:15")

    def test_action_inconnue_de_parametre_refusee_a_l_equipage_a_terre(self):
        self.client.force_login(self.a_rouge)
        reponse = self.client.post(reverse("settings"), {"action": "add_grade", "name": "X"})
        self.assertIn(reponse.status_code, (302, 403))
        if reponse.status_code == 302:
            suite = self.client.get(reponse["Location"])
            self.assertContains(suite, "lecture seule")
