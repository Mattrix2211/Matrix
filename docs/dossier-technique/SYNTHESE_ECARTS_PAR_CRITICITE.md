# Synthèse des écarts par criticité

> **Diffusion restreinte.** Édition G0 en attente de validation finale. **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Ce document est une aide de lecture, pas un plan de développement** : il ne propose ni ordre de traitement, ni lot, ni calendrier. Il ne modifie aucune décision du PO ni aucune entrée des registres (`restreint/ECARTS_DECISIONS_CODE.md` : 26 écarts, 8 points à confirmer, 7 propositions, qui restent la référence).
> **Les rangements ci-dessous sont mes classements de lecture, à corriger par le PO** : ils ne sont pas des décisions. Chaque entrée renvoie à son identifiant du registre.

## Les trois catégories

| Catégorie | Critère |
|---|---|
| **Risque de sécurité** | Qui peut agir, voir ou administrer : droits, autorité de décision, accès, reprise après sinistre |
| **Blocage fonctionnel** | Un circuit décidé n'existe pas, ou un dossier peut rester coincé sans alerte |
| **Amélioration secondaire** | Libellé, documentation, confort, idée à plus tard ; aucun usage empêché |

## 1. Risques de sécurité

| Id | Constat | Pourquoi ici | Remarque |
|---|---|---|---|
| **A1** | L'administrateur d'unité atteint tous les seuils par défaut des actes métier | Un compte technique peut trancher des échanges et publier des listes alors que la règle le lui interdit | 🟢 vérifié |
| **A2** | Les échanges de tours sont validés par qui gère la liste, pas par le COMAEQ ou son suppléant | Autorité de décision différente de celle décidée | 🟢 ; B1, B3 liés |
| **A3** | La publication d'une liste dépend d'un seuil réglable par bâtiment | Un bâtiment peut abaisser le seuil de publication | 🟢 |
| **A4** | Le commandant en second : même acte refusé par l'API et accepté par l'écran | Comportement de droits incohérent entre canaux | 🟢 ; B2 lié |
| **A14** | Passation : un chef de section lit la synthèse de tout le bâtiment, au lieu de sa seule section | Visibilité d'informations d'autres sections | 🟢 **confirmé par test (12/11/2026, comptes fictifs)** ; aucune fuite réelle alléguée |
| **A23** | Pas de limitation des tentatives de connexion, ni HSTS, ni réglage de proxy ; aucun serveur HTTPS livré | Accès et sécurité de transport | Cible (accès avec les SIC) ; ⚪ architecture à définir |
| **A24** | Aucune sauvegarde, restauration, supervision ni conservation des journaux | Perte de données non couverte, pas de reprise | 🟢 absence constatée ; D7 lié |
| **A25** | Un module désactivé reste accessible par l'API (lecture et écriture), l'administration, les tâches planifiées, l'accueil et le calendrier | Désactivation non étanche hors pages web, menu et recherche | 🟢 confirmé par test ; choix volontaire du code ; règle attendue à décider par le PO |
| **B1** | Suppléance du COMAEQ : principe décidé, procédure à confirmer | Autorité de substitution non définie | À confirmer |
| **B2** | Commandant en second : responsabilités attribuées, qui les attribue à confirmer | Même sujet que A4 | À confirmer |
| **B5** | Chef de liste des quarts : qui le désigne à confirmer | Désignation = source de droits | À confirmer |

## 2. Blocages fonctionnels

| Id | Constat | Effet | Remarque |
|---|---|---|---|
| **A20** | Une occurrence « En validation » n'a pas de sortie dédiée ; sorties par correction du compte rendu, par l'API « démarrer » (état incohérent) ou l'administration ; jamais en retard ; non liée au ticket ; suspend l'entretien récurrent d'une installation | Peut rester indéfiniment sans notification ni échéance | 🟢 confirmé par test ; règle de sortie à décider (D2) |
| **A15** | RETEX en une étape au lieu du circuit hiérarchique ; pas de demande de correction | Circuit décidé absent | 🟢 |
| **A16** | Le marquage « flotte » du RETEX ne transmet rien | Aucune transmission à un organisme | 🟢 ; D3 lié |
| **A17** | Appareillage : signature unique, ni fiche de référence, ni classification, ni circuit COMANAV | Circuit décidé absent ; Matrix reste un outil de suivi | 🟢 ; D4 lié |
| **A18** | Transfert de matériel sans circuit d'approbation | Pas de trace d'approbation | 🟢 |
| **A19** | Demande de places formation sans dossier vivant ni transmission formalisée | Circuit cible Notion absent | 🟢 |
| **A13** | Deux priorités au lieu de trois ; pas de règle d'abaissement | Nuance et hiérarchie de priorité absentes | 🟢 |
| **A21** | Périodicités nommées, outillage, durée indicative non développés | Fonctions décidées absentes | Cible non contradictoire |
| **A12** | Pas de page imprimable ni de réimpression versionnée de la feuille de service | Le BSC passe par le navigateur | Cible |
| **B3** | Échanges limités aux services à quai | Pas de règle pour les quarts à la mer ; ne pas généraliser sans validation | À confirmer |
| **B4** | Autorité cible de la déclaration d'accostage ou d'appareillage | Fonctionnement actuel documenté | À confirmer |
| **B6, B7** | Fin de journée d'une tâche ; ordre des grades | Valeurs à fournir par le PO | À confirmer |
| **D1, D2, D3, D4** | Ticket pour installation non conforme ; sortie de « En validation » ; transmission d'un RETEX ; classification « critique » | Propositions 🟣 | **Pas des décisions** |

## 3. Améliorations secondaires

| Id | Constat |
|---|---|
| **A5** | Identifiants stables (UUID, NNO) absents pour comptes, unités, tâches, listes |
| **A6** | Documentation du dépôt annonce 14 applications, il y en a 21 |
| **A7** | Droits à attributs codés au cas par cas, pas de moteur général |
| **A8** | Cahier des charges en partie obsolète (génération des tours, rondes, organisation miroir abandonnées) |
| **A9** | Deux bibliothèques déclarées sans usage constaté |
| **A10** | Vocabulaire cible (mission, capacité, dérogation…) sans équivalent dans le code |
| **A11** | Libellé « Mes tours de service » au lieu de « Mes tours de services » |
| **A22** | Script d'installation annonce Python 3.8, le projet suppose 3.12 |
| **A26** | Neuf modules sans API (cohérent avec la phase 7 différée) |
| **B8** | Durées de conservation des notifications, journaux et estimations à confirmer |
| **D5, D6, D7** | Favoris et formulaires RH ; observations de recette ; exploitation (D7 recoupe le sujet d'A24, classé en sécurité) |

## Lecture d'ensemble

- **Total** : 26 écarts, 8 points à confirmer, 7 propositions, chacun classé une seule fois (D7 recoupe le sujet d'A24 : A24, constat, est classé en sécurité ; D7, proposition, en secondaire).
- **Sécurité** : 8 écarts (A1, A2, A3, A4, A14, A23, A24, A25) et 3 points à confirmer (B1, B2, B5). **Aucun n'est une faille exploitée constatée** : ce sont des écarts entre la règle décidée et le comportement du code.
- **Blocage fonctionnel** : 9 écarts (A12, A13, A15 à A21), 4 points à confirmer (B3, B4, B6, B7) et les propositions D1 à D4.
- **Secondaire** : 9 écarts (A5 à A11, A22, A26), le point B8 et les propositions D5, D6, D7.
- **A20 est le seul écart pouvant coincer un dossier sans notification ni échéance** (l'occurrence reste visible en « À faire » et en supervision).
- Les décisions du PO ne sont pas modifiées ; les écarts ne sont pas corrigés ; aucun lot n'est lancé.
