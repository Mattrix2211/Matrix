# P. Lot L02 — compte rendu de livraison (AUD-028)

**Branche** : `claude/l02-archivage-effectif-v11`, dernier commit `a3832b3`, **empilée sur L05 (`517a2ce`) qui contient L01** : fusion dans l'ordre L01, L05, L02. `main` non modifiée, aucune PR. **Aucune migration.** Statut : livré, en attente de validation du PO. L03 et L04 non lancés.

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

## 4. Décision à confirmer par le PO

**Le matériel compte comme occupation.** Une unité qui porte des installations ou du matériel ne peut pas être archivée tant qu'ils ne sont pas réaffectés (cohérent avec la décision « matériel toujours rattaché à une entité responsable »). Conséquence : en l'absence de circuit de transfert (lot L13), un secteur équipé ne peut pas encore être archivé. À assouplir si vous le souhaitez (par exemple n'exiger que l'absence de marins actifs).

## 5. Risques résiduels (non bloquants, à verser à la dette)

1. Points d'attache non protégés : pièce de stock (`logistics/web_views.py`, secteur posté), création de liste de quarts (le POST ne revérifie pas l'unité, seul l'affichage filtre), cibles de formation existantes (l'API de formation refuse une unité archivée même inchangée), création en masse de matériel du catalogue (`bulk_create`, contourne `clean()`).
2. `add_service / add_sector / add_section` : si une unité archivée du même nom existe, le message « ajouté » s'affiche sans créer ni réactiver (`get_or_create`) ; `duplicate_ship` recopie les services archivés comme actifs.
3. Une valeur de rattachement vidée dans le formulaire d'édition met toujours le rattachement à NULL (comportement antérieur, acte volontaire).
4. Mises à jour en masse de comptes : une unité archivée est refusée même pour un compte qui la porte déjà (prudent).
5. Archiver un bâtiment passe par l'API ou l'administration, pas par l'écran Réglages.
6. Le calcul des unités encore occupées fait une requête par unité archivée (acceptable à cette échelle).
7. Pas de test d'intégration qui poste le formulaire `edit_user` d'un compte désactivé rattaché à une unité archivée (le contenu des listes est testé, pas la soumission).

## 6. Suite recommandée

**L03 (suppression sûre des unités)** : elle s'appuie directement sur L02 (même module `org/archivage.py`, même notion d'obstacles) et demande une migration de protection (`on_delete=PROTECT`). Les tests existants qui supposent la suppression en cascade devront être réécrits avec votre accord. Rien n'est lancé sans votre GO.
