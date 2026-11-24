"""Le dispositif détecte réellement un accès insuffisamment protégé ou un point d'entrée oublié (lot L29)."""
from pathlib import Path

from django.test import override_settings

from matrix.core import points_entree

from .outils import MondeFictif, Verification, acces_anonymes_non_refuses, comparer, lignes_routes_ecriture, points_non_couverts

URLCONF_PIEGE = "matrix.tests.habilitation.urls_piege"


@override_settings(ROOT_URLCONF=URLCONF_PIEGE)
class DetectionTests(MondeFictif):
    def test_une_route_oubliee_du_registre_est_signalee(self):
        self.assertEqual(points_non_couverts(points_entree.routes()), ["piege/ouvert/"])

    def test_une_route_ouverte_a_un_visiteur_non_connecte_est_signalee(self):
        anomalies = {adresse for _, adresse, code in acces_anonymes_non_refuses(points_entree.routes()) if code == 200}
        self.assertEqual(anomalies, {"/piege/ouvert/", "/quarts/piege-ouvert/"})

    def test_la_matrice_signale_un_profil_qui_atteint_ce_qui_devrait_lui_etre_refuse(self):
        verification = Verification("piege", "WEB-QUARTS", "get", "/quarts/piege-ouvert/", attendu={"equipier_b1": "refus"})
        self.assertEqual(comparer(verification, self), [("equipier_b1", "refus", "acces")])

    def test_la_matrice_signale_un_ecart_connu_corrige(self):
        verification = Verification("piege", "WEB-QUARTS", "get", "/quarts/piege-ouvert/", attendu={"equipier_b1": "acces"},
                                    ecarts_connus={"equipier_b1": "refus"}, lot_correctif="L00")
        self.assertEqual(comparer(verification, self), [("equipier_b1", "refus", "acces")])

    def test_une_nouvelle_route_d_ecriture_dans_une_famille_connue_change_l_instantane(self):
        """Une route ajoutée sous un préfixe déjà couvert (`quarts/`) passe la couverture par règle ; l'instantané la signale."""
        attendu = (Path(__file__).parent / "instantane_routes_ecriture.txt").read_text(encoding="utf-8").splitlines()
        ajoutees = set(lignes_routes_ecriture(points_entree.routes())) - set(attendu)
        self.assertEqual(ajoutees, {"web|piege/ouvert/|?|SANS-REGLE", "web|quarts/piege-ouvert/|?|WEB-QUARTS"})
