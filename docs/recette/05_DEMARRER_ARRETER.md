# Démarrer et arrêter la démonstration

## Windows (recommandé)
1. Une seule fois : `setup.bat`
2. Démarrer : double-clic sur `lancer_demo.bat` (ou, dans PowerShell, à la racine du projet : `.\lancer_demo.bat`)
   - base absente → création et génération des données fictives ;
   - base présente → migrations manquantes appliquées et données complétées, **rien n'est supprimé**.
3. Ouvrir http://127.0.0.1:8800/
4. Arrêter : dans la fenêtre du serveur, **Ctrl+C** (ou fermer la fenêtre).

## Commandes équivalentes (PowerShell, venv activé)
```
python scripts\preparer_instance_test.py --mettre-a-jour   # migrations + compléments, sans rien supprimer
python scripts\preparer_instance_test.py --servir          # lance http://127.0.0.1:8800/
python scripts\preparer_instance_test.py --verifier        # contrôle sans rien écrire que la base visée est bien celle de démonstration
```
Repartir de zéro (efface **uniquement** la base de démonstration `instance_test_marins\db.sqlite3`) :
```
python scripts\preparer_instance_test.py --reinitialiser
```
La base de développement (`db.sqlite3`) n'est jamais touchée : le script refuse tout autre fichier.
