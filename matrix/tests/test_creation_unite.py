"""Tests de la création/modification d'une unité (Ship) avec son type, depuis
l'onglet « Unités » des Réglages (/parametre/?tab=navires).

Tâche Notion « [FEAT] Renommer « Navire » en « Unité » avec typage » : une
unité n'est pas forcément un navire opérationnel (école, centre de formation,
bureau à terre...). Le nom de code Python (Ship, ship, ship_id...) reste
inchangé — seul le vocabulaire affiché à l'utilisateur devient « Unité »."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from org.models import Ship


class TypeUniteModeleTests(TestCase):
    """Le champ type_unite doit rester rétrocompatible : toute unité déjà
    existante (créée avant cette tâche) doit être considérée comme un navire
    par défaut, sans action manuelle."""

    def test_type_unite_par_defaut_est_navire(self):
        unite = Ship.objects.create(name="Richelieu", code="RIC")
        self.assertEqual(unite.type_unite, Ship.TypeUnite.NAVIRE)

    def test_on_peut_creer_une_unite_de_type_ecole(self):
        unite = Ship.objects.create(name="École de Maistrance", code="EM", type_unite=Ship.TypeUnite.ECOLE)
        self.assertEqual(unite.type_unite, "ECOLE")
        self.assertEqual(unite.get_type_unite_display(), "École")

    def test_les_quatre_types_d_unite_sont_disponibles(self):
        codes = {code for code, _ in Ship.TypeUnite.choices}
        self.assertEqual(codes, {"NAVIRE", "ECOLE", "CENTRE_FORMATION", "BUREAU"})


class CreationUniteViaReglagesTests(TestCase):
    """La création d'une unité, réservée aux superusers Django, doit permettre
    de choisir son type directement dans le même formulaire (principe « plus
    rapide qu'Excel » : pas d'étape supplémentaire)."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_test", email="admin@navy.fr", password="pass",
        )
        self.url = reverse("settings")

    def test_creation_d_une_unite_avec_type_ecole(self):
        self.client.login(username="admin_test", password="pass")
        response = self.client.post(self.url, {
            "action": "add_ship",
            "name": "Centre de formation Cherbourg",
            "code": "CFC",
            "type_unite": "CENTRE_FORMATION",
            "next_tab": "navires",
        })
        self.assertEqual(response.status_code, 302)
        unite = Ship.objects.get(code="CFC")
        self.assertEqual(unite.type_unite, "CENTRE_FORMATION")

    def test_creation_sans_type_unite_precise_retombe_sur_navire(self):
        self.client.login(username="admin_test", password="pass")
        self.client.post(self.url, {
            "action": "add_ship",
            "name": "Surcouf",
            "code": "SUR",
            "next_tab": "navires",
        })
        unite = Ship.objects.get(code="SUR")
        self.assertEqual(unite.type_unite, Ship.TypeUnite.NAVIRE)

    def test_modification_du_type_d_une_unite_existante(self):
        unite = Ship.objects.create(name="Jean Bart", code="JB")
        self.client.login(username="admin_test", password="pass")
        response = self.client.post(self.url, {
            "action": "edit_ship",
            "pk": unite.pk,
            "name": "Jean Bart",
            "code": "JB",
            "type_unite": "BUREAU",
            "next_tab": "navires",
        })
        self.assertEqual(response.status_code, 302)
        unite.refresh_from_db()
        self.assertEqual(unite.type_unite, "BUREAU")

    def test_onglet_unites_affiche_les_choix_de_type(self):
        self.client.login(username="admin_test", password="pass")
        response = self.client.get(self.url, {"tab": "navires"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "École")
        self.assertContains(response, "Centre de formation")
        self.assertContains(response, "Bureau")


class ClasseNavireTests(TestCase):
    """Tâche « [FEAT] Champs complémentaires : NNO (pièces), classe de navire » :
    champ optionnel, texte libre (pas de liste fermée : nomenclature propre à
    la Marine Nationale que l'utilisateur remplit lui-même)."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_classe", email="admin_classe@navy.fr", password="pass",
        )
        self.url = reverse("settings")

    def test_creation_avec_classe_de_navire(self):
        self.client.login(username="admin_classe", password="pass")
        self.client.post(self.url, {
            "action": "add_ship", "name": "Aquitaine", "code": "AQU",
            "classe_navire": "Frégate La Fayette", "next_tab": "navires",
        })
        unite = Ship.objects.get(code="AQU")
        self.assertEqual(unite.classe_navire, "Frégate La Fayette")

    def test_creation_sans_classe_de_navire_reste_vide(self):
        # Rétrocompatibilité : les unités déjà existantes (créées avant cette
        # tâche) doivent avoir une chaîne vide, pas None, sans action manuelle.
        self.client.login(username="admin_classe", password="pass")
        self.client.post(self.url, {
            "action": "add_ship", "name": "Surcouf II", "code": "SU2", "next_tab": "navires",
        })
        unite = Ship.objects.get(code="SU2")
        self.assertEqual(unite.classe_navire, "")

    def test_modification_de_la_classe_de_navire(self):
        unite = Ship.objects.create(name="Suffren", code="SUF")
        self.client.login(username="admin_classe", password="pass")
        response = self.client.post(self.url, {
            "action": "edit_ship", "pk": unite.pk, "name": "Suffren", "code": "SUF",
            "classe_navire": "Sous-marin nucléaire d'attaque type Suffren", "next_tab": "navires",
        })
        self.assertEqual(response.status_code, 302)
        unite.refresh_from_db()
        self.assertEqual(unite.classe_navire, "Sous-marin nucléaire d'attaque type Suffren")

    def test_commentaire_dev_classe_navire_non_affiche_en_clair(self):
        """Régression : le commentaire {# ... #} multi-lignes expliquant
        l'absence de la classe de navire dans le tableau compact s'affichait
        en clair, faute d'être invisible avec {% comment %}...{% endcomment %}."""
        self.client.login(username="admin_classe", password="pass")
        response = self.client.get(self.url, {"tab": "navires"})
        self.assertNotContains(response, "n'est pas affichée dans ce tableau compact")
