# Feuille de route priorisée — version 0 (provisoire)

**Ne pas utiliser avant l'audit 18.** Elle est fondée sur trop peu de constats pour être arbitrée. Éléments d'ores et déjà établis, par criticité :

| Priorité | Élément | Justification |
|---|---|---|
| P1 | Décider du sort de `main` (AUD-001, DP-01) | La ligne `main` contient une permission trop large sur la feuille de service |
| P2 | Intégration continue et tests navigateur versionnés (AUD-002, AUD-003) | Garde-fou de non-régression absent ou non rejouable |
| P2 | Trancher la passation (AUD-006) | Périmètre de V1 incertain |
| P3 | Aligner les documents (AUD-004, AUD-005) et traiter les résidus Rondes (AUD-007) | Clarté et dette |

Aucun travail de développement n'est lancé sans accord du PO.
