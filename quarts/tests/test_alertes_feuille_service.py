"""Tests de l'organisation d'alerte (sécurité / protection-défense) de la feuille
de service : résolution fonction -> titulaire, postes obligatoires non armés,
circuit proposer -> valider, droits et traçabilité."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog
from notifications.models import Notification
from org.models import CommandantAdjoint, CommandantEnSecond, RoleThresholdConfig
from quarts import alertes
from quarts.models import (
    FeuilleService,
    ModificationOrganisationAlerte as Modification,
    PosteAlerte,
    ScenarioAlerte,
)
from quarts.tests.test_feuille_service import FeuilleServiceTestsBase, _utilisateur


class AlertesBase(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.scenario = ScenarioAlerte.objects.create(
            ship=self.ship, libelle="Alerte intrus", famille=ScenarioAlerte.FAMILLE_PROTECTION,
        )
        self.poste = PosteAlerte.objects.create(
            scenario=self.scenario, libelle="PC sécu", fonction=self.fonction, obligatoire=True,
        )

    def _donnees(self, **surcharge):
        donnees = {
            "libelle": "Alerte incendie", "famille": "SECURITE", "adjoint_sigle": "", "ordre": 1, "actif": True,
            "postes": [{"libelle": "Directeur de lutte", "fonction_id": self.fonction.pk, "obligatoire": True, "ordre": 0}],
        }
        donnees.update(surcharge)
        return donnees


class EtatAlertesTests(AlertesBase):
    def test_poste_obligatoire_non_arme_sans_titulaire(self):
        etat = alertes.etat_alertes(self.ship, self.jour)
        self.assertEqual(len(etat[0]["non_armes"]), 1)
        self.assertFalse(etat[0]["postes"][0]["arme"])

    def test_poste_arme_par_le_titulaire_du_jour(self):
        self._publier_tour(marin=self.marin_service)
        etat = alertes.etat_alertes(self.ship, self.jour)
        self.assertTrue(etat[0]["postes"][0]["arme"])
        self.assertEqual(etat[0]["postes"][0]["creneau"].marin, self.marin_service)
        self.assertEqual(etat[0]["non_armes"], [])

    def test_poste_facultatif_non_arme_n_est_pas_signale(self):
        self.poste.obligatoire = False
        self.poste.save()
        self.assertEqual(alertes.etat_alertes(self.ship, self.jour)[0]["non_armes"], [])

    def test_scenario_inactif_ignore(self):
        self.scenario.actif = False
        self.scenario.save()
        self.assertEqual(alertes.etat_alertes(self.ship, self.jour), [])

    def test_coma_responsable_par_defaut_selon_la_famille(self):
        self.assertEqual(self.scenario.adjoint_responsable, "COMAEQ")
        securite = ScenarioAlerte.objects.create(ship=self.ship, libelle="Voie d'eau")
        self.assertEqual(securite.adjoint_responsable, "COMANAV")
        securite.adjoint_sigle = "COMOPS"
        self.assertEqual(securite.adjoint_responsable, "COMOPS")


class PublicationTests(AlertesBase):
    def _feuille(self):
        return FeuilleService.objects.create(ship=self.ship, date=self.jour, created_by=self.equipier)

    def test_publication_signale_les_postes_non_armes_sans_reaffecter(self):
        coma = _utilisateur("coma_eq", "ETAT_MAJOR", ship=self.ship)
        CommandantAdjoint.objects.create(ship=self.ship, sigle="COMAEQ", titulaire=coma)
        feuille = self._feuille()
        feuille.viser_comaeq(self.commandant)
        self.assertTrue(Notification.objects.filter(user=coma, verb__contains="non armés").exists())
        self.assertTrue(Notification.objects.filter(user=self.equipier, verb__contains="non armés").exists())
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_postes_alerte_non_armes").exists())
        self.assertIsNone(alertes.etat_alertes(self.ship, self.jour)[0]["postes"][0]["creneau"])

    def test_publication_sans_probleme_ne_notifie_pas(self):
        self._publier_tour(marin=self.marin_service)
        self._feuille().viser_comaeq(self.commandant)
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_postes_alerte_non_armes").exists())

    def test_version_figee_contient_les_alertes(self):
        self._publier_tour(marin=self.marin_service)
        feuille = self._feuille()
        feuille.viser_comaeq(self.commandant)
        figees = feuille.versions.first().contenu_fige["alertes"]
        self.assertEqual(figees[0]["scenario"], "Alerte intrus")
        self.assertIn("marin_service", figees[0]["postes"][0]["marin"])

    def test_la_feuille_affiche_les_postes_non_armes(self):
        self.client.force_login(self.equipier)
        reponse = self.client.get(reverse(
            "feuille-service-detail", kwargs={"ship_id": self.ship.pk, "date_str": self.jour.isoformat()}
        ))
        self.assertContains(reponse, "Alerte intrus")
        self.assertContains(reponse, "Non armé")


class CircuitModificationTests(AlertesBase):
    def test_le_bsc_ne_modifie_pas_seul_une_organisation_permanente(self):
        RoleThresholdConfig.objects.create(ship=self.ship, thresholds={"feuille_service_configuration": "EQUIPIER"})
        modification, erreur = alertes.proposer_modification(
            self.equipier, self.ship, Modification.ACTION_CREER, self._donnees(),
        )
        self.assertIsNone(erreur)
        self.assertEqual(modification.statut, Modification.STATUT_EN_ATTENTE)
        self.assertFalse(ScenarioAlerte.objects.filter(libelle="Alerte incendie").exists())
        self.assertTrue(Notification.objects.filter(user=self.commandant, verb__contains="validation").exists())

    def test_validation_applique_et_trace(self):
        modification, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_CREER, self._donnees(),
        )
        alertes.valider(modification, self.commandant)
        scenario = ScenarioAlerte.objects.get(libelle="Alerte incendie")
        self.assertEqual(scenario.postes.count(), 1)
        modification.refresh_from_db()
        self.assertEqual(modification.statut, Modification.STATUT_VALIDEE)
        self.assertEqual(modification.decidee_par, self.commandant)
        self.assertTrue(AuditLog.objects.filter(action="alerte_organisation_validee").exists())
        self.assertTrue(Notification.objects.filter(user=self.chef_service, verb__contains="validée").exists())

    def test_refus_avec_motif_conserve_l_organisation(self):
        modification, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_SUPPRIMER, scenario=self.scenario,
        )
        alertes.refuser(modification, self.commandant, "Pas maintenant")
        self.assertTrue(ScenarioAlerte.objects.filter(pk=self.scenario.pk).exists())
        modification.refresh_from_db()
        self.assertEqual(modification.motif_refus, "Pas maintenant")

    def test_l_autorite_applique_directement_mais_la_demande_est_conservee(self):
        modification, _ = alertes.proposer_modification(
            self.commandant, self.ship, Modification.ACTION_MODIFIER,
            self._donnees(libelle="Alerte intrus 2"), self.scenario,
        )
        self.assertEqual(modification.statut, Modification.STATUT_VALIDEE)
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.libelle, "Alerte intrus 2")

    def test_suppression_validee(self):
        modification, _ = alertes.proposer_modification(
            self.commandant, self.ship, Modification.ACTION_SUPPRIMER, scenario=self.scenario,
        )
        self.assertFalse(ScenarioAlerte.objects.filter(pk=self.scenario.pk).exists())
        modification.refresh_from_db()
        self.assertEqual(modification.donnees["libelle"], "Alerte intrus")

    def test_fonction_d_un_autre_navire_refusee(self):
        from quarts.models import FonctionFeuilleService
        etrangere = FonctionFeuilleService.objects.create(ship=self.autre_ship, libelle="Autre")
        postes = [{"libelle": "X", "fonction_id": etrangere.pk, "obligatoire": True, "ordre": 0}]
        modification, erreur = alertes.proposer_modification(
            self.commandant, self.ship, Modification.ACTION_CREER, self._donnees(postes=postes),
        )
        self.assertIsNone(modification)
        self.assertIn("Fonction", erreur)

    def test_nom_en_double_refuse(self):
        _, erreur = alertes.proposer_modification(
            self.commandant, self.ship, Modification.ACTION_CREER, self._donnees(libelle="Alerte intrus"),
        )
        self.assertIn("déjà", erreur)

    def test_validation_revérifie_le_nom_en_double(self):
        premiere, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_CREER, self._donnees(),
        )
        seconde, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_CREER, self._donnees(),
        )
        self.assertIsNone(alertes.valider(premiere, self.commandant))
        erreur = alertes.valider(seconde, self.commandant)
        self.assertIn("déjà", erreur)
        self.assertEqual(ScenarioAlerte.objects.filter(libelle="Alerte incendie").count(), 1)
        seconde.refresh_from_db()
        self.assertEqual(seconde.statut, Modification.STATUT_EN_ATTENTE)

    def test_validation_revérifie_la_fonction_supprimée(self):
        from quarts.models import FonctionFeuilleService
        temporaire = FonctionFeuilleService.objects.create(ship=self.ship, libelle="Temporaire")
        postes = [{"libelle": "X", "fonction_id": temporaire.pk, "obligatoire": True, "ordre": 0}]
        modification, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_CREER, self._donnees(postes=postes),
        )
        temporaire.delete()
        erreur = alertes.valider(modification, self.commandant)
        self.assertIn("Fonction", erreur)
        self.assertFalse(ScenarioAlerte.objects.filter(libelle="Alerte incendie").exists())
        self.assertFalse(PosteAlerte.objects.filter(libelle="X").exists())

    def test_modification_dont_le_scénario_a_disparu(self):
        modification, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_MODIFIER,
            self._donnees(libelle="Alerte intrus 2"), self.scenario,
        )
        self.scenario.delete()
        modification.refresh_from_db()
        erreur = alertes.valider(modification, self.commandant)
        self.assertIn("n'existe plus", erreur)
        self.assertFalse(ScenarioAlerte.objects.exists())
        self.assertEqual(modification.statut, Modification.STATUT_EN_ATTENTE)

    def test_commandant_en_second_valide_seulement_si_le_navire_lui_confie_le_droit(self):
        second = _utilisateur("second", "ETAT_MAJOR", ship=self.ship)
        CommandantEnSecond.objects.create(ship=self.ship, titulaire=second)
        self.assertFalse(alertes.peut_valider_organisation_alerte(second, self.ship))
        RoleThresholdConfig.objects.create(ship=self.ship, droits_en_second=["alerte_organisation_validation"])
        self.assertTrue(alertes.peut_valider_organisation_alerte(second, self.ship))
        self.assertFalse(alertes.peut_valider_organisation_alerte(self.etat_major, self.ship))

    def test_autorite_d_un_autre_navire_sans_droit(self):
        etranger = _utilisateur("cdt_autre", "COMMANDANT", ship=self.autre_ship)
        self.assertFalse(alertes.peut_valider_organisation_alerte(etranger, self.ship))
        self.assertFalse(alertes.peut_proposer_organisation_alerte(etranger, self.ship))


class VueOrganisationAlerteTests(AlertesBase):
    def _poster(self, user, **donnees):
        self.client.force_login(user)
        return self.client.post(reverse("feuille-service-alertes"), {"ship": self.ship.pk, **donnees})

    def test_equipier_interdit(self):
        self.client.force_login(self.equipier)
        self.assertEqual(self.client.get(reverse("feuille-service-alertes"), {"ship": self.ship.pk}).status_code, 403)

    def test_chef_de_service_propose_puis_commandant_valide(self):
        self._poster(
            self.chef_service, action="enregistrer", libelle="Alerte foule", famille="PROTECTION",
            ordre="2", actif="on", poste_libelle=["Accueil", ""], poste_fonction=[str(self.fonction.pk), ""],
            poste_obligatoire=["1", "1"],
        )
        modification = Modification.objects.get(statut=Modification.STATUT_EN_ATTENTE)
        self.assertEqual(len(modification.donnees["postes"]), 1)
        reponse = self._poster(self.commandant, action="valider", pk=modification.pk)
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(ScenarioAlerte.objects.filter(libelle="Alerte foule").exists())

    def test_validation_en_erreur_affiche_un_message_sans_500(self):
        donnees = self._donnees()
        premiere, _ = alertes.proposer_modification(self.chef_service, self.ship, Modification.ACTION_CREER, donnees)
        seconde, _ = alertes.proposer_modification(self.chef_service, self.ship, Modification.ACTION_CREER, donnees)
        self._poster(self.commandant, action="valider", pk=premiere.pk)
        reponse = self._poster(self.commandant, action="valider", pk=seconde.pk)
        self.assertEqual(reponse.status_code, 302)
        seconde.refresh_from_db()
        self.assertEqual(seconde.statut, Modification.STATUT_EN_ATTENTE)

    def test_chef_de_service_ne_peut_pas_valider(self):
        modification, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_SUPPRIMER, scenario=self.scenario,
        )
        self.assertEqual(self._poster(self.chef_service, action="valider", pk=modification.pk).status_code, 403)
        self.assertTrue(ScenarioAlerte.objects.filter(pk=self.scenario.pk).exists())

    def test_refus_sans_motif_ignore(self):
        modification, _ = alertes.proposer_modification(
            self.chef_service, self.ship, Modification.ACTION_SUPPRIMER, scenario=self.scenario,
        )
        self._poster(self.commandant, action="refuser", pk=modification.pk, motif="")
        modification.refresh_from_db()
        self.assertEqual(modification.statut, Modification.STATUT_EN_ATTENTE)

    def test_page_affichee_pour_le_commandant(self):
        self.client.force_login(self.commandant)
        reponse = self.client.get(reverse("feuille-service-alertes"), {"ship": self.ship.pk})
        self.assertContains(reponse, "Alerte intrus")
