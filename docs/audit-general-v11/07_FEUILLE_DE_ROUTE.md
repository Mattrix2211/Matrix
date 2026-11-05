# Feuille de route priorisée — version 0 (provisoire)

**Ne pas utiliser avant l'audit 18.** Elle est fondée sur trop peu de constats pour être arbitrée. Éléments d'ores et déjà établis, par criticité :

| Priorité | Élément | Justification |
|---|---|---|
| P1 | Garde-fou `seed_demo` (AUD-009) et procédure de production HTTPS/réseau de bord (AUD-011) | Risque de comptes à mot de passe connu ; bâtiment bloqué à l'installation |
| P1 | Décider du sort de `main` (AUD-001, DP-01) | La ligne `main` contient une permission trop large sur la feuille de service |
| P2 | Intégration continue et tests navigateur versionnés (AUD-002, AUD-003) | Garde-fou de non-régression absent ou non rejouable |
| P2 | Lien mort de l'accueil (AUD-008), mot de passe PostgreSQL par défaut (AUD-010), import de l'effectif (AUD-012) | Confiance dans l'accueil ; sécurité ; mise en service |
| P2 | Trancher la passation (AUD-006) | Périmètre de V1 incertain |
| P3 | Aligner les documents (AUD-004, AUD-005) et traiter les résidus Rondes (AUD-007) | Clarté et dette |

**Ajouts de la 2ᵉ passe** (propositions, non lancées) : DP-09 (droits par niveau), DP-10 (HTTPS du bord), AUD-017 (clé d'exemple acceptée), AUD-016 et AUD-018 (liens refusés, titres d'onglet). DP-03 (sections) est en analyse.

Aucun travail de développement n'est lancé sans accord du PO.
