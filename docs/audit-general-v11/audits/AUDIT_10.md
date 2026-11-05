# Audit 10 — Logistique, stocks et inventaires

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). (tâche Notion « À faire plus tard »).

| Contrôle | Résultat |
|---|---|
| Quantité d'une pièce = somme de ses mouvements | **vérifié** sur la base de démonstration (3 pièces, 0 écart) |
| Sortie supérieure au stock | refusée (`StockInsuffisant`) |
| Inventaire sans motif | refusé (`MotifRequis`) |
| Suppression d'un mouvement | refusée (`ValidationError`) : historique immuable |
| Écriture d'un mouvement par un équipier ou un suivi à terre | 403 |
| Écriture par un chef de section hors périmètre de la pièce | 404 |
| Concurrence | verrou de ligne dans le code ; **suite complète OK sous PostgreSQL**, dont les tests de concurrence ; pas de test de charge |
| Lien avec la maintenance (prélèvement depuis un ticket, ligne de demande « Consommée ») | décrit et testé par la suite ; non rejoué |

## Écarts par rapport à l'expression de besoin

Cahier §21 : stocks, pièces, consommables, outillage, EPI, demandes, **prêts, retours, inventaires**. Présents : pièces, mouvements, inventaire de pièces, demandes de pièces. **Absents** (différés par décision) : prêts, retours, inventaires d'outillage et d'EPI. Fonctionnalité manquante connue, pas un bug.

## Non vérifié

Interface de stock en navigateur, seuils d'alerte de stock bas (tâche Celery), échantillon réduit (3 pièces), réservations.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Invariants du stock rejoués (somme des mouvements, refus du stock négatif, motif obligatoire, immuabilité) ; mutation « stock négatif accepté » **tuée par les tests**.

### Non vérifié ou dépendant d'une validation externe

Interface de stock en navigateur, seuils d'alerte planifiés, prêts et retours (différés).
