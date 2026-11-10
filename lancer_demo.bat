@echo off
REM Lance la demonstration fictive (base separee, cette machine seulement) : http://127.0.0.1:8800/
REM A chaque lancement : migrations manquantes appliquees, donnees completees ; rien n'est supprime.
if not exist venv (
    echo ERREUR: executez d'abord setup.bat
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
if exist instance_test_marins\db.sqlite3 (
    echo Mise a jour de la base de demonstration existante...
    python scripts\preparer_instance_test.py --mettre-a-jour
) else (
    echo Preparation des donnees fictives...
    python scripts\preparer_instance_test.py --reinitialiser
)
if errorlevel 1 (
    pause
    exit /b 1
)
echo.
echo Ouvrez http://127.0.0.1:8800/
echo Mots de passe des comptes (generes, non affiches ici) : python scripts\preparer_instance_test.py --identifiants
echo Pour repartir de donnees neuves : python scripts\preparer_instance_test.py --reinitialiser
echo.
python scripts\preparer_instance_test.py --servir
