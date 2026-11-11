# Chapitre 3 — Lire ce dossier

> **Pour qui :** tous. **Diffusion :** générale.
> **Ce que vous y trouverez :** l'état du logiciel décrit, les trois étiquettes qui distinguent le réel, le cible et l'incertain, l'organisation des fichiers et la façon de vérifier une affirmation.

---

## 3.1 L'état du logiciel décrit : l'état B

Ce dossier décrit Matrix tel qu'il existe dans le code, à un instant précis.

| | État A | **État B (référence principale)** |
|---|---|---|
| Branche | `main` | `claude/l03-suppression-sure-v11` |
| Commit | `6ef16ad` (28/10/2026) | **`6d6d0be`** (11/11/2026) |
| Contenu | V1 FANLAB (PR n° 16) | V1.1 (UX « Naval Premium », correctifs de recette) **et** lots L01, L05, L02, L03 |
| Statut | publié, point de comparaison historique | **non fusionné dans `main`** |

> ⚠️ **L'état B n'est pas fusionné dans `main`.** Tout ce que ce dossier décrit comme « actuel » est ce que contient la branche `claude/l03-suppression-sure-v11`. Ce n'est pas une version déployée ni validée pour l'exploitation. Les quatre lots sont **empilés** : la branche L03 contient L02, L05 et L01.

Les lots ajoutés par rapport à `main` :

| Lot | Objet | Effet |
|---|---|---|
| L01 | Verrou des commandes de démonstration | Les commandes qui créent des comptes fictifs ne s'exécutent que sur une base dédiée, marquée comme telle |
| L05 | Configuration de production | Refus de démarrer en production avec une clé secrète ou un mot de passe de base d'exemple |
| L02 | Archivage effectif des unités | Archiver une unité occupée est refusé ; aucune nouvelle affectation vers une unité archivée |
| L03 | Suppression sûre des unités | Une unité encore référencée ne peut plus être supprimée |

Dans les chapitres, l'état A n'apparaît que dans un encadré **« Comparaison avec `main` »**, quand il diffère.

## 3.2 Les trois étiquettes

| Étiquette | Signification | Preuve attendue |
|---|---|---|
| 🟢 **Actuel** | Ce comportement existe dans le code de l'état B | Référence `fichier:ligne` vérifiée sur B, ou test, ou migration |
| 🔵 **Cible** | Règle validée par le Product Owner, **non développée ou partielle**. Jamais rédigée au présent comme si elle fonctionnait | Identifiant de décision `DEC-…` et, s'il existe, lot `Lnn` |
| ⚪ **Non vérifié** | Information issue d'une seule source (Notion, mémoire) ou point non rejoué | La limite est dite en clair ; recensée en annexe F |

Chaque chapitre est construit de la même manière : *ce que c'est et à quoi ça sert → qui l'utilise → comment ça marche → quelles données → quels contrôles → liens avec les autres modules*, puis, séparément, **le fonctionnement cible** et **les limites**.

Ce dossier **n'est pas un audit** : il n'inventorie pas d'anomalies. Une limite connue apparaît seulement comme périmètre actuel d'une fonction.

## 3.3 Les sources et leur poids

1. **Le code de l'état B** et ses tests : référence pour le fonctionnement actuel.
2. **Les décisions du PO**, enregistrées dans le dossier d'analyse V1.2 (125 décisions identifiées `DEC-…`, branche `claude/eager-hopper-2cbcqh`, dossier `docs/dossier-technique-v12/`) : référence pour le fonctionnement cible. Elles sont **citées, jamais rediscutées**.
3. **Notion** (cahier des charges, organigramme et rôles, décisions) : source de connaissance et de décisions ; ses pages portent l'état « non vérifié » et ne valent pas recette. Une note ancienne ne prévaut pas sur une décision plus récente.
4. **Les comptes rendus de lots** (L01, L05, L02, L03) : référence pour ce qui a été changé et testé.
5. **`docs/archive/`** : historique, jamais une consigne.

Le *Guide du marin 2023* n'a jamais été disponible : il n'est source d'aucune règle.

## 3.4 Organisation des fichiers

Le dossier est un ensemble de fichiers Markdown maintenus dans le dépôt, sous `docs/dossier-technique/`.

| Dossier | Contenu | Diffusion |
|---|---|---|
| `diffusable/` | Usage, règles métier, circuits, parcours, glossaire | Générale |
| `restreint/` | Architecture, données, sécurité, configuration, exploitation, matrices de droits | Restreinte |
| `schemas/` | Sources Mermaid (`src/`) et exports SVG lisibles hors ligne (`svg/`) | Selon le chapitre qui les utilise |
| `couverture/` | Inventaires et matrices générés depuis le code | Restreinte |
| `outils/` | Scripts d'inventaire et de contrôle (lecture seule) | Restreinte |

Les chapitres mêlant usage et technique existent en deux fichiers : `NN_titre.md` (diffusable) et `NN_titre_technique.md` (restreint). Aucun mot de passe, clé ou donnée réelle n'est écrit dans le dossier.

## 3.5 Vérifier une affirmation

Chaque chapitre se termine par ses **sources** : chemins de fichiers et numéros de ligne **sur l'état B**. Pour contrôler :

```bash
git fetch origin claude/l03-suppression-sure-v11
git show 6d6d0be:matrix/core/roles.py | sed -n '4,15p'
```

Les inventaires chiffrés (nombre de modèles, de routes, de tâches planifiées…) sont **générés** par `outils/inventaire.py` depuis le code ; ils ne sont jamais saisis à la main. Un contrôle automatique (`outils/verifier_references.py`) vérifie que chaque fichier et chaque numéro de ligne cités existent bien sur l'état B.

## 3.6 Vocabulaire

Le glossaire complet est l'**annexe A**. Quatre distinctions à garder en tête dès maintenant :

- **Rôle** : profil d'accès dans Matrix (équipier, chef de section… administrateur général). Ce n'est ni un grade ni une fonction.
- **Fonction** : ce que la personne exerce (chef de liste, BSC, COMAEQ, fonction de service ou de quart).
- **Grade** : le rang. Il n'ouvre aucun droit métier à lui seul.
- **Brevet / qualification** : ce que la personne est habilitée à faire du point de vue de la formation.

## 3.7 Limites de ce dossier

- ⚪ Le dossier décrit un **état du code**, pas un état déployé ; il ne vaut ni recette ni homologation.
- ⚪ Les vérifications portent sur le code et ses tests (suite complète sur SQLite). **PostgreSQL, Windows et un navigateur réel n'ont pas été rejoués** pour cette édition.
- ⚪ Les pages Notion consultées portent l'état « non vérifié » ; ce qui n'en est reconnu que par elles est étiqueté en conséquence.
- ⚪ Certaines pages de référence n'ont pas encore été lues (formation et brevets, recette UX) : elles le seront avant les chapitres qui en dépendent.

## 3.8 Révisions

| Date | Contenu |
|---|---|
| 11/11/2026 | Édition G0, ensemble 1 : chapitres 1 à 5, 18, 19, 22 ; annexes A et B |
| 11/11/2026 | Ensemble 2 : chapitres 6 à 10 ; chapitre 5 complété (sept profils, écarts d'implémentation) ; registre des écarts `restreint/ECARTS_DECISIONS_CODE.md` |

---

**Sources.** Comptes rendus des lots : `docs/dossier-technique-v12/N_LOT_L01_COMPTE_RENDU.md`, `O_LOT_L05_COMPTE_RENDU.md`, `P_LOT_L02_COMPTE_RENDU.md`, `Q_LOT_L03_COMPTE_RENDU.md` et `A_REGISTRE_DECISIONS.md` (branche `claude/eager-hopper-2cbcqh`, commit `6cc1557`). `CLAUDE.md` (règles du projet).
