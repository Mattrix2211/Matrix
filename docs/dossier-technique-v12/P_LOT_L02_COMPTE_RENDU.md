# P. Lot L02 — compte rendu de livraison (AUD-028)

> **Mis à jour après l'arbitrage du PO** : le matériel et les installations continuent de compter comme occupation (règle confirmée, non assouplie), et les contournements résiduels ont été fermés (§7). Le §4 et les risques du §5 sont mis à jour en conséquence.

**Branche** : `claude/l02-archivage-effectif-v11`, dernier commit `6e14a65` (version consolidée, voir §7), **empilée sur L05 (`517a2ce`) qui contient L01** : fusion dans l'ordre L01, L05, L02. `main` non modifiée, aucune PR. **Aucune migration.** Statut : livré, en attente de validation du PO. L03 et L04 non lancés.

## 1. Règle appliquée (`org/archivage.py`, règle unique)

- Une unité (bâtiment, service, secteur, section) est **active** si elle et tous ses ancêtres ne sont pas archivés ; sinon **archivée**.
- **Archiver ne supprime rien** et ne modifie ni le rattachement des marins ni leur périmètre (vérifié par test : profil et filtres de périmètre identiques avant/après).
- **Archiver une unité occupée est refusé**, avec les effectifs dans le message : marins actifs, installations, matériel (sous-unités comprises). Un compte désactivé ne bloque pas. Réactiver sous un parent archivé est refusé. Créer ou déplacer une unité sous un parent archivé est refusé.
- **Idempotent** : archiver ou réactiver deux fois ne change rien et ne trace qu'une fois. Chaque changement est dans `AuditLog` (avant → après).
- Une unité archivée n'est **plus proposée ni acceptée pour un nouveau rattachement** ; une **valeur déjà portée reste modifiable** (renommer, éditer la fiche d'un marin ou d'un matériel).

## 2. Où la règle s'applique

| Point | Effet |
|---|---|
| Modèles (`clean()`), administration Django | Archiver une unité occupée refusé |
| API de structure (`/api/org/…`) | 400 avec message : archivage d'une unité occupée, création / réactivation / déplacement sous un parent archivé ; renommer une unité archivée reste possible |
| Écran Réglages > Hiérarchie | Boutons **Archiver / Réactiver**, badge « Archivé », refus avec message ; ajout d'un sous-élément refusé sous une unité archivée ; périmètre : un administrateur ne touche que son bâtiment |
| Affectation des marins (annuaire web, API des comptes) | Unité archivée refusée sauf valeur inchangée ; l'annuaire garde dans ses listes les unités archivées auxquelles un compte, même désactivé, est encore rattaché (aucun rattachement perdu, aucun élargissement de périmètre) |
| Matériel et installations | Rattachement à une unité archivée refusé (formulaires, affectation en masse, import, API) ; valeur inchangée tolérée |
| Listes de choix de nouvelles saisies | Désignation de chef de liste, secteur d'une anomalie, cibles d'annonces / documents / programme / postes : unités actives seulement. **Lecture et gestion de l'existant inchangées** (les annonces ciblant une unité archivée restent lisibles) |

## 3. Résultats

| Vérification | Résultat |
|---|---|
| Suite complète SQLite (`test --parallel 4`) sur `a3832b3` | **3 931 tests OK, 20 ignorés** (3 895 de L05 + 36 nouveaux) |
| Nouveaux tests (`org/tests/test_archivage.py`) | 36 OK ; test de mutation (règle neutralisée) : 16 échecs ; retrait des 3 correctifs de relecture : 3 échecs |
| `check`, `makemigrations --check` | OK, aucun changement de modèle |
| Relectures indépendantes | Première : ❌ trois blocages réels (affectation en masse du matériel, API matériel rejetant une valeur archivée inchangée, compte désactivé perdant son option) ; **tous corrigés** ; seconde : ✅ validé |
| Défaut de ma propre règle trouvé par un test | les unités « déjà portées » étaient comparées par identifiant seul (collision entre niveaux) ; comparées désormais par type et identifiant |

**Non exécuté** : PostgreSQL (non disponible ; 20 tests ignorés) ; navigation sur l'écran Réglages dans un vrai navigateur (couvert par des tests de vue et de gabarit, pas par une recette visuelle).

## 4. Arbitrage du PO (confirmé)

**Le matériel et les installations comptent comme occupation.** Une unité ne peut pas être archivée tant que ses marins actifs, ses installations et son matériel n'ont pas été réaffectés. La règle n'est pas simplifiée à la seule vérification des marins. Conséquence assumée : en l'absence de circuit de transfert (lot L13), un secteur équipé ne peut pas encore être archivé ; le matériel se réaffecte entre-temps par l'affectation en masse existante.

## 5. Risques résiduels (non bloquants, à verser à la dette)

1. *(Corrigé, voir §7)* pièce de stock, POST de création de liste, exigences de formation, création en masse du catalogue.
2. *(Corrigé, voir §7)* `get_or_create` trompeur et `duplicate_ship`.
3. Une valeur de rattachement vidée dans le formulaire d'édition met toujours le rattachement à NULL (comportement antérieur, acte volontaire).
4. Mises à jour en masse de comptes : une unité archivée est refusée même pour un compte qui la porte déjà (prudent).
5. Archiver un bâtiment passe par l'API ou l'administration, pas par l'écran Réglages.
6. Le calcul des unités encore occupées fait une requête par unité archivée (acceptable à cette échelle).
7. *(Corrigé, voir §7)* test d'intégration de l'édition d'un compte désactivé.
8. Autres rattachements à une unité, sans contrôle d'archivage : `ReferentFormation.ship` (API de formation) et `DemandePlace.ship` (le navire est toujours celui de l'appelant) ; `ChefDeListe` créés hors des vues, imports non audités.
9. Concurrence : entre le test d'existence et la création d'un homonyme, une course pourrait lever une erreur d'intégrité (le risque existait avec `get_or_create`). `duplicate_ship` n'est pas atomique (antérieur).
10. Le message « Ce secteur est archivé » du stock s'affiche aussi quand l'archivage vient du service parent.

## 7. Corrections complémentaires (arbitrage du PO)

Règle appliquée : les données historiques restent consultables selon les droits existants ; aucune **nouvelle** affectation vers une unité archivée ; une valeur déjà portée reste modifiable ; pas de refonte des modules.

| # | Point | Correction |
|---|---|---|
| 1 | Pièces de stock | Création et déplacement vers un secteur ou une section archivés refusés (message) ; une pièce déjà dans un secteur archivé reste modifiable sans changer de secteur |
| 2 | Listes de quarts et de gardes | Le POST de création (index et assistant, qui passent tous deux par `_creer_liste`) et la désignation d'un chef de liste revérifient l'unité côté serveur |
| 3 | Formation | Exigences de formation (API) : nouvelle cible archivée refusée pour tous les rôles, administrateur général compris ; cible existante inchangée tolérée ; les refus de rôle gardent le message d'origine |
| 4 | Catalogue | `creer_exemplaires` (`bulk_create`) vérifie le rattachement avant toute écriture ; l'assistant affiche l'erreur |
| 5 | `get_or_create` | Un homonyme existant (archivé ou actif) n'est ni réactivé ni annoncé comme ajouté ; message dédié, qui invite à réactiver s'il est archivé |
| 6 | `duplicate_ship` | Les services, secteurs et sections archivés ne sont pas recopiés (donc jamais « réactivés » par copie) ; l'original est intact |
| 7 | Édition d'un compte désactivé | Test d'intégration : le rattachement à l'unité archivée, le périmètre et l'historique sont conservés ; déplacement vers une autre unité archivée refusé ; l'option reste proposée dans le formulaire |

**Vérifications** : suite complète SQLite sur `6e14a65` : **3 952 tests OK, 20 ignorés** (3 931 + 21 nouveaux ; `org/tests/test_archivage.py` passe à 57 tests). Test de mutation : retirer chacune des six corrections fait échouer au moins un test (11 échecs au total). Module formation relancé après le dernier ajustement : 317 tests OK. `check` et `makemigrations --check` OK, aucune migration. **Relecture indépendante ciblée : ✅ validé**, aucun point bloquant ; sa remarque sur le message de permission de formation a été corrigée.

**Régressions vérifiées par la suite complète** : comptes (annuaire, API, création et édition), listes de quarts et échanges, stock, formations, matériel et installations, annonces, anomalies.

**Limites non vérifiées** : PostgreSQL (non disponible ; 20 tests ignorés) ; recette visuelle dans un navigateur (écran Réglages, assistant d'équipement).

## 6. Suite recommandée

**L03 (suppression sûre des unités)** : elle s'appuie directement sur L02 (même module `org/archivage.py`, même notion d'obstacles) et demande une migration de protection (`on_delete=PROTECT`). Les tests existants qui supposent la suppression en cascade devront être réécrits avec votre accord. Rien n'est lancé sans votre GO.
