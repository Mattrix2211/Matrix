from datetime import date, timedelta

from django.test import SimpleTestCase

from assets.trend import jours_avant_franchissement_seuil, regression_lineaire_simple


def _serie(valeur_depart, pas_par_jour, nb_points, depart=date(2026, 1, 1)):
    """Construit une série de relevés (date, valeur) régulièrement espacée d'un
    jour, avec une évolution linéaire parfaite (pas de bruit) pour des tests
    de régression déterministes."""
    return [
        (depart + timedelta(days=i), valeur_depart + i * pas_par_jour)
        for i in range(nb_points)
    ]


class RegressionLineaireSimpleTests(SimpleTestCase):
    def test_pente_et_origine_calculees_correctement(self):
        # y = 2x + 10 exactement, aucun bruit.
        points = [(0, 10), (1, 12), (2, 14), (3, 16), (4, 18)]
        pente, origine = regression_lineaire_simple(points)
        self.assertAlmostEqual(pente, 2.0)
        self.assertAlmostEqual(origine, 10.0)

    def test_moins_de_deux_points_renvoie_none(self):
        self.assertIsNone(regression_lineaire_simple([(0, 10)]))
        self.assertIsNone(regression_lineaire_simple([]))

    def test_tous_les_x_identiques_renvoie_none(self):
        self.assertIsNone(regression_lineaire_simple([(5, 1), (5, 2), (5, 3)]))


class JoursAvantFranchissementSeuilTests(SimpleTestCase):
    def test_derive_a_la_baisse_detectee_isolement(self):
        # Isolement qui chute de 100 000 Ω par jour, seuil de danger à 500 000 Ω.
        releves = _serie(1_000_000, -100_000, 5)
        jours = jours_avant_franchissement_seuil(releves, seuil=500_000, sens="BAISSE")
        # Dernier relevé (jour 4) = 600 000 Ω, il reste 100 000 Ω à perdre à ce
        # rythme -> 1 jour avant le seuil.
        self.assertEqual(jours, 1)

    def test_derive_a_la_hausse_detectee_heures(self):
        # Heures de marche qui augmentent de 50h/jour, seuil d'entretien à 1000h.
        releves = _serie(800, 50, 5)
        jours = jours_avant_franchissement_seuil(releves, seuil=1000, sens="HAUSSE")
        # Dernier relevé (jour 4) = 1000h -> déjà atteint, donc pas d'alerte
        # préventive (dépassement avéré, traité par la branche compteur existante).
        self.assertIsNone(jours)

    def test_derive_a_la_hausse_pas_encore_atteinte(self):
        releves = _serie(700, 50, 5)
        jours = jours_avant_franchissement_seuil(releves, seuil=1000, sens="HAUSSE")
        # Dernier relevé (jour 4) = 900h, il reste 100h à ce rythme (50h/j) -> 2 jours.
        self.assertEqual(jours, 2)

    def test_tendance_stable_ne_declenche_aucune_alerte(self):
        releves = _serie(600_000, 0, 5)
        jours = jours_avant_franchissement_seuil(releves, seuil=500_000, sens="BAISSE")
        self.assertIsNone(jours)

    def test_tendance_qui_s_ameliore_ne_declenche_aucune_alerte(self):
        # L'isolement augmente (s'améliore) : pas de dérive vers le seuil bas.
        releves = _serie(400_000, 20_000, 5)
        jours = jours_avant_franchissement_seuil(releves, seuil=500_000, sens="BAISSE")
        self.assertIsNone(jours)

    def test_seuil_deja_franchi_ne_declenche_pas_de_nouvelle_alerte(self):
        releves = _serie(400_000, -10_000, 5)
        jours = jours_avant_franchissement_seuil(releves, seuil=500_000, sens="BAISSE")
        self.assertIsNone(jours)

    def test_pas_assez_de_releves_renvoie_none(self):
        releves = _serie(1_000_000, -100_000, 2)
        jours = jours_avant_franchissement_seuil(releves, seuil=500_000, sens="BAISSE")
        self.assertIsNone(jours)

    def test_ne_conserve_que_les_dix_derniers_releves(self):
        # 20 relevés, dont les 10 premiers avec une pente très différente : seuls
        # les 10 plus récents doivent influencer le résultat.
        anciens = _serie(2_000_000, 500_000, 10, depart=date(2025, 1, 1))
        recents = _serie(1_000_000, -50_000, 10, depart=date(2026, 1, 1))
        jours = jours_avant_franchissement_seuil(anciens + recents, seuil=100_000, sens="BAISSE")
        # Si les anciens relevés (en hausse) avaient influencé le calcul, la
        # pente globale n'aurait pas forcément indiqué une dégradation.
        self.assertEqual(jours, 9)

    def test_sens_invalide_leve_une_erreur(self):
        with self.assertRaises(ValueError):
            jours_avant_franchissement_seuil([(date(2026, 1, 1), 1)], seuil=0, sens="AUTRE")
