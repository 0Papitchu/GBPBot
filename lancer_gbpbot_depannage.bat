@echo off
title GBPBot - Mode Dépannage
color 0E

echo.
echo ============================================================
echo         GBPBot - Lanceur Mode Dépannage
echo ============================================================
echo.
echo Ce lanceur utilise le script pont pour résoudre les problèmes
echo courants de lancement et de dépendances.
echo.
echo Utilisez ce mode si vous rencontrez des erreurs avec les 
echo méthodes de lancement standards.
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
echo Démarrage de GBPBot en mode dépannage...
echo.

if exist gbpbot_cli_bridge.py (
    python gbpbot_cli_bridge.py
) else (
    echo [91mFichier gbpbot_cli_bridge.py non trouvé![0m
    echo Récupération du script pont...
    echo.
    
    :: Créer un script minimaliste si le pont n'existe pas
    echo import os, sys, subprocess > gbpbot_cli_bridge_recovery.py
    echo print("\033[93mCréation d'un script pont minimaliste de récupération...\033[0m") >> gbpbot_cli_bridge_recovery.py
    echo print("Lancement du diagnostic de base...") >> gbpbot_cli_bridge_recovery.py
    echo print("\nVérification de la structure du projet:") >> gbpbot_cli_bridge_recovery.py
    echo print(f"- Répertoire courant: {os.getcwd()}") >> gbpbot_cli_bridge_recovery.py
    echo print(f"- Python: {sys.executable}") >> gbpbot_cli_bridge_recovery.py
    echo print(f"- Le dossier 'gbpbot' existe: {os.path.exists('gbpbot')}") >> gbpbot_cli_bridge_recovery.py
    echo print(f"- Fichier cli_interface.py existe: {os.path.exists('gbpbot/cli_interface.py')}") >> gbpbot_cli_bridge_recovery.py
    echo print(f"- Fichier cli.py existe: {os.path.exists('gbpbot/cli.py')}") >> gbpbot_cli_bridge_recovery.py
    echo print("\nInstallation des dépendances essentielles...") >> gbpbot_cli_bridge_recovery.py
    echo subprocess.call([sys.executable, "-m", "pip", "install", "rich", "click", "python-dotenv", "psutil"]) >> gbpbot_cli_bridge_recovery.py
    echo input("\nDiagnostic terminé. Appuyez sur Entrée pour quitter...") >> gbpbot_cli_bridge_recovery.py
    
    python gbpbot_cli_bridge_recovery.py
)

:: Vérifier si une erreur s'est produite
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [91mUne erreur s'est produite lors du lancement du GBPBot.[0m
    echo.
    echo Pour plus d'informations sur le dépannage, consultez:
    echo docs/TROUBLESHOOTING_LAUNCH.md
)

pause 