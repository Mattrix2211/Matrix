# Passage B — Synthèse de la recette V1 par l'équipage de testeurs

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant chaque mission (sauf les trois exécutions de M13) |
| Navigateur | Chromium headless 1366×768, serveur MCP `playwright` (outils `mcp__playwright__*` disponibles, vérifiés par une navigation réelle) |
| Date | 2026-10-13 |
| Coordinateur | Session Claude Code ; aucune modification de Matrix, aucune écriture Notion, aucune fusion |

**Avertissement.** Les « marins » sont des agents IA qui simulent des profils : cette campagne n'est ni une validation par de vrais marins ni une homologation SSI. Les notes sont des indications relatives, pas des mesures d'usage. Les constats de périmètre sont des hypothèses à confirmer ; aucune fuite n'a été confirmée par le coordinateur.

## 1. Missions jouées et non jouées

**Jouées : 18 sur 18** (P1 : M01, M02, M03, M05, M06, M08, M10, M12, M13 ; P2 : M04, M07, M09, M11, M14, M15, M16, M17, M18). Rapports : `2026-10-13-B-M<nn>-*.md`, consolidation : `2026-10-13-B-observateur.md`.

**Non jouées / non testées à l'intérieur des missions jouées** (statut : Non testé)
- `terre_securite` et `terre_chef_securite` (M16 : seul `terre_classe` a été joué ; frontière « autre classe refusée » non testée).
- Enregistrement de l'accusé de lecture (M01 : le marin n'a pas cliqué, la mission demandait seulement de dire s'il y a quelque chose à confirmer).
- Proposition, contrôle et publication d'une liste de quarts, et suppression d'un créneau (M10 : boîte `confirm()` du navigateur non gérable par les marins, qui n'ont pas `browser_handle_dialog`).
- Échange de quart (M10 : aucun échange dans le jeu de données de `seed_recette`).
- Validation de la relève côté équipage B (M13 : `cdt_b` n'a trouvé aucun écran de relève).
- Visa COMAEQ (M14 : geste introuvable) et feuille de service (M14 : aucune rubrique configurée).
- Impression réelle du compte rendu (M04), connexion du nouveau compte (M18), refus explicite de candidature hors ressort (M17), accès direct par identifiant hors périmètre (M07, M11), ouverture des pages « Paramètres », « Flotte », « Plan du navire », « Prêt à appareiller » (jamais ouvertes par les marins qui les voient dans le menu), annulation/modification/suppression sur la plupart des missions.
- Aucune mesure de durée par action : toutes les durées de marin sont « **non mesurée** ». Seule la durée totale de chaque agent, relevée par l'outil, est indiquée dans les rapports.

## 2. Tableau missions × statut × score

Statuts : Réussi · Réussi avec réserve · Échoué · Exécuté (non prouvé) · Non testé · Impossible à vérifier. « Réussi » repose sur le compte rendu et, pour M02, M04, M06, M07-notifications, une lecture de la base par le coordinateur. Scores (méthode de `notation-ergonomie.md`, 0 à 4) : moyenne des critères observés, attribués par le coordinateur d'après les comptes rendus ; **critères 2 (temps) et 9 (conservation du contexte) non notés** (« n/o » : temps non mesuré, contexte observable seulement ponctuellement) ; autres critères « n/o » quand non observés. Indicatif seulement.

| Mission | Marin / compte | Statut | Score | Critères notés (1 · 3 · 4 · 5 · 6 · 7 · 8 · 10) | Alerte |
|---|---|---|---|---|---|
| M01 | Lucas / `equipier_a` | Réussi ; accusé Non testé | 2,8 | 4 · 3 · 2 · 2 · 3 · n/o · n/o · 3 | — |
| M02 | Lucas / `equipier_a` | Réussi (notification prouvée en base) | 2,8 | 3 · 4 · 3 · 2 · 4 · 2 · 1 · 3 | — |
| M03 | Julien / `equipier_a3` | Réussi avec réserve | 1,8 | 3 · 2 · 1 · 2 · 1 · 2 · 1 · 2 | Critère 6 ≤ 1 (documentation à 4 clics) |
| M04 | Julien / `equipier_a3` | Réussi (compte rendu, audit prouvé) ; impression Exécuté non prouvé | 1,8 | 2 · 2 · 2 · 2 · 2 · 2 · 1 · 1 | — |
| M05 | Claire / `chef_section_a` | Réussi | 3,5 | 4 · 4 · 4 · 3 · 4 · 2 · 3 · 4 | — |
| M06 | Claire / `chef_section_a` | Réussi (circulation prouvée en base) | 2,6 | 3 · 3 · 3 · 2 · 4 · 2 · 1 · 3 | — |
| M07 | Claire / `chef_section_a` | Réussi (observation passive) ; accès direct Non testé | 2,4 | 3 · 3 · 2 · 2 · n/o · n/o · n/o · 2 | — |
| M08 | Antoine / `chef_service_a` | Réussi avec réserve (conflits non signalés par l'application) | 2,5 | 3 · 2 · 2 · 2 · 3 · n/o · n/o · 3 | — |
| M09 | Antoine / `chef_service_a` | Réussi (remontée) ; état de l'installation partiel | 2,4 | 3 · 3 · 2 · 2 · 2 · 3 · 2 · 2 | — |
| M10 | Chef de liste / `chef_secteur_a` | Échoué en partie ; publication Impossible à vérifier ; échange Non testé | 1,3 | 1 · 2 · 1 · 2 · 1 · 1 · 1 · 1 | Critère 6 ≤ 1 (affecter un créneau existant introuvable) |
| M11 | Équipier élec. / `equipier_elec_a` | Réussi (refus observé) | 3,0 | 3 · 4 · 3 · 3 · n/o · n/o · n/o · 2 | — |
| M12 | Équipage B à terre / `chef_secteur_b` | Réussi (2e réponse Exécuté non prouvé) | 2,3 | 3 · 2 · 2 · 2 · 3 · 2 · 1 · 3 | — |
| M13 | `cdt_a` · `cdt_b` · `second_a` | Consigne : Réussi (`cdt_a`, `second_a`) ; relève : Échoué / Non testé | 1,9 | 1 · 2 · 2 · 2 · 1 · 2 · 3 · 2 | Critère 1 = 0 pour `cdt_b` sur une mission P1 ; critère 6 ≤ 1 (relève introuvable) |
| M14 | COMAEQ / `coma_comaeq` | Échoué (visa introuvable) ; feuille de service Non testée (donnée absente) | 1,0 | 0 · 2 · 1 · 1 · 1 · n/o · n/o · 1 | Critère 1 = 0 ; critère 6 ≤ 1 |
| M15 | COMANAV / `coma_comanav` | Réussi avec réserve (chiffres divergents) | 2,7 | 3 · 3 · 2 · 2 · 3 · n/o · n/o · 3 | — |
| M16 | Soutien à terre / `terre_classe` | Réussi (réponse) ; frontière « aucune modification à bord » : **P0 potentiel à confirmer** | 2,1 | 3 · 3 · 2 · 2 · 2 · 2 · 1 · 2 | Fuite de droit signalée (P0 potentiel) |
| M17 | Référente formation / `referent_formation_a` | Réussi avec réserve (effet de « Sélectionner » Exécuté non prouvé) | 2,0 | 3 · 3 · 2 · 2 · 3 · 1 · 0 · 2 | — |
| M18 | Admin navire / `admin_navire` | Réussi ; connexion du nouveau compte Non testée | 2,6 | 3 · 2 · 2 · 2 · 2 · 4 · 3 · 3 | — |

Moyenne indicative des 18 missions : environ 2,3 sur 4 (acceptable avec friction). Aucune mission n'est « naturelle » (4).

## 3. Anomalies proposées (à arbitrer par le Product Owner, aucune écrite au backlog)

Priorités **proposées**, statut **hypothèse à confirmer** sauf mention. Détail et preuves : `2026-10-13-B-observateur.md`.

**P0 potentiels (fuite de périmètre signalée par des marins, non confirmée — à confirmer par `qa-securite`)**
- P-1 : `terre_classe` voit les formulaires de modification d'une tâche et d'une demande du bord (M16). Aucun clic ; écriture réelle non établie.
- P-2 / P-3 : listes « interlocuteur », « Marin », « Responsable du dossier », « Marin à affecter » couvrant tout le bâtiment, équipage B inclus (M03, M05, M06, M09, M14, M17), avec présélection sur l'administrateur (M09). À l'inverse, les listes d'attribution de tâche sont bien limitées à la section (M05, M07).
- P-4 : l'accueil de `cdt_b` a affiché « Cdt A » après déconnexion de `cdt_a` (M13). Le compte `cdt_b` s'appelle bien « Benoît Cdt B » en base ; les droits affichés étaient ceux de B. Interprétation brouillée par l'anomalie de procédure (section 4).

**P1 proposés (parcours V1 essentiel potentiellement bloqué, à confirmer)**
- Visa COMAEQ introuvable : le bouton « Valider » de l'accueil ouvre un écran « Enregistrer la correction » (M14).
- Relève entre équipages : cachée dans Paramètres › Utilisateurs pour `cdt_a`, introuvable pour `cdt_b` et `second_a` ; « Générer la synthèse de passation » sans retour (M13).
- Liste de quarts : impossible d'affecter un créneau existant, aucun avertissement d'absence ou de qualification ; publication et échange non testables (M10). À rapprocher de l'absence d'alerte de conflit absences/quarts/gardes (M08) — **à confronter à la liste « À faire plus tard »** avant de retenir comme défaut V1.

**P2 proposés**
- Message « Mot de passe incorrect » trompeur et conformité remise à « — » à la clôture de maintenance (M03, M04 : deux marins) ; bandeau « Assignée » et bouton actif après clôture.
- « None » affiché dans les listes de quarts (M08, M13).
- Heures du calendrier différentes de celles de l'accueil/liste (M01, M08) ; chiffres de retard divergents entre accueil et Vue COMANAV (M15) ; « Bloquées 0 » contredit par le tableau (M12) ; « Non affectés 0 Conforme » qui ignore les absences (M08).
- Circuits de remontée ambigus : « Signaler une difficulté » / « Je suis bloqué » / « Signaler une anomalie » / « Discussion » ; étiquette « Demande bord–terre » pour un sujet interne (M02, M03, M06, M09).
- Absence de confirmation explicite après action et « qui est prévenu » invisible (notification pourtant prouvée en base en M02 et M06).
- Entrées de menu d'administration visibles pour presque tous les rôles (accès réel non testé) ; boutons d'écriture visibles à portée non établie (M03, M08, M15, M17).
- Documentation à 4 clics de l'écran d'exécution (M03) ; fiche d'installation sans état d'avancement (M09, M15) ; perte des champs après rejet du formulaire de création d'utilisateur (M18).

**P3 / arbitrages métier**
- Vocabulaire non Marine et jargon développeur affiché (« CLAUDE.md §6 » sur Feuille de service › Réglages, M13), noms affichés incohérents (données de recette), calendrier dense, accueil chargé.
- Droits étendus de COMAEQ (corriger des comptes rendus terminés), de l'administrateur de navire (créer des rôles de commandement, « Administrateur général » dans les listes de seuils), du second (publication à tous les équipages), diffusion large des notifications de blocage : choix métier à arbitrer.
- Pas de relance des non-lecteurs, pas d'impression du compte rendu saisi, pas de champ de relevé de mesure, pas d'annulation d'un message ou d'un blocage : probablement à rapprocher de « À faire plus tard ».

## 4. Distinction des natures (extrait)

| Nature | Exemples |
|---|---|
| Défaut technique probable | message « Mot de passe incorrect » ; « None » ; heures incohérentes ; chiffres divergents ; visa COMAEQ ; bandeau « Assignée » après clôture |
| Problème ergonomique | circuits de remontée ambigus ; absence de confirmation ; menu trop large ; documentation à 4 clics ; calendrier dense |
| Incohérence métier à arbitrer | droits COMAEQ, administrateur, second ; « Mes listes de quarts » vide pour le chef de service ; relève vue de A seulement |
| Fonctionnalité différée | alerte de conflit, impression du compte rendu saisi, relance des non-lecteurs, champs de relevé, annulation d'un message (à confronter à « À faire plus tard ») |

## 5. Limites de l'exécution

1. **Simulation par des agents IA** (profils copiés des fichiers du dossier, sans accès à la page Notion « Équipage de testeurs ») : pas de vrais marins, pas d'homologation SSI. Les marins ouvrent parfois des écrans par adresse tapée, comportement d'agent non imputé à l'application.
2. **Anomalie de procédure du coordinateur** : `browser_close` n'a pas été exécuté entre `cdt_a` et `cdt_b` (M13). `cdt_b` a trouvé le navigateur connecté en `cdt_a`, s'est déconnecté puis reconnecté (journal serveur : `POST /logout/` puis `POST /accounts/login/`). L'isolation de session n'a pas été respectée pour le début de cette exécution. Les trois exécutions de M13 se sont succédé sans remise à zéro de la base.
3. **Outillage** : les agents `marin-*` n'ont pas `browser_handle_dialog` ; toute action protégée par une boîte `confirm()` du navigateur est donc inexécutable pour eux (cf. M10) — limite de la campagne, pas un défaut avéré de Matrix. Une session navigateur a dû être nettoyée après blocage (onglets en attente d'une boîte de dialogue) ; sans conséquence sur les résultats.
4. **Jeu de données** : aucun échange de quart, aucune rubrique de feuille de service pour Bretagne ; scénarios correspondants non jouables.
5. **Erreurs de console** relevées à chaque `browser_close` (`ERR_CONNECTION_REFUSED` sur `/notifications/compteur/`) : artefact du redémarrage du serveur entre deux missions, non un défaut.
6. **Captures** : 5,1 Mo environ rangées dans `rapports/captures/` (certaines non relues par les marins). Les mots de passe provisoires fictifs d'un compte jetable sont masqués dans le rapport M18.
7. **Mesures** : durées et nombres d'actions rapportés par les marins (estimations) ; aucune mesure chronométrée au niveau de l'action.

## 6. Contrôle d'intégrité

`git status --short` : aucun fichier de code modifié. `git diff --stat 5ea072d HEAD` hors `docs/recette-v1/rapports/` : vide. Seuls des fichiers de `docs/recette-v1/rapports/` ont été ajoutés ; `.env` et `db.sqlite3` sont ignorés par git. Aucune modification de Matrix, aucune écriture Notion, aucune fusion, aucune PR. Poussé sur `claude/recette-v1-passage-b` uniquement.
