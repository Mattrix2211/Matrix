# Plan de la passe finale avant validation de V2

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire. Date : 19/11/2026. **Ce plan n'exécute rien** : aucune source, aucun PDF ni aucune capture n'a été modifié pour le préparer. Il attend votre approbation. Aucun changement applicatif, aucune décision métier nouvelle, aucune PR, aucune fusion dans `main`, aucune phase 13.

## 1. Constat sur la nouvelle incohérence (tickets automatiques)

Vérifié : le fonctionnement actuel est celui de `12_fiche_maintenance.md`. Un compte rendu non conforme crée un ticket **uniquement pour un matériel mobile** ; pour une **installation**, aucun ticket n'est créé et l'écran de fin l'annonce à tort (NE-07). Le ticket pour une installation est la **proposition 🟣 D1**, non arbitrée.

| # | Fichier | Formulation | Problème |
|---|---|---|---|
| T1 | RF `03_vue_ensemble.md` ligne 103 (journée-type du marin) | « Un relevé sort de la normale : un **ticket correctif** est créé et notifié au chef » | Faux de deux façons : un relevé hors plage ne crée **pas** de ticket (l'écran propose un lien pré-rempli vers une anomalie) ; le ticket automatique vient d'un contrôle non conforme sur un matériel mobile |
| T2 | RF `03_vue_ensemble.md` ligne 124 (enchaînements) | « une exécution de maintenance non conforme crée un ticket correctif » | Généralisation : vrai pour un matériel mobile seulement |
| T3 | DT `21_interactions_modules.md` ligne 20 (signaux) | « Ticket créé quand une exécution est non conforme » | Même généralisation (les lignes 28 et 42 du même fichier sont, elles, correctes) |
| T4 | Schémas `S24` et `S26` (sources `.mmd`, tableaux associés) | « non conforme sur un matériel » | Ambigu : « matériel » n'exclut pas clairement les installations ; à écrire « matériel mobile ». S26 figure dans RF (fiche Maintenance) et DT (chapitre Maintenance) |

Recherche étendue aux trois documents, au registre et aux schémas (mots « ticket », « non conforme », « automatique ») : aucune autre généralisation. Guide : corrects (`12_maintenance.md`, `00_matrix_en_une_page.md`, `18_limites_visibles.md`). Registre : corrects (NE-07, D1). Résumé du décideur et fiche Maintenance : corrects.

**Corrections proposées** (la distinction actuel / proposition est conservée) :
- T1 → « Il **exécute** une maintenance guidée. Si un contrôle sur un **matériel mobile** est non conforme, un **ticket correctif** est créé automatiquement et notifié au chef ; sur une **installation**, aucun ticket n'est créé (le marin signale lui-même une anomalie). Un relevé hors plage propose un lien pré-rempli vers une anomalie (🟢) ; 🟣 un ticket automatique pour une installation reste une proposition (D1), non arbitrée. »
- T2 → « une **exécution non conforme sur un matériel mobile** crée un **ticket correctif** (maintenance → logistique) ; pour une installation, aucun ticket n'est créé (NE-07 ; 🟣 proposition D1) ; »
- T3 → « Ticket créé quand une exécution **sur un matériel mobile** est non conforme (pas pour une installation) ; … »
- T4 → libellé « non conforme sur un matériel mobile » dans S24 et S26 ; SVG régénérés.

## 2. Arbitrages D-04 à D-12

### D-04 — préserver toutes les relations
Concerne cinq schémas aujourd'hui présentés en tableau : **S02** (carte des modules, RF p.16-17), **S14** (sources du calendrier, RF p.53), **S22** (équiper depuis le catalogue, RF p.82), **S27** (stock et pièces, RF p.95), **S38** (feuille de route, RF p.121-122).
- Chaque schéma est **redessiné en vrai schéma de flux** (flèches étiquetées, regroupements), sans relation nouvelle : les liaisons viennent des tableaux « De / Condition / Vers » existants et, pour S02, de l'inventaire des dépendances du code (généré), non d'une interprétation.
- **Tous les tableaux « De / Condition ou passage / Vers » sont conservés** (ils sont le tableau de relations complémentaire). Seul est retiré le tableau d'éléments (« SRC, FIL, CAL… ») dont les codes n'ont pas de sens pour un lecteur et dont chaque libellé figure déjà dans les cellules « De » et « Vers » : **aucune relation ni information n'est supprimée**. Les dépendances de S02 sont vérifiées une à une contre ce tableau avant publication.
- Contrôle de lisibilité : texte des nouveaux schémas ≥ 8 pt à la largeur de page (outil existant), comme pour les 46 autres.

### D-05 — parenthèse mal formée
RF p.127 : « Dossier V1.2 (, comptes rendus L01, L05, L02, L03) » devient « Dossier V1.2 (comptes rendus des lots L01, L05, L02 et L03) ». Source : `25_cible_et_feuille_de_route.md`, ligne « Sources » (ligne 143) du chapitre 21 « Fonctionnement cible et feuille de route ». Même défaut recherché dans toute la série : un seul cas.

### D-06 — index des schémas exhaustif
`31_index_des_schemas.md` est aujourd'hui rédigé en tableau de 24 lignes aux libellés hétérogènes. Il devient un tableau **généré** des **46 schémas** : N° (S01…S42, avec les variantes S09d, S10b, S25d, S28b), titre homogène, forme (figure, figure CIBLE ou tableau de relations), document et section où il figure (guide : aucun ; référentiel : section ; dossier technique : section). Les références utilisent les numéros de section résolus à la construction. Génération par script, pas à la main ; contrôle automatique que chaque schéma du dépôt y figure.

### D-07 — provenance historique des preuves de tests
Reformulation sans nouveau test ni nouvelle preuve, en distinguant clairement trois cas :
- **Source historique** : « compte rendu de lot de l'édition initiale (11/11/2026) : n tests OK sur l'ensemble de sept paquets, **non rejoués pour la révision 2** ». Concerne RF `13_fiche_logistique`, `14_fiche_formations`, `15_fiche_documentation_retex` (ligne « suite des 7 paquets de l'ensemble 3 »), `16_fiche_preparation_appareillage`, et DT `24_qualite_contribution` (lignes 17 et 109 : « ensemble 1 : 360 tests ; ensemble 2 : 1 464 ; ensemble 3 : 1 491 »).
- **Rejeu récent** : seuls les tests réellement exécutés dans cette révision sont cités comme tels (par exemple les trois suites de la prise en main développeur, DT).
- L'étiquette 🟢 est maintenue pour le fonctionnement décrit (confirmé par le code et, le cas échéant, par le navigateur) ; la phrase sur les tests passe en ⚪ « non rejoué ».
- Corrections de mêmes natures dans DT `08_quarts_services_feuille_technique.md` ligne 124, dont la phrase « comptes rendus de lots compte rendu du lot L02 » est mal formée (défaut de mes remplacements antérieurs).

### D-12 — captures partielles
17 captures sont en « partie haute ». Leur légende porte déjà « Partie haute de l'écran : la page se poursuit en dessous ». Relecture des pages concernées : l'information nécessaire au parcours est visible (boutons d'action de l'exécution de maintenance, bouton « Enregistrer la correction » de l'état « En validation », « Valider et clôturer » de l'appareillage, filtres et onglets des quarts, actions de la liste des échanges). **Aucune modification proposée.** Option, non retenue par défaut : un bandeau « CAPTURE PARTIELLE » plus visible dans chaque légende ; elle coûterait une reconstruction du guide sans changer sa pagination. Dites-moi si vous la souhaitez.

## 3. Documents réellement concernés et impact sur la pagination

| Document | Modifications | Reconstruction | Pagination prévue |
|---|---|---|---|
| **Référentiel** | T1, T2, T4 (S24, S26) ; D-04 (5 schémas, 5 tableaux d'éléments retirés) ; D-05 ; D-06 (index) ; D-07 (4 fiches) | **1** (la 7e depuis la candidate) | 135 → **136 à 138** : chaque schéma ajoute environ 0,3 page et le tableau retiré en gagne environ 0,25 ; l'index passe de 24 à 46 lignes (+1 page). Pages de contenu à revoir : 16-17, 53, 82, 95, 121-122, 127, 135-136, plus les pages voisines et la fiche Maintenance (S26) |
| **Dossier technique** | T3, T4 (S26) ; D-07 (chapitre Qualité) ; phrase mal formée du chapitre Quarts | **1** (la 3e) | 94 → **94** (changements de texte et de libellé de schéma, sans effet attendu sur la pagination) |
| **Guide utilisateur** | aucune | **0** (reste à 5) | 86 inchangé |
| **Registre** | aucune | **0** (reste à 2) | 52 inchangé |

Les empreintes du texte extrait du guide et du registre doivent rester identiques à celles de V2 : c'est le contrôle de non-régression de ces deux documents.

## 4. Budget de reconstructions (dépassement documenté)

| Document | Candidate (phase 10) | Après la candidate | Dont dépassement du budget de 2 | Prévu par la passe finale |
|---|---|---|---|---|
| Guide utilisateur | 1 | **5** | + 3 | 0 |
| Référentiel | 1 | **6** | + 4 | 1 (7) |
| Dossier technique | 1 | 2 | 0 | 1 (3, +1) |
| Registre | 1 | 2 | 0 | 0 |

Causes du dépassement : corrections de rendu E1-E5 (une reconstruction), recadrage des captures et pagination (guide : 4 reconstructions), renvois, chemins `.md`, numéros de chapitre de l'ancienne édition et ponctuation des paragraphes « Sources » découverts en inspectant les pages tardives (référentiel : 5 reconstructions). Le budget n'a pas été remis à zéro ; chaque dépassement est tracé dans `RAPPORT_V2.md` §6. La passe finale regroupe toutes les corrections en **une seule reconstruction par document concerné**.

## 5. Ordre d'exécution après approbation

1. Sources : T1-T4, D-04 (schémas `.mmd` et suppression des tableaux d'éléments), D-05, D-06 (générateur de l'index), D-07.
2. Régénération des SVG et contrôle ≥ 8 pt ; contrôle HTML des quatre documents (C1 à C14 sur sources) **avant** toute impression.
3. **Une** reconstruction du référentiel et **une** du dossier technique ; guide et registre inchangés (empreintes du texte comparées).
4. Contrôles C1 à C14 sur les PDF, C12 (deux constructions), statuts des 125 décisions, recherche automatique de « ticket » + « non conforme » dans les PDF.
5. Inspection : pages modifiées et pages voisines à 96 ppp ; journal V2 mis à jour page par page (statut « inspectée » seulement pour les pages réellement vues).
6. Rapport de passe finale, commit, push. Arrêt avant validation V2 et avant phase 13.

## 6. Points à valider

1. Approbation du plan ci-dessus (documents concernés : référentiel et dossier technique).
2. Accord pour **une reconstruction supplémentaire du dossier technique** (3e) : elle n'est pas contournable si T3 doit être corrigé dans le PDF.
3. Confirmation de la suppression du seul tableau d'éléments (codes SRC, FIL…) des cinq schémas, les tableaux de relations étant intégralement conservés.
4. D-12 : captures partielles conservées telles quelles (recommandé) ou bandeau « CAPTURE PARTIELLE » (une reconstruction du guide).
