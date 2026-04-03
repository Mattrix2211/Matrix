@echo off
echo ================================================
echo Creation d'un nouveau superutilisateur
echo ================================================
echo.

REM Verification de l'environnement virtuel
if not exist venv (
    echo ERREUR: Environnement virtuel non trouve
    echo Veuillez d'abord executer setup.bat
    pause
    exit /b 1
)

REM Activation de l'environnement virtuel
call venv\Scripts\activate.bat

echo Ce script va vous permettre de creer un nouveau compte administrateur.
echo Vous devrez fournir:
echo - Un nom d'utilisateur
echo - Une adresse email
echo - Un mot de passe (tape 2 fois pour confirmation)
echo.

python manage.py createsuperuser

echo.
echo ================================================
echo Compte cree avec succes!
echo ================================================
echo.
pause
