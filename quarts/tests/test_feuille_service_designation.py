"""Désignation des rédacteurs de la feuille de service : autorité du COMAEQ de l'équipage, cloisonnement par
équipage (à bord comme à terre), désignations devenues inopérantes."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from matrix.core.equipage import tracer_changement_equipage
from org.models import Service, Ship
from quarts.models import (
    RedacteurFeuilleService,
    designations_inoperantes,
    designations_inoperantes_de,
    equipages_sans_redacteur,
    peut_designer_redacteurs,
    peut_rediger_feuille_service,
)


class DesignationBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM Désignation", code="FDG", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(ship=self.navire, name="Pont")
        self.url = reverse("feuille-service-redacteurs")
        for e in ("A", "B"):
            self._m(f"coma_{e}", "ETAT_MAJOR", e, fonction_coma="COMAEQ")
            self._m(f"cdt_{e}", "COMMANDANT", e)
            self._m(f"second_{e}", "COMMANDANT_EN_SECOND", e)
            self._m(f"chef_service_{e}", "CHEF_SERVICE", e, service=self.service)
            self._m(f"matelot_{e}", "EQUIPIER", e)
        self._m("admin_unite", "ADMIN_NAVIRE", "")
        self._m("maitre", "MASTER_ADMIN", "")

    def _m(self, nom, role, equipage, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def _post(self, nom, action, **donnees):
        self.client.force_login(User.objects.get(username=nom))
        return self.client.post(self.url, {"action": action, "ship": self.navire.pk, **donnees})

    def _designer(self, nom, cible):
        return self._post(nom, "designer", user=User.objects.get(username=cible).pk)


class AutoriteTests(DesignationBase):
    def test_le_comaeq_de_l_equipage_designe_avec_trace(self):
        self.assertEqual(self._designer("coma_A", "matelot_A").status_code, 302)
        designation = RedacteurFeuilleService.objects.get(user__username="matelot_A")
        self.assertEqual((designation.equipage, designation.accordee_par.username), ("A", "coma_A"))
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_redacteur_designe").count(), 1)
        self.assertTrue(peut_rediger_feuille_service(User.objects.get(username="matelot_A"), self.navire))

    def test_ni_le_grade_ni_un_seuil_de_role_ne_suffisent(self):
        for nom in ("chef_service_A", "second_A", "cdt_A", "admin_unite", "maitre", "matelot_A"):
            self.assertEqual(self._designer(nom, "matelot_A").status_code, 403, nom)
        self.assertFalse(RedacteurFeuilleService.objects.exists())

    def test_le_bsc_ne_designe_personne(self):
        RedacteurFeuilleService.objects.create(ship=self.navire, equipage="A", user=User.objects.get(username="matelot_A"))
        self.assertEqual(self._designer("matelot_A", "chef_service_A").status_code, 403)

    def test_aucun_droit_sur_l_autre_equipage(self):
        self.assertEqual(self._designer("coma_A", "matelot_B").status_code, 403)
        designation = RedacteurFeuilleService.objects.create(ship=self.navire, equipage="B", user=User.objects.get(username="matelot_B"))
        self.assertEqual(self._post("coma_A", "retirer", pk=designation.pk).status_code, 403)
        self.assertTrue(RedacteurFeuilleService.objects.filter(pk=designation.pk).exists())

    def test_l_equipage_a_terre_designe_les_siens_sans_toucher_a_l_autre(self):
        # A est à bord : l'équipage B est à terre, en lecture seule ailleurs, mais désigne ses propres rédacteurs.
        self.assertEqual(self._designer("coma_B", "matelot_B").status_code, 302)
        self.assertTrue(RedacteurFeuilleService.objects.filter(user__username="matelot_B", equipage="B").exists())
        self.assertEqual(self._designer("coma_B", "matelot_A").status_code, 403)
        designation = RedacteurFeuilleService.objects.get(user__username="matelot_B")
        self.assertEqual(self._post("coma_B", "retirer", pk=designation.pk).status_code, 302)
        self.assertFalse(RedacteurFeuilleService.objects.exists())

    def test_l_equipage_a_terre_reste_en_lecture_seule_ailleurs(self):
        self.client.force_login(User.objects.get(username="coma_B"))
        reglages = self.client.post(reverse("feuille-service-reglages"), {"action": "enregistrer_rubriques", "ship": self.navire.pk})
        self.assertEqual(reglages.status_code, 403)

    def test_poste_de_comaeq_vacant_le_commandant_de_l_equipage_designe_en_secours(self):
        UserProfile.objects.filter(user__username="coma_A").update(fonction_coma="")
        self.assertEqual(self._designer("chef_service_A", "matelot_A").status_code, 403)
        self.assertEqual(self._designer("cdt_B", "matelot_A").status_code, 403)
        self.assertEqual(self._designer("second_A", "matelot_A").status_code, 403)
        self.assertEqual(self._designer("cdt_A", "matelot_A").status_code, 302)

    def test_le_commandant_ne_double_pas_un_comaeq_en_poste(self):
        self.assertFalse(peut_designer_redacteurs(User.objects.get(username="cdt_A"), self.navire, "A"))

    def test_cible_d_un_autre_batiment_ou_inactive_introuvable(self):
        autre = Ship.objects.create(name="Autre", code="AUT")
        etranger = User.objects.create_user(username="etranger", password="pass")
        UserProfile.objects.update_or_create(user=etranger, defaults={"role": "EQUIPIER", "ship": autre})
        self.assertEqual(self._designer("coma_A", "etranger").status_code, 404)
        User.objects.filter(username="matelot_A").update(is_active=False)
        self.assertEqual(self._designer("coma_A", "matelot_A").status_code, 404)

    def test_double_designation_sans_doublon_ni_nouvelle_trace(self):
        self._designer("coma_A", "matelot_A")
        self._designer("coma_A", "matelot_A")
        self.assertEqual(RedacteurFeuilleService.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_redacteur_designe").count(), 1)

    def test_retrait_trace(self):
        self._designer("coma_A", "matelot_A")
        designation = RedacteurFeuilleService.objects.get()
        self._post("coma_A", "retirer", pk=designation.pk)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_redacteur_retire", target_user__username="matelot_A").exists())

    def test_la_page_est_lisible_par_tout_marin_sans_commande_de_designation(self):
        self.client.force_login(User.objects.get(username="matelot_A"))
        page = self.client.get(self.url, {"ship": self.navire.pk})
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "appartient au COMAEQ")
        self.assertNotContains(page, 'name="action" value="designer"')

    def test_les_reglages_ne_designent_plus_personne(self):
        self.client.force_login(User.objects.get(username="chef_service_A"))
        reponse = self.client.post(reverse("feuille-service-reglages"), {
            "action": "designer_redacteur", "ship": self.navire.pk, "user": User.objects.get(username="matelot_A").pk})
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(RedacteurFeuilleService.objects.exists())

    def test_equipage_unique(self):
        simple = Ship.objects.create(name="BRF simple", code="BRS")
        profil = UserProfile.objects.get(user__username="coma_A")
        profil.ship, profil.equipage = simple, ""
        profil.save()
        marin = User.objects.create_user(username="marin_simple", password="pass")
        UserProfile.objects.update_or_create(user=marin, defaults={"role": "EQUIPIER", "ship": simple})
        self.client.force_login(User.objects.get(username="coma_A"))
        reponse = self.client.post(self.url, {"action": "designer", "ship": simple.pk, "user": marin.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(RedacteurFeuilleService.objects.filter(ship=simple, equipage="", user=marin).exists())


class DesignationsInoperantesTests(DesignationBase):
    def setUp(self):
        super().setUp()
        self.matelot = User.objects.get(username="matelot_A")
        self.designation = RedacteurFeuilleService.objects.create(ship=self.navire, equipage="A", user=self.matelot)

    def test_designation_operante_ne_signale_rien(self):
        self.assertEqual(designations_inoperantes(self.navire), [])

    def test_changement_d_equipage_rend_la_designation_inoperante_sans_droit_chez_l_autre(self):
        UserProfile.objects.filter(user=self.matelot).update(equipage="B")
        self.assertEqual([d.pk for d in designations_inoperantes(self.navire)], [self.designation.pk])
        self.assertFalse(peut_rediger_feuille_service(User.objects.get(pk=self.matelot.pk), self.navire))
        self.assertIn("A", equipages_sans_redacteur(self.navire))
        self.assertEqual([d.pk for d in designations_inoperantes_de(self.matelot)], [self.designation.pk])

    def test_compte_desactive_ou_parti(self):
        User.objects.filter(pk=self.matelot.pk).update(is_active=False)
        self.assertEqual(len(designations_inoperantes(self.navire)), 1)
        User.objects.filter(pk=self.matelot.pk).update(is_active=True)
        UserProfile.objects.filter(user=self.matelot).update(ship=None)
        self.assertEqual(len(designations_inoperantes(self.navire)), 1)

    def test_passage_en_equipage_unique_trace_les_designations_inoperantes(self):
        avant = (True, "A")
        self.navire.double_equipage = False
        self.navire.save()
        tracer_changement_equipage(User.objects.get(username="cdt_A"), self.navire, avant)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_redacteur_inoperant", target_user=self.matelot).exists())
        self.assertEqual(equipages_sans_redacteur(self.navire), [""])

    def test_la_page_avertit(self):
        UserProfile.objects.filter(user=self.matelot).update(equipage="B")
        self.client.force_login(User.objects.get(username="coma_A"))
        page = self.client.get(self.url, {"ship": self.navire.pk})
        self.assertContains(page, "Désignation(s) devenue(s) inopérante(s)")
        self.assertContains(page, "Aucun rédacteur opérant")

    def test_la_feuille_avertit_ceux_qui_designent(self):
        RedacteurFeuilleService.objects.all().delete()
        url = reverse("feuille-service-detail", args=[self.navire.pk, "2026-11-02"])
        self.client.force_login(User.objects.get(username="coma_A"))
        self.assertContains(self.client.get(url), "Aucun rédacteur opérant")
        self.client.force_login(User.objects.get(username="matelot_A"))
        self.assertNotContains(self.client.get(url), "Aucun rédacteur opérant")  # le marin n'a rien à y faire

    def test_la_modification_d_un_profil_previent_et_trace(self):
        self.client.force_login(User.objects.get(username="admin_unite"))
        reponse = self.client.post(reverse("user-directory"), {
            "action": "edit_user", "pk": self.matelot.pk, "role": "EQUIPIER", "ship": self.navire.pk, "equipage": "B",
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)
        if UserProfile.objects.get(user=self.matelot).equipage == "B":
            self.assertContains(reponse, "ne donne plus aucun droit")
            self.assertTrue(AuditLog.objects.filter(action="feuille_service_redacteur_inoperant").exists())


class BasculeEquipageUniqueDoubleTests(DesignationBase):
    """Un bâtiment passé d'équipage unique à double équipage garde des désignations sans équipage : elles sont inopérantes
    et doivent rester retirables par l'autorité de l'équipage du demandeur, sans droit sur la feuille de l'autre équipage."""

    def setUp(self):
        super().setUp()
        self.matelot = User.objects.get(username="matelot_A")
        self.ancienne = RedacteurFeuilleService.objects.create(ship=self.navire, equipage="", user=self.matelot)

    def test_la_designation_sans_equipage_ne_donne_aucun_droit(self):
        self.assertFalse(peut_rediger_feuille_service(self.matelot, self.navire))
        self.assertEqual([d.pk for d in designations_inoperantes(self.navire)], [self.ancienne.pk])

    def test_le_comaeq_de_l_equipage_la_retire(self):
        self.assertEqual(self._post("coma_A", "retirer", pk=self.ancienne.pk).status_code, 302)
        self.assertFalse(RedacteurFeuilleService.objects.filter(pk=self.ancienne.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_redacteur_retire").exists())

    def test_le_comaeq_a_terre_la_retire_aussi_mais_ni_chef_de_service_ni_matelot(self):
        for nom in ("chef_service_A", "matelot_A", "second_A"):
            self.assertEqual(self._post(nom, "retirer", pk=self.ancienne.pk).status_code, 403, nom)
        self.assertEqual(self._post("coma_B", "retirer", pk=self.ancienne.pk).status_code, 302)

    def test_une_designation_operante_reste_protegee_entre_equipages(self):
        operante = RedacteurFeuilleService.objects.create(ship=self.navire, equipage="A", user=self.matelot)
        self.assertEqual(self._post("coma_B", "retirer", pk=operante.pk).status_code, 403)

    def test_la_page_propose_le_retrait(self):
        self.client.force_login(User.objects.get(username="coma_A"))
        self.assertContains(self.client.get(self.url, {"ship": self.navire.pk}), "Inopérante")
        self.assertContains(self.client.get(self.url, {"ship": self.navire.pk}), 'value="retirer"')
