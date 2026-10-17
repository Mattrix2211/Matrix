"""Chaque équipage, en mer ou à terre, a SA feuille de service : droits stricts par équipage propriétaire."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from org.models import ReleveEquipage, Sector, Service, Ship
from quarts.models import FeuilleService, peut_viser_comaeq, peut_viser_secteur, peut_viser_service


class FeuilleParEquipageTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(
            name="FREMM Terre", code="FTE", classe_navire="FREMM", double_equipage=True, equipage_a_bord="A",
        )
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.secteur = Sector.objects.create(service=self.service, name="Courant")
        self.jour = timezone.localdate()
        self.url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.jour:%Y-%m-%d}"])
        for e in ("A", "B"):
            self._m(f"redacteur_{e}", "EQUIPIER", e, service=self.service, sector=self.secteur)
            self._m(f"chef_secteur_{e}", "CHEF_SECTEUR", e, service=self.service, sector=self.secteur)
            self._m(f"chef_service_{e}", "CHEF_SERVICE", e, service=self.service)
            self._m(f"comaeq_{e}", "ETAT_MAJOR", e, fonction_coma="COMAEQ")
            self._m(f"cdt_{e}", "COMMANDANT", e)
            self._m(f"second_{e}", "COMMANDANT_EN_SECOND", e)
        self.admin = self._m("admin_navire", "ADMIN_UNITE", "")
        self.maitre = self._m("maitre", "MASTER_ADMIN", "")

    def _m(self, nom, role, equipage, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "ship": self.ship, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def _post(self, nom, action, suffixe="", **donnees):
        self.client.force_login(User.objects.get(username=nom))
        return self.client.post(self.url + suffixe, {"action": action, **donnees})

    def _feuille(self, e):
        return FeuilleService.objects.get(ship=self.ship, equipage=e, date=self.jour)

    def _circuit(self, e, jusqu_a_comaeq=True):
        self.assertEqual(self._post(f"redacteur_{e}", "creer").status_code, 302)
        self._post(f"redacteur_{e}", "proposer")
        self._post(f"chef_secteur_{e}", "viser_secteur")
        self._post(f"chef_service_{e}", "viser_service")

    def test_chaque_equipage_mene_sa_feuille_jusqu_a_la_publication(self):
        for e in ("A", "B"):
            self._circuit(e)
            self.assertEqual(self._feuille(e).statut, FeuilleService.STATUT_VISA_COMAEQ, e)
        # Le COMAEQ de A ne vise que la feuille A, même avec ?equipage=B forgé.
        self.assertEqual(self._post("comaeq_A", "viser_comaeq", "?equipage=B").status_code, 302)
        self.assertEqual(self._feuille("A").statut, FeuilleService.STATUT_PUBLIEE)
        self.assertEqual(self._feuille("B").statut, FeuilleService.STATUT_VISA_COMAEQ)
        self._post("comaeq_B", "viser_comaeq")
        self.assertEqual(self._feuille("B").statut, FeuilleService.STATUT_PUBLIEE)
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_visa_comaeq_exceptionnel").exists())

    def test_comaeq_vacant_b_le_commandant_b_valide_avec_trace(self):
        self._circuit("B")
        UserProfile.objects.filter(user__username="comaeq_B").update(fonction_coma="")
        for refuse in ("redacteur_B", "second_B", "cdt_A", "comaeq_A", "admin_navire", "maitre"):
            self.assertIn(self._post(refuse, "viser_comaeq").status_code, (400, 403), refuse)
        self.assertEqual(self._feuille("B").statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertEqual(self._post("cdt_B", "viser_comaeq").status_code, 302)
        self.assertEqual(self._feuille("B").statut, FeuilleService.STATUT_PUBLIEE)
        self.assertTrue(AuditLog.objects.filter(
            action="feuille_service_visa_comaeq_exceptionnel", actor__username="cdt_B").exists())
        self.assertTrue(self._feuille("B").versions.get().contenu_fige["visa_exceptionnel"])

    def test_membres_de_l_autre_equipage_et_non_habilites_ne_visent_pas(self):
        self._circuit("B")
        feuille = self._feuille("B")
        for nom in ("redacteur_A", "comaeq_A", "cdt_A", "second_A", "second_B", "admin_navire", "maitre", "redacteur_B"):
            self.assertFalse(peut_viser_comaeq(User.objects.get(username=nom), feuille), nom)
        for nom in ("chef_secteur_A", "chef_service_A", "admin_navire", "maitre"):
            user = User.objects.get(username=nom)
            self.assertFalse(peut_viser_secteur(user, feuille) or peut_viser_service(user, feuille), nom)

    def test_administrateurs_ne_redigent_ni_ne_visent_par_le_seul_role(self):
        for nom in ("admin_navire", "maitre"):
            self.assertIn(self._post(nom, "creer", "?equipage=B").status_code, (400, 403), nom)
        self.assertFalse(FeuilleService.objects.exists())
        self._circuit("B")
        for nom in ("admin_navire", "maitre"):
            for action in ("viser_secteur", "viser_service", "viser_comaeq", "proposer", "enregistrer_entete"):
                self.assertIn(self._post(nom, action, "?equipage=B").status_code, (400, 403), f"{nom} {action}")
        self.assertEqual(self._feuille("B").statut, FeuilleService.STATUT_VISA_COMAEQ)
        # La lecture reste possible, avec choix de l'équipage affiché.
        self.client.force_login(self.maitre)
        self.assertEqual(self.client.get(self.url + "?equipage=B").status_code, 200)

    def test_requete_forgee_d_un_autre_equipage_n_atteint_pas_la_feuille(self):
        self._circuit("B")
        avant = self._feuille("B").statut
        self._post("chef_secteur_A", "renvoyer", "?equipage=B", motif="x", equipage="B")
        self._post("redacteur_A", "enregistrer_entete", "?equipage=B", equipage="B")
        feuille = self._feuille("B")
        self.assertEqual(feuille.statut, avant)
        self.assertFalse(FeuilleService.objects.filter(equipage="A").exclude(statut="BROUILLON").exists())

    def test_equipage_a_terre_hors_feuille_reste_en_lecture_seule(self):
        self.client.force_login(User.objects.get(username="redacteur_B"))
        for chemin in (
            reverse("feuille-service-reglages"), reverse("feuille-service-alertes"),
            "/taches/creer/", "/stock/",
        ):
            self.assertEqual(self.client.post(chemin, {"action": "x"}).status_code, 403, chemin)
        self.assertEqual(
            self.client.post(self.url, {"action": "rattacher_feuille", "feuille_id": 1}).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"action": "inconnue"}).status_code, 403)

    def test_la_releve_ne_modifie_ni_feuilles_ni_visas_historiques(self):
        self._circuit("A")
        self._post("comaeq_A", "viser_comaeq")
        self._circuit("B")

        def etat():
            return [
                (f.equipage, f.statut, f.visa_secteur_par_id, f.visa_service_par_id, f.visa_comaeq_par_id,
                 [v.numero for v in f.versions.all()])
                for f in FeuilleService.objects.order_by("equipage")
            ]
        avant = etat()
        self.ship.equipage_a_bord = "B"
        self.ship.save()
        ReleveEquipage.objects.filter(ship=self.ship).delete()
        self.assertEqual(avant, etat())
        # Après la relève, la feuille B en cours se vise par son COMAEQ, celle de A reste publiée.
        self._post("comaeq_B", "viser_comaeq")
        self.assertEqual(self._feuille("A").statut, FeuilleService.STATUT_PUBLIEE)
        self.assertEqual(self._feuille("B").statut, FeuilleService.STATUT_PUBLIEE)
