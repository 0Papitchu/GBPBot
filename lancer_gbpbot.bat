@echo off
title GBPBot - Lanceur
color 0B

echo.
echo ============================================================
echo                   GBPBot - Lanceur
echo ============================================================
echo.

:: Vérifier si Python est installé
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

:: Vérifier la version de Python (minimum 3.7)
python -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [91mVersion de Python insuffisante.[0m
    echo Vous utilisez une version de Python inférieure à 3.7.
    echo Veuillez installer Python 3.7 ou supérieur depuis:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Lancer le script pont GBPBot
echo Démarrage de GBPBot...
echo.

if exist gbpbot_cli_bridge.py (
    python gbpbot_cli_bridge.py
) else (
    echo [91mFichier gbpbot_cli_bridge.py non trouvé![0m
    echo Essai avec gbpbot_cli.py...
    echo.
    
    if exist gbpbot_cli.py (
        python gbpbot_cli.py
    ) else (
        echo [91mFichier gbpbot_cli.py non trouvé![0m
        echo Assurez-vous d'être dans le bon répertoire.
        echo.
    )
)

:: Vérifier si une erreur s'est produite
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [91mUne erreur s'est produite lors du lancement du GBPBot.[0m
    echo.
    echo Pour toute aide supplémentaire, consultez la documentation.
)

pause 