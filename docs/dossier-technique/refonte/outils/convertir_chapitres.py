"""Conversion initiale des anciens chapitres vers les sources du référentiel fonctionnel (RF) et du dossier technique (DT).

Réutilise le texte existant (déplacement, pas réécriture) : retire le cartouche et la numérotation des titres, pose les directives
`couvre` (une par ancien titre), réécrit les renvois « chapitre N » en renvois résolus, remplace les schémas retirés par leur tableau.
Les fichiers produits sont ensuite relus et complétés à la main ; ce script n'est lancé qu'une fois par fichier (il refuse d'écraser).
Usage : python convertir_chapitres.py
"""
import csv
import re
import sys
from pathlib import Path

from chemins import ancien as chemin_ancien

R = Path(__file__).resolve().parent.parent
DT = R.parent

# (ancien fichier, doc, nouveau nom, partie)
RF = [
    ("diffusable/02_vue_ensemble.md", "03_vue_ensemble.md", "Cadre"),
    ("diffusable/01_vision.md", "02_vision.md", "Cadre"),
    ("diffusable/04_organisation.md", "04_organisation.md", "Organisation et rôles"),
    ("diffusable/05_comptes_roles_autorisations.md", "05_roles_et_autorisations.md", "Organisation et rôles"),
    ("diffusable/06_accueil_pilotage.md", "06_fiche_accueil_pilotage.md", "Modules"),
    ("diffusable/07_calendrier.md", "07_fiche_calendrier.md", "Modules"),
    ("diffusable/08_quarts_services_feuille.md", "08_fiche_quarts_services_feuille.md", "Modules"),
    ("diffusable/09_communication.md", "09_fiche_communication.md", "Modules"),
    ("diffusable/10_taches_demandes_programme_postes.md", "10_fiche_taches_demandes_programme_postes.md", "Modules"),
    ("diffusable/11_materiel_installations.md", "11_fiche_materiel_installations.md", "Modules"),
    ("diffusable/13_logistique.md", "13_fiche_logistique.md", "Modules"),
    ("diffusable/14_formations.md", "14_fiche_formations.md", "Modules"),
    ("diffusable/15_documentation_retex.md", "15_fiche_documentation_retex.md", "Modules"),
    ("diffusable/16_preparation_appareillage.md", "16_fiche_preparation_appareillage.md", "Modules"),
    ("diffusable/17_ergonomie_navigation.md", "17_principes_interface.md", "Modules"),
    ("diffusable/25_fonctionnement_cible.md", "25_cible_et_feuille_de_route.md", "Cible et feuille de route"),
    ("diffusable/26_historique_versions_lots.md", "26_historique_des_versions.md", "Cible et feuille de route"),
    ("diffusable/annexes/A_glossaire.md", "30_glossaire.md", "Références"),
]
DTX = [
    ("restreint/04_organisation_technique.md", "04_organisation_technique.md", "Modules"),
    ("restreint/05_comptes_autorisations_technique.md", "05_comptes_autorisations_technique.md", "Modules"),
    ("restreint/06_accueil_pilotage_technique.md", "06_accueil_pilotage_technique.md", "Modules"),
    ("restreint/07_calendrier_technique.md", "07_calendrier_technique.md", "Modules"),
    ("restreint/08_quarts_services_feuille_technique.md", "08_quarts_services_feuille_technique.md", "Modules"),
    ("restreint/09_communication_technique.md", "09_communication_technique.md", "Modules"),
    ("restreint/10_taches_demandes_programme_postes_technique.md", "10_taches_demandes_programme_postes_technique.md", "Modules"),
    ("restreint/11_materiel_installations_technique.md", "11_materiel_installations_technique.md", "Modules"),
    ("restreint/13_logistique_technique.md", "13_logistique_technique.md", "Modules"),
    ("restreint/14_formations_technique.md", "14_formations_technique.md", "Modules"),
    ("restreint/15_documentation_retex_technique.md", "15_documentation_retex_technique.md", "Modules"),
    ("restreint/16_preparation_appareillage_technique.md", "16_preparation_appareillage_technique.md", "Modules"),
    ("restreint/17_ergonomie_navigation_technique.md", "17_ergonomie_navigation_technique.md", "Modules"),
    ("restreint/18_architecture.md", "18_architecture.md", "Architecture et exploitation"),
    ("restreint/19_modeles_donnees.md", "19_modeles_donnees.md", "Architecture et exploitation"),
    ("restreint/20_api_interfaces.md", "20_api_interfaces.md", "Architecture et exploitation"),
    ("restreint/21_interactions_modules.md", "21_interactions_modules.md", "Architecture et exploitation"),
    ("restreint/22_securite.md", "22_securite.md", "Architecture et exploitation"),
    ("restreint/23_configuration_deploiement_exploitation.md", "23_configuration_deploiement_exploitation.md", "Architecture et exploitation"),
    ("restreint/24_qualite_contribution.md", "24_qualite_contribution.md", "Architecture et exploitation"),
    ("restreint/26_historique_branches_technique.md", "26_historique_branches.md", "Historique"),
]
# ancien numéro de chapitre -> (doc, nom de fichier sans extension) : pour réécrire « chapitre N »
CHAP_RF = {1: "02_vision", 2: "03_vue_ensemble", 3: "01_lire_ce_document", 4: "04_organisation", 5: "05_roles_et_autorisations",
           6: "06_fiche_accueil_pilotage", 7: "07_fiche_calendrier", 8: "08_fiche_quarts_services_feuille", 9: "09_fiche_communication",
           10: "10_fiche_taches_demandes_programme_postes", 11: "11_fiche_materiel_installations", 12: "12_fiche_maintenance",
           13: "13_fiche_logistique", 14: "14_fiche_formations", 15: "15_fiche_documentation_retex", 16: "16_fiche_preparation_appareillage",
           17: "17_principes_interface", 25: "25_cible_et_feuille_de_route", 26: "26_historique_des_versions"}
CHAP_DT = {18: "18_architecture", 19: "19_modeles_donnees", 20: "20_api_interfaces", 21: "21_interactions_modules", 22: "22_securite",
           23: "23_configuration_deploiement_exploitation", 24: "24_qualite_contribution", 12: "12_maintenance_technique",
           4: "04_organisation_technique", 5: "05_comptes_autorisations_technique", 6: "06_accueil_pilotage_technique",
           7: "07_calendrier_technique", 8: "08_quarts_services_feuille_technique", 9: "09_communication_technique",
           10: "10_taches_demandes_programme_postes_technique", 11: "11_materiel_installations_technique", 13: "13_logistique_technique",
           14: "14_formations_technique", 15: "15_documentation_retex_technique", 16: "16_preparation_appareillage_technique",
           17: "17_ergonomie_navigation_technique", 26: "26_historique_branches"}
SVG_NOUVEAU = {"S09_dependances_paquets.svg": "S09d_dependances_detail.svg", "S10_er_org_accounts.svg": "S10_organisation_rattachement.svg"}
SCHEMAS_EN_TABLEAU = {"S02", "S14", "S22", "S24", "S27", "S36", "S37", "S38", "S40", "S42"}


def titres_mapping():
    return list(csv.DictReader((R / "MAPPING_ANCIEN_NOUVEAU.csv").open(encoding="utf-8"), delimiter=";"))


def tableau_de_remplacement(sid):
    f = next((R / "schemas/tableaux").glob(f"{sid}_*.md"))
    t = f.read_text(encoding="utf-8")
    t = re.sub(r"<!--.*?-->\s*", "", t, flags=re.S).strip()
    return t


def renvois(texte, cible):
    """« chapitre 12 » -> renvoi résolu par nom de fichier ; « chapitres 6, 12 et 17 » -> une liste de renvois."""
    def un(n):
        n = int(n)
        d = CHAP_DT if cible == "DT" else CHAP_RF
        autre = CHAP_RF if cible == "DT" else CHAP_DT
        if n in d:
            return f"[[{cible}:{d[n]}]]"
        if n in autre:
            return f"[[{'RF' if cible == 'DT' else 'DT'}:{autre[n]}]]"
        return f"chapitre {n}"
    def liste(m):
        nums = re.findall(r"\d+", m.group(0))
        seps = re.findall(r",| et| à", m.group(0))
        out = un(nums[0])
        for s, n in zip(seps, nums[1:]):
            out += {",": ", ", " et": " et ", " à": " à "}[s] + un(n)
        return out
    return re.sub(r"\b[Cc]hapitres? \d+(?:(?:,| et| à) \d+)*", lambda m: liste(m) if "chapitre " + m.group(0).split()[1] != "" else m.group(0), texte)


def convertir(ancien, nouveau, doc, partie, dest):
    src = chemin_ancien(ancien).read_text(encoding="utf-8")
    ligne = src.split("\n")
    titres = [t["titre"] for t in titres_mapping() if t["ancien_fichier"] == ancien]
    # cartouche : tout ce qui précède le premier « --- » ou le premier titre de niveau 2
    i1 = next(i for i, l in enumerate(ligne) if l.startswith("# "))
    h1 = ligne[i1]
    j = i1 + 1
    cart = []
    while j < len(ligne) and (not ligne[j].strip() or ligne[j].strip() == "---" or ligne[j].startswith(">")):
        if ligne[j].startswith(">"):
            cart.append(ligne[j])
        j += 1
    corps = ligne[j:]
    txt_cart = " ".join(c.lstrip("> ").strip() for c in cart)
    m = re.search(r"Ce que vous y trouverez\s*:?\*\*\s*(.*?)(?:\*\*État décrit|$)", txt_cart)
    trouverez = (m.group(1).strip() if m else "").rstrip(" .")
    m2 = re.search(r"Pour qui\s*:?\*\*\s*(.*?)(?:\*\*|$)", txt_cart)
    public = (m2.group(1).strip().rstrip(" .") if m2 else "responsables métier, commandement")
    couvre = []
    sortie = []
    h1_texte = re.sub(r"^#\s+", "", h1).strip()
    nouveau_titre = re.sub(r"^(Chapitre|Annexe) [A-Z0-9]+( \(technique\))?\s*[—-]\s*", "", h1_texte)
    if h1_texte in titres or True:
        couvre.append(h1_texte)
    def img(m):
        alt, fichier = m.group(1), m.group(2)
        nom = Path(fichier).name
        sid = nom[:3]
        if doc == "RF" and sid in SCHEMAS_EN_TABLEAU:
            return f"**{alt}** (remplacé par un tableau)\n\n" + tableau_de_remplacement(sid)
        nom = SVG_NOUVEAU.get(nom, nom)
        if doc == "RF" and nom.startswith("S09"):
            nom = "S09_groupes_fonctionnels.svg"
        return f"![{alt}](../schemas/svg/{nom})"
    for l in corps:
        if re.match(r"^(#{2,4}) ", l):
            niveau = re.match(r"^(#{2,4}) ", l).group(1)
            texte = l[len(niveau) + 1:].strip()
            couvre.append(texte)
            propre = re.sub(r"^(?:[A-Z]\.|\d+\.)?\d+(?:\.\d+)*(?:\.T\d+)?(?: bis)?\.?\s+", "", texte)
            propre = re.sub(r"^\d+\.T\d+ (bis )?", "", propre)
            sortie.append(f"{niveau} {propre}")
            continue
        if l.strip() == "---":
            continue
        if re.match(r"^\*Schéma S\d+", l.strip()):
            continue
        l = re.sub(r"!\[([^\]]*)\]\(([^)]*\.svg)\)", img, l)
        sortie.append(l)
    texte = "\n".join(sortie)
    texte = renvois(texte, doc)
    texte = re.sub(r"\n{3,}", "\n\n", texte).strip() + "\n"
    ent = [f"<!-- couvre: {ancien} | {t} -->" for t in dict.fromkeys(couvre)]
    ent.append(f"<!-- partie: {partie} -->")
    ligne_pub = (f'<div class="ligne-public"><b>Public :</b> {public} · <b>Ce que vous y trouverez :</b> {trouverez}</div>' if trouverez
                 else f'<div class="ligne-public"><b>Public :</b> {public}</div>')
    out = "\n".join(ent) + f"\n# {nouveau_titre}\n\n{ligne_pub}\n\n{texte}"
    p = dest / nouveau
    if p.exists():
        print("existe déjà, conservé :", p.name)
        return
    p.write_text(out, encoding="utf-8")
    print("écrit", p.relative_to(R), len(out.split()), "mots")


def main():
    for anc, nom, partie in RF:
        convertir(anc, nom, "RF", partie, R / "2_referentiel_fonctionnel")
    for anc, nom, partie in DTX:
        convertir(anc, nom, "DT", partie, R / "3_dossier_technique")


if __name__ == "__main__":
    main()
