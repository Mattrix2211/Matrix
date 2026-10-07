"""Double équipage : relève par le commandant, lecture seule centrale, équipage obligatoire."""
import base64
import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.forms import UserProfileForm
from accounts.models import AuditLog, UserProfile
from org.models import Ship


class DoubleEquipageBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM", code="FR-DE", double_equipage=True, equipage_a_bord="A")
        self.cdt = self._marin("cdt", "COMMANDANT", "A")
        self.cdt_b = self._marin("cdtb", "COMMANDANT", "B")
        self.admin = self._marin("adm", "ADMIN_NAVIRE", "B")
        self.chef_terre = self._marin("chef", "CHEF_SERVICE", "B")
        self.bord = self._marin("bord", "EQUIPIER", "A")

    def _marin(self, nom, role, equipage):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage},
        )
        return user


class RelevePersonnelTests(DoubleEquipageBase):
    def _agir(self, nom, action, **donnees):
        self.client.login(username=nom, password="pass")
        return self.client.post(reverse("settings"), {"action": action, **donnees})

    def _a_bord(self):
        self.navire.refresh_from_db()
        return self.navire.equipage_a_bord

    def test_proposition_seule_ne_change_rien_et_notifie_l_autre_commandant(self):
        self._agir("cdt", "proposer_releve", equipage="B")
        self.assertEqual(self._a_bord(), "A")
        self.assertTrue(self.cdt_b.notifications.exists())
        self.assertTrue(AuditLog.objects.filter(action="releve_proposee", actor=self.cdt).exists())

    def test_le_deuxieme_commandant_valide_et_les_deux_validations_sont_tracees(self):
        self._agir("cdt", "proposer_releve", equipage="B")
        self._agir("cdtb", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "B")
        trace = AuditLog.objects.get(action="releve_validee")
        self.assertIn("propose_par=cdt", trace.details)
        self.assertIn("decide_par=cdtb", trace.details)
        self.assertTrue(AuditLog.objects.filter(action="changement_equipage", actor=self.cdt_b).exists())

    def test_refus_ne_change_rien(self):
        self._agir("cdt", "proposer_releve", equipage="B")
        self._agir("cdtb", "decider_releve", decision="refuser")
        self.assertEqual(self._a_bord(), "A")

    def test_auto_validation_refusee(self):
        self._agir("cdt", "proposer_releve", equipage="B")
        self._agir("cdt", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "A")

    def test_commandant_en_second_supplee_le_commandant_absent(self):
        # Le commandant de l'équipage B est remplacé par son second.
        UserProfile.objects.filter(user=self.cdt_b).update(role="COMMANDANT_EN_SECOND")
        self._agir("cdt", "proposer_releve", equipage="B")
        self.assertTrue(self.cdt_b.notifications.exists())
        self._agir("cdtb", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "B")

    def test_commandant_en_second_propose_et_le_commandant_valide(self):
        second = self._marin("second", "COMMANDANT_EN_SECOND", "A")
        self._agir("second", "proposer_releve", equipage="B")
        self.assertEqual(self.navire.releves.count(), 1)
        self._agir("second", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "A")
        self._agir("cdtb", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "B")
        self.assertTrue(second.notifications.exists())

    def test_commandant_et_son_second_de_meme_equipage_ne_se_valident_pas(self):
        self._marin("second", "COMMANDANT_EN_SECOND", "A")
        self._agir("cdt", "proposer_releve", equipage="B")
        self._agir("second", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "A")

    def test_equipage_sans_commandant_ni_second_refuse(self):
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self._marin("second_a", "COMMANDANT_EN_SECOND", "A")
        self._agir("second_a", "proposer_releve", equipage="B")
        self.assertFalse(self.navire.releves.exists())

    def test_equipage_sans_commandant_refuse(self):
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self._agir("cdt", "proposer_releve", equipage="B")
        self.assertFalse(self.navire.releves.exists())

    def test_non_commandant_refuse(self):
        for nom in ("adm", "chef", "bord"):
            self._agir(nom, "proposer_releve", equipage="B")
        self.assertFalse(self.navire.releves.exists())
        self._agir("cdt", "proposer_releve", equipage="B")
        self._agir("adm", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "A")

    def test_une_seule_proposition_annulable_par_son_auteur(self):
        self._agir("cdt", "proposer_releve", equipage="B")
        self._agir("cdtb", "proposer_releve", equipage="A")
        self.assertEqual(self.navire.releves.count(), 1)
        self._agir("cdtb", "annuler_releve")
        self.assertEqual(self.navire.releves.get().statut, "en_attente")
        self._agir("cdt", "annuler_releve")
        self.assertEqual(self.navire.releves.get().statut, "annulee")

    def test_master_admin_ne_contourne_pas(self):
        User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self._agir("root", "proposer_releve", equipage="B", ship_id=self.navire.pk)
        self.assertFalse(self.navire.releves.exists())

    def _secours(self, motif="Commandant B évacué", nom="root"):
        self.client.login(username=nom, password="pass")
        return self.client.post(reverse("settings"), {
            "action": "valider_releve_secours", "ship_id": self.navire.pk, "motif": motif,
        })

    def _proposition_sans_commandant_b(self):
        User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self._agir("cdt", "proposer_releve", equipage="B")
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")

    def test_secours_valide_sans_commandant_ni_second_avec_trace(self):
        self._proposition_sans_commandant_b()
        self._secours()
        self.assertEqual(self._a_bord(), "B")
        trace = AuditLog.objects.get(action="releve_validee_secours")
        self.assertIn("motif=Commandant B évacué", trace.details)
        self.assertIn("decide_par=root", trace.details)
        self.assertTrue(self.cdt.notifications.filter(verb__contains="secours").exists())
        self.assertTrue(self.bord.notifications.filter(verb__contains="secours").exists())

    def test_secours_motif_vide_refuse(self):
        self._proposition_sans_commandant_b()
        self._secours(motif="   ")
        self.assertEqual(self._a_bord(), "A")
        self.assertFalse(AuditLog.objects.filter(action="releve_validee_secours").exists())

    def test_secours_refuse_si_un_commandant_ou_un_second_existe(self):
        User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self._agir("cdt", "proposer_releve", equipage="B")
        self._secours()
        self.assertEqual(self._a_bord(), "A")
        UserProfile.objects.filter(user=self.cdt_b).update(role="COMMANDANT_EN_SECOND")
        self._secours()
        self.assertEqual(self._a_bord(), "A")

    def test_secours_refuse_aux_non_administrateurs_generaux(self):
        self._proposition_sans_commandant_b()
        for nom in ("adm", "cdt", "chef"):
            self._secours(nom=nom)
        self.assertEqual(self._a_bord(), "A")

    def test_administrateur_general_ne_propose_pas_meme_en_secours(self):
        User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self._agir("root", "proposer_releve", equipage="B", ship_id=self.navire.pk)
        self.assertFalse(self.navire.releves.exists())

    def test_secours_refuse_sans_proposition(self):
        User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self._secours()
        self.assertEqual(self._a_bord(), "A")

    def test_secours_auto_validation_commandant_refusee(self):
        self._proposition_sans_commandant_b()
        self._agir("cdt", "decider_releve", decision="valider")
        self.assertEqual(self._a_bord(), "A")

    def test_bouton_secours_affiche_seulement_dans_le_cas_de_secours(self):
        self._proposition_sans_commandant_b()
        self.client.login(username="root", password="pass")
        url = f"{reverse('settings')}?tab=equipage&ship={self.navire.pk}"
        self.assertContains(self.client.get(url), "Valider en secours")
        UserProfile.objects.filter(user=self.cdt_b).update(role="COMMANDANT")
        self.assertNotContains(self.client.get(url), "Valider en secours")
        self.client.login(username="cdt", password="pass")
        self.assertNotContains(self.client.get(reverse("settings"), {"tab": "equipage"}), "Valider en secours")

    def test_secours_refuse_au_proposant_superuser_commandant(self):
        root = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        UserProfile.objects.update_or_create(
            user=root, defaults={"role": "COMMANDANT", "ship": self.navire, "equipage": "A"})
        self._agir("root", "proposer_releve", equipage="B", ship_id=self.navire.pk)
        self.assertTrue(self.navire.releves.exists())
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self._secours()
        self.assertEqual(self._a_bord(), "A")

    def test_commandant_inactif_ne_bloque_pas_le_secours(self):
        self._proposition_sans_commandant_b()
        UserProfile.objects.filter(user=self.cdt_b).update(role="COMMANDANT")
        self._secours()
        self.assertEqual(self._a_bord(), "A")
        User.objects.filter(pk=self.cdt_b.pk).update(is_active=False)
        self._secours()
        self.assertEqual(self._a_bord(), "B")

    def test_commandant_inactif_ne_compte_pas_pour_proposer(self):
        User.objects.filter(pk=self.cdt_b.pk).update(is_active=False)
        self._agir("cdt", "proposer_releve", equipage="B")
        self.assertFalse(self.navire.releves.exists())

    def test_double_decision_sur_releve_deja_decidee_sans_doublon(self):
        from matrix.core.equipage import decider_releve, valider_releve_secours
        self._agir("cdt", "proposer_releve", equipage="B")
        perimee = self.navire.releves.get()
        cdt_b = User.objects.get(pk=self.cdt_b.pk)
        self.assertEqual(decider_releve(cdt_b, perimee, True), "")
        self.assertNotEqual(decider_releve(cdt_b, perimee, True), "")
        root = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self.assertNotEqual(valider_releve_secours(root, perimee, "motif"), "")
        self.assertEqual(AuditLog.objects.filter(action__startswith="releve_validee").count(), 1)
        self.assertEqual(self.cdt.notifications.count(), 1)

    def test_secours_refuse_si_proposant_hors_des_deux_equipages(self):
        self._proposition_sans_commandant_b()
        UserProfile.objects.filter(user=self.cdt).update(equipage="C")
        self._secours()
        self.assertEqual(self._a_bord(), "A")

    def _master_role(self):
        master = User.objects.create_user(username="master", password="pass")
        UserProfile.objects.update_or_create(user=master, defaults={"role": "MASTER_ADMIN"})
        return master

    def test_master_admin_de_role_voit_l_onglet_et_choisit_un_navire(self):
        self._master_role()
        Ship.objects.create(name="Zulu-Vedette", code="ZV")
        self.client.login(username="master", password="pass")
        r = self.client.get(reverse("settings"), {"tab": "equipage", "ship": self.navire.pk})
        self.assertContains(r, "Relève — FREMM")
        self.assertNotContains(r, ">Zulu-Vedette</option>")

    def test_master_admin_de_role_valide_en_secours_dans_le_cas_autorise_seulement(self):
        self._master_role()
        self._agir("cdt", "proposer_releve", equipage="B")
        self._secours(nom="master")
        self.assertEqual(self._a_bord(), "A")
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self.client.login(username="master", password="pass")
        self.assertContains(
            self.client.get(reverse("settings"), {"tab": "equipage", "ship": self.navire.pk}), "Valider en secours")
        self._secours(nom="master")
        self.assertEqual(self._a_bord(), "B")

    def test_master_admin_de_role_ne_propose_pas(self):
        self._master_role()
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        self._agir("master", "proposer_releve", equipage="B", ship_id=self.navire.pk)
        self.assertFalse(self.navire.releves.exists())

    def test_le_commandant_d_un_autre_navire_ne_peut_pas(self):
        autre = Ship.objects.create(name="Autre", code="AU", double_equipage=True, equipage_a_bord="A")
        self.cdt.profile.ship = autre
        self.cdt.profile.save()
        self._agir("cdt", "proposer_releve", equipage="B", ship_id=self.navire.pk)
        self.assertFalse(self.navire.releves.exists())

    def test_onglet_visible_commandant_et_admin_seulement(self):
        self.client.login(username="adm", password="pass")
        r = self.client.get(reverse("settings"), {"tab": "equipage"})
        self.assertContains(r, "proposée et validée par les commandants")
        self.assertNotContains(r, "Proposer la relève")
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("settings"), {"tab": "equipage"}), "Proposer la relève")
        self.client.login(username="bord", password="pass")
        self.assertEqual(self.client.get(reverse("settings"), {"tab": "equipage"}).status_code, 403)

    def test_alerte_marins_sans_equipage(self):
        self._marin("sans", "EQUIPIER", "")
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("settings"), {"tab": "equipage"}), "1 marin sans équipage")

    def test_api_ne_change_pas_l_equipage_a_bord(self):
        url = reverse("ship-detail", args=[self.navire.pk])
        for nom in ("adm", "cdt"):
            self.client.login(username=nom, password="pass")
            self.assertEqual(self.client.patch(url, {"equipage_a_bord": "B"}, content_type="application/json").status_code, 403)

    def test_admin_django_trace_le_changement(self):
        root = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self.client.login(username="root", password="pass")
        donnees = {"name": "FREMM", "code": "FR-DE", "type_unite": self.navire.type_unite, "classe_navire": "",
                   "double_equipage": "on", "equipage_a_bord": "B"}
        self.client.post(reverse("admin:org_ship_change", args=[self.navire.pk]), donnees)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "B")
        self.assertTrue(AuditLog.objects.filter(action="changement_equipage", actor=root).exists())


class LectureSeuleCentraleTests(DoubleEquipageBase):
    # Écritures du bâtiment prises dans chaque module : le garde agit avant la vue.
    ECRITURES_WEB = (
        ("ticket-transition", [uuid.uuid4()]),
        ("ticket-assign", [uuid.uuid4()]),
        ("ticket-comment-create", [uuid.uuid4()]),
        ("part-request-create", [uuid.uuid4()]),
        ("anomalie-create", []),
        ("anomalie-transition", [1]),
        ("ronde-lancer", [1]),
        ("ronde-terminer", [1]),
        ("echange-proposer", [1]),
        ("quarts-reglages", []),
        ("formation-valider", []),
        ("formation-list", []),
        ("asset-list", []),
        ("asset-import", []),
        ("pret-appareillage", []),
        ("calendar-event-move", []),
    )

    def test_equipage_a_terre_refuse_toutes_les_ecritures_web(self):
        for nom in ("chef", "adm"):
            self.client.login(username=nom, password="pass")
            for vue, args in self.ECRITURES_WEB:
                with self.subTest(nom=nom, vue=vue):
                    self.assertEqual(self.client.post(reverse(vue, args=args), {}).status_code, 403)

    def test_equipage_a_bord_non_bloque(self):
        self.client.login(username="cdt", password="pass")
        for vue, args in self.ECRITURES_WEB:
            with self.subTest(vue=vue):
                reponse = self.client.post(reverse(vue, args=args), {})
                self.assertNotIn(b"Lecture seule : votre", reponse.content)

    def test_equipage_a_terre_refuse_les_ecritures_api(self):
        self.client.login(username="chef", password="pass")
        for url in ("/api/logistics/tickets/", "/api/maintenance/occurrences/", "/api/threads/messages/", "/api/assets/assets/"):
            with self.subTest(url=url):
                r = self.client.post(url, {}, content_type="application/json")
                self.assertEqual(r.status_code, 403)
                self.assertIn("Lecture seule", r.json()["detail"])

    def test_authentification_basic_ne_contourne_pas_le_garde(self):
        jeton = base64.b64encode(b"chef:pass").decode()
        r = self.client.post("/api/logistics/tickets/", {}, content_type="application/json", HTTP_AUTHORIZATION=f"Basic {jeton}")
        self.assertEqual(r.status_code, 403)
        self.assertIn("Lecture seule", r.json()["detail"])

    def test_lecture_et_reglages_restent_possibles_a_terre(self):
        self.client.login(username="adm", password="pass")
        self.assertEqual(self.client.get("/api/logistics/tickets/").status_code, 200)
        r = self.client.post(reverse("settings"), {"action": "update_notification_time", "notification_time": "07:00", "notification_time_soir": "19:00"})
        self.assertEqual(r.status_code, 302)

    def test_bandeau_sur_toutes_les_pages_a_terre_seulement(self):
        self.client.login(username="chef", password="pass")
        for vue in ("ticket-list", "asset-list", "rondes-index", "formation-list"):
            with self.subTest(vue=vue):
                self.assertContains(self.client.get(reverse(vue)), "Lecture seule — Équipage B à terre")
        self.client.login(username="bord", password="pass")
        self.assertNotContains(self.client.get(reverse("ticket-list")), "Lecture seule")


class EquipageObligatoireTests(DoubleEquipageBase):
    def test_formulaire_exige_l_equipage_sur_double_equipage(self):
        form = UserProfileForm({"role": "EQUIPIER", "ship": self.navire.pk, "equipage": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("equipage", form.errors)

    def test_formulaire_sans_double_equipage_non_concerne(self):
        simple = Ship.objects.create(name="Zulu-Vedette", code="ZV")
        form = UserProfileForm({"role": "EQUIPIER", "ship": simple.pk, "equipage": ""})
        self.assertNotIn("equipage", form.errors)

    def test_api_refuse_un_profil_sans_equipage_mais_garde_les_existants(self):
        sans = self._marin("sans", "EQUIPIER", "")
        root = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self.client.login(username="root", password="pass")
        url = reverse("userprofile-detail", args=[sans.profile.pk])
        # Modifier un autre champ d'un profil existant sans équipage reste possible.
        self.assertEqual(self.client.patch(url, {"grade": "QM1"}, content_type="application/json").status_code, 200)
        # Changer d'unité ou d'équipage impose la valeur.
        r = self.client.patch(url, {"ship": self.navire.pk}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("equipage", r.json())

    def test_annuaire_cree_avec_equipage_et_refuse_sans(self):
        self.client.login(username="cdt", password="pass")
        base = {"action": "create_user", "first_name": "Jean", "last_name": "Test", "role": "EQUIPIER", "ship_id": self.navire.pk}
        self.client.post(reverse("user-directory"), base)
        self.assertFalse(User.objects.filter(last_name="Test").exists())
        self.client.post(reverse("user-directory"), {**base, "equipage": "B"})
        self.assertEqual(User.objects.get(last_name="Test").profile.equipage, "B")

    def test_annuaire_signale_les_marins_sans_equipage(self):
        self._marin("sans", "EQUIPIER", "")
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("user-directory")), "1 marin sans équipage")


class ExemptionsA_TerreTests(DoubleEquipageBase):
    def _json(self, methode, url, donnees):
        return getattr(self.client, methode)(url, donnees, content_type="application/json")

    def test_admin_a_terre_ne_change_pas_son_equipage(self):
        self.client.login(username="adm", password="pass")
        r = self.client.post(reverse("user-directory"), {"action": "edit_user", "pk": self.admin.pk, "equipage": "A", "ship_id": self.navire.pk})
        self.assertEqual(r.status_code, 403)
        r = self._json("patch", reverse("userprofile-detail", args=[self.admin.profile.pk]), {"equipage": "A"})
        self.assertEqual(r.status_code, 403)
        self.admin.profile.refresh_from_db()
        self.assertEqual(self.admin.profile.equipage, "B")

    def test_chef_a_terre_ne_modifie_pas_un_profil(self):
        self.client.login(username="chef", password="pass")
        r = self._json("patch", reverse("userprofile-detail", args=[self.bord.profile.pk]), {"grade": "QM1"})
        self.assertEqual(r.status_code, 403)

    def test_admin_a_terre_ne_modifie_ni_navire_ni_parametres(self):
        self.client.login(username="adm", password="pass")
        self.assertEqual(self._json("patch", reverse("ship-detail", args=[self.navire.pk]), {"name": "X"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("settings"), {"action": "toggle_module"}).status_code, 403)

    def test_commandant_a_terre_garde_la_releve(self):
        # Le commandant de l'équipage B (à terre) valide la relève proposée par celui de A.
        self.client.login(username="cdt", password="pass")
        self.client.post(reverse("settings"), {"action": "proposer_releve", "equipage": "B"})
        self.client.login(username="cdtb", password="pass")
        r = self.client.post(reverse("settings"), {"action": "decider_releve", "decision": "valider"})
        self.assertEqual(r.status_code, 302)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "B")

    def test_mot_de_passe_et_theme_restent_possibles_a_terre(self):
        self.client.login(username="adm", password="pass")
        r = self.client.post(reverse("basculer-theme"), {})
        self.assertNotEqual(r.status_code, 403)
        r = self.client.post(reverse("password_change"), {"old_password": "pass", "new_password1": "Zx9!kLmQ2w", "new_password2": "Zx9!kLmQ2w"})
        self.assertEqual(r.status_code, 302)

    def test_modification_sans_champ_equipage_le_conserve(self):
        self.client.login(username="cdt", password="pass")
        self.client.post(reverse("user-directory"), {"action": "edit_user", "pk": self.bord.pk, "ship_id": self.navire.pk, "first_name": "Z"})
        self.bord.profile.refresh_from_db()
        self.assertEqual(self.bord.profile.equipage, "A")
