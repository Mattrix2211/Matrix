# Passage A : QA intégration et fiabilité (agent `qa-integration`)

- **SHA** `59dd2f2`, worktree jetable ; PostgreSQL 16 jetable (`matrix_int*`) et SQLite ; client de test Django, aucun navigateur. Dépôt non modifié.
- **Déjà établi avant lui, non recompté** : suite SQLite 2 833 OK, migrations PostgreSQL, retour arrière `logistics` 0013/0014, ANO-001, ANO-002. **Déclaré par la PR #8** : suite verte, test `notify_overdue_occurrences` intermittent, migrations PostgreSQL « non éprouvées ». Tout le reste ci-dessous est exécuté par l'agent.
- **Réserve** : une partie des constats vient de POST forgés ou de double soumission, gestes que l'interface normale ne propose pas ; leur gravité est notée en conséquence.

## Synthèse par ligne de couverture

| Id | Statut | Résultat |
|---|---|---|
| INT-01/03 | Exécuté, **Échoué** sur PostgreSQL | **197 tests en échec sur 2 833** : 181 pour la cause d'ANO-001, 8 en cascade (`InterfaceError: connection already closed` dans `assets.tests.test_documents_installation`), 6 `training/tests/test_fusion_formations.py:39` (`AUTOINCREMENT`, syntaxe SQLite dans le test, `fusionner_formations` non éprouvée sur PostgreSQL), 1 `notify_overdue_occurrences`, 1 `test_push_fallback` (ANO-002). Applications entièrement vertes : absences, accounts, demandes, logistics, org, postes, retex, threads |
| INT-04 | **Réussi** | Stocks préservés avant, après retour arrière et après reprise ; somme des mouvements = quantité. Réserve P3 : le retour arrière détruit l'historique réel des mouvements |
| INT-05 | Réussi (tâches, annonces→tâches, demandes) ; **Échoué** (quarts) | Tâche attribuée : audit, notification avec lien, « Aujourd'hui », calendrier du marin et du chef, invisible pour un autre équipier |
| INT-06 | Échoué (partiel) | Voir D-05, D-12, D-04, D-08 |
| INT-07 | Exécuté | Tâches, demandes, relève, annonces : conformes. Listes, maintenance, blocage : D-05, D-10, D-11 |
| INT-08 | Réussi (fonctions), Échoué (test) | Relances et rappel d'accusé sans doublon. Le test « intermittent » est **déterministe selon l'ordre d'exécution** (premier appel dans le processus = une requête de plus car cache `ContentType` froid, 29 ≠ 30) : défaut du test, pas du produit |
| INT-09 | **Échoué** | D-02, D-03, D-04, D-08, D-09 |
| INT-10 | Redis et WeasyPrint réussis ; Web Push échoué (D-07) ; pywebpush absent non testé | Sans Celery beat, relances/alertes/diffusion différée n'ont pas lieu, sans signalement dans l'interface (P3 d'exploitation) |

## Extension d'ANO-001 (même ligne `annonces/services.py:166`)

`filtre_ciblage` est réutilisée : sur PostgreSQL, `/`, `/annonces/`, `/programme/` (`programme/services.py:141`), `/calendar/events/` (`calendar_app/api_views.py:351`) et les widgets de documentation (`documentation/services.py:62`) répondent 500 pour 8 comptes sans équipage : `cdt_nor`, `chef_secteur_nor`, `equipier_nor` et les 5 comptes de BordOps I. Parcours de pages sur PostgreSQL de 22 comptes de démo : 2 833 réponses 200, 9 réponses 500 (8 = ANO-001, 1 = D-01).

## Défauts nouveaux

| Id | Prio | Constat | Où |
|---|---|---|---|
| D-01 | P3 | `GET /programme/nouveau/` par `admin` : 500 (écriture lors d'un GET : `TypeProgramme` avec `ship_id=None`) | `programme/services.py:33-37` |
| D-02 | P2 | PostgreSQL : un NUL ou plus de 200 caractères dans un POST donne 500 (tâche, annonce `DataError`) ; `SansNulMiddleware` ne nettoie que la query string, `_valider` ne contrôle pas la longueur | `matrix/core/middleware.py:34-40` ; `annonces/services.py:211-232` |
| D-03 | P3 | Identifiant non numérique dans un POST forgé : 500 (13 cas) ; `/calendar/events/?start=abc` : 500 | `taches/web_views.py:104` ; `absences/web_views.py:63` ; `calendar_app/api_views.py:37-60` |
| D-04 | P2 | Modification simultanée d'une annonce : un 500 et un titre contredisant l'historique (version 2 conservée ≠ contenu publié) | `annonces/services.py:240-255` |
| D-05 | P2 | Liste de quarts PUBLIÉE modifiable directement (ajout/suppression de créneau) sans nouvelle version, sans `AuditLog`, sans notification du marin : contre les principes 7 et 8 de `CLAUDE.md` | `quarts/listes_views.py:656-707` |
| D-06 | P2 | Aucun conflit de planning détecté à l'affectation (créneau pendant une permission validée, doublon, hors période de la liste) ; détection seulement pour les échanges | `quarts/echanges.py:55-146` |
| D-07 | P2 | Web Push synchrone sans délai maximal : création d'une notification DANGER bloquée > 12 s si l'endpoint ne répond pas (contre « Internet n'existe pas ») | `notifications/push.py:77` ; `signals.py` |
| D-08 | P2 | Écrasement du stock par une fiche périmée (quantité 9 au lieu de 14) : mécanisme prouvé, course réelle non reproduite | `logistics/web_views.py:~785-797` |
| D-09 | P3 | Double soumission : demande « Résolu » deux fois (2 messages, 4 notifications), liste republiée deux fois, tâche créée deux fois ; les tâches (verrou) sont protégées | `demandes/web_views.py:145` ; `quarts/models.py:477` |
| D-10 | P3 | Maintenance `CANCELLED` repasse `IN_PROGRESS` par « Enregistrer » | `maintenance/web_views.py:_ecrire` |
| D-11 | P3 | Tâche bloquée terminée directement par l'assigné, sans levée par le chef (à confirmer par le PO) | `taches/services.py` |
| D-12 | P3 | Programme : `modifier_evenement` écrase titre, lieu, description sans valeur antérieure ; un changement de lieu ne prévient pas le public | `programme/services.py:105-116` |
| D-13 | P3 | N+1 sur `/annonces/` (+1 requête par annonce : 15 → 35, 85 → 105 avec 20 annonces) | `annonces/web_views.py:63` ; `models.py:cible_libelle` |
| D-14 | P3 | Journal d'audit limité aux 200 dernières lignes, sans filtre ; pas de journal propre à une tâche alors que `docs/DEMO.md` (étape 8) en parle | `matrix/views.py:469` |

## Synthèse de passation (décision PO : dans la V1, configurable, activée par défaut)

- Validation de la relève par `cdt_b` : 1 `SynthesePassation` (9 blocs), audit `passation_generee` + `changement_equipage` + `releve_validee`, notifications aux chefs de l'équipage montant ; seconde validation refusée, synthèse unique.
- Désactivée (`ParametresPassation.active=False`) : relève valide, aucune synthèse, aucune trace ; les synthèses déjà générées deviennent illisibles (404) tant que le paramètre est coupé (P3). Sans enregistrement de paramètre : activée.
- **Résilience** : génération en échec simulé (exception puis erreur SQL réelle sur PostgreSQL) : la relève est validée, l'équipage à bord change, seul `passation_echec` est écrit (sans la cause), la transaction survit grâce au point de sauvegarde. **Défaut P3** : aucune notification ni message à l'utilisateur, qui voit « relève validée » (`matrix/core/equipage.py:210-223`). Reprise manuelle sans doublon.
- **Incohérences documentaires** : Notion « Décisions » (10/10) dit « pas de synthèse automatique planifiée à date » (code : rien de planifié, la synthèse naît de la validation de la relève : compatible, décision PO du jour) ; `docs/REFERENCE.md:20` parle de « deux équipages en miroir » alors que la décision Notion exclut l'organisation en miroir ; `docs/REFERENCE.md` et le message de refus du code désignent le réglage différemment (« Seuils par rôle »).

## Cadrage (questions pour le PO)

- « Service à quai » et « garde » sont un seul modèle `ServiceGarde` (libellé « Service à quai / garde », type libre) ; quart, feuille de service, programme et absence sont distincts. Aucune génération automatique de tours.
- **QR code présent en V1** (`/api/assets/installations/<id>/qr_png/` → 200, route `scan/<uuid>/`, `qrcode[pil]` dans `requirements.txt`) alors que le cadrage le dit hors V1 (P3, à trancher).

## Performances (PostgreSQL, équipier / chef de section / commandant)

`/` 58 / 39 / 77 requêtes (constant avec la charge) ; `/taches/` 13 / 21 / 21 ; `/calendar/events/` 25 / 26 / 21 ; `/notifications/` 17 / 18 / 16 ; `/annonces/` 15 / 15 / 85 puis 35 / 35 / 105 (D-13). `/postes/` : 162 requêtes pour `admin`. Aucun autre N+1.

## Non testé / impossible à vérifier

Concurrence réelle entre deux navigateurs, rendu visuel, persistance d'un brouillon à la reconnexion, pywebpush absent, course réelle sur la fiche de pièce (D-08), `fusionner_formations` sur PostgreSQL.

## Recommandations de l'agent

1. Corriger ANO-001 en priorité (4 familles de pages, 181 tests) et ajouter PostgreSQL au protocole de non-régression.
2. P2 à planifier avant la V1 : D-02, D-04, D-05, D-06, D-07, D-08.
3. Questions au PO : D-11, service à quai contre garde, QR code, synthèses illisibles à la désactivation, mention « miroir » de `docs/REFERENCE.md`.
