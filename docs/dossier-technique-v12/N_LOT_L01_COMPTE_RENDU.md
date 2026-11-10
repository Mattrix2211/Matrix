# N. Lot L01 — compte rendu de livraison (AUD-009)

**Branche** : `claude/l01-verrou-demo-v11` (issue de la V1.1 `1c37f22`), dernier commit `8e60fee`. `main` non modifiée, aucune PR. **Statut : livré, en attente de la recette et de la validation définitive du PO.**

## 1. Ce qui a été fait

| Exigence du PO | Réalisation |
|---|---|
| Empêcher l'exécution accidentelle sur une base non dédiée, même en cas de configuration erronée | Les 4 commandes `seed_demo*` exigent **toutes** ces conditions : mode DEBUG, `MATRIX_INSTANCE_DEMO=1`, SQLite sur fichier, fichier voisin `<base>.instance_demo` contenant un **identifiant d'instance non vide** écrit par `scripts/preparer_instance_test.py`, base vide ou déjà marquée en base (`accounts.InstanceDemo`) |
| Aucune modification non autorisée des profils existants | Une base non vide et non marquée est refusée avant toute écriture (testé avec un compte existant homonyme) |
| Pas de mots de passe prévisibles | Plus de `pass` ni `admin` : fournis (`MATRIX_DEMO_PASSWORD`, `MATRIX_DEMO_ADMIN_PASSWORD`) ou générés au hasard dans `<base>.identifiants` (0600, O_EXCL, jamais écrasé, lié à l'identifiant d'instance). Rien dans la sortie ni la ligne de commande. `--identifiants` les affiche à la demande |
| Marquage fondé sur une preuve, pas sur des noms | `marquer_instance_demo` exige l'identifiant du fichier voisin et **ne le crée jamais**. Un fichier vide ou sans ligne `instance :` est refusé. Les noms de comptes sont un contrôle secondaire |
| Anciennes bases de démonstration | Refusées par `--mettre-a-jour` ; deux choix explicites : `--reinitialiser` ou `--mettre-a-jour --adopter-ancienne-base` (accepté seulement si **chaque** compte est un compte de démonstration encore protégé par un ancien mot de passe prévisible) |
| Production | Une base marquée refuse de démarrer hors DEBUG : `matrix.E001` (`manage.py`) et refus à l'import de `wsgi.py` / `asgi.py` |
| Contrôle avant mise en production | `python manage.py verifier_instance` (lecture seule) |
| Création des environnements de démonstration | `preparer_instance_test.py` pose lui-même variable, preuve et chemin des identifiants ; parcours `--reinitialiser`, `--mettre-a-jour`, `--servir` vérifiés de bout en bout |

Migration : `accounts/0021` (table `InstanceDemo`) puis `0022` (champ `identifiant`), additives ; aller-retour vérifié sur une base peuplée, aucune donnée perdue.

## 2. Résultats des vérifications

| Vérification | Résultat |
|---|---|
| Suite complète SQLite (`test --parallel 4`), commit `8e60fee` | **3 884 tests OK, 20 ignorés** (tests réservés à PostgreSQL) |
| Tests ciblés (verrou, script de démonstration) | 80 OK |
| `manage.py check`, `makemigrations --check` | OK (seul avertissement : DEBUG actif, attendu) |
| Migration 0021 → 0022, avancée et retour arrière, base de démonstration peuplée | OK, 61 comptes conservés |
| Parcours officiel `--reinitialiser`, `--mettre-a-jour`, `--identifiants`, `verifier_instance` | OK |
| Ancienne base : refus sans drapeau, adoption d'une base d'origine, refus avec un vrai `admin` | OK |
| Contournements essayés : sans variable, sans DEBUG, base réelle sans fichier voisin, fichier d'identifiants d'une autre instance, production sur base marquée | Tous refusés, rien de modifié |
| Relecture indépendante (deux passes) | Première ✅ ; seconde passe : ❌ sur un fichier voisin vide et sur une preuve fabriquée par le script, corrigés puis ✅ |

**Non exécuté, avec raison** : PostgreSQL (non disponible dans cet environnement ; 20 tests ignorés sur SQLite en dépendent) ; Windows (`lancer_demo.bat`, droits du fichier d'identifiants, console) : environnement Linux ; lecteur d'écran et navigateur : sans objet pour ce lot. Les nouveaux tests qui simulent un chemin SQLite sont ignorés sur PostgreSQL.

## 3. Risques résiduels

1. **Windows non testé.** Procédure de recette : `docs/recette/L01_recette_windows.md`. Sous Windows, le fichier d'identifiants hérite des droits du dossier (le `0600` n'a pas d'effet).
2. **Acte volontaire.** Un opérateur qui crée à la main un fichier voisin `instance : x` sur une base réelle, avec DEBUG, la variable d'activation, SQLite sur fichier, et une base dont tous les comptes portent des noms de la liste de démonstration (par exemple un vrai `admin` seul), peut remplir ou marquer cette base à tort. Aucun enchaînement accidentel ne le permet. Marquer reste du côté sûr (une base marquée refuse de démarrer hors DEBUG) ; le vrai danger est l'exécution de `seed_demo*` sur ces données.
3. **Remarques non bloquantes de la relecture, non traitées pour ne pas modifier le code après la suite complète** : `preuve_presente` du script accepte `instance :` sans valeur (refus propre ensuite par Django) ; `adopter_ancienne_base` écrit le fichier avant la transaction de marquage (état sans danger en cas d'échec) ; `--servir` accepte une ancienne base à fichier vide, en local seulement ; un refus d'adoption laisse les migrations déjà appliquées.
4. **Fichier d'identifiants** : un fichier par base, jamais partagé ; il reste en clair sur le disque du poste de démonstration (fictif).
5. `seed_demo` sur une base marquée réécrit toujours le profil des comptes homonymes : comportement idempotent voulu, limité aux bases de démonstration.

## 4. Documentation mise à jour (sur la branche L01)

`README.md`, `docs/DEMO.md`, `docs/TESTS_MARINS.md`, `docs/demo/guide_recette_metier.md`, `docs/recette/01_COMPTES.md`, `docs/recette/L01_recette_windows.md` (nouveau), `.gitignore` (`*.identifiants`).

## 5. Pour recetter

```bash
git fetch origin claude/l01-verrou-demo-v11 && git checkout claude/l01-verrou-demo-v11
python scripts/preparer_instance_test.py --reinitialiser
python scripts/preparer_instance_test.py --identifiants
python scripts/preparer_instance_test.py --servir
```

Puis `python manage.py seed_demo` sans variable : refus attendu. Recette Windows : suivre `docs/recette/L01_recette_windows.md`.

**Aucun autre lot n'est lancé** (L05 inclus).
