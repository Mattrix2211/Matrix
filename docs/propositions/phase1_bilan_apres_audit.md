# Phase 1 après audit indépendant — bilan

Branche `claude/iteration-ux-v11-20261102`. Départ : `2b0fe3b`. Arrivée de la phase 1 : `30b5fc7`. Aucun merge, aucun déploiement.
Le rapport `MATRIX_V11_AUDIT_INDEPENDANT.md` n'a pas été transmis à cet environnement : les points traités sont ceux de l'ordre de travail.

## 1. Corrections

| # | Point | Correction | Commit |
|---|---|---|---|
| 1 | **P0 — Calendrier** | Le déplacement (glisser-déposer) d'une occurrence ou d'un ticket applique `niveau_ecriture_sur`, comme les fiches et l'API. L'indicateur `editable` et les actions rapides du popover suivent la même règle (le bouton n'est pas le seul garde-fou : le serveur refuse). Exception conservée : l'assigné replanifie sa propre occurrence. Objet absent ou hors périmètre : 404 ; action interdite sur un objet visible : 403 | `ec5fa87` |
| 2 | **P0 — Sécurité à l'exécution** | Bloc « Sécurité de l'intervention » sur `/maintenance/occurrences/<id>/execute/` : EPI, consignes et précautions avant intervention, risques particuliers (champ « attention » des étapes), points de contrôle obligatoires. Mêmes données que le document imprimable (`securite_fiche`, une seule source). Colonne collante sur grand écran, en tête sur mobile, repliable mais ouverte par défaut. Fiche sans consigne : message explicite | `ec5fa87` |
| 3 | **Feuille — BSC** | Le rédacteur désigné de l'équipage propriétaire lit sa feuille pendant la validation (`suivi_redacteur_feuille`) ; modification et nouvelle proposition refusées (403) ; un renvoi explicite lui rend le brouillon et efface les visas | `30b5fc7` |
| 4 | **Feuille — « Publier »** | Un seul bouton « Publier » pour le COMAEQ (plus de « Viser et publier », plus de « Visa du COMAEQ et publication »). Le comportement serveur existait déjà et est conservé : une transaction verrouillée relit le contenu, compare l'empreinte visée, vérifie statut, équipage et droits, fige la version, enregistre auteur et horodatage, trace dans l'`AuditLog` | `30b5fc7` |
| 5 | **Erreurs** | 20 réponses 400 « introuvable » deviennent des 404 Matrix ; tout 400 nu d'une page du site (« Action inconnue », date invalide…) est habillé en page Matrix « Requête invalide » (API, JSON et HTMX inchangés) ; `Feuille introuvable` en 404 | `30b5fc7` |

### Précisions et corrections d'interprétation

- **« Créer le brouillon » pour l'équipage B à terre : pas de défaut.** Mon constat de l'audit était **erroné**. L'action est **autorisée par conception** (décision : chaque équipage, à bord ou à terre, rédige et vise sa propre feuille ; exceptions du middleware `ACTIONS_FEUILLE_SERVICE_A_TERRE`) : le clic a bien créé le brouillon de l'équipage B. Le bouton reste donc visible. Les écritures interdites à l'équipage B restent masquées côté serveur par le middleware d'équipage à terre.
- **Visas devenus invalides** : l'empreinte vérifiée à la publication porte sur les **affectations (personnel) et les alertes**, pas sur le texte de l'en-tête. Le texte de l'en-tête n'est modifiable ni par le rédacteur (verrouillé pendant la validation) ni autrement que par la **correction légère du COMAEQ**, qui conserve les visas selon la règle déjà validée (similarité, motif obligatoire, une par cycle). Une affectation modifiée après les visas (échange, remplacement) refuse la publication, invalide les visas et renvoie en brouillon (tests existants `test_feuille_service_rectificatif`). **Point à confirmer par le PO** : une correction légère d'en-tête qui conserve les visas est-elle bien le comportement voulu ?

## 2. Inventaire des autres mutations présentant le risque « état-major non borné par service »

| Domaine | Bornage par service | Statut |
|---|---|---|
| Tickets, stock, anomalies, matériels, installations (+ documents), occurrences (exécution, correction, plans), correctifs, tournées, plan du navire, équipement par le catalogue | **oui** (`niveau_ecriture_sur`) | Mesuré et testé |
| API REST (`RolePermission`) | **oui** | Testé |
| **Calendrier : déplacement** | **oui (nouveau)** | Mesuré avant/après, 8 tests |
| Fiches de maintenance d'installation (proposer une version) | rôle chef de section/secteur seulement : l'état-major n'est **pas** rédacteur | Pas de risque identifié |
| Catalogue flotte, exemplaires, propositions flotte | périmètre global (spécialité), hors service | Non concerné |
| Tâches (attribution), formations (validation), documents, RETEX, programme (événements de service), absences (validation), postes | **non** | Risque identique ; **matrice proposée, arbitrage PO requis, rien restreint** |
| Quarts : publication de listes (`liste_service_publication`), alertes d'organisation | seuil de niveau, chef de liste désigné | **À analyser** : non mesuré pour un état-major sur une liste d'un service non rattaché |

## 3. Tests (phase 1)

- **SQLite : 235 tests ciblés OK ; PostgreSQL 16 : 235 tests ciblés OK** (modules : déplacement calendrier, événements personnels, exécution et fiche imprimable, circuit de la feuille sur les deux équipages, visa COMAEQ vacant, échanges, feuille à terre, vues quarts, tickets hors périmètre, pages d'erreur sans DEBUG, écriture des commandants adjoints, matrice de permissions).
- Nouveaux : `calendar_app/tests/test_deplacement_par_service.py` (8), `maintenance/tests/test_execution_securite.py` (3), `quarts/tests/test_feuille_service_circuit_bsc.py` (6, équipages A et B), 3 tests d'habillage des erreurs.
- 21 tests anciens ajustés : l'ancienne attente **400** devient **404** (décision de politique d'erreur) ; aucun test n'a été supprimé pour passer.
- Un test que j'avais écrit (modification d'en-tête après visas) a été retiré : il visait un chemin impossible par l'interface (voir §1).
- **Les suites complètes ne sont pas relancées à ce stade** : elles le seront sur le HEAD final de la recette.

## 4. Sondes de permissions rejouées (16 profils)

Avant : COMOPS et COMAEQ déplaçaient les occurrences et tickets des autres services (✔). Après : refus 403 pour toutes les fonctions hors service rattaché, 404 pour les chefs hors périmètre, la ligne « Calendrier » est identique à la ligne « Ticket : transition ». Tableaux `avant` / `apres` dans le ZIP de phase 1.

## 5. Parcours rejoués (copie de la base de démonstration)

- P04 : les consignes (EPI, attention, points critiques) sont affichées sur l'écran d'exécution ; document imprimable inchangé.
- P05 : le BSC rouvre sa feuille proposée (**200**, lecture seule) ; les visas demandent une confirmation ; le COMAEQ voit le bouton unique « Publier » (1 bouton, ancien libellé absent) et la feuille passe à « Publiée » ; le COMANAV n'a ni visa ni publication ; l'équipage B lit.
- P08 : 404 Matrix pour objets absents ou hors périmètre ; plus de 400 brut.

## 6. Défauts résiduels et non exécuté

- **Parcours d'échange de tour** : toujours non démontrable (conflits d'affectation de la démonstration) → phase 2 (scénarios cohérents).
- **Vocabulaire « Difficultés signalées / Anomalies »** : non traité (phase 3).
- **Quarts / alertes** : analyse de bornage par service à faire.
- **Safari / iOS** : non exécuté (aucun environnement disponible). Tests navigateur sous Chromium seulement.
- **Relecture indépendante** (agent `relecteur`) du diff de la phase 1 : **non réalisée** à ce stade.
- Les captures « après » proviennent d'une instance de démonstration (DEBUG actif) ; les pages d'erreur d'un serveur sans DEBUG.
