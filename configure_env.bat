@echo off
setlocal enabledelayedexpansion

echo === Gestionnaire des fichiers d'environnement GBPBot ===
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Erreur: Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.7 ou supérieur.
    pause
    exit /b 1
)

REM Vérifier si le script existe
if not exist "scripts\setup_env.py" (
    echo Erreur: Le script setup_env.py n'a pas été trouvé.
    echo Assurez-vous d'exécuter ce script depuis la racine du projet GBPBot.
    pause
    exit /b 1
)

:menu
cls
echo === Gestionnaire des fichiers d'environnement GBPBot ===
echo.
echo 1. Créer une sauvegarde du fichier .env actuel
echo 2. Initialiser .env à partir de .env.local
echo 3. Valider le fichier .env
echo 4. Quitter
echo.

set /p choice=Votre choix (1-4): 

if "%choice%"=="1" (
    echo.
    echo Création d'une sauvegarde...
    python scripts\setup_env.py 1
    echo.
    pause
    goto menu
)

if "%choice%"=="2" (
    echo.
    echo Initialisation du fichier .env...
    python scripts\setup_env.py 2
    echo.
    pause
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo Validation du fichier .env...
    python scripts\setup_env.py 3
    echo.
    pause
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo Au revoir!
    exit /b 0
)

echo.
echo Choix invalide. Veuillez réessayer.
pause
goto menu 