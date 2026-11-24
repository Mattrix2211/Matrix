"""Matrice exécutée : accès sensibles par profil, avec protections existantes et écarts connus (lot L29).

Chaque ligne appelle réellement le site avec le profil indiqué. Le résultat attendu est la cible des décisions du PO ;
un écart du code actuel est enregistré tel quel et nomme le lot correctif, il n'est ni masqué ni corrigé ici."""
import re
from pathlib import Path

from django.conf import settings

from matrix.core.registre_acces import REGLES

from .outils import MondeFictif, comparer, observer
from .verifications import VERIFICATIONS

PLAN = (Path(settings.BASE_DIR) / "docs" / "PLAN_LOTS_REPRISE.md").read_text(encoding="utf-8")

# Règles sensibles ou à écart dont la preuve par exécution reste à produire : liste explicite, jamais implicite.
# Elles sont couvertes par des suites existantes (champ `couverture` du registre) ou relèvent d'un lot suivant.
SANS_PREUVE_EXECUTEE = frozenset({
    "ADMIN-AUTRES", "ADMIN-ORGANISATION", "API-DISCUSSIONS", "API-FORMATIONS", "API-MAINTENANCE", "API-MATERIEL",
    "API-TABLEAUX", "WEB-ABSENCES", "WEB-DOCUMENTATION", "WEB-ECHANGES",
    "WEB-FEUILLE-SERVICE", "WEB-FORMATIONS", "WEB-LOGISTIQUE", "WEB-MAINTENANCE", "WEB-MATERIEL", "WEB-MEDIA", "WEB-PERSONNEL",
    "WEB-QUARTS", "WEB-RAPPORTS", "WEB-RETEX", "WEB-TABLEAUX",
})


class MatriceProfilsTests(MondeFictif):
    def test_chaque_ligne_donne_le_resultat_enregistre_pour_chaque_profil(self):
        for verification in VERIFICATIONS:
            with self.subTest(verification.identifiant):
                divergences = comparer(verification, self)
                self.assertEqual(
                    divergences, [],
                    f"{verification.identifiant} : (profil, enregistré, observé). Un écart connu corrigé doit sortir de "
                    f"`ecarts_connus` ; une divergence nouvelle est une régression de droits.")

    def test_un_ecart_connu_differe_de_la_cible_et_nomme_son_lot(self):
        for verification in VERIFICATIONS:
            for profil, observe in verification.ecarts_connus.items():
                self.assertIn(profil, verification.attendu, verification.identifiant)
                self.assertNotEqual(observe, verification.attendu[profil], f"{verification.identifiant} / {profil}")
                self.assertTrue(verification.lot_correctif, verification.identifiant)

    def test_les_regles_citees_existent(self):
        identifiants = {r.identifiant for r in REGLES}
        for verification in VERIFICATIONS:
            self.assertIn(verification.regle, identifiants, verification.identifiant)

    def test_les_profils_attendus_existent(self):
        for verification in VERIFICATIONS:
            for profil in verification.attendu:
                self.client_de(profil)

    def test_le_bilan_des_regles_sensibles_est_explicite(self):
        exercees = {v.regle for v in VERIFICATIONS}
        a_prouver = {
            r.identifiant for r in REGLES
            if (r.lecture_sensible or r.ecarts) and r.classe in ("authentifie", "administration") and r.identifiant not in exercees
        }
        self.assertEqual(a_prouver, set(SANS_PREUVE_EXECUTEE), "Toute règle sensible est soit exercée, soit déclarée sans preuve exécutée.")

    def test_une_ecriture_refusee_ne_laisse_aucune_trace(self):
        verification = next(v for v in VERIFICATIONS if v.identifiant == "V07-elevation-de-role-api")
        self.assertEqual(observer(verification, self, "equipier_b1")[0], "refus")
        self.equipier_b1.profile.refresh_from_db()
        self.assertEqual(self.equipier_b1.profile.role, "EQUIPIER")

    def test_chaque_verification_a_un_temoin_positif_ou_un_code_de_refus_exact(self):
        """Un 404 d'adresse ressemble à un refus : sans profil qui accède, la ligne doit exiger le code exact du refus."""
        for verification in VERIFICATIONS:
            temoin = any(c.startswith("acces") for c in (*verification.attendu.values(), *verification.ecarts_connus.values()))
            self.assertTrue(temoin or verification.codes, verification.identifiant)

    def test_le_lot_correctif_d_un_ecart_est_dans_le_plan(self):
        for verification in VERIFICATIONS:
            for lot in re.findall(r"\bL\d+\b", verification.lot_correctif):
                self.assertIn(f"**{lot}**", PLAN, f"{verification.identifiant} : {lot}")
