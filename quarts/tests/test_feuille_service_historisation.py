"""Historisation des feuilles de service : la structure (rubriques et fonctions)
est figée à la création ; les réglages ultérieurs ne changent pas une feuille
publiée, un brouillon se resynchronise explicitement."""
from datetime import datetime

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from accounts.models import AuditLog
from org.models import Ship
from quarts.models import (
    CreneauServiceGarde,
    FeuilleService,
    FonctionFeuilleService,
    RubriqueEnTeteFeuilleService,
    ServiceGarde,
)
from quarts.tests.test_feuille_service import FeuilleServiceTestsBase


class HistorisationBase(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        self.feuille.valeurs_entete = {str(self.rubrique_quotidienne.uid): "Dimanche"}
        self.feuille.save(update_fields=["valeurs_entete"])
        self.url = f"/quarts/feuille-service/{self.ship.pk}/{self.jour.isoformat()}/"

    def _publier(self):
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        self.feuille.refresh_from_db()

    def _modifier_les_reglages(self):
        self.rubrique_fixe.libelle = "Consignes"
        self.rubrique_fixe.valeur_fixe = "Vigipirate normal"
        self.rubrique_fixe.save()
        self.rubrique_quotidienne.delete()
        RubriqueEnTeteFeuilleService.objects.create(ship=self.ship, libelle="Nouvelle rubrique", ordre=5)
        self.fonction.libelle = "Officier de quart"
        self.fonction.poste_recherche = "Autre poste"
        self.fonction.save()
        FonctionFeuilleService.objects.create(ship=self.ship, libelle="Nouvelle fonction")


class StructureFigeeTests(HistorisationBase):
    def test_la_feuille_naît_avec_la_structure_du_batiment(self):
        structure = self.feuille.structure_figee
        self.assertEqual(
            [r["libelle"] for r in structure["rubriques"]], ["Mesures de sécurité", "Type de journée"]
        )
        self.assertEqual(structure["rubriques"][1]["uid"], str(self.rubrique_quotidienne.uid))
        self.assertEqual([f["libelle"] for f in structure["fonctions"]], ["Officier de garde"])

    def test_feuille_publiee_inchangee_par_les_reglages(self):
        self._publier()
        avant = [(e["rubrique"].libelle, e["valeur"]) for e in self.feuille.rubriques_affichees]
        self._modifier_les_reglages()
        apres = [(e["rubrique"].libelle, e["valeur"]) for e in self.feuille.rubriques_affichees]
        self.assertEqual(avant, apres)
        self.assertEqual(
            apres, [("Mesures de sécurité", "Vigipirate renforcé"), ("Type de journée", "Dimanche")]
        )
        self.assertEqual([e["fonction"].libelle for e in self.feuille.personnel], ["Officier de garde"])

    def test_la_page_d_une_feuille_publiee_ignore_les_reglages_modifies(self):
        self._publier()
        self._modifier_les_reglages()
        self.client.login(username="bsc", password="pass")
        page = self.client.get(self.url).content.decode()
        self.assertIn("Mesures de sécurité", page)
        self.assertIn("Vigipirate renforcé", page)
        self.assertNotIn("Nouvelle rubrique", page)
        self.assertNotIn("Nouvelle fonction", page)

    def test_le_titulaire_est_retrouve_par_le_poste_fige(self):
        self.fonction.poste_recherche = "Poste X"
        self.fonction.save()
        feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour.replace(day=1) if self.jour.day != 1 else self.jour.replace(day=2),
        )
        self.fonction.poste_recherche = "Poste Y"
        self.fonction.save()
        self.assertEqual(feuille.structure_figee["fonctions"][0]["poste_recherche"], "Poste X")

    def test_identite_stable_apres_renommage_dans_la_version(self):
        self._publier()
        self._modifier_les_reglages()
        entete = self.feuille.versions.get().contenu_fige["entete"]
        self.assertEqual(
            {e["uid"] for e in entete},
            {str(self.rubrique_fixe.uid), str(self.rubrique_quotidienne.uid)},
        )
        personnel = self.feuille.versions.get().contenu_fige["personnel"]
        self.assertEqual(personnel[0]["uid"], str(self.fonction.uid))
        self.assertEqual(personnel[0]["fonction"], "Officier de garde")

    def test_un_echange_apres_publication_ne_change_pas_les_titulaires_publies(self):
        creneau = self._publier_tour(marin=self.marin_service)
        self._publier()
        creneau.marin = self.chef_service
        creneau.save(update_fields=["marin", "updated_at"])
        self.assertEqual(self.feuille.personnel[0]["marin_fige"], "marin_service")
        self.assertEqual(self.feuille.personnel_travail[0]["creneau"].marin, self.chef_service)


class ResynchronisationTests(HistorisationBase):
    def test_un_brouillon_garde_sa_structure_et_signale_la_divergence(self):
        self.assertFalse(self.feuille.structure_divergente)
        self._modifier_les_reglages()
        self.assertTrue(self.feuille.structure_divergente)
        self.assertNotIn(
            "Nouvelle rubrique", [e["rubrique"].libelle for e in self.feuille.rubriques_affichees]
        )
        self.client.login(username="bsc", password="pass")
        self.assertContains(self.client.get(self.url), "Resynchroniser")

    def test_resynchronisation_preserve_les_saisies_compatibles(self):
        rubrique_retiree = RubriqueEnTeteFeuilleService.objects.create(ship=self.ship, libelle="À retirer", ordre=9)
        feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour.replace(day=1) if self.jour.day != 1 else self.jour.replace(day=2),
            created_by=self.equipier,
        )
        feuille.valeurs_entete = {
            str(self.rubrique_quotidienne.uid): "Dimanche", str(rubrique_retiree.uid): "Valeur perdue",
        }
        feuille.save(update_fields=["valeurs_entete"])
        rubrique_retiree.delete()
        self.rubrique_quotidienne.libelle = "Journée"
        self.rubrique_quotidienne.save()
        nouvelle = RubriqueEnTeteFeuilleService.objects.create(ship=self.ship, libelle="Nouvelle", ordre=7)

        self.client.login(username="bsc", password="pass")
        url = f"/quarts/feuille-service/{self.ship.pk}/{feuille.date.isoformat()}/"
        self.assertEqual(self.client.post(url, {"action": "resynchroniser"}).status_code, 302)
        feuille.refresh_from_db()
        libelles = {e["rubrique"].libelle: e["valeur"] for e in feuille.rubriques_affichees}
        self.assertEqual(libelles, {
            "Mesures de sécurité": "Vigipirate renforcé", "Journée": "Dimanche", "Nouvelle": "",
        })
        self.assertEqual(feuille.valeurs_entete, {str(self.rubrique_quotidienne.uid): "Dimanche"})
        self.assertFalse(feuille.structure_divergente)
        trace = AuditLog.objects.get(action="feuille_service_structure_resynchronisee")
        self.assertIn("À retirer = Valeur perdue", trace.details)
        self.assertIn(str(nouvelle.uid), str(feuille.structure_figee))

    def test_resynchronisation_reservee_au_redacteur_du_brouillon(self):
        self.client.login(username="chef_secteur", password="pass")
        self.assertEqual(self.client.post(self.url, {"action": "resynchroniser"}).status_code, 403)

    def test_pas_de_resynchronisation_d_une_feuille_publiee(self):
        self._publier()
        self._modifier_les_reglages()
        self.client.login(username="etat_major", password="pass")
        self.assertEqual(self.client.post(self.url, {"action": "resynchroniser"}).status_code, 403)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.structure_figee["origine"], "creation")

    def test_saisie_limitee_aux_rubriques_figees(self):
        nouvelle = RubriqueEnTeteFeuilleService.objects.create(ship=self.ship, libelle="Ajoutée après")
        self.client.login(username="bsc", password="pass")
        self.client.post(self.url, {
            "action": "enregistrer_entete",
            f"rubrique_{self.rubrique_quotidienne.uid}": "Lundi",
            f"rubrique_{nouvelle.uid}": "Forcée",
        })
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete, {str(self.rubrique_quotidienne.uid): "Lundi"})


class FeuilleSansInstantaneTests(HistorisationBase):
    def _rendre_historique(self):
        FeuilleService.objects.filter(pk=self.feuille.pk).update(structure_figee=None)
        self.feuille.refresh_from_db()

    def test_feuille_publiee_sans_instantane_lue_dans_sa_version(self):
        self._publier_tour(marin=self.marin_service)
        self._publier()
        self._rendre_historique()
        self._modifier_les_reglages()
        self.assertEqual(self.feuille.version_publiee.numero, 1)
        self.assertEqual(
            [(e["rubrique"].libelle, e["valeur"]) for e in self.feuille.rubriques_affichees],
            [("Mesures de sécurité", "Vigipirate renforcé"), ("Type de journée", "Dimanche")],
        )
        self.assertEqual(self.feuille.personnel[0]["marin_fige"], "marin_service")
        self.client.login(username="bsc", password="pass")
        self.assertContains(self.client.get(self.url), "Feuille publiée avant l'historisation")

    def test_feuille_sans_version_signale_la_limite(self):
        FeuilleService.objects.filter(pk=self.feuille.pk).update(
            structure_figee=None, statut=FeuilleService.STATUT_PUBLIEE,
        )
        self.client.login(username="bsc", password="pass")
        self.assertContains(self.client.get(self.url), "sans version conservée")


class BandeauMigrationTests(HistorisationBase):
    def test_bandeau_dit_que_la_structure_est_celle_de_la_migration(self):
        structure = dict(self.feuille.structure_figee, origine="migration")
        FeuilleService.objects.filter(pk=self.feuille.pk).update(structure_figee=structure)
        self.client.login(username="bsc", password="pass")
        self.assertContains(self.client.get(self.url), "pas d'après la structure d'origine")
        self._modifier_les_reglages()
        self.assertContains(self.client.get(self.url), "pas sur sa structure d'origine")


class MigrationHistorisationTests(TransactionTestCase):
    """Migration de données testée de bout en bout : identités, re-clefage, figement."""

    avant = [("quarts", "0005_feuille_service_identites_structure")]
    apres = [("quarts", "0007_feuille_service_identites_uniques")]

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.apres)

    def test_migration_des_donnees_existantes_puis_retour_arriere(self):
        executeur = MigrationExecutor(connection)
        executeur.migrate(self.avant)
        apps = executeur.loader.project_state(self.avant).apps
        Ship_, Rubrique = apps.get_model("org", "Ship"), apps.get_model("quarts", "RubriqueEnTeteFeuilleService")
        Fonction, Feuille = apps.get_model("quarts", "FonctionFeuilleService"), apps.get_model("quarts", "FeuilleService")
        Version = apps.get_model("quarts", "VersionFeuilleService")
        navire = Ship_.objects.create(name="Migr", code="MIG")
        rubrique = Rubrique.objects.create(ship=navire, libelle="Jour", type_saisie="QUOTIDIENNE")
        Rubrique.objects.create(ship=navire, libelle="Inactive", actif=False)
        Fonction.objects.create(ship=navire, libelle="OG", poste_recherche="Officier")
        brouillon = Feuille.objects.create(
            ship=navire, date="2026-01-01", statut="BROUILLON", valeurs_entete={str(rubrique.pk): "Lundi", "999": "orpheline"},
        )
        publiee = Feuille.objects.create(
            ship=navire, date="2026-01-02", statut="PUBLIEE", valeurs_entete={str(rubrique.pk): "Mardi"},
        )
        Version.objects.create(feuille=publiee, numero=1, publiee_le=timezone.now(), contenu_fige={"entete": []})

        executeur = MigrationExecutor(connection)
        executeur.migrate(self.apres)
        apps = executeur.loader.project_state(self.apres).apps
        Rubrique, Feuille = apps.get_model("quarts", "RubriqueEnTeteFeuilleService"), apps.get_model("quarts", "FeuilleService")
        uid = str(Rubrique.objects.get(libelle="Jour").uid)
        brouillon, publiee = Feuille.objects.get(pk=brouillon.pk), Feuille.objects.get(pk=publiee.pk)
        self.assertEqual(brouillon.valeurs_entete, {uid: "Lundi", "999": "orpheline"})
        self.assertEqual([r["libelle"] for r in brouillon.structure_figee["rubriques"]], ["Jour"])
        self.assertEqual(brouillon.structure_figee["fonctions"][0]["poste_recherche"], "Officier")
        self.assertEqual(brouillon.structure_figee["origine"], "migration")
        self.assertEqual(publiee.valeurs_entete, {uid: "Mardi"})
        self.assertIsNone(publiee.structure_figee)
        self.assertEqual(apps.get_model("quarts", "VersionFeuilleService").objects.count(), 1)

        executeur = MigrationExecutor(connection)
        executeur.migrate(self.avant)
        apps = executeur.loader.project_state(self.avant).apps
        self.assertEqual(
            apps.get_model("quarts", "FeuilleService").objects.get(pk=publiee.pk).valeurs_entete,
            {str(rubrique.pk): "Mardi"},
        )
