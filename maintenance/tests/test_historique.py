"""Historique d'un équipement (UX-3.10) : frise, séries de relevés par `cle`, relevés reportés dans les mesures,
correction par un chef avec saisie d'origine conservée, rappel de la dernière valeur."""
import uuid
from datetime import timedelta
from importlib import import_module
from unittest import mock

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Roles, UserProfile
from assets.models import (
    Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate, Installation, InstallationHourReading,
    InstallationIsolationReading, InstallationMaintenance, InstallationVibrationReading, ModeDeclenchement,
)
from maintenance import historique
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship

migration = import_module("maintenance.migrations.0009_executions_indexees_par_cle")


def _marin(nom, ship, role=Roles.EQUIPIER, sector=None, service=None):
    user = User.objects.create_user(username=nom)
    UserProfile.objects.update_or_create(user=user, defaults={"ship": ship, "role": role, "sector": sector, "service": service})
    return user


class Base(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire histo", code="NH-1")
        self.service = Service.objects.create(ship=self.ship, name="Service histo")
        self.sector = Sector.objects.create(service=self.service, name="Secteur histo")
        self.marin = _marin("marin_h", self.ship)
        self.chef = _marin("chef_h", self.ship, Roles.CHEF_SECTEUR, self.sector, self.service)
        self.installation = Installation.objects.create(
            designation="Groupe histo", ship=self.ship, service=self.service, sector=self.sector)
        self.fiche = InstallationMaintenance.objects.create(
            installation=self.installation, periodicity="3 mois", title="Visite trimestrielle",
            mode_declenchement=ModeDeclenchement.CALENDRIER, intervalle=3, unite_intervalle="M")
        self.v1 = ChecklistTemplate.objects.create(
            fiche=self.fiche, numero=1, name="Visite trimestrielle", sector=self.sector, valide_le=timezone.now(),
            intervalle=3, unite_intervalle="M", duree_estimee_min=60)
        self.plombage = ChecklistItemTemplate.objects.create(template=self.v1, label="Plombage", order=1)
        self.pression = ChecklistItemTemplate.objects.create(
            template=self.v1, label="Pression", field_type="number", unit="bar", valeur_min=3, valeur_max=5, order=2)

    def occurrence(self, fiche=None, jours=0):
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=fiche or self.fiche, scheduled_for=timezone.localdate() + timedelta(days=jours),
            status="ASSIGNED")
        occ.assignees.add(self.marin)
        return occ

    def executer(self, occ, user=None, version_items=None, conformity="CONFORME", **valeurs):
        """Envoie un compte rendu complet par l'écran de saisie."""
        self.client.force_login(user or self.marin)
        donnees = {"conformity": conformity, **valeurs}
        for item in version_items or (self.plombage, self.pression):
            donnees.setdefault(f"item_{item.pk}", "conforme" if item.field_type == "checkbox" else "4")
        return self.client.post(reverse("occurrence-execute", args=[occ.pk]), donnees)


class FriseTests(Base):
    def test_frise_complete_filtrable_et_non_conformites_en_avant(self):
        self.executer(self.occurrence(), **{f"item_{self.pression.pk}": "4,2"})
        mauvais = self.executer(self.occurrence(jours=1), conformity="NON_CONFORME", **{
            f"item_{self.plombage.pk}": "non_conforme", f"commentaire_{self.plombage.pk}": "Plomb arraché"})
        self.assertEqual(mauvais.status_code, 302)
        self.client.force_login(self.marin)
        r = self.client.get(reverse("historique-installation", args=[self.installation.pk]))
        self.assertContains(r, "Visite trimestrielle")
        self.assertContains(r, "3 mois · v1")
        self.assertContains(r, "marin_h")
        self.assertContains(r, "Plomb arraché")
        self.assertContains(r, "mx-histo__entree--danger")
        self.assertContains(r, "mx-histo__entree--ok")
        anomalies = self.client.get(reverse("historique-installation", args=[self.installation.pk]) + "?anomalies=1")
        self.assertContains(anomalies, "mx-histo__entree--danger")
        self.assertNotContains(anomalies, "mx-histo__entree--ok")
        autre = self.client.get(reverse("historique-installation", args=[self.installation.pk]) + "?gamme=1+an")
        self.assertContains(autre, "Aucun compte rendu")
        sans_nul = self.client.get(reverse("historique-installation", args=[self.installation.pk]) + "?gamme=a%00b&page=zz")
        self.assertEqual(sans_nul.status_code, 200)

    def test_onglet_historique_de_l_installation_montre_la_frise(self):
        self.executer(self.occurrence())
        self.client.force_login(self.marin)
        r = self.client.get(reverse("installation-detail", args=[self.installation.pk]))
        self.assertContains(r, "Comptes rendus de maintenance")
        self.assertContains(r, "mx-histo__entree--ok")

    def test_historique_du_materiel(self):
        type_ = AssetType.objects.create(name="Extincteur h", category="Incendie", sector=self.sector)
        asset = Asset.objects.create(asset_type=type_, ship=self.ship, service=self.service, sector=self.sector)
        modele = ChecklistTemplate.objects.create(name="Gamme h", sector=self.sector)
        point = ChecklistItemTemplate.objects.create(template=modele, label="Goupille", order=1)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle h", every_n_days=30, checklist_template=modele)
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="ASSIGNED")
        occ.assignees.add(self.marin)
        self.executer(occ, version_items=[point])
        r = self.client.get(reverse("historique-materiel", args=[asset.pk]))
        self.assertContains(r, "Contrôle h")
        self.assertContains(self.client.get(reverse("asset-detail", args=[asset.pk])), "Historique de cet exemplaire")

    def test_perimetre_et_identifiants_forges(self):
        navire = Ship.objects.create(name="Autre navire", code="AN-1")
        etranger = _marin("etranger_h", navire)
        self.client.force_login(etranger)
        self.assertEqual(self.client.get(reverse("historique-installation", args=[self.installation.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("historique-materiel", args=[uuid.uuid4()])).status_code, 404)
        self.assertEqual(self.client.get("/maintenance/historique/installation/9999999999999999999999/").status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("historique-installation", args=[self.installation.pk])).status_code, 302)


class RequetesConstantesTests(Base):
    def test_nombre_de_requetes_independant_du_nombre_de_comptes_rendus(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        url = reverse("historique-installation", args=[self.installation.pk])
        self.executer(self.occurrence())
        self.client.force_login(self.chef)
        with CaptureQueriesContext(connection) as peu:
            self.client.get(url)
        for jours in range(1, 6):
            self.executer(self.occurrence(jours=jours))
        self.client.force_login(self.chef)
        with CaptureQueriesContext(connection) as beaucoup:
            self.client.get(url)
        self.assertEqual(len(peu), len(beaucoup))


class SeriesTests(Base):
    def _version_2(self):
        """Seconde version de la fiche : la ligne « Pression » garde sa `cle`, son libellé change."""
        v2 = ChecklistTemplate.objects.create(
            fiche=self.fiche, numero=2, name="Visite trimestrielle", sector=self.sector, valide_le=timezone.now() + timedelta(seconds=1))
        ChecklistItemTemplate.objects.create(template=v2, cle=self.plombage.cle, label="Plombage", order=1)
        pression = ChecklistItemTemplate.objects.create(
            template=v2, cle=self.pression.cle, label="Pression extincteur", field_type="number", unit="bar",
            valeur_min=3, valeur_max=5, order=2)
        return v2, pression

    def test_serie_continue_d_une_version_a_l_autre(self):
        self.executer(self.occurrence(), **{f"item_{self.pression.pk}": "4,5"})
        _, pression2 = self._version_2()
        occ = self.occurrence(jours=1)
        self.executer(occ, version_items=[pression2], **{f"item_{pression2.pk}": "4"})
        series = historique.series(historique.sources_de(self.installation))
        self.assertEqual(len(series), 1)
        self.assertEqual([p["valeur"] for p in series[0]["points"]], [4.5, 4.0])
        self.assertEqual(series[0]["libelle"], "Pression extincteur")
        self.assertEqual(series[0]["tendance"]["code"], "baisse")
        self.client.force_login(self.marin)
        r = self.client.get(reverse("historique-installation", args=[self.installation.pk]) + "?vue=releves")
        self.assertContains(r, "Pression extincteur")
        self.assertContains(r, 'data-serie="serie-0"')
        self.assertContains(r, 'id="serie-0"')

    def test_ancien_compte_rendu_indexe_par_libelle_encore_lu(self):
        occ = self.occurrence()
        MaintenanceExecution.objects.create(
            occurrence=occ, completed_at=timezone.now(), conformity="CONFORME", version_fiche=self.v1,
            results={"Plombage": {"etat": "conforme", "commentaire": ""}}, measurements={"Pression": 4.4})
        series = historique.series(historique.sources_de(self.installation))
        self.assertEqual(series[0]["derniere"]["valeur"], 4.4)
        entree = historique.frise(historique.sources_de(self.installation), self.chef)[0]
        self.assertEqual({l["libelle"] for l in entree["lignes"]}, {"Plombage", "Pression"})

    def test_derive_avant_la_limite(self):
        base = timezone.now() - timedelta(days=40)
        for rang, valeur in enumerate((4.8, 4.4, 4.0, 3.6)):
            occ = self.occurrence(jours=rang - 10)
            MaintenanceExecution.objects.create(
                occurrence=occ, completed_at=base + timedelta(days=rang * 10), conformity="CONFORME",
                version_fiche=self.v1, measurements={str(self.pression.cle): valeur})
        serie = historique.series(historique.sources_de(self.installation))[0]
        self.assertIsNotNone(serie["derive_jours"])
        self.client.force_login(self.marin)
        r = self.client.get(reverse("historique-installation", args=[self.installation.pk]) + "?vue=releves")
        self.assertContains(r, "la limite de la plage sera atteinte")

    def test_correction_met_a_jour_la_serie_et_garde_l_origine(self):
        occ = self.occurrence()
        self.executer(occ, **{f"item_{self.pression.pk}": "4"})
        self.executer(occ, user=self.chef, **{f"item_{self.pression.pk}": "8", "motif": "Mauvaise lecture"})
        serie = historique.series(historique.sources_de(self.installation))[0]
        point = serie["points"][0]
        self.assertEqual((point["valeur"], point["origine"], point["corrige"], point["hors_plage"]), (8.0, 4.0, True, True))
        self.client.force_login(self.marin)
        frise = self.client.get(reverse("historique-installation", args=[self.installation.pk]))
        self.assertContains(frise, "Mauvaise lecture")
        self.assertContains(frise, "Saisie d'origine")
        releves = self.client.get(reverse("historique-installation", args=[self.installation.pk]) + "?vue=releves")
        self.assertContains(releves, "saisi : 4")

    def test_rappel_de_la_derniere_valeur_sur_l_ecran_de_saisie(self):
        self.executer(self.occurrence(), **{f"item_{self.pression.pk}": "4,5"})
        self.executer(self.occurrence(jours=1), **{f"item_{self.pression.pk}": "4"})
        occ = self.occurrence(jours=2)
        self.client.force_login(self.marin)
        r = self.client.get(reverse("occurrence-execute", args=[occ.pk]))
        self.assertContains(r, "Dernier : ")
        self.assertContains(r, "en baisse")
        self.assertContains(r, "Signaler une anomalie")


class RelevesAlimentesTests(Base):
    def setUp(self):
        super().setUp()
        self.heures = ChecklistItemTemplate.objects.create(
            template=self.v1, label="Compteur horaire", field_type="number", unit="h", releve="heures", order=3)
        self.isolement = ChecklistItemTemplate.objects.create(
            template=self.v1, label="Isolement", field_type="number", unit="Ω", releve="isolement", order=4)
        self.vibrations = ChecklistItemTemplate.objects.create(
            template=self.v1, label="Vibrations", field_type="text", releve="vibrations", order=5)
        self.items = (self.plombage, self.pression, self.heures, self.isolement, self.vibrations)

    def _saisie(self, occ, user=None, **extra):
        valeurs = {f"item_{self.heures.pk}": "1250,5", f"item_{self.isolement.pk}": "560000",
                   f"item_{self.vibrations.pk}": "b", **extra}
        return self.executer(occ, user, version_items=self.items, **valeurs)

    def test_cloture_alimente_les_mesures_sans_doublon(self):
        occ = self.occurrence()
        self._saisie(occ)
        heure = InstallationHourReading.objects.get(installation=self.installation)
        self.assertEqual((str(heure.hours), heure.execution.occurrence), ("1250.50", occ))
        self.assertEqual(InstallationIsolationReading.objects.get().ohms, 560000)
        self.assertEqual(InstallationVibrationReading.objects.get().state, "B")
        # Correction par le chef : la mesure est mise à jour, jamais doublée.
        self._saisie(occ, self.chef, **{f"item_{self.heures.pk}": "1300", "motif": "Compteur relu"})
        self.assertEqual(InstallationHourReading.objects.count(), 1)
        self.assertEqual(str(InstallationHourReading.objects.get().hours), "1300.00")
        # Une valeur effacée retire la mesure de ce compte rendu.
        self._saisie(occ, self.chef, **{f"item_{self.isolement.pk}": "", "motif": "Pas de mesure"})
        self.assertFalse(InstallationIsolationReading.objects.exists())

    def test_enregistrement_en_direct_n_alimente_rien(self):
        occ = self.occurrence()
        self.client.force_login(self.marin)
        self.client.post(reverse("occurrence-execute", args=[occ.pk]), {
            "action": "enregistrer", f"item_{self.heures.pk}": "1250"})
        self.assertFalse(InstallationHourReading.objects.exists())

    def test_valeurs_forgees_refusees_sans_erreur_serveur(self):
        occ = self.occurrence()
        for extra, message in (
            ({f"item_{self.vibrations.pk}": "Z"}, "saisissez A, B ou C"),
            ({f"item_{self.heures.pk}": "-5"}, "hors des limites"),
            ({f"item_{self.heures.pk}": "99999999999"}, "hors des limites"),
            ({f"item_{self.isolement.pk}": "1e300"}, "hors des limites"),
        ):
            r = self._saisie(occ, **extra)
            self.assertContains(r, message)
        self.assertFalse(InstallationHourReading.objects.exists())
        self.assertFalse(MaintenanceExecution.objects.exists())

    def test_l_assistant_de_fiche_garde_le_type_de_releve(self):
        from assets import fiche_maintenance, fiche_web
        contenu = fiche_maintenance.contenu_de(self.v1)
        self.assertEqual({l["label"]: l["releve"] for l in contenu["lignes"]}["Isolement"], "isolement")
        from django.http import QueryDict
        post = QueryDict(mutable=True)
        post.setlist("ligne_label", ["Vibrations", "Heures"])
        for champ in ("ligne_cle", "ligne_unite", "ligne_min", "ligne_max"):
            post.setlist(champ, ["", ""])
        post.setlist("ligne_type", ["checkbox", "checkbox"])
        post.setlist("ligne_releve", ["vibrations", "heures"])
        lignes = fiche_web.lire_formulaire(post)["lignes"]
        self.assertEqual([(l["field_type"], l["releve"]) for l in lignes], [("text", "vibrations"), ("number", "heures")])


class MigrationParCleTests(Base):
    def test_indexation_par_cle_sure_et_rejouable(self):
        occ = self.occurrence()
        execution = MaintenanceExecution.objects.create(
            occurrence=occ, completed_at=timezone.now(), version_fiche=self.v1, conformity="CONFORME",
            results={"Plombage": {"etat": "conforme", "commentaire": ""}, "Libellé inconnu": "x"},
            measurements={"Pression": 4.2})
        sans_version = MaintenanceExecution.objects.create(
            occurrence=self.occurrence(jours=1), completed_at=timezone.now(), measurements={"Pression": 1.0})
        MaintenanceExecution.objects.filter(pk=sans_version.pk).update(version_fiche=None)
        MaintenanceExecution.objects.filter(pk=execution.pk).update(results=execution.results)
        for _ in range(2):
            migration.indexer_par_cle(apps, None)
        execution.refresh_from_db()
        self.assertEqual(execution.measurements, {str(self.pression.cle): 4.2})
        self.assertEqual(set(execution.results), {str(self.plombage.cle), "Libellé inconnu"})
        sans_version.refresh_from_db()
        self.assertEqual(sans_version.measurements, {"Pression": 1.0})
        migration.indexer_par_libelle(apps, None)
        execution.refresh_from_db()
        self.assertEqual(execution.measurements, {"Pression": 4.2})

    def test_libelle_en_double_reste_inchange(self):
        ChecklistItemTemplate.objects.create(template=self.v1, label="Pression", field_type="number", order=9)
        execution = MaintenanceExecution.objects.create(
            occurrence=self.occurrence(), completed_at=timezone.now(), version_fiche=self.v1, measurements={"Pression": 4.2})
        migration.indexer_par_cle(apps, None)
        execution.refresh_from_db()
        self.assertEqual(execution.measurements, {"Pression": 4.2})


class ApiCompteRenduTermineTests(Base):
    def test_un_compte_rendu_termine_ne_se_reecrit_pas_par_l_api(self):
        occ = self.occurrence()
        self.client.force_login(self.chef)
        url = f"/api/maintenance/occurrences/{occ.pk}/complete/"
        reponse = self.client.post(url, {"conformity": "CONFORME"}, content_type="application/json")
        self.assertEqual(reponse.status_code, 200)
        execution = MaintenanceExecution.objects.get(occurrence=occ)
        self.assertEqual(execution.saisie_origine["par"], self.chef.pk)
        encore = self.client.post(url, {"conformity": "NON_CONFORME"}, content_type="application/json")
        self.assertEqual(encore.status_code, 409)
        patch = self.client.patch(
            f"/api/maintenance/executions/{execution.pk}/", {"notes": "réécrit", "saisie_origine": {"x": 1}},
            content_type="application/json")
        self.assertEqual(patch.status_code, 400)
        execution.refresh_from_db()
        self.assertEqual((execution.conformity, execution.notes), ("CONFORME", ""))


class FicheImprimableOrdreTests(Base):
    def test_le_qr_rouvre_le_formulaire_dans_l_ordre_du_papier(self):
        occ = self.occurrence()
        self.client.force_login(self.marin)
        with mock.patch("maintenance.web_views._qr_data_uri", return_value="data:image/png;base64,") as qr:
            papier = self.client.get(reverse("occurrence-imprimer", args=[occ.pk])).content.decode()
        self.assertTrue(qr.call_args[0][0].endswith(reverse("occurrence-execute", args=[occ.pk])))
        ecran = self.client.get(reverse("occurrence-execute", args=[occ.pk])).content.decode()
        self.assertLess(papier.index("Plombage"), papier.index("Pression"))
        self.assertLess(ecran.index("Plombage"), ecran.index("Pression"))
