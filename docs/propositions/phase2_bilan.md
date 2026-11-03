# Phase 2 (travaux autorisés) — bilan

Branche `claude/iteration-ux-v11-20261102`. Aucun merge, aucun déploiement. Les suites complètes ne sont **pas** relancées (réservées au HEAD final avant demande de GO).

## 1. Décisions PO appliquées

**Correction légère d'en-tête du COMAEQ.** La règle fondée sur la similarité textuelle (ratio ≥ 0,6 ; ajout ≤ 60 caractères) a été **remplacée** : l'ancien test acceptait « Saint Hervé » → « Saint Gilles » comme correction légère, c'est-à-dire un changement d'information qui gardait les visas. Nouvelle règle structurelle (`quarts/correction_legere.py`) : seuls conservent les visas la casse, la ponctuation, les espaces et la **coquille d'un mot** (un caractère de différence, mot d'au moins 4 lettres, trois mots au plus). Tout ajout, retrait, nombre, heure, date, négation, restriction, mot sensible (mer, quai, avant, après, non, sans…) modifié ou remplacement d'un mot par un autre exige une **nouvelle validation** (le COMAEQ renvoie en brouillon). Motif, auteur, date et valeurs avant/après restent tracés (`AuditLog`). 4 tests unitaires et 2 tests de circuit (changement de saint, 14h00 → 04h00 refusés malgré une forte similarité).
**Équipage B à terre : « Créer le brouillon » légitime** — aucune correction (déjà corrigé dans le bilan de phase 1).

## 2. Contrôles complémentaires de phase 1

- **Commits `30b5fc7` et `ba15940`** : `30b5fc7` est le commit de **code** de la phase 1 (BSC, bouton « Publier », 404, middleware, 21 fichiers) ; `ba15940` ne contient que le **document de bilan** (`phase1_bilan_apres_audit.md`), aucun code.
- **Relecture indépendante** (agent relecteur, diff `2b0fe3b..30b5fc7`) : aucun point bloquant ; 3 points importants **corrigés** (commit `c9a69e4`) : (1) le middleware habillait à tort des réponses JSON ou vides hors `/api/` → désormais limité aux réponses `text/plain`/`text/html` non vides sans balise `<html>` ; (2) occurrence du calendrier : le 403 précédait le contrôle de périmètre et pouvait révéler l'existence d'un objet à un autre bâtiment → périmètre (404) avant niveau (403), test ajouté ; (3) N+1 des états-majors dans l'API du calendrier → services rattachés calculés une seule fois par requête, `select_related` complétés, test de requêtes ajouté. Mineurs : test inutile retiré ; `HttpResponseBadRequest` reste utilisé (pas d'import mort) ; message du 404 « créez la feuille d'abord » non affiché (404 générique, accepté) ; texte brut d'un 400 repris dans la page Matrix : échappé, à surveiller.
- **Fiche sans consigne** : le message est désormais « Aucune consigne n'est renseignée sur cette fiche. **Cela ne signifie pas qu'il n'y a aucun risque** : appliquez les consignes du bord et les règles de sécurité de l'équipement, puis signalez l'omission… » ; un test vérifie la phrase et l'absence de « sans risque ».
- **En-tête après visa** : voir §1 (règle structurelle). Reste vrai : l'empreinte de publication couvre les **affectations et alertes**, pas le texte d'en-tête, lequel n'est modifiable que par le rédacteur en brouillon ou par la correction légère du COMAEQ.

## 3. Travaux A, B, C

**A. Échanges de tours** — `quarts/tests/test_echange_parcours_complet.py` (8 tests) : demande, réponse, acceptation, validation par le chef de liste, permutation des affectations, version de liste figée, notifications, traçabilité, calendrier ; refus du marin avec motif ; rejet du chef ; annulation ; **conflits réels** (absence validée, autre liste publiée au même moment, tour déjà commencé) ; équipage B refusé. **Rejoué dans le navigateur** sur la démo dense (13 captures) : échange réussi (demande → acceptation → validation → affectations → notifications → calendrier), échange refusé, conflit réel détecté (« Conflit d'affectation : … déjà affecté(e) à … »). Aucune fausse double affectation.
**B. Démo dense** — `python manage.py seed_demo_dense` : **isolée** (refuse toute base dont `equipier_a` n'a pas le mot de passe fictif ou sans la Bretagne), **reproductible** (graine fixe, dates relatives), **idempotente** (marqueur d'audit), atomique, identités fictives sans nom de rôle (18 marins), **aucune structure non validée** (elle réutilise les services/secteurs/sections existants). Ajoute : 28 tâches (2 priorités, échéances passées/futures, 4 statuts), 14 anomalies dont 6 liées à des tickets à 4 états, 4 tickets directs, 24 occurrences de maintenance (6 statuts, exécutions), 8 événements de programme, 4 annonces, demandes, 6 documents (brouillon/soumis/validé), 5 RETEX, 5 postes affectés, 6 absences, 45 notifications ; un **service à quai** de 5 jours (J+21) et un **quart à la mer** de 7 jours (J+28), périodes disjointes ; 6 échanges aux 6 états. 9 tests. Volumes après génération : 33 tâches, 17 anomalies, 17 tickets, 35 occurrences.
**C. Anomalie → ticket** — `logistics/tests/test_parcours_anomalie_ticket.py` : signalement, permissions (déclarant, autre service, autre commandant adjoint, équipage B refusés), prise en compte, conversion (rattachement à l'équipement, anomalie liée, pas de doublon), affectation (notification), transitions bornées au service, confirmation de remise en service, clôture avec diagnostic et solution, trace et lien retour. **Aucun défaut trouvé** dans ce parcours ; il n'a pas été rejoué dans le navigateur.

## 4. Tests (phase 2)

110 tests ciblés : **SQLite OK, PostgreSQL 16 OK** (démo dense, échanges, parcours anomalie/ticket, correction légère, COMAEQ, calendrier par service, pages d'erreur, sécurité d'exécution, circuit BSC/Publier, échanges existants, visa COMAEQ vacant). Journaux dans le ZIP.

## 5. Défauts résiduels et réserves

- **30 chevauchements mer/quai hérités de `seed_demo`** (3 marins : `equipier_a`, `equipier_a2`, `chef_secteur_a`) : le détecteur `doubles_affectations` les compte ; **non corrigés** car des tests existants s'appuient sur `seed_demo`. La démo dense n'en ajoute aucun et ses scénarios d'échange utilisent des marins sans chevauchement.
- Une seule échelle de priorité de tâche existe (normale / urgente) : « plusieurs priorités » se limite à deux niveaux.
- Listes très longues non paginées en démo dense (maintenance : 35 occurrences, anomalies 17, tâches 33) : à examiner pour la densité (phase 3).
- Le parcours anomalie → ticket est couvert par test, pas rejoué visuellement.
- Safari / iOS non testés ; Chromium seulement.
- `mesure` de permissions de publication des listes et des alertes **non faite** (analyse en §4 du document d'arbitrage, lecture du code).

## 6. Décisions PO en attente (voir `phase2_analyses_pour_arbitrage.md`)

1. Modèle mer/quai (mode d'application sur la liste ou régime du bâtiment). 2. Bornage des modules sans service (par la cible ou par domaine ; ordre). 3. Délégation explicite (forme, qui l'accorde, durée). 4. Publication des listes et validation des alertes (routage par le commandant adjoint compétent). 5. Organigrammes (scission de la Bretagne seule ; 5 questions BRF/POM). 6. Intégration des vues A + B (progressive, après la décision 1).
