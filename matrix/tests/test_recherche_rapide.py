"""Recherche rapide de la barre supérieure (docs/UX.md §21) : regroupement par
catégorie, périmètre identique aux vues de liste/détail, modules activés,
bornes de saisie, échappement, nombre de requêtes et accessibilité."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from logistics.models import Anomalie, CorrectiveTicket
from matrix.core import recherche
from org.models import ModuleActivation, Sector, Section, Service, Ship
from training.models import TrainingCourse

URL = "recherche-rapide"


class RechercheRapideTestCase(TestCase):
    def setUp(self):
        cache.clear()  # le cache des modules actifs survit d'un test à l'autre
        self.navire = Ship.objects.create(name="Navire A", code="NAVA")
        self.service = Service.objects.create(ship=self.navire, name="Service A")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur A")
        self.section_1 = Section.objects.create(sector=self.secteur, name="Section 1")
        self.section_2 = Section.objects.create(sector=self.secteur, name="Section 2")
        self.type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.secteur)
        self.autre_navire = Ship.objects.create(name="Navire B", code="NAVB")
        autre_service = Service.objects.create(ship=self.autre_navire, name="Service B")
        self.autre_secteur = Sector.objects.create(service=autre_service, name="Secteur B")
        autre_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.autre_secteur)

        def materiel(ident, section, navire=self.navire, service=self.service, secteur=self.secteur, type_=self.type):
            return Asset.objects.create(
                asset_type=type_, internal_id=ident, ship=navire, service=service, sector=secteur, section=section,
            )

        self.mat_s1 = materiel("ZEBRE-1", self.section_1)
        self.mat_s2 = materiel("ZEBRE-2", self.section_2)
        self.mat_autre = materiel("ZEBRE-3", None, self.autre_navire, autre_service, self.autre_secteur, autre_type)
        self.install_s1 = Installation.objects.create(
            designation="Pompe ZEBRE", ship=self.navire, service=self.service, sector=self.secteur, section=self.section_1,
        )
        self.install_autre = Installation.objects.create(
            designation="Pompe ZEBRE lointaine", ship=self.autre_navire, service=autre_service, sector=self.autre_secteur,
        )
        self.ticket_s1 = CorrectiveTicket.objects.create(asset=self.mat_s1, description="Fuite ZEBRE")
        self.ticket_autre = CorrectiveTicket.objects.create(asset=self.mat_autre, description="Fuite ZEBRE ailleurs")
        self.formation = TrainingCourse.objects.create(title="Secourisme ZEBRE", statut_validation="ACTIVE")

        self.equipier = self._marin("equipier", "EQUIPIER", section=self.section_1, sector=self.secteur, ship=self.navire)
        self.chef = self._marin("chef", "CHEF_SECTEUR", sector=self.secteur, ship=self.navire)
        self.commandant = self._marin("cdt", "COMMANDANT", ship=self.navire, last_name="Zebrowski")

        self.anomalie_equipier = Anomalie.objects.create(
            titre="Voyant ZEBRE", created_by=self.equipier, ship=self.navire, section=self.section_1,
        )
        self.anomalie_section_2 = Anomalie.objects.create(
            titre="Voyant ZEBRE bis", created_by=self.chef, ship=self.navire, sector=self.secteur, section=self.section_2,
        )

    def _marin(self, username, role, **profil):
        user = User.objects.create_user(username=username, password="pass", last_name=profil.pop("last_name", ""))
        UserProfile.objects.filter(user=user).update(role=role, **profil)
        return User.objects.get(pk=user.pk)

    def chercher(self, user, terme):
        self.client.force_login(user)
        return self.client.get(reverse(URL), {"q": terme})


class PerimetreTests(RechercheRapideTestCase):
    def test_equipier_ne_voit_que_sa_section(self):
        reponse = self.chercher(self.equipier, "ZEBRE")
        self.assertContains(reponse, reverse("asset-detail", args=[self.mat_s1.pk]))
        self.assertNotContains(reponse, reverse("asset-detail", args=[self.mat_s2.pk]))
        self.assertNotContains(reponse, reverse("asset-detail", args=[self.mat_autre.pk]))
        self.assertNotContains(reponse, reverse("installation-detail", args=[self.install_autre.pk]))
        self.assertNotContains(reponse, reverse("ticket-detail", args=[self.ticket_autre.pk]))

    def test_chef_de_secteur_voit_tout_son_secteur_mais_pas_un_autre_navire(self):
        reponse = self.chercher(self.chef, "ZEBRE")
        for objet in (self.mat_s1, self.mat_s2):
            self.assertContains(reponse, reverse("asset-detail", args=[objet.pk]))
        self.assertNotContains(reponse, reverse("asset-detail", args=[self.mat_autre.pk]))
        self.assertNotContains(reponse, reverse("ticket-detail", args=[self.ticket_autre.pk]))

    def test_anomalies_comme_la_liste_des_anomalies(self):
        equipier = self.chercher(self.equipier, "ZEBRE")
        self.assertContains(equipier, reverse("anomalie-detail", args=[self.anomalie_equipier.pk]))
        self.assertNotContains(equipier, reverse("anomalie-detail", args=[self.anomalie_section_2.pk]))
        chef = self.chercher(self.chef, "ZEBRE")
        self.assertContains(chef, reverse("anomalie-detail", args=[self.anomalie_section_2.pk]))

    def test_chaque_resultat_est_ouvrable_par_son_destinataire(self):
        self.client.force_login(self.equipier)
        reponse = self.client.get(reverse(URL), {"q": "ZEBRE"})
        for groupe in reponse.context["groupes"]:
            for resultat in filter(lambda r: r["url"], groupe["resultats"]):
                self.assertEqual(self.client.get(resultat["url"]).status_code, 200, resultat["url"])

    def test_equipier_trouve_un_collegue_du_meme_navire(self):
        reponse = self.chercher(self.equipier, "Zebrowski")
        self.assertContains(reponse, "Marins")
        self.assertContains(reponse, "Zebrowski")
        self.assertContains(reponse, "Commandant")  # rôle en sous-titre

    def test_equipier_ne_trouve_pas_un_marin_dun_autre_navire(self):
        self._marin("zebre_ailleurs", "EQUIPIER", ship=self.autre_navire, last_name="Zebrelle")
        self.assertNotContains(self.chercher(self.equipier, "Zebrelle"), "Zebrelle")
        self.assertNotContains(self.chercher(self.commandant, "Zebrelle"), "Zebrelle")

    def test_sans_rattachement_aucun_marin(self):
        orphelin = self._marin("orphelin", "EQUIPIER")
        self.assertNotContains(self.chercher(orphelin, "Zebrowski"), "Marins")
        self.assertNotContains(self.chercher(orphelin, "equipier"), "Marins")

    def test_maitre_voit_la_flotte(self):
        self._marin("zebre_ailleurs", "EQUIPIER", ship=self.autre_navire, last_name="Zebrelle")
        admin = User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self.assertContains(self.chercher(admin, "Zebrelle"), "Zebrelle")

    def test_resultat_marin_sans_lien_pour_equipier_avec_lien_pour_commandant(self):
        equipier = self.chercher(self.equipier, "Zebrowski")
        self.assertNotContains(equipier, reverse("user-directory"))
        self.assertContains(equipier, 'role="option"')
        self.assertContains(self.chercher(self.commandant, "Zebrowski"), reverse("user-directory") + "?q=cdt")

    def test_annuaire_toujours_interdit_a_un_equipier(self):
        self.client.force_login(self.equipier)
        self.assertEqual(self.client.get(reverse("user-directory")).status_code, 403)

    def test_identifiant_de_connexion_non_cherchable(self):
        self._marin("zorglub_login", "EQUIPIER", ship=self.navire, last_name="Martin")
        self.assertNotContains(self.chercher(self.equipier, "zorglub"), "Marin")
        self.assertContains(self.chercher(self.equipier, "Martin"), "Martin")

    def test_marin_sans_nom_ne_devoile_pas_son_identifiant(self):
        self._marin("anonyme_login", "EQUIPIER", ship=self.navire)
        self.assertNotContains(self.chercher(self.equipier, "anonyme"), "anonyme_login")
        User.objects.filter(username="anonyme_login").update(first_name="Zed")
        self.assertContains(self.chercher(self.equipier, "Zed"), "Zed")

    def test_compte_desactive_absent(self):
        parti = self._marin("parti", "EQUIPIER", ship=self.navire, last_name="Partivite")
        User.objects.filter(pk=parti.pk).update(is_active=False)
        self.assertNotContains(self.chercher(self.equipier, "Partivite"), "Partivite")
        self.assertNotContains(self.chercher(self.commandant, "Partivite"), "Partivite")

    def test_email_absent_des_resultats(self):
        User.objects.filter(pk=self.commandant.pk).update(email="secret.cdt@navy.fr")
        self.assertNotContains(self.chercher(self.equipier, "Zebrowski"), "secret.cdt")
        self.assertNotContains(self.chercher(self.equipier, "secret.cdt"), "Zebrowski")


class CategoriesTests(RechercheRapideTestCase):
    def test_resultats_regroupes_par_categorie_avec_sous_titre_et_lien(self):
        reponse = self.chercher(self.chef, "ZEBRE")
        for libelle in ("Installations", "Matériels", "Tickets correctifs", "Anomalies", "Formations"):
            self.assertContains(reponse, libelle)
        self.assertContains(reponse, "Secteur A")  # sous-titre d'une installation

    def test_module_desactive_masque_ses_categories(self):
        ModuleActivation.objects.create(ship=self.navire, module="assets", active=False)
        cache.clear()
        reponse = self.chercher(self.chef, "ZEBRE")
        self.assertNotContains(reponse, "Installations")
        self.assertNotContains(reponse, "Matériels")
        self.assertContains(reponse, "Tickets correctifs")

    def test_cinq_resultats_maximum_et_tout_voir(self):
        for i in range(7):
            Installation.objects.create(
                designation=f"Groupe LOT {i}", ship=self.navire, service=self.service, sector=self.secteur,
            )
        reponse = self.chercher(self.chef, "LOT")
        self.assertEqual(len(reponse.context["groupes"][0]["resultats"]), recherche.PAR_CATEGORIE)
        self.assertContains(reponse, reverse("installation-list") + "?q=LOT")

    def test_pas_de_tout_voir_sans_ecran_de_liste_filtrant(self):
        self.assertNotContains(self.chercher(self.chef, "ZEBRE"), "Tout voir : Formations")

    def test_aucun_resultat_utilise_etat_vide(self):
        reponse = self.chercher(self.chef, "introuvableXYZ")
        self.assertContains(reponse, "mx-vide")
        self.assertContains(reponse, 'data-nombre="0"')


class SaisieTests(RechercheRapideTestCase):
    def test_minimum_de_caracteres(self):
        reponse = self.chercher(self.chef, "z")
        self.assertContains(reponse, "au moins 2 caractères")
        self.assertEqual(reponse.context["groupes"], [])

    def test_caracteres_de_controle_retires(self):
        self.assertEqual(recherche.normaliser("ZE\x00BRE\x1f"), "ZEBRE")
        self.assertContains(self.chercher(self.chef, "ZE\x00BRE"), "Installations")

    def test_terme_vide_apres_nettoyage(self):
        for terme in ("\x00\x00", "   "):
            reponse = self.chercher(self.chef, terme)
            self.assertEqual(reponse.status_code, 200)
            self.assertEqual(reponse.context["groupes"], [])

    def test_longueur_maximale(self):
        self.assertEqual(len(recherche.normaliser("a" * 500)), recherche.MAX_CARACTERES)

    def test_caracteres_speciaux_sans_effet(self):
        Installation.objects.create(
            designation="Vanne 100% O'Brien_x", ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.assertContains(self.chercher(self.chef, "100%"), "Vanne 100%")
        self.assertContains(self.chercher(self.chef, "O'Brien"), "O&#x27;Brien")
        # « % » et « _ » ne sont pas des jokers : « Z%E » ne correspond à rien.
        self.assertNotContains(self.chercher(self.chef, "Z%E"), "ZEBRE")
        self.assertNotContains(self.chercher(self.chef, "Z_BRE"), "ZEBRE")

    def test_balise_script_echappee(self):
        Installation.objects.create(
            designation="<script>alert(1)</script>", ship=self.navire, service=self.service, sector=self.secteur,
        )
        reponse = self.chercher(self.chef, "<script>")
        self.assertNotContains(reponse, "<script>alert")
        self.assertContains(reponse, "&lt;script&gt;alert(1)")

    def test_anonyme_refuse(self):
        reponse = self.client.get(reverse(URL), {"q": "ZEBRE"})
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/login/", reponse["Location"])

    def test_methode_post_refusee(self):
        self.client.force_login(self.chef)
        self.assertEqual(self.client.post(reverse(URL), {"q": "ZEBRE"}).status_code, 405)


class PerformanceTests(RechercheRapideTestCase):
    def test_une_requete_par_categorie_au_plus(self):
        for i in range(5):
            Asset.objects.create(
                asset_type=self.type, internal_id=f"ZEBRE-N{i}", ship=self.navire, service=self.service,
                sector=self.secteur, section=self.section_1,
            )
        self.client.force_login(self.commandant)
        self.client.get(reverse(URL), {"q": "ZEBRE"})  # amorce le cache des modules
        with CaptureQueriesContext(connection) as requetes:
            self.client.get(reverse(URL), {"q": "ZEBRE"})
        # session + utilisateur + profil + navire + 6 catégories + marge.
        self.assertLessEqual(len(requetes), 11, [q["sql"][:80] for q in requetes])


class AccessibiliteTests(RechercheRapideTestCase):
    def test_champ_de_la_barre_est_un_combobox_libelle(self):
        self.client.force_login(self.chef)
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('role="combobox"', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('aria-controls="recherche-panneau"', html)
        self.assertIn('for="recherche-champ"', html)
        self.assertIn("(/ ou Ctrl+K)", html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('hx-trigger="input changed delay:250ms"', html)

    def test_anonyme_sans_champ_de_recherche(self):
        self.assertNotContains(self.client.get(reverse("login")), "recherche-champ")

    def test_resultats_en_listbox_avec_options(self):
        reponse = self.chercher(self.chef, "ZEBRE")
        self.assertContains(reponse, 'role="listbox"')
        self.assertContains(reponse, 'role="option"')
        self.assertContains(reponse, 'role="group"')
