# Rapport de livraison — Ensemble 4 (« Interface, exploitation, cible »)

> **Diffusion restreinte.** Date : 11/11/2026. Branche documentaire : `claude/fervent-wright-kl6gtx`. État du logiciel décrit : état B, `claude/l03-suppression-sure-v11` @ `6d6d0be`, **non fusionné dans `main`**.
> Aucun code applicatif modifié, aucune fusion dans `main`, aucune PR, aucun nouveau lot. Aucune décision du PO rouverte. Le bilan complet et la revue transversale sont dans `BILAN_FINAL_G0.md`.

---

## 1. Retours du PO sur l'ensemble 3 : traitement

| Demande | Traitement |
|---|---|
| Écarts A15 à A21 documentés, pas de correction de code | Conservés au registre ; **A19 corrigé** (voir §2) ; aucun code touché |
| **RETEX** : circuit cible inchangé ; le chef de service autorise la diffusion après validation ; la transmission effective est distincte ; « flotte » n'est jamais une preuve de transmission ; destinataires et canaux à confirmer | Chapitre 15 (§15.5) réécrit avec les trois actes distincts ; schémas S30 (réel) et S31 (cible) mis à jour ; écarts A15 et A16 ; point D3 |
| **Appareillage** : principe `DEC-APP-14` conservé comme cible ; circuit actuel à signature unique décrit séparément ; Matrix est un outil de suivi et ne délivre pas l'autorisation réelle | Chapitre 16 : rappel en tête (§16.1), cible reformulée (« le chef de service examine ; le COMANAV approuve le référentiel ») ; schéma S33 ; écart A17 ; point D4 |
| **Installation non conforme** : ticket de suivi proposé, « à valider par le PO » ; un ticket ne clôture pas une anomalie ni n'autorise une remise en service | Étiquette **🟣 proposition** créée (chapitres 3, 12, 25, registre partie D) ; point D1 ; **ce n'est nulle part présenté comme une décision** |
| **A20** : examiner si « En validation » a une sortie | **Examiné au code** : aucune action de validation dédiée ; **seule sortie : la correction du compte rendu** par un chef de secteur (conformité finale conforme) ; aucun lien automatique ticket → occurrence ; occurrence exclue du calcul des retards ; **risque de blocage sans alerte** documenté (chapitre 12 §12.4, A20, D2) |
| **RETEX et documentation : faible couverture de tests** | Signalée explicitement : `documentation` 9 fonctions de test, `retex` 5 (chapitres 15, 24, rapports) |
| **Stock et commandes : décrire exhaustivement l'existant**, sans règle cible inventée | Chapitre 13 : nouvelle section 13.9 bis (fiche, états, écrans, export, demandes, API, **ce qui n'a pas été trouvé**) ; aucune cible inventée (aucune décision V1.2 sur le stock) |
| Distinguer décisions validées, propositions, éléments non vérifiés | Quatre étiquettes : 🟢 réel, 🔵 cible validée, 🟣 proposition à valider, ⚪ non vérifié |

## 2. Corrections apportées à des chapitres déjà livrés

| Chapitre | Erreur trouvée | Correction |
|---|---|---|
| 14 et A19 | J'avais écrit que « l'organisme de formation n'est pas un acteur de Matrix » | **Faux** : un organisme de formation est **une unité de type École ou Centre de formation** ; un référent de la formation dans cette unité attribue ou refuse les places et le demandeur est notifié. Ce qui manque : dossier vivant, timeline, transmission formalisée |
| 14 | Les qualifications étaient dites sans effet dans les quarts | Une liste de service à quai peut exiger des **habilitations** ; un **échange de tour** est refusé d'emblée si elles manquent (jamais une tâche ordinaire) |
| 12 | Placeholders d'identifiants de décision dans un premier jet | Remplacés par les vrais `DEC-PER`, `DEC-OUT`, `DEC-DUR` |
| 13 | « Ce qui n'existe pas » | Reformulé « non trouvé dans le code examiné » (absence déduite de la lecture) |
| Schémas S24, S27, S28, S30, S31, S33 | Libellés en décalage avec le texte | Alignés sur les chapitres |
| Chapitres diffusables 1, 2, 4, 5, 14 et glossaire | Références de code `fichier:ligne` dans des fichiers diffusables | Retirées (règle de séparation, §4) |

## 3. Chapitres, annexes et schémas livrés

| Élément | Fichiers |
|---|---|
| **17 — Interface, ergonomie, parcours** | `diffusable/17_ergonomie_navigation.md`, `restreint/17_ergonomie_navigation_technique.md` |
| **20 — API REST, intégrations, interfaces web** | `restreint/20_api_interfaces.md` |
| **21 — Interactions entre modules** | `restreint/21_interactions_modules.md` |
| **23 — Configuration, déploiement, exploitation** | `restreint/23_configuration_deploiement_exploitation.md` |
| **24 — Qualité, tests, contribution** | `restreint/24_qualite_contribution.md` |
| **25 — Fonctionnement cible et feuille de route** | `diffusable/25_fonctionnement_cible.md` |
| **26 — Historique des versions et des lots** | `diffusable/26_historique_versions_lots.md`, `restreint/26_historique_branches_technique.md` |
| Annexes C à H | C routes, D modèles, E tâches planifiées, commandes et variables, F sources / branches / non vérifiés, G couverture (restreint) ; H index des schémas (diffusable) et H bis (restreint) |
| Schémas S34 à S42 | navigation par rôle, déploiement type, cycle de l'instance de démonstration, flux asynchrones, feuille de route, dépendances entre lots, généalogie des branches, chaîne d'un lot, carte des routes |

Sources Notion lues avant rédaction : « 07 — SIC… », « Cap UX/UI Naval Premium », « Recette UX V1.1 », « Feuille de route », « 04 — Maintenance… » (vérifiée a posteriori pour le chapitre 11). Le sous-module `design/` est vide : ⚪.

## 4. Séparation diffusable / restreint

**Règle** (chapitre 3 §3.5) : les fichiers diffusables ne contiennent **ni référence de code (fichier:ligne), ni nom de variable ou de secret, ni commande d'exploitation, ni adresse ou port, ni chemin vers la partie restreinte** ; aucun schéma n'est partagé entre les deux parties. Le contrôle `outils/controle_separation.py` l'applique et **bloque l'export PDF** s'il signale une violation. Résultat : **0 violation** (21 fichiers diffusables, 30 restreints ; 31 schémas diffusables, 11 restreints). Le texte extrait du PDF diffusable ne contient aucune référence de code, aucune variable d'environnement, aucune adresse.

**Cette séparation n'est pas une autorisation de diffusion** : la classification et les destinataires restent à valider.

## 5. Constats propres à l'ensemble 4

- **Seuls neuf groupes ont une API** ; quarts, absences, tâches, annonces, demandes, programme, postes, documentation, RETEX et rapports n'en ont aucune (A26). Pas de pagination ni de limitation de débit trouvées.
- **Un module désactivé ne bloque que les pages** : API, tâches planifiées et enchaînements internes continuent (A25).
- **Aucun outil ni document de sauvegarde, restauration, supervision, journalisation** dans le dépôt (A24) ; aucun serveur d'application ni HTTPS livré ; pas de limitation des tentatives de connexion ni de HSTS trouvés (A23).
- **Aucun mode hors-ligne** côté client ; le service worker ne sert qu'aux notifications push.
- **Incohérence de documentation** : `setup.bat` annonce Python 3.8+, le projet suppose 3.12+ (A22).
- **Deux tâches nommées « …_daily » tournent chaque minute** (elles comparent l'heure à la préférence de chaque marin).
- **Aucune exigence SIC chiffrée** n'a été trouvée dans la page Notion « 07 ».

## 6. Contrôles et tests

| Contrôle | Résultat |
|---|---|
| Références de code vérifiées (fichier, ligne, symbole ; annexe C incluse) | **1 093, 0 erreur** |
| Cohérence documentaire (structure, étiquettes, liens, chiffres, secrets) | **51 fichiers, 42 schémas, 0 erreur** |
| Séparation diffusable / restreint | **0 violation** |
| Revue transversale automatique | **0 erreur** |
| Identifiants `DEC-…` | 70 cités, **70 existent** dans le registre V1.2 |
| Tests rejoués sur l'état B (`matrix`, `notifications`, `accounts`, `org`) | **1 434 tests OK (9 ignorés)** |
| Tests rejoués (ensemble 3, sept paquets) | 1 491 OK (1 ignoré) |
| Suite complète | **Non rejouée** : 3 963 OK, 20 ignorés d'après les comptes rendus de lots |
| PDF | Générés (§ du bilan) ; rendu relu visuellement sur plusieurs pages |

## 7. Éléments non vérifiés

Voir l'annexe F (registre généré des ⚪, 174 passages) et le bilan final : écrans non rejoués dans un navigateur, Windows, Safari, mobile, lecteurs d'écran, impression ; PostgreSQL, Redis et Celery réels ; PDF métier (WeasyPrint) ; Web Push ; charge ; pages Notion lues seulement par recherche ; sous-module `design/` vide ; observations de recette PO non rapprochées une à une du code.
