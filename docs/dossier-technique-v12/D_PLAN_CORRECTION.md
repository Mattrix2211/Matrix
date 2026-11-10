# D. Plan de correction priorisé

> **Mise à jour du 10/11** : l'ordonnancement détaillé est désormais dans `M_PLAN_DEVELOPPEMENT.md` (28 lots) et les priorités dans `K_PRIORITES_JUSTIFIEES.md` (3 P0, 7 P1, 18 P2, 19 P3). Les priorités du tableau récapitulatif ci-dessous sont **obsolètes** ; les étapes restent valables comme vue d'ensemble.

Plan d'**implémentation par étapes cohérentes**, pour une phase de développement ultérieure. **Aucune étape n'est lancée** : chacune demande votre accord explicite. Priorités : P0 sécurité et intégrité des données ; P1 dysfonctionnements métier et autorisations ; P2 ergonomie et amélioration des processus ; P3 évolutions non essentielles et documentation. Pour chaque lot : décisions couvertes, anomalies, dépendances, tests (voir `E2_CATALOGUE_TESTS.md`), questions préalables (voir `F_QUESTIONS_RESIDUELLES.md`).

Conventions du dépôt à respecter à chaque lot (CLAUDE.md) : petite tâche = `@dev` seul ; grosse tâche (migration, droits, nouveau modèle, plus de 50 lignes) = `@dev` puis `@relecteur` ; commentaires courts en français ; suite complète une seule fois en fin de chantier ; jamais `git add .`.

## Étape 0 — Préparation (aucun code applicatif)

| Action | Détail |
|---|---|
| 0.1 | Décider de la base : fusion de la V1.1 dans `main` (DP-01), ou branche de développement dérivée de `1c37f22`. **Recommandation** : brancher depuis `1c37f22` ; décider la fusion séparément. |
| 0.2 | Valider le dossier (registre A, plan D, questions F). |
| 0.3 | Lancer les sondes `rejouer_tout.sh` et la suite SQLite/PostgreSQL sur `1c37f22` pour fixer la référence de non-régression (T-REG-01 à 03). |

## Étape 1 — Sécurité et intégrité des données (priorités individuelles : voir K)

| Lot | Contenu | Anomalies | Décisions | Taille | Dépend de |
|---|---|---|---|---|---|
| 1.1 | Verrou des commandes `seed_demo*` : refus par défaut, variable explicite, marqueur de base, test (P06) ; noms de bâtiments fictifs | AUD-009, AUD-024 | DEC-PRE-06 | Grosse | — |
| 1.2 | Durcissement de configuration : `DB_PASSWORD` obligatoire avec `DB_HOST`, clé secrète d'exemple refusée | AUD-010, AUD-017 | RT-04 | Petite | — |
| 1.3 | Plus de suppression physique avec historique : archivage effectif, message clair à la place de l'erreur 500, comptes désactivés au lieu d'être supprimés, tâches réattribuées ou « non affectées » (P07) | AUD-020, 021, 028, 034 | DEC-DRT-05, DEC-MUT-06, DEC-MUT-07 | **Grosse** (migration probable) | F-05 (partie suppression sans historique) |
| 1.4 | Procédure de sauvegarde et de restauration écrite et testée | AUD-031 | DEC-PRE-06 | Documentaire + exploitant | Experts SIC |

Les lots 1.1 à 1.3 sont indépendants et parallélisables. Critère de sortie : T-SEC-01 à 06, T-ORG-01 à 03, T-CPT-01 à 03, T-REG-04.

## Étape 2 — P1 : autorisations et responsabilités

| Lot | Contenu | Anomalies | Décisions | Dépend de |
|---|---|---|---|---|
| 2.1 | Garde-fou immédiat : exclure l'administrateur technique des visas, publications et validations métier (option A) | AUD-014, 015 | DEC-DRT-02 | F-01 (peut partir sans réponse) |
| 2.2 | Suppléance générale : explicite, temporaire, bornée, unicité du responsable actif, récapitulatif au retour (extension de `RemplacementChefDeListe`) | — | DEC-SUP-01 à 06 | F-01, F-06, IM-05 |
| 2.3 | Droits par fonction pour les visas intermédiaires et la publication ; fermeture des voies directes de modification des listes | AUD-014, 015, 022, 033 | DEC-DRT-01, DEC-FDS-02 | 2.1, 2.2, F-02 |
| 2.4 | Structure du bord par une fonction habilitée (renommer, archiver, réactiver) | AUD-019, 037 | DEC-ORG-02, DEC-DRT-05 | 1.3, F-10 |
| 2.5 | Rattachement incomplet : pas d'accès opérationnel sans autorisation explicite ; accueil neutre | — | DEC-DRT-06 | 1.3 |
| 2.6 | RETEX : circuit auteur → section (si présente) → secteur → service ; correction motivée et nouvelle version | AUD-045 | DEC-RTX-01 à 04 | 2.2 |
| 2.7 | Transfert de matériel : circuit à deux chefs de service, application par l'administrateur habilité, tâches qui suivent, trace avant/après | AUD-044 | DEC-MAT-01 à 04 | 2.1, F-03, IM-11, IM-13 |
| 2.8 | Déploiement et connexions : HTTPS derrière un proxy, limitation des tentatives | AUD-011, 035 | DEC-PRE-06 | Experts SIC, F-11 |
| 2.9 | Fusion de la V1.1 corrigeant AUD-001 | AUD-001 | DEC-FDS-11 | 0.1 |

## Étape 3 — P1/P2 : tâches (cœur du travail quotidien)

| Lot | Contenu | Décisions | Taille / dépend |
|---|---|---|---|
| 3.1 | Priorités normale/haute/urgente ; origine de la priorité ; une priorité du chef de secteur ne peut être abaissée par le chef de section | DEC-TAC-04, 05 | Grosse (migration) |
| 3.2 | Case « Validation du responsable requise » ; statut « À valider » ; approbation ou correction motivée ; validation directe par le chef de secteur ; distinction avec les visas techniques | DEC-CLO-01 à 05 | Grosse |
| 3.3 | Rang des grades (configurable) ; coordinateur proposé, choix du chef en cas d'égalité ou de désignation libre | DEC-COL-02 à 05, PT-ORG-01 | Grosse ; IM-02 |
| 3.4 | Tâche bloquée : notification du responsable, déblocage sans anomalie obligatoire ; état explicite « Non réalisée — À reprogrammer » | DEC-BLQ-01 à 05, PT-TAC-01 | Grosse ; IM-09 ; supervision de Celery (AUD-032) |
| 3.5 | Qualifications affichées à titre informatif, jamais bloquantes | DEC-QUA-01 à 03 | Petite |
| 3.6 | Notifications et trace des changements d'attribution et de priorité | DEC-TAC-06 | Petite, avec 3.1 |

3.2 est indépendant de 2.2 : la validation ordinaire du chef de secteur ne demande pas de suppléance.

## Étape 4 — P2 : maintenance, anomalies, durées

| Lot | Contenu | Décisions | Dépend de |
|---|---|---|---|
| 4.1 | Périodicités nommées et échéance depuis la réalisation effective, calendrier fixe sur option de fiche ; historique des retards | DEC-PER-01 à 04 | IM-14 |
| 4.2 | Durée estimée (option B) : historique, médiane robuste, charge en heures-personnes, exclusion des attentes, correction manuelle | DEC-DUR-01 à 07, PT-DUR-01 à 07 | 3.4 (périodes bloquées), 4.1 |
| 4.3 | Remarques d'outillage et d'instruction, visibles du chef de secteur, sans modification automatique de la fiche | DEC-OUT-01 à 05 | — |
| 4.4 | Anomalies et interventions : plusieurs interventions par anomalie, clôture indépendante, décision du chef de secteur ; ticket : statuts inconnus rejetés ; message d'alerte pour une non-conformité sur installation | DEC-ANO-01 à 05 | F-04, F-12, IM-04, IM-15 |

## Étape 5 — P2 : feuilles de service et appareillage

| Lot | Contenu | Décisions | Dépend de |
|---|---|---|---|
| 5.1 | Feuille de service : alerte de réimpression après nouvelle version ; suppléant COMAEQ habilité ; échanges décidés par le COMAEQ | DEC-FDS-02, 06, 07 | 2.2, F-02, IM-06, IM-07 |
| 5.2 | Fraction à quai : composition paramétrable, signalement des postes vacants | DEC-FDS-08, 09 | F-13 |
| 5.3 | Préparation à l'appareillage : contrôles issus des fiches de référence, circuit section/secteur → service → COMANAV, contrôles obligatoires, réserves, points critiques non dérogeables, actualisation par version de référence | DEC-APP-01 à 13, PT-APP-01 | F-07, 2.2 |
| 5.4 | Doublon de créneau sur liste publiée | AUD-033 | Avec les voies D-05/D-06 de Notion |

## Étape 6 — P2 : mutation de personnel

DEC-MUT-01 à 05 : conserver le compte, demande de rattachement par le nouveau bâtiment, information et confirmation de l'ancien, régularisation motivée, droits retirés à la date effective, historique conservé. Dépend de 1.3, 2.5 et F-05.

## Étape 7 — P2/P3 : ergonomie

DEC-UX-01 à 11 : correction des boutons et liens (AUD-008, 016, 027), titres d'onglet (AUD-018), tours de service à venir/à valider/effectués, épinglage du menu, recherche de personnes, vue personnelle du calendrier (AUD-025), archivage des notifications (AUD-038), niveaux d'annonce (AUD-041, F-08). **Garde-fous** : ne pas dégrader les écrans déjà acceptés (recherche globale, menu latéral : N5) ; recette visuelle du PO sur captures.

## Étape 8 — P3 : dette, documentation, évolutions

CI hors ligne et tests navigateur (AUD-002, 003 ; F-14), documentation Notion et CLAUDE.md (AUD-004, 005), tests des modules secondaires (AUD-030), découpage des vues géantes (AUD-029), complément de la démonstration (AUD-036), import de personnel (AUD-012), mesure du rapport de bilan (AUD-013), prêts et inventaires (AUD-040, différé).

## Ordre d'exécution et dépendances

```
0 ──► 1.1 ┐
      1.2 ├──► 2.1 ──► 2.3 ──► 5.1
      1.3 ┤      │       ▲
      1.4 ┘      ▼       │
                2.2 ──► 2.6, 5.3
        1.3 ──► 2.4, 2.5 ──► 6
        2.1 ──► 2.7
3.x (indépendant de 2.x sauf 3.3 → IM-02) ──► 4.2 (via 3.4)
```

## Priorités

Voir `K_PRIORITES_JUSTIFIEES.md` (le tableau de la première version, à 8 P0, est retiré).

## Fonctionnalités nouvelles demandées par le PO et absentes de l'audit

Ces écarts ne correspondent à aucune des 47 anomalies ; ils figurent dans le plan pour ne pas être perdus : priorités à trois niveaux, validation de tâche, coordinateur, « Non réalisée », périodicités nommées, durées actualisées, remarques d'outillage, intervention distincte de l'anomalie, mutation, transfert de matériel, suppléance générale, alerte de réimpression, préparation à l'appareillage, circuit RETEX hiérarchique, épinglage du menu.
