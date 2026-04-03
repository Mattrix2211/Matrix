@echo off
echo ================================================
echo Reinitialisation du compte administrateur
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

echo Ce script va creer ou reinitialiser le compte administrateur.
echo.
echo Identifiants par defaut:
echo - Nom d'utilisateur: admin
echo - Mot de passe: adminpass
echo - Email: admin@example.com
echo.
set /p confirm="Voulez-vous continuer ? (O/N): "
if /i not "%confirm%"=="O" (
    echo Operation annulee
    pause
    exit /b 0
)

echo.
echo Creation/Reinitialisation du compte administrateur...
python scripts\create_superuser.py

echo.
echo ================================================
echo Terminé!
echo ================================================
echo.
echo Vous pouvez maintenant vous connecter avec:
echo - Utilisateur: admin
echo - Mot de passe: adminpass
echo.
pause
