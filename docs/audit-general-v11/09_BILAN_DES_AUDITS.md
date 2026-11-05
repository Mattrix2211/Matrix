# Bilan des 20 audits : clôturé, clôturé avec réserves, bloqué

Date : 2026-11-05 (4ᵉ passe). Commit audité `1c37f22` ; comparaison avec `main` : `10_COMPARAISON_MAIN_V11.md`.

**Définitions (demandées par le PO)** — **Clôturé** : tous les contrôles nécessaires et réalisables sont terminés. **Clôturé avec réserves** : l'analyse technique est terminée, mais des validations externes ou matérielles restent nécessaires, **ou** des éléments précis restent non vérifiés (listés ; ils ne sont **pas** réputés conformes). **Bloqué** : une vérification indispensable ne peut réellement pas être faite.

**Résultat : 0 audit clôturé sans réserve, 20 clôturés avec réserves, 0 bloqué.** Aucun audit n'est classé « partiel » : une validation externe ou une décision du PO en attente n'est pas un motif de statut partiel. En revanche, « avec réserves » n'est pas « conforme » : la colonne « Non vérifié » reste à lire.

| N° | Audit | Statut | Justification (analyse achevée sur…) | Non vérifié (réalisable ou externe) |
|---|---|---|---|---|
| 01 | Besoin et historique | CAR | Notion (hub, 13 pages), 16 titres de PR, backlog (décompte, tâches ouvertes, ≈ 60 titres terminés recoupés avec le code) | 343 tâches terminées une à une (réalisable) ; conversations ChatGPT, FANLAB, rapport indépendant (indisponibles) |
| 02 | Configurabilité | CAR | seuils (effet réel, limité au bâtiment), écran et API de structure, simulation d'un nouveau bâtiment, 55 droits en dur revus | effet d'un seuil sur deux processus ; décisions A et B |
| 03 | Première mise en service | CAR | installation, migration, pipeline de démonstration, nouveau bâtiment en 11 étapes, montée de version sur base peuplée (SQLite, PostgreSQL) | Windows (`.bat`), proxy TLS réel, import de personnel (à planifier) |
| 04 | Usage quotidien | CAR | 11 parcours de bout en bout en navigateur (tâche, échange, annonce, anomalie, maintenance, discussion, formation, calendrier…) ; 8 468 requêtes sans erreur 500 | efficacité mesurée par des marins |
| 05 | UX et accessibilité | CAR | maquettes A et B, charte, mobile, clavier, mode sombre, impression | tablette, lecteur d'écran, papier réel |
| 06 | Rôles et permissions | CAR | 1 407 + 196 essais de droits des quarts, circuit, délégations bornées, droits d'autres modules, comparaison avec `main` | fiches flotte, programme, postes, RETEX action par action |
| 07 | Calendrier | CAR | 7 sources, étanchéité, vues et événement personnel en navigateur | conflits (fonction absente), fuseaux des relèves |
| 08 | Maintenance et installations | CAR | exécution web et API, confirmation critique, non-conformité (AUD-023) | circuits de fiches, périodicité, dérive, catalogue, tournées (couverts par les tests, non rejoués) |
| 09 | Quarts et services | CAR | droits, circuit, cas limites des listes publiées, échange, délégations | assistant de création jusqu'à la publication, changements de mode, régimes réels |
| 10 | Logistique | CAR | invariants du stock, droits, mutation tuée | interface, alertes planifiées, prêts/retours (différés) |
| 11 | Communication | CAR | accès, discussion, notifications, annonces avec accusé | mentions, pièces jointes, Web Push |
| 12 | Formations et autres modules | CAR | inventaire, formation, documentation (circuit), RETEX et absences (formulaires) | RETEX et absences de bout en bout, postes |
| 13 | Architecture | CAR | taille, complexité, imports, couplage, mutations | duplication, N+1, volumétrie |
| 14 | Données et intégrité | CAR | PostgreSQL complet, cascades, montée de version peuplée, suppression d'unités et de comptes | sauvegarde/restauration, concurrence en charge |
| 15 | Sécurité et résilience | CAR | secrets, proxy, comptes de démonstration, connexions répétées, seuils, accès anonymes | injections/XSS, en-têtes, fichiers, politique SSI |
| 16 | Qualité des tests | CAR | métriques sur 3 815 tests, 13 mutations de droits (18 exécutions), comparaison avec `main` | couverture de lignes, qualité de chaque assertion |
| 17 | Déploiement et exploitation | CAR | procédure, PostgreSQL, proxy simulé, sondes reproductibles | vrai proxy, serveur d'application, supervision, sauvegarde |
| 18 | Cohérence globale | CAR | croisement des 19 autres | dépend de leurs réserves |
| 19 | Conformité Marine nationale | CAR | pages Notion croisées avec le code | sources publiques, expert du bord |
| 20 | Données de démonstration | CAR | pipeline mesuré | fidélité aux usages, Windows |

(CAR = clôturé avec réserves.)

## Pourquoi aucun audit n'est « bloqué »

Aucune vérification indispensable n'est impossible : les réserves externes (SIC, expert du bord, matériel Windows, tablette, lecteur d'écran, volumes réels) limitent la **portée des preuves**, pas la possibilité de conclure sur ce qui a été exécuté.

## Travaux réalisables qui n'ont pas été faits (pour mémoire, aucun n'est indispensable à la lecture des anomalies)

Relecture des 343 tâches terminées et des descriptions de PR ; circuits des fiches flotte, RETEX et absences de bout en bout ; assistant de création de liste jusqu'à la publication ; duplication de code et mesure de couverture de lignes ; scénarios de concurrence en charge.
