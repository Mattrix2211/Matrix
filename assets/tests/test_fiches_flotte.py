"""Fiches flotte : catégorie la plus proche, circuit en six étapes, voie directe, adaptation locale, signalements, comparaison."""
from datetime import date, timedelta
from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from accounts.models import AuditLog, ResponsableSpecialite, SpecialityChoice
from assets import fiche_adaptation, fiche_comparaison, fiche_flotte, fiche_maintenance, fiche_signalement, fiche_validation as circuit
from assets.models import (
    ArticleCatalogue, Asset, AssetType, CategorieCatalogue, ChecklistTemplate, ChefResponsableSpecialite, InstallationMaintenance,
    SignalementFiche,
)
from assets.proposition_article import ErreurCircuit
from assets.tests.test_fiches_maintenance import BaseFiches
from dashboard.aujourdhui import a_faire
from maintenance import tasks, tournee
from maintenance.models import MaintenanceOccurrence
from notifications.models import Notification

Etat = ChecklistTemplate.Etat
migration = import_module("assets.migrations.0038_fiches_niveau_coherent")


class BaseFlotte(BaseFiches):
    def setUp(self):
        super().setUp()
        self.spe = SpecialityChoice.objects.create(name="Sécurité")
        self.parent = CategorieCatalogue.objects.create(nom="Extincteurs", specialite=self.spe)
        self.enfant = CategorieCatalogue.objects.create(nom="Extincteurs CO2", specialite=self.spe, parent=self.parent)
        self.resp = self._u("resp", "EQUIPIER")
        self.chef_resp = self._u("chef_resp", "EQUIPIER")
        lien = ResponsableSpecialite.objects.create(specialite=self.spe, user=self.resp)
        ChefResponsableSpecialite.objects.create(responsable=lien, chef=self.chef_resp)

    def proposer(self, categorie=None, auteur=None, **plus):
        return circuit.soumettre_flotte(auteur or self.chef_section, self.contenu(**plus), {"categorie": categorie or self.parent})

    def parcours_complet(self, version):
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            if circuit.peut_agir(user, version)[0]:
                circuit.viser(user, version.pk, version.etat)
                version.refresh_from_db()
        circuit.verifier(self.resp, version.pk)
        version.refresh_from_db()
        circuit.viser(self.chef_resp, version.pk, version.etat)
        version.refresh_from_db()
        return version

    def publier(self, categorie=None, **plus):
        """Publication par la voie directe du responsable de spécialité."""
        version = circuit.soumettre_flotte(self.resp, self.contenu(**plus), {"categorie": categorie or self.parent})
        circuit.viser(self.chef_resp, version.pk, version.etat)
        version.refresh_from_db()
        return version

    def exemplaire(self, categorie, nom):
        article = ArticleCatalogue.objects.get_or_create(categorie=categorie, designation=f"Article {categorie.nom}")[0]
        type_ = AssetType.objects.get_or_create(sector=self.secteur, name="Extincteur", defaults={"category": "Sécurité"})[0]
        return Asset.objects.create(asset_type=type_, designation=nom, ship=self.ship, service=self.machine,
                                    sector=self.secteur, article_catalogue=article)


class CircuitFlotteTests(BaseFlotte):
    def test_circuit_en_six_etapes_avec_notification_a_chaque_etape(self):
        version = self.proposer()
        self.assertEqual((version.etat, version.ship_origine, version.service_origine, version.secteur_origine),
                         (Etat.VISA_SECTEUR, self.ship, self.machine, self.secteur))
        self.assertIsNone(version.sector_id)
        self.assertEqual((version.fiche.niveau, version.fiche.categorie), ("FLOTTE", self.parent))
        attendus = [(self.chef_secteur, Etat.VISA_SERVICE, self.chef_service), (self.chef_service, Etat.VISA_COMA, self.comaeq),
                    (self.comaeq, Etat.VERIFICATION, self.resp)]
        for valideur, suivant, notifie in attendus:
            circuit.viser(valideur, version.pk, version.etat)
            version.refresh_from_db()
            self.assertEqual(version.etat, suivant)
            self.assertTrue(Notification.objects.filter(user=notifie, object_id=str(version.pk)).exists(), suivant)
        self.assertFalse(Notification.objects.filter(user=self.comanav).exists())
        circuit.verifier(self.resp, version.pk)
        version.refresh_from_db()
        self.assertEqual((version.etat, version.verificateur), (Etat.VISA_CHEF_SPECIALITE, self.resp))
        self.assertTrue(Notification.objects.filter(user=self.chef_resp, object_id=str(version.pk)).exists())
        circuit.viser(self.chef_resp, version.pk, version.etat)
        version.refresh_from_db()
        fiche = version.fiche
        self.assertEqual(version.etat, Etat.VALIDEE)
        self.assertEqual((fiche.periodicity, fiche.intervalle), ("3 mois", 3))
        self.assertTrue(Notification.objects.filter(user=self.chef_section, verb__contains="validée").exists())
        self.assertEqual(version.evenements.filter(action__in=["visee", "verifiee"]).count(), 5)
        self.assertTrue(AuditLog.objects.filter(action="fiche.version.verifiee").exists())

    def test_frise_complete_avec_organisme_fonction_service_et_titulaire(self):
        version = self.proposer()
        frise = circuit.frise(version)
        self.assertEqual([e["libelle"] for e in frise], [
            "Rédaction", "Chef de secteur", "Chef de service", "Commandant adjoint", "Responsable de spécialité",
            "Chef du responsable de spécialité", "Validée"])
        self.assertEqual((frise[1]["organisme"], frise[1]["titulaire"]), ("Frégate", "chef_secteur"))
        self.assertEqual((frise[3]["fonction"], frise[3]["titulaire"]), ("Commandant adjoint (COMAEQ)", "comaeq"))
        self.assertEqual((frise[4]["organisme"], frise[4]["titulaire"], frise[5]["titulaire"]), ("Terre", "resp", "chef_resp"))

    def test_chef_de_secteur_redacteur_saute_son_visa(self):
        version = self.proposer(auteur=self.chef_secteur)
        self.assertEqual(version.etat, Etat.VISA_SERVICE)
        self.assertNotIn(Etat.VISA_SECTEUR, circuit.circuit(version))

    def test_refus_motive_a_chaque_etape_et_resoumission(self):
        for etape, refuseur in [(Etat.VISA_SECTEUR, self.chef_secteur), (Etat.VISA_SERVICE, self.chef_service)]:
            version = self.proposer(name=f"Fiche {etape}")
            while version.etat != etape:
                circuit.viser(self.chef_secteur if version.etat == Etat.VISA_SECTEUR else self.chef_service, version.pk, version.etat)
                version.refresh_from_db()
            with self.assertRaises(ErreurCircuit):
                circuit.refuser(refuseur, version.pk, etape, "  ")
            circuit.refuser(refuseur, version.pk, etape, "Gamme à revoir")
            version.refresh_from_db()
            self.assertEqual((version.etat, version.motif_refus), (Etat.REFUSEE, "Gamme à revoir"))
            self.assertTrue(Notification.objects.filter(user=self.chef_section, verb__contains="Gamme à revoir").exists())
            circuit.resoumettre(self.chef_section, version.pk, self.contenu(name=f"Fiche {etape}", intervalle=6))
            version.refresh_from_db()
            self.assertEqual((version.etat, version.motif_refus, version.intervalle), (Etat.VISA_SECTEUR, "", 6))
            InstallationMaintenance.objects.filter(pk=version.fiche_id).delete()

    def test_le_responsable_peut_corriger_ou_renvoyer(self):
        version = self.proposer()
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            circuit.viser(user, version.pk, version.etat)
            version.refresh_from_db()
        circuit.verifier(self.resp, version.pk, self.contenu(duree_estimee_min=120))
        version.refresh_from_db()
        self.assertEqual(version.duree_estimee_min, 120)
        self.assertTrue(version.evenements.filter(action="corrigee").exists())
        autre = self.proposer(categorie=self.enfant, name="À renvoyer")
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            circuit.viser(user, autre.pk, autre.etat)
            autre.refresh_from_db()
        circuit.refuser(self.resp, autre.pk, Etat.VERIFICATION, "Périodicité incohérente")
        autre.refresh_from_db()
        self.assertEqual(autre.etat, Etat.REFUSEE)

    def test_auto_validation_interdite_et_une_seule_etape_par_personne(self):
        version = self.proposer()
        self.assertFalse(circuit.peut_agir(self.chef_section, version)[0])
        direct = circuit.soumettre_flotte(self.resp, self.contenu(name="Directe"), {"categorie": self.enfant})
        self.assertFalse(circuit.peut_agir(self.resp, direct)[0])
        with self.assertRaises(ErreurCircuit):
            circuit.viser(self.resp, direct.pk, direct.etat)
        # Un chef de secteur ayant visé ne peut plus intervenir à une autre étape de la même version.
        circuit.viser(self.chef_secteur, version.pk, version.etat)
        version.refresh_from_db()
        self.assertEqual(circuit._etapes_de(version, self.chef_secteur), {Etat.VISA_SECTEUR})

    def test_droits_de_redaction_et_de_verification(self):
        for user in (self.equipier, self.chef_service, self.comaeq):
            with self.subTest(user.username), self.assertRaises(ErreurCircuit):
                circuit.soumettre_flotte(user, self.contenu(), {"categorie": self.parent})
        version = self.proposer()
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            circuit.viser(user, version.pk, version.etat)
            version.refresh_from_db()
        autre = self._u("autre_resp", "EQUIPIER")
        ResponsableSpecialite.objects.create(specialite=SpecialityChoice.objects.create(name="Mécanique"), user=autre)
        with self.assertRaises(ErreurCircuit):
            circuit.verifier(autre, version.pk)
        with self.assertRaises(ErreurCircuit):
            circuit.viser(self.resp, version.pk, Etat.VERIFICATION)

    def test_a_terre_en_lecture_seule_ne_propose_rien(self):
        self.ship.double_equipage, self.ship.equipage_a_bord = True, "A"
        self.ship.save()
        self.chef_section.profile.equipage = "B"
        self.chef_section.profile.save()
        self.chef_section.refresh_from_db()
        with self.assertRaises(ErreurCircuit):
            self.proposer(auteur=User.objects.get(pk=self.chef_section.pk))

    def test_contenu_invalide_refuse_sans_erreur_serveur(self):
        for plus in ({"mode_declenchement": "COMPTEUR", "seuil_heures": 500, "intervalle": None},
                     {"intervalle": None}, {"name": " "}, {"intervalle": 10 ** 9},
                     {"preparations": [{"type": "piece", "libelle": "Joint", "quantite": 1, "piece": 1}]},
                     {"lignes": [{"cle": "00000000-0000-0000-0000-000000000000", "label": "x", "field_type": "checkbox", "unit": ""}]}):
            with self.subTest(plus), self.assertRaises(ErreurCircuit):
                self.proposer(**plus)
        self.assertFalse(InstallationMaintenance.objects.filter(niveau="FLOTTE").exists())

    def test_une_gamme_par_categorie_mais_une_sous_categorie_peut_la_reprendre(self):
        self.publier()
        with self.assertRaises(ErreurCircuit):
            self.proposer(name="Doublon")
        self.proposer(categorie=self.enfant, name="Spécifique CO2")

    def test_une_seule_version_en_cours_et_resume_obligatoire(self):
        fiche = self.publier().fiche
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre_flotte(self.chef_section, self.contenu(), fiche=fiche)
        version = circuit.soumettre_flotte(self.chef_section, self.contenu(resume_modifications="Plus fréquent", intervalle=2), fiche=fiche)
        self.assertEqual(version.numero, 2)
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre_flotte(self.chef_secteur, self.contenu(resume_modifications="Autre"), fiche=fiche)
        fiche.refresh_from_db()
        self.assertEqual(fiche.version_validee.numero, 1)


class VoieDirecteTests(BaseFlotte):
    def test_le_responsable_cree_une_fiche_visee_par_son_chef_puis_publiee(self):
        version = circuit.soumettre_flotte(self.resp, self.contenu(), {"categorie": self.parent})
        self.assertEqual((version.etat, version.role_redacteur, version.verificateur), (Etat.VISA_CHEF_SPECIALITE, "RESPONSABLE_SPECIALITE", self.resp))
        self.assertEqual([e["libelle"] for e in circuit.frise(version)], ["Rédaction", "Chef du responsable de spécialité", "Validée"])
        self.assertTrue(Notification.objects.filter(user=self.chef_resp, object_id=str(version.pk)).exists())
        circuit.viser(self.chef_resp, version.pk, version.etat)
        version.refresh_from_db()
        self.assertEqual(version.etat, Etat.VALIDEE)
        self.assertEqual(version.fiche.version_validee, version)

    def test_sans_chef_designe_la_redaction_directe_est_refusee_sauf_configuration_explicite(self):
        ChefResponsableSpecialite.objects.all().delete()
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre_flotte(self.resp, self.contenu(), {"categorie": self.parent})
        with override_settings(CATALOGUE_CHEF_SPECIALITE_OPTIONNEL=True):
            version = circuit.soumettre_flotte(self.resp, self.contenu(), {"categorie": self.parent})
        self.assertEqual(version.etat, Etat.VALIDEE)

    def test_blocage_expliqué_quand_le_chef_manque(self):
        version = self.proposer()
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            circuit.viser(user, version.pk, version.etat)
            version.refresh_from_db()
        ChefResponsableSpecialite.objects.all().delete()
        with self.assertRaises(ErreurCircuit):
            circuit.verifier(self.resp, version.pk)
        version.verificateur = self.resp
        version.etat = Etat.VISA_CHEF_SPECIALITE
        self.assertIn("Aucun chef n'est désigné", circuit.message_blocage(version))

    def test_visibilite_des_versions_en_cours(self):
        version = self.proposer()
        visibles = lambda user: circuit.versions_visibles(user).filter(pk=version.pk).exists()
        self.assertTrue(visibles(self.chef_section) and visibles(self.chef_secteur) and visibles(self.chef_service))
        self.assertFalse(visibles(self.equipier) or visibles(self.resp) or visibles(self.chef_resp))
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            circuit.viser(user, version.pk, version.etat)
            version.refresh_from_db()
        self.assertTrue(visibles(self.resp))
        circuit.verifier(self.resp, version.pk)
        self.assertTrue(visibles(self.chef_resp))
        self.assertFalse(visibles(self.equipier))
        circuit.viser(self.chef_resp, version.pk, Etat.VISA_CHEF_SPECIALITE)
        self.assertTrue(visibles(self.equipier))


class ResolveurTests(BaseFlotte):
    def test_la_fiche_de_la_categorie_la_plus_proche_l_emporte_gamme_par_gamme(self):
        parent_3m = self.publier(self.parent, name="Parent 3 mois")
        parent_1a = self.publier(self.parent, name="Parent 1 an", intervalle=1, unite_intervalle="A")
        enfant_3m = self.publier(self.enfant, name="Enfant 3 mois")
        applicables = fiche_flotte.fiches_applicables(self.enfant)
        self.assertEqual(applicables["3 mois"], enfant_3m.fiche)
        self.assertEqual(applicables["1 an"], parent_1a.fiche)
        self.assertEqual(fiche_flotte.fiches_applicables(self.parent)["3 mois"], parent_3m.fiche)
        titres = [f["fiche"].title for f in fiche_flotte.fiches_de_categorie(self.enfant)]
        self.assertEqual(titres, ["Parent 1 an", "Enfant 3 mois"])
        self.assertEqual([f["heritee"] for f in fiche_flotte.fiches_de_categorie(self.enfant)], [True, False])

    def test_generation_des_occurrences_selon_la_fiche_la_plus_proche(self):
        parent_3m = self.publier(self.parent, name="Parent 3 mois").fiche
        enfant_3m = self.publier(self.enfant, name="Enfant 3 mois").fiche
        parent_1a = self.publier(self.parent, name="Parent 1 an", intervalle=1, unite_intervalle="A").fiche
        ext_parent = self.exemplaire(self.parent, "Ext parent")
        ext_enfant = self.exemplaire(self.enfant, "Ext enfant")
        aujourdhui = date.today()
        tasks.generer_occurrences_fiches_flotte(aujourdhui, aujourdhui + timedelta(days=400))
        plans = lambda asset: set(MaintenanceOccurrence.objects.filter(asset=asset).values_list("plan__fiche__title", flat=True))
        self.assertEqual(plans(ext_parent), {"Parent 3 mois", "Parent 1 an"})
        self.assertEqual(plans(ext_enfant), {"Enfant 3 mois", "Parent 1 an"})
        plan = parent_3m.plans.get()
        self.assertEqual((plan.every_n_days, plan.scope), (90, "FICHE"))
        # Relancer ne duplique rien.
        avant = MaintenanceOccurrence.objects.count()
        tasks.generer_occurrences_fiches_flotte(aujourdhui, aujourdhui + timedelta(days=400))
        self.assertEqual(MaintenanceOccurrence.objects.count(), avant)
        self.assertTrue(enfant_3m.plans.exists() and parent_1a.plans.exists())

    def test_l_execution_et_la_tournee_lisent_la_fiche_la_plus_proche(self):
        parent = self.publier(self.parent, name="Parent 3 mois").fiche
        enfant = self.publier(self.enfant, name="Enfant 3 mois", lignes=[{"label": "Goupille", "field_type": "checkbox", "unit": ""}]).fiche
        plan = tasks.MaintenancePlan.objects.create(scope="FICHE", fiche=parent, name="Parent 3 mois")
        ext_enfant, ext_parent = self.exemplaire(self.enfant, "CO2"), self.exemplaire(self.parent, "Poudre")
        occ_enfant = MaintenanceOccurrence.objects.create(plan=plan, asset=ext_enfant, scheduled_for=date.today())
        occ_parent = MaintenanceOccurrence.objects.create(plan=plan, asset=ext_parent, scheduled_for=date.today())
        self.assertEqual(occ_enfant.version_fiche(), enfant.version_validee)
        self.assertEqual(occ_parent.version_fiche(), parent.version_validee)
        self.assertEqual([l.label for l in occ_enfant.lignes_fiche()], ["Goupille"])
        groupes = tournee.groupes([occ_enfant, occ_parent])
        self.assertEqual(sorted(g["modele"] for g in groupes), ["Enfant 3 mois", "Parent 3 mois"])
        self.client.force_login(self.chef_service)
        occ_enfant.assignees.add(self.chef_service)
        self.assertEqual(self.client.get(reverse("occurrence-execute", args=[occ_enfant.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("occurrence-imprimer", args=[occ_enfant.pk])).status_code, 200)

    def test_une_nouvelle_version_s_applique_sans_toucher_aux_executions_passees(self):
        v1 = self.publier(self.parent)
        plan = tasks.MaintenancePlan.objects.create(scope="FICHE", fiche=v1.fiche, name="Plan")
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=self.exemplaire(self.parent, "A"), scheduled_for=date.today())
        v2 = circuit.soumettre_flotte(self.resp, self.contenu(resume_modifications="Plus de lignes", lignes=[]), fiche=v1.fiche)
        circuit.viser(self.chef_resp, v2.pk, v2.etat)
        self.assertEqual(MaintenanceOccurrence.objects.get(pk=occ.pk).version_fiche().numero, 2)


class AdaptationTests(BaseFlotte):
    def flotte_installation(self, **plus):
        cible = {"specialite": self.spe, "equipement": "Pompe incendie", "reference_equipement": "", "classe_navire": ""}
        version = circuit.soumettre_flotte(self.resp, self.contenu(name="Pompe flotte", **plus), cible)
        circuit.viser(self.chef_resp, version.pk, version.etat)
        version.refresh_from_db()
        return version.fiche

    def adapter(self, flotte):
        version = circuit.soumettre(self.chef_section, self.installation, fiche_adaptation.contenu_de_adaptation(flotte), origine=flotte)
        return self.valider(version).fiche

    def test_la_fiche_flotte_n_apparait_pas_dans_les_fiches_du_bord(self):
        flotte = self.flotte_installation()
        self.assertFalse(self.installation.maintenances.exists())
        self.assertEqual(fiche_flotte.fiches_pour_installation(self.installation), [flotte])
        self.assertEqual(fiche_adaptation.fiches_flotte_proposees(self.installation), [flotte])

    def test_la_classe_de_navire_limite_la_portee(self):
        self.ship.classe_navire = "Horizon"
        self.ship.save()
        flotte = self.flotte_installation()
        flotte.classe_navire = "FREMM"
        flotte.save()
        self.installation.refresh_from_db()
        self.assertEqual(fiche_flotte.fiches_pour_installation(self.installation), [])
        flotte.classe_navire = "horizon"
        flotte.save()
        self.assertEqual(fiche_flotte.fiches_pour_installation(self.installation), [flotte])

    def test_adaptation_locale_tracee_puis_decision_apres_changement_de_la_flotte(self):
        flotte = self.flotte_installation()
        locale = self.adapter(flotte)
        self.assertEqual((locale.origine, locale.origine_numero, locale.installation), (flotte, 1, self.installation))
        self.assertFalse(fiche_adaptation.flotte_adaptable(self.installation, flotte))
        v2 = circuit.soumettre_flotte(self.resp, self.contenu(name="Pompe flotte", resume_modifications="Ajout d'un contrôle", intervalle=2,
                                                              lignes=[{"label": "Nouveau", "field_type": "checkbox", "unit": ""}]), fiche=flotte)
        circuit.viser(self.chef_resp, v2.pk, v2.etat)
        locale.refresh_from_db()
        self.assertEqual(locale.origine_en_attente, 2)
        self.assertEqual(locale.version_validee.numero, 1)
        self.assertEqual(locale.intervalle, 3)
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur, verb__contains="v2").exists())
        version = fiche_adaptation.reprendre(self.chef_secteur, locale.pk)
        locale.refresh_from_db()
        self.assertEqual((version.etat, locale.origine_numero, locale.origine_en_attente), (Etat.VISA_SERVICE, 2, None))
        self.assertEqual([l.label for l in version.items.all()], ["Nouveau"])
        self.assertTrue(AuditLog.objects.filter(action="fiche.origine.reprise").exists())
        with self.assertRaises(ErreurCircuit):
            fiche_adaptation.reprendre(self.chef_secteur, locale.pk)

    def test_garder_la_sienne_est_trace_et_ne_change_rien(self):
        flotte = self.flotte_installation()
        locale = self.adapter(flotte)
        v2 = circuit.soumettre_flotte(self.resp, self.contenu(name="Pompe flotte", resume_modifications="Changement", intervalle=2), fiche=flotte)
        circuit.viser(self.chef_resp, v2.pk, v2.etat)
        with self.assertRaises(ErreurCircuit):
            fiche_adaptation.garder(self.equipier, locale.pk)
        fiche_adaptation.garder(self.chef_secteur, locale.pk)
        locale.refresh_from_db()
        self.assertEqual((locale.origine_en_attente, locale.origine_numero, locale.versions.count()), (None, 1, 1))
        self.assertTrue(AuditLog.objects.filter(action="fiche.origine.gardee").exists())
        flotte.refresh_from_db()
        self.assertEqual(flotte.version_validee.numero, 2)

    def test_une_adaptation_ne_modifie_ni_la_flotte_ni_les_autres_navires(self):
        flotte = self.flotte_installation()
        locale = self.adapter(flotte)
        v2 = circuit.soumettre(self.chef_secteur, self.installation, self.contenu(name="Pompe locale", resume_modifications="Local", intervalle=1), locale)
        self.valider(v2, (self.chef_service, self.comaeq))
        flotte.refresh_from_db()
        self.assertEqual((flotte.version_validee.numero, flotte.intervalle), (1, 3))
        self.assertEqual(locale.versions.count(), 2)

    def test_le_bord_ne_peut_pas_adapter_une_fiche_qui_ne_le_vise_pas(self):
        flotte = self.flotte_installation()
        self.assertFalse(fiche_adaptation.flotte_adaptable(self.autre, flotte))
        self.client.force_login(self.chef_section)
        reponse = self.client.get(reverse("fiche-nouvelle", args=[self.autre.pk]) + f"?depuis={flotte.pk}")
        self.assertEqual(reponse.status_code, 403)


class SignalementTests(BaseFlotte):
    def test_fiche_du_bord_signalee_au_chef_de_secteur(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        signalement = fiche_signalement.signaler(self.equipier, occ, "Il manque la consignation")
        self.assertEqual((signalement.fiche, signalement.traite, signalement.version), (fiche, False, fiche.version_validee))
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur, verb__contains="consignation").exists())
        self.assertFalse(Notification.objects.filter(user=self.resp).exists())
        self.assertTrue(AuditLog.objects.filter(action="fiche.signalement").exists())

    def test_fiche_flotte_signalee_au_responsable_de_specialite(self):
        fiche = self.publier().fiche
        plan = tasks.MaintenancePlan.objects.create(scope="FICHE", fiche=fiche, name="Plan")
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=self.exemplaire(self.parent, "A"), scheduled_for=date.today())
        fiche_signalement.signaler(self.equipier, occ, "Pression erronée")
        self.assertTrue(Notification.objects.filter(user=self.resp, verb__contains="Pression erronée").exists())
        self.assertFalse(Notification.objects.filter(user=self.chef_secteur).exists())

    def test_signalement_invalide_refuse(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        for texte in ("", "   ", "x" * 2001):
            with self.subTest(len(texte)), self.assertRaises(ErreurCircuit):
                fiche_signalement.signaler(self.equipier, occ, texte)

    def test_le_chef_de_secteur_ouvre_une_version_a_partir_du_signalement(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        signalement = fiche_signalement.signaler(self.equipier, occ, "Étape manquante")
        self.assertTrue(circuit.peut_traiter_signalement(self.chef_secteur, fiche)[0])
        self.assertFalse(circuit.peut_traiter_signalement(self.equipier, fiche)[0])
        self.client.force_login(self.chef_secteur)
        page = self.client.get(reverse("fiche-modifier", args=[fiche.pk]) + f"?signalement={signalement.pk}")
        self.assertContains(page, "Étape manquante")
        version = circuit.soumettre(self.chef_secteur, self.installation, self.contenu(resume_modifications="Étape ajoutée"), fiche, signalement=signalement)
        signalement.refresh_from_db()
        self.assertEqual((signalement.traite, signalement.version_proposee), (True, version))
        self.assertEqual(list(fiche_signalement.ouverts(fiche)), [])

    def test_signalement_depuis_l_ecran_d_execution(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        occ.assignees.add(self.equipier)
        self.client.force_login(self.equipier)
        self.assertContains(self.client.get(reverse("occurrence-execute", args=[occ.pk])), "fausse ou incomplète")
        reponse = self.client.post(reverse("occurrence-signaler-fiche", args=[occ.pk]), {"texte": "Fiche périmée"})
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(SignalementFiche.objects.get().texte, "Fiche périmée")
        self.client.post(reverse("occurrence-signaler-fiche", args=[occ.pk]), {"texte": ""})
        self.assertEqual(SignalementFiche.objects.count(), 1)


class ComparaisonTests(BaseFlotte):
    def test_lignes_ajoutees_modifiees_supprimees_et_deplacees(self):
        v1 = self.publier(etapes=[{"texte": "A", "attention": ""}, {"texte": "B", "attention": ""}])
        cles = {l.label: l.cle for l in v1.items.all()}
        contenu = fiche_maintenance.contenu_de(v1) | {"resume_modifications": "x", "etapes": [{"texte": "A", "attention": ""}, {"texte": "C", "attention": ""}, {"texte": "D", "attention": ""}],
                                                      "lignes": [{"cle": cles["Pression"], "label": "Pression", "field_type": "number", "unit": "mbar", "valeur_min": 4.0, "valeur_max": 6.0},
                                                                 {"label": "Neuve", "field_type": "checkbox", "unit": ""}]}
        v2 = circuit.soumettre_flotte(self.chef_section, contenu, fiche=v1.fiche)
        diff = fiche_comparaison.comparer(v1, v2)
        lignes = {e["texte"]: e for e in dict(diff["sections"])["Contrôles et relevés"]}
        self.assertEqual((lignes["Pression"]["statut"], lignes["Neuve"]["statut"], lignes["Plombage"]["statut"]), ("modifiee", "ajoutee", "supprimee"))
        self.assertIn("Unité : bar → mbar", lignes["Pression"]["details"])
        etapes = [(e["statut"], e["texte"]) for e in dict(diff["sections"])["Méthodologie"]]
        self.assertEqual(etapes, [("inchangee", "A"), ("modifiee", "C"), ("ajoutee", "D")])
        self.assertGreaterEqual(diff["total"], 5)

    def test_l_ecran_de_visa_affiche_la_comparaison(self):
        v1 = self.publier()
        v2 = circuit.soumettre_flotte(self.chef_section, self.contenu(resume_modifications="Plus court", intervalle=1), fiche=v1.fiche)
        self.client.force_login(self.chef_secteur)
        page = self.client.get(reverse("fiche-detail", args=[v1.fiche_id]) + f"?v={v2.numero}")
        self.assertContains(page, "Comparer avec la version appliquée (v1)")
        self.assertContains(page, "Gamme")


class EcransFlotteTests(BaseFlotte):
    def donnees(self, **plus):
        return {"name": "Contrôle trimestriel", "mode_declenchement": "CALENDRIER", "intervalle": "3", "unite_intervalle": "M",
                "duree_estimee_min": "30", "nb_personnes": "1", "etape_texte": ["Contrôler"], "etape_attention": [""],
                "ligne_cle": ["", ""], "ligne_type": ["checkbox", "number"], "ligne_label": ["Goupille", "Pression"],
                "ligne_unite": ["", "bar"], "ligne_min": ["", "10"], "ligne_max": ["", "15"], "ligne_obligatoire": ["1", "0"], **plus}

    def test_bloc_fiches_du_catalogue_et_boutons(self):
        article = ArticleCatalogue.objects.create(categorie=self.enfant, designation="Extincteur CO2 5 kg")
        self.publier(self.parent, name="Contrôle annuel")
        self.client.force_login(self.chef_section)
        page = self.client.get(reverse("catalogue-article", args=[article.pk]))
        self.assertContains(page, "Contrôle annuel")
        self.assertContains(page, "héritée de « Extincteurs »")
        self.assertContains(page, "Proposer une fiche")
        self.assertContains(page, "Proposer une modification")
        self.client.force_login(self.equipier)
        page = self.client.get(reverse("catalogue-article", args=[article.pk]))
        self.assertContains(page, "Contrôle annuel")
        self.assertNotContains(page, "Proposer une fiche")
        self.client.force_login(self.resp)
        self.assertContains(self.client.get(reverse("catalogue-article", args=[article.pk])), "Créer une fiche")

    def test_proposition_par_l_assistant_puis_verification_par_le_responsable(self):
        self.client.force_login(self.chef_section)
        url = reverse("fiche-flotte-nouvelle", args=[self.parent.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        reponse = self.client.post(url, self.donnees())
        self.assertEqual(reponse.status_code, 302)
        version = ChecklistTemplate.objects.get(name="Contrôle trimestriel")
        self.assertEqual([(l.label, l.required) for l in version.items.order_by("order")], [("Goupille", True), ("Pression", False)])
        for user in (self.chef_secteur, self.chef_service, self.comaeq):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("fiche-detail", args=[version.fiche_id]) + "?v=1").status_code, 200)
            self.client.post(reverse("fiche-viser", args=[version.pk]), {"etape": version.etat})
            version.refresh_from_db()
        self.assertEqual(version.etat, Etat.VERIFICATION)
        self.client.force_login(self.resp)
        detail = self.client.get(reverse("fiche-detail", args=[version.fiche_id]) + "?v=1")
        self.assertContains(detail, "Vérifier et transmettre")
        url_verif = reverse("fiche-flotte-verifier", args=[version.pk])
        self.assertContains(self.client.get(url_verif), "Vérifier la version 1")
        self.client.post(url_verif, self.donnees(duree_estimee_min="45", resume_modifications=""))
        version.refresh_from_db()
        self.assertEqual((version.etat, version.duree_estimee_min), (Etat.VISA_CHEF_SPECIALITE, 45))
        self.client.force_login(self.chef_resp)
        self.client.post(reverse("fiche-viser", args=[version.pk]), {"etape": version.etat})
        version.refresh_from_db()
        self.assertEqual(version.etat, Etat.VALIDEE)

    def test_aucune_erreur_serveur_sur_entrees_invalides(self):
        self.client.force_login(self.chef_section)
        url = reverse("fiche-flotte-nouvelle", args=[self.parent.pk])
        for plus in ({"intervalle": "abc"}, {"duree_estimee_min": "-5"}, {"ligne_cle": ["pas-un-uuid", ""]}, {"name": ""}, {"seuil_heures": "x"}):
            with self.subTest(plus):
                self.assertEqual(self.client.post(url, self.donnees(**plus)).status_code, 200)
        self.assertEqual(self.client.get(reverse("fiche-flotte-nouvelle", args=["00000000-0000-0000-0000-000000000000"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("fiche-flotte-modifier", args=[999999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("fiche-flotte-verifier", args=[999999])).status_code, 404)
        self.assertFalse(ChecklistTemplate.objects.filter(fiche__niveau="FLOTTE").exists())

    def test_l_ordre_des_lignes_envoye_par_l_editeur_est_conserve(self):
        self.client.force_login(self.chef_section)
        self.client.post(reverse("fiche-flotte-nouvelle", args=[self.parent.pk]), self.donnees(
            ligne_label=["Pression", "Goupille"], ligne_type=["number", "checkbox"], ligne_unite=["bar", ""], ligne_min=["10", ""],
            ligne_max=["15", ""]))
        version = ChecklistTemplate.objects.get(name="Contrôle trimestriel")
        self.assertEqual([l.label for l in version.items.order_by("order")], ["Pression", "Goupille"])

    def test_un_equipier_ne_peut_ni_ouvrir_ni_poster_l_assistant(self):
        self.client.force_login(self.equipier)
        url = reverse("fiche-flotte-nouvelle", args=[self.parent.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.donnees()).status_code, 403)

    def test_remplacement_pour_une_sous_categorie_part_de_la_fiche_du_parent(self):
        parent = self.publier(self.parent, name="Contrôle du parent")
        self.client.force_login(self.resp)
        page = self.client.get(reverse("fiche-flotte-nouvelle", args=[self.enfant.pk]) + f"?depuis={parent.fiche_id}")
        self.assertContains(page, "Contrôle du parent")
        self.assertContains(page, "Plombage")

    def test_proposer_comme_fiche_flotte_depuis_une_fiche_du_bord(self):
        fiche = self.fiche_validee()
        self.client.force_login(self.chef_section)
        self.assertContains(self.client.get(reverse("fiche-detail", args=[fiche.pk])), "Proposer comme fiche flotte")
        url = reverse("fiche-flotte-depuis-bord", args=[fiche.pk])
        page = self.client.get(url)
        self.assertContains(page, "Pompe incendie")
        reponse = self.client.post(url, self.donnees(specialite=str(self.spe.pk), equipement="Pompe incendie", reference_equipement="", classe_navire=""))
        self.assertEqual(reponse.status_code, 302)
        flotte = InstallationMaintenance.objects.get(niveau="FLOTTE")
        self.assertEqual((flotte.specialite, flotte.equipement, flotte.installation, flotte.categorie), (self.spe, "Pompe incendie", None, None))
        self.assertEqual(self.client.post(url, self.donnees(equipement="x")).status_code, 200)

    def test_les_fiches_a_valider_apparaissent_dans_a_faire(self):
        version = self.proposer()
        titres = lambda user: [(e["titre"], e["detail"]) for e in a_faire(user, date.today())]
        self.assertIn((version.name, "Fiche à valider · Visa du chef de secteur"), titres(self.chef_secteur))
        self.assertNotIn(version.name, [t for t, _ in titres(self.chef_service)])
        self.assertNotIn(version.name, [t for t, _ in titres(self.equipier)])
        circuit.viser(self.chef_secteur, version.pk, version.etat)
        self.assertIn(version.name, [t for t, _ in titres(self.chef_service)])
        self.assertNotIn(version.name, [t for t, _ in titres(self.chef_secteur)])

    def test_la_notification_renvoie_vers_la_fiche_et_le_signalement_aussi(self):
        version = self.proposer()
        notification = Notification.objects.filter(user=self.chef_secteur).get()
        self.client.force_login(self.chef_secteur)
        liens = import_module("notifications.liens")
        reponse = self.client.get(reverse("fiche-detail", args=[version.fiche_id]))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(str(version.fiche_id), liens.liens_accessibles(reponse.wsgi_request, [notification])[notification.pk])


class MigrationFlotteTests(BaseFlotte):
    def test_une_version_de_fiche_flotte_n_a_pas_de_secteur(self):
        version = self.publier()
        self.assertIsNone(version.sector_id)
        self.assertEqual(str(version), version.name)

    def test_la_normalisation_du_niveau_ne_touche_pas_aux_fiches_deja_coherentes(self):
        flotte = InstallationMaintenance.objects.create(categorie=self.parent, niveau="FLOTTE", periodicity="1 an", title="Annuel")
        bord = InstallationMaintenance.objects.create(installation=self.installation, periodicity="3 mois", title="Trimestriel", description="Texte")
        migration.normaliser_niveau(apps, None)
        flotte.refresh_from_db()
        bord.refresh_from_db()
        self.assertEqual((flotte.niveau, flotte.title, bord.niveau, bord.description), ("FLOTTE", "Annuel", "BORD", "Texte"))


class RelectureTests(BaseFlotte):
    def signalement_flotte(self):
        fiche = self.publier().fiche
        plan = tasks.MaintenancePlan.objects.create(scope="FICHE", fiche=fiche, name="Plan")
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=self.exemplaire(self.parent, "A"), scheduled_for=date.today())
        return fiche, fiche_signalement.signaler(self.equipier, occ, "Texte confidentiel du marin")

    def test_un_signalement_de_fiche_flotte_n_est_ni_lisible_ni_clos_par_le_bord(self):
        fiche, signalement = self.signalement_flotte()
        self.client.force_login(self.chef_section)
        url = reverse("fiche-flotte-modifier", args=[fiche.pk])
        self.assertNotContains(self.client.get(url + f"?signalement={signalement.pk}"), "Texte confidentiel")
        self.assertNotContains(self.client.get(reverse("fiche-detail", args=[fiche.pk])), "Texte confidentiel")
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre_flotte(self.chef_section, self.contenu(resume_modifications="x"), fiche=fiche, signalement=signalement)
        signalement.refresh_from_db()
        self.assertFalse(signalement.traite)
        self.assertEqual(fiche.versions.count(), 1)
        # Le responsable, lui, le lit et le clôt ; un signalement déjà clos ne se rejoue pas.
        self.client.force_login(self.resp)
        self.assertContains(self.client.get(url + f"?signalement={signalement.pk}"), "Texte confidentiel")
        version = circuit.soumettre_flotte(self.resp, self.contenu(resume_modifications="x"), fiche=fiche, signalement=signalement)
        signalement.refresh_from_db()
        self.assertEqual((signalement.traite, signalement.version_proposee), (True, version))
        circuit.viser(self.chef_resp, version.pk, version.etat)
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre_flotte(self.resp, self.contenu(resume_modifications="y"), fiche=fiche, signalement=signalement)

    def test_un_signalement_du_bord_n_est_traitable_que_dans_le_perimetre(self):
        fiche = self.fiche_validee()
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        signalement = fiche_signalement.signaler(self.equipier, occ, "Secret du bord")
        with self.assertRaises(ErreurCircuit):
            circuit.soumettre(self.equipier, self.installation, self.contenu(resume_modifications="x"), fiche, signalement=signalement)
        signalement.refresh_from_db()
        self.assertFalse(signalement.traite)

    def test_reprendre_et_garder_refusent_une_fiche_qui_n_est_pas_une_adaptation(self):
        fiche = self.fiche_validee()
        for action in (fiche_adaptation.reprendre, fiche_adaptation.garder):
            with self.assertRaises(ErreurCircuit):
                action(self.chef_secteur, fiche.pk)
        self.client.force_login(self.chef_secteur)
        for nom in ("fiche-reprendre", "fiche-garder"):
            self.assertEqual(self.client.post(reverse(nom, args=[fiche.pk])).status_code, 302)
        self.assertEqual(self.client.post(reverse("fiche-reprendre", args=[999999])).status_code, 404)

    def test_l_adaptation_d_un_navire_ne_touche_ni_la_flotte_ni_les_autres_navires(self):
        cible = {"specialite": self.spe, "equipement": "Pompe incendie", "reference_equipement": "", "classe_navire": ""}
        version = circuit.soumettre_flotte(self.resp, self.contenu(name="Pompe flotte"), cible)
        circuit.viser(self.chef_resp, version.pk, version.etat)
        flotte = version.fiche
        # Un second navire adapte la même fiche flotte.
        from org.models import Section, Sector, Service, Ship
        from assets.models import Installation

        navire = Ship.objects.create(name="Autre", code="AUT")
        service = Service.objects.create(ship=navire, name="Machine", commandant_adjoint="COMAEQ")
        secteur = Sector.objects.create(service=service, name="Propulsion")
        section = Section.objects.create(sector=secteur, name="Moteurs")
        pompe = Installation.objects.create(designation="Pompe incendie", ship=navire, service=service, sector=secteur, section=section)
        chef = self._u("chef_autre", "CHEF_SECTION", ship=navire, service=service, sector=secteur, section=section)
        adaptation_autre = circuit.soumettre(chef, pompe, fiche_adaptation.contenu_de_adaptation(flotte), origine=flotte).fiche
        locale = circuit.soumettre(self.chef_section, self.installation, fiche_adaptation.contenu_de_adaptation(flotte), origine=flotte).fiche
        avant = (flotte.versions.count(), adaptation_autre.versions.count(), adaptation_autre.title)
        circuit.refuser(self.chef_secteur, locale.versions.get().pk, Etat.VISA_SECTEUR, "Local")
        circuit.resoumettre(self.chef_section, locale.versions.get().pk, self.contenu(name="Pompe locale", intervalle=1))
        flotte.refresh_from_db()
        adaptation_autre.refresh_from_db()
        self.assertEqual((flotte.versions.count(), adaptation_autre.versions.count(), adaptation_autre.title), avant)
        self.assertEqual((flotte.title, flotte.intervalle), ("Pompe flotte", 3))
        self.assertEqual(adaptation_autre.versions.get().name, "Pompe flotte")
        self.assertEqual(list(InstallationMaintenance.objects.filter(origine=flotte).values_list("installation", flat=True).order_by("installation")),
                         sorted([self.installation.pk, pompe.pk]))

    def test_les_caracteres_nul_sont_retires_des_saisies(self):
        self.client.force_login(self.chef_section)
        donnees = {"name": "Fiche\x00 NUL", "description": "a\x00b", "mode_declenchement": "CALENDRIER", "intervalle": "3",
                   "unite_intervalle": "M", "etape_texte": ["Étape\x00"], "etape_attention": [""], "ligne_label": ["Point\x00"],
                   "ligne_type": ["checkbox"], "ligne_cle": [""], "ligne_unite": [""], "ligne_min": [""], "ligne_max": [""]}
        reponse = self.client.post(reverse("fiche-flotte-nouvelle", args=[self.parent.pk]), donnees)
        self.assertEqual(reponse.status_code, 302)
        version = ChecklistTemplate.objects.get(fiche__niveau="FLOTTE")
        self.assertEqual((version.name, version.description, version.etapes.get().texte, version.items.get().label),
                         ("Fiche NUL", "ab", "Étape", "Point"))
        self.client.force_login(self.resp)
        reponse = self.client.post(reverse("fiche-flotte-depuis-bord", args=[self.fiche_validee().pk]), {
            **donnees, "name": "Autre", "specialite": str(self.spe.pk), "equipement": "Pompe\x00", "reference_equipement": "r\x00", "classe_navire": "c\x00"})
        self.assertEqual(reponse.status_code, 302)
        flotte = InstallationMaintenance.objects.get(niveau="FLOTTE", categorie__isnull=True)
        self.assertEqual((flotte.equipement, flotte.reference_equipement, flotte.classe_navire), ("Pompe", "r", "c"))
        circuit.refuser(self.chef_secteur, version.pk, Etat.VISA_SECTEUR, "mo\x00tif")
        self.assertEqual(ChecklistTemplate.objects.get(pk=version.pk).motif_refus, "motif")
        occ = MaintenanceOccurrence.objects.create(installation_maintenance=InstallationMaintenance.objects.get(installation=self.installation), scheduled_for=date.today())
        self.assertEqual(fiche_signalement.signaler(self.equipier, occ, "a\x00b").texte, "ab")


class GenerationIdempotenteTests(BaseFlotte):
    def test_relancer_la_generation_un_autre_jour_ne_cree_rien_de_plus(self):
        self.publier(self.parent)
        ext = self.exemplaire(self.parent, "A")
        aujourdhui = date.today()
        tasks.generer_occurrences_fiches_flotte(aujourdhui, aujourdhui + timedelta(days=90))
        nombre = MaintenanceOccurrence.objects.filter(asset=ext).count()
        for jour in range(1, 6):
            tasks.generer_occurrences_fiches_flotte(aujourdhui + timedelta(days=jour), aujourdhui + timedelta(days=90 + jour))
        # Seule la prochaine échéance, au pas de la gamme, peut s'ajouter.
        dates = list(MaintenanceOccurrence.objects.filter(asset=ext).order_by("scheduled_for").values_list("scheduled_for", flat=True))
        self.assertEqual({(b - a).days for a, b in zip(dates, dates[1:])}, {90})
        self.assertLessEqual(len(dates) - nombre, 1)

    def test_la_generation_des_plans_existants_est_idempotente_elle_aussi(self):
        ext = self.exemplaire(self.parent, "A")
        plan = tasks.MaintenancePlan.objects.create(scope="ASSET", asset=ext, name="Plan", every_n_days=30)
        aujourdhui = date.today()
        tasks._creer_occurrences(plan, ext, aujourdhui, aujourdhui + timedelta(days=90))
        nombre = plan.occurrences.count()
        for jour in range(1, 10):
            tasks._creer_occurrences(plan, ext, aujourdhui + timedelta(days=jour), aujourdhui + timedelta(days=90 + jour))
        self.assertLessEqual(plan.occurrences.count() - nombre, 1)
        self.assertEqual(tasks.generate_occurrences(), {"status": "ok"})

    def test_la_sous_categorie_qui_publie_retire_les_occurrences_futures_non_commencees_du_parent(self):
        parent = self.publier(self.parent, name="Parent").fiche
        ext_enfant, ext_parent = self.exemplaire(self.enfant, "CO2"), self.exemplaire(self.parent, "Poudre")
        aujourdhui = date.today()
        tasks.generer_occurrences_fiches_flotte(aujourdhui, aujourdhui + timedelta(days=200))
        plan = parent.plans.get()
        futures = MaintenanceOccurrence.objects.filter(plan=plan, asset=ext_enfant)
        commencee, terminee = futures.order_by("scheduled_for")[1], futures.order_by("scheduled_for")[2]
        from maintenance.models import MaintenanceExecution

        MaintenanceExecution.objects.create(occurrence=commencee)
        MaintenanceOccurrence.objects.filter(pk=terminee.pk).update(status="DONE")
        self.publier(self.enfant, name="Enfant")
        statuts = {o.pk: o.status for o in futures}
        self.assertEqual(statuts[commencee.pk], "PLANNED")
        self.assertEqual(statuts[terminee.pk], "DONE")
        self.assertEqual(sum(1 for s in statuts.values() if s == "CANCELLED"), len(statuts) - 2)
        self.assertFalse(MaintenanceOccurrence.objects.filter(plan=plan, asset=ext_parent, status="CANCELLED").exists())
