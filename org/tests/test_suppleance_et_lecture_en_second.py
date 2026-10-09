"""Commandant en second : lecture transverse (annuaire, listes de service, feuille
de service, formations) sans aucune écriture, suppléance explicite et tracée du
commandant, cadre de droits métier vide par défaut."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from matrix.core import role_thresholds
from matrix.core.roles import RoleLevel, user_role_level
from notifications.models import Notification
from org.commandant_en_second import droit_metier_en_second, niveau_lecture
from org.models import CommandantEnSecond, Equipage, RoleThresholdConfig, Service, Ship, SuppleanceCommandant
from org.suppleance import suppleance_en_cours, traiter_suppleances_echues
from quarts.models import FeuilleService, ServiceGarde
from quarts.web_views import _peut_lire_liste
from quarts.models import peut_lire_feuille_service
from training.models import TrainingCourse


def _marin(username, role, ship, equipage=None):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.ship = Ship.objects.create(name="BRF Lecture", code="BRF-L")
        self.autre = Ship.objects.create(name="Autre Lecture", code="AUT-L")
        self.commandant = _marin("cdt", "COMMANDANT", self.ship)
        self.second = _marin("second", "ETAT_MAJOR", self.ship)
        self.poste = CommandantEnSecond.objects.create(ship=self.ship, titulaire=self.second)
        self.matelot = _marin("matelot", "EQUIPIER", self.ship)
        self.etranger = _marin("etranger", "EQUIPIER", self.autre)
        self.fonction = ServiceFunctionChoice.objects.create(name="Permanence")

    def suppleance(self, debut=None, fin=None, **extra):
        maintenant = timezone.now()
        return SuppleanceCommandant.objects.create(
            ship=self.ship, suppleant=self.second, designe_par=self.commandant,
            debut=debut or maintenant - timedelta(hours=1), fin=fin or maintenant + timedelta(hours=5), **extra,
        )


class LectureAnnuaireTests(Base):
    def test_annuaire_web_en_lecture_seule_borne_au_navire(self):
        self.client.force_login(self.second)
        reponse = self.client.get(reverse("user-directory"))
        self.assertEqual(reponse.status_code, 200)
        logins = {u.username for u in reponse.context["users"]}
        self.assertIn("matelot", logins)
        self.assertNotIn("etranger", logins)
        self.assertTrue(reponse.context["lecture_seule"])
        self.assertNotContains(reponse, "data-bs-target=\"#createUserModal\"")

    def test_annuaire_web_ecriture_refusee(self):
        self.client.force_login(self.second)
        reponse = self.client.post(
            reverse("user-directory"), {"action": "bulk_delete_users", "selected_ids": [self.matelot.pk]}
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.matelot.pk).exists())

    def test_annuaire_web_sans_poste_reste_interdit(self):
        self.poste.delete()
        self.client.force_login(self.second)
        self.assertEqual(self.client.get(reverse("user-directory")).status_code, 403)

    def test_le_commandant_n_est_pas_en_lecture_seule(self):
        self.client.force_login(self.commandant)
        self.assertFalse(self.client.get(reverse("user-directory")).context["lecture_seule"])

    def test_api_profils_lecture_seule_et_bornee(self):
        api = APIClient()
        api.force_authenticate(self.second)
        donnees = api.get("/api/accounts/profiles/").json()
        donnees = donnees["results"] if isinstance(donnees, dict) else donnees
        noms = {p["user"] if isinstance(p["user"], str) else p.get("username") for p in donnees}
        self.assertEqual(len(donnees), 3)  # commandant, second, matelot : pas l'autre navire
        self.assertEqual(api.patch(f"/api/accounts/profiles/{self.matelot.profile.pk}/", {"grade": "X"}).status_code, 403)
        self.assertTrue(noms)


class LectureFormationTests(Base):
    def test_formation_en_attente_visible(self):
        cours = TrainingCourse.objects.create(title="SST", statut_validation="WAITING_VALIDATION", updated_by=self.matelot)
        api = APIClient()
        api.force_authenticate(self.second)
        donnees = api.get("/api/training/courses/").json()
        donnees = donnees["results"] if isinstance(donnees, dict) else donnees
        self.assertIn(cours.pk, {c["id"] for c in donnees})
        self.assertEqual(niveau_lecture(self.second), RoleLevel.COMMANDANT)
        self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)


class LectureListesEtFeuilleTests(Base):
    def _garde(self, ship=None, statut=ServiceGarde.STATUT_BROUILLON):
        return ServiceGarde.objects.create(
            fonction=self.fonction, date_debut=timezone.localdate(),
            date_fin=timezone.localdate() + timedelta(days=5), statut=statut,
            created_by=self.commandant, ship=ship or self.ship,
        )

    def test_liste_brouillon_du_navire_lisible_pas_gerable(self):
        from quarts.models import peut_gerer_liste
        liste = self._garde()
        self.assertTrue(_peut_lire_liste(self.second, liste))
        self.assertFalse(peut_gerer_liste(self.second, liste))

    def test_liste_d_un_autre_navire_illisible(self):
        self.assertFalse(_peut_lire_liste(self.second, self._garde(ship=self.autre)))

    def test_tableau_de_bord_des_listes_montre_les_listes_du_navire(self):
        liste = self._garde()
        self.client.force_login(self.second)
        reponse = self.client.get(reverse("quarts-index"))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(liste, list(reponse.context["services_garde"]))
        self.assertFalse(reponse.context["peut_creer"])

    def test_feuille_en_cours_de_visa_lisible_en_lecture(self):
        feuille = FeuilleService.objects.create(
            ship=self.ship, date=timezone.localdate(), created_by=self.matelot, updated_by=self.matelot,
        )
        # Le second n'est pas titulaire du COMAEQ : seul son poste ouvre la lecture.
        self.assertTrue(peut_lire_feuille_service(self.second, feuille))
        self.poste.delete()
        self.assertFalse(peut_lire_feuille_service(self.second, feuille))


class DoubleEquipageLectureTests(TestCase):
    def test_lecture_limitee_a_son_equipage(self):
        ship = Ship.objects.create(name="FREMM L", code="FR-L", double_equipage=True)
        bleu = Equipage.objects.create(ship=ship, nom="Bleu")
        rouge = Equipage.objects.create(ship=ship, nom="Rouge")
        second = _marin("second_b", "ETAT_MAJOR", ship, bleu)
        CommandantEnSecond.objects.create(ship=ship, equipage=bleu, titulaire=second)
        garde_kwargs = dict(
            fonction=ServiceFunctionChoice.objects.create(name="Perm"), date_debut=timezone.localdate(),
            date_fin=timezone.localdate() + timedelta(days=2),
        )
        cdt_bleu = _marin("cdt_bleu", "COMMANDANT", ship, bleu)
        cdt_rouge = _marin("cdt_rouge", "COMMANDANT", ship, rouge)
        liste_bleue = ServiceGarde.objects.create(ship=ship, created_by=cdt_bleu, **garde_kwargs)
        liste_rouge = ServiceGarde.objects.create(ship=ship, created_by=cdt_rouge, **garde_kwargs)
        self.assertTrue(_peut_lire_liste(second, liste_bleue))
        self.assertFalse(_peut_lire_liste(second, liste_rouge))


class SuppleanceTests(Base):
    def test_sans_suppleance_aucun_droit_du_commandant(self):
        self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)

    def test_suppleance_active_donne_le_niveau_commandant(self):
        self.suppleance()
        self.assertEqual(user_role_level(self.second), RoleLevel.COMMANDANT)
        self.assertIsNotNone(suppleance_en_cours(self.second))

    def test_suppleance_expiree_programmee_ou_annulee_ne_donne_rien(self):
        maintenant = timezone.now()
        self.suppleance(debut=maintenant - timedelta(days=2), fin=maintenant - timedelta(days=1))
        self.suppleance(debut=maintenant + timedelta(days=1), fin=maintenant + timedelta(days=2))
        self.suppleance(annulee_le=maintenant)
        self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)

    def test_suppleance_sans_poste_ou_sur_un_autre_navire_ne_donne_rien(self):
        suppleance = self.suppleance()
        suppleance.ship = self.autre
        suppleance.save()
        self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)
        suppleance.ship = self.ship
        suppleance.save()
        self.poste.delete()
        self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)

    def test_pendant_la_suppleance_l_ecriture_du_commandant_est_ouverte(self):
        self.client.force_login(self.second)
        donnees = {"action": "set_commandant_en_second", "libelle": "OFFICIER_EN_SECOND"}
        self.assertEqual(self.client.post(reverse("settings"), donnees).status_code, 403)
        self.suppleance()
        self.assertEqual(self.client.post(reverse("settings"), donnees).status_code, 302)
        self.poste.refresh_from_db()
        self.assertEqual(self.poste.libelle, "OFFICIER_EN_SECOND")

    def test_fin_automatique_a_l_echeance(self):
        suppleance = self.suppleance(fin=timezone.now() + timedelta(hours=1))
        self.assertEqual(user_role_level(self.second), RoleLevel.COMMANDANT)
        with mock.patch("org.suppleance.timezone.now", return_value=suppleance.fin + timedelta(minutes=1)):
            self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)

    def test_debut_et_fin_traces_et_notifies_une_seule_fois(self):
        suppleance = self.suppleance(fin=timezone.now() + timedelta(hours=1))
        self.assertEqual(traiter_suppleances_echues(), 1)
        self.assertEqual(traiter_suppleances_echues(), 0)
        self.assertTrue(AuditLog.objects.filter(action="debut_suppleance_commandant", target_user=self.second).exists())
        SuppleanceCommandant.objects.filter(pk=suppleance.pk).update(fin=timezone.now() - timedelta(minutes=1))
        self.assertEqual(traiter_suppleances_echues(), 1)
        self.assertTrue(AuditLog.objects.filter(action="fin_suppleance_commandant", target_user=self.second).exists())
        self.assertEqual(Notification.objects.filter(user=self.second).count(), 2)

    def test_suppleance_echue_traitee_une_seule_fois_meme_appelee_deux_fois(self):
        maintenant = timezone.now()
        self.suppleance(debut=maintenant - timedelta(days=2), fin=maintenant - timedelta(days=1))
        self.assertEqual(traiter_suppleances_echues(), 2)
        self.assertEqual(traiter_suppleances_echues(), 0)
        self.assertEqual(AuditLog.objects.filter(action="debut_suppleance_commandant").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="fin_suppleance_commandant").count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.second).count(), 2)

    def test_course_entre_deux_traitements_ne_cree_aucun_doublon(self):
        maintenant = timezone.now()
        suppleance = self.suppleance(debut=maintenant - timedelta(days=2), fin=maintenant - timedelta(days=1))
        vrai_atomic = transaction.atomic

        def concurrent(*args, **kwargs):
            # Un autre processus traite les mêmes événements avant nous.
            SuppleanceCommandant.objects.filter(pk=suppleance.pk).update(debut_trace=True, fin_tracee=True)
            return vrai_atomic(*args, **kwargs)

        with mock.patch("org.suppleance.transaction.atomic", side_effect=concurrent):
            self.assertEqual(traiter_suppleances_echues(), 0)
        self.assertFalse(AuditLog.objects.filter(action__endswith="_suppleance_commandant").exists())
        self.assertFalse(Notification.objects.filter(user=self.second).exists())

    def test_affichage_de_l_onglet_n_ecrit_rien(self):
        maintenant = timezone.now()
        self.suppleance(debut=maintenant - timedelta(days=2), fin=maintenant - timedelta(days=1))
        self.client.force_login(self.commandant)
        avant = (AuditLog.objects.count(), Notification.objects.count())
        reponse = self.client.get(reverse("settings"), {"tab": "commandants_adjoints"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual((AuditLog.objects.count(), Notification.objects.count()), avant)
        self.assertFalse(SuppleanceCommandant.objects.filter(debut_trace=True).exists())
        self.assertContains(reponse, "Terminée")

    def test_cout_de_user_role_level_borne_pour_l_etat_major(self):
        user_role_level(self.second)  # charge le profil une fois
        with CaptureQueriesContext(connection) as une_fois:
            user_role_level(self.second)
        self.assertLessEqual(len(une_fois), 2)
        with self.assertNumQueries(len(une_fois) * 5):
            for _ in range(5):
                user_role_level(self.second)

    def _designer(self, acteur, **extra):
        self.client.force_login(acteur)
        maintenant = timezone.localtime()
        donnees = {
            "action": "designer_suppleance", "poste_id": self.poste.pk, "motif": "Permission",
            "debut": (maintenant - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "fin": (maintenant + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
        }
        donnees.update(extra)
        return self.client.post(reverse("settings"), donnees, follow=True)

    def test_le_commandant_designe_avec_audit_et_notification(self):
        self._designer(self.commandant)
        suppleance = SuppleanceCommandant.objects.get()
        self.assertEqual((suppleance.suppleant, suppleance.ship, suppleance.designe_par), (self.second, self.ship, self.commandant))
        self.assertTrue(AuditLog.objects.filter(action="designation_suppleance_commandant", actor=self.commandant).exists())
        self.assertTrue(AuditLog.objects.filter(action="debut_suppleance_commandant").exists())
        self.assertTrue(Notification.objects.filter(user=self.second).exists())

    def test_le_suppleant_ne_peut_pas_se_designer_ni_annuler(self):
        self.suppleance()
        self._designer(self.second)
        self.assertEqual(SuppleanceCommandant.objects.count(), 1)
        self.client.post(
            reverse("settings"), {"action": "annuler_suppleance", "suppleance_id": SuppleanceCommandant.objects.get().pk}
        )
        self.assertIsNone(SuppleanceCommandant.objects.get().annulee_le)

    def test_un_chef_de_service_ne_peut_pas_designer(self):
        self._designer(_marin("chef", "CHEF_SERVICE", self.ship))
        self.assertFalse(SuppleanceCommandant.objects.exists())

    def test_periode_incoherente_refusee(self):
        maintenant = timezone.localtime()
        self._designer(
            self.commandant, debut=(maintenant + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            fin=(maintenant + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
        )
        self.assertFalse(SuppleanceCommandant.objects.exists())

    def test_annulation_par_le_commandant_coupe_les_droits_et_trace(self):
        suppleance = self.suppleance()
        self.client.force_login(self.commandant)
        self.client.post(reverse("settings"), {"action": "annuler_suppleance", "suppleance_id": suppleance.pk})
        suppleance.refresh_from_db()
        self.assertEqual((suppleance.annulee_par, suppleance.statut), (self.commandant, "Annulée"))
        self.assertEqual(user_role_level(self.second), RoleLevel.ETAT_MAJOR)
        self.assertTrue(AuditLog.objects.filter(action="annulation_suppleance_commandant").exists())

    def test_l_administrateur_d_un_autre_navire_ne_touche_pas_ma_suppleance(self):
        suppleance = self.suppleance()
        self.client.force_login(_marin("adm_autre", "ADMIN_NAVIRE", self.autre))
        self.client.post(reverse("settings"), {"action": "annuler_suppleance", "suppleance_id": suppleance.pk})
        suppleance.refresh_from_db()
        self.assertIsNone(suppleance.annulee_le)

    def test_double_equipage_suppleance_de_l_equipage_du_poste(self):
        ship = Ship.objects.create(name="FREMM S2", code="FR-S2", double_equipage=True)
        bleu = Equipage.objects.create(ship=ship, nom="Bleu")
        rouge = Equipage.objects.create(ship=ship, nom="Rouge")
        second = _marin("second_bleu2", "ETAT_MAJOR", ship, bleu)
        CommandantEnSecond.objects.create(ship=ship, equipage=bleu, titulaire=second)
        maintenant = timezone.now()
        SuppleanceCommandant.objects.create(
            ship=ship, equipage=rouge, suppleant=second, debut=maintenant - timedelta(hours=1),
            fin=maintenant + timedelta(hours=1),
        )
        self.assertEqual(user_role_level(second), RoleLevel.ETAT_MAJOR)
        SuppleanceCommandant.objects.update(equipage=bleu)
        self.assertEqual(user_role_level(second), RoleLevel.COMMANDANT)


class DroitsMetierEnSecondTests(Base):
    def test_aucun_droit_ouvert_par_defaut(self):
        self.assertFalse(droit_metier_en_second(self.second, "alerte_securite"))
        self.assertFalse(droit_metier_en_second(self.second, "alerte_organisation_validation"))

    def test_droit_configure_par_navire_pour_le_seul_titulaire(self):
        droit = role_thresholds.DroitEnSecond("alerte_securite", "Déclencher une alerte sécurité", "Sécurité")
        RoleThresholdConfig.objects.create(ship=self.ship, droits_en_second=["alerte_securite"])
        with mock.patch.dict(role_thresholds.REGISTRE_DROITS_EN_SECOND_PAR_CLE, {droit.cle: droit}):
            self.assertTrue(droit_metier_en_second(self.second, "alerte_securite"))
            self.assertFalse(droit_metier_en_second(self.second, "autre_action"))
            self.assertFalse(droit_metier_en_second(self.matelot, "alerte_securite"))
            self.assertFalse(droit_metier_en_second(self.etranger, "alerte_securite"))


class SuppleanceEquipageATerreTests(TestCase):
    def test_suppleance_sur_un_poste_de_l_equipage_a_terre_ne_donne_aucune_ecriture(self):
        from org.equipages import est_en_lecture_seule

        ship = Ship.objects.create(name="FREMM T", code="FR-T", classe_navire="FREMM", double_equipage=True)
        bleu = Equipage.objects.create(ship=ship, nom="Bleu")
        rouge = Equipage.objects.create(ship=ship, nom="Rouge")
        ship.equipage_a_bord = bleu
        ship.save()
        second_terre = _marin("second_terre", "ETAT_MAJOR", ship, rouge)
        poste = CommandantEnSecond.objects.create(ship=ship, equipage=rouge, titulaire=second_terre)
        maintenant = timezone.now()
        SuppleanceCommandant.objects.create(
            ship=ship, equipage=rouge, suppleant=second_terre, debut=maintenant - timedelta(hours=1),
            fin=maintenant + timedelta(hours=1),
        )
        # Le niveau de suppléance est bien actif, mais le marin reste à terre : lecture seule.
        self.assertEqual(user_role_level(second_terre), RoleLevel.COMMANDANT)
        self.assertTrue(est_en_lecture_seule(second_terre))
        self.client.force_login(second_terre)
        reponse = self.client.post(
            reverse("settings"), {"action": "set_commandant_en_second", "libelle": "OFFICIER_EN_SECOND"}
        )
        self.assertEqual(reponse.status_code, 302)  # écriture bloquée par le middleware, avec message
        poste.refresh_from_db()
        self.assertNotEqual(poste.libelle, "OFFICIER_EN_SECOND")
        reponse = self.client.post(
            reverse("settings"), {"action": "set_commandant_en_second", "libelle": "OFFICIER_EN_SECOND"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(reponse.status_code, 403)
        poste.refresh_from_db()
        self.assertNotEqual(poste.libelle, "OFFICIER_EN_SECOND")
