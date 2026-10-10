"""Barre latérale (docs/UX.md §7) : visibilité par rôle et par module,
entrée courante, état replié mémorisé par marin, aucun lien mort."""
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse

from accounts.models import SpecialityChoice, UserProfile
from matrix.core.icones import ICONES
from matrix.core.modules import invalidate_cache
from matrix.core.navigation import GROUPES, construire_navigation
from org.models import ModuleActivation, Ship


def _libelles(groupes):
    return [e["libelle"] for g in groupes for e in g["entrees"]]


def _titres(groupes):
    return [g["titre"] for g in groupes]


class NavigationLateraleTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Frégate Nav", code="FR-NAV")
        self.addCleanup(invalidate_cache, self.ship.id)

    def _marin(self, username, role):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.ship})
        return User.objects.get(pk=user.pk)  # recharge : le profil créé par signal est en cache

    def _nav(self, user, chemin="/"):
        return construire_navigation(user, chemin)

    def test_equipier_ne_voit_ni_administration_ni_vue_flotte(self):
        libelles = _libelles(self._nav(self._marin("equipier_nav", "EQUIPIER")))
        self.assertIn("Aujourd'hui", libelles)
        self.assertIn("Matériels", libelles)
        self.assertNotIn("Annuaire", libelles)
        self.assertNotIn("Flotte", libelles)
        self.assertNotIn("Configurer le plan du navire", libelles)

    def test_chef_de_section_voit_la_vue_flotte(self):
        self.assertIn("Flotte", _libelles(self._nav(self._marin("section_nav", "CHEF_SECTION"))))

    def test_chef_de_service_configure_le_plan_mais_pas_d_annuaire(self):
        libelles = _libelles(self._nav(self._marin("service_nav", "CHEF_SERVICE")))
        self.assertIn("Configurer le plan du navire", libelles)
        self.assertNotIn("Annuaire", libelles)

    def test_commandant_voit_l_annuaire(self):
        self.assertIn("Annuaire", _libelles(self._nav(self._marin("cdt_nav", "COMMANDANT"))))

    def test_groupes_dans_l_ordre_du_chapitre_7(self):
        admin = User.objects.create_superuser(username="admin_nav", password="pass", email="a@a.fr")
        self.assertEqual(
            _titres(self._nav(admin)),
            ["Personnel", "Équipements", "Maintenance", "Activité", "Compétences", "Supervision", "Administration"],
        )

    def test_module_desactive_masque_ses_entrees_et_le_groupe_vide(self):
        user = self._marin("module_nav", "EQUIPIER")
        for module in ("rondes", "quarts", "absences"):
            ModuleActivation.objects.create(ship=self.ship, module=module, active=False)
        invalidate_cache(self.ship.id)
        groupes = self._nav(user)
        self.assertNotIn("Rondes", _libelles(groupes))
        self.assertNotIn("Quarts et gardes", _libelles(groupes))
        self.assertNotIn("Activité", _titres(groupes))

    def test_module_assets_desactive_masque_equipements(self):
        user = self._marin("assets_nav", "EQUIPIER")
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)
        self.assertNotIn("Équipements", _titres(self._nav(user)))

    def test_entree_courante_unique_et_aria_current(self):
        self.client.force_login(self._marin("courant_nav", "EQUIPIER"))
        html = self.client.get(reverse("asset-list")).content.decode()
        self.assertEqual(html.count('aria-current="page"'), 1)
        courante = html.split('aria-current="page"')[0].rsplit("<a ", 1)[1]
        self.assertIn('aria-label="Matériels"', courante)

    def test_plan_du_navire_est_plus_precis_que_materiels(self):
        user = self._marin("plan_nav", "EQUIPIER")
        groupes = self._nav(user, reverse("plan-navire-vue"))
        courantes = [e["libelle"] for g in groupes for e in g["entrees"] if e["courante"]]
        self.assertEqual(courantes, ["Plan du navire"])

    def test_calendrier_filtre_maintenance_reste_sur_calendrier(self):
        user = self._marin("cal_nav", "EQUIPIER")
        courantes = [e["libelle"] for g in self._nav(user, reverse("calendar-index"))
                     for e in g["entrees"] if e["courante"]]
        self.assertEqual(courantes, ["Calendrier"])

    def test_une_seule_entree_maintenance_vers_les_occurrences(self):
        user = self._marin("maint_nav", "EQUIPIER")
        entrees = [e for g in self._nav(user) for e in g["entrees"] if e["libelle"] == "Maintenance"]
        self.assertEqual([e["url"] for e in entrees], [reverse("maintenance-occurrences")])
        self.assertNotIn("Gestion Maintenance", _libelles(self._nav(user)))

    def test_libelles_du_chapitre_7_en_supervision(self):
        admin = User.objects.create_superuser(username="sup_nav", password="pass", email="s@s.fr")
        supervision = [g for g in self._nav(admin) if g["titre"] == "Supervision"][0]
        self.assertEqual(
            [e["libelle"] for e in supervision["entrees"]],
            ["Prêt à appareiller", "Flotte", "Spécialités", "Classes de navire"],
        )

    def test_pret_a_appareiller_visible_de_tout_marin(self):
        libelles = _libelles(self._nav(self._marin("pret_nav", "EQUIPIER")))
        self.assertIn("Prêt à appareiller", libelles)

    def test_accueil_courant_uniquement_sur_la_racine(self):
        user = self._marin("accueil_nav", "EQUIPIER")
        courantes = lambda chemin: [e["libelle"] for g in self._nav(user, chemin)
                                    for e in g["entrees"] if e["courante"]]
        self.assertEqual(courantes("/"), ["Aujourd'hui"])
        self.assertNotIn("Aujourd'hui", courantes("/formations/"))

    def test_page_sans_entree_correspondante_n_a_pas_de_courante(self):
        self.client.force_login(self._marin("profil_nav", "EQUIPIER"))
        html = self.client.get(reverse("mon-profil")).content.decode()
        self.assertNotIn('aria-current="page"', html)

    def test_libelle_toujours_accompagne_d_une_icone(self):
        self.client.force_login(self._marin("icone_nav", "COMMANDANT"))
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count('class="mx-lateral__lien'), html.count('mx-lateral__icone'))
        self.assertIn('title="Matériels"', html)

    def test_visiteur_anonyme_sans_barre_laterale(self):
        response = self.client.get(reverse("login"))
        self.assertNotContains(response, 'id="barre-laterale"')

    def test_aucun_lien_mort(self):
        admin = User.objects.create_superuser(username="mort_nav", password="pass", email="m@m.fr")
        for groupe in self._nav(admin):
            for entree in groupe["entrees"]:
                chemin = entree["url"].split("?")[0]
                self.assertTrue(resolve(chemin), entree["libelle"])
        # Sans spécialité ni classe de navire existantes, ces tableaux de bord répondent 403.
        SpecialityChoice.objects.create(name="Mécan")
        Ship.objects.filter(pk=self.ship.pk).update(classe_navire="FREMM")
        self.client.force_login(admin)
        for groupe in self._nav(admin):
            for entree in groupe["entrees"]:
                reponse = self.client.get(entree["url"])
                self.assertIn(reponse.status_code, (200, 302), entree["libelle"])

    def test_icones_des_entrees_declarees_dans_la_table(self):
        for _, entrees in GROUPES:
            for entree in entrees:
                self.assertIn(entree.icone, ICONES, entree.libelle)

    def test_construire_navigation_sans_requete_http(self):
        requete = RequestFactory().get("/")
        self.assertTrue(construire_navigation(self._marin("rf_nav", "EQUIPIER"), requete.path))


class EtatBarreLateraleTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Frégate Etat", code="FR-ETAT")
        self.marin = User.objects.create_user(username="etat_a", password="pass")
        self.autre = User.objects.create_user(username="etat_b", password="pass")
        for u in (self.marin, self.autre):
            UserProfile.objects.update_or_create(user=u, defaults={"role": "EQUIPIER", "ship": self.ship})
        self.url = reverse("memoriser-barre-laterale")

    def test_depliee_par_defaut(self):
        self.client.force_login(self.marin)
        html = self.client.get("/").content.decode()
        self.assertNotIn("mx-lateral--repliee", html.split('<aside', 1)[1].split('>', 1)[0])
        self.assertIn('aria-expanded="true"', html)

    def test_replier_est_memorise_pour_ce_marin_seulement(self):
        self.client.force_login(self.marin)
        reponse = self.client.post(self.url, {"repliee": "1"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(reponse.status_code, 204)
        self.marin.profile.refresh_from_db()
        self.assertTrue(self.marin.profile.barre_laterale_repliee)
        html = self.client.get("/").content.decode()
        self.assertIn("mx-lateral--repliee", html.split('<aside', 1)[1].split('>', 1)[0])
        self.assertIn('aria-expanded="false"', html)
        self.autre.profile.refresh_from_db()
        self.assertFalse(self.autre.profile.barre_laterale_repliee)

    def test_deplier_remet_l_etat_par_defaut(self):
        self.client.force_login(self.marin)
        self.client.post(self.url, {"repliee": "1"})
        self.client.post(self.url, {"repliee": "0"})
        self.marin.profile.refresh_from_db()
        self.assertFalse(self.marin.profile.barre_laterale_repliee)

    def test_sans_javascript_redirige_vers_la_page_precedente(self):
        self.client.force_login(self.marin)
        reponse = self.client.post(self.url, {"repliee": "1"}, HTTP_REFERER="/calendar/")
        self.assertRedirects(reponse, "/calendar/", fetch_redirect_response=False)

    def test_redirection_externe_refusee(self):
        self.client.force_login(self.marin)
        reponse = self.client.post(self.url, {"repliee": "1"}, HTTP_REFERER="http://exemple.test/")
        self.assertRedirects(reponse, "/", fetch_redirect_response=False)

    def test_connexion_requise_et_post_uniquement(self):
        self.assertEqual(self.client.post(self.url, {"repliee": "1"}).status_code, 302)
        self.client.force_login(self.marin)
        self.assertEqual(self.client.get(self.url).status_code, 405)
