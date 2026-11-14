# Revue manuelle des affirmations et étiquettes du pilote (renforcement du contrôle C2)

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Réalisée le 14/11/2026 par lecture de chaque affirmation étiquetée des trois sources pilotes, rapprochée de l'ancien chapitre 12 **et** du code de l'état B (lecture du code, navigateur ou test selon la ligne). Ce n'est pas une relecture indépendante : elle est faite par l'auteur du pilote ; la relecture indépendante demandée par le PO reste à faire.
> Le contrôle automatique C2 ne compare que des mots ; il n'a servi qu'à repérer les phrases à relire.

## 1. Affirmations étiquetées (14)

| # | Document | Affirmation | Étiquette | Source ancienne | Vérification dans l'état B | Verdict |
|---|---|---|---|---|---|---|
| 1 | RF | Installation critique : la **clôture** exige une confirmation explicite pour un verdict autre que « non conforme » ; refus tracé ; le clôturant est enregistré comme valideur | 🟢 | ch. 12 §12.3 | Code : confirmation exigée seulement hors enregistrement en direct, installation critique, conformité ≠ NON_CONFORME ; refus tracé (`tracer_refus`) ; `valide_par = user` | **Corrigé** : la première rédaction omettait la condition « verdict autre que non conforme » et la distinction « clôture / enregistrement en cours » ; ajoutées |
| 2 | RF | Correction après coup : saisie d'origine conservée, auteur et motif, message de conflit en cas d'écriture simultanée | 🟢 | ch. 12 §12.3 | Code : motif obligatoire si déjà terminé ; `ModificationCompteRendu` ; `_Conflit` | Conforme |
| 3 | RF | « création d'une tâche depuis une anomalie » | ⚪ | ch. 12 §12.9 | Non rejoué | Étiquette conservée (⚪) |
| 4 | RF | Génération des échéances, retards, exécution guidée, compte rendu, correction motivée : disponibles | 🟢 | ch. 12 §12.2–12.4 | Code et navigateur (12/11/2026) | Conforme |
| 5 | RF | Ticket automatique pour un matériel mobile non conforme (gravité 3, une fois par échéance) | 🟢 | ch. 12 §12.3 | Code : signal sur `MaintenanceExecution`, `get_or_create`, `severity = 3`, ignoré si `asset is None` | Conforme |
| 6 | RF | Ticket automatique pour une installation non conforme, avec garde-fous | 🟣 | ch. 12 §12.11 | Aucun code ; proposition D1 « à valider par le PO » | Conforme (reste une proposition, jamais décrite au présent) |
| 7 | RF | Périodicités nommées, échéance depuis la réalisation effective | 🔵 | ch. 12 §12.11 | Code : `every_n_days` (90 par défaut) ; prochaine échéance = dernière planifiée + pas, pas la date de réalisation | **Précisé** : l'état actuel est dit dans la cellule |
| 8 | RF | Remarques d'outillage et d'instruction | 🔵 | ch. 12 §12.11 | Aucun modèle de remarque (recherche textuelle dans les modèles de `maintenance` et `assets`) | Conforme |
| 9 | RF | Durée indicative actualisée, historique des estimations | 🔵 | ch. 12 §12.11 | Code : `expected_duration_min`, `duree_estimee_min` saisis, jamais recalculés | **Précisé** : l'état actuel est dit dans la cellule |
| 10 | RF | Configuration réelle, potentiels, composants | 🔵 | ch. 12 §12.11 | Aucun code ; orientation Notion | Conforme |
| 11 | RF | Sortie de « En validation » : trois chemins, risque de blocage, suspension de l'entretien d'une installation | 🟢 | ch. 12 §12.4, registre A20 | Tests du 12/11/2026 (18), rejoués pendant l'audit le même jour ; navigateur : bouton de correction visible du seul chef de secteur et au-delà | Conforme |
| 12 | RF | Envois de notifications non rejoués | ⚪ | ch. 12 §12.12 | — | Conforme |
| 13 | RF | Écrans de tournée et de ticket complet non rejoués en totalité | ⚪ | ch. 12 §12.12 | — | Conforme (l'ancien « aucun écran rejoué » est remplacé par une limite précise) |
| 14 | DT | Limites de la section technique | ⚪ | 12T « Limites » | — | Conforme |

## 2. Affirmations non étiquetées mais factuelles, vérifiées aussi
| Affirmation (RF, GU ou DT) | Vérification |
|---|---|
| Seuils par défaut : exécution EQUIPIER ; maintenance d'autrui et plans CHEF_SECTION ; correction CHEF_SECTEUR | Registre de seuils (`REGISTRE_ACTIONS`) |
| Anomalie : « chef de section ou plus » prend en compte et convertit ; état-major limité aux services de sa fonction | `_est_chef`, `_peut_traiter` (`niveau_ecriture_sur`) |
| Ticket : chef de section ou plus, périmètre, confirmation de remise en service, REX à la clôture | `TicketTransitionView` |
| Échéances sur 90 jours ; retard sur PLANNED et ASSIGNED ; WAITING_VALIDATION exclu des retards | `generate_occurrences(days_ahead=90)`, `compute_overdue`, `STATUTS_SANS_RETARD` |
| Tout marin peut s'assigner, sauf équipage et soutien à terre | `MaintenanceOccurrenceSelfAssignView` et gabarit de la liste |
| « Le bouton Exécuter apparaît pour des échéances non exécutables » (NE-01) | Navigateur 12/11/2026 : 403 à l'ouverture pour un équipier |
| Modules désactivés : pages refusées, accueil et calendrier affichent encore les maintenances (A25) | Tests du 12/11/2026 ; limite de portée : les pages du guide ne le montrent pas |
| Rondes : retirées de l'interface | Aucune vue dans `rondes/` ; test `test_module_rondes_retire` |

## 3. Ce que cette revue ne couvre pas
- Le **guide utilisateur** ne porte pas d'étiquettes dans le texte : sa justesse dépend de ses captures (provisoires) ; chaque légende renvoie au profil de démonstration.
- Les captures n'ont pas été vérifiées une à une contre les phrases qui les commentent au-delà de ce qui est dit ici ; c'est l'objet de la phase 4.
- Aucune relecture par une seconde personne.
