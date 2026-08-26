"""Tests des catégories de formation (domaine métier) : champ `category` sur
TrainingCourse, autocomplétion dans le formulaire de gestion des formations,
et regroupement par catégorie dans l'arbre de compétences. Catalogue devenu
global (tâche Notion « Formation unique et portable entre navires ») : les
catégories proposées le sont pour l'ENSEMBLE du catalogue, plus par secteur."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from training.models import TrainingCourse, TrainingRecord
from training.services import (
    CATEGORIE_NON_RENSEIGNEE,
    calculer_carte_competences,
    regrouper_par_categorie,
    regrouper_par_composantes_connexes,
)


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class ChampCategorieTests(TestCase):
    """Le champ `category` doit être du texte libre, facultatif et rétrocompatible
    (même pattern que AssetType.category, cf. assets/models.py)."""

    def test_champ_facultatif_valeur_par_defaut_vide(self):
        formation = TrainingCourse.objects.create(title="Sans catégorie")
        formation.refresh_from_db()
        self.assertEqual(formation.category, "")

    def test_champ_accepte_du_texte_libre(self):
        formation = TrainingCourse.objects.create(
            title="Habilitation électrique niveau 1", category="Habilitation électrique",
        )
        formation.refresh_from_db()
        self.assertEqual(formation.category, "Habilitation électrique")

    def test_definition_du_champ_blank_et_default(self):
        champ = TrainingCourse._meta.get_field("category")
        self.assertTrue(champ.blank)
        self.assertEqual(champ.default, "")


class AutocompletionCategorieTests(TestCase):
    """Le formulaire de gestion des formations doit proposer, via un datalist,
    toutes les catégories déjà utilisées dans le catalogue (global)."""

    def setUp(self):
        TrainingCourse.objects.create(title="Extinction niveau 1", category="Incendie")
        TrainingCourse.objects.create(title="Extinction niveau 2", category="Incendie")
        TrainingCourse.objects.create(title="Évacuation", category="Sécurité générale")
        TrainingCourse.objects.create(title="Non catégorisée")

        self.chef = User.objects.create_user(username="chef_cat", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION"})

    def test_categories_proposees_sans_doublon(self):
        self.client.login(username="chef_cat", password="pass")
        r = self.client.get("/formations/")
        self.assertEqual(r.context["categories_existantes"], ["Incendie", "Sécurité générale"])

    def test_datalist_presente_dans_le_html(self):
        self.client.login(username="chef_cat", password="pass")
        r = self.client.get("/formations/")
        self.assertContains(r, "categoriesToutes")
        self.assertContains(r, "Incendie")

    def test_filtre_par_categorie(self):
        self.client.login(username="chef_cat", password="pass")
        r = self.client.get("/formations/", {"category": "Incendie"})
        titres = [f.title for f in r.context["formations"]]
        self.assertCountEqual(titres, ["Extinction niveau 1", "Extinction niveau 2"])

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
    tout le catalogue, seul l'affichage doit être réparti par catégorie puis,
    au sein de chaque catégorie, par composante connexe (branches de
    prérequis totalement indépendantes les unes des autres, cf.
    regrouper_par_composantes_connexes) — d'où la structure imbriquée
    (nom_categorie, composantes) où `composantes` est une liste de listes de
    niveaux (une entrée par composante)."""

    def setUp(self):
        self.incendie_1 = TrainingCourse.objects.create(title="Extinction niveau 1", category="Incendie")
        self.incendie_2 = TrainingCourse.objects.create(title="Extinction niveau 2", category="Incendie")
        self.incendie_2.prerequisites.set([self.incendie_1])
        self.secours = TrainingCourse.objects.create(title="Secourisme de base", category="Secourisme")
        self.sans_categorie = TrainingCourse.objects.create(title="Sans domaine")
        self.marin = User.objects.create_user(username="marin_regroupe", password="pass")

    def _carte(self):
        formations = list(TrainingCourse.objects.all().prefetch_related("prerequisites"))
        return calculer_carte_competences(formations, self.marin)

    @staticmethod
    def _ids_du_groupe(composantes):
        """Aplatit une entrée (composantes) de regrouper_par_categorie en une
        liste d'identifiants de formation, tous niveaux et composantes
        confondus — pratique pour les assertions qui ne portent pas sur la
        disposition en sous-colonnes elle-même."""
        return [
            item["course"].id
            for niveaux in composantes
            for _, items in niveaux
            for item in items
        ]

    def test_groupes_tries_par_ordre_alphabetique(self):
        groupes = regrouper_par_categorie(self._carte())
        noms = [nom for nom, _ in groupes]
        self.assertEqual(noms, ["Incendie", "Secourisme", CATEGORIE_NON_RENSEIGNEE])

    def test_formation_sans_categorie_dans_le_groupe_non_categorisees(self):
        groupes = regrouper_par_categorie(self._carte())
        groupe_non_categorise = dict(groupes)[CATEGORIE_NON_RENSEIGNEE]
        self.assertEqual(self._ids_du_groupe(groupe_non_categorise), [self.sans_categorie.id])

    def test_niveau_conserve_a_travers_les_groupes(self):
        # Le niveau de "Extinction niveau 2" doit rester 1 même une fois
        # isolé dans son groupe de catégorie (et sa composante connexe).
        groupes = regrouper_par_categorie(self._carte())
        groupe_incendie = dict(groupes)["Incendie"]
        niveaux_par_id = {
            item["course"].id: niveau
            for niveaux in groupe_incendie
            for niveau, items in niveaux
            for item in items
        }
        self.assertEqual(niveaux_par_id[self.incendie_1.id], 0)
        self.assertEqual(niveaux_par_id[self.incendie_2.id], 1)

    def test_incendie_reste_une_seule_composante(self):
        # "Extinction niveau 1" et "Extinction niveau 2" sont reliées par un
        # prérequis : une seule composante connexe (une seule sous-colonne)
        # pour la catégorie Incendie, pas deux.
        groupes = regrouper_par_categorie(self._carte())
        groupe_incendie = dict(groupes)["Incendie"]
        self.assertEqual(len(groupe_incendie), 1)

    def test_aucune_formation_perdue_ni_dupliquee(self):
        groupes = regrouper_par_categorie(self._carte())
        toutes_les_ids = []
        for _, composantes in groupes:
            toutes_les_ids.extend(self._ids_du_groupe(composantes))
        self.assertCountEqual(
            toutes_les_ids,
            [self.incendie_1.id, self.incendie_2.id, self.secours.id, self.sans_categorie.id],
        )


class ComposantesConnexesTests(TestCase):
    """training.services.regrouper_par_composantes_connexes : deux formations
    d'une même catégorie sans AUCUN lien de prérequis entre elles (même
    transitif) doivent être placées dans deux composantes distinctes, pour
    être affichées en sous-colonnes côte à côte plutôt qu'empilées
    verticalement (complément du bug « les formations de branches différentes
    s'empilent » — confirmé par l'utilisateur : « en fait les deux », valable
    aussi bien entre catégories qu'à l'intérieur d'une même catégorie)."""

    def setUp(self):
        self.secourisme_1 = TrainingCourse.objects.create(title="Secourisme niveau 1", category="Secourisme")
        self.secourisme_2 = TrainingCourse.objects.create(title="Secourisme niveau 2", category="Secourisme")
        self.secourisme_2.prerequisites.set([self.secourisme_1])
        # Deux formations de la même catégorie, sans aucun lien de prérequis
        # avec la chaîne secourisme_1 -> secourisme_2 ci-dessus.
        self.plongee = TrainingCourse.objects.create(title="Plongée niveau 1", category="Secourisme")
        self.marin = User.objects.create_user(username="marin_composantes", password="pass")

    def _carte(self):
        formations = list(TrainingCourse.objects.all().prefetch_related("prerequisites"))
        return calculer_carte_competences(formations, self.marin)

    def test_deux_formations_independantes_dans_des_composantes_distinctes(self):
        groupes = regrouper_par_categorie(self._carte())
        groupe_secourisme = dict(groupes)["Secourisme"]
        # Deux composantes connexes : {secourisme_1, secourisme_2} et {plongee}.
        self.assertEqual(len(groupe_secourisme), 2)
        ids_par_composante = [
            {item["course"].id for _, items in niveaux for item in items}
            for niveaux in groupe_secourisme
        ]
        self.assertIn({self.secourisme_1.id, self.secourisme_2.id}, ids_par_composante)
        self.assertIn({self.plongee.id}, ids_par_composante)

    def test_formations_reliees_par_prerequis_dans_la_meme_composante(self):
        carte = self._carte()
        composantes = regrouper_par_composantes_connexes(carte)
        # Une seule composante ici : le seul lien de prérequis relie déjà
        # secourisme_1 et secourisme_2 (la plongée reste bien séparée).
        composante_avec_secourisme_1 = next(
            c for c in composantes if any(item["course"].id == self.secourisme_1.id for item in c)
        )
        ids = {item["course"].id for item in composante_avec_secourisme_1}
        self.assertEqual(ids, {self.secourisme_1.id, self.secourisme_2.id})


class ArbreCompetencesParCategorieVueTests(TestCase):
    """Rendu HTML de l'arbre de compétences : sections par catégorie, badge
    de repère quand un prérequis appartient à une autre catégorie."""

    def setUp(self):
        self.base_secourisme = TrainingCourse.objects.create(title="Secourisme niveau 1", category="Secourisme")
        self.avance_incendie = TrainingCourse.objects.create(title="Chef d'équipe incendie", category="Incendie")
        # Prérequis traversant les catégories : Secourisme -> Incendie.
        self.avance_incendie.prerequisites.set([self.base_secourisme])
        self.non_categorisee = TrainingCourse.objects.create(title="Stage divers")

        self.chef = User.objects.create_user(username="chef_arbre", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION"})

    def test_sections_par_categorie_affichees(self):
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Secourisme")
        self.assertContains(r, "Incendie")
        self.assertContains(r, CATEGORIE_NON_RENSEIGNEE)

    def test_formation_non_categorisee_toujours_visible(self):
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertContains(r, "Stage divers")

    def test_badge_vers_categorie_du_prerequis_different(self):
        # "Chef d'équipe incendie" (catégorie Incendie) a pour prérequis
        # manquant une formation de la catégorie Secourisme : un repère visuel
        # doit pointer vers cette catégorie.
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertContains(r, 'href="#cat-secourisme"')

    def test_prerequis_valide_de_meme_categorie_sans_badge_croise(self):
        # Deux formations de la même catégorie : pas de badge de renvoi
        # nécessaire (le prérequis est déjà visible dans la même section).
        autre = TrainingCourse.objects.create(title="Secourisme niveau 2", category="Secourisme")
        autre.prerequisites.set([self.base_secourisme])
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        # Le badge ne doit apparaître que pour le prérequis inter-catégories,
        # pas pour "Secourisme niveau 2" -> "Secourisme niveau 1" (même catégorie).
        self.assertContains(r, 'href="#cat-secourisme"', count=1)

    def test_contexte_categories_regroupe_correctement(self):
        TrainingRecord.objects.create(
            user=self.chef, course=self.base_secourisme,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        noms = [nom for nom, _ in r.context["categories"]]
        self.assertEqual(noms, ["Incendie", "Secourisme", CATEGORIE_NON_RENSEIGNEE])

    def test_categories_disposees_cote_a_cote_pas_empilees(self):
        # Bug signalé : les catégories (branches indépendantes) s'empilaient
        # verticalement. Elles doivent maintenant être regroupées dans un
        # conteneur unique disposé en colonnes parallèles (arbre-categories),
        # qui enveloppe bien toutes les sections de catégorie plutôt que de
        # les laisser s'enchaîner comme des blocs indépendants dans la page.
        self.client.login(username="chef_arbre", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        html = r.content.decode()
        debut_conteneur = html.find('<div class="arbre-categories">')
        derniere_section = html.rfind('<section class="arbre-categorie"')
        debut_script = html.find("arbre_competences.js")
        self.assertNotEqual(debut_conteneur, -1)
        # Chaque section de catégorie doit être ouverte après le conteneur...
        self.assertGreater(derniere_section, debut_conteneur)
        # ...et le conteneur ne doit se refermer qu'après la dernière section,
        # donc juste avant le script des connecteurs de l'arbre.
        self.assertIn("</div>", html[derniere_section:debut_script])
