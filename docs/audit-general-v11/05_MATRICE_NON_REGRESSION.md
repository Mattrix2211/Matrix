# Matrice de non-régression — squelette (complété à la 2ᵉ passe pour Permissions et Quarts)

**Parcours rejouables ajoutés par l'audit** (`sondes/`, jetables, non intégrés à la suite) : circuit complet de la feuille de service en navigateur (5 acteurs, `nav5.js`) ; matrice de droits des quarts (`matrice_droits.py`) ; balayage des liens de 42 comptes (`liens_morts.py`). **À protéger en priorité** : AUD-001 (création de feuille réservée aux rédacteurs désignés), étanchéité entre équipages et entre bâtiments, visa COMAEQ réservé au titulaire.
**Lacunes de test constatées** : aucun test ne vérifie que l'administrateur d'unité ne vise pas la feuille de l'équipage à bord (AUD-014) ; aucun test ne couvre un secteur sans section (DP-03) ; aucun test ne vérifie le proxy TLS (AUD-011).

Non rempli : elle suppose la reconstitution des fonctionnalités validées (audit 01) et la lecture des tests (audit 16). Elle liste ce qui devra être couvert et les fichiers de test déjà présents, sans en évaluer la pertinence.

| Domaine | Fonctionnalité validée à protéger | Tests présents (à évaluer) | Lacune pressentie | État |
|---|---|---|---|---|
| Permissions | Étanchéité équipage et bâtiment, supervision bornée | `matrix/tests/test_etancheite_equipage*.py`, `test_securite_*.py`, `test_core_permissions.py`, `test_fuites_sans_rattachement.py` | Pas de parcours navigateur versionné | À auditer |
| Organisation | Hiérarchie, COMA, création d'unité | `test_creation_unite.py`, `test_commandants_adjoints.py`, `org/tests` | — | À auditer |
| Calendrier | Sources, périmètre JSON | `calendar_app/tests` (17 fichiers) | — | À auditer |
| Maintenance | Fiches, occurrences | `maintenance/tests`, `assets/tests` | — | À auditer |
| Quarts et services MER/QUAI | Listes, échanges, feuille de service, visas | `quarts/tests` (40 fichiers, 609 tests) | Scénarios concurrents sur PostgreSQL à confirmer | À auditer |
| Notifications | Régimes, liens | `notifications/tests` | — | À auditer |
| Logistique | Stock, mouvements | `logistics/tests` | — | À auditer |
| Communication | Fils, annonces | `threads/tests`, `annonces/tests` | — | À auditer |
| Double équipage | Relève, lecture seule à terre | `test_acces_equipage.py` | — | À auditer |
| UX V1.1 | Maquettes A et B, bandeau, menu | `test_navigation_laterale.py`, `test_contrastes.py`, JS | Aucun rendu automatisé | À auditer |
| Données historiques | Migrations, rondes retirées | `test_module_rondes_retire.py`, tests de migration | — | À auditer |
| Mise en service | Initialisation, import | `test_core_checks.py` | Non testé de bout en bout | À auditer |
