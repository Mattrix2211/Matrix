"""Rédaction de la feuille de service : réservée aux rédacteurs désignés (BSC, délégués) de leur équipage ;
lecture de la feuille publiée ouverte à tout marin du bâtiment ; visas et publication inchangés."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from org.models import Sector, Service, Ship
from quarts.models import (
    FeuilleService,
    RedacteurFeuilleService,
    peut_acceder_feuille_service,
    peut_lire_feuille_service,
    peut_rediger_feuille_service,
)


class RedactionBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM Rédaction", code="FRD", double_equipage=True, equipage_a_bord="A")
        self.autre_navire = Ship.objects.create(name="Autre bâtiment", code="AUB")
        self.service = Service.objects.create(ship=self.navire, name="Pont")
        self.secteur = Sector.objects.create(service=self.service, name="Courant")
        self.jour = timezone.localdate()
        self.url = reverse("feuille-service-detail", args=[self.navire.pk, f"{self.jour:%Y-%m-%d}"])
        self.matelot_a = self._m("matelot_a", "EQUIPIER", "A")
        self.matelot_b = self._m("matelot_b", "EQUIPIER", "B")
        self.bsc_a = self._m("bsc_a", "EQUIPIER", "A")
        self.bsc_b = self._m("bsc_b", "EQUIPIER", "B")
        self.chef_service_a = self._m("chef_service_a", "CHEF_SERVICE", "A", service=self.service)
        self.chef_service_b = self._m("chef_service_b", "CHEF_SERVICE", "B", service=self.service)
        self.cdt_a = self._m("cdt_a", "COMMANDANT", "A")
        self.second_a = self._m("second_a", "COMMANDANT_EN_SECOND", "A")
        self.coma_a = self._m("coma_a", "ETAT_MAJOR", "A", fonction_coma="COMAEQ")
        self.admin_unite = self._m("admin_unite", "ADMIN_UNITE", "")
        self.maitre = self._m("maitre", "MASTER_ADMIN", "")
        RedacteurFeuilleService.objects.create(ship=self.navire, equipage="A", user=self.bsc_a)
        RedacteurFeuilleService.objects.create(ship=self.navire, equipage="B", user=self.bsc_b)

    def _m(self, nom, role, equipage, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def _post(self, nom, action, suffixe="", **donnees):
        self.client.force_login(User.objects.get(username=nom))
        return self.client.post(self.url + suffixe, {"action": action, **donnees})

    def _publiee(self, equipage="A"):
        feuille = FeuilleService.objects.create(
            ship=self.navire, equipage=equipage, date=self.jour, created_by=self.bsc_a,
            statut=FeuilleService.STATUT_PUBLIEE,
        )
        feuille.creer_version(self.bsc_a)
        return feuille


class CreationEtRedactionTests(RedactionBase):
    def test_un_matelot_ne_cree_pas_de_feuille(self):
        for nom in ("matelot_a", "chef_service_a", "cdt_a", "second_a", "coma_a", "admin_unite", "maitre"):
            self.assertEqual(self._post(nom, "creer").status_code, 403, nom)
        self.assertFalse(FeuilleService.objects.exists())

    def test_le_bsc_designe_cree_la_feuille_de_son_equipage(self):
        self.assertEqual(self._post("bsc_a", "creer").status_code, 302)
        feuille = FeuilleService.objects.get()
        self.assertEqual((feuille.equipage, feuille.created_by), ("A", self.bsc_a))

    def test_le_bsc_d_un_equipage_n_ecrit_pas_chez_l_autre(self):
        self.assertEqual(self._post("bsc_a", "creer", "?equipage=B").status_code, 302)
        self.assertEqual(FeuilleService.objects.get().equipage, "A")  # l'équipage vient du profil, pas du paramètre

    def test_la_designation_vaut_pour_un_equipage_seulement(self):
        RedacteurFeuilleService.objects.filter(user=self.bsc_b).delete()
        RedacteurFeuilleService.objects.create(ship=self.navire, equipage="A", user=self.bsc_b)  # désigné pour A, membre de B
        self.assertFalse(peut_rediger_feuille_service(self.bsc_b, self.navire))

    def test_aucune_action_d_ecriture_pour_un_non_redacteur_sur_une_feuille_existante(self):
        self._post("bsc_a", "creer")
        for nom in ("matelot_a", "chef_service_a", "cdt_a", "second_a", "admin_unite", "maitre"):
            for action in ("enregistrer_entete", "resynchroniser", "proposer"):
                self.assertEqual(self._post(nom, action).status_code, 403, (nom, action))
        self.assertEqual(FeuilleService.objects.get().statut, FeuilleService.STATUT_BROUILLON)

    def test_un_autre_redacteur_designe_peut_reprendre_le_brouillon(self):
        self._post("bsc_a", "creer")
        suppleant = self._m("suppleant_a", "EQUIPIER", "A")
        RedacteurFeuilleService.objects.create(ship=self.navire, equipage="A", user=suppleant)
        self.assertEqual(self._post("suppleant_a", "enregistrer_entete").status_code, 302)

    def test_retrait_de_la_designation_retire_le_droit(self):
        RedacteurFeuilleService.objects.filter(user=self.bsc_a).delete()
        self.assertEqual(self._post("bsc_a", "creer").status_code, 403)

    def test_rectificatif_reserve_aux_redacteurs(self):
        feuille = self._publiee()
        self.assertFalse(feuille.versions.exclude(pk=None).count() == 0)
        for nom in ("matelot_a", "cdt_a", "chef_service_a", "admin_unite"):
            self.assertEqual(self._post(nom, "ouvrir_rectificatif").status_code, 403, nom)


class LectureTests(RedactionBase):
    def test_tout_marin_du_batiment_lit_la_feuille_publiee_de_son_equipage(self):
        feuille = self._publiee()
        for nom in ("matelot_a", "bsc_a", "cdt_a", "chef_service_a"):
            self.client.force_login(User.objects.get(username=nom))
            reponse = self.client.get(self.url)
            self.assertEqual(reponse.status_code, 200, nom)
            self.assertEqual(reponse.context["feuille"], feuille, nom)
            self.assertFalse(reponse.context["peut_rediger"] and nom != "bsc_a", nom)

    def test_le_matelot_ne_voit_pas_le_bouton_de_creation(self):
        self.client.force_login(self.matelot_a)
        self.assertNotContains(self.client.get(self.url), "Créer le brouillon")
        self.client.force_login(self.bsc_a)
        self.assertContains(self.client.get(self.url), "Créer le brouillon")

    def test_la_feuille_de_l_autre_equipage_reste_invisible(self):
        self._publiee("B")
        self.client.force_login(self.matelot_a)
        self.assertIsNone(self.client.get(self.url).context["feuille"])
        feuille_b = FeuilleService.objects.get(equipage="B")
        self.assertFalse(peut_lire_feuille_service(self.matelot_a, feuille_b))

    def test_le_brouillon_reste_invisible_au_matelot(self):
        self._post("bsc_a", "creer")
        feuille = FeuilleService.objects.get()
        self.assertFalse(peut_lire_feuille_service(self.matelot_a, feuille))
        self.assertTrue(peut_lire_feuille_service(self.bsc_a, feuille))

    def test_acces_refuse_hors_du_batiment(self):
        etranger = User.objects.create_user(username="etranger", password="pass")
        UserProfile.objects.update_or_create(user=etranger, defaults={"role": "EQUIPIER", "ship": self.autre_navire})
        etranger = User.objects.get(pk=etranger.pk)
        self.assertFalse(peut_acceder_feuille_service(etranger, self.navire))
        self.client.force_login(etranger)
        self.assertEqual(self.client.get(self.url).status_code, 403)


class DesignationDesRedacteursTests(RedactionBase):
    def setUp(self):
        super().setUp()
        self.reglages = reverse("feuille-service-reglages")

    def _designer(self, nom, cible, ship=None):
        self.client.force_login(User.objects.get(username=nom))
        return self.client.post(self.reglages, {"action": "designer_redacteur", "ship": (ship or self.navire).pk, "user": cible.pk})

    def test_le_chef_de_service_designe_un_redacteur_de_son_equipage_avec_trace(self):
        self.assertEqual(self._designer("chef_service_a", self.matelot_a).status_code, 302)
        self.assertTrue(RedacteurFeuilleService.objects.filter(user=self.matelot_a, equipage="A").exists())
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_redacteur_designe", target_user=self.matelot_a).count(), 1)
        self.assertEqual(self._post("matelot_a", "creer").status_code, 302)

    def test_double_designation_sans_doublon_ni_nouvelle_trace(self):
        self._designer("chef_service_a", self.matelot_a)
        self._designer("chef_service_a", self.matelot_a)
        self.assertEqual(RedacteurFeuilleService.objects.filter(user=self.matelot_a).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="feuille_service_redacteur_designe").count(), 1)

    def test_un_matelot_ou_un_bsc_ne_designent_personne(self):
        for nom in ("matelot_a", "bsc_a"):
            self.assertEqual(self._designer(nom, self.matelot_a).status_code, 403, nom)
        self.assertEqual(RedacteurFeuilleService.objects.filter(user=self.matelot_a).count(), 0)

    def test_chaque_equipage_designe_les_siens(self):
        self.assertEqual(self._designer("chef_service_a", self.matelot_b).status_code, 403)
        self.navire.equipage_a_bord = "B"  # l'équipage à terre est en lecture seule : il désigne les siens quand il est à bord
        self.navire.save()
        self.assertEqual(self._designer("chef_service_b", self.matelot_b).status_code, 302)
        self.assertTrue(RedacteurFeuilleService.objects.filter(user=self.matelot_b, equipage="B").exists())

    def test_l_administrateur_n_herite_pas_du_droit_de_designer_sur_un_double_equipage(self):
        self.assertEqual(self._designer("maitre", self.matelot_a).status_code, 403)

    def test_cible_d_un_autre_batiment_introuvable(self):
        etranger = User.objects.create_user(username="etranger", password="pass")
        UserProfile.objects.update_or_create(user=etranger, defaults={"role": "EQUIPIER", "ship": self.autre_navire})
        self.assertEqual(self._designer("chef_service_a", User.objects.get(pk=etranger.pk)).status_code, 404)

    def test_retrait_avec_trace_et_cloisonnement_par_equipage(self):
        designation_b = RedacteurFeuilleService.objects.get(user=self.bsc_b)
        self.client.force_login(self.chef_service_a)
        refus = self.client.post(self.reglages, {"action": "retirer_redacteur", "ship": self.navire.pk, "pk": designation_b.pk})
        self.assertEqual(refus.status_code, 403)
        designation_a = RedacteurFeuilleService.objects.get(user=self.bsc_a)
        self.client.post(self.reglages, {"action": "retirer_redacteur", "ship": self.navire.pk, "pk": designation_a.pk})
        self.assertFalse(RedacteurFeuilleService.objects.filter(user=self.bsc_a).exists())
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_redacteur_retire", target_user=self.bsc_a).exists())

    def test_la_page_des_reglages_liste_les_redacteurs(self):
        self.client.force_login(self.chef_service_a)
        self.assertContains(self.client.get(f"{self.reglages}?ship={self.navire.pk}"), "Rédacteurs de la feuille")
