<!-- couvre: diffusable/03_lire_ce_dossier.md | Chapitre 3 — Lire ce dossier -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.1 L'état du logiciel décrit : l'état B -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.2 Les quatre étiquettes -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.3 Les sources et leur poids -->
<!-- retire: diffusable/03_lire_ce_dossier.md | 3.4 Organisation des fichiers | Déplacée dans le dossier technique (organisation du dépôt) et dans le point d'entrée README_DOSSIER.md -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.5 Vérifier une affirmation -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | Règle de séparation -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.6 Vocabulaire -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.7 Limites de ce dossier -->
<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.8 Révisions -->
<!-- partie: Cadre -->
# Lire ce document

<div class="ligne-public"><b>Public :</b> tous les lecteurs du référentiel · <b>Ce que vous y trouverez :</b> l'état du logiciel décrit, les quatre étiquettes, le poids des sources, la façon de vérifier une affirmation et les limites du document</div>

## L'état du logiciel décrit : l'état B

Ce document décrit Matrix tel qu'il existe dans le code à un instant précis : **l'état B, version de référence du 11/11/2026**. C'est une version de développement : elle comprend la version V1.1 (interface « Naval Premium », correctifs de recette) et quatre lots de sécurisation (verrou des commandes de démonstration, configuration de production, archivage effectif des unités, suppression sûre des unités). **L'état B n'est pas fusionné dans la branche de référence** : tout ce que ce document décrit comme « actuel » est ce que contient cette version, qui n'est ni déployée ni validée.

L'identifiant technique de cette version (branche, empreinte) figure uniquement dans le dossier technique à accès restreint ([[DT:01_lire_ce_dossier_technique]]).

| Lot livré dans l'état B | Objet | Effet |
|---|---|---|
| L01 | Verrou des commandes de démonstration | Les commandes qui créent des comptes fictifs ne s'exécutent que sur une base dédiée, marquée comme telle |
| L05 | Configuration de production | Refus de démarrer en production avec une clé secrète ou un mot de passe de base d'exemple |
| L02 | Archivage effectif des unités | Archiver une unité occupée est refusé ; aucune nouvelle affectation vers une unité archivée |
| L03 | Suppression sûre des unités | Une unité encore référencée ne peut plus être supprimée |

## Les quatre étiquettes

| Étiquette | Signification | Preuve attendue |
|---|---|---|
| 🟢 **Actuel** | Ce comportement existe dans le code de l'état B | Vérifié dans le code, par un test ou rejoué sur l'instance de démonstration |
| 🔵 **Cible** | Règle validée par le Product Owner, **non développée ou partielle**. Jamais rédigée au présent comme si elle fonctionnait | Identifiant de décision et, s'il existe, lot |
| 🟣 **Proposition** | Idée ou règle **proposée**, **à valider par le PO** : ce n'est **pas** une décision. Jamais rédigée au présent | Mention « à valider par le PO » et, s'il existe, rattachement à un lot |
| ⚪ **Non vérifié** | Information issue d'une seule source ou point non rejoué | La limite est dite en clair ; recensée dans les annexes consultables |

Chaque fiche de module est construite de la même manière : à quoi sert le module ; qui fait quoi ; écran de référence ; règles ; circuit ; fonctionnement actuel et cible ; limites et écarts ; décisions du PO. Ce document **n'est pas un audit** : une limite connue apparaît comme périmètre actuel d'une fonction, et le registre central des écarts et décisions ([[RE:01_lire_ce_registre]]) porte le détail de chaque écart.

## Les sources et leur poids

1. **Le code de l'état B** et ses tests : référence pour le fonctionnement actuel.
2. **Les décisions du PO**, enregistrées dans le dossier d'analyse V1.2 ({{fait:n_decisions_v12}} décisions identifiées « DEC-… ») : référence pour le fonctionnement cible. Elles sont **citées, jamais rouvertes**.
3. **Notion** (cahier des charges, organigramme et rôles, décisions) : source de connaissance et de décisions ; ses pages portent l'état « non vérifié » et ne valent pas recette. Une note ancienne ne prévaut pas sur une décision plus récente.
4. **Les comptes rendus de lots** (L01, L05, L02, L03) : référence pour ce qui a été changé et testé.
5. **Les archives du dépôt** : historique, jamais une consigne.

Le *Guide du marin 2023* n'a jamais été disponible : il n'est source d'aucune règle.

## Vérifier une affirmation

Chaque fiche renvoie à ses sources. Les références précises au code sont réservées au dossier technique à accès restreint ; les inventaires chiffrés (nombre de modèles, de routes, de tâches planifiées…) sont **générés** depuis le code, jamais saisis à la main, et un contrôle automatique vérifie que le même chiffre figure dans tous les documents.

### Règle de séparation

| Document | Peut contenir | Ne contient jamais |
|---|---|---|
| **Guide utilisateur et référentiel fonctionnel** | Usage, règles métier, circuits, parcours, droits en clair, glossaire, cible, historique, schémas explicatifs | Référence de fichier et de ligne, nom de variable ou de secret, commande d'exploitation, adresse, port, nom de branche, empreinte de version |
| **Dossier technique, annexes consultables, registre** | Architecture, données, sécurité, interface de programmation, exploitation, droits par clé, écarts détaillés | — (accès restreint) |

⚠ **Cette séparation n'est pas une autorisation de diffusion.** La mention « DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE » est une précaution documentaire, non une classification officielle : la classification et la liste des destinataires restent à valider par le PO et, pour les documents techniques, avec les SIC.

## Vocabulaire

Le glossaire complet figure en fin de ce document ([[RF:30_glossaire]]). Quatre distinctions à garder en tête dès maintenant :

- **Rôle** : profil d'accès dans Matrix (équipier, chef de section… administrateur général). Ce n'est ni un grade ni une fonction.
- **Fonction** : ce que la personne exerce (chef de liste, BSC, COMAEQ, fonction de service ou de quart).
- **Grade** : le rang. Il n'ouvre aucun droit métier à lui seul.
- **Brevet / qualification** : ce que la personne est habilitée à faire du point de vue de la formation.

## Limites de ce document

- ⚪ Le document décrit un **état du code**, pas un état déployé ; il ne vaut ni recette ni homologation.
- ⚪ Les vérifications portent sur le code et ses tests (suite complète sur SQLite). **PostgreSQL et Windows n'ont pas été rejoués** pour cette édition.
- 🟢 Les écrans cités par le guide utilisateur ont été **rejoués sur une instance de démonstration isolée le 16/11/2026**, avec des données fictives et un navigateur en français. Les parcours qui n'y figurent pas restent reconstitués d'après le code ⚪. Les deux vues de téléphone sont **émulées** : aucun appareil réel n'a été essayé ⚪.
- ⚪ Les pages Notion consultées portent l'état « non vérifié » ; la liste exacte des sources lues et non lues est dans les annexes consultables.

## Révisions

| Date | Contenu |
|---|---|
| 11/11/2026 | Édition G0 : chapitres 1 à 26, annexes A à H, schémas S01 à S42, version PDF |
| 13/11/2026 | Révision 2 : refonte en cinq livrables (guide utilisateur, référentiel fonctionnel, dossier technique, annexes consultables, registre) ; maquette pilote « Maintenance » |
| 16/11/2026 | Révision 2, rédaction complète des sources ; captures refaites sur une instance de démonstration isolée |
