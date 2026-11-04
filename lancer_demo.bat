@echo off
REM Lance la démonstration fictive (base séparée, cette machine seulement) : http://127.0.0.1:8800/
if not exist venv (
    echo ERREUR: executez d'abord setup.bat
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
if not exist instance_test_marins\db.sqlite3 (
    echo Preparation des donnees fictives...
    python scripts\preparer_instance_test.py --reinitialiser
    if errorlevel 1 pause & exit /b 1
)
echo.
echo Ouvrez http://127.0.0.1:8800/  -  mot de passe de tous les comptes : pass
echo Pour repartir de donnees neuves : python scripts\preparer_instance_test.py --reinitialiser
echo.
python scripts\preparer_instance_test.py --servir
