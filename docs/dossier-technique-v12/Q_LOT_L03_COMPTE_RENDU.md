# Q. Lot L03 — compte rendu de livraison (AUD-020)

**Branche** : `claude/l03-suppression-sure-v11` (issue de L02, `6e14a65`), commit `6d6d0be`. `main` non modifiée, aucune PR. **Statut : livré, en attente de la validation du PO.**

## 1. Règle métier appliquée

Une unité (bâtiment, service, secteur, section) **ne se supprime jamais tant qu'un objet la référence** : marins, matériel, installations, listes de quart, annonces, documents, fiches, désignations, relevés d'équipage, configuration du bâtiment (seuils de rôle, modules)… On l'**archive** (L02), ce qui conserve tout. Une unité sans aucune référence peut être supprimée, avec ses sous-unités vides.

## 2. Ce qui a été fait

| Exigence | Réalisation |
|---|---|
| Identifier les cascades | Inventaire de 105 relations vers les unités (14 applications) |
| Empêcher la suppression d'une unité référencée | 92 relations passées en `PROTECT` ; exclues : la hiérarchie bâtiment → service → secteur → section (suppression d'unités vides) et `ReferenceBatiment.unite` (simple référentiel, remis à vide) |
| Aucune extension de droits | Aucun rattachement n'est jamais remis à vide par une suppression ; la configuration d'un bâtiment (seuils, modules) l'empêche aussi d'être supprimé, car sa disparition remettrait les valeurs par défaut |
| Historique, auteurs, validations, traces | Rien n'est supprimé ; refus tracé (`suppression_unite_refusee`), suppression réussie tracée (`delete_<type>`) avec identifiant, nom et nombre de sous-unités |
| Écrans, API, administration | Réglages : refus avec le détail, borné au bâtiment de l'appelant (bâtiment : administrateur général). API : **409** avec le détail au lieu de 204 pour une unité référencée. Administration Django : même service, y compris « supprimer la sélection » |
| Migration | 14 migrations `AlterField`, **sans SQL** ; aller-retour vérifié sur base peuplée (org 0018 annulée puis réappliquée, profil conservé) |

Nouveau : `org/structure_services.py` (`dependances`, `verifier_suppression`, `supprimer`).

## 3. Tests existants adaptés (3, tous parce que la cascade contredisait la règle)

1. `test_securite_ecritures` : la suppression d'une section de 4 marins attendait 204 ; elle attend maintenant 409, section et marins conservés, refus tracé.
2. `test_coherence_configuration` : la suppression en cascade d'un bâtiment emportait ses modules désactivés (qui redevenaient actifs) ; le test vérifie maintenant le refus puis le retrait explicite de la ligne.
3. `processus_config` (nettoyage du test à deux processus, base temporaire) : retire d'abord la configuration.

## 4. Vérifications

| Vérification | Résultat |
|---|---|
| Nouveaux tests `org.tests.test_suppression_unites` | 11 OK ; 2 échouent quand le contrôle est neutralisé |
| Suite complète, avant adaptation | 3 963 tests, 6 échecs, tous dans les 3 tests ci-dessus |
| Tests ciblés après adaptation (cohérence, écritures, org) | OK |
| Relecture indépendante | ✅ sans blocage |
| `makemigrations --check`, `check` | OK |

**Suite complète finale** : voir la section « Suite complète » du message de livraison (à relancer une fois après les dernières retouches).

## 5. Risques résiduels

1. PostgreSQL, Windows et navigateur : non vérifiés ici.
2. Les liens many-to-many `allowed_sectors` ne sont pas empêchés par `PROTECT` mais sont comptés par le contrôle.
3. Fils de discussion ou notifications attachés à une unité par relation générique : non vérifiés (à porter à « Dette — org » si présents).
4. Administration : en cas de course très rare, Django peut afficher « supprimé avec succès » après le message de refus.
5. Tests complémentaires non écrits : sortie de périmètre via Réglages, suppression réussie d'un bâtiment, action de masse.
6. Le code client qui attendait 204 sur une unité référencée reçoit désormais 409.

**Aucun autre lot n'est lancé** (L04 inclus).
