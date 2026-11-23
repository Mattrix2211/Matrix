# Bilan final — Dossier technique intégral de Matrix, édition G0

> **Diffusion restreinte.** Date : 11/11/2026. Branche documentaire : `claude/fervent-wright-kl6gtx`. État du logiciel décrit : **état B**, `claude/l03-suppression-sure-v11` @ `6d6d0be`, **non fusionné dans `main`** ; l'état A (`main` @ `6ef16ad`) sert de comparaison.
> **Contraintes respectées** : aucun code applicatif modifié, aucune fusion dans `main`, aucune PR, aucun nouveau lot de développement (L04 non lancé), travail exclusivement sur la branche documentaire. Les 125 décisions du dossier V1.2 sont citées par identifiant, jamais rouvertes.
> **Ce bilan présente le dossier pour validation finale. Il ne vaut ni recette, ni homologation, ni autorisation de diffusion.**

---

## 1. Ce qui est livré

| Livrable | Contenu | Où |
|---|---|---|
| **26 chapitres** | Parties I à VIII du sommaire validé ; **19 fichiers diffusables** (usage, règles métier, circuits, parcours, cible, historique) et **22 fichiers restreints** (compléments techniques, architecture, données, sécurité, API, interactions, exploitation, qualité) | `diffusable/`, `restreint/` |
| **8 annexes** | A glossaire (diffusable) ; B matrice rôle × action ; C index des routes ; D index des modèles ; E tâches planifiées, commandes et variables ; F sources, branches, non vérifiés ; G couverture ; H index des schémas (diffusable) + H bis (restreint) | `diffusable/annexes/`, `restreint/annexes/` |
| **Registre des écarts** | 26 écarts d'implémentation (A1 à A26), 8 points à confirmer (B1 à B8), décisions non développées (partie C), **7 propositions à valider (D1 à D7)** | `restreint/ECARTS_DECISIONS_CODE.md` |
| **42 schémas** | Sources Mermaid et exports SVG lisibles hors ligne | `schemas/src/`, `schemas/svg/` |
| **Deux PDF** | **Diffusable** (105 pages) et **restreint** (142 pages), avec couverture, sommaire, signets, bandeau de diffusion en en-tête et numéros de page | `pdf/` |
| **Outils de contrôle** | Inventaire, vérification des références, cohérence, séparation, revue transversale, génération des annexes et des PDF | `outils/` |
| **Rapports** | Rapports de livraison des quatre ensembles et ce bilan | `RAPPORT_E1.md` à `RAPPORT_E4.md`, `BILAN_FINAL_G0.md` |
| **Mode d'emploi** | Où lire quoi, régénérer et contrôler | `00_LISEZ-MOI.md` |

Volume : environ 58 000 mots de chapitres (34 600 diffusables, 23 400 restreints) et 17 400 mots d'annexes.

### Les deux PDF

| Fichier | Contenu | Pages |
|---|---|---|
| `pdf/Matrix_Dossier_technique_G0_DIFFUSABLE.pdf` | 19 chapitres diffusables + annexes A et H | 105 |
| `pdf/Matrix_Dossier_technique_G0_RESTREINT.pdf` | 22 fichiers restreints, registre des écarts, annexes B à G et H bis | 142 |

Les annexes larges (matrice de droits, routes, modèles, tâches, sources, couverture, registre des écarts) sont imprimées **en paysage**. Les sommaires renvoient par liens ; la navigation par **signets** est disponible dans le lecteur PDF. **Avant l'export, le script refuse de produire un PDF si les deux périmètres se mélangent** ; le texte extrait du PDF diffusable ne contient aucune référence de code, variable d'environnement, commande d'exploitation ni adresse.

## 2. Revue transversale demandée

| # | Vérification | Résultat | Preuve |
|---|---|---|---|
| 1 | **26 chapitres et 8 annexes présents et cohérents** | ✅ 26 sur 26 ; 8 sur 8 (+ H bis) ; structure homogène (encadré lecteur, étiquettes, limites, sources) | `controle_transversal.py` ; `controle_coherence.py` : 51 fichiers, 0 erreur |
| 2 | **Tous les modules et circuits inventoriés sont couverts** | ✅ 22 paquets cités ; **135 modèles sur 135** expliqués ; **14 modules** activables cités ; **20 tâches planifiées**, **18 commandes** et **35 actions à seuil** dans les annexes E et B ; **721 routes** (185 pages et 171 API détaillées en annexe C, 365 d'administration résumées) ; **50 circuits métier** « rédigés » dans la matrice | Annexe G : aucun circuit « à vérifier » |
| 3 | **Règles PO, comportements réels et non vérifiés distingués** | ✅ quatre étiquettes : 🟢 réel (81 marques), 🔵 cible validée (79), 🟣 proposition à valider (4), ⚪ non vérifié (193) ; chaque circuit à écart décrit **l'actuel et le cible séparément** (échanges, listes, tâches, RETEX, appareillage) ; aucune cible rédigée au présent relevée à la relecture des chapitres 12, 15, 16 et 25 (les autres chapitres n’ont pas fait l’objet de cette relecture ciblée) | Légende au chapitre 3 ; registre des écarts |
| 4 | **Les schémas correspondent aux explications** | ✅ 42 sur 42 exportés, référencés et indexés ; **relecture visuelle** de ceux de l'ensemble 3 et 4 ; **6 schémas corrigés** pour s'aligner sur les chapitres (S24, S27, S28, S30, S31, S33) | Annexes H et H bis |
| 5 | **Références de code et liens valides** | ✅ **1 093 références** vérifiées sur l'état B (fichier, ligne, symbole) ; liens et images résolus ; 70 identifiants `DEC-…` cités, **70 existent** | `verifier_references.py` : 0 erreur |
| 6 | **Contradictions centralisées, aucune décision inventée** | ✅ tout est au registre (§4) ; deux identifiants inventés par erreur dans des premiers jets ont été **détectés et supprimés** avant livraison ; les règles cibles non décidées sont marquées « à confirmer » ou 🟣 | Registre ; annexe F §F.3 |
| 7 | **Compréhensible par un marin, un responsable, un développeur** | ⚠️ **Conçu pour, non éprouvé** : chaque chapitre commence par « ce que fait le marin », puis « ce que font les responsables », avec des exemples fictifs, des circuits et des schémas ; les mécanismes sont renvoyés dans la partie restreinte. **Aucun lecteur réel n'a relu le dossier** : la relecture par un marin, un responsable et un développeur reste à faire | §6 |

### Corrections issues de cette revue (en plus de l'ensemble 4)

- **Chapitre 14 / A19** : l'organisme de formation **est** une unité École ou Centre de formation ; mon rapport de l'ensemble 3 disait le contraire. Corrigé.
- **Chapitre 14** : des habilitations peuvent bloquer un échange de tour de service ; corrigé.
- **Annexe G** : déplacée dans `restreint/annexes/` (elle était dans `couverture/`).
- **Annexe H** : scindée pour que l'index diffusable ne cite que des schémas diffusables.
- **Parties diffusables** : toutes les références de code retirées.

## 3. Ce que dit le dossier du logiciel, en dix lignes

1. Matrix est une application Django (22 paquets, 135 modèles) qui sert **un bâtiment à la fois**, sans Internet.
2. Le **marin** voit sa journée ; le **chef** supervise son périmètre ; l'**acteur à terre** consulte et commente.
3. Les **droits** reposent sur un rôle, un périmètre, des seuils configurables par bâtiment et des désignations ; le **serveur décide toujours**.
4. Les **quarts et services** suivent un circuit proposer → valider → publier ; la feuille de service a un rédacteur désigné et des visas.
5. La **maintenance** va du plan à l'exécution guidée ; un contrôle non conforme sur un matériel mobile crée un **ticket** automatique ; la clôture d'une installation critique exige une confirmation.
6. Le **stock** est un solde justifié par des mouvements immuables, avec alertes de pénurie.
7. Les **formations** ont trois circuits (demande de places, candidature, formation proposée par le bord) ; une qualification manquante ne bloque pas une tâche ordinaire.
8. Les **documents** sont versionnés et validés ; un **RETEX** validé devient un document et déclenche des actions.
9. La **préparation à l'appareillage** est une session de points à cocher et une signature ; **Matrix ne délivre jamais l'autorisation d'appareiller**.
10. **Ni sauvegarde, ni supervision, ni serveur de production ne sont fournis** ; la mise en service opérationnelle n'est **pas autorisée** (NO GO du PO).

## 4. Contradictions, écarts et propositions — centralisés

Tout figure dans `restreint/ECARTS_DECISIONS_CODE.md`. Synthèse :

| Famille | Contenu | Nombre |
|---|---|---|
| **Écarts d'implémentation** (décision validée non respectée par le code) | A1 à A4 (administrateur technique, échanges de tours, publication des listes, commandant en second), A11 à A21 (libellés, impression, priorités, passation, RETEX, appareillage, transfert, formation), A22 à A26 (documentation d'installation, sécurité d'accès, sauvegarde, modules désactivés, modules sans API) | 26 au total avec A5 à A10 (documentation et cahier) |
| **Points à confirmer** | B1 à B8 : suppléance du COMAEQ, commandant en second, échanges à la mer, accostage et appareillage, chef de liste des quarts, fin de journée d'une tâche, ordre des grades, conservation | 8 |
| **Décisions non développées** (non contradictoires) | Partie C | voir registre |
| **Propositions à valider (🟣)** | D1 ticket pour installation non conforme ; D2 sortie de « En validation » ; D3 transmission d'un RETEX ; D4 autorité de classification « critique » ; D5 favoris, annuaire, formulaires RH ; D6 observations de recette ; D7 sauvegarde et exploitation | 7 |
| **Non vérifiés** | Annexe F §F.5 | 174 passages |

**Écarts les plus lourds de conséquences** (à arbitrer par le PO, sans correction demandée ici) : A1 (l'administrateur technique peut agir sur les circuits métier), A2 et A3 (échanges et publication), A4 (droits du commandant en second), A15 (RETEX en une étape), A17 (appareillage à signature unique), **A20 (occurrence « En validation » qui peut rester bloquée sans alerte)**, A23 (sécurité d'accès), A24 (aucune sauvegarde).

## 5. Limites de ce dossier

- **Un état du code, pas un état déployé.** Aucune instance de production n'existe ; rien n'a été mesuré (charge, performance).
- **Tests** : sous-ensembles rejoués sur l'état B (360 + 1 464 + 1 491 + 1 434 tests, tous OK) ; **la suite complète de 3 963 tests n'a pas été rejouée** (chiffre repris des comptes rendus de lots). Les tests de `documentation` (9) et `retex` (5) sont **faibles**.
- **Non rejoués** : navigateurs (Chrome, Firefox, Safari), mobile, lecteurs d'écran, impression physique, Windows, PostgreSQL, Redis et Celery réels, Web Push réel, export PDF métier (WeasyPrint).
- **Sources** : quelques pages Notion vues seulement par recherche ; le sous-module `design/` est vide ; aucune exigence SIC chiffrée n'a été fournie ; le *Guide du marin 2023* n'a jamais été disponible (non utilisé).
- **Plan en 28 lots** : proposition du dossier V1.2, **à valider** ; seuls L01, L05, L02, L03 sont livrés, sur l'état B non fusionné.
- **Classification et destinataires** des deux parties : **à valider séparément** ; la séparation diffusable / restreint n'est pas une autorisation de diffusion.

## 6. Ce que je vous demande pour la validation finale

1. **Valider (ou corriger) la couverture et la méthode** — pas une relecture ligne à ligne : cette validation reposera sur ce bilan et sur les contrôles automatiques.
2. **Faire relire** le chapitre « marin » de quelques chapitres clés (6, 8, 12, 17) par un marin, un responsable et un développeur : c'est la seule vérification de lisibilité qui manque.
3. **Trancher, quand vous le souhaiterez**, les propositions D1 à D4 et les écarts lourds de la partie 4 ; **le dossier ne les tranche pas**.
4. **Décider du sort de l'état B** (fusion dans `main`, lots suivants, L04) : **hors périmètre de ce dossier**, rien n'a été entrepris.
5. **Classer** les deux PDF (destinataires, niveau de diffusion) avant toute transmission.

## 7. Reproduire les contrôles

```bash
python docs/dossier-technique/outils/verifier_references.py <racine_etat_B> docs/dossier-technique origin/claude/eager-hopper-2cbcqh
python docs/dossier-technique/outils/controle_coherence.py docs/dossier-technique
python docs/dossier-technique/outils/controle_separation.py docs/dossier-technique
python docs/dossier-technique/outils/controle_transversal.py docs/dossier-technique
python docs/dossier-technique/outils/construire_pdf.py docs/dossier-technique docs/dossier-technique/pdf
```

Détail des commandes d'inventaire et de génération : `00_LISEZ-MOI.md`.
