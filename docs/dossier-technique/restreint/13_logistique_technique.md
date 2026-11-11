# Chapitre 13 (technique) — Logistique : mécanismes

> **Diffusion restreinte.** Complète `diffusable/13_logistique.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les références de code, les droits et les points non vérifiés du chapitre.

---

| Objet | Référence |
|---|---|
| Pièce de stock | `logistics/models.py` `StockPiece` (:128) |
| Mouvement (immuable) | `logistics/models.py` `MouvementStock` (:222) |
| Demande de pièces | `logistics/models.py` `PartRequest` (:97) ; ligne `PartLineItem` (:107) |
| Écriture d'un mouvement | `logistics/stock.py` `enregistrer_mouvement` (:37) — verrou, transaction, `AuditLog` |
| Sortie automatique à la consommation | `logistics/web_views.py` `PartLineItemUpdateStatusView` (:525) |
| Prélèvement direct | `logistics/web_views.py` `TicketStockPrelevementView` (:564) |
| Liste de stock | `logistics/web_views.py` `StockPieceListView` (:634) |
| Seuil `stock_ecriture` | `matrix/core/role_thresholds.py` (:100), portée navire, chef de section |
| Alerte de pénurie | `notifications/tasks.py` `notify_low_stock` (:101) |

Schéma : S27.

Non vérifié : aucun circuit d'approbation de commande dans `logistics/` ; aucune décision V1.2 sur le stock.

## Tests

🟢 logistics/tests/ (228 fonctions).

## Limites

- ⚪ Aucun circuit d'approbation de commande dans `logistics/` ; aucune décision V1.2 sur le stock.
- ⚪ Les envois de notifications ne sont pas rejoués.

---

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (—).
