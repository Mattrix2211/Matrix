# Recette Windows du lot L01 (verrou de la démonstration)

**Limite** : cette procédure n'a pas pu être exécutée par l'équipe de développement (environnement Linux). Elle est à dérouler par le PO ou un testeur sous Windows ; tant qu'elle n'est pas faite, le comportement de `lancer_demo.bat` sous Windows est « non vérifié ». La relecture statique du lanceur est en fin de document.

**Prérequis** : `setup.bat` exécuté une fois ; projet placé dans le profil de l'utilisateur (ex. `C:\Users\<nom>\Matrix`), pas dans un dossier partagé. Les commandes se tapent dans l'invite de commandes, à la racine du projet, environnement virtuel activé (`venv\Scripts\activate`).

| # | Action | Résultat attendu | OK ? |
|---|---|---|---|
| 1 | Supprimer le dossier `instance_test_marins` s'il existe, puis double-clic sur `lancer_demo.bat` | Message « Preparation des donnees fictives... », migrations, création des comptes ; le serveur démarre ; la fenêtre affiche l'adresse http://127.0.0.1:8800/ et la commande `--identifiants`, **aucun mot de passe** | |
| 2 | Dans une seconde fenêtre : `python scripts\preparer_instance_test.py --identifiants` | Deux lignes `comptes :` et `admin :` avec des mots de passe aléatoires, et une ligne `instance :` | |
| 3 | Dans `instance_test_marins`, vérifier la présence de `db.sqlite3`, `db.sqlite3.instance_demo` (contient `instance : …`) et `db.sqlite3.identifiants` ; propriétés du dernier fichier > Sécurité | Seuls votre compte (et SYSTEM/Administrateurs) y ont accès. Sinon : noter le constat, c'est le risque résiduel Windows | |
| 4 | Ouvrir http://127.0.0.1:8800/ ; se connecter avec `equipier_a` et le mot de passe de la ligne `comptes` | Connexion réussie | |
| 5 | Se connecter avec `equipier_a` / `pass`, puis `admin` / `admin` | Les deux connexions **échouent** | |
| 6 | Arrêter le serveur (Ctrl+C), relancer `lancer_demo.bat` | Message « Mise a jour de la base de demonstration existante... » ; les mots de passe de l'étape 2 sont **inchangés** | |
| 7 | Dans l'invite : `python manage.py seed_demo` | Message commençant par « Refus : seed_demo ne s'exécute que sur une base dédiée… » ; aucune donnée modifiée | |
| 8 | `python scripts\preparer_instance_test.py --reinitialiser`, puis `--identifiants` | Nouvelle base ; les deux mots de passe sont **différents** de l'étape 2 ; l'ancien fichier d'identifiants a disparu | |
| 9 | (Seulement si vous avez une base de démonstration créée **avant** ce lot, dont le fichier `db.sqlite3.instance_demo` est vide) `lancer_demo.bat` | Le lanceur **refuse** : « base préparée avant le verrou… » (aucune modification). Puis `python scripts\preparer_instance_test.py --mettre-a-jour --adopter-ancienne-base` : adoption réussie si tous les comptes sont d'origine, l'ancien mot de passe `pass` ne fonctionne plus, `--identifiants` donne les nouveaux. Sinon `--reinitialiser` | |
| 9b | Dans une copie jetable, ajouter à la base un compte `admin` avec un mot de passe de votre choix (admin Django ou `createsuperuser`), puis `--mettre-a-jour --adopter-ancienne-base` | Refus : l'adoption n'a pas lieu, le compte et le fichier voisin restent inchangés | |
| 10 | `set MATRIX_SQLITE_PATH=%CD%\instance_test_marins\db.sqlite3` puis `set DJANGO_DEBUG=1` puis `python manage.py verifier_instance` | « Aucun compte à mot de passe prévisible… » | |
| 11 | Même fenêtre : `set DJANGO_DEBUG=0` puis `set DJANGO_SECRET_KEY=une-cle-quelconque-de-test` puis `python manage.py check` | Erreur `matrix.E001` : la base de démonstration ne peut pas servir en production | |

**Compte rendu** : noter pour chaque ligne OK / KO / commentaire, la version de Windows et de Python (`python --version`).

## Relecture statique de `lancer_demo.bat` (sans exécution)

- Fichier ASCII pur (aucun accent) : pas de problème de page de code ; aucune parenthèse dans les `echo` placés dans des blocs `if` (cause classique d'erreur d'analyse).
- Enchaînement : vérifie `venv`, l'active, choisit `--mettre-a-jour` si `instance_test_marins\db.sqlite3` existe (même chemin que le script) sinon `--reinitialiser`, s'arrête avec `pause` si le script échoue (code de sortie 1, y compris le refus d'une base qui contient un compte non fictif), puis lance `--servir`.
- Seul le texte d'information a changé dans ce lot (plus de mot de passe affiché, renvoi vers `--identifiants`).
- Une ancienne base (fichier voisin vide) fait volontairement échouer le lanceur : `pause` affiche le message qui indique les deux options. Un fichier voisin vide créé à la main est un acte volontaire de l'opérateur ; il ne suffit ni à remplir ni à marquer une base, et l'adoption exige en plus que les comptes soient d'origine.
- Réserve : le fichier est enregistré avec des fins de ligne LF. `cmd.exe` les accepte pour ce script (aucune étiquette `goto`), mais un `.gitattributes` imposant CRLF aux `.bat` serait plus sûr (recommandation, non appliquée dans ce lot).
- Côté Python : le script transmet au processus fils les variables Windows nécessaires (`SYSTEMROOT`, `USERPROFILE`, `TEMP`…), ouvre le fichier d'identifiants avec `os.open(…, 0o600)` (droits POSIX sans effet sous Windows : le fichier hérite du dossier) et n'utilise que des API portables.
