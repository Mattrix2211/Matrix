"""Génère MAPPING_ANCIEN_NOUVEAU.csv : chaque titre de l'ancien dossier, son emplacement prévu dans la refonte.

Usage : python generer_mapping.py <dossier-technique> <sortie.csv>
Les colonnes « nouveau_doc » et « nouvelle_section » sont préremplies d'après le §4 du plan ; « statut » vaut
« planifié » tant que la section n'est pas rédigée, puis « rédigé » (mis à jour par la phase correspondante)
ou « retiré » avec un motif approuvé par le PO.
"""
import csv
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
SORTIE = Path(sys.argv[2])

# fichier (préfixe numérique ou nom) -> (document, rubrique)
CHAPITRES = {
    "01": ("GU+RF", "Matrix en une page ; RF §1"), "02": ("RF+GU", "RF §2 carte des modules (tableau) ; GU menu"),
    "03": ("RF", "Lire ce document"), "04": ("RF", "Organisation"), "05": ("RF+DT", "Rôles et fiches de rôle ; DT mécanismes"),
    "06": ("RF", "Fiche module Accueil et pilotage"), "07": ("RF", "Fiche module Calendrier"),
    "08": ("RF", "Fiche module Quarts, services, feuille"), "09": ("RF", "Fiche module Communication"),
    "10": ("RF", "Fiche module Tâches, demandes, programme, postes"), "11": ("RF", "Fiche module Matériel et installations"),
    "12": ("RF", "Fiche module Maintenance, anomalies, tickets"), "13": ("RF", "Fiche module Logistique"),
    "14": ("RF", "Fiche module Formations"), "15": ("RF", "Fiche module Documentation et RETEX"),
    "16": ("RF", "Fiche module Préparation à l'appareillage"), "17": ("GU+RF", "Usage ; principes d'interface"),
    "18": ("DT", "Architecture"), "19": ("DT", "Données"), "20": ("DT", "API"), "21": ("DT", "Interactions"),
    "22": ("DT", "Sécurité"), "23": ("DT", "Exploitation"), "24": ("DT", "Qualité"),
    "25": ("RF", "Cible et feuille de route"), "26": ("RF+DT", "Historique ; branches en DT"),
}
ANNEXES = {
    "A_glossaire": ("RF+GU", "Glossaire"), "H_index_schemas": ("RF", "Index des schémas"),
    "B_matrice_role_action": ("RF+AC", "Matrice métier (RF) ; matrice technique (AC)"),
    "C_index_routes": ("AC", "Index des routes"), "D_index_modeles": ("AC", "Index des modèles"),
    "E_taches_commandes_variables": ("AC+DT", "Tâches, commandes, variables"),
    "F_sources_branches_non_verifies": ("AC+DT", "Éléments non vérifiés (tableau) ; sources et branches"),
    "G_matrice_couverture": ("AC", "Matrice de couverture"), "H_bis_schemas_restreints": ("DT", "Index des schémas techniques"),
}
SCHEMAS = {}
for s in "S01 S03 S04 S05 S06 S07 S08 S11 S12 S15 S16 S18 S19 S20 S23 S25 S26 S29 S30 S32 S34 S35 S39".split():
    SCHEMAS[s] = "conserver (rendu aux normes)"
for s in "S09 S10 S13 S28".split():
    SCHEMAS[s] = "refaire (mise en page)"
for s in "S17 S21 S31 S33".split():
    SCHEMAS[s] = "marquer CIBLE dans l'image"
for s in "S02 S14 S22 S24 S27 S36 S37 S38 S40 S42".split():
    SCHEMAS[s] = "remplacer par un tableau"
SCHEMAS["S41"] = "conserver en DT seulement"

lignes = []
def titres(chemin, doc, rub, kind):
    for l in chemin.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^(#{1,3}) (.+)$", l)
        if m:
            lignes.append([str(chemin.relative_to(D)), kind, len(m.group(1)), m.group(2).strip(), doc, rub, "planifié", ""])

for p in sorted(D.glob("diffusable/[0-9]*.md")):
    doc, rub = CHAPITRES[p.name[:2]]; titres(p, doc, rub, "chapitre")
for p in sorted(D.glob("restreint/[0-9]*.md")):
    nn = p.name[:2]
    doc, rub = CHAPITRES[nn]
    if "_technique" in p.name or nn == "26":
        doc = "DT"; rub = "Chapitre technique de module (fusion)" if "_technique" in p.name else "Historique et branches"
    titres(p, doc, rub, "complément technique" if "_technique" in p.name else "chapitre technique")
titres(D / "restreint/ECARTS_DECISIONS_CODE.md", "RE", "Registre vivant", "registre")
for p in sorted(list(D.glob("diffusable/annexes/*.md")) + list(D.glob("restreint/annexes/*.md"))):
    doc, rub = ANNEXES[p.stem]; titres(p, doc, rub, "annexe")
for p in sorted((D / "schemas/src").glob("S*.mmd")):
    lignes.append([str(p.relative_to(D)), "schéma", 0, p.stem, "voir décision", SCHEMAS[p.stem[:3]], "planifié", ""])

with SORTIE.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["ancien_fichier", "type", "niveau", "titre", "nouveau_doc", "nouvelle_section", "statut", "motif_si_retire"])
    w.writerows(lignes)
print(len(lignes), "lignes")
