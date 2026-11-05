# Matrice de non-régression (3ᵉ passe)

Principe : une fonctionnalité validée est protégée par (1) un test de la suite existante (3 829 tests, verts sur SQLite et PostgreSQL), (2) une sonde d'audit rejouable (`sondes/`, jetable, non intégrée à la suite), (3) une ligne de recette. Aucun test n'a été supprimé, désactivé ou assoupli par l'audit. Une colonne « Lacune » signale ce qu'un test vert ne démontre pas.

| Domaine | Fonctionnalité validée à protéger | Tests existants (non évalués un par un) | Sondes d'audit rejouables | Lacune constatée | Changements qui la menacent |
|---|---|---|---|---|---|
| Permissions | écritures refusées hors périmètre, hors fonction ; étanchéité équipage et bâtiment | `matrix/tests/test_etancheite_equipage*.py`, `test_securite_*.py`, `test_core_permissions.py`, `test_fuites_sans_rattachement.py` | `matrice_droits.py`, `droits2.py`, `sonde_pages_par_profil.py`, `sonde_routes_anonymes.py` | aucun test ne parcourt « liens affichés ↔ droits serveur » (AUD-016) | P02 (droits fonctionnels), P05 (planchers) |
| Organisation | hiérarchie, COMA par service, création d'unité | `org/tests`, `test_commandants_adjoints.py`, `test_creation_unite.py` | `structure.py`, `structure2.py`, `api_org.py`, `cascade.py` | aucun test de suppression avec conséquences, ni de secteur sans section (AUD-020, DP-03) | P01, P04 |
| Calendrier | 7 sources, périmètre, iCal | `calendar_app/tests` | `calendrier.py` | filtre par défaut de l'interface non testé (AUD-025) | personnalisation « Mon quotidien » |
| Maintenance | confirmation sur critique, comptes rendus, tickets | `maintenance/tests`, `assets/tests` | `maintenance.py`, `mnt2.py` | non-conformité sur installation sans ticket non testée (AUD-023) | fiches, périodicité |
| Quarts et services MER/QUAI | circuit de la feuille, droits de rédaction, visa COMAEQ strict, étanchéité | `quarts/tests` (609 tests) | `circuit.py`, `auto_visa.py`, `lecture_brouillon.py`, `navigateur/nav5.js` | test des administrateurs limité à l'équipage B à terre (AUD-014) | D-05, D-06, P02 |
| Notifications | accès par propriétaire | `notifications/tests` | `comm.py` | rappels planifiés non rejoués (ANO-013) | régimes de notification |
| Logistique | stock = somme des mouvements, immuabilité, motif, droits | `logistics/tests` | `stock.py` | charge et concurrence réelle non testées | prêts/retours (différé) |
| Communication | fils et annonces par périmètre | `threads/tests`, `annonces/tests` | `comm.py` | écriture d'un message non concluante | espaces de groupe (abandonnés) |
| Double équipage | séparation A/B, relève, lecture seule à terre | `test_acces_equipage.py`, `org/tests` | `droits2.py` (création inter-équipage), `circuit.py` | relève et passation non rejouées | DP-02 |
| UX V1.1 | accueil, menus, mobile, clavier | `test_navigation_laterale.py`, `test_contrastes.py`, 4 tests JS | `navigateur/nav1.js`, `nav4.js` | aucun test navigateur versionné dans la suite (AUD-003) ; titres d'onglet identiques (AUD-018) | refonte UX |
| Données historiques | migrations, PostgreSQL | suite complète | `migrate` sur base vierge SQLite et PostgreSQL | migration d'une base peuplée non testée | toute migration |
| Parcours de mise en service | installation, initialisation, comptes, structure | `test_core_checks.py` | mesures de `migrate` et `seed_demo` | aucun test de bout en bout ; import de personnel absent (AUD-012) ; proxy TLS non testé (AUD-011) | DP-10, DP-11 |

## Règles pour les corrections futures

1. Toute correction d'une anomalie du registre s'accompagne d'un test qui échoue avant et passe après, ajouté à la suite (pas seulement une sonde).
2. Les tests qui encodent un comportement jugé erroné (par exemple `test_supervision_globale_vise_secteur_et_service_pas_le_comaeq`) sont réécrits **avec** la décision du PO, jamais supprimés pour obtenir du vert.
3. Avant toute fusion : suite complète sur SQLite et sur PostgreSQL, puis rejeu des sondes ci-dessus sur le pipeline complet de démonstration.
