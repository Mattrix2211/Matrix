# C. Matrice de traçabilité

Correspondance **décision PO → état dans le code V1.1 → anomalies d'audit → tests d'acceptation**. Les états sont ceux de `A1_DECISIONS_S1_S2.md` ; la preuve est donnée à cet endroit. Les décisions Notion, DP et propositions techniques sont dans `A_REGISTRE_DECISIONS.md` ; leur lien aux anomalies figure dans `H_ANOMALIES_47.md`.

## C.1 Décisions → code → anomalies → tests

| Décision | État du code | Anomalies | Tests |
|---|---|---|---|
| DEC-ORG-01 | Existe | AUD-037 | T-ORG-04, T-ORG-07 |
| DEC-ORG-02 | Partiel | AUD-019 AUD-037 | T-ORG-04, T-ORG-05 |
| DEC-ORG-03 | Partiel | AUD-037 | T-ORG-07 |
| DEC-ORG-04 | Partiel | AUD-022 | T-DRT-04 |
| DEC-ORG-05 | Non vérifié | — | — |
| DEC-ORG-06 | Partiel | AUD-022 | — |
| DEC-DRT-01 | Partiel | AUD-014 AUD-015 AUD-022 | T-DRT-04 |
| DEC-DRT-02 | Partiel | AUD-014 AUD-015 | T-DRT-01, T-FDS-11 |
| DEC-DRT-03 | Non vérifié | — | T-DRT-02 |
| DEC-DRT-04 | Partiel | AUD-025 | T-DRT-03 |
| DEC-DRT-05 | Absent | AUD-020 AUD-021 AUD-028 AUD-034 | T-ORG-01, T-ORG-02, T-CPT-01 |
| DEC-DRT-06 | Non vérifié | AUD-019 | T-CPT-04, T-CPT-05 |
| DEC-MUT-01 | Partiel | — | T-CPT-06 |
| DEC-MUT-02 | Absent | — | T-CPT-06 |
| DEC-MUT-03 | Absent | — | T-CPT-07 |
| DEC-MUT-04 | Absent | — | T-CPT-08 |
| DEC-MUT-05 | Partiel | AUD-034 | T-CPT-08 |
| DEC-MUT-06 | Absent | AUD-034 | T-CPT-09 |
| DEC-MUT-07 | Absent | AUD-034 AUD-020 | T-CPT-01, T-CPT-02, T-CPT-03 |
| DEC-TAC-01 | Non vérifié | — | T-TAC-03 |
| DEC-TAC-02 | Non vérifié | — | T-TAC-04 |
| DEC-TAC-03 | Non vérifié | — | — |
| DEC-TAC-04 | Partiel | — | T-TAC-01 |
| DEC-TAC-05 | Absent | — | T-TAC-02 |
| DEC-TAC-06 | Non vérifié | — | T-TAC-04 |
| DEC-QUA-01 | Non vérifié | — | T-TAC-15 |
| DEC-QUA-02 | Partiel | — | T-TAC-15 |
| DEC-QUA-03 | Non vérifié | — | T-TAC-15 |
| DEC-COL-01 | Existe | — | T-TAC-09 |
| DEC-COL-02 | Absent | — | T-TAC-09 |
| DEC-COL-03 | Absent | — | T-TAC-10 |
| DEC-COL-04 | Absent | — | T-TAC-10 |
| DEC-COL-05 | Absent | — | T-TAC-11 |
| DEC-CLO-01 | Absent | — | T-TAC-05 |
| DEC-CLO-02 | Existe | — | T-TAC-08 |
| DEC-CLO-03 | Absent | — | T-TAC-05, T-TAC-06 |
| DEC-CLO-04 | Absent | — | T-TAC-07 |
| DEC-CLO-05 | Existe | — | T-TAC-11 |
| DEC-BLQ-01 | Existe | — | T-TAC-12 |
| DEC-BLQ-02 | Non vérifié | — | T-TAC-12 |
| DEC-BLQ-03 | Non vérifié | — | T-TAC-13 |
| DEC-BLQ-04 | Non vérifié | — | T-TAC-13 |
| DEC-BLQ-05 | Absent | AUD-039 AUD-032 | T-TAC-14 |
| DEC-PER-01 | Existe | — | T-MNT-01 |
| DEC-PER-02 | Partiel | — | T-MNT-02 |
| DEC-PER-03 | Non vérifié | — | T-MNT-03, T-MNT-04 |
| DEC-PER-04 | Non vérifié | — | T-MNT-05 |
| DEC-DUR-01 | Partiel | — | T-DUR-02 |
| DEC-DUR-02 | Absent | — | T-DUR-01 |
| DEC-DUR-03 | Absent | — | T-DUR-01 |
| DEC-DUR-04 | Absent | — | T-DUR-04 |
| DEC-DUR-05 | Absent | — | T-DUR-03 |
| DEC-DUR-06 | Partiel | — | T-DUR-05 |
| DEC-DUR-07 | Absent | — | T-DUR-06 |
| DEC-OUT-01 | Absent | — | T-MNT-06 |
| DEC-OUT-02 | Absent | — | T-MNT-07 |
| DEC-OUT-03 | Absent | — | T-MNT-07 |
| DEC-OUT-04 | Existe | — | T-MNT-08 |
| DEC-OUT-05 | Existe | — | T-MNT-08 |
| DEC-ANO-01 | Partiel | AUD-043 | T-ANO-01 |
| DEC-ANO-02 | Non vérifié | AUD-043 | T-ANO-01 |
| DEC-ANO-03 | Non vérifié | AUD-043 | T-ANO-02 |
| DEC-ANO-04 | Non vérifié | — | T-ANO-03 |
| DEC-ANO-05 | Partiel | — | T-ANO-01 |
| DEC-FDS-01 | Existe | AUD-001 | T-FDS-01, T-FDS-02 |
| DEC-FDS-02 | Partiel | AUD-014 | T-FDS-03, T-FDS-04 |
| DEC-FDS-03 | Existe | — | T-FDS-03 |
| DEC-FDS-04 | Non vérifié | — | — |
| DEC-FDS-05 | Existe | — | T-FDS-05 |
| DEC-FDS-06 | Non vérifié | — | T-FDS-06 |
| DEC-FDS-07 | Partiel | — | T-FDS-07 |
| DEC-FDS-08 | Partiel | AUD-046 | T-FDS-08 |
| DEC-FDS-09 | Non vérifié | AUD-046 | T-FDS-09 |
| DEC-FDS-10 | Existe | — | — |
| DEC-FDS-11 | Existe | AUD-001 | T-FDS-01 |
| DEC-FDS-12 | Existe | AUD-001 | T-FDS-10 |
| DEC-APP-01 | Partiel | AUD-047 | T-APP-01 |
| DEC-APP-02 | Partiel | AUD-047 | T-APP-02 |
| DEC-APP-03 | Existe | — | T-MNT-08 |
| DEC-APP-04 | Absent | AUD-047 | T-APP-06 |
| DEC-APP-05 | Absent | AUD-047 | T-APP-06 |
| DEC-APP-06 | Absent | AUD-047 | T-APP-07 |
| DEC-APP-07 | Absent | AUD-047 | T-APP-07 |
| DEC-APP-08 | Absent | AUD-047 | T-APP-07 |
| DEC-APP-09 | Absent | AUD-047 | T-APP-08 |
| DEC-APP-10 | Absent | AUD-047 | T-APP-03 |
| DEC-APP-11 | Absent | AUD-047 | T-APP-04 |
| DEC-APP-12 | Absent | AUD-047 | T-APP-05 |
| DEC-APP-13 | Non vérifié | — | T-APP-09 |
| DEC-RTX-01 | Absent | AUD-045 | T-RTX-01, T-RTX-02, T-RTX-05 |
| DEC-RTX-02 | Partiel | — | T-RTX-03 |
| DEC-RTX-03 | Non vérifié | AUD-045 | T-RTX-03 |
| DEC-RTX-04 | Partiel | — | T-RTX-04 |
| DEC-SUP-01 | Partiel | AUD-014 | T-SUP-01, T-SUP-02 |
| DEC-SUP-02 | Partiel | — | T-SUP-03 |
| DEC-SUP-03 | Absent | — | T-SUP-06 |
| DEC-SUP-04 | Partiel | — | T-SUP-04 |
| DEC-SUP-05 | Absent | — | T-SUP-05 |
| DEC-SUP-06 | Non vérifié | — | T-SUP-07 |
| DEC-MAT-01 | Absent | AUD-044 | T-MAT-01 |
| DEC-MAT-02 | Absent | AUD-044 | T-MAT-02, T-MAT-05 |
| DEC-MAT-03 | Absent | AUD-044 | T-MAT-03 |
| DEC-MAT-04 | Non vérifié | AUD-044 | T-MAT-04 |
| DEC-UX-01 | Partiel | AUD-008 AUD-016 | T-UX-01 |
| DEC-UX-02 | Partiel | — | T-UX-01 |
| DEC-UX-03 | Existe | — | T-UX-02 |
| DEC-UX-04 | Absent | — | T-UX-03 |
| DEC-UX-05 | Partiel | — | T-UX-04 |
| DEC-UX-06 | Partiel | AUD-038 | T-UX-05 |
| DEC-UX-07 | Partiel | AUD-008 AUD-016 AUD-026 AUD-027 | T-UX-06 |
| DEC-UX-08 | Partiel | — | T-UX-04 |
| DEC-UX-09 | Absent | — | T-UX-07 |
| DEC-UX-10 | Partiel | — | T-UX-01 |
| DEC-UX-11 | Existe | AUD-025 | T-UX-08 |
| DEC-PRE-01 | Existe | — | T-REG-06 |
| DEC-PRE-02 | Partiel | AUD-006 | T-REG-03 |
| DEC-PRE-03 | Existe | AUD-013 | T-REG-05 |
| DEC-PRE-04 | Existe | — | T-REG-07 |
| DEC-PRE-05 | Existe | — | — |
| DEC-PRE-06 | Absent | AUD-011 AUD-031 | — |
| DEC-QUA-04 | Absent | — | T-QUA-01 |
| DEC-SUP-07 | Partiel | — | T-SUP-01 |
| DEC-FDS-13 | Absent | — | T-FDS-12 |
| DEC-FDS-14 | Partiel | AUD-015 | T-FDS-13 |
| DEC-APP-14 | Absent | AUD-047 | T-APP-10 |

## C.2 Anomalies → décisions → tests

| Anomalie | Classe | Décisions applicables | Tests | Priorité |
|---|---|---|---|---|
| AUD-001 | Déjà corrigée | DEC-FDS-01, DEC-FDS-11, DEC-FDS-12, DEC-DRT-02 | T-FDS-01 T-FDS-02 T-FDS-10 T-FDS-11 T-REG-03 | P1 |
| AUD-002 | Anomalie confirmée | DP-07 (ouverte : CI compatible hors Internet) | T-REG-01 T-REG-02 | P2 |
| AUD-003 | Anomalie confirmée | DP-08 (ouverte) | T-REG-03 | P2 |
| AUD-004 | Anomalie confirmée | DP-04 (ouverte) | — | P3 |
| AUD-005 | Anomalie confirmée | — | — | P3 |
| AUD-006 | Décision PO manquante | DEC-PRE-02, DP-02 | T-REG-03 | P3 |
| AUD-007 | Anomalie confirmée | DP-05 (levée par N5) | — | P3 |
| AUD-008 | Anomalie confirmée | DEC-UX-07 | T-UX-06 | P2 |
| AUD-009 | Anomalie confirmée | DEC-PRE-06, DP-01 ; proposition P06 | T-SEC-01 T-SEC-02 T-SEC-03 T-SEC-04 | P0 |
| AUD-010 | Anomalie confirmée | — | T-SEC-06 | P2 |
| AUD-011 | Anomalie confirmée | DP-10, DEC-PRE-06, P03 | T-REG-03 | P1 |
| AUD-012 | Écart fonctionnel non couvert par l'audit | DP-11 (besoin confirmé) | — | P2 |
| AUD-013 | À reproduire | DEC-PRE-03 | T-REG-05 | P3 |
| AUD-014 | Anomalie confirmée | DEC-DRT-01, DEC-DRT-02, DEC-FDS-02, DP-09 | T-DRT-01 T-FDS-03 T-FDS-04 T-FDS-11 | P1 |
| AUD-015 | Anomalie confirmée | DEC-DRT-02, DP-09, B3 (résiduel) | T-DRT-01 T-FDS-05 | P1 |
| AUD-016 | Anomalie confirmée | DEC-UX-07 | T-UX-06 | P3 |
| AUD-017 | Anomalie confirmée | — | T-SEC-05 | P2 |
| AUD-018 | Anomalie confirmée | — | T-UX-06 | P3 |
| AUD-019 | Anomalie confirmée | DEC-ORG-02, DP-13, A2, A3 | T-ORG-06 | P1 |
| AUD-020 | Anomalie confirmée | DEC-DRT-05, DP-13 ; proposition P07 | T-ORG-01 T-ORG-02 | P0 |
| AUD-021 | Anomalie confirmée | DEC-DRT-05 | T-ORG-03 | P2 |
| AUD-022 | À reproduire | DEC-ORG-06, DEC-DRT-01 | T-DRT-04 | P2 |
| AUD-023 | Anomalie confirmée | — | T-ANO-03 | P2 |
| AUD-024 | Anomalie confirmée | DP-01 | T-SEC-03 | P2 |
| AUD-025 | À reproduire | DEC-UX-11, DEC-DRT-04 | T-UX-08 T-DRT-03 | P3 |
| AUD-026 | Déjà corrigée | DEC-UX-07 | T-UX-06 | P3 |
| AUD-027 | Anomalie confirmée | DEC-UX-07 | T-UX-06 | P3 |
| AUD-028 | Anomalie confirmée | DEC-DRT-05, DP-13 | T-ORG-02 | P1 |
| AUD-029 | Anomalie confirmée | — | T-REG-01 | P3 |
| AUD-030 | À reproduire | — | T-RTX-01 T-RTX-05 | P2 |
| AUD-031 | Anomalie confirmée | DEC-PRE-06 | T-REG-04 | P1 |
| AUD-032 | Anomalie confirmée | DEC-BLQ-05 | T-TAC-14 | P2 |
| AUD-033 | Anomalie confirmée | DEC-FDS-05 | T-FDS-05 | P2 |
| AUD-034 | Anomalie confirmée | DEC-MUT-07, DEC-MUT-06, DEC-DRT-05 ; proposition P07 | T-CPT-01 T-CPT-02 T-CPT-03 T-CPT-09 | P0 |
| AUD-035 | Anomalie confirmée | C5 (ouverte) | T-SEC-07 | P2 |
| AUD-036 | Écart fonctionnel non couvert par l'audit | DP-01 | T-REG-03 | P3 |
| AUD-037 | Décision PO manquante | DEC-ORG-03, DEC-ORG-02 | T-ORG-07 | P3 |
| AUD-038 | Écart fonctionnel non couvert par l'audit | DEC-UX-06 | T-UX-05 | P3 |
| AUD-039 | Anomalie confirmée | DEC-BLQ-05 | T-TAC-14 | P3 |
| AUD-040 | Fonctionnement conforme | — | — | P3 |
| AUD-041 | Décision PO manquante | — | T-UX-06 | P3 |
| AUD-042 | Décision PO manquante | DEC-UX-05 | T-UX-04 | P3 |
| AUD-043 | Anomalie confirmée | DEC-ANO-01, DEC-ANO-03 | T-ANO-04 | P2 |
| AUD-044 | Anomalie confirmée | DEC-MAT-01, DEC-MAT-02, DEC-MAT-03, DEC-MAT-04 | T-MAT-01 T-MAT-02 T-MAT-03 T-MAT-04 T-MAT-05 | P2 |
| AUD-045 | Anomalie confirmée | DEC-RTX-01, DEC-RTX-03 | T-RTX-01 T-RTX-02 T-RTX-05 | P2 |
| AUD-046 | Écart fonctionnel non couvert par l'audit | DEC-FDS-08, DEC-FDS-09 | T-FDS-08 T-FDS-09 | P3 |
| AUD-047 | Anomalie confirmée | DEC-APP-01 à DEC-APP-13 | T-APP-01 à T-APP-09 | P2 |

## C.3 Tests → décisions (couverture inverse)

| Test | Décisions couvertes |
|---|---|
| T-SEC-01 | anomalie / non-régression (voir C.2) |
| T-SEC-02 | anomalie / non-régression (voir C.2) |
| T-SEC-03 | anomalie / non-régression (voir C.2) |
| T-SEC-04 | anomalie / non-régression (voir C.2) |
| T-SEC-05 | anomalie / non-régression (voir C.2) |
| T-SEC-06 | anomalie / non-régression (voir C.2) |
| T-SEC-07 | anomalie / non-régression (voir C.2) |
| T-ORG-01 | DEC-DRT-05 |
| T-ORG-02 | DEC-DRT-05 |
| T-ORG-03 | anomalie / non-régression (voir C.2) |
| T-ORG-04 | DEC-ORG-01, DEC-ORG-02 |
| T-ORG-05 | DEC-ORG-02 |
| T-ORG-06 | anomalie / non-régression (voir C.2) |
| T-ORG-07 | DEC-ORG-01, DEC-ORG-03 |
| T-CPT-01 | DEC-DRT-05, DEC-MUT-07 |
| T-CPT-02 | DEC-MUT-07 |
| T-CPT-03 | DEC-MUT-07 |
| T-CPT-04 | DEC-DRT-06 |
| T-CPT-05 | DEC-DRT-06 |
| T-CPT-06 | DEC-MUT-01, DEC-MUT-02 |
| T-CPT-07 | DEC-MUT-03 |
| T-CPT-08 | DEC-MUT-04, DEC-MUT-05 |
| T-CPT-09 | DEC-MUT-06 |
| T-DRT-01 | DEC-DRT-02 |
| T-DRT-02 | DEC-DRT-03 |
| T-DRT-03 | DEC-DRT-04 |
| T-DRT-04 | DEC-ORG-04, DEC-DRT-01 |
| T-TAC-01 | DEC-TAC-04 |
| T-TAC-02 | DEC-TAC-05 |
| T-TAC-03 | DEC-TAC-01 |
| T-TAC-04 | DEC-TAC-02, DEC-TAC-06 |
| T-TAC-05 | DEC-CLO-01, DEC-CLO-03 |
| T-TAC-06 | DEC-CLO-03 |
| T-TAC-07 | DEC-CLO-04 |
| T-TAC-08 | DEC-CLO-02 |
| T-TAC-09 | DEC-COL-01, DEC-COL-02 |
| T-TAC-10 | DEC-COL-03, DEC-COL-04 |
| T-TAC-11 | DEC-COL-05, DEC-CLO-05 |
| T-TAC-12 | DEC-BLQ-01, DEC-BLQ-02 |
| T-TAC-13 | DEC-BLQ-03, DEC-BLQ-04 |
| T-TAC-14 | DEC-BLQ-05 |
| T-TAC-15 | DEC-QUA-01, DEC-QUA-02, DEC-QUA-03 |
| T-MNT-01 | DEC-PER-01 |
| T-MNT-02 | DEC-PER-02 |
| T-MNT-03 | DEC-PER-03 |
| T-MNT-04 | DEC-PER-03 |
| T-MNT-05 | DEC-PER-04 |
| T-MNT-06 | DEC-OUT-01 |
| T-MNT-07 | DEC-OUT-02, DEC-OUT-03 |
| T-MNT-08 | DEC-OUT-04, DEC-OUT-05, DEC-APP-03 |
| T-DUR-01 | DEC-DUR-02, DEC-DUR-03 |
| T-DUR-02 | DEC-DUR-01 |
| T-DUR-03 | DEC-DUR-05 |
| T-DUR-04 | DEC-DUR-04 |
| T-DUR-05 | DEC-DUR-06 |
| T-DUR-06 | DEC-DUR-07 |
| T-DUR-07 | anomalie / non-régression (voir C.2) |
| T-ANO-01 | DEC-ANO-01, DEC-ANO-02, DEC-ANO-05 |
| T-ANO-02 | DEC-ANO-03 |
| T-ANO-03 | DEC-ANO-04 |
| T-ANO-04 | anomalie / non-régression (voir C.2) |
| T-FDS-01 | DEC-FDS-01, DEC-FDS-11 |
| T-FDS-02 | DEC-FDS-01 |
| T-FDS-03 | DEC-FDS-02, DEC-FDS-03 |
| T-FDS-04 | DEC-FDS-02 |
| T-FDS-05 | DEC-FDS-05 |
| T-FDS-06 | DEC-FDS-06 |
| T-FDS-07 | DEC-FDS-07 |
| T-FDS-12 | DEC-FDS-13 |
| T-FDS-08 | DEC-FDS-08 |
| T-FDS-09 | DEC-FDS-09 |
| T-FDS-10 | DEC-FDS-12 |
| T-FDS-11 | DEC-DRT-02 |
| T-APP-01 | DEC-APP-01 |
| T-APP-02 | DEC-APP-02 |
| T-APP-03 | DEC-APP-10 |
| T-APP-04 | DEC-APP-11 |
| T-APP-05 | DEC-APP-12 |
| T-APP-06 | DEC-APP-04, DEC-APP-05 |
| T-APP-07 | DEC-APP-06, DEC-APP-07, DEC-APP-08 |
| T-APP-08 | DEC-APP-09 |
| T-APP-09 | DEC-APP-13 |
| T-APP-10 | DEC-APP-14 |
| T-FDS-13 | DEC-FDS-14 |
| T-RTX-01 | DEC-RTX-01 |
| T-RTX-02 | DEC-RTX-01 |
| T-RTX-03 | DEC-RTX-02, DEC-RTX-03 |
| T-RTX-04 | DEC-RTX-04 |
| T-RTX-05 | DEC-RTX-01 |
| T-SUP-01 | DEC-SUP-01, DEC-SUP-07 |
| T-SUP-02 | DEC-SUP-01 |
| T-SUP-03 | DEC-SUP-02 |
| T-SUP-04 | DEC-SUP-04 |
| T-SUP-05 | DEC-SUP-05 |
| T-SUP-06 | DEC-SUP-03 |
| T-SUP-07 | DEC-SUP-06 |
| T-QUA-01 | DEC-QUA-04 |
| T-MAT-01 | DEC-MAT-01 |
| T-MAT-02 | DEC-MAT-02 |
| T-MAT-03 | DEC-MAT-03 |
| T-MAT-04 | DEC-MAT-04 |
| T-MAT-05 | DEC-MAT-02 |
| T-UX-01 | DEC-UX-01, DEC-UX-02, DEC-UX-10 |
| T-UX-02 | DEC-UX-03 |
| T-UX-03 | DEC-UX-04 |
| T-UX-04 | DEC-UX-05, DEC-UX-08 |
| T-UX-05 | DEC-UX-06 |
| T-UX-06 | DEC-UX-07 |
| T-UX-07 | DEC-UX-09 |
| T-UX-08 | DEC-UX-11 |
| T-REG-01 | anomalie / non-régression (voir C.2) |
| T-REG-02 | anomalie / non-régression (voir C.2) |
| T-REG-03 | DEC-PRE-02 |
| T-REG-04 | anomalie / non-régression (voir C.2) |
| T-REG-05 | DEC-PRE-03 |
| T-REG-06 | DEC-PRE-01 |
| T-REG-07 | DEC-PRE-04 |

## C.4 Bilan de couverture

- Existe : 21 décisions
- Partiel : 36 décisions
- Non vérifié : 24 décisions
- Absent : 44 décisions
- Décisions sans test associé : DEC-ORG-05, DEC-ORG-06, DEC-TAC-03, DEC-FDS-04, DEC-FDS-10, DEC-PRE-05, DEC-PRE-06
