"""Jeu de démonstration métier : fiches de maintenance complètes, roulements de quart, fraction de service à quai."""
from collections import Counter
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import InstallationMaintenance
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence
from quarts.models import (
    CreneauQuart,
    CreneauServiceGarde,
    FeuilleService,
    Quart,
    ServiceGarde,
    peut_lire_feuille_service,
    peut_rediger_feuille_service,
    personnel_du_jour,
)


class DonneesDemoMetierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.jour = timezone.localdate()

    def _marin(self, nom):
        return User.objects.get(username=nom)

    def test_preparation_reproductible_et_idempotente(self):
        avant = (Quart.objects.count(), ServiceGarde.objects.count(), FeuilleService.objects.count())
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual((Quart.objects.count(), ServiceGarde.objects.count(), FeuilleService.objects.count()), avant)

    # ---------- Maintenance ----------

    def test_les_fiches_ont_preparation_etapes_et_points_de_controle(self):
        for titre in ("Graissage des paliers", "Nettoyage du séparateur", "Vidange et filtre à huile", "Contrôle des niveaux et fuites"):
            version = InstallationMaintenance.objects.get(title=titre).version_validee
            self.assertTrue(version.preparations.exists() and version.etapes.exists(), titre)
            self.assertTrue(3 <= version.items.count() <= 6, titre)
            self.assertEqual(set(version.preparations.values_list("type", flat=True)) >= {"outil", "epi", "consigne"}, True, titre)

    def test_scenarios_retard_attente_et_termine_avec_observations(self):
        statuts = Counter(MaintenanceOccurrence.objects.filter(installation_maintenance__isnull=False).values_list("status", flat=True))
        self.assertTrue(statuts["OVERDUE"] and statuts["WAITING_VALIDATION"] and statuts["DONE"])
        terminee = MaintenanceExecution.objects.get(occurrence__status="DONE")
        self.assertEqual(terminee.conformity, "A_SURVEILLER")
        self.assertTrue(any(isinstance(v, dict) and v["etat"] == "non_conforme" for v in terminee.results.values()))
        self.assertTrue(terminee.measurements and terminee.notes and terminee.valide_par_id)

    def test_la_fiche_est_consultable_et_imprimable_depuis_un_compte_marin(self):
        self.client.login(username="equipier_a", password="pass")
        fiche = InstallationMaintenance.objects.get(title="Graissage des paliers")
        page = self.client.get(reverse("fiche-detail", args=[fiche.pk]))
        self.assertContains(page, "Pompe à graisse manuelle")
        self.assertContains(page, "Ne jamais intervenir sur une machine en rotation")
        occurrence = MaintenanceOccurrence.objects.get(installation_maintenance=fiche, status="DONE")
        self.assertEqual(self.client.get(reverse("occurrence-execute", args=[occurrence.pk])).status_code, 200)
        self.assertContains(self.client.get(reverse("occurrence-imprimer", args=[occurrence.pk])), "Cartouche de graisse")

    # ---------- Quarts à la mer ----------

    def _par_jour(self, quart):
        jours = {}
        for c in quart.creneaux.select_related("marin").order_by("debut"):
            jours.setdefault(timezone.localtime(c.debut).date(), []).append(c)
        return jours

    def test_par_tiers_sept_creneaux_par_jour_et_trois_participants(self):
        quart = Quart.objects.get(nom="Quart machine — par tiers")
        self.assertEqual(quart.statut, Quart.STATUT_PUBLIEE)
        for jour, creneaux in self._par_jour(quart).items():
            heures = [(timezone.localtime(c.debut).hour, timezone.localtime(c.fin).hour or 24) for c in creneaux]
            self.assertEqual(heures, [(0, 4), (4, 8), (8, 12), (12, 15), (15, 18), (18, 20), (20, 24)], jour)
        self.assertEqual(len({c.marin_id for c in quart.creneaux.all()}), 3)

    def test_au_quart_le_marin_de_musique_n_a_aucun_quart_de_nuit_et_l_homme_mort_aucun_quart(self):
        quart = Quart.objects.get(nom__startswith="Quart machine — au quart")
        participants = {c.marin.username for c in quart.creneaux.select_related("marin")}
        self.assertEqual(len(participants), 4)  # effectif au roulement
        self.assertNotIn("equipier_elec_a", participants)  # homme mort : disponible, aucun quart
        for jour, creneaux in self._par_jour(quart).items():
            musique = [c for c in creneaux if c.note.startswith("De musique")]
            self.assertEqual(len(musique), 1, jour)
            marin = musique[0].marin
            self.assertEqual((timezone.localtime(musique[0].debut).hour, timezone.localtime(musique[0].fin).hour), (18, 20))
            nuit = [c for c in creneaux if c.marin_id == marin.pk and (timezone.localtime(c.debut).hour >= 20 or timezone.localtime(c.debut).hour < 8)]
            self.assertEqual(nuit, [], jour)
            for c in creneaux:
                if timezone.localtime(c.debut).hour >= 20 or timezone.localtime(c.debut).hour < 8:
                    self.assertTrue(c.marin_id, jour)  # chaque créneau de nuit est tenu

    def test_par_bordees_deux_participants(self):
        quart = Quart.objects.get(nom="Quart passerelle — par bordées")
        self.assertEqual(len({c.marin_id for c in quart.creneaux.all()}), 2)

    def test_les_tableaux_de_quart_sont_separes_de_la_feuille_de_service(self):
        feuille = FeuilleService.objects.get()
        postes = {e["creneau"].poste for e in personnel_du_jour(feuille.ship, self.jour, "A") if e["creneau"]}
        self.assertFalse(postes & {"Machine avant", "Veille"})
        self.assertFalse(CreneauQuart.objects.filter(quart__nom__startswith="Fraction").exists())

    def test_le_tableau_de_quart_publie_est_imprimable(self):
        quart = Quart.objects.get(nom="Quart machine — par tiers")
        self.client.login(username="equipier_a", password="pass")
        page = self.client.get(reverse("quart-detail", args=[quart.pk]))
        self.assertContains(page, "Imprimer ce tableau")
        self.assertContains(page, 'onclick="window.print()"')

    # ---------- Fraction de service à quai (exemple BRF) ----------

    def test_la_fraction_a_quai_a_neuf_postes_pourvus_dont_trois_gradés_de_coupee_distincts(self):
        personnel = personnel_du_jour(FeuilleService.objects.get().ship, self.jour, "A")
        self.assertEqual(len(personnel), 9)
        self.assertTrue(all(e["creneau"] and e["creneau"].marin_id for e in personnel))
        coupee = [e["marin_id"] for e in personnel if e["fonction"].libelle.startswith("Gradé de coupée")]
        self.assertEqual(len(coupee), 3)
        self.assertEqual(len(set(coupee)), 3)  # trois titulaires distincts, aucun doublon

    def test_poste_vacant_visible_sans_relève_interne(self):
        CreneauServiceGarde.objects.filter(poste="Gradé de coupée 2", debut__date=self.jour).update(marin=None)
        personnel = personnel_du_jour(FeuilleService.objects.get().ship, self.jour, "A")
        vacants = [e["fonction"].libelle for e in personnel if not e["marin_id"]]
        self.assertEqual(vacants, ["Gradé de coupée 2"])
        self.assertEqual(CreneauServiceGarde.objects.filter(poste="Gradé de coupée 1", debut__date=self.jour).count(), 1)

    def test_les_gardes_a_quai_a_venir_alimentent_mes_tours_de_service(self):
        dates = ServiceGarde.objects.filter(nom__startswith="Fraction de service à quai", statut="PUBLIEE").count()
        self.assertEqual(dates, 3)
        self.assertEqual(CreneauServiceGarde.objects.filter(marin=self._marin("equipier_a"), service_garde__nom__startswith="Fraction").count(), 3)

    # ---------- Feuille de service ----------

    def test_le_bsc_ecrit_et_les_marins_lisent_la_feuille_publiee(self):
        feuille = FeuilleService.objects.get()
        self.assertEqual(feuille.statut, FeuilleService.STATUT_PUBLIEE)
        bsc = self._marin("equipier_a2")
        self.assertTrue(peut_rediger_feuille_service(bsc, feuille.ship))
        for nom in ("equipier_a", "equipier_incendie_a", "chef_secteur_a", "cdt_a"):
            marin = self._marin(nom)
            self.assertTrue(peut_lire_feuille_service(marin, feuille), nom)
            self.assertFalse(peut_rediger_feuille_service(marin, feuille.ship), nom)
        self.client.login(username="equipier_a", password="pass")
        page = self.client.get(reverse("feuille-service-detail", args=[feuille.ship.pk, f"{self.jour:%Y-%m-%d}"]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Gradé de coupée 3")
        self.assertNotContains(page, "Créer le brouillon")
