"""Tests des catégories de formation (domaine métier) : champ `category` sur
TrainingCourse, autocomplétion dans le formulaire de gestion des formations,
et regroupement par catégorie dans l'arbre de compétences."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from training.models import TrainingCourse, TrainingRecord
from training.services import (
    CATEGORIE_NON_RENSEIGNEE,
    calculer_carte_competences,
    regrouper_par_categorie,
)


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class ChampCategorieTests(TestCase):
    """Le champ `category` doit être du texte libre, facultatif et rétrocompatible
    (même pattern que AssetType.category, cf. assets/models.py)."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Cat", code="CAT")
        service = Service.objects.create(ship=ship, name="Technique")
        self.sector = Sector.objects.create(service=service, name="Électricité")

    def test_champ_facultatif_valeur_par_defaut_vide(self):
        formation = TrainingCourse.objects.create(sector=self.sector, title="Sans catégorie")
        formation.refresh_from_db()
        self.assertEqual(formation.category, "")

    def test_champ_accepte_du_texte_libre(self):
        formation = TrainingCourse.objects.create(
            sector=self.sector, title="Habilitation électrique niveau 1", category="Habilitation électrique",
        )
        formation.refresh_from_db()
        self.assertEqual(formation.category, "Habilitation électrique")

    def test_definition_du_champ_blank_et_default(self):
        champ = TrainingCourse._meta.get_field("category")
        self.assertTrue(champ.blank)
        self.assertEqual(champ.default, "")


class AutocompletionCategorieTests(TestCase):
    """Le formulaire de gestion des formations doit proposer, via un datalist,
    les catégories déjà utilisées dans le secteur — sans fuite d'un autre secteur."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Auto", code="AUT")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Incendie")
        self.autre_sector = Sector.objects.create(service=service, name="Autre secteur")
        TrainingCourse.objects.create(sector=self.sector, title="Extinction niveau 1", category="Incendie")
        TrainingCourse.objects.create(sector=self.sector, title="Extinction niveau 2", category="Incendie")
        TrainingCourse.objects.create(sector=self.sector, title="Évacuation", category="Sécurité générale")
        TrainingCourse.objects.create(sector=self.sector, title="Non catégorisée")
        TrainingCourse.objects.create(sector=self.autre_sector, title="Ailleurs", category="Levage")

        self.chef = User.objects.create_user(username="chef_cat", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION"})

    def test_categories_proposees_sont_celles_du_secteur_sans_doublon(self):
        self.client.login(username="chef_cat", password="pass")
        r = self.client.get("/formations/")
        categories = r.context["categories_par_secteur"].get(self.sector.id, [])
        self.assertEqual(categories, ["Incendie", "Sécurité générale"])

    def test_categorie_dun_autre_secteur_non_proposee(self):
        self.client.login(username="chef_cat", password="pass")
        r = self.client.get("/formations/")
        categories = r.context["categories_par_secteur"].get(self.sector.id, [])
        self.assertNotIn("Levage", categories)

    def test_datalist_presente_dans_le_html(self):
        self.client.login(username="chef_cat", password="pass")
        r = self.client.get("/formations/")
        self.assertContains(r, f"categoriesSecteur-{self.sector.id}")
        self.assertContains(r, "Incendie")

    def test_chef_peut_modifier_la_categorie_dune_formation(self):
        formation = TrainingCourse.objects.get(title="Non catégorisée")
        self.client.login(username="chef_cat", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": formation.id,
            "category": "Sécurité générale",
        })
        self.assertEqual(r.status_code, 302)
        formation.refresh_from_db()
        self.assertEqual(formation.category, "Sécurité générale")

    def test_categorie_non_touchee_si_champ_absent_du_post(self):
        # Compatibilité : un appel qui ne fournit pas "category" (ex. anciens
        # tests de prérequis) ne doit pas effacer la catégorie existante.
        formation = TrainingCourse.objects.get(title="Extinction niveau 1")
        self.client.login(username="chef_cat", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": formation.id,
        })
        self.assertEqual(r.status_code, 302)
        formation.refresh_from_db()
        self.assertEqual(formation.category, "Incendie")


class RegroupementParCategorieTests(TestCase):
    """training.services.regrouper_par_categorie : le graphe est calculé sur
    tout le secteur, seul l'affichage doit être réparti par catégorie."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Regroupe", code="REG")
        service = Service.objects.create(ship=ship, name="Machines")
        self.sector = Sector.objects.create(service=service, name="Propulsion")
        self.incendie_1 = TrainingCourse.objects.create(
            sector=self.sector, title="Extinction niveau 1", category="Incendie",
        )
        self.incendie_2 = TrainingCourse.objects.create(
            sector=self.sector, title="Extinction niveau 2", category="Incendie",
        )
        self.incendie_2.prerequisites.set([self.incendie_1])
        self.secours = TrainingCourse.objects.create(
            sector=self.sector, title="Secourisme de base", category="Secourisme",
        )
        self.sans_categorie = TrainingCourse.objects.create(sector=self.sector, title="Sans domaine")
        self.marin = User.objects.create_user(username="marin_regroupe", password="pass")

    def _carte(self):
        formations = list(
            TrainingCourse.objects.filter(sector=self.sector).prefetch_related("prerequisites")
        )
        return calculer_carte_competences(formations, self.marin)

    def test_groupes_tries_par_ordre_alphabetique(self):
        groupes = regrouper_par_categorie(self._carte())
        noms = [nom for nom, _ in groupes]
        self.assertEqual(noms, ["Incendie", "Secourisme", CATEGORIE_NON_RENSEIGNEE])

    def test_formation_sans_categorie_dans_le_groupe_non_categorisees(self):
        groupes = regrouper_par_categorie(self._carte())
        groupe_non_categorise = dict(groupes)[CATEGORIE_NON_RENSEIGNEE]
        ids = [item["course"].id for _, items in groupe_non_categorise for item in items]
        self.assertEqual(ids, [self.sans_categorie.id])

    def test_niveau_conserve_a_travers_les_groupes(self):
        # Le niveau de "Extinction niveau 2" (calculé sur tout le secteur) doit
        # rester 1 même une fois isolé dans son groupe de catégorie.
        groupes = regrouper_par_categorie(self._carte())
        groupe_incendie = dict(groupes)["Incendie"]
        niveaux_par_id = {
            item["course"].id: niveau for niveau, items in groupe_incendie for item in items
        }
        self.assertEqual(niveaux_par_id[self.incendie_1.id], 0)
        self.assertEqual(niveaux_par_id[self.incendie_2.id], 1)

    def test_aucune_formation_perdue_ni_dupliquee(self):
        groupes = regrouper_par_categorie(self._carte())
        toutes_les_ids = [
            item["course"].id for _, niveaux in groupes for _, items in niveaux for item in items
        ]
        self.assertCountEqual(
            toutes_les_ids,
            [self.incendie_1.id, self.incendie_2.id, self.secours.id, self.sans_categorie.id],
        )


class ArbreCompetencesParCategorieVueTests(TestCase):
    """Rendu HTML de l'arbre de compétences : sections par catégorie, badge
    de repère quand un prérequis appartient à une autre catégorie."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Arbre", code="ARB")
        service = Service.objects.create(ship=ship, name="Sécurité")
        self.sector = Sector.objects.create(service=service, name="Prévention")
        self.base_secourisme = TrainingCourse.objects.create(
            sector=self.sector, title="Secourisme niveau 1", category="Secourisme",
        )
        self.avance_incendie = TrainingCourse.objects.create(
            sector=self.sector, title="Chef d'équipe incendie", category="Incendie",
        )
        # Prérequis traversant les catégories : Secourisme -> Incendie.
        self.avance_incendie.prerequisites.set([self.base_secourisme])
        self.non_categorisee = TrainingCourse.objects.create(sector=self.sector, title="Stage divers")

        self.chef = User.objects.create_user(username="chef_arbre", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION"})

    def test_sections_par_categorie_affichees(self):
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get(f"/formations/arbre-competences/?secteur={self.sector.id}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Secourisme")
        self.assertContains(r, "Incendie")
        self.assertContains(r, CATEGORIE_NON_RENSEIGNEE)

    def test_formation_non_categorisee_toujours_visible(self):
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get(f"/formations/arbre-competences/?secteur={self.sector.id}")
        self.assertContains(r, "Stage divers")

    def test_badge_vers_categorie_du_prerequis_different(self):
        # "Chef d'équipe incendie" (catégorie Incendie) a pour prérequis
        # manquant une formation de la catégorie Secourisme : un repère visuel
        # doit pointer vers cette catégorie.
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get(f"/formations/arbre-competences/?secteur={self.sector.id}")
        self.assertContains(r, 'href="#cat-secourisme"')

    def test_prerequis_valide_de_meme_categorie_sans_badge_croise(self):
        # Deux formations de la même catégorie : pas de badge de renvoi
        # nécessaire (le prérequis est déjà visible dans la même section).
        autre = TrainingCourse.objects.create(
            sector=self.sector, title="Secourisme niveau 2", category="Secourisme",
        )
        autre.prerequisites.set([self.base_secourisme])
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get(f"/formations/arbre-competences/?secteur={self.sector.id}")
        # Le badge ne doit apparaître que pour le prérequis inter-catégories,
        # pas pour "Secourisme niveau 2" -> "Secourisme niveau 1" (même catégorie).
        self.assertContains(r, 'href="#cat-secourisme"', count=1)

    def test_contexte_categories_regroupe_correctement(self):
        TrainingRecord.objects.create(
            user=self.chef, course=self.base_secourisme,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get(f"/formations/arbre-competences/?secteur={self.sector.id}")
        noms = [nom for nom, _ in r.context["categories"]]
        self.assertEqual(noms, ["Incendie", "Secourisme", CATEGORIE_NON_RENSEIGNEE])
