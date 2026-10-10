"""Fiche de maintenance : versions, gammes, circuit de validation bord, lecture par les exécutions."""
from datetime import date
from importlib import import_module
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from assets import fiche_maintenance, fiche_validation as circuit
from assets.mesures import heures_par_gamme
from assets.models import (
    ChecklistTemplate, Installation, InstallationHourReading,
    InstallationMaintenance,
)
from assets.proposition_article import ErreurCircuit
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence
from notifications.models import Notification
from org.models import Section, Sector, Service, Ship

migration = import_module("assets.migrations.0036_fiches_version_1")
Etat = ChecklistTemplate.Etat
CONTENU = {
    "name": "Entretien trimestriel", "description": "Contrôle courant", "resume_modifications": "",
    "mode_declenchement": "CALENDRIER", "intervalle": 3, "unite_intervalle": "M", "seuil_heures": None,
    "duree_estimee_min": 90, "nb_personnes": 2, "qualification": None,
    "preparations": [{"type": "outil", "libelle": "Clé de 17", "quantite": 1, "piece": None}],
    "etapes": [{"texte": "Consigner la pompe", "attention": "Haute pression"}],
    "lignes": [{"label": "Plombage", "field_type": "checkbox", "unit": ""},
               {"label": "Pression", "field_type": "number", "unit": "bar", "valeur_min": 4.0, "valeur_max": 6.0}],
}


class BaseFiches(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Frégate", code="FRG")
        self.machine = Service.objects.create(ship=self.ship, name="Machine", commandant_adjoint="COMAEQ")
        self.secteur = Sector.objects.create(service=self.machine, name="Propulsion")
        self.section = Section.objects.create(sector=self.secteur, name="Moteurs")
        autre_service = Service.objects.create(ship=self.ship, name="Pont", commandant_adjoint="COMANAV")
        self.autre_secteur = Sector.objects.create(service=autre_service, name="Manoeuvre")
        self.installation = Installation.objects.create(
            designation="Pompe incendie", ship=self.ship, service=self.machine, sector=self.secteur, section=self.section)
        self.autre = Installation.objects.create(
            designation="Pompe de cale", ship=self.ship, service=self.machine, sector=self.secteur, section=self.section)
        self.chef_section = self._u("chef_section", "CHEF_SECTION", ship=self.ship, service=self.machine, sector=self.secteur, section=self.section)
        self.chef_secteur = self._u("chef_secteur", "CHEF_SECTEUR", ship=self.ship, service=self.machine, sector=self.secteur)
        self.chef_service = self._u("chef_service", "CHEF_SERVICE", ship=self.ship, service=self.machine)
        self.comaeq = self._u("comaeq", "ETAT_MAJOR", ship=self.ship, fonction_coma="COMAEQ")
        self.comanav = self._u("comanav", "ETAT_MAJOR", ship=self.ship, fonction_coma="COMANAV")
        self.equipier = self._u("equipier", "EQUIPIER", ship=self.ship, service=self.machine, sector=self.secteur, section=self.section)

    def _u(self, nom, role, **rattachement):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return User.objects.get(pk=user.pk)

    def contenu(self, **plus):
        return {**CONTENU, **plus}

    def soumettre(self, auteur=None, **plus):
        return circuit.soumettre(auteur or self.chef_section, self.installation, self.contenu(**plus))

    def valider(self, version, visiteurs=None):
        for user in visiteurs or (self.chef_secteur, self.chef_service, self.comaeq):
            version.refresh_from_db()
            if version.etat != Etat.VALIDEE and circuit.peut_agir(user, version)[0]:
                circuit.viser(user, version.pk, version.etat)
        version.refresh_from_db()
        return version

    def fiche_validee(self, **plus):
        version = self.valider(self.soumettre(**plus))
        return version.fiche


class CircuitTests(BaseFiches):
    def test_chef_de_section_passe_par_le_secteur_puis_le_service_puis_le_coma(self):
        version = self.soumettre()
        self.assertEqual(version.etat, Etat.VISA_SECTEUR)
        self.assertEqual(version.fiche.periodicity, "—")
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur, object_id=str(version.pk)).exists())
        circuit.viser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR)
        version.refresh_from_db()
        self.assertEqual(version.etat, Etat.VISA_SERVICE)
        self.assertTrue(Notification.objects.filter(user=self.chef_service, object_id=str(version.pk)).exists())
        circuit.viser(self.chef_service, version.pk, Etat.VISA_SERVICE)
        self.assertTrue(Notification.objects.filter(user=self.comaeq, object_id=str(version.pk)).exists())
        self.assertFalse(Notification.objects.filter(user=self.comanav).exists())
        circuit.viser(self.comaeq, version.pk, Etat.VISA_COMA)
        version.refresh_from_db()
        fiche = version.fiche
        self.assertEqual(version.etat, Etat.VALIDEE)
        self.assertEqual((fiche.periodicity, fiche.intervalle, fiche.unite_intervalle, fiche.planned_duration_min, fiche.people_count),
                         ("3 mois", 3, "M", 90, 2))
        self.assertTrue(Notification.objects.filter(user=self.chef_section, verb__contains="validée").exists())
        self.assertTrue(AuditLog.objects.filter(action="fiche.version.publiee").exists())
        self.assertEqual(version.evenements.filter(action="visee").count(), 3)

    def test_chef_de_secteur_commence_au_service(self):
        version = self.soumettre(auteur=self.chef_secteur)
        self.assertEqual(version.etat, Etat.VISA_SERVICE)
        self.assertEqual([e["libelle"] for e in circuit.frise(version)], ["Rédaction", "Chef de service", "Commandant adjoint", "Validée"])

    def test_seul_le_commandant_adjoint_du_service_vise(self):
        version = self.soumettre(auteur=self.chef_secteur)
        circuit.viser(self.chef_service, version.pk, Etat.VISA_SERVICE)
        version.refresh_from_db()
        self.assertFalse(circuit.peut_agir(self.comanav, version)[0])
        with self.assertRaises(ErreurCircuit):
            circuit.viser(self.comanav, version.pk, Etat.VISA_COMA)

    def test_droits_de_redaction(self):
        for user in (self.equipier, self.chef_service):
            with self.subTest(user.username), self.assertRaises(ErreurCircuit):
                circuit.soumettre(user, self.installation, self.contenu())
        hors = Installation.objects.create(designation="Treuil", ship=self.ship, service=self.machine, sector=self.autre_secteur)
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre(self.chef_section, hors, self.contenu())

    def test_auto_validation_et_double_intervention_interdites(self):
        version = self.soumettre(auteur=self.chef_secteur)
        self.assertFalse(circuit.peut_agir(self.chef_secteur, version)[0])
        circuit.viser(self.chef_service, version.pk, Etat.VISA_SERVICE)
        version.refresh_from_db()
        self.assertFalse(circuit.peut_agir(self.chef_service, version)[0])

    def test_visa_perime_refuse(self):
        version = self.soumettre()
        circuit.viser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR)
        with self.assertRaises(ErreurCircuit):
            circuit.viser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR)

    def test_refus_motive_revient_au_redacteur_puis_correction(self):
        version = self.soumettre()
        with self.assertRaises(ErreurCircuit):
            circuit.refuser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR, "  ")
        circuit.refuser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR, "Pression à revoir")
        version.refresh_from_db()
        self.assertEqual((version.etat, version.motif_refus), (Etat.REFUSEE, "Pression à revoir"))
        self.assertTrue(Notification.objects.filter(user=self.chef_section, verb__contains="Pression à revoir").exists())
        self.assertEqual(circuit.frise(version)[1]["etat"], "refusee")
        with self.assertRaises(ErreurCircuit):
            circuit.resoumettre(self.chef_secteur, version.pk, self.contenu())
        circuit.resoumettre(self.chef_section, version.pk, self.contenu(name="Entretien corrigé"))
        version.refresh_from_db()
        self.assertEqual((version.etat, version.name, version.motif_refus), (Etat.VISA_SECTEUR, "Entretien corrigé", ""))
        self.assertEqual(version.numero, 1)

    def test_equipage_a_terre_refuse_en_ecriture(self):
        self.ship.double_equipage, self.ship.equipage_a_bord = True, "A"
        self.ship.save()
        UserProfile.objects.filter(user=self.chef_section).update(equipage="B")
        self.client.force_login(User.objects.get(pk=self.chef_section.pk))
        reponse = self.client.post(reverse("fiche-nouvelle", args=[self.installation.pk]), {"name": "X"})
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(InstallationMaintenance.objects.exists())
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre(User.objects.get(pk=self.chef_section.pk), self.installation, self.contenu())

    def test_seuil_de_redaction_configurable(self):
        from org.models import RoleThresholdConfig
        from matrix.core.role_thresholds import invalidate_cache

        RoleThresholdConfig.objects.create(ship=self.ship, thresholds={"fiche_bord_redaction": "CHEF_SECTEUR"})
        invalidate_cache(self.ship.id)
        self.addCleanup(invalidate_cache, self.ship.id)
        self.assertFalse(circuit.peut_rediger(self.chef_section, self.installation)[0])
        self.assertTrue(circuit.peut_rediger(self.chef_secteur, self.installation)[0])

    def test_frise_organisme_fonction_service_titulaire(self):
        version = self.soumettre()
        circuit.viser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR)
        version.refresh_from_db()
        etapes = circuit.frise(version)
        secteur, service, coma = etapes[1], etapes[2], etapes[3]
        self.assertEqual((secteur["etat"], secteur["titulaire"]), ("faite", "chef_secteur"))
        self.assertEqual((service["etat"], service["fonction"], service["organisme"], service["service"]),
                         ("actuelle", "Chef de service", "Frégate", "Machine"))
        self.assertEqual((coma["fonction"], coma["titulaire"]), ("Commandant adjoint (COMAEQ)", "comaeq"))


class VersionsTests(BaseFiches):
    def test_une_version_en_cours_a_la_fois_et_validee_reste_appliquee(self):
        fiche = self.fiche_validee()
        nouvelle = circuit.soumettre(self.chef_section, self.installation, self.contenu(
            name="Entretien révisé", intervalle=6, resume_modifications="Périodicité allongée"), fiche)
        self.assertEqual(nouvelle.numero, 2)
        fiche.refresh_from_db()
        self.assertEqual((fiche.intervalle, fiche.title), (3, "Entretien trimestriel"))
        self.assertEqual(fiche.version_validee.numero, 1)
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre(self.chef_section, self.installation, self.contenu(resume_modifications="x"), fiche)
        self.valider(nouvelle)
        fiche.refresh_from_db()
        self.assertEqual((fiche.intervalle, fiche.version_validee.numero), (6, 2))

    def test_resume_des_modifications_obligatoire(self):
        fiche = self.fiche_validee()
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre(self.chef_section, self.installation, self.contenu(), fiche)

    def test_une_fiche_par_gamme(self):
        self.fiche_validee()
        with self.assertRaises(ErreurCircuit):
            self.soumettre(name="Autre entretien")
        circuit.soumettre(self.chef_section, self.installation, self.contenu(name="Annuel", intervalle=1, unite_intervalle="A"))
        circuit.soumettre(self.chef_section, self.installation, self.contenu(
            name="Révision 1 000 h", mode_declenchement="COMPTEUR", intervalle=None, seuil_heures=1000))
        self.assertEqual(self.installation.maintenances.count(), 3)

    def test_gamme_obligatoire(self):
        with self.assertRaises(ErreurCircuit):
            self.soumettre(intervalle=None)

    def test_les_lignes_gardent_leur_identite_d_une_version_a_l_autre(self):
        fiche = self.fiche_validee()
        v1 = fiche.version_validee
        contenu = fiche_maintenance.contenu_de(v1)
        pression = next(l for l in contenu["lignes"] if l["label"] == "Pression")
        pression.update(label="Pression d'huile", valeur_max=7.0)
        contenu["lignes"].append({"label": "Fuite", "field_type": "checkbox", "unit": ""})
        contenu["resume_modifications"] = "Renommage"
        v2 = circuit.soumettre(self.chef_section, self.installation, contenu, fiche)
        v2_pression = v2.items.get(label="Pression d'huile")
        self.assertEqual(v2_pression.cle, v1.items.get(label="Pression").cle)
        self.assertEqual(v2.items.count(), 3)
        self.assertEqual(v1.items.count(), 2)
        self.assertEqual(v1.items.get(label="Pression").valeur_max, 6.0)

    def test_dupliquer_est_une_copie_independante(self):
        fiche = self.fiche_validee()
        copie = circuit.dupliquer(self.chef_section, fiche.version_validee, self.autre)
        self.assertNotEqual(copie.fiche_id, fiche.pk)
        self.assertEqual(copie.fiche.installation, self.autre)
        self.assertEqual(copie.etat, Etat.VISA_SECTEUR)
        cles = {i.cle for i in fiche.version_validee.items.all()}
        self.assertFalse(cles & {i.cle for i in copie.items.all()})
        self.assertEqual(copie.items.count(), 2)

    def test_niveau_et_categorie_pour_les_fiches_flotte(self):
        from accounts.models import SpecialityChoice
        from assets.models import CategorieCatalogue

        categorie = CategorieCatalogue.objects.create(nom="Extincteurs", specialite=SpecialityChoice.objects.create(name="Sécurité"))
        flotte = InstallationMaintenance.objects.create(categorie=categorie, niveau="FLOTTE", periodicity="1 an", title="Contrôle annuel")
        self.assertIsNone(flotte.installation)
        self.assertIsNone(flotte.version_validee)
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            InstallationMaintenance.objects.create(periodicity="x", title="Orpheline")


class MigrationTests(BaseFiches):
    def test_les_fiches_existantes_deviennent_la_version_1_validee(self):
        fiche = InstallationMaintenance.objects.create(
            installation=self.installation, periodicity="3 mois", title="Ancienne fiche", description="Texte libre",
            planned_duration_min=45, people_count=3, intervalle=3, unite_intervalle="M", mode_declenchement="CALENDRIER")
        migration.creer_versions_initiales(apps, None)
        migration.creer_versions_initiales(apps, None)
        version = fiche.versions.get()
        self.assertEqual((version.numero, version.etat, version.name, version.description, version.duree_estimee_min, version.nb_personnes),
                         (1, Etat.VALIDEE, "Ancienne fiche", "Texte libre", 45, 3))
        fiche.refresh_from_db()
        self.assertEqual((fiche.periodicity, fiche.description, fiche.intervalle), ("3 mois", "Texte libre", 3))
        self.assertEqual(fiche.version_validee, version)

    def test_voie_historique_cree_une_version_validee_seulement_si_changement(self):
        fiche = InstallationMaintenance.objects.create(installation=self.installation, periodicity="1 an", title="Annuel", intervalle=1, unite_intervalle="A")
        v1 = fiche_maintenance.enregistrer_version_directe(fiche, self.chef_service, "Création")
        self.assertEqual((v1.numero, v1.etat), (1, Etat.VALIDEE))
        self.assertIsNone(fiche_maintenance.enregistrer_version_directe(fiche, self.chef_service, "Rien"))
        fiche.title = "Annuel révisé"
        fiche.save()
        v2 = fiche_maintenance.enregistrer_version_directe(fiche, self.chef_service, "Titre")
        self.assertEqual((v2.numero, v2.name), (2, "Annuel révisé"))


class GenerationEtExecutionTests(BaseFiches):
    def test_aucune_occurrence_tant_que_rien_n_est_valide_et_aucune_pour_une_fiche_flotte(self):
        from django.core.management import call_command

        self.soumettre()
        call_command("generate_installation_occurrences", days_ahead=3650)
        self.assertFalse(MaintenanceOccurrence.objects.exists())
        fiche = self.valider(self.installation.maintenances.get().versions.get()).fiche
        call_command("generate_installation_occurrences", days_ahead=3650)
        self.assertEqual(MaintenanceOccurrence.objects.filter(installation_maintenance=fiche).count(), 1)

    def test_l_execution_garde_la_version_utilisee(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        self.assertEqual([l.label for l in occ.lignes_fiche()], ["Plombage", "Pression"])
        execution = MaintenanceExecution.objects.create(occurrence=occ)
        v1 = fiche.version_validee
        self.assertEqual(execution.version_fiche, v1)
        contenu = fiche_maintenance.contenu_de(v1) | {"resume_modifications": "Ajout", "lignes": [{"label": "Seule ligne", "field_type": "checkbox"}]}
        self.valider(circuit.soumettre(self.chef_section, self.installation, contenu, fiche))
        occ = MaintenanceOccurrence.objects.get(pk=occ.pk)
        self.assertEqual(occ.version_fiche(), v1)
        autre = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        self.assertEqual([l.label for l in autre.lignes_fiche()], ["Seule ligne"])

    def test_fiche_imprimable_lit_la_version_validee(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        circuit.soumettre(self.chef_section, self.installation, self.contenu(
            resume_modifications="x", lignes=[{"label": "Non validée", "field_type": "checkbox"}]), fiche)
        self.client.force_login(self.chef_service)
        reponse = self.client.get(reverse("occurrence-imprimer", args=[occ.pk]))
        self.assertContains(reponse, "Plombage")
        self.assertContains(reponse, "Consigner la pompe")
        self.assertContains(reponse, "Haute pression")
        self.assertNotContains(reponse, "Non validée")

    def test_compte_rendu_affiche_les_lignes_de_la_fiche(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        self.client.force_login(self.chef_service)
        self.assertContains(self.client.get(reverse("occurrence-execute", args=[occ.pk])), "Pression")

    def test_modele_autonome_inchange_et_versions_hors_api(self):
        fiche = self.fiche_validee()
        autonome = ChecklistTemplate.objects.create(name="Autonome", sector=self.secteur)
        self.assertEqual(autonome.version_applicable(), autonome)
        self.assertEqual(fiche.version_validee.version_applicable(), fiche.version_validee)
        self.client.force_login(self.chef_service)
        reponse = self.client.get("/api/assets/checklist-templates/")
        noms = [t["name"] for t in reponse.json()]
        self.assertIn("Autonome", noms)
        self.assertNotIn("Entretien trimestriel", noms)


class GammesHeuresTests(BaseFiches):
    def test_heures_depuis_la_derniere_visite_par_gamme(self):
        mille = InstallationMaintenance.objects.create(
            installation=self.installation, periodicity="1 000 h", title="1 000 h", mode_declenchement="COMPTEUR",
            seuil_heures=1000, derniere_echeance_heures=Decimal("500"))
        deux_mille = InstallationMaintenance.objects.create(
            installation=self.installation, periodicity="2 000 h", title="2 000 h", mode_declenchement="COMPTEUR",
            seuil_heures=2000, derniere_echeance_heures=Decimal("0"))
        InstallationMaintenance.objects.create(installation=self.installation, periodicity="1 mois", title="Mensuelle", intervalle=1, unite_intervalle="M")
        releve = InstallationHourReading.objects.create(installation=self.installation, hours=Decimal("1200"))
        gammes = heures_par_gamme(list(self.installation.maintenances.all()), [releve])
        self.assertEqual([(g["fiche"], g["depuis_visite"], g["pourcentage"]) for g in gammes],
                         [(mille, Decimal("700"), 70), (deux_mille, Decimal("1200"), 60)])

    def test_page_installation_et_liste_montrent_les_gammes(self):
        InstallationMaintenance.objects.create(
            installation=self.installation, periodicity="1 000 h", title="Révision 1 000 h", mode_declenchement="COMPTEUR",
            seuil_heures=1000, derniere_echeance_heures=Decimal("500"))
        InstallationHourReading.objects.create(installation=self.installation, hours=Decimal("1200"))
        self.client.force_login(self.chef_service)
        detail = self.client.get(reverse("installation-detail", args=[self.installation.pk]))
        self.assertContains(detail, "Par gamme")
        self.assertContains(detail, reverse("fiche-detail", args=[self.installation.maintenances.get().pk]))
        liste = self.client.get(reverse("installation-list") + "?show_hours=1")
        self.assertContains(liste, "Gamme 1 000 h")


class EcransTests(BaseFiches):
    def donnees(self, **plus):
        donnees = {
            "name": "Entretien semestriel", "description": "", "mode_declenchement": "CALENDRIER", "intervalle": "6",
            "unite_intervalle": "M", "seuil_heures": "", "duree_estimee_min": "60", "nb_personnes": "2", "qualification": "",
            "prep_type": ["outil", "piece"], "prep_libelle": ["Clé", ""], "prep_quantite": ["1", "1"], "prep_piece": ["", ""],
            "etape_texte": ["Consigner", ""], "etape_attention": ["Danger", ""],
            "ligne_cle": ["", ""], "ligne_type": ["checkbox", "number"], "ligne_label": ["Plombage", "Pression"],
            "ligne_unite": ["", "bar"], "ligne_min": ["", "4,5"], "ligne_max": ["", "6"],
        }
        donnees.update(plus)
        return donnees

    def test_assistant_cree_une_fiche_et_ignore_les_lignes_vides(self):
        self.client.force_login(self.chef_section)
        url = reverse("fiche-nouvelle", args=[self.installation.pk])
        self.assertContains(self.client.get(url), "Gamme et identité")
        reponse = self.client.post(url, self.donnees())
        version = ChecklistTemplate.objects.get(name="Entretien semestriel")
        self.assertRedirects(reponse, f"{reverse('fiche-detail', args=[version.fiche_id])}?v=1")
        self.assertEqual((version.preparations.count(), version.etapes.count(), version.items.count()), (1, 1, 2))
        self.assertEqual(version.items.get(label="Pression").valeur_min, 4.5)
        self.assertEqual(version.redacteur, self.chef_section)

    def test_assistant_refuse_un_equipier_et_affiche_l_erreur_de_gamme(self):
        self.client.force_login(self.equipier)
        self.assertEqual(self.client.get(reverse("fiche-nouvelle", args=[self.installation.pk])).status_code, 403)
        self.fiche_validee()
        self.client.force_login(self.chef_section)
        reponse = self.client.post(reverse("fiche-nouvelle", args=[self.installation.pk]), self.donnees(intervalle="3"))
        self.assertContains(reponse, "Une fiche existe déjà pour la gamme")

    def test_detail_frise_et_visas(self):
        version = self.soumettre()
        url = reverse("fiche-detail", args=[version.fiche_id])
        self.client.force_login(self.chef_secteur)
        reponse = self.client.get(url)
        self.assertContains(reponse, "Aucune version validée")
        self.assertContains(reponse, "Commandant adjoint (COMAEQ)")
        self.assertContains(reponse, "Frégate")
        self.assertContains(reponse, reverse("fiche-viser", args=[version.pk]))
        self.assertContains(reponse, "Discussion")
        self.client.force_login(self.equipier)
        self.assertNotContains(self.client.get(url), reverse("fiche-viser", args=[version.pk]))
        self.client.force_login(self.chef_secteur)
        self.client.post(reverse("fiche-viser", args=[version.pk]), {"etape": Etat.VISA_SECTEUR})
        version.refresh_from_db()
        self.assertEqual(version.etat, Etat.VISA_SERVICE)

    def test_refus_depuis_l_ecran(self):
        version = self.soumettre()
        self.client.force_login(self.chef_secteur)
        self.client.post(reverse("fiche-refuser", args=[version.pk]), {"etape": Etat.VISA_SECTEUR, "motif": ""})
        version.refresh_from_db()
        self.assertEqual(version.etat, Etat.VISA_SECTEUR)
        self.client.post(reverse("fiche-refuser", args=[version.pk]), {"etape": Etat.VISA_SECTEUR, "motif": "Incomplet"})
        version.refresh_from_db()
        self.assertEqual(version.etat, Etat.REFUSEE)
        self.client.force_login(self.chef_section)
        self.assertContains(self.client.get(reverse("fiche-detail", args=[version.fiche_id])), "Incomplet")
        self.assertEqual(self.client.get(reverse("fiche-modifier", args=[version.fiche_id])).status_code, 200)

    def test_perimetre_fiche_hors_perimetre_introuvable(self):
        version = self.soumettre()
        autre_navire = Ship.objects.create(name="Autre", code="AUT")
        etranger = self._u("etranger", "CHEF_SERVICE", ship=autre_navire)
        self.client.force_login(etranger)
        self.assertEqual(self.client.get(reverse("fiche-detail", args=[version.fiche_id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("fiche-viser", args=[version.pk]), {"etape": Etat.VISA_SECTEUR}).status_code, 404)
        self.assertEqual(self.client.post(reverse("fiche-dupliquer", args=[version.fiche_id]), {"installation": self.autre.pk}).status_code, 404)

    def test_dupliquer_depuis_l_ecran(self):
        fiche = self.fiche_validee()
        self.client.force_login(self.chef_section)
        self.assertContains(self.client.get(reverse("fiche-detail", args=[fiche.pk])), "Copier vers une autre installation")
        self.client.post(reverse("fiche-dupliquer", args=[fiche.pk]), {"installation": "pas-un-uuid"})
        self.assertEqual(InstallationMaintenance.objects.count(), 1)
        self.client.post(reverse("fiche-dupliquer", args=[fiche.pk]), {"installation": self.autre.pk})
        self.assertEqual(InstallationMaintenance.objects.filter(installation=self.autre).count(), 1)

    def test_lien_de_notification_vers_la_fiche(self):
        from notifications.liens import liens_accessibles
        from django.test import RequestFactory

        version = self.soumettre()
        notification = Notification.objects.get(user=self.chef_secteur, object_id=str(version.pk))
        requete = RequestFactory().get("/")
        requete.user = self.chef_secteur
        self.assertEqual(liens_accessibles(requete, [notification])[notification.pk],
                         f"{reverse('fiche-detail', args=[version.fiche_id])}?v=1")

    def test_commentaire_de_discussion(self):
        fiche = self.fiche_validee()
        self.client.force_login(self.chef_section)
        self.client.post(reverse("fiche-comment-create", args=[fiche.pk]), {"body": "Pensez au joint"})
        self.assertContains(self.client.get(reverse("fiche-detail", args=[fiche.pk])), "Pensez au joint")


class VoieDirecteTests(BaseFiches):
    def test_modification_directe_refusee_tant_qu_une_version_est_en_circuit(self):
        fiche = self.fiche_validee()
        circuit.soumettre(self.chef_section, self.installation, self.contenu(resume_modifications="Changement", intervalle=6), fiche)
        fiche.refresh_from_db()
        fiche.title = "Titre direct"
        fiche.save()
        with self.assertRaisesMessage(ErreurCircuit, "en cours de validation"):
            fiche_maintenance.enregistrer_version_directe(fiche, self.chef_service, "Direct")
        self.assertEqual(fiche.versions.count(), 2)

    def test_modification_directe_via_l_ecran_affiche_le_refus_et_annule(self):
        fiche = self.fiche_validee()
        circuit.soumettre(self.chef_section, self.installation, self.contenu(resume_modifications="Changement", intervalle=6), fiche)
        self.client.force_login(self.chef_service)
        self.client.post(reverse("installation-detail", args=[self.installation.pk]), {
            "action": "edit_maintenance", "maintenance_id": fiche.pk, "title": "Titre direct"})
        fiche.refresh_from_db()
        self.assertEqual(fiche.title, "Entretien trimestriel")

    def test_modification_directe_trace_l_auteur_et_se_fonde_sur_la_date_de_validation(self):
        fiche = self.fiche_validee()
        fiche.title = "Direct"
        fiche.save()
        v2 = fiche_maintenance.enregistrer_version_directe(fiche, self.chef_service, "Raison")
        evenement = v2.evenements.get()
        self.assertEqual((evenement.user, evenement.motif), (self.chef_service, "Raison"))
        self.assertTrue(AuditLog.objects.filter(action="fiche.version.directe", actor=self.chef_service).exists())
        self.assertEqual(fiche.version_validee, v2)
        ChecklistTemplate.objects.exclude(pk=v2.pk).filter(fiche=fiche).update(valide_le="2999-01-01T00:00:00Z")
        self.assertEqual(fiche.version_validee.numero, 1)

    def test_deuxieme_fiche_de_meme_gamme_refusee(self):
        InstallationMaintenance.objects.create(installation=self.installation, periodicity="Mensuelle", title="A")
        doublon = InstallationMaintenance.objects.create(installation=self.installation, periodicity="mensuelle", title="B")
        with self.assertRaisesMessage(ErreurCircuit, "existe déjà"):
            fiche_maintenance.enregistrer_version_directe(doublon, self.chef_service, "Création")
        InstallationMaintenance.objects.filter(pk=doublon.pk).update(periodicity="Annuelle")
        self.assertIsNotNone(fiche_maintenance.enregistrer_version_directe(doublon, self.chef_service, "Création"))


class EntreesForgeesTests(BaseFiches):
    def poster(self, **plus):
        donnees = {
            "name": "Fiche", "mode_declenchement": "CALENDRIER", "intervalle": "3", "unite_intervalle": "M",
            "duree_estimee_min": "10", "nb_personnes": "1",
            "prep_type": ["piece"], "prep_libelle": ["Joint"], "prep_quantite": ["1"], "prep_piece": [""],
            "etape_texte": ["Faire"], "etape_attention": [""],
            "ligne_cle": [""], "ligne_type": ["checkbox"], "ligne_label": ["Point"], "ligne_unite": [""],
            "ligne_min": [""], "ligne_max": [""],
        }
        donnees.update(plus)
        self.client.force_login(self.chef_section)
        reponse = self.client.post(reverse("fiche-nouvelle", args=[self.installation.pk]), donnees)
        self.assertEqual(reponse.status_code, 200, "attendu : message d'erreur, pas de redirection ni d'erreur serveur")
        self.assertFalse(InstallationMaintenance.objects.exists())
        return reponse

    def test_entrees_invalides(self):
        from logistics.models import StockPiece
        import uuid

        autre = Ship.objects.create(name="Autre", code="AUT")
        autre_service = Service.objects.create(ship=autre, name="S")
        piece = StockPiece.objects.create(ship=autre, service=autre_service, sector=Sector.objects.create(service=autre_service, name="X"),
                                          reference="R", designation="D")
        cas = {
            "qualification inconnue": ({"qualification": "9999"}, "Qualification inconnue"),
            "pièce d'un autre navire": ({"prep_piece": [str(piece.pk)]}, "Pièce inconnue"),
            "pièce inexistante": ({"prep_piece": ["9999"]}, "Pièce inconnue"),
            "clé illisible": ({"ligne_cle": ["pas-un-uuid"]}, "Identifiant de ligne invalide"),
            "clé inconnue": ({"ligne_cle": [str(uuid.uuid4())]}, "Identifiant de ligne inconnu"),
            "unité inconnue": ({"unite_intervalle": "Z"}, "Unité de périodicité inconnue"),
            "titre trop long": ({"name": "x" * 256}, "255 caractères"),
            "libellé trop long": ({"ligne_label": ["x" * 256]}, "trop long"),
            "unité de relevé trop longue": ({"ligne_unite": ["x" * 51]}, "trop long"),
            "entier hors bornes": ({"intervalle": "99999999999999999999"}, "hors limites"),
            "durée négative": ({"duree_estimee_min": "-5"}, "hors limites"),
            "quantité hors bornes": ({"prep_quantite": ["99999999999"]}, "hors limites"),
            "minimum au-dessus du maximum": ({"ligne_type": ["number"], "ligne_min": ["9"], "ligne_max": ["1"]}, "minimum dépasse"),
            "entier illisible": ({"seuil_heures": "12abc"}, "pas un nombre entier"),
        }
        for nom, (donnees, message) in cas.items():
            with self.subTest(nom):
                self.assertContains(self.poster(**donnees), message)

    def test_valeur_non_finie_ignoree(self):
        from assets.fiche_web import lire_formulaire
        from django.http import QueryDict

        contenu = lire_formulaire(QueryDict("ligne_cle=&ligne_unite=&ligne_label=Pression&ligne_type=number&ligne_min=nan&ligne_max=inf"))
        self.assertEqual((contenu["lignes"][0]["valeur_min"], contenu["lignes"][0]["valeur_max"]), (None, None))

    def test_la_cle_d_une_ligne_connue_est_conservee_en_uuid(self):
        fiche = self.fiche_validee()
        ligne = fiche.version_validee.items.get(label="Plombage")
        self.client.force_login(self.chef_section)
        donnees = {
            "name": "Fiche", "mode_declenchement": "CALENDRIER", "intervalle": "3", "unite_intervalle": "M",
            "duree_estimee_min": "10", "nb_personnes": "1", "resume_modifications": "Renommage",
            "ligne_cle": [str(ligne.cle)], "ligne_type": ["checkbox"], "ligne_label": ["Plombage renommé"],
            "ligne_unite": [""], "ligne_min": [""], "ligne_max": [""],
        }
        self.client.post(reverse("fiche-modifier", args=[fiche.pk]), donnees)
        v2 = fiche.versions.get(numero=2)
        self.assertEqual(v2.items.get().cle, ligne.cle)
        corrige = fiche_maintenance.contenu_de(v2)
        corrige["lignes"][0]["label"] = "Corrigé"
        v2.etat = Etat.REFUSEE
        v2.save()
        fiche_maintenance.remplacer_contenu(v2, corrige)
        self.assertEqual(v2.items.get().cle, ligne.cle)
        self.assertEqual(v2.items.count(), 1)


class ApiLignesTests(BaseFiches):
    def test_les_lignes_d_une_version_ne_se_modifient_pas_par_l_api(self):
        fiche = self.fiche_validee()
        version = fiche.version_validee
        ligne = version.items.first()
        modele = ChecklistTemplate.objects.create(name="Autonome", sector=self.secteur)
        item = modele.items.create(label="Point")
        self.client.force_login(self.chef_service)
        url = "/api/assets/checklist-items/"
        self.assertEqual(self.client.post(url, {"template": version.pk, "label": "Intrus"}).status_code, 400)
        self.assertEqual(self.client.patch(f"{url}{ligne.pk}/", {"label": "Piraté"}, content_type="application/json").status_code, 404)
        self.assertEqual(self.client.patch(f"{url}{item.pk}/", {"template": version.pk}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(url, {"template": modele.pk, "label": "Bon"}).status_code, 201)
        self.assertEqual(version.items.count(), 2)
        ligne.refresh_from_db()
        self.assertEqual(ligne.label, "Plombage")
