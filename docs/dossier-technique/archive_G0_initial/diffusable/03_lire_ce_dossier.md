# Chapitre 3 — Lire ce dossier

> **Pour qui :** tous. **Diffusion :** générale.
> **Ce que vous y trouverez :** l'état du logiciel décrit, les quatre étiquettes qui distinguent le réel, la cible validée, les propositions et le non vérifié, l'organisation des fichiers et la façon de vérifier une affirmation.

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

## 3.2 Les quatre étiquettes

| Étiquette | Signification | Preuve attendue |
|---|---|---|
| 🟢 **Actuel** | Ce comportement existe dans le code de l'état B | Référence de code (fichier et ligne) vérifiée sur B et consignée dans la partie restreinte, ou test, ou migration |
| 🔵 **Cible** | Règle validée par le Product Owner, **non développée ou partielle**. Jamais rédigée au présent comme si elle fonctionnait | Identifiant de décision `DEC-…` et, s'il existe, lot `Lnn` |
| 🟣 **Proposition** | Idée ou règle **proposée** (par l'assistant ou relevée en recette), **à valider par le PO** : ce n'est **pas** une décision. Jamais rédigée au présent | Mention « à valider par le PO » et, s'il existe, rattachement à un lot |
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

Chaque chapitre se termine par ses **sources**. Dans les chapitres **diffusables**, elles désignent les modules du code de l'état B, les décisions du PO (`DEC-…`) et les pages Notion consultées ; **les références précises au code (fichier et ligne) se trouvent uniquement dans la partie restreinte**, pour les développeurs.

Les inventaires chiffrés (nombre de modèles, de routes, de tâches planifiées…) sont **générés** depuis le code, jamais saisis à la main. Des contrôles automatiques vérifient que chaque référence de code existe sur l'état B, que les chiffres cités correspondent à l'inventaire, que les schémas sont tous exportés et référencés, et que **les parties diffusable et restreinte ne se mélangent pas** (aucune référence de code, variable de configuration, commande d'exploitation ou lien vers la partie restreinte dans les fichiers diffusables).

### Règle de séparation

| Partie | Peut contenir | Ne contient jamais |
|---|---|---|
| **Diffusable** | Usage, règles métier, circuits, parcours, droits en clair, glossaire, cible, historique, schémas explicatifs | Références `fichier:ligne`, noms de variables ou de secrets, commandes d'exploitation, adresses et ports, chemins vers la partie restreinte |
| **Restreinte** | Architecture, données, sécurité, API, exploitation, déploiement, droits détaillés, registre des écarts, annexes générées | — (tout y est déjà restreint) |

⚠ **Cette séparation n'est pas une autorisation de diffusion.** La classification définitive et la liste des destinataires restent à valider séparément par le PO et, pour la partie restreinte, avec les SIC.

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
- ⚪ Quelques pages Notion n'ont été vues que dans les résultats de recherche, sans lecture complète, et le sous-module de charte graphique est vide dans l'environnement de rédaction : la liste exacte des sources lues et non lues est dans la partie restreinte (annexe F).

## 3.8 Révisions

| Date | Contenu |
|---|---|
| 11/11/2026 | Édition G0, ensemble 1 : chapitres 1 à 5, 18, 19, 22 ; annexes A et B |
| 11/11/2026 | Ensemble 2 : chapitres 6 à 10 ; chapitre 5 complété (sept profils, écarts d'implémentation) ; registre des écarts (partie restreinte du dossier) |
| 11/11/2026 | Ensemble 3 : chapitres 11 à 16 ; schémas S22 à S33 ; registre des écarts complété (A15 à A21) ; chapitre 5 (BSC, chef de liste, points à confirmer) et chapitre 8 révisés ; A12 et A14 reformulés |
| 11/11/2026 | Ensemble 4 : chapitres 17, 20, 21, 23 à 26 ; annexes C à H ; schémas S34 à S42 ; registre des écarts complété (A22 à A26) ; règle de séparation diffusable / restreint ; version PDF |

---

**Sources.** Comptes rendus des lots : `docs/dossier-technique-v12/N_LOT_L01_COMPTE_RENDU.md`, `O_LOT_L05_COMPTE_RENDU.md`, `P_LOT_L02_COMPTE_RENDU.md`, `Q_LOT_L03_COMPTE_RENDU.md` et `A_REGISTRE_DECISIONS.md` (branche `claude/eager-hopper-2cbcqh`, commit `6cc1557`). `CLAUDE.md` (règles du projet).
