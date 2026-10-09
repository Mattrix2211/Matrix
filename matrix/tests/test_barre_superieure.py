"""Barre supérieure (docs/UX.md §8) : identité visible, déconnexion en un clic
(POST + CSRF), sélecteur de bâtiment réservé aux utilisateurs à terre et validé
côté serveur contre leur périmètre."""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import ResponsableSpecialite, SpecialityChoice, UserProfile
from matrix.core.contexte_batiment import CLE_SESSION, batiment_courant, batiments_du_perimetre
from org.models import ResponsableClasseNavire, Ship


class BarreSuperieureTestCase(TestCase):
    def setUp(self):
        self.alsace = Ship.objects.create(name="Alsace", code="D656", classe_navire="FREMM")
        self.provence = Ship.objects.create(name="Provence", code="D652", classe_navire="FREMM")
        self.latouche = Ship.objects.create(name="Latouche-Tréville", code="D646", classe_navire="La Fayette")
        self.ancien = Ship.objects.create(name="Ancien", code="X1", archived=True)

    def _marin(self, username, role="EQUIPIER", ship=None, **profil):
        user = User.objects.create_user(username=username, password="pass", **{
            cle: profil.pop(cle) for cle in ("first_name", "last_name") if cle in profil
        })
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, **profil})
        return User.objects.get(pk=user.pk)

    def _connecte(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("home"))


class IdentiteTests(BarreSuperieureTestCase):
    def test_nom_grade_role_et_batiment_visibles(self):
        user = self._marin(
            "dupont", "CHEF_SERVICE", self.alsace, first_name="Jean", last_name="Dupont",
            grade="Maître", fonction_service="COMOPS",
        )
        reponse = self._connecte(user)
        self.assertContains(reponse, "Maître Jean Dupont")
        self.assertContains(reponse, "Chef de service · COMOPS")
        self.assertContains(reponse, "Alsace")

    def test_utilisateur_sans_nom_complet_affiche_son_identifiant(self):
        reponse = self._connecte(self._marin("marin_sans_nom", ship=self.alsace))
        self.assertContains(reponse, "marin_sans_nom")
        self.assertContains(reponse, "Équipier")

    def test_superutilisateur_affiche_administrateur_general(self):
        admin = User.objects.create_superuser(username="root_barre", password="pass", email="r@r.fr")
        self.assertContains(self._connecte(admin), "Administrateur général")

    def test_barre_dans_un_repere_banniere(self):
        reponse = self._connecte(self._marin("repere", ship=self.alsace))
        self.assertContains(reponse, "<header")


class DeconnexionTests(BarreSuperieureTestCase):
    def test_bouton_de_deconnexion_visible_en_post_avec_csrf(self):
        reponse = self._connecte(self._marin("deco", ship=self.alsace))
        html = reponse.content.decode()
        debut = html.index(f'action="{reverse("logout")}"')
        formulaire = html[html.rindex("<form", 0, debut):html.index("</form>", debut)]
        self.assertIn('method="post"', formulaire)
        self.assertIn("csrfmiddlewaretoken", formulaire)
        self.assertIn("Déconnexion", formulaire)

    def test_deconnexion_post_redirige_vers_la_connexion(self):
        self.client.force_login(self._marin("deco2", ship=self.alsace))
        reponse = self.client.post(reverse("logout"))
        self.assertRedirects(reponse, "/login/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deconnexion_efface_le_batiment_courant(self):
        self.client.force_login(self._marin("deco3", "MASTER_ADMIN"))
        self.client.post(reverse("choisir-batiment"), {"batiment": self.provence.pk})
        self.client.post(reverse("logout"))
        self.assertNotIn(CLE_SESSION, self.client.session)

    def test_deconnexion_par_get_refusee(self):
        user = self._marin("deco4", ship=self.alsace)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_deconnexion_sans_jeton_csrf_refusee(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self._marin("deco5", ship=self.alsace))
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        self.assertIn("_auth_user_id", client.session)


class SelecteurBatimentTests(BarreSuperieureTestCase):
    def test_utilisateur_de_bord_sans_selecteur_batiment_en_texte(self):
        for role in ("EQUIPIER", "CHEF_SERVICE", "COMMANDANT", "ADMIN_NAVIRE"):
            reponse = self._connecte(self._marin(f"bord_{role}", role, self.alsace))
            self.assertNotContains(reponse, "Changer de bâtiment")
            self.assertContains(reponse, "Bâtiment de rattachement")

    def test_administrateur_general_voit_tous_les_batiments_actifs(self):
        reponse = self._connecte(self._marin("admin_flotte", "MASTER_ADMIN"))
        self.assertContains(reponse, "Changer de bâtiment")
        for navire in (self.alsace, self.provence, self.latouche):
            self.assertContains(reponse, f'name="batiment" value="{navire.pk}"')
        self.assertNotContains(reponse, f'value="{self.ancien.pk}"')

    def test_responsable_de_classe_ne_voit_que_les_batiments_de_ses_classes(self):
        user = self._marin("resp_classe", "EQUIPIER", self.latouche)
        ResponsableClasseNavire.objects.create(user=user, classe_navire="FREMM")
        reponse = self._connecte(user)
        self.assertContains(reponse, f'name="batiment" value="{self.alsace.pk}"')
        self.assertContains(reponse, f'name="batiment" value="{self.provence.pk}"')
        # Son propre bâtiment de rattachement reste proposé.
        self.assertContains(reponse, f'name="batiment" value="{self.latouche.pk}"')
        self.assertNotContains(reponse, f'value="{self.ancien.pk}"')

    def test_responsable_de_classe_d_une_seule_unite_sans_selecteur(self):
        user = self._marin("resp_classe_seul", "EQUIPIER", None)
        ResponsableClasseNavire.objects.create(user=user, classe_navire="La Fayette")
        self.assertNotContains(self._connecte(user), "Changer de bâtiment")

    def test_responsable_de_specialite_suit_toute_la_flotte(self):
        user = self._marin("resp_spe", "EQUIPIER", self.alsace)
        specialite = SpecialityChoice.objects.create(name="Mécan")
        ResponsableSpecialite.objects.create(user=user, specialite=specialite)
        self.assertEqual(
            set(batiments_du_perimetre(user)), {self.alsace, self.provence, self.latouche}
        )
        self.assertContains(self._connecte(user), "Changer de bâtiment")

    def test_choix_memorise_et_affiche(self):
        user = self._marin("admin_choix", "MASTER_ADMIN")
        self.client.force_login(user)
        reponse = self.client.post(
            reverse("choisir-batiment"), {"batiment": self.provence.pk, "next": reverse("calendar-index")},
        )
        self.assertRedirects(reponse, reverse("calendar-index"), fetch_redirect_response=False)
        self.assertEqual(self.client.session[CLE_SESSION], self.provence.pk)
        page = self.client.get(reverse("home"))
        self.assertEqual(page.context["batiment_courant"], self.provence)

    def test_batiment_hors_perimetre_refuse(self):
        user = self._marin("resp_hors", "EQUIPIER", self.latouche)
        ResponsableClasseNavire.objects.create(user=user, classe_navire="FREMM")
        self.client.force_login(user)
        autre = Ship.objects.create(name="Autre", code="Z9", classe_navire="Horizon")
        for demande in (autre.pk, self.ancien.pk, "abc", ""):
            reponse = self.client.post(reverse("choisir-batiment"), {"batiment": demande})
            self.assertEqual(reponse.status_code, 403, demande)
        self.assertNotIn(CLE_SESSION, self.client.session)

    def test_utilisateur_de_bord_ne_peut_pas_forcer_un_autre_batiment(self):
        self.client.force_login(self._marin("bord_force", "COMMANDANT", self.alsace))
        reponse = self.client.post(reverse("choisir-batiment"), {"batiment": self.provence.pk})
        self.assertEqual(reponse.status_code, 403)
        self.assertNotIn(CLE_SESSION, self.client.session)

    def test_choix_par_get_et_sans_connexion_refuses(self):
        self.assertEqual(self.client.get(reverse("choisir-batiment")).status_code, 302)
        self.client.force_login(self._marin("admin_get", "MASTER_ADMIN"))
        self.assertEqual(self.client.get(reverse("choisir-batiment")).status_code, 405)

    def test_choix_sans_jeton_csrf_refuse(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self._marin("admin_csrf", "MASTER_ADMIN"))
        reponse = client.post(reverse("choisir-batiment"), {"batiment": self.provence.pk})
        self.assertEqual(reponse.status_code, 403)
        self.assertNotIn(CLE_SESSION, client.session)

    def test_redirection_vers_un_hote_externe_neutralisee(self):
        self.client.force_login(self._marin("admin_next", "MASTER_ADMIN"))
        reponse = self.client.post(
            reverse("choisir-batiment"), {"batiment": self.alsace.pk, "next": "https://exemple.org/"},
        )
        self.assertRedirects(reponse, "/", fetch_redirect_response=False)

    def test_choix_perime_ignore_si_le_perimetre_change(self):
        user = self._marin("resp_perime", "EQUIPIER", self.latouche)
        reponsabilite = ResponsableClasseNavire.objects.create(user=user, classe_navire="FREMM")
        self.client.force_login(user)
        self.client.post(reverse("choisir-batiment"), {"batiment": self.provence.pk})
        reponsabilite.delete()
        reponse = self.client.get(reverse("home"))
        self.assertEqual(reponse.context["batiment_courant"], self.latouche)

    def test_sans_choix_le_batiment_de_rattachement_est_le_defaut(self):
        user = self._marin("admin_defaut", "MASTER_ADMIN", self.alsace)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("home")).context["batiment_courant"], self.alsace)

    def test_batiment_courant_fonction_pure(self):
        user = self._marin("admin_pur", "MASTER_ADMIN")
        requete = type("R", (), {"user": user, "session": {CLE_SESSION: self.provence.pk}})()
        self.assertEqual(batiment_courant(requete), self.provence)
