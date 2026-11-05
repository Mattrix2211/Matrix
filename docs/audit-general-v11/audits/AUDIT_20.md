# Audit 20 — Données de démonstration

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Périmètre : génération reproductible par les quatre commandes `seed_demo*`, mesures sur base temporaire ; non couvert : `lancer_demo.bat` sous Windows).

## Mesures (pipeline complet : `seed_demo`, `seed_demo_mer_quai`, `seed_demo_dense`, `seed_demo_metier`, ≈ 54 s sur SQLite)

| Mesure | Valeur |
|---|---|
| Comptes | 61, dont 60 avec le mot de passe `pass` et 1 avec `admin` |
| Rôles couverts | compte de flotte 1, administrateur d'unité 1, commandants 6, second 1, état-major 5, chefs de service 5, de secteur 8, de section 2, équipiers 32 |
| Bâtiments | 5, dont 1 à double équipage (A/B) ; modes mer et quai d’après `docs/recette/01_COMPTES.md` (non revérifiés) |
| Échanges de service | 7 (demandé 2, accepté 1, validé 1, refusé 1, rejeté 1, annulé 1) : tous les états couverts |
| Tâches | 37 (en cours 10, à faire 11, terminées 9, bloquées 7) |
| Absences | 10 ; feuilles de service 1 |
| **Secteurs sans section** | **0** : le cas DP-03 n'est pas exercé |
| Noms de bâtiments | **4 sur 5 sont des noms réels** de l'inventaire 2025 (Bretagne, Normandie, Jacques Chevallier, Auguste Bénébig) |
| Base `seed_demo` seule (sans les trois autres) | 42 comptes, 0 échange : la démonstration n'est cohérente qu'avec le pipeline complet |

## Constats

- **AUD-024 (DONNÉES, P2)** : noms réels de bâtiments dans la démonstration (tâche Notion « noms de bâtiments fictifs » déjà au backlog, à faire).
- **AUD-009** : mots de passe connus et absence de garde-fou (rappel).
- **AUD-008** : l'assignation d'un ticket hors périmètre est un défaut de **donnée** de démonstration en plus du défaut de code.
- Couverture : tous les états d'un échange, tâches bloquées, double équipage, activation différée, désignation historique. **Manquants** : secteur sans section, marin transversal, suppression d'unité, bâtiment sans COMAEQ titulaire, délégation de visa.
- Les données de démonstration sont relatives à la date du jour (rejouables).

## Réserves

Fidélité aux usages réels non évaluée (accès à un expert du bord requis) ; Windows non testé ; dates relatives non testées dans le temps.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Déjà clos avec réserves (voir plus haut).

### Non vérifié ou dépendant d'une validation externe

Fidélité aux usages réels (expert du bord), Windows.
