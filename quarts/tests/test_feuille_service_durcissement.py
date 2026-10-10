"""Double équipage : durcissement de la feuille de service (réserves du Tech Lead,
décisions du 30/09/2026) — paramètre ?equipage= protégé, choix déterministe de
la feuille du jour, état incohérent signalé, feuilles historiques retrouvables
et rattachables (avec trace dans l'AuditLog)."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from org.models import Ship
from quarts.models import FeuilleService, feuille_du_jour


def creer_marin(username, role, ship, equipage=""):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class BaseFeuille(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="FREMM Feuille D", code="FFD", classe_navire="FREMM", double_equipage=True)
        self.bleu, self.rouge = "A", "B"
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        self.jour = timezone.localdate()
        self.url = f"/quarts/feuille-service/{self.ship.pk}/{self.jour.isoformat()}/"

    def feuille(self, equipage, statut=FeuilleService.STATUT_PUBLIEE, jour=None):
        return FeuilleService.objects.create(ship=self.ship, equipage=equipage, date=jour or self.jour, statut=statut)


class ParametreEquipageTests(BaseFeuille):
    def test_chiffres_unicode_ne_provoquent_pas_d_erreur_500(self):
        self.client.force_login(creer_marin("admin_g", "MASTER_ADMIN", None))
        self.feuille(self.bleu)
        for valeur in ("²", "٣", "①", "1e3", "-1", ""):
            reponse = self.client.get(self.url, {"equipage": valeur})
            self.assertEqual(reponse.status_code, 200, valeur)
            self.assertEqual(reponse.context["equipage"], self.bleu, valeur)

    def test_equipage_choisi_par_l_administrateur_general(self):
        self.client.force_login(creer_marin("admin_g", "MASTER_ADMIN", None))
        reponse = self.client.get(self.url, {"equipage": self.rouge})
        self.assertEqual(reponse.context["equipage"], self.rouge)


class FeuilleDuJourDeterministeTests(BaseFeuille):
    def test_double_equipage_feuille_de_l_equipage_demande_uniquement(self):
        sans = self.feuille("")
        bleue, rouge = self.feuille(self.bleu), self.feuille(self.rouge)
        self.assertEqual(feuille_du_jour(self.ship, self.jour, self.bleu), bleue)
        self.assertEqual(feuille_du_jour(self.ship, self.jour, self.rouge), rouge)
        self.assertIsNone(feuille_du_jour(self.ship, self.jour, ""))
        self.assertNotEqual(feuille_du_jour(self.ship, self.jour, self.bleu), sans)

    def test_equipage_unique_prefere_la_feuille_sans_equipage(self):
        self.ship.double_equipage = False
        self.ship.save()
        self.feuille(self.rouge)
        sans = self.feuille("")
        self.feuille(self.bleu)
        self.assertEqual(feuille_du_jour(self.ship, self.jour, ""), sans)

    def test_equipage_unique_sans_feuille_neutre_prefere_l_equipage_a_bord(self):
        self.ship.double_equipage = False
        self.ship.save()
        self.feuille(self.rouge)
        bleue = self.feuille(self.bleu)
        for _ in range(3):
            self.assertEqual(feuille_du_jour(self.ship, self.jour, ""), bleue)

    def test_equipage_unique_feuille_historique_demandee_et_lien_vers_les_autres(self):
        self.ship.double_equipage = False
        self.ship.save()
        self.feuille(self.rouge)
        self.feuille(self.bleu)
        self.client.force_login(creer_marin("cdt_u", "COMMANDANT", self.ship))
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.context["feuille"].equipage, self.bleu)
        self.assertContains(reponse, f"?equipage={self.rouge}")
        reponse = self.client.get(self.url, {"equipage": self.rouge})
        self.assertEqual(reponse.context["feuille"].equipage, self.rouge)

    def test_equipage_unique_creation_sans_equipage_meme_avec_parametre(self):
        self.ship.double_equipage = False
        self.ship.save()
        marin = creer_marin("marin_u", "EQUIPIER", self.ship)
        self.client.force_login(marin)
        self.client.post(f"{self.url}?equipage={self.rouge}", {"action": "creer"})
        self.assertEqual(FeuilleService.objects.get().equipage, "")


class EtatIncoherentTests(BaseFeuille):
    def setUp(self):
        super().setUp()
        self.ship.equipage_a_bord = ""
        self.ship.save()
        self.cdt = creer_marin("cdt_i", "COMMANDANT", self.ship)
        self.client.force_login(self.cdt)

    def test_etat_incoherent_message_et_lien_vers_les_equipages(self):
        self.feuille("")
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["etat_incoherent"])
        self.assertIsNone(reponse.context["feuille"])
        self.assertContains(reponse, "Configuration à corriger")

    def test_aucune_creation_en_etat_incoherent(self):
        reponse = self.client.post(self.url, {"action": "creer"}, follow=True)
        self.assertFalse(FeuilleService.objects.exists())
        self.assertContains(reponse, "Aucun équipage à bord n")

    def test_equipage_a_bord_defini_pas_d_etat_incoherent(self):
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        self.assertFalse(self.client.get(self.url).context["etat_incoherent"])

    def test_equipage_unique_jamais_incoherent(self):
        unique = Ship.objects.create(name="BRF D", code="BRD")
        marin = creer_marin("marin_b", "EQUIPIER", unique)
        self.client.force_login(marin)
        reponse = self.client.get(f"/quarts/feuille-service/{unique.pk}/{self.jour.isoformat()}/")
        self.assertFalse(reponse.context["etat_incoherent"])


class RattachementFeuilleHistoriqueTests(BaseFeuille):
    def setUp(self):
        super().setUp()
        self.cdt = creer_marin("cdt_r", "COMMANDANT", self.ship, self.bleu)
        self.client.force_login(self.cdt)
        self.orpheline = self.feuille("")

    def _rattacher(self, equipage, feuille=None):
        return self.client.post(self.url, {
            "action": "rattacher_feuille", "feuille_id": (feuille or self.orpheline).pk, "equipage": equipage,
        })

    def test_feuille_sans_equipage_listee_sur_le_double_equipage(self):
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Feuilles historiques sans équipage")
        self.assertIn(self.orpheline, list(reponse.context["feuilles_sans_equipage"]))

    def test_rattachement_trace_dans_l_audit_log(self):
        self._rattacher(self.rouge)
        self.orpheline.refresh_from_db()
        self.assertEqual(self.orpheline.equipage, self.rouge)
        journal = AuditLog.objects.get(action="rattacher_feuille_service")
        self.assertEqual(journal.actor, self.cdt)
        self.assertIn("-> B", journal.details)
        self.assertIn(self.jour.isoformat(), journal.details)

    def test_rattachement_refuse_si_l_equipage_a_deja_une_feuille_ce_jour(self):
        self.feuille(self.rouge)
        self._rattacher(self.rouge)
        self.orpheline.refresh_from_db()
        self.assertEqual(self.orpheline.equipage, "")
        self.assertFalse(AuditLog.objects.filter(action="rattacher_feuille_service").exists())

    def test_rattachement_reserve_aux_habilites(self):
        self.client.force_login(creer_marin("simple", "EQUIPIER", self.ship, self.bleu))
        self.assertEqual(self._rattacher(self.rouge).status_code, 403)
        self.orpheline.refresh_from_db()
        self.assertEqual(self.orpheline.equipage, "")

    def test_rattachement_d_un_equipage_inconnu_de_l_unite_refuse(self):
        self._rattacher("Z")
        self.orpheline.refresh_from_db()
        self.assertEqual(self.orpheline.equipage, "")

    def test_rattachement_possible_meme_en_etat_incoherent(self):
        self.ship.equipage_a_bord = ""
        self.ship.save()
        UserProfile.objects.filter(user=self.cdt).update(equipage="A")
        self._rattacher(self.bleu)
        self.orpheline.refresh_from_db()
        self.assertEqual(self.orpheline.equipage, self.bleu)

    def test_feuille_retrouvable_apres_rattachement(self):
        self._rattacher(self.bleu)
        self.assertEqual(feuille_du_jour(self.ship, self.jour, self.bleu), self.orpheline)

    def test_identifiant_unicode_ne_provoque_pas_d_erreur_500(self):
        reponse = self.client.post(self.url, {"action": "rattacher_feuille", "feuille_id": "²", "equipage": "²"})
        self.assertEqual(reponse.status_code, 302)
