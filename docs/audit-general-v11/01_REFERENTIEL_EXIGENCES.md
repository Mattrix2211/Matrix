# Référentiel des exigences — version 0 (provisoire)

> **Mise à jour de la 4ᵉ passe** : la colonne « État » de ce tableau est celle de la 1ʳᵉ passe. L'état à jour de chaque exigence, avec sa preuve, est dans `03_MATRICE_CONFORMITE.md`.

Construit à partir des seules sources lues pendant la session du 2026-11-05 (voir `08_LIMITES_ET_PREUVES.md`). **Ce n'est pas encore exhaustif** : les pages Notion 01 à 05 et 07 à 12, les 380 tâches du backlog et les PR #1 à #16 n'ont pas été dépouillées.

Légende. Statut historique : OBL obligatoire / SOUH souhaité / DIFF différé / ABAN abandonné / CONF à confirmer. État actuel : **NV = non vérifié** (aucune preuve produite par l'audit à ce stade), IMPL, PARTIEL, ABS. Aucun état « implémenté » n'est posé sans preuve : l'existence d'un code n'est pas une preuve de fonctionnement.

Sources abrégées : CDC = Notion « Cahier des charges » (page `3d46e7f2…`, vue au 2026-10-10) ; ORG = « Organigramme et rôles » (`3e46e7f2…`, 2026-10-31) ; DEC = sous-page 13 « Décisions… » ; P06 = sous-page 06 « Service courant… » ; FDR = « Feuille de route » ; CLM = `CLAUDE.md` ; UX = `docs/UX.md`.

## A. Principes

| ID | Exigence | Source | Date | Hist. | État | Preuves à ce stade | Régression | Décision PO |
|---|---|---|---|---|---|---|---|---|
| EX-001 | Matrix est la plateforme quotidienne du marin ; la GMAO n'en est qu'un module | CDC §1 | 2026-09-06 | OBL | NV | — | — | — |
| EX-002 | Aucune règle susceptible d'évoluer n'est codée en dur (durée d'un quart, droits d'un chef, nombre de services) | CDC §4, §33 ; CLM principe 6 | 2026-09-06 | OBL | PARTIEL | Seuils de rôle par bâtiment en base (`matrix/core/role_thresholds.py`, `VersionConfiguration`, `org/models.py:132`). Reste à auditer le reste (audit 02) | Élevé | — |
| EX-003 | Internet n'existe pas : aucun CDN, police distante, télémétrie | CDC §25, §26 ; CLM principe 4 | 2026-09-06 | OBL | PARTIEL | Test `matrix/tests/test_icones.py:49` interdit les liens http(s) ; commentaires « auto-hébergé » dans `base.html`, `login.html`. Balayage complet des gabarits et dépendances non fait | Moyen | — |
| EX-004 | Tout est traçable (`AuditLog`), jamais d'écrasement silencieux | CDC §30 ; CLM principe 8 | 2026-09-06 | OBL | NV | `AuditLog` existe (`accounts/models.py:177`) ; couverture par module non mesurée | Élevé | — |
| EX-005 | Proposer → valider → publier ; version publiée active jusqu'à validation ; versions conservées | CDC §31, §34 | 2026-09-06 | OBL | NV | Modèles `VersionQuart`, `VersionServiceGarde`, `VersionFeuilleService` existent ; comportement non vérifié | Élevé | — |
| EX-006 | Administration distribuée : permission, périmètre, responsabilité, configuration | CDC §5, §35 | 2026-09-06 | OBL | NV | — | Élevé | — |
| EX-007 | Les droits ne se déduisent pas du seul grade ; vérification côté serveur | DEC (directive du 2026-10-31) | 2026-10-31 | OBL | NV | Nombreux commits « Sécurité » d'octobre ; à rejouer (audit 06) | Élevé | — |
| EX-008 | Principe de non-surcharge : le marin voit ce qui lui est utile maintenant | CDC §39 | 2026-09-06 | OBL | NV | — | Moyen | — |
| EX-009 | Tolérance aux coupures bord–terre ; synchronisation avec gestion de conflits | CDC §27, §28 | 2026-09-06 | DIFF (Phase 7, « volontairement différée ») | ABS | Aucune synchronisation recherchée dans le code à ce stade ; à confirmer par audit 13 | — | Arbitrage de calendrier |

## B. Quotidien et calendrier

| ID | Exigence | Source | Date | Hist. | État | Preuves | Régression | Décision |
|---|---|---|---|---|---|---|---|---|
| EX-010 | Le marin voit sa journée à l'ouverture : agenda, actions, notifications | CDC §6, §40 ; UX §9 | 2026-09 | OBL | NV | Tests de l'accueil dans `dashboard/tests` ; parcours navigateur du dossier de recette (non rejouable, voir AUD-003) | Moyen | — |
| EX-011 | Un calendrier unique alimenté par planning, quart, service, tâche, formation, maintenance, réunion | CDC §15 | 2026-09-06 | OBL | NV | `calendar_app/` | Moyen | — |
| EX-012 | Le calendrier est la colonne vertébrale du quotidien et du pilotage des chefs ; chaîne organiser → affecter → consulter → exécuter → suivre | FDR (cap du 2026-10-09) | 2026-10-09 | OBL | NV | — | Moyen | — |
| EX-013 | Recherche universelle (marin, équipement, tâche, document…) | CDC §37 | 2026-09-06 | SOUH | NV | Tests `test_global_search.py`, `test_recherche_rapide.py` | Faible | — |
| EX-014 | Notifications explicites (titre, objet, échéance) | CDC §38 | 2026-09-06 | OBL | NV | `notifications/` ; catalogue de 68 sites de création (`docs/propositions/notifications_par_regime.md`) | Moyen | — |

## C. Quarts, services, feuille de service

| ID | Exigence | Source | Date | Hist. | État | Preuves | Régression | Décision |
|---|---|---|---|---|---|---|---|---|
| EX-020 | Chef de liste : créer, publier, remplacer, gérer les indisponibilités | CDC §8, §10 | 2026-09-06 | OBL | NV | `quarts/models.py:174` `ChefDeListe` | Élevé | — |
| EX-021 | **Génération automatique des tours : ABANDONNÉE** ; planification manuelle avec contrôle des contraintes | CDC bandeau du 2026-10-09 ; FDR | 2026-10-09 | **ABAN** | Conforme à l'abandon sur la recherche ciblée (aucun générateur trouvé par grep sur `quarts/`) ; à confirmer par audit 09. **Attention** : le commit `ad032ed` du 2026-09-23 « génération intelligente des listes » a existé : vérifier qu'il n'en reste rien d'actif | Moyen | — |
| EX-022 | Aucun rythme de quart codé en dur ; régimes bordées / tiers / quart / cinquième / sixième | CDC §8 ; P06 (2026-10-31) | 2026-10-31 | OBL | NV | — | Élevé | — |
| EX-023 | Distinguer « hommes morts » (aucun quart) et « de musique » (nuit complète sans quart) | P06 rectification 2026-10-31 | 2026-10-31 | OBL (cadrage) | NV | — | Moyen | Confirmer le vocabulaire en interface |
| EX-024 | Fraction de service à quai : contrôler que tous les postes requis ont un titulaire ; composition-type configurable (exemple BRF : 9 postes) ; **pas** de contrôle de qualification pour l'instant | P06 2026-10-31 | 2026-10-31 | OBL (complétude) / DIFF (qualifications) | NV | — | Élevé | — |
| EX-025 | Feuille de service et tableaux de quart = deux supports distincts ; la feuille n'agrège pas tous les quarts à la mer | P06 rectification | 2026-10-31 | OBL | NV | — | Moyen | — |
| EX-026 | Rédaction de la feuille de service réservée à une fonction BSC ou délégation habilitée, jamais au simple rattachement au bâtiment | P06 « point de sécurité » | 2026-10-31 | OBL | **IMPL sur 1c37f22 (par lecture du code)** ; **non conforme sur `main` 6ef16ad** | `quarts/models.py:2065` (sur 1c37f22) filtre sur `RedacteurFeuilleService` ; sur `main` `peut_rediger_feuille_service` accepte tout marin du navire. Tests à rejouer : voir AUD-001 | Élevé | — |
| EX-027 | Chaque équipage a sa propre feuille de service ; validation par le COMAEQ compétent, ou le commandant du même équipage si le poste est vacant | DEC 2026-10-19 | 2026-10-19 | OBL | NV | — | Élevé | — |
| EX-028 | Échange de service : A demande, B accepte, le chef valide ; l'historique conserve l'échange ; l'impossibilité est expliquée | CDC §12 à §14 | 2026-09-06 | OBL | NV | `quarts/models.py:751` `EchangeService` | Élevé | — |
| EX-029 | Service à quai, garde et quart sont des notions distinctes | DEC 2026-10 | 2026-10 | OBL | NV | — | Moyen | — |

## D. Organisation, rôles, permissions

| ID | Exigence | Source | Date | Hist. | État | Preuves | Régression | Décision |
|---|---|---|---|---|---|---|---|---|
| EX-030 | Hiérarchie configurable par navire (commandant → second → COMA → services → secteurs → sections) ; sections facultatives selon le PO | ORG ; DEC ; brief du PO | 2026-10 | OBL | NV | `org/models.py` (13 modèles) | Élevé | Le caractère facultatif des sections est dans le brief du PO ; sa source écrite n'est pas encore retrouvée (CONF) |
| EX-031 | Chaque service rattaché explicitement à son COMA compétent ; le visa COMA résout ce rattachement | DEC | 2026-10 | OBL | NV | — | Élevé | — |
| EX-032 | Visa COMA : sans titulaire, le visa reste en attente avec message ; l'administrateur désigne sans viser à la place ; exception propre à la feuille de service | DEC 2026-10-18 | 2026-10-18 | OBL | NV | — | Élevé | — |
| EX-033 | Double équipage A/B avec relève validée, lecture seule à terre ; pas de modèle `org.Equipage`, pas d'organisation miroir ni de passation automatique (retirés, à re-décider) | CDC bandeau ; FDR ; DEC | 2026-10-10 | OBL (A/B) / DIFF (miroir, passation auto) | NV | — | Élevé | Passation : DEC la dit « maintenue en V1 » (2026-10), FDR la dit différée (2026-10-10) : **contradiction à arbitrer**, voir `06_DECISIONS_PO.md` |
| EX-034 | Commandement à terre : lecture, pas d'écriture métier par défaut ; soutien à terre sans rattachement ni habilitation = aucun droit automatique | DEC 2026-10, 2026-10-21 | 2026-10-21 | OBL | NV | Commits de sécurité des 13 et 14 octobre | Élevé | — |
| EX-035 | Commandant en second : vision globale, écritures limitées aux responsabilités attribuées | DEC | 2026-10 | OBL | NV | `matrix/tests/test_commandant_en_second_vision.py` | Élevé | — |
| EX-036 | Fonctions annexes « adjudant de compagnie » et « OSS » reconnues comme fonctions, **sans** GO d'implémentation | ORG 2026-10-31 | 2026-10-31 | CONF / DIFF | ABS (conforme à l'absence de GO, à vérifier) | — | — | GO PO à obtenir si souhaité |
| EX-037 | Ne pas afficher « chef de groupement » ni « CAN » dans l'interface | ORG ; DEC | 2026-10 | OBL | NV | À balayer (audit 19) | Faible | — |
| EX-038 | Organismes à terre comme unités (bâtiment ou bureau) | ORG 2026-10-21 | 2026-10-21 | DIFF (« pas de nouveau développement majeur pendant la consolidation ») | NV | — | — | — |

## E. Maintenance, matériel, logistique, communication, connaissance

| ID | Exigence | Source | Date | Hist. | État | Preuves | Régression | Décision |
|---|---|---|---|---|---|---|---|---|
| EX-040 | Fiche matériel flotte : un bord ne la publie pas seul ; circuit en 7 étapes jusqu'à ALFAN/Exploitation | ORG ; DEC | 2026-10 | OBL | NV | — | Élevé | — |
| EX-041 | Fiche d'installation : adaptable au bord, circuit section/secteur → service → COMA | ORG | 2026-10 | OBL | NV | — | Moyen | — |
| EX-042 | Compte rendu d'intervention : notifié au chef de secteur, sans visa, modifications tracées | ORG | 2026-10 | OBL | NV | — | Moyen | — |
| EX-043 | Matrix complète les outils du SSF (SIGLe/ODIN), sans les remplacer ; identifiants stables (UUID, NNO) | ORG ; FDR ; CLM | 2026-10 | OBL | NV | — | Faible | — |
| EX-044 | Discussions attachées aux objets (tâche, équipement, anomalie…) via `threads` | CDC §16, §17 | 2026-09-06 | OBL | NV | `threads/` | Moyen | — |
| EX-045 | Annonces par niveau (information, important, critique) respectant les périmètres | CDC §19 | 2026-09-06 | OBL | NV | `annonces/` | Moyen | — |
| EX-046 | Logistique : stocks, prêts, retours, inventaires | CDC §21 | 2026-09-06 | OBL | NV | `logistics/` | Moyen | — |
| EX-047 | Documentation, formations, qualifications, RETEX | CDC §22 | 2026-09-06 | OBL | NV | `documentation/` (9 tests), `retex/` (5 tests), `training/` | Moyen | — |
| EX-048 | QR codes hors V1 ; génération automatique écartée | DEC ; CDC bandeau | 2026-10 | ABAN (V1) | NV | Du code `assets/scan_views.py` existe : à qualifier (écart avec « hors V1 » ?) | Faible | À confirmer |
| EX-049 | PÉPIN / CRAT / RAV/c : remplacement futur des messages par mail ; circuits **non validés** ; pas d'implémentation officielle | ORG ; DEC 2026-10-21 | 2026-10-21 | DIFF | ABS (conforme) | — | — | Cartographie métier à faire |

## F. UX et exploitation

| ID | Exigence | Source | Date | Hist. | État | Preuves | Régression | Décision |
|---|---|---|---|---|---|---|---|---|
| EX-050 | PC fixe partagé 1366×768 = support principal ; mobile dégradé proprement | UX §2 ; REFERENCE §1 | 2026-10 | OBL | NV | `docs/RECETTE.md` (déclaratif) | Moyen | — |
| EX-051 | Interface contemporaine, sobre, moins de texte explicatif permanent, aide contextuelle réversible | DEC 2026-10-29 | 2026-10-29 | OBL | NV | — | Moyen | Stockage des préférences : non validé |
| EX-052 | Tout ce qui est lu par un humain est en français | CLM principe 1 | 2026-09 | OBL | NV | Hook `verifier-francais-avant-commit.sh` | Faible | — |
| EX-053 | Fonctionnement possible sur PostgreSQL de production et SQLite de développement | CLM ; commit `compat-postgresql` | 2026-10 | OBL | NV | Résultat PostgreSQL du dossier de recette non rejouable ici (voir limites) | Moyen | — |

## G. Décisions postérieures au cahier

| ID | Exigence | Source | Date | Hist. | État | Preuves | Régression | Décision |
|---|---|---|---|---|---|---|---|---|
| EX-054 | Module Rondes (parcours, points de contrôle, photos) | CDC §20, §42 (Phase 4) ; tâche Notion « Rondes : ajouter une photo par point de contrôle » | 2026-09-06 | **ABAN par décision PO explicite du 2026-11-02** (Notion, « Ordre de travail… V1.1 », section « P1 — retrait module Rondes ») | Retiré conformément à la décision : plus de route ni de menu ni de tâche planifiée (test `matrix/tests/test_module_rondes_retire.py`) ; modèles et migrations conservés (`rondes/models.py`) ; **code et tests de l'app supprimés** (commit `96762da`) | Vérification de l'absence de route : à rejouer | Faible | Le Cahier des charges (§20, §42) cite toujours les rondes : à aligner, sinon un lecteur futur croira à un oubli. Décision de suppression physique des données : non prise |

## Écarts de gouvernance déjà identifiés entre sources

1. **Baseline obsolète** : le Cahier des charges (Notion) fixe la baseline au 10/10/2026 sur `dfd6a3c` ; `main` est à `6ef16ad` (28/10) et la V1.1 à `1c37f22` (05/11).
2. **Compte du backlog Notion** : la Feuille de route (10/10) annonce 28 À faire / 3 En vérification / 10 À faire plus tard / 268 Terminé ; la base interrogée le 05/11 donne 14 / 1 / 21 / 343 (+1 En cours, total 380). Évolution normale, mais le chiffre figé dans la page est périmé.
3. **Passation automatique** : maintenue en V1 (DEC, compléments d'octobre) contre différée (FDR 10/10) : voir `06_DECISIONS_PO.md`, DP-02.
4. **`CLAUDE.md`** cite `RoleLevel` et `RolePermission` comme points d'extension. `RoleLevel` est une énumération (`matrix/core/roles.py`), et `RolePermission` n'apparaît que dans un commentaire (`training/serializers.py:15`) : aucun modèle de ce nom (AUD-005).
5. **`docs/REFERENCE.md` §4** parle de « 14 apps » ; le dépôt compte 22 paquets Python à code applicatif (dont le projet `matrix` et `reports`, sans modèle).
6. **Cahier des charges non aligné sur les décisions de novembre** : le retrait des Rondes (02/11) n'y figure pas ; le vocabulaire « COMA » générique est banni depuis la recette du 02/11 alors que le cahier et `DEC` l'emploient encore.
