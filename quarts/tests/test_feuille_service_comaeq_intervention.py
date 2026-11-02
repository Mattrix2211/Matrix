"""Le COMAEQ corrige l'en-tête ou renvoie la feuille au rédacteur à tout palier du circuit, sans droit de rédacteur."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from notifications.models import Notification
from org.models import Ship
from quarts.models import FeuilleService, RubriqueEnTeteFeuilleService, peut_gerer_brouillon_feuille, peut_intervenir_comaeq


class InterventionComaeqTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="BRF Intervention", code="BI")
        self.rubrique = RubriqueEnTeteFeuilleService.objects.create(ship=self.navire, libelle="Saint du jour")
        self.comaeq = self._marin("comaeq", "ETAT_MAJOR", fonction_coma="COMAEQ")
        self.bsc = self._marin("bsc", "EQUIPIER")
        self.chef = self._marin("chef", "CHEF_SERVICE")
        self.commandant = self._marin("cdt", "COMMANDANT")
        self.feuille = FeuilleService.objects.create(
            ship=self.navire, date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
            created_by=self.bsc, valeurs_entete={str(self.rubrique.uid): "Saint Hervé"},
        )
        self.feuille.visa_secteur_par = self.feuille.visa_service_par = self.chef
        self.feuille.visa_secteur_le = self.feuille.visa_service_le = timezone.now()
        self.feuille.proposee_par = self.bsc
        self.feuille.proposee_le = timezone.now() - timezone.timedelta(minutes=5)
        self.feuille.empreinte_visee = self.feuille._empreinte_contenu()
        self.feuille.save()
        self.url = reverse("feuille-service-detail", args=[self.navire.pk, f"{self.feuille.date:%Y-%m-%d}"])
        self.cle = f"rubrique_{self.rubrique.uid}"

    def _marin(self, nom, role, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, **champs})
        return User.objects.get(pk=user.pk)

    def _post(self, nom, **donnees):
        self.client.force_login(User.objects.get(username=nom))
        return self.client.post(self.url, donnees)

    def test_le_comaeq_corrige_sans_etre_redacteur_et_conserve_les_visas(self):
        self.assertFalse(peut_gerer_brouillon_feuille(self.comaeq, self.feuille))
        self.assertTrue(peut_intervenir_comaeq(self.comaeq, self.feuille))
        self._post("comaeq", action="modifier_comaeq", motif="Erreur de saint", **{self.cle: "Saint Gilles"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Gilles")
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertEqual(self.feuille.visa_secteur_par, self.chef)
        self.assertEqual(self.feuille.visa_service_par, self.chef)
        trace = AuditLog.objects.get(action="feuille_service_modifiee_comaeq")
        self.assertIn("Erreur de saint", trace.details)
        self.assertIn("Saint Hervé -> Saint Gilles", trace.details)
        self.assertTrue(Notification.objects.filter(user=self.bsc, verb__contains="corrigée par le COMAEQ").exists())

    def test_la_publication_reste_possible_apres_la_correction(self):
        self._post("comaeq", action="modifier_comaeq", motif="Erreur", **{self.cle: "Saint Gilles"})
        self.feuille.refresh_from_db()
        self.assertTrue(self.feuille.viser_comaeq(self.comaeq, self.feuille._empreinte_contenu()))
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)

    def test_motif_obligatoire(self):
        self._post("comaeq", action="modifier_comaeq", motif="  ", **{self.cle: "Saint Gilles"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Hervé")
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_modifiee_comaeq").exists())

    def test_les_autres_n_ont_pas_ce_pouvoir(self):
        for nom in ("bsc", "chef", "cdt"):
            reponse = self._post(nom, action="modifier_comaeq", motif="x", **{self.cle: "Pirate"})
            self.assertEqual(reponse.status_code, 403, nom)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Hervé")

    def test_pas_de_correction_sur_une_feuille_publiee_ou_en_brouillon(self):
        for statut in (FeuilleService.STATUT_BROUILLON, FeuilleService.STATUT_PUBLIEE):
            FeuilleService.objects.filter(pk=self.feuille.pk).update(statut=statut)
            reponse = self._post("comaeq", action="modifier_comaeq", motif="x", **{self.cle: "Autre"})
            self.assertEqual(reponse.status_code, 403, statut)

    def test_contenu_change_ailleurs_la_correction_est_refusee_sans_recaler_l_empreinte(self):
        empreinte = self.feuille.empreinte_visee
        FeuilleService.objects.filter(pk=self.feuille.pk).update(empreinte_visee="perimee")
        self._post("comaeq", action="modifier_comaeq", motif="Erreur", **{self.cle: "Saint Gilles"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.empreinte_visee, "perimee")
        self.assertNotEqual(self.feuille.empreinte_visee, empreinte)
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Hervé")

    def test_le_comaeq_renvoie_a_tout_palier_avec_motif(self):
        for statut in (FeuilleService.STATUT_VISA_SECTEUR, FeuilleService.STATUT_VISA_SERVICE, FeuilleService.STATUT_VISA_COMAEQ):
            FeuilleService.objects.filter(pk=self.feuille.pk).update(statut=statut)
            reponse = self._post("comaeq", action="renvoyer", motif=f"Reprendre ({statut})")
            self.assertEqual(reponse.status_code, 302, statut)
            self.feuille.refresh_from_db()
            self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON, statut)
            self.assertIsNone(self.feuille.visa_service_par)
            FeuilleService.objects.filter(pk=self.feuille.pk).update(statut=FeuilleService.STATUT_VISA_COMAEQ, visa_service_par=self.chef)

    def test_un_marin_sans_pouvoir_ne_renvoie_pas(self):
        FeuilleService.objects.filter(pk=self.feuille.pk).update(statut=FeuilleService.STATUT_VISA_SECTEUR)
        self.assertEqual(self._post("bsc", action="renvoyer", motif="x").status_code, 403)

    def test_le_comaeq_voit_les_deux_commandes(self):
        self.client.force_login(self.comaeq)
        page = self.client.get(self.url)
        self.assertContains(page, "Corriger l'en-tête (COMAEQ)")
        self.assertContains(page, "Renvoyer en brouillon pour correction")

    def test_la_colonne_circuit_remonte_pour_qui_a_une_action(self):
        self.client.force_login(self.comaeq)
        self.assertContains(self.client.get(self.url), "order-first order-xl-last")
        self.client.force_login(self.commandant)
        page = self.client.get(self.url)
        self.assertContains(page, "Circuit de validation")
        self.assertNotContains(page, "order-first order-xl-last")

    def test_le_circuit_dit_ce_qui_est_fait_et_ce_qui_est_attendu(self):
        self.client.force_login(self.comaeq)
        page = self.client.get(self.url)
        self.assertContains(page, "Action attendue")
        self.assertContains(page, "mx-circuit__etape--fait")
        self.assertContains(page, "mx-circuit__etape--en-cours")
        self.assertContains(page, "Dernière modification")

    def test_une_reecriture_n_est_pas_une_correction(self):
        self._post("comaeq", action="modifier_comaeq", motif="Réécriture", **{self.cle: "Programme entièrement différent du jour"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Hervé")
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_modifiee_comaeq").exists())

    def test_l_ajout_trop_long_dans_une_rubrique_vide_est_refuse(self):
        FeuilleService.objects.filter(pk=self.feuille.pk).update(valeurs_entete={})
        self.feuille.refresh_from_db()
        FeuilleService.objects.filter(pk=self.feuille.pk).update(empreinte_visee=self.feuille._empreinte_contenu())
        self._post("comaeq", action="modifier_comaeq", motif="Ajout", **{self.cle: "x" * 120})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete, {})

    def test_la_correction_acceptee_reste_signalee_dans_le_circuit(self):
        self._post("comaeq", action="modifier_comaeq", motif="Coquille", **{self.cle: "Saint Herve"})
        self.client.force_login(self.comaeq)
        page = self.client.get(self.url)
        self.assertContains(page, "Corrigée par le COMAEQ après proposition")
        self.assertContains(page, "Coquille")


    def test_une_seule_correction_legere_par_cycle_de_visa(self):
        self._post("comaeq", action="modifier_comaeq", motif="Coquille", **{self.cle: "Saint Herve"})
        self._post("comaeq", action="modifier_comaeq", motif="Encore", **{self.cle: "Saint Herve!"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Herve")
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_modifiee_comaeq").count(), 1)


class InterventionComaeqDoubleEquipageTests(TestCase):
    """Le COMAEQ de l'autre équipage n'a aucun pouvoir sur la feuille de l'équipage à bord."""

    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM Interv", code="FI", double_equipage=True, equipage_a_bord="A")
        self.rubrique = RubriqueEnTeteFeuilleService.objects.create(ship=self.navire, libelle="Saint du jour")
        self.coma_a = self._marin("coma_a", "A")
        self.coma_b = self._marin("coma_b", "B")
        self.feuille = FeuilleService.objects.create(
            ship=self.navire, equipage="A", date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
            valeurs_entete={str(self.rubrique.uid): "Saint Hervé"},
        )
        self.feuille.proposee_le = timezone.now()
        self.feuille.empreinte_visee = self.feuille._empreinte_contenu()
        self.feuille.save()
        self.url = reverse("feuille-service-detail", args=[self.navire.pk, f"{self.feuille.date:%Y-%m-%d}"])

    def _marin(self, nom, equipage):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": "ETAT_MAJOR", "ship": self.navire, "equipage": equipage, "fonction_coma": "COMAEQ"})
        return User.objects.get(pk=user.pk)

    def test_seul_le_comaeq_de_l_equipage_de_la_feuille_intervient(self):
        self.assertTrue(peut_intervenir_comaeq(self.coma_a, self.feuille))
        self.assertFalse(peut_intervenir_comaeq(self.coma_b, self.feuille))
        self.client.force_login(self.coma_b)
        for donnees in ({"action": "modifier_comaeq", "motif": "x"}, {"action": "renvoyer", "motif": "x"}):
            reponse = self.client.post(self.url + "?equipage=A", donnees)
            self.assertIn(reponse.status_code, (400, 403, 404), donnees["action"])
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertEqual(self.feuille.valeurs_entete[str(self.rubrique.uid)], "Saint Hervé")


class CorrectionComaeqEtanchePeriEquipageTests(TestCase):
    """La correction faite sur la feuille d'un équipage n'apparaît jamais dans le circuit de l'autre."""

    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM Etanche", code="FE", double_equipage=True, equipage_a_bord="B")
        self.rubrique = RubriqueEnTeteFeuilleService.objects.create(ship=self.navire, libelle="Saint du jour")
        self.coma = {}
        self.feuilles = {}
        for equipage in ("A", "B"):
            user = User.objects.create_user(username=f"coma_{equipage}", password="pass")
            UserProfile.objects.update_or_create(user=user, defaults={
                "role": "ETAT_MAJOR", "ship": self.navire, "equipage": equipage, "fonction_coma": "COMAEQ"})
            self.coma[equipage] = User.objects.get(pk=user.pk)
            feuille = FeuilleService.objects.create(
                ship=self.navire, equipage=equipage, date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
                valeurs_entete={str(self.rubrique.uid): "Saint Hervé"})
            feuille.proposee_le = timezone.now() - timezone.timedelta(minutes=5)
            feuille.empreinte_visee = feuille._empreinte_contenu()
            feuille.save()
            self.feuilles[equipage] = feuille

    def test_la_correction_de_b_est_invisible_sur_la_feuille_de_a(self):
        feuille_b = self.feuilles["B"]
        self.client.force_login(self.coma["B"])
        url_b = reverse("feuille-service-detail", args=[self.navire.pk, f"{feuille_b.date:%Y-%m-%d}"])
        self.client.post(url_b, {"action": "modifier_comaeq", "motif": "Coquille B", f"rubrique_{self.rubrique.uid}": "Saint Herve"})
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_modifiee_comaeq").count(), 1)
        self.assertContains(self.client.get(url_b), "Corrigée par le COMAEQ")
        self.client.force_login(self.coma["A"])
        url_a = reverse("feuille-service-detail", args=[self.navire.pk, f"{self.feuilles['A'].date:%Y-%m-%d}"]) + "?equipage=A"
        page_a = self.client.get(url_a)
        self.assertNotContains(page_a, "Corrigée par le COMAEQ")
        self.assertNotContains(page_a, "Coquille B")
