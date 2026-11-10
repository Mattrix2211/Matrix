# E. Stratégie de tests

Le catalogue complet des 117 scénarios d'acceptation est dans `E2_CATALOGUE_TESTS.md`. La couverture décision ↔ test est dans `C_MATRICE_TRACABILITE.md` (C.1 et C.3). **Aucun test n'a été exécuté pour ce dossier** ; la référence de départ est celle de l'audit (3 829 tests verts sur SQLite et PostgreSQL à `1c37f22`).

## E.1 Principes

1. **Un test par règle de décision**, nommé par son identifiant `T-…`, rattaché à une `DEC-…` ou à une `AUD-…`.
2. **Quatre familles à chaque lot** : cas nominal, refus d'accès (UI, POST, API, accès direct), cas limite, historique (rien n'est écrasé, qui/quand/valeur précédente).
3. **Droits côté serveur** (RT-01) : chaque refus est testé sur la requête, pas sur l'absence d'un bouton.
4. **Deux moteurs** : SQLite et PostgreSQL ; migration d'une base peuplée sans perte (T-REG-04).
5. **Non-régression des droits** : la matrice de droits (`sondes/matrice_droits.py`) ne doit jamais devenir plus permissive qu'en V1.1 (T-DRT-04). Les mutations de droits de l'audit (13 mutations, 12 tuées, une survivante) montrent que les tests de droits doivent viser la fonction exacte.
6. **Pas de test simulé** : un test non exécuté est déclaré non exécuté (règle de N5).
7. **Jeu de données fictives** : comptes par rôle, aucun nom réel, créés sur une instance isolée (kit `scripts/preparer_instance_test.py`), jamais par `seed_demo` hors de cette instance.

## E.2 Scénarios par rôle (extrait de la matrice des profils)

| Rôle | Nominal | Refus | Limites | Historique |
|---|---|---|---|---|
| Équipier | T-TAC-08, T-TAC-12, T-MNT-06 | T-DRT-02, T-DRT-03, T-FDS-01 | T-TAC-14 | T-MNT-05 |
| Chef de section | T-TAC-05 | T-TAC-02, T-TAC-03 | T-RTX-02 | T-RTX-04 |
| Chef de secteur | T-TAC-04, T-TAC-06, T-TAC-07, T-TAC-13, T-ANO-01..03, T-MNT-01..02 | — | T-TAC-10, T-DUR-07 | T-DUR-01, T-APP-06 |
| Chef de service | T-MAT-01, T-APP-02 | T-APP-03, T-APP-05 | — | T-APP-08 |
| COMAEQ / suppléant | T-FDS-03, T-FDS-04, T-FDS-07 | T-FDS-10 | T-SUP-03 | T-FDS-05, T-SUP-04 |
| BSC | T-FDS-02, T-FDS-06, T-FDS-08 | — | T-FDS-09 | T-FDS-05 |
| Administrateur technique | T-MAT-02 (application) | T-DRT-01, T-FDS-11 | — | T-CPT-02 |
| Exploitant | T-SEC-01 à 06 | T-SEC-02, T-SEC-03 | T-SEC-04 | T-REG-04 |
| Compte incomplet / muté | T-CPT-05, T-CPT-06 | T-CPT-04 | T-CPT-07 | T-CPT-08, T-CPT-09 |
| Suppléant | T-SUP-01 | T-SUP-02, T-SUP-07 | T-SUP-03, T-SUP-06 | T-SUP-04, T-SUP-05 |

## E.3 Familles de cas limites à ne pas oublier

- **Secteur sans section** (DEC-ORG-02) : circuit RETEX, attribution, validation sans chef de section.
- **Égalité de grades** dans une tâche collective ; participants de corps différents.
- **Chef de section absent** sans suppléance : le chef de secteur valide quand même.
- **Double équipage** : une feuille par équipage et par jour ; équipage à terre.
- **Fin de journée** et fuseau du bâtiment (IM-09) ; Celery arrêté.
- **Durée** : moins de 3 mesures, mesure aberrante, tâche collective, tâche bloquée plusieurs jours.
- **Transfert de matériel** : tâche ouverte à réattribuer, tâche clôturée conservée, double approbation incomplète.
- **Mutation sans réponse** de l'ancien bâtiment ; compte désactivé qui a des tâches ouvertes.
- **Référence d'appareillage modifiée** pendant une préparation ouverte, puis pendant une préparation signée.
- **Double envoi** d'un formulaire (AUD-033).

## E.4 Non-régression obligatoire à chaque lot

| Famille | Test |
|---|---|
| Suite complète | T-REG-01 (SQLite), T-REG-02 (PostgreSQL) |
| Sondes d'audit | T-REG-03 : `docs/audit-general-v11/sondes/rejouer_tout.sh` (branche d'audit) |
| Migrations | T-REG-04 |
| Exports | T-REG-05 |
| Absences | T-REG-06 |
| QR | T-REG-07 |
| Droits | T-DRT-04 |
| Navigation | T-UX-06 (liens morts) |

## E.5 Critères de sortie d'un lot

Tests du lot verts ; non-régression verte sur les deux moteurs ; relecture indépendante pour une grosse tâche (CLAUDE.md) ; tableau « corrigé / testé / bloqué / décision PO requise » comme en N5 ; ce qui n'a pas été exécuté (Windows natif, Safari, lecteur d'écran, imprimante réelle) est écrit noir sur blanc ; **aucun merge ni déploiement sans votre accord**.
