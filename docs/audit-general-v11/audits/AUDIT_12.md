# Audit 12 — Formations, documentation et autres modules

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Inventaire des modules présents dans le dépôt (aucun n'est ignoré au motif qu'il est absent du menu), contrôles d'accès exécutés, circuits métier non rejoués de bout en bout.

## Inventaire

| Module | Présent | Accès vérifié | Circuit rejoué |
|---|---|---|---|
| Formations (catalogue, sessions, référents, candidatures, arbre) | oui (310 tests) | validation d'une qualification : **référent de la formation** et **commandant et plus** (conforme à la règle documentée) ; refusé aux chefs de section/service, COMA, second, suivi à terre, autre bâtiment ; **l'administrateur d'unité valide aussi** (effet du niveau : P02) | non |
| Documentation et procédures | oui (9 tests) | bibliothèque ouverte à tous les connectés ; création réservée à partir de chef de section (404 pour équipier et suivi à terre) | non (proposer → valider → publier) |
| RETEX | oui (5 tests) | proposition ouverte à un équipier (200), domaines et gestion réservés aux chefs ; **404 pour l'administrateur général sans bâtiment** | non |
| Postes du bord | oui (7 tests) | liste ouverte ; création réservée (404 équipier) | non |
| Absences | oui (21 tests) | page personnelle pour tous | non |
| Programme du bâtiment | oui (10 tests) | page ouverte ; alimente le calendrier (vérifié) | non |
| Demandes (difficultés signalées) | oui (41 tests) | page ouverte | non |
| Rondes | **retirées** le 02/11 ; `rondes/models.py` et migrations demeurent sans test ni route | — | — |
| Tâches | oui (94 tests) | page ouverte ; 37 tâches en démonstration complète | non |

## Constats

- Ces modules sont **faiblement testés** par rapport à leur importance métier : documentation 9 tests, RETEX 5, postes 7, programme 10, contre 609 pour les quarts.
- AUD-007 (résidu Rondes) toujours valable.
- Le RETEX est un point d'entrée pour tout marin, mais l'administrateur général n'y accède pas (404) : sans conséquence métier (il n'a pas de bâtiment), à noter.

## Non vérifié

Tous les circuits de validation (documents, RETEX, fiches), la liste d'attente des sessions, les prérequis anti-cycle, les relances de tâches, le tableau d'effectifs des postes, l'impact des absences sur les échanges et la génération des listes.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Circuit documentaire rejoué : brouillon, soumission, **l'auteur ne peut pas valider**, le COMA valide, version applicable publiée ; candidature à une formation (état « en attente d'approbation ») ; validation de qualification ; formulaires RETEX et absence ouverts.

### Non vérifié ou dépendant d'une validation externe

RETEX de bout en bout, absences et leur effet sur les échanges, postes et tableau d'effectifs.
