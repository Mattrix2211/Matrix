@echo off
echo ================================================
echo Installation de l'application de gestion
echo ================================================
echo.

REM Verification de Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou n'est pas dans le PATH
    echo Veuillez installer Python 3.8 ou superieur
    pause
    exit /b 1
)

echo [1/6] Python detecte
python --version
echo.

REM Creation de l'environnement virtuel
echo [2/6] Creation de l'environnement virtuel...
if not exist venv (
    python -m venv venv
    echo Environnement virtuel cree avec succes
) else (
    echo Environnement virtuel deja existant
)
echo.

REM Activation de l'environnement virtuel
echo [3/6] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
echo.

REM Installation des dependances
echo [4/6] Installation des dependances Python...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERREUR: Echec de l'installation des dependances
    pause
    exit /b 1
)
echo Dependances installees avec succes
echo.

REM Application des migrations
echo [5/6] Application des migrations de base de donnees...
python manage.py migrate
if errorlevel 1 (
    echo ERREUR: Echec des migrations
    pause
    exit /b 1
)
echo Migrations appliquees avec succes
echo.

REM Collecte des fichiers statiques
echo [6/6] Collecte des fichiers statiques...
python manage.py collectstatic --noinput
echo.

echo ================================================
echo Installation terminee avec succes!
echo ================================================
echo.
echo Pour demarrer l'application, executez: start.bat
echo.
pause
