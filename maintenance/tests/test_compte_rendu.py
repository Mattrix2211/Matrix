"""Compte rendu de maintenance saisi sur PC (UX-3.5) et exécution en direct (UX-3.6)."""
import json
import shutil
import uuid
import subprocess
import unittest
from pathlib import Path

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, Roles, UserProfile
from assets.models import (
    Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate, Installation, InstallationMaintenance,
    ModeDeclenchement,
)
from maintenance.compte_rendu import lire_nombre, lire_saisie, resume, valeur_de
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from notifications.models import Notification
from org.models import Sector, Service, Ship


class LectureSaisieTests(SimpleTestCase):
    class Ligne:
        def __init__(self, id, label, field_type, required=False, mini=None, maxi=None):
            self.id, self.label, self.field_type, self.required = id, label, field_type, required
            self.cle = uuid.UUID(int=id)
            self.valeur_min, self.valeur_max = mini, maxi

    def test_virgule_francaise(self):
        self.assertEqual(lire_nombre("4,2"), 4.2)
        self.assertIsNone(lire_nombre(" "))
        with self.assertRaises(ValueError):
            lire_nombre("abc")

    def test_lecture_et_resume(self):
        items = [
            self.Ligne(1, "Goupille", "checkbox"), self.Ligne(2, "Fuite", "checkbox"),
            self.Ligne(3, "Pression", "number", mini=3, maxi=5),
        ]
        results, mesures, erreurs = lire_saisie(items, {
            "item_1": "conforme", "item_2": "non_conforme", "commentaire_2": "Suintement", "item_3": "5,5",
        })
        self.assertEqual(erreurs, [])
        self.assertEqual(results[str(items[1].cle)], {"etat": "non_conforme", "commentaire": "Suintement"})
        self.assertEqual(mesures, {str(items[2].cle): 5.5})
        self.assertEqual(resume(items, results, mesures)["texte"], "2/2 contrôles, 1 non conforme, 1 relevé à surveiller")

    def test_valeurs_non_finies_et_anciens_libelles(self):
        for texte in ("nan", "inf", "-inf", "1e999"):
            with self.assertRaises(ValueError):
                lire_nombre(texte)
        pression = self.Ligne(3, "Pression", "number")
        self.assertEqual(valeur_de({"Pression": 4.0}, pression), 4.0)
        self.assertEqual(valeur_de({str(pression.cle): 5.0, "Pression": 4.0}, pression), 5.0)
        self.assertIsNone(valeur_de(["pas", "un dict"], pression))

    def test_ligne_obligatoire_et_valeur_illisible(self):
        items = [self.Ligne(1, "Goupille", "checkbox", required=True), self.Ligne(2, "Pression", "number")]
        _, _, erreurs = lire_saisie(items, {"item_2": "x"})
        self.assertEqual(len(erreurs), 2)
        _, _, erreurs = lire_saisie(items, {}, exiger_complet=False)
        self.assertEqual(erreurs, [])


class CompteRenduWebTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire compte rendu", code="NT-CR")
        self.service = Service.objects.create(ship=self.ship, name="Service CR")
        self.sector = Sector.objects.create(service=self.service, name="Secteur CR")
        self.tech = User.objects.create_user(username="tech_cr", password="MotDePasseCorrect1")
        UserProfile.objects.update_or_create(user=self.tech, defaults={"ship": self.ship})
        self.chef = User.objects.create_user(username="chef_cr", password="x")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"ship": self.ship, "role": Roles.CHEF_SECTEUR, "sector": self.sector, "service": self.service},
        )
        type_actif = AssetType.objects.create(name="Extincteur CR", category="Incendie", sector=self.sector)
        self.asset = Asset.objects.create(asset_type=type_actif, ship=self.ship, service=self.service, sector=self.sector)
        modele = ChecklistTemplate.objects.create(name="Gamme CR", sector=self.sector)
        self.goupille = ChecklistItemTemplate.objects.create(template=modele, label="Goupille", field_type="checkbox", order=1)
        self.pression = ChecklistItemTemplate.objects.create(
            template=modele, label="Pression", field_type="number", unit="bar", valeur_min=3, valeur_max=5, order=2,
        )
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Contrôle CR", every_n_days=30, checklist_template=modele)
        self.occ = MaintenanceOccurrence.objects.create(plan=plan, asset=self.asset, scheduled_for=timezone.localdate(), status="ASSIGNED")
        self.occ.assignees.add(self.tech)
        self.client.login(username="tech_cr", password="MotDePasseCorrect1")
        self.url = reverse("occurrence-execute", args=[self.occ.pk])

    def _saisie(self, **extra):
        donnees = {
            f"item_{self.goupille.pk}": "conforme", f"item_{self.pression.pk}": "4,2", "conformity": "CONFORME",
        }
        donnees.update(extra)
        return donnees

    def test_page_dans_l_ordre_de_la_fiche_papier(self):
        r = self.client.get(self.url)
        contenu = r.content.decode()
        self.assertLess(contenu.index("Goupille"), contenu.index("Pression"))
        self.assertContains(r, "Tout conforme")
        self.assertContains(r, "Terminer la maintenance")
        self.assertContains(r, 'data-brouillon="compte-rendu:')
        self.assertContains(r, "attendu : 3 à 5")

    def test_saisie_complete_notifie_le_chef_de_secteur(self):
        self.client.post(self.url, self._saisie(notes="RAS", intervenants=[str(self.tech.pk)]))
        execution = MaintenanceExecution.objects.get(occurrence=self.occ)
        self.assertEqual(execution.results[str(self.goupille.cle)]["etat"], "conforme")
        self.assertEqual(execution.measurements[str(self.pression.cle)], 4.2)
        self.assertEqual(list(execution.intervenants.all()), [self.tech])
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "DONE")
        notification = Notification.objects.get(user=self.chef)
        self.assertIn("Compte rendu saisi", notification.verb)
        self.assertFalse(Notification.objects.filter(user=self.tech).exists())

    def test_conformite_obligatoire_et_valeur_illisible(self):
        r = self.client.post(self.url, self._saisie(conformity="", **{f"item_{self.pression.pk}": "abc"}))
        self.assertContains(r, "conformité finale est à déclarer")
        self.assertContains(r, "valeur numérique illisible")
        self.assertFalse(MaintenanceExecution.objects.exists())

    def test_enregistrement_en_direct_sans_cloture(self):
        self.client.post(self.url, {f"item_{self.goupille.pk}": "conforme", "action": "enregistrer"}, HTTP_HX_REQUEST="true")
        execution = MaintenanceExecution.objects.get(occurrence=self.occ)
        self.assertIsNone(execution.completed_at)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "IN_PROGRESS")
        self.assertFalse(Notification.objects.exists())
        # La saisie enregistrée est reprise à la réouverture.
        self.assertContains(self.client.get(self.url), "checked")

    def test_marin_ne_corrige_pas_son_compte_rendu_termine(self):
        self.client.post(self.url, self._saisie())
        r = self.client.post(self.url, self._saisie(**{f"item_{self.pression.pk}": "6", "motif": "Erreur"}))
        self.assertEqual(r.status_code, 302)
        execution = MaintenanceExecution.objects.get(occurrence=self.occ)
        self.assertEqual(execution.measurements[str(self.pression.cle)], 4.2)
        self.assertFalse(AuditLog.objects.filter(action="occurrence_compte_rendu_modifie").exists())
        self.assertContains(self.client.get(self.url), "Seul un chef de secteur peut le corriger")

    def test_correction_par_le_chef_tracee_et_origine_conservee(self):
        self.client.post(self.url, self._saisie(notes="RAS"))
        self.client.logout()
        self.client.login(username="chef_cr", password="x")
        r = self.client.post(self.url, self._saisie(**{f"item_{self.pression.pk}": "6"}))
        self.assertContains(r, "motif de la modification est obligatoire")
        correction = self._saisie(**{f"item_{self.pression.pk}": "6", "motif": "Erreur de lecture", "notes": "RAS"})
        self.client.post(self.url, correction)
        entree = AuditLog.objects.get(action="occurrence_compte_rendu_modifie")
        self.assertIn("Erreur de lecture", entree.details)
        modifs = json.loads(entree.details.split("modifications=")[1])
        self.assertEqual(modifs["releves"], {"avant": {"Pression": 4.2}, "apres": {"Pression": 6.0}})
        execution = MaintenanceExecution.objects.get(occurrence=self.occ)
        self.assertEqual(execution.executed_by, self.tech)
        self.assertEqual(execution.saisie_origine["measurements"], {str(self.pression.cle): 4.2})
        self.assertEqual(execution.saisie_origine["par"], self.tech.pk)
        trace = execution.modifications.get()
        self.assertEqual((trace.auteur, trace.motif), (self.chef, "Erreur de lecture"))
        self.assertEqual(trace.modifications["Pression"], {"avant": 4.2, "apres": 6.0})
        # Le marin d'origine est prévenu de la correction.
        self.assertTrue(Notification.objects.filter(user=self.tech, verb__startswith="Compte rendu modifié").exists())
        # Rejouer la même correction ne crée ni trace ni notification de plus.
        self.client.post(self.url, correction)
        self.assertEqual(execution.modifications.count(), 1)

    def test_double_envoi_du_marin_ne_cree_qu_un_compte_rendu(self):
        self.client.post(self.url, self._saisie())
        r = self.client.post(self.url, self._saisie())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(MaintenanceExecution.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.chef).count(), 1)

    def test_nul_et_notes_trop_longues_refuses_sans_erreur_serveur(self):
        r = self.client.post(self.url, self._saisie(notes="x" * 10001))
        self.assertContains(r, "limitées à")
        self.client.post(self.url, self._saisie(notes="a\x00b"))
        self.assertEqual(MaintenanceExecution.objects.get(occurrence=self.occ).notes, "ab")

    def test_valeur_non_finie_refusee(self):
        r = self.client.post(self.url, self._saisie(**{f"item_{self.pression.pk}": "nan"}))
        self.assertContains(r, "valeur numérique illisible")

    def test_mot_de_passe_seulement_pour_installation_critique(self):
        installation = Installation.objects.create(
            designation="Groupe CR", ship=self.ship, service=self.service, sector=self.sector, critique=True,
        )
        maintenance = InstallationMaintenance.objects.create(
            installation=installation, periodicity="1 mois", title="Contrôle", mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1, unite_intervalle="M",
        )
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED")
        occ.assignees.add(self.tech)
        url = reverse("occurrence-execute", args=[occ.pk])
        # Enregistrer en cours d'exécution ne demande aucun mot de passe.
        self.client.post(url, {"action": "enregistrer"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "IN_PROGRESS")
        # La clôture le demande.
        self.client.post(url, {"conformity": "CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "IN_PROGRESS")
        self.client.post(url, {"conformity": "CONFORME", "mot_de_passe": "MotDePasseCorrect1"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")
        self.assertEqual(MaintenanceExecution.objects.get(occurrence=occ).valide_par, self.tech)


@unittest.skipUnless(shutil.which("node"), "node absent : logique JS vérifiée par le QA dans le navigateur")
class CompteRenduJsTests(SimpleTestCase):
    def test_logique_pure(self):
        script = Path(__file__).resolve().parents[2] / "matrix" / "tests" / "compte_rendu.test.js"
        resultat = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
