<!-- couvre: restreint/13_logistique_technique.md | Chapitre 13 (technique) — Logistique : mécanismes -->
<!-- couvre: restreint/13_logistique_technique.md | Tests -->
<!-- couvre: restreint/13_logistique_technique.md | Limites -->
<!-- partie: Modules -->
# Logistique : mécanismes

<div class="ligne-public"><b>Public :</b> développeurs, administrateurs · <b>Ce que vous y trouverez :</b> les références de code, les droits et les points non vérifiés du chapitre</div>

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
| Routes web | `logistics/web_urls.py` (`stock/`, `stock/<pk>/mouvements/`, `tickets/<uuid>/prelever-stock/`, `part-request/…`, `part-line/…`) |
| Mouvements | `logistics/mouvements_web.py` `StockPieceMouvementsView` (:32) |
| API | `logistics/urls.py` : tickets, part-requests, part-lines ; pas de route stock |

Schéma : S27.

Non vérifié : aucun circuit d'approbation de commande dans `logistics/` ; aucune décision V1.2 sur le stock.

## Tests

🟢 logistics/tests/ (228 fonctions).

## Limites

- ⚪ Aucun circuit d'approbation de commande dans `logistics/` ; aucune décision V1.2 sur le stock.
- ⚪ Les envois de notifications ne sont pas rejoués.

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (—).
