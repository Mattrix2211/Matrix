# A. Registre des décisions PO

Base de référence : **V1.1, commit `1c37f22`** (branche `claude/iteration-ux-v11-20261102`), validée par le PO comme base fonctionnelle auditée. `main` (`6ef16ad`) n'a pas été touchée.

## Légende des sources

| Code | Source |
|---|---|
| S1 | Message du PO « Consolidation des décisions PO » (§1 à §17) |
| S2 | Message du PO de précisions (arbitrages sur RETEX, organisation, validation des tâches, rattachement incomplet, appareillage, départs, passation, QR) |
| S3 | Message du PO du 10/11 (échanges de tours, qualifications, suppléance, organisation, RETEX, appareillage, priorités, sources) |
| R06 | `docs/audit-general-v11/06_DECISIONS_PO.md` (branche d'audit, `4aa4dcf`) : DP-01 à DP-14, blocs A à D |
| N1 | Notion « Cahier des charges » (Matrix 2.0), édité le 10/10/2026 |
| N2 | Notion « Organigramme et rôles » (31/10/2026) |
| N3 | Notion « 13 — Décisions Matrix et gouvernance fonctionnelle » (31/10/2026) |
| N4 | Notion « Cap UX/UI Naval Premium » (29/10/2026) |
| N5 | Notion « Ordre de travail Claude — Correctifs métier et UX V1.1 » (01/11/2026) |
| N6 | Notion « Feuille de Route » (10/10/2026) |
| N7 | Notion base « Tâches en cours » (état lu en novembre 2026) |
| N8 | Notion « 06 — Service courant, BSC, feuille de service et commissariat » |
| N9 | Notion « Audit métier Matrix × Guide du marin 2023 » (31/10/2026) |

**Statuts** : *Confirmée PO* = formulée par le PO (S1, S2, ou page Notion qui l'indique) ; *Orientation PO* = direction donnée sans règle complète ; *Proposition technique* = ma proposition, **non** une décision PO ; *Règle technique évidente* = conséquence directe d'une règle du dépôt, à distinguer d'une décision métier ; *Ouverte* = non décidée (voir `F_QUESTIONS_RESIDUELLES.md`).

**Limite de lecture** : les pages Notion portent l'état de vérification « non vérifié » ; les comptes rendus de développement et les « relectures indépendantes » qu'elles contiennent ne valent pas recette du PO. Je n'ai pas lu : les pages 01 à 05, 07 à 12 sous « Organigramme et rôles », « Vision et Objectifs », « Recette UX V1.1 », « Tranche 1 », ni le *Guide du marin 2023* (jamais accessible ici, cité uniquement via Notion).

## Plan du registre

- **A.1** — 123 décisions des messages S1, S2 et S3 : `A1_DECISIONS_S1_S2.md` (une décision par entrée, avec ID, source, statut, acteurs, règle, exceptions, critères de validation).
- **A.2** — décisions du dépôt (DP et blocs A à D) et leur sort : ci-dessous.
- **A.3** — décisions Notion pertinentes : ci-dessous.
- **A.4** — propositions techniques et règles techniques évidentes : ci-dessous.

## A.2 Décisions du dépôt (`06_DECISIONS_PO.md`) et leur sort

| ID | Statut dans le dépôt | Sort après S1/S2 et Notion |
|---|---|---|
| DP-01 | Décision : `main` intacte, audit sur branche dédiée | **Confirmée et respectée.** Reste ouverte : l'autorisation de fusionner la V1.1 (AUD-001 y est corrigé). |
| DP-02 | Ouverte : passation maintenue ou différée | **En grande partie tranchée** par S1/S2 (DEC-PRE-02) et N3 (« maintenue en V1, configurable, activée par défaut »). Reste l'alignement de Notion (DP-04). |
| DP-03 | Orientation (option B complétée par D) | **Confirmée sur le fond par S2** (DEC-ORG-02). Les modalités du marin transversal restent ouvertes (A1 → F-10). |
| DP-04 | Ouverte : mettre à jour cahier et feuille de route | Ouverte. Les pages Notion lues citent encore `dfd6a3c` (AUD-004). |
| DP-05 | Ouverte : données de Rondes | **Tranchée par N5** : conserver données et migrations tant qu'aucune suppression physique n'est autorisée. |
| DP-06 | Ouverte : route QR active | **Tranchée par S2** (DEC-PRE-04) : reporter sans suppression précipitée ; la route est conservée. |
| DP-07 | Ouverte : CI hors Internet | Ouverte (F-14). |
| DP-08 | Ouverte : tests navigateur versionnés | Ouverte (F-14). |
| DP-09 | Orientation : titulaire, suppléant, supérieur distincts ; admin technique sans visa métier | **Confirmée par S1** (DEC-DRT-02, DEC-SUP-*). Mécanisme d'ensemble : F-01. |
| DP-10 | Orientation : reverse proxy TLS | Maintenue ; décision réservée aux experts SIC (S1 §13, DEC-PRE-06). |
| DP-11 | Besoin d'import en masse à terme | Confirmée (AUD-012). Non planifiée. |
| DP-12 | 404 initial « non reproduit » | Confirmée (AUD-026 corrigé en V1.1, présent sur `main`). |
| DP-13 | Orientation : gérer la structure localement, archiver plutôt que supprimer | **Confirmée par S1/S2** (DEC-DRT-05, DEC-MUT-07). |
| DP-14 | Revue des droits en dur au cas par cas | En cours (P05), non terminée (AUD-022). |

### Blocs A à D de l'audit

| Question | Sort | Renvoi |
|---|---|---|
| A1 marin transversal (T1/T2) | Ouverte | F-10 |
| A2 fonction « gestion de la structure » | Ouverte | F-10 |
| A3 niveau de réorganisation | Ouverte | F-10 |
| A4 grâce pour comptes « à compléter » | **Tranchée par S2** : pas d'accès sans autorisation ; la grâce implicite est écartée | DEC-DRT-06 |
| A5 départ d'un marin | **Tranchée par S2** : désactiver ou transférer, historique conservé. Reste : suppression d'un compte sans historique | DEC-MUT-07, F-05 |
| A6 réaffectation d'installation | **Tranchée par S1 §11** (approbation des chefs de service) ; reste le vocabulaire chef de service / commandant adjoint | DEC-MAT-01 à 04, IM-11 |
| B1 introduction des droits par fonction | Ouverte (ordre de mise en œuvre) | F-01 |
| B2 intervention d'exception du supérieur | Ouverte | F-01 |
| B3 publication des listes de service | **Tranchée pour la feuille de service** (COMAEQ ou suppléant habilité) **et pour les échanges** (S3). **Ouverte pour les listes de quarts et de gardes** (chef de liste vs COMAEQ) : contradiction C-1 | DEC-FDS-02, DEC-FDS-07, J |
| B4 règles métier au cas par cas | Prêt à appareiller : tranché en partie (DEC-APP-*) ; absences et bilans : ouverts | F-07, DEC-PRE-01 |
| B5 validation d'un RETEX | **Caduque** : remplacée par le circuit hiérarchique de S1/S2 | DEC-RTX-01 |
| C1 verrou de démonstration | Priorité confirmée (N4, N7) ; modalités = P06, non validées formellement | AUD-009 |
| C2 à C4 PKI, serveur, sauvegarde | Réservées aux experts SIC (S1 §13) | DEC-PRE-06 |
| C5 limitation des connexions | Ouverte, avec les SIC | F-11 |
| D « Chemin de non-conformité sur installation » | Ouverte | F-12 |
| D « Secteur obligatoire pour une installation » | Ouverte | F-03 |
| D « Niveau d'annonce Urgent/Critique » | Ouverte | F-08 |
| D « Déroulé du ticket correctif » | Ouverte | F-04 |
| D « Composition-type d'une fraction à quai » | Principe validé (N8), GO d'implémentation requis | F-13 |
| D « Prêt à appareiller » | Tranché en grande partie (S1 §8, S2) ; reste la définition des contrôles obligatoires | F-07 |
| D « Complément de la démonstration » | Après les corrections ; GO du PO | AUD-036 |

## A.3 Décisions Notion pertinentes

| ID | Source | Décision | Statut | Rapport avec ce dossier |
|---|---|---|---|---|
| NOT-01 | N2, N3 | Hiérarchie configurable par navire : commandant → second → COMAEQ/COMOPS/COMANAV/COMAVIA → services → secteurs → sections → équipiers ; chaque service rattaché au COMA compétent | Confirmée PO | Résolution des visas par fonction (AUD-014) |
| NOT-02 | N3 | Un visa COMA se résout sur le COMA du service concerné ; sans titulaire, il reste en attente avec signalement ; un administrateur désigne le titulaire sans viser | Confirmée PO | DEC-DRT-02 |
| NOT-03 | N3 | Exception de la feuille de service : poste COMAEQ vacant → commandant de l'équipage, tracé et signalé ; un titulaire absent n'ouvre pas l'exception | Confirmée PO | DEC-FDS-02 |
| NOT-04 | N3 (19/10) | Chaque équipage, en mer ou à terre, a sa feuille de service ; pas de validation croisée par le seul grade | Confirmée PO | DEC-FDS-12 |
| NOT-05 | N2, N3 | Fiche d'installation : section/secteur → chef de service → commandant adjoint compétent | Confirmée PO | DEC-APP-03, DEC-OUT-05 |
| NOT-06 | N2, N3 | Fiche matériel flotte : 7 étapes jusqu'au catalogue flotte | Confirmée PO | idem |
| NOT-07 | N2, N3 | Compte rendu d'intervention : notifié au chef de secteur, sans visa obligatoire, modifications tracées | Confirmée PO | DEC-ANO-04 |
| NOT-08 | N3 | Commandement à terre sans rattachement ni habilitation : lecture seule, pas d'écriture métier par défaut ; pas de nouveau système de délégation en V1 | Confirmée PO | Tension avec S1 §10 (CT-02) |
| NOT-09 | N3 | Commandant en second : vision globale, écritures limitées aux responsabilités attribuées ; suppléance du commandant pour la relève | Confirmée PO | DEC-DRT-01 |
| NOT-10 | N1, N6 | La génération automatique de répartition des quarts et services est abandonnée ; planification manuelle avec contrôle des contraintes | Confirmée PO | Cahier §8, §10, §11 obsolètes (CT-09) |
| NOT-11 | N5 | Supprimer Rondes de Matrix (navigation, accueil, recherche, routes) en préservant données et migrations | Confirmée PO | AUD-007, DP-05 |
| NOT-12 | N3 | Synthèse de passation maintenue en V1 ; QR codes hors V1 ; service à quai, garde, quart = notions distinctes | Confirmée PO | DEC-PRE-02, DEC-PRE-04 |
| NOT-13 | N8 | Fraction de service à quai : contrôler la présence d'un titulaire par poste requis ; pas de relève interne ni de vérification automatique des qualifications à ce stade | Confirmée PO (principe) | DEC-FDS-08, DEC-QUA-01 |
| NOT-14 | N8 | Tableau de quart à la mer et feuille de service sont deux supports distincts ; tableau imprimable par équipe | Confirmée PO | Ne pas injecter les quarts dans la feuille |
| NOT-15 | N8 | Régimes de quart : bordées (2), tiers (3), au quart (4), cinquième (5), sixième (6) ; « de musique » ; « homme mort » | Confirmée PO (vocabulaire d'usage) | Aucun rythme codé en dur |
| NOT-16 | N5 | Désignation nominative du rédacteur de la feuille (bâtiment, équipage, marin) ; accord de principe ; autorité de désignation à arbitrer | Accord de principe (relecture ChatGPT, pas recette PO) | DEC-FDS-01 ; code V1.1 : COMAEQ de l'équipage |
| NOT-17 | N4 | Aide progressive réversible ; pas de profil débutant/expert opaque ; droits toujours appliqués côté serveur | Confirmée PO | DEC-UX-10 |
| NOT-18 | N5 | Bandeau supérieur ardoise `#344A63` ; recette visuelle du PO réservée | Sous réserve de recette | Hors périmètre du dossier |
| NOT-19 | N3 (31/10) | Directive : logique de marin militaire — grade ≠ fonction ≠ habilitation ≠ périmètre ; ne pas sur-automatiser ; proposer avec alternatives | Confirmée PO (méthode) | Règle de rédaction de ce dossier |
| NOT-20 | N2, N3 | Organismes à terre comme unités ; circuits PÉPIN, CRAT, RAV/c à documenter avant implémentation ; pas de développement majeur pendant la consolidation | Orientation PO | Hors périmètre |
| NOT-21 | N2 | Adjudant de compagnie, OSS : fonctions métier, pas des permissions nouvelles | Confirmée PO | Hors périmètre immédiat |
| NOT-22 | N7 | Rattachement organisationnel obligatoire pour tout compte opérationnel | Décision produit validée, « À faire plus tard » | DEC-DRT-06 |
| NOT-23 | N7 | Calendrier « Mon quotidien » : activités du marin d'abord, vue collective séparée | Décision produit validée, « À faire plus tard » | AUD-025 |
| NOT-24 | N7 (28/10) | Échanges de garde : validation par le chef de liste habilité | Décision produit du 28/10, **remplacée par S3 (10/11)** : décision finale du COMAEQ ou de son suppléant habilité ; le chef de liste instruit | DEC-FDS-07, DEC-FDS-13 (CT-01 résolue) |
| NOT-25 | N7 | Idées futures : épingler les rubriques, recherche de personnes, qualifications automatiques des postes, formulaires RH | À faire plus tard | DEC-UX-04, DEC-UX-09 (S1 les rend actuelles) |
| NOT-26 | N7 | Prêt à appareiller et veille d'appareillage : cadrages « À faire plus tard / ne pas développer » | Cadrage ancien | S1 §8, S2, S3 retiennent les règles ; le calendrier reste à votre main (CT-05) |
| NOT-27 | N7 (02/10) | Mutation : formations et qualifications suivent le marin ; l'historique d'activité reste la propriété de l'ancien bâtiment ; les compteurs d'équité ne suivent pas ; dépend de l'architecture de déploiement | Confirmée PO | DEC-MUT-*, lot L25 reporté |
| NOT-28 | N7 (28/10) | Rattachement obligatoire : aucun accès implicite du seul fait du grade, de la fonction ou du rattachement | Confirmée PO | DEC-DRT-06 |
| NOT-29 | N7 (06/10) | Prêt à appareiller : équipiers et chefs de section saisissent ; chefs de secteur et de service modifient ; niveaux au-dessus en lecture | Confirmée PO (règle de droits) | DEC-APP-02 ; à rapprocher du circuit S1 §8 |
| NOT-30 | N7 (20/10) | Veille d'appareillage : modèles de checklists créés et modifiés par les chefs de secteur habilités, sans modification du code, versionnés ; la clôture n'est jamais une déclaration d'aptitude | Confirmée PO | DEC-APP-*, DEC-APP-13 ; validation des modèles non définie (C-2) |
| NOT-31 | N7 (28/10) | `seed_demo` : refus hors DEBUG, mots de passe non prévisibles ou saisis, noms de bâtiments fictifs | Confirmée PO | AUD-009, AUD-024, lot L01 |

## A.4 Propositions techniques (non validées par le PO)

| ID | Proposition | Rattachée à |
|---|---|---|
| PT-DUR-01 | Durée indicative = médiane des N dernières réalisations valides (N=5 par défaut, configurable). Médiane plutôt que moyenne : insensible aux valeurs extrêmes. | DEC-DUR-01 |
| PT-DUR-02 | Une mesure est écartée si elle sort de médiane ± k·MAD (k=3 par défaut). Pas d'actualisation avant 3 mesures valides. | DEC-DUR-05 |
| PT-DUR-03 | On mesure le **travail effectif** : somme des périodes « En cours » ; les périodes « Bloquée », attente de pièces ou interruption déclarée sont exclues. | DEC-DUR-05 |
| PT-DUR-04 | Deux mesures par réalisation : temps écoulé (début → fin) et charge en heures-personnes (participants × durée de présence ; approximation signalée si la présence n'est pas saisie). | DEC-DUR-04 |
| PT-DUR-05 | Une ligne d'historique par actualisation (ancienne valeur, nouvelle, N, méthode, date). Actualisation appliquée seulement si l'écart dépasse un seuil (10 % par défaut) pour éviter le bruit. | DEC-DUR-02, 03 |
| PT-DUR-06 | Une correction manuelle du chef de secteur prime et suspend l'actualisation automatique jusqu'à ce que le chef la réactive. | DEC-DUR-06 |
| PT-DUR-07 | Granularité : par fiche et par installation, avec repli sur la fiche. Paramètres (N, k, seuil) dans les réglages du bâtiment. | DEC-DUR-01 |
| PT-TAC-01 | État « Non réalisée — À reprogrammer » calculé à la lecture (secours) **et** par tâche planifiée supervisée, car Celery n'est pas garanti (AUD-032). | DEC-BLQ-05 |
| PT-ORG-01 | Ordre des grades : champ de rang configurable sur `GradeChoice`, utilisé pour proposer le coordinateur. | DEC-COL-02 |
| PT-SUP-01 | Suppléance par objet dédié (fonction, périmètre, titulaire, suppléant, début, fin, activée par, motif), avec contrainte d'unicité du responsable actif par périmètre ; étend `RemplacementChefDeListe` au lieu de créer un système parallèle. Voir P02 option C. | DEC-SUP-* |
| PT-CPT-01 | États de rattachement des comptes (complet / à compléter / autorisé) selon P01 ; accueil neutre pour un compte incomplet. | DEC-DRT-06 |
| PT-DEL-01 | Archivage effectif d'abord, puis suppression bloquée si l'objet a un historique (P07). | DEC-DRT-05 |
| PT-SEC-01 | Verrou de démonstration par couches (P06). | AUD-009 |
| PT-APP-01 | Contrôles d'appareillage versionnés par fiche de référence, avec drapeaux `obligatoire` et `critique_non_derogeable` portés par la fiche (configuration, pas code). | DEC-APP-04 à 12 |

### Règles techniques évidentes (issues du dépôt, pas des décisions métier)

| ID | Règle | Source |
|---|---|---|
| RT-01 | Les droits sont vérifiés côté serveur (UI, POST, API), jamais déduits du seul affichage. | N4, N5 |
| RT-02 | Chaque changement sensible est journalisé dans `AuditLog` avec la valeur précédente. | CLAUDE.md principe 8, N1 §30 |
| RT-03 | Tout texte lu par un humain est en français, commentaires et commits compris. | CLAUDE.md principe 1 |
| RT-04 | Aucune règle susceptible d'évoluer n'est codée en dur. | CLAUDE.md principe 6 |
| RT-05 | Tests sur SQLite et PostgreSQL ; migration testée sur base peuplée. | Audit, N5 |
| RT-06 | Identifiants stables (UUID, NNO) conservés. | CLAUDE.md |
| RT-07 | Aucune ressource externe (CDN, API, télémétrie). | CLAUDE.md principe 4, N1 §26 |
