@echo off
title GBPBot - Lanceur
color 0B

echo ============================================================
echo                    GBPBot - Lanceur v1.0
echo ============================================================
echo.

:: Vérifier si Python est disponible
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [91mErreur: Python n'est pas installé ou n'est pas dans le PATH.[0m
    echo [93mVeuillez installer Python depuis https://www.python.org/downloads/[0m
    echo.
    echo Assurez-vous d'activer l'option "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

:: Vérifier si le lanceur existe
if not exist "%~dp0gbpbot_launcher.py" (
    echo [91mErreur: Fichier gbpbot_launcher.py introuvable.[0m
    echo [93mVeuillez vous assurer que ce fichier est présent dans le même répertoire.[0m
    echo.
    pause
    exit /b 1
)

:: Afficher les options de lancement
echo Sélectionnez une option de lancement:
echo.
echo [1] Lancer GBPBot via l'interface interactive
echo [2] Lancer GBPBot en mode CLI direct
echo [3] Lancer GBPBot en mode simulation
echo [4] Lancer le dashboard
echo [5] Quitter
echo.

:: Lire le choix de l'utilisateur
set /p choice="Votre choix: "

:: Traiter le choix
if "%choice%"=="1" (
    echo.
    echo Lancement de GBPBot en mode interactif...
    echo.
    python "%~dp0gbpbot_launcher.py"
) else if "%choice%"=="2" (
    echo.
    echo Lancement de GBPBot en mode CLI...
    echo.
    python "%~dp0gbpbot_launcher.py" --mode cli
) else if "%choice%"=="3" (
    echo.
    echo Lancement de GBPBot en mode simulation...
    echo.
    python "%~dp0gbpbot_launcher.py" --mode simulation
) else if "%choice%"=="4" (
    echo.
    echo Lancement du dashboard GBPBot...
    echo.
    python "%~dp0gbpbot_launcher.py" --mode dashboard
) else if "%choice%"=="5" (
    echo.
    echo Au revoir!
    exit /b 0
) else (
    echo.
    echo [91mOption invalide.[0m Veuillez choisir une option entre 1 et 5.
    timeout /t 3 >nul
    exit /b 1
)

:: Vérifier si une erreur s'est produite
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [91mUne erreur s'est produite lors du lancement du GBPBot.[0m
    echo.
    echo Si vous rencontrez des problèmes, essayez les solutions suivantes:
    echo 1. Vérifiez que Python 3.8+ est installé correctement
    echo 2. Vérifiez que toutes les dépendances sont installées
    echo 3. Consultez les logs dans le dossier ./logs
    echo.
)

pause 