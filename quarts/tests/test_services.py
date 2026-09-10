"""Tests du compteur d'équité par marin sur les services de garde (Phase 2,
tâche Notion « Services/gardes : compteur d'équité par marin »)."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Sector, Section, Service, Ship
from quarts.models import ChefDeListe, CreneauServiceGarde, ServiceGarde
from quarts.services import (
    CATEGORIE_SEMAINE,
    CATEGORIE_VENDREDI,
    CATEGORIE_WEEKEND,
    compteur_equite_marin,
    compteurs_equite_perimetre,
)


def _aware(annee, mois, jour, heure=8):
    return timezone.make_aware(timezone.datetime(annee, mois, jour, heure))


class CalculCompteurTests(TestCase):
    """Vérifie le calcul des 3 catégories, l'exclusion des brouillons et les
    deux périodes (mois en cours / année en cours)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Équité", code="EQT")
        self.marin = User.objects.create_user(username="marin_equite", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        # Date de référence figée pour des tests déterministes, indépendants
        # du jour d'exécution (mardi 08/09/2026, milieu de mois et d'année).
        self.aujourdhui = date(2026, 9, 8)

        self.garde = ServiceGarde.objects.create(
            ship=self.ship, date_debut=self.aujourdhui, date_fin=self.aujourdhui + timedelta(days=60),
        )

    def _creneau(self, quand, publiee=True, marin=None):
        garde = self.garde
        if not publiee:
            garde = ServiceGarde.objects.create(
                ship=self.ship, date_debut=self.aujourdhui, date_fin=self.aujourdhui + timedelta(days=60),
            )
        creneau = CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Garde 24h", debut=quand, fin=quand + timedelta(hours=24),
            marin=marin or self.marin,
        )
        return creneau

    def test_trois_categories_correctement_reparties(self):
        # Mardi 08/09/2026 -> semaine ; vendredi 11/09/2026 -> vendredi ;
        # samedi 12/09/2026 et dimanche 13/09/2026 -> week-end.
        self._creneau(_aware(2026, 9, 8))
        self._creneau(_aware(2026, 9, 9))
        self._creneau(_aware(2026, 9, 11))
        self._creneau(_aware(2026, 9, 12))
        self._creneau(_aware(2026, 9, 13))
        self.garde.publier(self.marin)

        compteur = compteur_equite_marin(self.marin, aujourdhui=self.aujourdhui)
        self.assertEqual(compteur["mois"][CATEGORIE_SEMAINE], 2)
        self.assertEqual(compteur["mois"][CATEGORIE_VENDREDI], 1)
        self.assertEqual(compteur["mois"][CATEGORIE_WEEKEND], 2)

    def test_creneau_de_liste_brouillon_est_exclu(self):
        self._creneau(_aware(2026, 9, 8), publiee=False)
        # La garde brouillon n'est jamais publiée.
        compteur = compteur_equite_marin(self.marin, aujourdhui=self.aujourdhui)
        self.assertEqual(compteur["mois"][CATEGORIE_SEMAINE], 0)
        self.assertEqual(compteur["annee"][CATEGORIE_SEMAINE], 0)

    def test_creneau_publie_est_compte(self):
        self._creneau(_aware(2026, 9, 8))
        self.garde.publier(self.marin)
        compteur = compteur_equite_marin(self.marin, aujourdhui=self.aujourdhui)
        self.assertEqual(compteur["mois"][CATEGORIE_SEMAINE], 1)

    def test_periode_mois_exclut_les_creneaux_hors_mois(self):
        # Même année, mois différent (août) : ne doit compter que dans "annee".
        self._creneau(_aware(2026, 8, 10))
        self.garde.publier(self.marin)
        compteur = compteur_equite_marin(self.marin, aujourdhui=self.aujourdhui)
        self.assertEqual(sum(compteur["mois"].values()), 0)
        self.assertEqual(sum(compteur["annee"].values()), 1)

    def test_periode_annee_exclut_les_creneaux_dune_autre_annee(self):
        self._creneau(_aware(2025, 9, 8))
        self.garde.publier(self.marin)
        compteur = compteur_equite_marin(self.marin, aujourdhui=self.aujourdhui)
        self.assertEqual(sum(compteur["mois"].values()), 0)
        self.assertEqual(sum(compteur["annee"].values()), 0)

    def test_marin_sans_aucun_creneau_obtient_des_compteurs_a_zero(self):
        autre = User.objects.create_user(username="marin_sans_creneau", password="pass")
        UserProfile.objects.update_or_create(user=autre, defaults={"role": "EQUIPIER", "ship": self.ship})
        compteur = compteur_equite_marin(autre, aujourdhui=self.aujourdhui)
        self.assertEqual(compteur["mois"], {CATEGORIE_SEMAINE: 0, CATEGORIE_VENDREDI: 0, CATEGORIE_WEEKEND: 0})
        self.assertEqual(compteur["annee"], {CATEGORIE_SEMAINE: 0, CATEGORIE_VENDREDI: 0, CATEGORIE_WEEKEND: 0})


class ScopingPerimetreTests(TestCase):
    """Vérifie que le compteur détaillé du périmètre couvre exactement les
    marins affectables sur la liste (même règle que marins_du_perimetre),
    ni plus ni moins."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Équité Périmètre", code="EQP")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.sector = Sector.objects.create(service=self.service, name="Manœuvre")
        self.section = Section.objects.create(sector=self.sector, name="Bordée A")
        self.autre_sector = Sector.objects.create(service=self.service, name="Autre secteur")

        self.marin_dans_perimetre = User.objects.create_user(username="marin_dans_perimetre", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_dans_perimetre, defaults={"role": "EQUIPIER", "section": self.section}
        )
        self.marin_hors_perimetre = User.objects.create_user(username="marin_hors_perimetre", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_hors_perimetre, defaults={"role": "EQUIPIER", "sector": self.autre_sector}
        )

        self.garde = ServiceGarde.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )

    def test_compteurs_perimetre_ne_couvre_que_les_marins_du_perimetre(self):
        resultat = compteurs_equite_perimetre(self.garde)
        marins_presents = {item["marin"].pk for item in resultat}
        self.assertIn(self.marin_dans_perimetre.pk, marins_presents)
        self.assertNotIn(self.marin_hors_perimetre.pk, marins_presents)


class VisibiliteWebTests(TestCase):
    """Vérifie la visibilité à deux niveaux exigée par le cadrage : le chef
    de liste voit les compteurs détaillés de tout son périmètre sur la fiche
    de la liste, un marin lambda ne voit que son propre total sur son tableau
    de bord personnel."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Équité Web", code="EQW")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Machine"), name="Propulsion"
        )

        self.chef = User.objects.create_user(username="chef_equite", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "EQUIPIER", "sector": self.sector})
        ChefDeListe.objects.create(user=self.chef, sector=self.sector)

        self.marin = User.objects.create_user(username="marin_equite_web", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "sector": self.sector})

        self.garde = ServiceGarde.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )
        debut = timezone.now() + timedelta(hours=2)
        CreneauServiceGarde.objects.create(
            service_garde=self.garde, poste="Garde 24h", debut=debut, fin=debut + timedelta(hours=24), marin=self.marin,
        )
        self.garde.publier(self.chef)

    def test_chef_de_liste_voit_les_compteurs_detailles_de_son_perimetre(self):
        self.client.login(username="chef_equite", password="pass")
        r = self.client.get(f"/quarts/garde/{self.garde.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.context["compteurs_equite"])
        marins_affiches = {item["marin"].pk for item in r.context["compteurs_equite"]}
        self.assertIn(self.marin.pk, marins_affiches)
        self.assertIn(self.chef.pk, marins_affiches)

    def test_marin_lambda_ne_voit_pas_les_compteurs_detailles_sur_la_fiche(self):
        self.client.login(username="marin_equite_web", password="pass")
        r = self.client.get(f"/quarts/garde/{self.garde.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["compteurs_equite"])

    def test_marin_voit_son_propre_total_sur_son_tableau_de_bord(self):
        self.client.login(username="marin_equite_web", password="pass")
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        compteur = r.context["mes_compteurs_equite_garde"]
        self.assertEqual(sum(compteur["mois"].values()) + sum(compteur["annee"].values()) >= 0, True)
        # Le total du marin doit refléter le créneau qui lui est affecté.
        self.assertGreaterEqual(sum(compteur["annee"].values()), 1)
