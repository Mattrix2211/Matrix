"""Tests de l'interface web : création/affectation/publication d'une liste,
et désignation des chefs de liste."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import FonctionQuartChoice, ServiceFunctionChoice, UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from quarts.models import ChefDeListe, CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde


class CreationListeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Création", code="WCR")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre"
        )

        self.cdl = User.objects.create_user(username="cdl_creation", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)

        self.equipier = User.objects.create_user(username="equipier_creation", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

        # Fonction obligatoire par liste (correction de cadrage du 09/09/2026,
        # cf. docstring de quarts/models.py) : un référentiel distinct selon
        # le type de liste créée.
        self.fonction_quart = FonctionQuartChoice.objects.create(name="Barre")
        self.fonction_service = ServiceFunctionChoice.objects.create(name="Permanence")

    def _payload(self, action="creer_quart"):
        payload = {
            "action": action,
            "perimetre": f"sector:{self.sector.pk}",
            "nom": "Semaine test",
            "date_debut": str(timezone.localdate()),
            "date_fin": str(timezone.localdate() + timedelta(days=6)),
        }
        if action == "creer_quart":
            payload["fonction_quart"] = self.fonction_quart.pk
        else:
            payload["fonction_service"] = self.fonction_service.pk
        return payload

    def test_chef_de_liste_peut_creer_un_quart_sur_son_perimetre(self):
        self.client.login(username="cdl_creation", password="pass")
        r = self.client.post("/quarts/", self._payload("creer_quart"))
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(Quart.objects.filter(sector=self.sector, nom="Semaine test").exists())

    def test_chef_de_liste_peut_creer_un_service_de_garde_sur_son_perimetre(self):
        self.client.login(username="cdl_creation", password="pass")
        r = self.client.post("/quarts/", self._payload("creer_service_garde"))
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(ServiceGarde.objects.filter(sector=self.sector, nom="Semaine test").exists())

    def test_non_designe_ne_peut_pas_creer_de_liste(self):
        self.client.login(username="equipier_creation", password="pass")
        r = self.client.post("/quarts/", self._payload("creer_quart"))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Quart.objects.filter(sector=self.sector).exists())

    def test_chef_de_liste_ne_peut_pas_creer_sur_un_autre_perimetre(self):
        autre_secteur = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Autre service"), name="Autre secteur"
        )
        self.client.login(username="cdl_creation", password="pass")
        payload = self._payload("creer_quart")
        payload["perimetre"] = f"sector:{autre_secteur.pk}"
        r = self.client.post("/quarts/", payload)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Quart.objects.filter(sector=autre_secteur).exists())

    def test_index_liste_les_listes_du_chef_de_liste(self):
        Quart.objects.create(sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        self.client.login(username="cdl_creation", password="pass")
        r = self.client.get("/quarts/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["quarts"]), 1)


class GestionCreneauxEtPublicationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Gestion", code="WGE")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Machine"), name="Propulsion"
        )
        self.section = Section.objects.create(sector=self.sector, name="Turbines")

        self.cdl = User.objects.create_user(username="cdl_gestion", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)

        self.marin = User.objects.create_user(username="marin_gestion", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "section": self.section})

        self.marin_hors_perimetre = User.objects.create_user(username="marin_hors_gestion", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_hors_perimetre, defaults={"role": "EQUIPIER"})

        # Publicateur habilité (rôle distinct du chef de liste, cf. workflow
        # proposer -> valider/publier) : CHEF_SERVICE atteint le seuil
        # configurable par défaut (matrix/core/role_thresholds.py, action
        # "liste_service_publication"), et son périmètre personnel couvre
        # exactement celui de la liste.
        self.publicateur = User.objects.create_user(username="publicateur_gestion", password="pass")
        UserProfile.objects.update_or_create(
            user=self.publicateur, defaults={"role": "CHEF_SERVICE", "sector": self.sector}
        )

        self.quart = Quart.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )

    def test_chef_de_liste_peut_ajouter_un_creneau_avec_marin_du_perimetre(self):
        self.client.login(username="cdl_gestion", password="pass")
        debut = (timezone.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {
            "action": "ajouter_creneau", "poste": "Passerelle", "debut": debut, "marin": self.marin.pk,
        })
        self.assertEqual(r.status_code, 302, r.content)
        creneau = CreneauQuart.objects.get(quart=self.quart)
        self.assertEqual(creneau.marin, self.marin)
        # Durée par défaut appliquée (4h) faute de date de fin saisie.
        self.assertEqual(creneau.fin - creneau.debut, timedelta(hours=self.quart.duree_creneau_heures))

    def test_ne_peut_pas_affecter_un_marin_hors_perimetre(self):
        self.client.login(username="cdl_gestion", password="pass")
        debut = (timezone.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {
            "action": "ajouter_creneau", "poste": "Passerelle", "debut": debut, "marin": self.marin_hors_perimetre.pk,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(CreneauQuart.objects.filter(quart=self.quart).exists())

    def test_gestionnaire_non_designe_ne_peut_pas_modifier_la_liste(self):
        autre = User.objects.create_user(username="autre_gestion", password="pass")
        UserProfile.objects.update_or_create(user=autre, defaults={"role": "EQUIPIER"})
        self.client.login(username="autre_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "publier"})
        self.assertEqual(r.status_code, 400)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_BROUILLON)

    def test_chef_de_liste_peut_proposer_une_liste(self):
        self.client.login(username="cdl_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "proposer"})
        self.assertEqual(r.status_code, 302, r.content)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_PROPOSEE)
        self.assertEqual(self.quart.proposee_par, self.cdl)
        # Le publicateur habilité est notifié qu'une validation est attendue.
        self.assertTrue(Notification.objects.filter(user=self.publicateur, verb__icontains="à valider").exists())

    def test_chef_de_liste_seul_ne_peut_pas_publier_lui_meme(self):
        # Workflow proposer -> valider/publier (cahier des charges §34) : un
        # chef de liste qui n'a que le droit de proposer (ici rôle EQUIPIER)
        # ne peut pas publier lui-même, même désigné ChefDeListe.
        self.quart.proposer(self.cdl)
        self.client.login(username="cdl_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "publier"})
        self.assertEqual(r.status_code, 400)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_PROPOSEE)

    def test_publication_refusee_avant_l_etape_proposee(self):
        # Même un publicateur habilité ne peut pas publier un brouillon
        # directement : il doit d'abord être proposé.
        self.client.login(username="publicateur_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "publier"})
        self.assertEqual(r.status_code, 302, r.content)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_BROUILLON)

    def test_publication_via_le_web_notifie_le_marin_affecte(self):
        debut = timezone.now() + timedelta(hours=3)
        CreneauQuart.objects.create(quart=self.quart, poste="Passerelle", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        self.quart.proposer(self.cdl)
        self.client.login(username="publicateur_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "publier"})
        self.assertEqual(r.status_code, 302)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_PUBLIEE)
        self.assertEqual(self.quart.publiee_par, self.publicateur)
        self.assertTrue(Notification.objects.filter(user=self.marin).exists())
        # Une version horodatée est figée à la publication (cahier des
        # charges §31).
        self.assertEqual(self.quart.versions.count(), 1)
        self.assertEqual(self.quart.versions.first().numero, 1)

    def test_marin_du_perimetre_peut_lire_une_liste_publiee(self):
        self.quart.publier(self.cdl)
        self.client.login(username="marin_gestion", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["peut_gerer"])

    def test_marin_ne_peut_pas_lire_un_brouillon(self):
        self.client.login(username="marin_gestion", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(r.status_code, 400)

    def test_marin_hors_perimetre_ne_peut_pas_lire_une_liste_publiee(self):
        self.quart.publier(self.cdl)
        self.client.login(username="marin_hors_gestion", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(r.status_code, 400)


class DesignationChefDeListeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Désignation", code="WDS")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Service désignation"), name="Secteur désignation"
        )

        self.chef_service = User.objects.create_user(username="chef_service_dsg", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "sector": self.sector}
        )

        self.chef_secteur_autre_service = User.objects.create_user(username="chef_secteur_dsg_autre", password="pass")
        self.autre_service = Service.objects.create(ship=self.ship, name="Autre service désignation")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Autre secteur désignation")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_autre_service, defaults={"role": "CHEF_SERVICE", "sector": self.autre_secteur}
        )

        self.candidat = User.objects.create_user(username="candidat_dsg", password="pass")
        UserProfile.objects.update_or_create(
            user=self.candidat, defaults={"role": "EQUIPIER", "ship": self.ship, "sector": self.sector})

        self.equipier = User.objects.create_user(username="equipier_dsg", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

        self.commandant = User.objects.create_user(username="commandant_dsg", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT", "ship": self.ship})

    def test_chef_service_peut_designer_sur_son_propre_perimetre(self):
        self.client.login(username="chef_service_dsg", password="pass")
        r = self.client.post("/quarts/reglages/", {
            "action": "designer", "user_id": self.candidat.pk, "perimetre": f"sector:{self.sector.pk}",
        })
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(ChefDeListe.objects.filter(user=self.candidat, sector=self.sector).exists())

    def test_chef_service_ne_peut_pas_designer_hors_de_son_perimetre(self):
        self.client.login(username="chef_secteur_dsg_autre", password="pass")
        r = self.client.post("/quarts/reglages/", {
            "action": "designer", "user_id": self.candidat.pk, "perimetre": f"sector:{self.sector.pk}",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(ChefDeListe.objects.filter(user=self.candidat, sector=self.sector).exists())

    def test_equipier_ne_peut_pas_acceder_a_la_page_de_designation(self):
        self.client.login(username="equipier_dsg", password="pass")
        r = self.client.get("/quarts/reglages/")
        self.assertEqual(r.status_code, 403)

    def test_commandant_peut_designer_sur_nimporte_quel_perimetre(self):
        self.client.login(username="commandant_dsg", password="pass")
        r = self.client.post("/quarts/reglages/", {
            "action": "designer", "user_id": self.candidat.pk, "perimetre": f"sector:{self.autre_secteur.pk}",
        })
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(ChefDeListe.objects.filter(user=self.candidat, sector=self.autre_secteur).exists())

    def test_retirer_une_designation(self):
        cdl = ChefDeListe.objects.create(user=self.candidat, sector=self.sector)
        self.client.login(username="chef_service_dsg", password="pass")
        r = self.client.post("/quarts/reglages/", {"action": "retirer", "pk": cdl.pk})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ChefDeListe.objects.filter(pk=cdl.pk).exists())


class PlanningEtOngletsTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Planning", code="WPL")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre"
        )
        self.cdl = User.objects.create_user(username="cdl_planning", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)
        self.second = User.objects.create_user(username="second_planning", password="pass")
        UserProfile.objects.update_or_create(
            user=self.second, defaults={"role": "COMMANDANT_EN_SECOND", "ship": self.sector.service.ship})
        aujourdhui = timezone.localdate()
        self.garde = ServiceGarde.objects.create(
            sector=self.sector, date_debut=aujourdhui, date_fin=aujourdhui + timedelta(days=9),
        )
        debut = timezone.now() + timedelta(hours=3)
        CreneauServiceGarde.objects.create(
            service_garde=self.garde, poste="Coupée", debut=debut, fin=debut + timedelta(hours=4),
        )

    def test_brouillon_affiche_badge_et_publier_pour_le_chef(self):
        self.client.login(username="cdl_planning", password="pass")
        r = self.client.get(f"/quarts/garde/{self.garde.pk}/")
        self.assertContains(r, "BROUILLON")
        # Circuit proposer -> valider -> publier : le chef de liste propose, il ne publie pas seul.
        self.assertContains(r, "Proposer la publication")
        self.assertContains(r, 'id="creneau-ajout"')
        self.assertEqual(
            [c for c, _ in r.context["onglets"]], ["planning", "echanges", "equite", "historique", "parametres"]
        )
        self.assertGreaterEqual(len(r.context["semaines"]), 2)

    def test_lecture_seule_sans_action_ni_parametres(self):
        self.garde.publier(self.cdl)
        self.client.login(username="second_planning", password="pass")
        r = self.client.get(f"/quarts/garde/{self.garde.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Publier la liste")
        self.assertNotContains(r, 'id="creneau-ajout"')
        self.assertEqual([c for c, _ in r.context["onglets"]], ["planning", "echanges"])

    def test_liste_publiee_sans_action_de_publication(self):
        self.garde.publier(self.cdl)
        self.client.login(username="cdl_planning", password="pass")
        self.assertNotContains(self.client.get(f"/quarts/garde/{self.garde.pk}/"), "Publier la liste")

    def test_onglets_echanges_equite_parametres(self):
        self.client.login(username="cdl_planning", password="pass")
        for vue, texte in (("echanges", "Rien à traiter"), ("equite", "Équité des services"), ("parametres", "Règles des échanges")):
            with self.subTest(vue=vue):
                self.assertContains(self.client.get(f"/quarts/garde/{self.garde.pk}/?vue={vue}"), texte)

    def test_quart_na_pas_donglet_echanges_ni_equite(self):
        quart = Quart.objects.create(sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        self.client.login(username="cdl_planning", password="pass")
        r = self.client.get(f"/quarts/quart/{quart.pk}/?vue=equite")
        self.assertEqual(r.context["vue"], "planning")
        self.assertEqual([c for c, _ in r.context["onglets"]], ["planning", "historique", "parametres"])

    def test_equipage_a_terre_masque_les_actions(self):
        self.client.login(username="cdl_planning", password="pass")
        with patch("matrix.context_processors.equipage_a_terre_lecture_seule", return_value=True):
            self.cdl.profile.equipage = "B"
            self.cdl.profile.save()
            r = self.client.get(f"/quarts/garde/{self.garde.pk}/")
        self.assertNotContains(r, "Publier la liste")
        self.assertNotContains(r, 'id="creneau-ajout"')


class AssistantCreationListeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Assistant", code="WAS")
        service = Service.objects.create(ship=self.ship, name="Pont")
        self.sector = Sector.objects.create(service=service, name="Manœuvre")
        self.autre_secteur = Sector.objects.create(service=service, name="Veille")
        self.cdl = User.objects.create_user(username="cdl_assistant", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)
        self.fonction = FonctionQuartChoice.objects.create(name="Barre assistant")
        self.client.login(username="cdl_assistant", password="pass")

    def _suivant(self, etape, **champs):
        return self.client.post("/quarts/creer/", {"etape": etape, "action": "suivant", **champs})

    def test_etape_perimetre_supprimee_quand_unique_et_periode_preremplie(self):
        r = self.client.get("/quarts/creer/")
        self.assertEqual(r.context["etapes"], ["Type", "Période", "Règles", "Vérification"])
        self.assertContains(r, 'data-brouillon="quarts:nouvelle-liste"')
        self.assertTrue(r.context["valeurs"]["date_debut"])

    def test_etape_perimetre_presente_si_plusieurs_choix(self):
        ChefDeListe.objects.create(user=self.cdl, sector=self.autre_secteur)
        r = self.client.get("/quarts/creer/")
        self.assertIn("Périmètre", r.context["etapes"])

    def test_parcours_complet_cree_le_brouillon(self):
        donnees = {
            "type_liste": "creer_quart", "date_debut": "2026-11-02", "date_fin": "2026-11-08",
            "fonction_quart": self.fonction.pk, "nom": "Semaine 45",
        }
        r = self._suivant(1, **donnees)
        self.assertEqual(r.context["cle_etape"], "periode")
        r = self._suivant(2, **donnees)
        self.assertEqual(r.context["cle_etape"], "regles")
        r = self._suivant(3, **donnees)
        self.assertEqual(r.context["cle_etape"], "verification")
        self.assertEqual(r.context["synthese"]["fonction"], self.fonction)
        r = self._suivant(4, **donnees)
        quart = Quart.objects.get(nom="Semaine 45")
        self.assertRedirects(r, f"/quarts/quart/{quart.pk}/")
        self.assertEqual(quart.statut, Quart.STATUT_BROUILLON)
        self.assertEqual(quart.sector, self.sector)

    def test_precedent_conserve_la_saisie(self):
        r = self.client.post("/quarts/creer/", {
            "etape": 3, "action": "precedent", "type_liste": "creer_quart",
            "date_debut": "2026-11-02", "date_fin": "2026-11-08",
        })
        self.assertEqual(r.context["cle_etape"], "periode")
        self.assertEqual(r.context["valeurs"]["date_debut"], "2026-11-02")

    def test_etape_invalide_reste_sur_l_etape(self):
        r = self._suivant(2, type_liste="creer_quart", date_debut="2026-11-08", date_fin="2026-11-02")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.context["cle_etape"], "periode")
        r = self._suivant(3, type_liste="creer_quart", date_debut="2026-11-02", date_fin="2026-11-08")
        self.assertEqual(r.context["cle_etape"], "regles")

    def test_non_designe_refuse(self):
        User.objects.create_user(username="simple_assistant", password="pass")
        self.client.login(username="simple_assistant", password="pass")
        self.assertEqual(self.client.get("/quarts/creer/").status_code, 403)
        self.assertEqual(self.client.post("/quarts/creer/", {"etape": 4}).status_code, 403)

    def test_perimetre_hors_droits_refuse(self):
        ChefDeListe.objects.create(user=self.cdl, sector=self.autre_secteur)
        r = self._suivant(5, type_liste="creer_quart", perimetre="sector:999999", date_debut="2026-11-02",
                          date_fin="2026-11-08", fonction_quart=self.fonction.pk)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.context["cle_etape"], "perimetre")
        self.assertFalse(Quart.objects.exists())
