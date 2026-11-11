# Chapitre 13 — Logistique : stock de pièces et demandes de pièces

> **Pour qui :** marins, responsables, développeurs. **Diffusion :** générale (références dans `restreint/13_logistique_technique.md`).
> **Ce que vous y trouverez :** comment le bord suit ses pièces de rechange, comment une réparation consomme du stock, comment une pénurie est signalée, et ce que Matrix ne fait pas encore (commande, approvisionnement flotte).
> **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.

---

## 13.1 Deux logiques complémentaires

| | **Stock proactif** | **Demande de pièces** |
|---|---|---|
| Question | « Qu'ai-je en réserve à bord ? » | « Il me faut telle pièce pour réparer ce matériel » |
| Objet | Fiche de pièce de rechange (`StockPiece`) | Demande rattachée à **un ticket correctif**, avec des lignes |
| Indépendance | Existe sans ticket | N'existe que par un ticket |

Les deux se rejoignent quand une ligne de demande est **consommée** : Matrix peut alors sortir la quantité du stock.

## 13.2 Ce que voit et fait le marin

- Il **consulte** le stock de son périmètre : référence, désignation, **NNO** (numéro de nomenclature OTAN, facultatif, texte libre), quantité, seuils, emplacement, photo, note ; une pastille indique **stock normal, bas ou critique**.
- Il **voit les pièces d'un ticket** sur lequel il intervient, avec l'état de chaque ligne.
- Il ne **modifie pas** le stock : les écritures commencent au seuil `stock_ecriture` (chef de section par défaut).

## 13.3 Ce que font les responsables

| Qui (seuil par défaut) | Ce qu'il fait |
|---|---|
| **Chef de section ou plus** (action `stock_ecriture`) | Crée ou modifie une pièce, **prélève** pour un ticket, saisit une **entrée**, un **inventaire** ou une **correction**, gère les lignes de demande de pièces de son périmètre |
| **Chef de secteur et plus** | Mêmes droits sur un périmètre plus large ; création d'une pièce **dans un secteur de son périmètre** uniquement |
| **Acteur à terre** | Consultation et commentaire seulement |

Le seuil est **réglable par bâtiment** (chapitre 5). Toute écriture est **bornée au périmètre** de la personne.

## 13.4 Le stock : un solde qui se justifie

![Stock et pièces](../schemas/svg/S27_stock_et_pieces.svg)

*Schéma S27 — Mouvements de stock et demandes de pièces.*

Règle centrale : **la quantité d'une pièce n'est jamais « tapée » ; elle résulte de mouvements.**

| Mouvement | Effet | Motif |
|---|---|---|
| **Entrée** | Ajoute | Facultatif |
| **Sortie** | Retire (refusée si le stock est insuffisant) | Facultatif ; rattachée à un ticket quand elle vient d'une intervention |
| **Inventaire** | Ramène le stock à l'effectif compté ; l'écart est enregistré | **Obligatoire** |
| **Correction** | Variation signée | **Obligatoire** |

Garanties (🟢 vérifiées au code) :
- un **mouvement n'est jamais modifié ni supprimé** : une erreur se corrige par un **nouveau mouvement** ;
- chaque mouvement garde **l'auteur, le motif, le solde après** et le lien éventuel au ticket ;
- l'écriture se fait **sous verrou**, dans une transaction : deux sorties simultanées ne peuvent pas rendre le stock négatif ;
- chaque mouvement est **audité** ;
- une **même sortie n'est jamais comptée deux fois** pour un même ticket et une même pièce.

## 13.5 La demande de pièces d'un ticket

1. Sur un ticket, un chef ouvre une **demande de pièces** (avec une date « nécessaire avant ») puis ajoute des **lignes** : référence, désignation, quantité, fournisseur, numéro de commande, coûts estimé et réel.
2. Chaque ligne suit les états : **À commander → Commandée → Expédiée → Reçue → Consommée** (ou **Retournée**).
3. Quand une ligne passe à **Consommée**, Matrix **tente une sortie de stock** pour cette ligne, si la personne a le droit de gérer le stock. Trois issues, toutes explicites à l'écran :
   - sortie enregistrée ;
   - **stock insuffisant** → avertissement, aucune sortie ;
   - **sortie déjà enregistrée** → avertissement, pas de doublon ;
   - droit de stock insuffisant → avertissement : la ligne passe « consommée » mais **sans sortie**.
4. Un chef peut aussi **prélever directement** une pièce du stock pour un ticket ; la sortie est **tracée dans la discussion du ticket**.

⚪ Dans l'état B, **la demande de pièces n'a pas de circuit d'approbation ni de commande réelle** : les états décrivent le suivi par le bord ; rien n'est transmis à un système d'approvisionnement.

## 13.6 Alertes de pénurie

Une tâche planifiée quotidienne contrôle le stock :
- sous le **seuil minimal** → alerte de niveau **avertissement** ;
- sous le **seuil critique** (ou à 0 si non renseigné) → alerte de niveau **danger** (déclenche un push) ;
- destinataires : **chef de service, chef de secteur et chef de section** dont le périmètre correspond à la pièce ;
- **une seule alerte active** par pièce et par destinataire (pas de rappel quotidien) ; elle est **mise à jour** si la situation s'aggrave ou s'améliore, et **résolue** quand le stock repasse au-dessus du seuil.

## 13.7 Droits en un coup d'œil

| Action | Seuil | Borne |
|---|---|---|
| Voir le stock | Tout marin du périmètre | Périmètre, équipage |
| Créer / modifier une pièce, mouvement, inventaire, prélèvement | `stock_ecriture` (chef de section) | Périmètre ; service de la pièce |
| Changer l'état d'une ligne de demande | Chef de section dans le périmètre du ticket | Périmètre du ticket |
| Sortie automatique à la consommation | `stock_ecriture` | Idem |

## 13.8 Interactions avec les autres modules

| Module | Lien |
|---|---|
| Tickets (ch. 12) | Une demande de pièces appartient à un ticket ; la consommation sort du stock |
| Installations (ch. 11) | Les pièces d'une installation (avec NNO) sont listées sur sa fiche ; elles sont **distinctes** du stock |
| Notifications | Alertes de stock bas / critique |
| Accueil (ch. 6) | Indicateur « pièces sous le seuil » (vue flotte, dashboard de classe) |
| Préparation à l'appareillage (ch. 16) | Pièces critiques manquantes |

## 13.9 Cas particuliers

- **Une pièce appartient à un bâtiment et à un service** (obligatoires) ; la section est facultative.
- **Équipage à terre / soutien à terre** : lecture seule.
- **Pièce sans NNO** : permis (champ facultatif, pièces anciennes).
- **Pièces de l'installation ≠ stock** : la liste de pièces d'une installation décrit ce qu'elle contient ; le stock décrit ce qui est à bord.

## 13.10 Fonctionnement cible 🔵

Le dossier V1.2 ne contient **aucune décision du PO** sur le stock ni sur la commande de pièces. Le cahier des charges prévoit une logistique plus large (approvisionnement, circuit SSF) mais **rien n'est validé ni développé** : ce chapitre ne décrit donc aucune cible.

## 13.11 Limites et éléments non vérifiés

- 🟢 Tests de l'état B : `logistics` (exécution à lancer, voir `RAPPORT_E3.md`).
- ⚪ Absence de circuit d'approbation pour les demandes de pièces : constatée au code, non confirmée comme voulue.
- ⚪ Les envois de notifications n'ont pas été rejoués.
- ⚪ Pas de page de détail rejouée dans un navigateur.

---

**Sources (état B).** `logistics/models.py`, `logistics/stock.py`, `logistics/web_views.py`, `notifications/tasks.py`. Références dans `restreint/13_logistique_technique.md`.
