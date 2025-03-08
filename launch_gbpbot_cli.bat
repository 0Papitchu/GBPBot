@echo off
title GBPBot Launcher
color 0B

echo ============================================================
echo                    GBPBot - Lanceur
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

:: Afficher les options de lancement
echo Sélectionnez une option de lancement:
echo.
echo [1] Lancer GBPBot normalement
echo [2] Lancer GBPBot sans environnement virtuel
echo [3] Lancer GBPBot en mode debug
echo [4] Quitter
echo.

:: Lire le choix de l'utilisateur
set /p choice="Votre choix: "

:: Traiter le choix
if "%choice%"=="1" (
    echo.
    echo Lancement de GBPBot avec vérification de l'environnement...
    echo.
    python gbpbot_cli.py
) else if "%choice%"=="2" (
    echo.
    echo Lancement de GBPBot sans environnement virtuel...
    echo.
    python gbpbot_cli.py --no-venv
) else if "%choice%"=="3" (
    echo.
    echo Lancement de GBPBot en mode debug...
    echo.
    python gbpbot_cli.py --debug
) else if "%choice%"=="4" (
    echo.
    echo Au revoir!
    exit /b 0
) else (
    echo.
    echo [91mOption invalide.[0m Veuillez choisir une option entre 1 et 4.
    timeout /t 3 >nul
    exit /b 1
)

:: Vérifier si une erreur s'est produite
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [91mUne erreur s'est produite lors du lancement du GBPBot.[0m
    echo.
    echo Si Python n'est pas installé, veuillez l'installer depuis:
    echo https://www.python.org/downloads/
    echo.
    echo Pour toute aide supplémentaire, consultez la documentation.
)

pause 