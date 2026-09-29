"""Double équipage (FREMM, PSP, BSAM), tranche 1 : modèle Équipage, rattachement
des marins, relève à bord / à terre, lecture seule de l'équipage à terre et
rétrocompatibilité stricte des navires à équipage unique."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from org.equipages import equipage_a_bord, est_en_lecture_seule, navire_eligible
from org.models import Equipage, Service, Ship


def creer_marin(username, role, ship=None, equipage=None):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": ship, "equipage": equipage}
    )
    return User.objects.get(pk=user.pk)


class EligibiliteTests(TestCase):
    def test_classes_concernees_seulement(self):
        for classe, attendu in [("FREMM", True), ("fremm Aquitaine", True), ("PSP", True), ("BSAM", True),
                                ("BRF", False), ("FDA", False), ("", False), ("FREMMX", False)]:
            self.assertEqual(navire_eligible(Ship(classe_navire=classe)), attendu, classe)


class ModeleEtHelperTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM A", code="FA", classe_navire="FREMM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        self.navire.equipage_a_bord = self.bleu
        self.navire.save()

    def test_equipage_a_bord_simple(self):
        self.assertEqual(equipage_a_bord(self.navire), self.bleu)

    def test_releve_planifiee_prend_effet_a_sa_date(self):
        demain = date.today() + timedelta(days=1)
        self.navire.equipage_releve, self.navire.date_releve = self.rouge, demain
        self.assertEqual(equipage_a_bord(self.navire), self.bleu)
        self.assertEqual(equipage_a_bord(self.navire, demain), self.rouge)

    def test_navire_a_equipage_unique_sans_equipage_a_bord(self):
        brf = Ship.objects.create(name="BRF", code="BRF")
        self.assertIsNone(equipage_a_bord(brf))

    def test_lecture_seule_uniquement_pour_l_equipage_a_terre(self):
        a_bord = creer_marin("a_bord", "EQUIPIER", self.navire, self.bleu)
        a_terre = creer_marin("a_terre", "COMMANDANT", self.navire, self.rouge)
        sans = creer_marin("sans", "EQUIPIER", self.navire)
        self.assertFalse(est_en_lecture_seule(a_bord))
        self.assertTrue(est_en_lecture_seule(a_terre))
        self.assertFalse(est_en_lecture_seule(sans))

    def test_administrateur_general_jamais_en_lecture_seule(self):
        master = creer_marin("master", "MASTER_ADMIN", self.navire, self.rouge)
        self.assertFalse(est_en_lecture_seule(master))

    def test_desactiver_le_double_equipage_leve_la_lecture_seule(self):
        a_terre = creer_marin("a_terre", "EQUIPIER", self.navire, self.rouge)
        self.navire.double_equipage = False
        self.navire.save()
        a_terre = User.objects.get(pk=a_terre.pk)
        self.assertFalse(est_en_lecture_seule(a_terre))

    def test_migration_retrocompatible_valeurs_par_defaut(self):
        brf = Ship.objects.create(name="BRF", code="BRF")
        self.assertFalse(brf.double_equipage)
        self.assertIsNone(brf.equipage_a_bord)
        self.assertIsNone(creer_marin("m", "EQUIPIER", brf).profile.equipage)


class PageEquipagesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("equipages")
        self.navire = Ship.objects.create(name="FREMM B", code="FB", classe_navire="FREMM")
        self.autre = Ship.objects.create(name="FREMM C", code="FC", classe_navire="FREMM")
        self.brf = Ship.objects.create(name="BRF", code="BRF", classe_navire="BRF")

    def _connecte(self, username, role, ship):
        user = creer_marin(username, role, ship)
        self.client.login(username=username, password="pass")
        return user

    def _post(self, action, **donnees):
        return self.client.post(self.url, {"action": action, **donnees})

    def _activer(self):
        self._post("activer_double_equipage")
        self.navire.refresh_from_db()

    def test_role_inferieur_au_seuil_refuse(self):
        self._connecte("chef", "CHEF_SERVICE", self.navire)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self._post("activer_double_equipage").status_code, 403)
        self.navire.refresh_from_db()
        self.assertFalse(self.navire.double_equipage)

    def test_commandant_active_le_double_equipage(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        self.assertTrue(self.navire.double_equipage)
        self.assertEqual(set(self.navire.equipages.values_list("nom", flat=True)), {"Bleu", "Rouge"})
        self.assertIsNotNone(self.navire.equipage_a_bord)
        self.assertTrue(AuditLog.objects.filter(action="activer_double_equipage").exists())
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_activation_refusee_pour_une_classe_non_concernee(self):
        self._connecte("cdt", "COMMANDANT", self.brf)
        self._post("activer_double_equipage")
        self.brf.refresh_from_db()
        self.assertFalse(self.brf.double_equipage)
        self.assertFalse(Equipage.objects.exists())

    def test_commandant_ne_touche_pas_a_un_autre_navire(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._post("activer_double_equipage", ship_id=self.autre.pk)
        self.autre.refresh_from_db()
        self.assertFalse(self.autre.double_equipage)

    def test_administrateur_general_choisit_le_navire(self):
        creer_marin("master", "MASTER_ADMIN")
        self.client.login(username="master", password="pass")
        self._post("activer_double_equipage", ship_id=self.autre.pk)
        self.autre.refresh_from_db()
        self.assertTrue(self.autre.double_equipage)

    def test_affectation_des_marins_dans_le_perimetre(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        bleu = self.navire.equipages.get(nom="Bleu")
        marin = creer_marin("marin", "EQUIPIER", self.navire)
        etranger = creer_marin("etranger", "EQUIPIER", self.autre)
        self._post("affecter_equipage_marin", user_id=marin.pk, equipage_id=bleu.pk)
        self._post("affecter_equipage_marin", user_id=etranger.pk, equipage_id=bleu.pk)
        marin.profile.refresh_from_db()
        etranger.profile.refresh_from_db()
        self.assertEqual(marin.profile.equipage, bleu)
        self.assertIsNone(etranger.profile.equipage)
        self.assertTrue(AuditLog.objects.filter(action="affecter_equipage_marin", target_user=marin).exists())

    def test_equipage_d_un_autre_navire_refuse(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        creer_marin("creation", "EQUIPIER", self.autre)
        autre_eq = Equipage.objects.create(ship=self.autre, nom="Bleu")
        marin = creer_marin("marin", "EQUIPIER", self.navire)
        self._post("affecter_equipage_marin", user_id=marin.pk, equipage_id=autre_eq.pk)
        marin.profile.refresh_from_db()
        self.assertIsNone(marin.profile.equipage)

    def test_releve_immediate_bascule_et_trace(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        rouge = self.navire.equipages.get(nom="Rouge")
        bleu = self.navire.equipages.get(nom="Bleu")
        descendant = creer_marin("desc", "EQUIPIER", self.navire, bleu)
        montant = creer_marin("mont", "EQUIPIER", self.navire, rouge)
        self._post("planifier_releve", equipage_id=rouge.pk, date=date.today().isoformat())
        self.navire.refresh_from_db()
        self.assertEqual(equipage_a_bord(self.navire), rouge)
        self.assertTrue(est_en_lecture_seule(User.objects.get(pk=descendant.pk)))
        self.assertFalse(est_en_lecture_seule(User.objects.get(pk=montant.pk)))
        self.assertTrue(AuditLog.objects.filter(action="equipage_releve").exists())

    def test_releve_planifiee_puis_annulee(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        rouge = self.navire.equipages.get(nom="Rouge")
        bleu_a_bord = equipage_a_bord(self.navire)
        demain = (date.today() + timedelta(days=1)).isoformat()
        self._post("planifier_releve", equipage_id=rouge.pk, date=demain)
        self.navire.refresh_from_db()
        self.assertEqual(equipage_a_bord(self.navire), bleu_a_bord)
        self.assertEqual(self.navire.equipage_releve, rouge)
        self._post("annuler_releve")
        self.navire.refresh_from_db()
        self.assertIsNone(self.navire.equipage_releve)

    def test_date_invalide_refusee(self):
        self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        rouge = self.navire.equipages.get(nom="Rouge")
        self._post("planifier_releve", equipage_id=rouge.pk, date="pas-une-date")
        self.navire.refresh_from_db()
        self.assertIsNone(self.navire.equipage_releve)

    def test_commandant_de_l_equipage_a_terre_ne_peut_pas_faire_la_releve(self):
        cdt = self._connecte("cdt", "COMMANDANT", self.navire)
        self._activer()
        rouge = self.navire.equipages.get(nom="Rouge")
        cdt.profile.equipage = rouge
        cdt.profile.save()
        bleu = self.navire.equipages.get(nom="Bleu")
        reponse = self._post("planifier_releve", equipage_id=rouge.pk, date=date.today().isoformat())
        self.assertEqual(reponse.status_code, 302)
        self.navire.refresh_from_db()
        self.assertEqual(equipage_a_bord(self.navire), bleu)


class LectureSeuleTests(TestCase):
    """Lecture seule appliquée par le point d'entrée unique (middleware + RolePermission)."""

    def setUp(self):
        cache.clear()
        self.navire = Ship.objects.create(name="PSP A", code="PA", classe_navire="PSP", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        self.navire.equipage_a_bord = self.bleu
        self.navire.save()
        self.payload = {"ship": self.navire.pk, "name": "Machine"}

    def test_equipage_a_terre_ne_peut_pas_ecrire_via_l_api(self):
        creer_marin("terre", "COMMANDANT", self.navire, self.rouge)
        self.client.login(username="terre", password="pass")
        reponse = self.client.post("/api/org/services/", self.payload)
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(Service.objects.exists())

    def test_equipage_a_terre_peut_lire(self):
        creer_marin("terre", "EQUIPIER", self.navire, self.rouge)
        self.client.login(username="terre", password="pass")
        self.assertEqual(self.client.get("/api/org/services/").status_code, 200)
        self.assertContains(self.client.get("/"), "lecture seule")

    def test_equipage_a_bord_ecrit_normalement(self):
        creer_marin("bord", "COMMANDANT", self.navire, self.bleu)
        self.client.login(username="bord", password="pass")
        reponse = self.client.post("/api/org/services/", self.payload)
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertNotContains(self.client.get("/"), "lecture seule")

    def test_api_basic_couverte_par_role_permission(self):
        import base64
        creer_marin("terre", "COMMANDANT", self.navire, self.rouge)
        jeton = base64.b64encode(b"terre:pass").decode()
        reponse = self.client.post(
            "/api/org/services/", self.payload, HTTP_AUTHORIZATION=f"Basic {jeton}"
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(Service.objects.exists())

    def test_la_releve_rend_l_ecriture_a_l_autre_equipage(self):
        creer_marin("terre", "COMMANDANT", self.navire, self.rouge)
        self.client.login(username="terre", password="pass")
        self.navire.equipage_a_bord = self.rouge
        self.navire.save()
        self.assertEqual(self.client.post("/api/org/services/", self.payload).status_code, 201)

    def test_deconnexion_toujours_possible(self):
        creer_marin("terre", "EQUIPIER", self.navire, self.rouge)
        self.client.login(username="terre", password="pass")
        self.assertEqual(self.client.post("/logout/").status_code, 302)
        self.assertEqual(self.client.get("/api/org/services/").status_code, 403)


class RetrocompatibiliteEquipageUniqueTests(TestCase):
    """Un navire à équipage unique se comporte exactement comme avant."""

    def setUp(self):
        cache.clear()
        self.brf = Ship.objects.create(name="BRF", code="BRF", classe_navire="BRF")

    def test_ecriture_inchangee_sans_equipage(self):
        creer_marin("cdt", "COMMANDANT", self.brf)
        self.client.login(username="cdt", password="pass")
        reponse = self.client.post("/api/org/services/", {"ship": self.brf.pk, "name": "Pont"})
        self.assertEqual(reponse.status_code, 201, reponse.content)

    def test_ecriture_inchangee_meme_avec_equipage_residuel(self):
        """Un marin resté rattaché à un équipage alors que le drapeau est
        retiré ne subit aucune restriction."""
        eq = Equipage.objects.create(ship=self.brf, nom="Rouge")
        creer_marin("cdt", "COMMANDANT", self.brf, eq)
        self.client.login(username="cdt", password="pass")
        reponse = self.client.post("/api/org/services/", {"ship": self.brf.pk, "name": "Pont"})
        self.assertEqual(reponse.status_code, 201, reponse.content)

    def test_aucun_bandeau_ni_menu_equipages(self):
        creer_marin("cdt", "COMMANDANT", self.brf)
        self.client.login(username="cdt", password="pass")
        page = self.client.get("/")
        self.assertNotContains(page, "lecture seule")
        self.assertNotContains(page, reverse("equipages"))


class LectureSeuleToutesLesVuesApiTests(TestCase):
    """L'authentification DRF couvre TOUTES les vues, Basic comme session,
    même celles qui n'utilisent pas RolePermission."""

    def setUp(self):
        cache.clear()
        self.navire = Ship.objects.create(name="BSAM A", code="BA", classe_navire="BSAM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        self.navire.equipage_a_bord = self.bleu
        self.navire.save()
        self.terre = creer_marin("terre", "COMMANDANT", self.navire, self.rouge)
        self.bord = creer_marin("bord", "COMMANDANT", self.navire, self.bleu)
        from notifications.models import Notification
        self.notif = Notification.objects.create(user=self.terre, verb="Test")
        self.Notification = Notification

    def _basic(self, username="terre"):
        import base64
        jeton = base64.b64encode(f"{username}:pass".encode()).decode()
        return {"HTTP_AUTHORIZATION": f"Basic {jeton}"}

    def _verifie_refuse(self, methode, url, **extra):
        reponse = getattr(self.client, methode)(url, {}, content_type="application/json", **extra)
        self.assertEqual(reponse.status_code, 403, f"{methode} {url}")
        self.assertIn("lecture seule", reponse.content.decode())

    def test_basic_bloque_threads_training_notifications(self):
        for url in ("/api/threads/threads/", "/api/training/courses/", "/api/notifications/notifications/"):
            self._verifie_refuse("post", url, **self._basic())

    def test_session_bloque_threads_training_notifications(self):
        self.client.login(username="terre", password="pass")
        for url in ("/api/threads/threads/", "/api/training/courses/", "/api/notifications/notifications/"):
            self._verifie_refuse("post", url)

    def test_equipage_a_bord_non_bloque_par_le_verrou(self):
        reponse = self.client.post(
            "/api/threads/threads/", {}, content_type="application/json", **self._basic("bord")
        )
        self.assertNotIn("lecture seule", reponse.content.decode())

    def test_exemptions_notifications_limitees(self):
        self.client.login(username="terre", password="pass")
        base = "/api/notifications/notifications/"
        self.assertEqual(self.client.post(base + "mark_all_read/").status_code, 200)
        reponse = self.client.patch(
            f"{base}{self.notif.pk}/", {"is_read": True}, content_type="application/json"
        )
        self.assertEqual(reponse.status_code, 200)
        self._verifie_refuse("delete", f"{base}{self.notif.pk}/")
        self._verifie_refuse("put", f"{base}{self.notif.pk}/")
        self.assertTrue(self.Notification.objects.filter(pk=self.notif.pk).exists())


class EquipageResiduelEtVerrouillageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.navire = Ship.objects.create(name="FREMM D", code="FD", classe_navire="FREMM", double_equipage=True)
        self.autre = Ship.objects.create(name="BRF D", code="BD", classe_navire="BRF")
        self.bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        self.navire.equipage_a_bord = self.bleu
        self.navire.save()

    def test_changement_de_navire_vide_l_equipage(self):
        marin = creer_marin("m", "EQUIPIER", self.navire, self.rouge)
        profil = marin.profile
        profil.ship = self.autre
        profil.save(update_fields=["ship"])
        profil.refresh_from_db()
        self.assertIsNone(profil.equipage)
        self.assertFalse(est_en_lecture_seule(User.objects.get(pk=marin.pk)))

    def test_equipage_d_un_autre_navire_ignore_meme_en_base(self):
        marin = creer_marin("m", "EQUIPIER", self.autre)
        UserProfile.objects.filter(user=marin).update(equipage=self.rouge)
        self.assertFalse(est_en_lecture_seule(User.objects.get(pk=marin.pk)))

    def test_marin_rattache_par_son_service_seulement(self):
        service = Service.objects.create(ship=self.navire, name="Pont")
        marin = creer_marin("m", "EQUIPIER", None, None)
        marin.profile.service = service
        marin.profile.equipage = self.rouge
        marin.profile.save()
        self.assertTrue(est_en_lecture_seule(User.objects.get(pk=marin.pk)))

    def _connecte(self, username, role, equipage):
        creer_marin(username, role, self.navire, equipage)
        self.client.login(username=username, password="pass")

    def test_auto_affectation_a_l_equipage_a_terre_refusee(self):
        self._connecte("chef", "COMMANDANT", self.bleu)
        moi = User.objects.get(username="chef")
        self.client.post(reverse("equipages"), {
            "action": "affecter_equipage_marin", "user_id": moi.pk, "equipage_id": self.rouge.pk})
        moi.profile.refresh_from_db()
        self.assertEqual(moi.profile.equipage, self.bleu)

    def test_releve_immediate_mettant_son_equipage_a_terre_refusee(self):
        self._connecte("chef", "COMMANDANT", self.bleu)
        self.client.post(reverse("equipages"), {
            "action": "planifier_releve", "equipage_id": self.rouge.pk, "date": date.today().isoformat()})
        self.navire.refresh_from_db()
        self.assertEqual(equipage_a_bord(self.navire), self.bleu)

    def test_plan_de_secours_admin_navire_corrige_l_equipage_a_bord(self):
        self._connecte("admin", "ADMIN_NAVIRE", self.bleu)
        self.client.post(reverse("equipages"), {
            "action": "planifier_releve", "equipage_id": self.rouge.pk, "date": date.today().isoformat()})
        self.navire.refresh_from_db()
        self.assertEqual(equipage_a_bord(self.navire), self.rouge)
        admin = User.objects.get(username="admin")
        self.assertFalse(est_en_lecture_seule(admin))
