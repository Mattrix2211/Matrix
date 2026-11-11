"""Génère l'annexe F (sources, décisions citées, branches, registre des éléments non vérifiés).

Usage : python generer_annexe_f.py <dossier_dossier_technique> <depot_git> <ref_git_v12>
Lecture seule. Le registre F.5 est celui produit par generer_annexes_e4.py.
"""
import re
import subprocess
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
G = Path(sys.argv[2]).resolve()
V12 = sys.argv[3]


def git(*args):
    return subprocess.run(["git", "-C", str(G), *args], capture_output=True, text=True).stdout


chapitres = {p.name: p.read_text(encoding="utf-8") for p in sorted(list(D.glob("diffusable/[0-9]*.md")) + list(D.glob("restreint/[0-9]*.md")))}
tout = "\n".join(chapitres.values())
registre = git("show", f"{V12}:docs/dossier-technique-v12/A_REGISTRE_DECISIONS.md") + git("show", f"{V12}:docs/dossier-technique-v12/A1_DECISIONS_S1_S2.md")
connues = set(re.findall(r"\bDEC-[A-Z]+-\d+\b", registre))
citees = sorted(set(re.findall(r"\bDEC-[A-Z]+-\d+\b", tout)))
inconnues = [d for d in citees if d not in connues]

L = ["# Annexe F — Sources, décisions citées, branches et éléments non vérifiés (généré)", "",
     "> Diffusion restreinte. Généré par `outils/generer_annexe_f.py` ; état B (`6d6d0be`), non fusionné dans `main`. Les sections F.1 et F.2 consignent ce qui a été **lu** et **non lu**, à la date de rédaction.", "",
     "## F.1 Sources lues", "",
     "| Source | Utilisation |", "|---|---|",
     "| Code de l'état B (`6d6d0be`), 21 applications et le noyau | Tous les chapitres ; références `fichier:ligne` vérifiées par script |",
     "| Dossier V1.2 (`docs/dossier-technique-v12/`, branche `claude/eager-hopper-2cbcqh`) : registre des 125 décisions, plan en 28 lots, comptes rendus L01, L05, L02, L03 | Décisions citées par `DEC-…`, jamais rouvertes ni recopiées |",
     "| Notion : Cahier des charges ; Organigramme et rôles ; pages 02, 06, 07, 11, 12 (glossaire), 13 (lues avant l'ensemble 1) ; page 04 (lue pour le chapitre 11) | Chapitres 4 à 16, 22, 25 (voir les citations « Notion » dans chaque chapitre) |",
     "| Notion : Feuille de route (10/10/2026) ; Cap UX/UI « Naval Premium » (29/10/2026) ; Recette UX V1.1 (31/10/2026) | Chapitres 17, 20, 25, 26 |",
     "| Notion : « 03 — Formation, stages, CFPES, FPS et qualification opérationnelle » (29/09/2026) | Chapitre 14, chapitre 21 |",
     "| Notion : « 04 — Maintenance, installations, SSF, SLM, ERDT… » (21/10/2026) | Chapitre 11 (configuration réelle, états techniques, interlocuteurs SSF/ERO/ERDT) |",
     "| Notion : « 07 — SIC, cyber, protection-défense et conformité » (30/09/2026) | Chapitre 23 (aucune exigence technique chiffrée trouvée) |",
     "| Documents du dépôt : `README.md`, `CLAUDE.md`, `docs/UX.md`, `docs/REFERENCE.md`, `docs/DEMO.md`, `docs/COMPATIBILITE_CHECKLIST.md`, `docs/recette/` | Chapitres 17, 23, 24 |",
     "", "## F.2 Sources non lues ou lues seulement par résultat de recherche ⚪", "",
     "- Notion : « Vision et Objectifs », « Audit métier Matrix × Guide du marin 2023 (31/10/2026) », « Ordre de travail Claude — Correctifs métier et UX V1.1 (01/11/2026) », « [CADRAGE UX] Corrections UX ciblées », « Tranche 1 — Prototype Naval Premium » : **vues dans les résultats de recherche, non lues en entier**.",
     "- Notion : pages 01, 05, 08, 09, 10 de l'organigramme (contexte) ; tâche « Recette V1 — F4 et F7 » ; **« [CADRAGE UX] Corrections UX ciblées »** (vue seulement dans les résultats de recherche).",
     "- Notion : tâches « Recette V1 — … » et autres tâches de la base « Tâches en cours » : non relues une à une.",
     "- Sous-module `design/` (charte graphique) : **vide** dans l'environnement de rédaction.",
     "- `docs/propositions/`, `docs/prototypes/`, `docs/archive/` du dépôt : exploités ponctuellement (par exemple les propositions mer/quai), non lus en entier ; l'archive n'est jamais une consigne.",
     "- *Guide du marin 2023* : **jamais disponible, non utilisé**.",
     "- Aucune exigence SIC opposable, aucune procédure de sauvegarde ou de supervision n'a été fournie.",
     "", "## F.3 Décisions du PO citées dans le dossier", "",
     f"**{len(citees)} identifiants `DEC-…`** distincts sont cités dans les chapitres ; **{len(citees) - len(inconnues)}** existent dans le registre V1.2 (125 décisions au total)."
     + (f" **Identifiants absents du registre : {', '.join(inconnues)}.**" if inconnues else " Aucun identifiant inventé."), "",
     ", ".join(f"`{d}`" for d in citees), "",
     "## F.4 Branches distantes", ""]
refs = git("for-each-ref", "--sort=-committerdate", "--format=%(refname:short)|%(committerdate:short)|%(objectname:short)", "refs/remotes/origin").strip().splitlines()
ANALYSEES = ("main", "integration/", "claude/paquet-bordops-review", "claude/feuille-service", "claude/quarts-regler", "claude/securite-", "claude/fiabilite-",
             "claude/validations-critiques", "claude/compat-postgresql", "claude/fix-ano-001", "claude/ux9-", "claude/ergonomie-p2", "docs/cahier-ux",
             "claude/ux-naval-premium", "claude/recette-metier-ux", "claude/iteration-ux", "claude/matrix-audit-general", "claude/matrix-v1-recette-audit",
             "claude/recette-v1-passage-b", "claude/eager-hopper", "claude/l0", "claude/maquette-carte", "claude/fervent-wright")
L += [f"**{len([r for r in refs if not r.startswith('origin/HEAD')])} branches distantes** à la date de l'inventaire. « Analysée » = expliquée au chapitre 26 ; « non analysée » = listée seulement.", "",
      "| Branche | Date | Commit | Dans A (`main`) | Dans B | Statut |", "|---|---|---|---|---|---|"]
for r in refs:
    nom, date, sha = r.split("|")
    nom = nom.replace("origin/", "", 1)
    if nom == "HEAD":
        continue
    ref = f"origin/{nom}"
    a = "oui" if subprocess.run(["git", "-C", str(G), "merge-base", "--is-ancestor", ref, "6ef16ad"]).returncode == 0 else "non"
    b = "oui" if subprocess.run(["git", "-C", str(G), "merge-base", "--is-ancestor", ref, "6d6d0be"]).returncode == 0 else "non"
    statut = "analysée" if nom.startswith(ANALYSEES) else "non analysée ⚪"
    L.append(f"| `{nom}` | {date} | `{sha}` | {a} | {b} | {statut} |")
L += [""]
L.append((D / "couverture/F5_registre_non_verifies.generated.md").read_text(encoding="utf-8"))
(D / "restreint/annexes/F_sources_branches_non_verifies.md").write_text("\n".join(L), encoding="utf-8")
print("annexe F générée ;", len(citees), "DEC cités ; inconnus :", inconnues)
