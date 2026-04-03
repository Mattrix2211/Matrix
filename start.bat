@echo off
echo ================================================
echo Demarrage de l'application de gestion
echo ================================================
echo.

REM Verification de l'environnement virtuel
if not exist venv (
    echo ERREUR: Environnement virtuel non trouve
    echo Veuillez d'abord executer setup.bat pour installer l'application
    pause
    exit /b 1
)

REM Activation de l'environnement virtuel
echo [1/4] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
echo.

REM Verification des migrations
echo [2/4] Verification des migrations...
python manage.py migrate --check >nul 2>&1
if errorlevel 1 (
    echo Des migrations sont en attente. Application des migrations...
    python manage.py migrate
)
echo.

REM Demarrage de Celery en arriere-plan (si Redis est disponible)
echo [3/4] Demarrage des services...
start /B celery -A matrix worker -l info --pool=solo >celery.log 2>&1
start /B celery -A matrix beat -l info >celery-beat.log 2>&1
echo Services Celery demarres
echo.

REM Demarrage du serveur Django
echo [4/4] Demarrage du serveur Django...
echo.
echo ================================================
echo L'application est accessible a l'adresse:
echo http://127.0.0.1:8000
echo ================================================
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.

python manage.py runserver
