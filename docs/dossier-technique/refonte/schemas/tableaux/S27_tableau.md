<!-- Brouillon généré depuis S27_stock_et_pieces.mmd : à rédiger en phrases ; le schéma est remplacé par ce tableau (plan §4). -->

| Élément | Contenu |
|---|---|
| `MV` | Mouvement de stock : entrée, sortie, inventaire, correction |
| `SO` | Quantité de la pièce : somme des mouvements |
| `AL` | Seuil minimal : alerte « avertissement » ; seuil critique : alerte « danger », avec Web Push |
| `TK` | Ticket correctif |
| `DP` | Demande de pièces : lignes à commander, commandée, expédiée, reçue, consommée |

| De | Condition ou passage | Vers |
|---|---|---|
| Mouvement de stock : entrée, sortie, inventaire, correction | — | Quantité de la pièce : somme des mouvements |
| Quantité de la pièce : somme des mouvements | — | Seuil minimal : alerte « avertissement » ; seuil critique : alerte « danger », avec Web Push |
| Ticket correctif | — | Demande de pièces : lignes à commander, commandée, expédiée, reçue, consommée |
| Demande de pièces : lignes à commander, commandée, expédiée, reçue, consommée | pièce consommée prélevée au stock | Mouvement de stock : entrée, sortie, inventaire, correction |
