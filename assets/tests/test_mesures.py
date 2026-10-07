"""Heures de marche (compteur total, depuis la dernière visite, heures par mois),
dérive d'isolement et formatage des mesures."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.mesures import (
    compteur_total, formater_heures, formater_nombre, formater_ohms, heures_par_releve, resume_heures,
)
from assets.models import (
    Installation, InstallationHourReading, InstallationIsolationReading, InstallationMaintenance, ModeDeclenchement,
)
from assets.trend import jours_avant_franchissement_seuil
from maintenance.models import MaintenanceOccurrence, mettre_a_jour_echeance_installation
from org.models import Sector, Service, Ship


class _Releve:
    def __init__(self, jour, heures, visite=False):
        self.date, self.hours, self.is_visit = jour, Decimal(heures), visite


class CalculHeuresTests(SimpleTestCase):
    def test_total_est_le_plus_grand_compteur_pas_la_somme(self):
        releves = [_Releve(date(2026, 1, 1), 4000), _Releve(date(2026, 2, 1), 4200), _Releve(date(2026, 3, 1), 4715)]
        self.assertEqual(compteur_total(releves), Decimal(4715))
        self.assertIsNone(compteur_total([]))

    def test_depuis_derniere_visite_avec_releve_visite(self):
        releves = [_Releve(date(2026, 1, 1), 4000, True), _Releve(date(2026, 3, 1), 4715)]
        r = resume_heures(releves)
        self.assertEqual((r["total"], r["a_la_visite"], r["depuis_visite"]), (4715, 4000, 715))

    def test_depuis_derniere_visite_avec_execution_de_maintenance(self):
        releves = [_Releve(date(2026, 1, 1), 4000, True), _Releve(date(2026, 3, 1), 4715)]
        r = resume_heures(releves, [Decimal(4500)])
        self.assertEqual(r["depuis_visite"], 215)

    def test_sans_visite_connue_depuis_visite_egale_total(self):
        r = resume_heures([_Releve(date(2026, 1, 1), 300)])
        self.assertEqual((r["total"], r["depuis_visite"]), (300, 300))

    def test_sans_releve(self):
        self.assertEqual(resume_heures([]), {"total": None, "a_la_visite": None, "depuis_visite": None})

    def test_heures_par_releve_est_la_difference_des_compteurs(self):
        releves = [_Releve(date(2026, 3, 1), 4300), _Releve(date(2026, 1, 1), 4000), _Releve(date(2026, 2, 1), 4120)]
        self.assertEqual(
            heures_par_releve(releves), [(date(2026, 2, 1), Decimal(120)), (date(2026, 3, 1), Decimal(180))]
        )


class FormatageTests(SimpleTestCase):
    def test_heures_avec_separateur_de_milliers(self):
        self.assertEqual(formater_heures(Decimal("4715.00")), "4 715 h".replace(" ", formater_nombre(1000)[1]))

    def test_ohms_unites_lisibles(self):
        self.assertEqual(formater_ohms(Decimal("560000.00")), "560 kΩ")
        self.assertEqual(formater_ohms(2400000), "2,4 MΩ")
        self.assertEqual(formater_ohms(750), "750 Ω")


class DeriveIsolementTests(SimpleTestCase):
    def test_derive_du_jeu_de_demo_detectee(self):
        # 2,4 MΩ à 560 kΩ en 6 mois, seuil 500 kΩ : la droite ajustée passe déjà sous
        # le seuil avant la dernière mesure, la dérive doit quand même être signalée.
        valeurs = [2400000, 1900000, 1500000, 1100000, 850000, 680000, 560000]
        fin = date(2026, 6, 1)
        releves = [(fin - timedelta(days=30 * m), v) for m, v in zip(range(6, -1, -1), valeurs)]
        jours = jours_avant_franchissement_seuil(releves, 500000, sens="BAISSE")
        self.assertIsNotNone(jours)
        self.assertGreater(jours, 0)


class _Base(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire", code="NAV-H")
        service = Service.objects.create(ship=self.ship, name="Srv")
        sector = Sector.objects.create(service=service, name="Sec")
        self.inst = Installation.objects.create(designation="GE", ship=self.ship, service=service, sector=sector)

    def releve(self, jour, heures, visite=False):
        return InstallationHourReading.objects.create(installation=self.inst, date=jour, hours=heures, is_visit=visite)

    def maintenance(self, **kw):
        return InstallationMaintenance.objects.create(
            installation=self.inst, periodicity="500 h", title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR, seuil_heures=500, **kw,
        )


class EcheanceHeuresTests(_Base):
    def test_declenchee_quand_heures_depuis_visite_atteignent_le_seuil(self):
        m = self.maintenance(derniere_echeance_heures=4200)
        self.releve(date(2026, 1, 1), 4500)
        self.releve(date(2026, 2, 1), 4700)
        call_command("generate_installation_occurrences")
        self.assertTrue(MaintenanceOccurrence.objects.filter(installation_maintenance=m).exists())

    def test_non_declenchee_malgre_un_gros_compteur_total(self):
        # Compteur total 4715 h mais seulement 15 h depuis la dernière visite.
        m = self.maintenance(derniere_echeance_heures=4700)
        self.releve(date(2026, 1, 1), 4000)
        self.releve(date(2026, 2, 1), 4715)
        call_command("generate_installation_occurrences")
        self.assertFalse(MaintenanceOccurrence.objects.filter(installation_maintenance=m).exists())

    def test_sans_reference_utilise_le_releve_marque_visite(self):
        m = self.maintenance()
        self.releve(date(2026, 1, 1), 4000, visite=True)
        self.releve(date(2026, 2, 1), 4300)
        call_command("generate_installation_occurrences")
        self.assertFalse(MaintenanceOccurrence.objects.filter(installation_maintenance=m).exists())
        self.releve(date(2026, 3, 1), 4500)
        call_command("generate_installation_occurrences")
        self.assertTrue(MaintenanceOccurrence.objects.filter(installation_maintenance=m).exists())

    def test_fin_de_maintenance_reference_le_compteur_total(self):
        m = self.maintenance(derniere_echeance_heures=0)
        self.releve(date(2026, 2, 1), 4715)
        self.releve(date(2026, 1, 1), 4000)
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=m, scheduled_for=timezone.localdate(), status="DONE",
        )
        mettre_a_jour_echeance_installation(occ)
        m.refresh_from_db()
        self.assertEqual(m.derniere_echeance_heures, Decimal("4715.00"))


class FicheHeuresTests(_Base):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"ship": self.ship})
        self.client.login(username="chef", password="pass")

    def test_contexte_total_depuis_visite_et_graphique_periodique(self):
        aujourdhui = timezone.localdate()
        self.releve(aujourdhui - timedelta(days=70), 4000, visite=True)
        self.releve(aujourdhui - timedelta(days=35), 4300)
        self.releve(aujourdhui, 4715)
        ctx = self.client.get(reverse("installation-detail", args=[self.inst.pk])).context
        self.assertEqual(ctx["hours_total"], Decimal("4715"))
        self.assertEqual(ctx["hours_last_visit"], Decimal("715"))
        self.assertEqual(ctx["hours_compteur_visite"], Decimal("4000"))
        # Jamais la somme des compteurs : uniquement les écarts entre relevés.
        self.assertEqual(sum(ctx["hours_month_values"]), 715)

    def test_indicateur_en_tete_affiche_total_et_depuis_visite(self):
        self.releve(date(2026, 1, 1), 4000, visite=True)
        self.releve(date(2026, 2, 1), 4715)
        ctx = self.client.get(reverse("installation-detail", args=[self.inst.pk])).context
        indicateur = next(i for i in ctx["indicateurs_fiche"] if i["libelle"] == "Heures de marche")
        self.assertEqual(indicateur["valeur"], formater_nombre(4715))
        self.assertIn("depuis la dernière visite", indicateur["detail"])

    def test_isolement_formate_dans_lindicateur(self):
        InstallationIsolationReading.objects.create(installation=self.inst, date=date(2026, 1, 1), ohms=Decimal("560000"))
        ctx = self.client.get(reverse("installation-detail", args=[self.inst.pk])).context
        indicateur = next(i for i in ctx["indicateurs_fiche"] if i["libelle"] == "Dernier isolement")
        self.assertEqual(indicateur["valeur"], "560 kΩ")
