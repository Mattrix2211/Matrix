# Dossier technique intégral de Matrix — Mode d'emploi

> **Statut :** édition G0 en cours de rédaction (ensembles 1 et 2 livrés pour revue). **État du logiciel décrit :** état B, branche `claude/l03-suppression-sure-v11`, commit `6d6d0be`, **non fusionné dans `main`**.
> Branche documentaire : `claude/fervent-wright-kl6gtx`. Aucun code applicatif n'est modifié par ce dossier.

## Où lire quoi

| Je suis… | Je commence par… |
|---|---|
| Marin | `diffusable/01_vision.md`, `diffusable/02_vue_ensemble.md` |
| Responsable | `diffusable/04_organisation.md`, `diffusable/05_comptes_roles_autorisations.md`, `diffusable/08_quarts_services_feuille.md` |
| Développeur | `restreint/18_architecture.md`, `restreint/19_modeles_donnees.md`, puis les fichiers `*_technique.md` |
| Administrateur | `restreint/22_securite.md`, `restreint/04_organisation_technique.md` |
| Tous | `diffusable/03_lire_ce_dossier.md` (étiquettes, états A/B, sources) |

## Contenu

| Dossier | Contenu | Diffusion |
|---|---|---|
| `diffusable/` | Chapitres d'usage et de règles métier ; glossaire (`diffusable/annexes/A_glossaire.md`) | Générale |
| `restreint/` | Architecture, données, sécurité, mécanismes de droits ; matrice rôle × action (`restreint/annexes/B_matrice_role_action.md`) | Restreinte |
| `schemas/src`, `schemas/svg` | Sources Mermaid et exports SVG lisibles hors ligne | Selon le chapitre |
| `couverture/` | Inventaires et matrice de couverture générés depuis le code | Restreinte |
| `outils/` | Scripts d'inventaire et de contrôle (lecture seule) | Restreinte |
| `restreint/ECARTS_DECISIONS_CODE.md` | Écarts entre décisions du PO et code, décisions ambiguës | Restreinte |
| `G0_*.md`, `RAPPORT_E1.md`, `RAPPORT_E2.md` | Cadrage, sommaire et rapport de livraison de l'ensemble 1 | Restreinte |

## Régénérer et contrôler

Les chiffres et matrices sont **générés** depuis le code de l'état B. Depuis la racine du dépôt :

```bash
# 1. Extraire l'état B dans un dossier à part (jamais dans ce dépôt)
git fetch origin claude/l03-suppression-sure-v11
mkdir /tmp/etat_B && git archive origin/claude/l03-suppression-sure-v11 | tar -x -C /tmp/etat_B

# 2. Inventaire, annexe B, matrice de couverture
cd /tmp/etat_B && python /chemin/du/depot/docs/dossier-technique/outils/inventaire.py /tmp/etat_B /chemin/du/depot/docs/dossier-technique/couverture/etat_B
cd /tmp/etat_B && python /chemin/du/depot/docs/dossier-technique/outils/generer_annexe_b.py /tmp/etat_B /chemin/du/depot/docs/dossier-technique/restreint/annexes/B_matrice_role_action.md
python docs/dossier-technique/outils/generer_matrice_couverture.py docs/dossier-technique

# 3. Contrôles documentaires
python -I docs/dossier-technique/outils/verifier_references.py /tmp/etat_B docs/dossier-technique origin/claude/eager-hopper-2cbcqh
python -I docs/dossier-technique/outils/controle_coherence.py docs/dossier-technique

# 4. Exporter les schémas Mermaid en SVG (nécessite Node, Playwright et le paquet npm mermaid 10.9.1)
node docs/dossier-technique/outils/rendre_schemas.js <dossier_contenant_node_modules_mermaid> docs/dossier-technique/schemas/src docs/dossier-technique/schemas/svg
```

Les scripts d'inventaire chargent Django sur la copie de l'état B ; ils ne touchent jamais à une base de données.

## Règles de rédaction

Voir `diffusable/03_lire_ce_dossier.md` : trois étiquettes (🟢 actuel, 🔵 cible, ⚪ non vérifié), références vérifiées sur l'état B, aucune fonction cible rédigée au présent, aucun audit.
