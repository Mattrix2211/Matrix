# Matrice unique de conformité — version 0

États : **V-C** vérifié conforme ; **V-NC** vérifié non conforme ; **PC** partiellement conforme ; **NV** non vérifié ; **DIFF** volontairement différé ; **ARB** décision métier à arbitrer.

À ce stade, **aucun audit fonctionnel n'est terminé** : la quasi-totalité des lignes sont NV. Cette matrice grandira avec les audits ; elle ne doit pas être lue comme un bilan.

| Exigence | Domaine | État | Preuve | Audit |
|---|---|---|---|---|
| EX-002 | Configuration | PC | Seuils de rôle en base par bâtiment (`matrix/core/role_thresholds.py`, `org/models.py:132`) ; le reste non audité | 02 |
| EX-003 | Hors-ligne | **V-C** pour le code statique (aucune URL externe active dans gabarits, scripts, styles) ; comportement réseau réel NV | `audits/AUDIT_15.md` §1 | 15 |
| EX-009 | Bord–terre | DIFF | Phase 7 « volontairement différée » (Notion FDR) | 13 |
| EX-021 | Génération auto abandonnée | PC (aucun générateur trouvé par recherche textuelle) | `grep` sur `quarts/` | 09 |
| EX-026 | Rédaction de la feuille | **V-C sur 1c37f22** pour la création (rejoué : `equipier_a` 403, rédacteurs désignés 302, 11 profils) ; non conforme sur `main` (lecture de code) ; édition, API et autres actions NV | `quarts/models.py:2065` ; `audits/AUDIT_06.md` §1 | 06, 09 |
| EX-033 | Passation | ARB | AUD-006 | 06 |
| EX-036 | Fonctions adjudant de compagnie, OSS | DIFF (pas de GO) | Notion ORG | 19 |
| EX-049 | PÉPIN, CRAT, RAV/c | DIFF | Notion ORG | 19 |
| EX-054 | Retrait de Rondes | V-C partiel : absence de routes affirmée par un test ; test non rejoué isolément par l'audit | `matrix/tests/test_module_rondes_retire.py` | 12 |
| EX-004 | Voir sa journée à l'ouverture | PC : 10 profils, environ 330 liens de l'accueil ouverts sans erreur 500 ; un lien mène à une 404 (AUD-008) ; justesse du contenu NV | `audits/AUDIT_06.md` §3 | 04 |
| Autres (EX-001, 005 à 008, 010 à 014, 020 à 035, 037, 038, 040 à 053) | — | NV | — | 02 à 12 |

Résultats de la suite de tests : voir `08_LIMITES_ET_PREUVES.md` (§3).
