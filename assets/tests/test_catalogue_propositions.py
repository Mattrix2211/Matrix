"""Proposition d'un nouvel article : circuit de visas, droits, périmètre, publication."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog, ResponsableSpecialite, SpecialityChoice, UserProfile
from assets import proposition_article as circuit
from assets.models import ArticleCatalogue, CategorieCatalogue, ChefResponsableSpecialite, PropositionArticle
from notifications.models import Notification
from org.models import Section, Sector, Service, Ship

Etat = PropositionArticle.Etat


class BasePropositions(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Frégate", code="FRG")
        self.machine = Service.objects.create(ship=self.ship, name="Machine", commandant_adjoint="COMAEQ")
        self.pont = Service.objects.create(ship=self.ship, name="Pont", commandant_adjoint="COMANAV")
        self.libre = Service.objects.create(ship=self.ship, name="Divers")
        self.secteur = Sector.objects.create(service=self.machine, name="Propulsion")
        self.section = Section.objects.create(sector=self.secteur, name="Moteurs")
        self.secteur_libre = Sector.objects.create(service=self.libre, name="Divers secteur")
        self.autre_secteur = Sector.objects.create(service=self.machine, name="Auxiliaires")
        spe = SpecialityChoice.objects.create(name="Mécanicien")
        self.categorie = CategorieCatalogue.objects.create(nom="Outillage", specialite=spe)
        self.chef_section = self._u("chef_section", "CHEF_SECTION", ship=self.ship, service=self.machine, sector=self.secteur, section=self.section)
        self.chef_secteur = self._u("chef_secteur", "CHEF_SECTEUR", ship=self.ship, service=self.machine, sector=self.secteur)
        self.chef_service = self._u("chef_service", "CHEF_SERVICE", ship=self.ship, service=self.machine)
        self.comaeq = self._u("comaeq", "ETAT_MAJOR", ship=self.ship, fonction_coma="COMAEQ")
        self.comanav = self._u("comanav", "ETAT_MAJOR", ship=self.ship, fonction_coma="COMANAV")
        self.resp = self._u("resp", "EQUIPIER")
        self.chef_resp = self._u("chef_resp", "EQUIPIER")
        lien = ResponsableSpecialite.objects.create(specialite=spe, user=self.resp)
        ChefResponsableSpecialite.objects.create(responsable=lien, chef=self.chef_resp)

    def _u(self, nom, role, **rattachement):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return User.objects.get(pk=user.pk)

    def proposer(self, auteur=None, **plus):
        self.client.force_login(auteur or self.chef_section)
        donnees = {"designation": "Clé dynamométrique", "categorie": str(self.categorie.pk), "marque": "Facom", **plus}
        reponse = self.client.post(reverse("catalogue-proposition-nouvelle"), donnees)
        self.assertEqual(reponse.status_code, 302, getattr(reponse, "context", None) and reponse.context["form"].errors)
        return PropositionArticle.objects.get(designation=donnees["designation"])

    def viser(self, user, proposition, etape=None):
        self.client.force_login(user)
        return self.client.post(reverse("catalogue-proposition-viser", args=[proposition.pk]),
                                {"etape": etape or self.etat(proposition)})

    def verifier(self, user, proposition, **plus):
        self.client.force_login(user)
        donnees = {"designation": proposition.designation, "categorie": str(proposition.categorie_id), "marque": proposition.marque, **plus}
        return self.client.post(reverse("catalogue-proposition-verifier", args=[proposition.pk]), donnees)

    def etat(self, proposition):
        return PropositionArticle.objects.get(pk=proposition.pk).etat


class CircuitNominalTests(BasePropositions):
    def test_circuit_complet_chef_de_section(self):
        p = self.proposer()
        self.assertEqual(p.etat, Etat.VISA_SECTEUR)
        self.assertEqual((p.service, p.ship, p.secteur), (self.machine, self.ship, self.secteur))
        self.assertFalse(ArticleCatalogue.objects.filter(designation="Clé dynamométrique").exists())
        for valideur, suivant in [(self.chef_secteur, Etat.VISA_SERVICE), (self.chef_service, Etat.VISA_COMA),
                                  (self.comaeq, Etat.VERIFICATION)]:
            self.viser(valideur, p)
            self.assertEqual(self.etat(p), suivant)
        self.assertFalse(ArticleCatalogue.objects.exists())
        self.verifier(self.resp, PropositionArticle.objects.get(pk=p.pk), marque="Facom Pro")
        p.refresh_from_db()
        self.assertEqual((p.etat, p.verificateur, p.marque), (Etat.VISA_CHEF_SPECIALITE, self.resp, "Facom Pro"))
        self.viser(self.chef_resp, p)
        p.refresh_from_db()
        self.assertEqual(p.etat, Etat.PUBLIEE)
        article = ArticleCatalogue.objects.get(designation="Clé dynamométrique")
        self.assertEqual((p.article, article.categorie, article.marque, article.actif), (article, self.categorie, "Facom Pro", True))
        self.assertEqual(article.created_by, self.chef_section)

    def test_chef_de_secteur_redacteur_saute_son_visa(self):
        p = self.proposer(self.chef_secteur)
        self.assertEqual(p.etat, Etat.VISA_SERVICE)
        self.assertNotIn(Etat.VISA_SECTEUR, circuit.circuit(p))

    def test_chaque_transition_est_tracee_et_notifie_la_suivante(self):
        p = self.proposer()
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur, object_id=str(p.pk)).exists())
        self.viser(self.chef_secteur, p)
        self.assertTrue(Notification.objects.filter(user=self.chef_service, object_id=str(p.pk)).exists())
        self.viser(self.chef_service, p)
        self.assertTrue(Notification.objects.filter(user=self.comaeq, object_id=str(p.pk)).exists())
        self.assertFalse(Notification.objects.filter(user=self.comanav).exists())
        self.assertEqual(AuditLog.objects.filter(action="catalogue.proposition.visee", actor=self.chef_secteur).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="catalogue.proposition.soumise").count(), 1)
        self.assertEqual(p.evenements.count(), 3)

    def test_publication_notifie_le_redacteur_et_trace_la_creation(self):
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.viser(self.comaeq, p)
        self.verifier(self.resp, PropositionArticle.objects.get(pk=p.pk))
        self.viser(self.chef_resp, p)
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur, verb__contains="publiée").exists())
        self.assertTrue(AuditLog.objects.filter(action="catalogue.creation", actor=self.chef_resp).exists())

    def test_la_frise_et_le_detail_s_affichent(self):
        p = self.proposer()
        self.client.force_login(self.chef_section)
        page = self.client.get(reverse("catalogue-proposition", args=[p.pk]))
        self.assertContains(page, "mx-frise__etape--actuelle")
        self.assertContains(page, "Commandant adjoint (COMAEQ)")
        self.assertContains(page, "ne peut pas être utilisé pour équiper")
        liste = self.client.get(reverse("catalogue-propositions"))
        self.assertContains(liste, "Clé dynamométrique")


class DroitsEtMachineAEtatsTests(BasePropositions):
    def test_seuls_chefs_de_section_et_de_secteur_proposent(self):
        self.client.force_login(self.chef_service)
        self.assertEqual(self.client.get(reverse("catalogue-proposition-nouvelle")).status_code, 403)
        self.client.force_login(self.chef_section)
        self.assertEqual(self.client.get(reverse("catalogue-proposition-nouvelle")).status_code, 200)

    def test_saut_d_etape_refuse_meme_en_post_direct(self):
        p = self.proposer()
        # Le chef de service et le COMA ne peuvent pas viser à la place du chef de secteur.
        for intrus in (self.chef_service, self.comaeq):
            self.viser(intrus, p)
            self.assertEqual(self.etat(p), Etat.VISA_SECTEUR)
        # Un envoi périmé (étape attendue différente) est refusé.
        self.viser(self.chef_secteur, p, etape=Etat.VISA_COMA)
        self.assertEqual(self.etat(p), Etat.VISA_SECTEUR)
        # La vérification n'est pas un visa.
        with self.assertRaises(circuit.ErreurCircuit):
            circuit.viser(self.resp, p.pk, Etat.VERIFICATION)

    def test_mauvais_valideur_refuse(self):
        p = self.proposer(self.chef_secteur)
        autre_service = self._u("chef_service_pont", "CHEF_SERVICE", ship=self.ship, service=self.pont)
        autre_secteur = self._u("chef_secteur_aux", "CHEF_SECTEUR", ship=self.ship, service=self.machine, sector=self.autre_secteur)
        for intrus in (autre_service, autre_secteur, self.comaeq, self.resp):
            self.viser(intrus, p)
            self.assertEqual(self.etat(p), Etat.VISA_SERVICE)
        self.viser(self.chef_service, p)
        for intrus in (self.comanav, self.chef_service, self.chef_secteur):
            self.viser(intrus, p)
            self.assertEqual(self.etat(p), Etat.VISA_COMA)

    def test_l_etat_major_non_titulaire_ne_vise_pas(self):
        em = self._u("em_simple", "ETAT_MAJOR", ship=self.ship)
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.viser(em, p)
        self.assertEqual(self.etat(p), Etat.VISA_COMA)

    def test_l_auteur_ne_vise_pas_sa_proposition(self):
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_secteur, p)
        self.assertEqual(self.etat(p), Etat.VISA_SERVICE)
        autorise, raison = circuit.peut_agir(self.chef_secteur, p)
        self.assertFalse(autorise)
        self.assertIn("propre proposition", raison)

    def test_une_personne_ne_cumule_pas_deux_etapes(self):
        # Le chef de service est aussi responsable de la spécialité : il ne peut pas vérifier après avoir visé.
        ResponsableSpecialite.objects.create(specialite=self.categorie.specialite, user=self.chef_service)
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.viser(self.comaeq, p)
        self.verifier(self.chef_service, PropositionArticle.objects.get(pk=p.pk))
        self.assertEqual(self.etat(p), Etat.VERIFICATION)
        self.assertFalse(circuit.peut_agir(self.chef_service, PropositionArticle.objects.get(pk=p.pk))[0])

    def test_double_visa_concurrent(self):
        p = self.proposer(self.chef_secteur)
        perimee = PropositionArticle.objects.get(pk=p.pk)
        circuit.viser(self.chef_service, p.pk, Etat.VISA_SERVICE)
        # Deuxième envoi issu de la même page : la proposition a déjà avancé.
        with self.assertRaises(circuit.ErreurCircuit):
            circuit.viser(self.chef_service, perimee.pk, perimee.etat)
        self.assertEqual(self.etat(p), Etat.VISA_COMA)
        self.assertEqual(p.evenements.filter(action="visee").count(), 1)

    def test_lecture_seule_a_terre(self):
        self.ship.double_equipage, self.ship.equipage_a_bord = True, "A"
        self.ship.save()
        UserProfile.objects.filter(user=self.chef_section).update(equipage="B")
        self.client.force_login(User.objects.get(pk=self.chef_section.pk))
        reponse = self.client.post(reverse("catalogue-proposition-nouvelle"), {"designation": "X", "categorie": str(self.categorie.pk)})
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(PropositionArticle.objects.exists())


class RefusTests(BasePropositions):
    def refuser(self, user, proposition, motif="", etape=None):
        self.client.force_login(user)
        return self.client.post(reverse("catalogue-proposition-refuser", args=[proposition.pk]),
                                {"etape": etape or self.etat(proposition), "motif": motif})

    def test_refus_sans_motif_refuse(self):
        p = self.proposer()
        self.refuser(self.chef_secteur, p, "   ")
        self.assertEqual(self.etat(p), Etat.VISA_SECTEUR)

    def test_refus_revient_au_redacteur_puis_nouveau_circuit(self):
        p = self.proposer()
        self.refuser(self.chef_secteur, p, "Référence manquante")
        p.refresh_from_db()
        self.assertEqual((p.etat, p.motif_refus), (Etat.REFUSEE, "Référence manquante"))
        self.assertTrue(Notification.objects.filter(user=self.chef_section, verb__contains="Référence manquante").exists())
        self.assertTrue(AuditLog.objects.filter(action="catalogue.proposition.refusee", details__contains="Référence manquante").exists())
        # Plus aucun visa possible tant que le rédacteur n'a pas corrigé.
        self.viser(self.chef_secteur, p, etape=Etat.VISA_SECTEUR)
        self.assertEqual(self.etat(p), Etat.REFUSEE)
        self.client.force_login(self.chef_section)
        reponse = self.client.post(reverse("catalogue-proposition-modifier", args=[p.pk]), {
            "designation": "Clé dynamométrique", "categorie": str(self.categorie.pk), "reference": "TW-200"})
        self.assertEqual(reponse.status_code, 302)
        p.refresh_from_db()
        self.assertEqual((p.etat, p.reference, p.motif_refus), (Etat.VISA_SECTEUR, "TW-200", ""))
        self.assertEqual(p.evenements.filter(action="resoumise").count(), 1)

    def test_seul_le_redacteur_corrige(self):
        p = self.proposer()
        self.refuser(self.chef_secteur, p, "Non")
        self.client.force_login(self.chef_secteur)
        self.assertEqual(self.client.get(reverse("catalogue-proposition-modifier", args=[p.pk])).status_code, 404)

    def test_le_responsable_peut_renvoyer(self):
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.viser(self.comaeq, p)
        self.refuser(self.resp, p, "Doublon d'un article existant")
        self.assertEqual(self.etat(p), Etat.REFUSEE)

    def test_un_mauvais_valideur_ne_refuse_pas(self):
        p = self.proposer()
        self.refuser(self.chef_service, p, "Non")
        self.assertEqual(self.etat(p), Etat.VISA_SECTEUR)


class ComaEtRepliTests(BasePropositions):
    def test_le_coma_du_bon_service_vise(self):
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.assertEqual(list(circuit.valideurs(PropositionArticle.objects.get(pk=p.pk))), [self.comaeq])

    def test_service_du_pont_routé_vers_comanav(self):
        secteur_pont = Sector.objects.create(service=self.pont, name="Manoeuvre")
        chef_secteur = self._u("chef_secteur_pont", "CHEF_SECTEUR", ship=self.ship, service=self.pont, sector=secteur_pont)
        chef_service = self._u("chef_service_pont", "CHEF_SERVICE", ship=self.ship, service=self.pont)
        p = self.proposer(chef_secteur)
        self.viser(chef_service, p)
        self.viser(self.comaeq, p)
        self.assertEqual(self.etat(p), Etat.VISA_COMA)
        self.viser(self.comanav, p)
        self.assertEqual(self.etat(p), Etat.VERIFICATION)

    def test_repli_sans_commandant_adjoint_configure(self):
        chef_secteur = self._u("chef_secteur_libre", "CHEF_SECTEUR", ship=self.ship, service=self.libre, sector=self.secteur_libre)
        chef_service = self._u("chef_service_libre", "CHEF_SERVICE", ship=self.ship, service=self.libre)
        commandant = self._u("cdt", "COMMANDANT", ship=self.ship)
        p = self.proposer(chef_secteur)
        self.viser(chef_service, p)
        self.assertEqual(self.etat(p), Etat.VISA_COMA)
        # Repli : seuil de rôle de la validation d'une formation du bord ; le chef de service a déjà visé.
        self.viser(chef_service, p)
        self.assertEqual(self.etat(p), Etat.VISA_COMA)
        self.viser(commandant, p)
        self.assertEqual(self.etat(p), Etat.VERIFICATION)

    def test_repli_commandant_d_un_autre_batiment_exclu(self):
        autre = Ship.objects.create(name="Autre", code="AUT")
        etranger = self._u("cdt_autre", "COMMANDANT", ship=autre)
        chef_secteur = self._u("chef_secteur_libre", "CHEF_SECTEUR", ship=self.ship, service=self.libre, sector=self.secteur_libre)
        chef_service = self._u("chef_service_libre", "CHEF_SERVICE", ship=self.ship, service=self.libre)
        p = self.proposer(chef_secteur)
        self.viser(chef_service, p)
        self.viser(etranger, p)
        self.assertEqual(self.etat(p), Etat.VISA_COMA)

    def test_titulaire_inactif_bascule_sur_le_repli_et_signale_l_absence_de_valideur(self):
        User.objects.filter(pk__in=[self.comaeq.pk, self.comanav.pk]).update(is_active=False)
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        p = PropositionArticle.objects.get(pk=p.pk)
        self.assertIn("Aucun valideur disponible", circuit.message_blocage(p))


class PerimetreTests(BasePropositions):
    def test_propositions_invisibles_hors_perimetre(self):
        p = self.proposer()
        autre = Ship.objects.create(name="Autre", code="AUT")
        autre_service = Service.objects.create(ship=autre, name="Machine", commandant_adjoint="COMAEQ")
        etrangers = [
            self._u("cs_autre", "CHEF_SERVICE", ship=autre, service=autre_service),
            self._u("cdt_autre", "COMMANDANT", ship=autre),
            self._u("chef_secteur_aux", "CHEF_SECTEUR", ship=self.ship, service=self.machine, sector=self.autre_secteur),
            self._u("chef_service_pont", "CHEF_SERVICE", ship=self.ship, service=self.pont),
            self.resp,
        ]
        for etranger in etrangers:
            self.client.force_login(etranger)
            self.assertEqual(self.client.get(reverse("catalogue-proposition", args=[p.pk])).status_code, 404, etranger.username)
            self.assertEqual(self.client.post(reverse("catalogue-proposition-viser", args=[p.pk]), {"etape": p.etat}).status_code, 404)
        self.assertEqual(self.etat(p), Etat.VISA_SECTEUR)

    def test_responsable_et_son_chef_voient_en_aval_seulement(self):
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.viser(self.comaeq, p)
        self.client.force_login(self.resp)
        self.assertEqual(self.client.get(reverse("catalogue-proposition", args=[p.pk])).status_code, 200)
        self.client.force_login(self.chef_resp)
        self.assertEqual(self.client.get(reverse("catalogue-proposition", args=[p.pk])).status_code, 404)
        self.verifier(self.resp, PropositionArticle.objects.get(pk=p.pk))
        self.client.force_login(self.chef_resp)
        self.assertEqual(self.client.get(reverse("catalogue-proposition", args=[p.pk])).status_code, 200)

    def test_a_viser_liste_les_propositions_du_valideur(self):
        p = self.proposer()
        self.assertEqual(circuit.propositions_a_viser(self.chef_secteur), [p])
        self.assertEqual(circuit.propositions_a_viser(self.chef_service), [])
        self.client.force_login(self.chef_secteur)
        self.assertContains(self.client.get(reverse("catalogue-propositions")), "Clé dynamométrique")


class ChefDuResponsableTests(BasePropositions):
    def _jusqu_a_la_verification(self):
        p = self.proposer(self.chef_secteur)
        self.viser(self.chef_service, p)
        self.viser(self.comaeq, p)
        return PropositionArticle.objects.get(pk=p.pk)

    def test_sans_chef_designe_la_transmission_est_bloquee(self):
        ChefResponsableSpecialite.objects.all().delete()
        p = self._jusqu_a_la_verification()
        self.verifier(self.resp, p, marque="Corrigée")
        p.refresh_from_db()
        self.assertEqual((p.etat, p.marque), (Etat.VERIFICATION, "Facom"))
        self.assertFalse(ArticleCatalogue.objects.exists())

    @override_settings(CATALOGUE_CHEF_SPECIALITE_OPTIONNEL=True)
    def test_sans_chef_l_etape_est_sautee_si_la_configuration_l_autorise(self):
        ChefResponsableSpecialite.objects.all().delete()
        p = self._jusqu_a_la_verification()
        self.verifier(self.resp, p)
        p.refresh_from_db()
        self.assertEqual(p.etat, Etat.PUBLIEE)
        self.assertTrue(ArticleCatalogue.objects.filter(designation=p.designation).exists())

    def test_le_chef_ne_peut_pas_etre_le_responsable(self):
        lien = ChefResponsableSpecialite.objects.get()
        lien.chef = self.resp
        with self.assertRaises(Exception):
            lien.full_clean()

    def test_la_correction_est_tracee(self):
        p = self._jusqu_a_la_verification()
        self.verifier(self.resp, p, designation="Clé dynamométrique 1/2", nno="9999")
        p.refresh_from_db()
        correction = p.evenements.get(action="corrigee")
        self.assertIn("Désignation", correction.motif)
        self.assertIn("NNO", correction.motif)

    def test_doublon_du_catalogue_refuse(self):
        ArticleCatalogue.objects.create(categorie=self.categorie, designation="Clé dynamométrique", marque="Facom")
        self.client.force_login(self.chef_section)
        reponse = self.client.post(reverse("catalogue-proposition-nouvelle"), {
            "designation": "clé dynamométrique", "categorie": str(self.categorie.pk), "marque": "facom"})
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(PropositionArticle.objects.exists())

    def test_boutons_du_catalogue(self):
        self.client.force_login(self.chef_section)
        page = self.client.get(reverse("catalogue"))
        self.assertContains(page, "Proposer un article")
        vide = self.client.get(reverse("catalogue"), {"q": "introuvable"})
        self.assertContains(vide, "Proposer cet article")
        self.assertContains(vide, "designation=introuvable")
        self.client.force_login(self.chef_service)
        self.assertNotContains(self.client.get(reverse("catalogue")), "Proposer un article")
