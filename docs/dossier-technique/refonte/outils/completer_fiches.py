"""Ajoute à chaque fiche du référentiel la section « Écarts et décisions du registre » (tableaux générés depuis registre.json).
Les identifiants viennent de la liste ci-dessous (module -> écarts, préfixes de décisions) et des identifiants cités dans la fiche.
Idempotent. Usage : python completer_fiches.py"""
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
REG = json.loads((R / "5_registre/registre.json").read_text(encoding="utf-8"))
DECS = [d["id"] for d in REG["decisions"]]
TOUS = {e["id"] for k in ("ecarts", "nouveaux_ecarts", "points_a_confirmer", "propositions") for e in REG[k]}

MODULES = {
    "04_organisation.md": ([], ["ORG", "MUT"]),
    "05_roles_et_autorisations.md": (["A1", "A4", "A7", "B2", "B5", "B7"], ["DRT", "SUP"]),
    "06_fiche_accueil_pilotage.md": (["A14", "NE-06"], []),
    "07_fiche_calendrier.md": (["A25"], []),
    "08_fiche_quarts_services_feuille.md": (["A2", "A3", "A12", "B1", "B3", "B4", "B5"], ["FDS"]),
    "09_fiche_communication.md": ([], []),
    "10_fiche_taches_demandes_programme_postes.md": (["A11", "A13", "B6"], ["TAC", "CLO", "COL", "BLQ"]),
    "11_fiche_materiel_installations.md": (["A18", "NE-04"], ["MAT"]),
    # 12_fiche_maintenance.md : déjà complète (maquette pilote)
    "13_fiche_logistique.md": (["NE-02"], []),
    "14_fiche_formations.md": (["A19"], ["QUA"]),
    "15_fiche_documentation_retex.md": (["A15", "A16", "D3"], ["RTX"]),
    "16_fiche_preparation_appareillage.md": (["A17", "B4", "D4"], ["APP"]),
    "17_principes_interface.md": (["A11", "D5", "D6", "NE-05"], ["UX"]),
}
MARQUE = "## Écarts et décisions du registre"


def ordre(i):
    m = re.match(r"([A-Z]+)-?(\d+)", i)
    return (m.group(1), int(m.group(2)))


for nom, (ecarts, prefixes) in MODULES.items():
    f = R / "2_referentiel_fonctionnel" / nom
    t = f.read_text(encoding="utf-8")
    if MARQUE in t:
        continue
    cites = set(re.findall(r"\b(A\d{1,2}|B\d|D\d|NE-\d{2})\b", re.sub(r"<!--.*?-->", "", t)))
    ids = sorted((set(ecarts) | cites) & TOUS, key=ordre)
    decs = [d for d in DECS if d.split("-")[1] in prefixes]
    cites_dec = set(re.findall(r"\bDEC-[A-Z]{2,4}-\d{2}\b", t)) & set(DECS)
    decs = sorted(set(decs) | cites_dec)
    bloc = [MARQUE, "",
            "Les tableaux ci-dessous sont **générés depuis le registre central** : le statut et l'état de chaque entrée y sont tenus ; cette fiche n'en donne aucun autre. "
            "Une proposition 🟣 n'est pas une décision ; « non développée » signifie seulement que le lot correspondant n'est pas livré dans l'état B.", ""]
    if ids:
        bloc += ["### Écarts, points à confirmer et propositions", "", "@ecarts " + " ".join(ids), ""]
    if decs:
        bloc += ["### Décisions du PO", "", "@decisions " + " ".join(decs), ""]
    if ids or decs:
        f.write_text(t.rstrip() + "\n\n" + "\n".join(bloc), encoding="utf-8")
        print("complété", nom, len(ids), "écarts,", len(decs), "décisions")
