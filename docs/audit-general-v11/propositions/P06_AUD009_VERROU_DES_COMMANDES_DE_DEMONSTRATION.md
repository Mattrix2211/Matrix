# P06 — AUD-009 : verrou des commandes de démonstration (proposition technique détaillée)

**Statut : proposition ; aucune modification applicative sans l'autorisation du PO.** Criticité **P0** (sécurité). Défaut **préexistant** : présent à l'identique sur `main` (`6ef16ad`) et sur la V1.1 (`1c37f22`).

## 1. Cause racine

1. Les quatre commandes `seed_demo`, `seed_demo_mer_quai`, `seed_demo_dense`, `seed_demo_metier` (`matrix/core/management/commands/`) n'ont **aucune condition préalable** dans `handle()` : ni lecture de `DEBUG`, ni de l'état de la base, ni de variable d'activation.
2. Les mots de passe sont des constantes du code (`MOT_DE_PASSE = "pass"`, compte `admin` avec `admin` : `seed_demo.py` en tête de fichier ; `seed_demo_dense.py:146`, `seed_demo_mer_quai.py:53`), appliquées à la création de chaque compte.
3. Le projet n'a **aucune notion de « nature de l'instance »** (démonstration, essai, production) : `matrix/settings.py` ne connaît que `DEBUG` et la clé secrète.
4. La seule protection réelle est **dans un script, hors du chemin obligatoire** : `scripts/preparer_instance_test.py` (base SQLite dédiée, `DEBUG` actif, hôtes locaux, courtier isolé, refus de lien symbolique). `python manage.py seed_demo` l'ignore.

## 2. Conséquences concrètes (mesurées ou lues dans le code)

| Situation | Effet |
|---|---|
| Exécution sur une base de production | création de 61 comptes à mot de passe connu (60 en « pass », plus le compte de flotte `admin`, superutilisateur, en « admin »), des tâches, annonces, listes et échanges fictifs mêlés aux vrais |
| Compte existant portant un nom de la démonstration | le mot de passe n'est **pas** modifié (`set_password` seulement à la création), mais son **profil est écrasé** : rôle, bâtiment, service, secteur, section, équipage, fonction (`_utilisateur`, après `get_or_create`). Un compte `admin` préexistant recevrait ainsi le rôle de compte de flotte sans changer de mot de passe |
| Base de démonstration promue en production par oubli | les 60 comptes restent actifs ; rien ne signale l'origine de la base |
| Noms de bâtiments | 4 sur 5 sont des noms réels (AUD-024) : confusion possible avec de vraies données |

## 3. Correction recommandée (par couches, de la plus sûre à la plus simple)

1. **Fonction commune de garde** (nouveau module `matrix/core/instance_demo.py`) appelée en première ligne de chaque `handle()`. Elle **refuse** (`CommandError`, message en français) sauf si **toutes** les conditions suivantes sont vraies : `DEBUG` actif ; variable d'environnement explicite `MATRIX_INSTANCE_DEMO=1` ; moteur SQLite ; la base est vide **ou** porte déjà le marqueur de démonstration ; aucun compte non fictif n'existe (aucun utilisateur actif hors liste connue des noms de la démonstration).
2. **Marqueur persistant** : une ligne en base (modèle minimal `InstanceDemo(date, commande)`) écrite au premier remplissage. Un **contrôle système de niveau erreur** (`matrix/core/checks.py`) refuse de démarrer en production (`DEBUG` inactif) si le marqueur existe : une base de démonstration ne peut pas devenir une base de production.
3. **Pas d'écrasement des comptes existants** : si le nom existe déjà, la commande s'arrête avec la liste des collisions (jamais de modification de profil).
4. **Mots de passe** : conserver `pass` seulement derrière le garde ; le compte de flotte reçoit un mot de passe aléatoire affiché une fois, sauf option explicite `--mot-de-passe-demo`.
5. **Chemin officiel** : `lancer_demo.bat` et `scripts/preparer_instance_test.py` posent `MATRIX_INSTANCE_DEMO=1` ; le `README` ne présente plus que ce chemin.
6. **Commande de contrôle en lecture seule** `verifier_instance` : liste les comptes dont le mot de passe vaut `pass` ou `admin` et la présence du marqueur ; utilisable par l'exploitant avant toute mise en production.

## 4. Risques de régression

| Risque | Mesure |
|---|---|
| 21 fichiers de test appellent `seed_demo*` sous `DEBUG` | le garde doit reconnaître le contexte de test (réglage `TESTING` ou variable posée par le socle de test) ; sinon 21 fichiers échouent |
| Les chaînes d'essai du PO (`lancer_demo.bat`) cessent de fonctionner | mise à jour du script dans le même changement |
| Le marqueur bloque un poste de démonstration légitime en mode production | le marqueur n'interdit que `DEBUG` inactif ; le poste de démo reste en `DEBUG` actif |
| Collisions de noms avec des comptes de développeurs | message explicite, option `--force-collisions` **non fournie** |

## 5. Tests de non-régression à créer

1. Chaque commande `seed_demo*` lève `CommandError` avec `DEBUG` inactif.
2. Elle lève `CommandError` sans `MATRIX_INSTANCE_DEMO=1`, même en `DEBUG`.
3. Elle lève `CommandError` sur un moteur PostgreSQL.
4. Elle lève `CommandError` si un compte non fictif existe (base « de vraie vie »), sans créer aucun compte.
5. Elle réussit sur base vide avec les trois conditions, écrit le marqueur, et reste rejouable.
6. Le contrôle système échoue (erreur) quand le marqueur existe et `DEBUG` est inactif.
7. Aucun compte existant n'est modifié par la commande (collision de nom) : profil identique avant et après.
8. `verifier_instance` liste exactement les comptes à mot de passe connu et ne modifie rien.
9. Le chemin `scripts/preparer_instance_test.py` fonctionne de bout en bout avec le garde.
10. La suite complète reste verte sur SQLite et sur PostgreSQL.

## 6. Conséquences sur les données existantes

- **Aucune migration destructive** ; une table d'une ligne est ajoutée (migration additive, sans valeur par défaut problématique).
- **Instances de démonstration déjà créées** (poste du PO, recette) : elles n'ont pas de marqueur. Une commande `marquer_instance_demo` (explicite, idempotente, réservée au `DEBUG` actif) l'écrit ; sans elle, le garde refuse une nouvelle exécution sur une base non vide hors marqueur, ce qui est le comportement voulu.
- **Instance réelle déjà polluée** : `verifier_instance` la détecte ; la remédiation (désactiver les comptes, réinitialiser les mots de passe, purger les objets fictifs) reste **manuelle et validée par l'exploitant**, jamais automatique.
- **Bases de démonstration existantes** : conservées telles quelles.
