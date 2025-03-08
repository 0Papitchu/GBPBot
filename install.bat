@echo off
:: =================================================================
:: GBPBot - Script d'Installation Windows
:: =================================================================
:: Ce script installe GBPBot et configure l'environnement nécessaire pour Windows
:: =================================================================

setlocal enabledelayedexpansion

:: Configuration des couleurs (pour Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

:: Répertoire de base
set "BASE_DIR=%cd%"
set "LOG_FILE=%BASE_DIR%\installation.log"

:: Fonction pour l'affichage des logs
:log
set "level=%~1"
set "message=%~2"
set "color=%NC%"

if "%level%"=="INFO" set "color=%GREEN%"
if "%level%"=="WARNING" set "color=%YELLOW%"
if "%level%"=="ERROR" set "color=%RED%"
if "%level%"=="STEP" set "color=%BLUE%"

:: Affichage dans la console
echo %color%[%level%] %message%%NC%

:: Enregistrement dans le fichier de log
echo [%date% %time%] [%level%] %message% >> "%LOG_FILE%"
goto :EOF

:: Fonction pour vérifier la réussite d'une commande
:check_success
if %errorlevel% equ 0 (
    call :log "INFO" "✅ Succès: %~1"
    exit /b 0
) else (
    call :log "ERROR" "❌ Échec: %~1"
    exit /b 1
)

:: Initialisation du fichier de log
echo # Log d'installation de GBPBot - %date% %time% > "%LOG_FILE%"

:: Vérifier les droits d'administrateur
net session >nul 2>&1
if %errorlevel% neq 0 (
    call :log "WARNING" "Ce script nécessite des droits d'administrateur pour installer certaines dépendances."
    call :log "WARNING" "Veuillez relancer ce script en tant qu'administrateur."
    
    echo.
    echo Appuyez sur une touche pour continuer quand même...
    pause >nul
)

:: Affichage du header
echo ============================================================
echo             GBPBot - Script d'Installation Windows
echo ============================================================
echo.

:: Vérification de l'existence de Chocolatey
call :log "STEP" "Vérification des outils nécessaires..."
where choco >nul 2>&1
if %errorlevel% neq 0 (
    call :log "WARNING" "Chocolatey n'est pas installé. Installation de Chocolatey..."
    
    :: Installation de Chocolatey
    @powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
    if %errorlevel% neq 0 (
        call :log "ERROR" "Échec de l'installation de Chocolatey. Veuillez l'installer manuellement depuis https://chocolatey.org/install"
        goto :error
    )
    
    call :log "INFO" "Chocolatey a été installé avec succès."
) else (
    call :log "INFO" "Chocolatey est déjà installé."
)

:: Installation des dépendances avec Chocolatey
call :log "STEP" "Installation des dépendances nécessaires..."

:: Installation de Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    call :log "INFO" "Installation de Python..."
    choco install -y python --version=3.11.0
    call :check_success "Installation de Python"
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    call :log "INFO" "Python est déjà installé: %PYTHON_VERSION%"
)

:: Installation de Git
where git >nul 2>&1
if %errorlevel% neq 0 (
    call :log "INFO" "Installation de Git..."
    choco install -y git
    call :check_success "Installation de Git"
) else (
    for /f "tokens=*" %%i in ('git --version') do set "GIT_VERSION=%%i"
    call :log "INFO" "Git est déjà installé: %GIT_VERSION%"
)

:: Installation de Node.js et npm
where node >nul 2>&1
if %errorlevel% neq 0 (
    call :log "INFO" "Installation de Node.js et npm..."
    choco install -y nodejs
    call :check_success "Installation de Node.js et npm"
) else (
    for /f "tokens=*" %%i in ('node --version') do set "NODE_VERSION=%%i"
    call :log "INFO" "Node.js est déjà installé: %NODE_VERSION%"
)

:: Installation de Curl
where curl >nul 2>&1
if %errorlevel% neq 0 (
    call :log "INFO" "Installation de Curl..."
    choco install -y curl
    call :check_success "Installation de Curl"
) else (
    call :log "INFO" "Curl est déjà installé."
)

:: Installation de wget
where wget >nul 2>&1
if %errorlevel% neq 0 (
    call :log "INFO" "Installation de wget..."
    choco install -y wget
    call :check_success "Installation de wget"
) else (
    call :log "INFO" "wget est déjà installé."
)

:: Refresh du PATH
call :log "INFO" "Mise à jour du PATH..."
:: SetX PATH "%PATH%;%APPDATA%\Python\Python311\Scripts"
:: call :check_success "Mise à jour du PATH"

:: Création de l'environnement virtuel Python
call :log "STEP" "Configuration de l'environnement Python..."

:: Vérification de l'existence de l'environnement virtuel
if not exist "venv" (
    call :log "INFO" "Création d'un environnement virtuel Python..."
    python -m venv venv
    call :check_success "Création de l'environnement virtuel"
) else (
    call :log "INFO" "L'environnement virtuel existe déjà."
)

:: Activation de l'environnement virtuel
call :log "INFO" "Activation de l'environnement virtuel..."
call venv\Scripts\activate.bat
call :check_success "Activation de l'environnement virtuel"

:: Mise à jour de pip
call :log "INFO" "Mise à jour de pip..."
python -m pip install --upgrade pip
call :check_success "Mise à jour de pip"

:: Vérification de l'existence du fichier requirements.txt
if not exist "requirements.txt" (
    call :log "WARNING" "Le fichier requirements.txt n'existe pas. Création d'un fichier par défaut..."
    
    :: Création d'un fichier requirements.txt minimal
    (
        echo # GBPBot - Dépendances Python
        echo # Générées par le script d'installation
        echo.
        echo # Dépendances de base
        echo python-dotenv==1.0.0
        echo web3==6.6.1
        echo requests==2.31.0
        echo websockets==11.0.3
        echo aiohttp==3.8.5
        echo rich==13.5.2
        echo click==8.1.7
        echo pydantic==2.3.0
        echo loguru==0.7.2
        echo.
        echo # Dépendances Solana
        echo solana==0.30.2
        echo anchorpy==0.17.0
        echo.
        echo # Dépendances AVAX
        echo snowtrace==0.1.4
        echo.
        echo # Dépendances pour l'IA
        echo numpy==1.25.2
        echo pandas==2.1.0
        echo scikit-learn==1.3.0
        echo joblib==1.3.2
        echo.
        echo # Dépendances pour l'interface utilisateur
        echo PyInquirer==1.0.3
        echo prompt_toolkit==3.0.36
        echo Flask==2.3.3
        echo Flask-SocketIO==5.3.5
    ) > requirements.txt
    
    call :log "INFO" "Fichier requirements.txt créé avec succès."
)

:: Installation des dépendances Python
call :log "INFO" "Installation des dépendances Python..."
pip install -r requirements.txt
call :check_success "Installation des dépendances Python"

:: Configuration de l'adaptateur Solana Web3.js
call :log "STEP" "Configuration de l'adaptateur Solana Web3.js..."

:: Vérification de l'existence de Node.js et npm
where node >nul 2>&1 && where npm >nul 2>&1
if %errorlevel% neq 0 (
    call :log "WARNING" "Node.js ou npm n'est pas installé. L'adaptateur Solana Web3.js ne sera pas configuré."
    goto :skip_solana_adapter
)

:: Création du répertoire de l'adaptateur
if not exist "gbpbot\adapters\node_bridge" (
    call :log "INFO" "Création du répertoire de l'adaptateur..."
    mkdir "gbpbot\adapters\node_bridge" 2>nul
    call :check_success "Création du répertoire de l'adaptateur"
)

:: Initialisation du projet Node.js
call :log "INFO" "Initialisation du projet Node.js..."
pushd "gbpbot\adapters\node_bridge"
if not exist "package.json" (
    npm init -y >nul
    call :check_success "Initialisation du projet Node.js"
) else (
    call :log "INFO" "Le projet Node.js est déjà initialisé."
)

:: Installation des dépendances Node.js
call :log "INFO" "Installation de @solana/web3.js..."
npm install @solana/web3.js --save
call :check_success "Installation de @solana/web3.js"

:: Retour au répertoire de base
popd

:skip_solana_adapter

:: Configuration du fichier .env
call :log "STEP" "Configuration du fichier .env..."

:: Vérification de l'existence du fichier .env
if exist ".env" (
    call :log "INFO" "Le fichier .env existe déjà."
    
    :: Demander s'il faut remplacer le fichier
    set /p "replace_env=Voulez-vous remplacer le fichier .env existant? (o/n): "
    if /i not "%replace_env%"=="o" (
        call :log "INFO" "Conservation du fichier .env existant."
        goto :skip_env_file
    )
)

:: Création du fichier .env
call :log "INFO" "Création du fichier .env..."

(
    echo # Configuration GBPBot
    echo # Généré par le script d'installation
    echo.
    echo # Configuration générale
    echo DEBUG=false
    echo LOG_LEVEL=info
    echo ENVIRONMENT=production
    echo.
    echo # Configuration Solana
    echo SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
    echo # SOLANA_PRIVATE_KEY=votre_clé_privée_ici
    echo.
    echo # Configuration AVAX
    echo AVAX_RPC_URL=https://api.avax.network/ext/bc/C/rpc
    echo # AVAX_PRIVATE_KEY=votre_clé_privée_ici
    echo.
    echo # Configuration Sonic
    echo SONIC_RPC_URL=https://rpc.sonic.fantom.network/
    echo # SONIC_PRIVATE_KEY=votre_clé_privée_ici
    echo.
    echo # Paramètres trading
    echo MAX_SLIPPAGE=1.0
    echo GAS_PRIORITY=medium
    echo MAX_TRANSACTION_AMOUNT=0.1
    echo ENABLE_SNIPING=true
    echo ENABLE_ARBITRAGE=false
    echo ENABLE_AUTO_MODE=false
    echo.
    echo # Sécurité
    echo REQUIRE_CONTRACT_ANALYSIS=true
    echo ENABLE_STOP_LOSS=true
    echo DEFAULT_STOP_LOSS_PERCENTAGE=5
    echo.
    echo # Interface utilisateur
    echo ENABLE_WEB_DASHBOARD=true
    echo WEB_DASHBOARD_PORT=8080
    echo.
    echo # IA et Machine Learning
    echo ENABLE_AI_ANALYSIS=true
    echo USE_LOCAL_MODELS=true
    echo USE_OPENAI_API=false
    echo # OPENAI_API_KEY=votre_clé_api_ici
    echo.
    echo # Configuration avancée
    echo MEMPOOL_MONITORING=true
    echo MEV_PROTECTION=true
    echo ENABLE_ANTI_RUGPULL=true
) > .env

call :check_success "Création du fichier .env"
call :log "INFO" "⚠️ N'oubliez pas de modifier le fichier .env avec vos clés privées et configurations spécifiques."

:skip_env_file

:: Création des scripts de démarrage
call :log "STEP" "Création des scripts de démarrage..."

:: Script de démarrage Windows
call :log "INFO" "Création du script de démarrage pour Windows..."
(
    echo @echo off
    echo REM Script de démarrage pour GBPBot ^(Windows^)
    echo.
    echo REM Vérifier si l'environnement virtuel existe
    echo if not exist "venv\Scripts\activate.bat" ^(
    echo     echo L'environnement virtuel n'existe pas. Exécutez d'abord install.bat.
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo REM Activer l'environnement virtuel
    echo call venv\Scripts\activate.bat
    echo.
    echo REM Démarrer GBPBot
    echo python gbpbot/start.py %%*
) > start_gbpbot.bat

call :check_success "Création du script de démarrage pour Windows"

:: Vérification de la structure du projet
call :log "STEP" "Vérification de la structure du projet..."

:: Création des répertoires de base s'ils n'existent pas
if not exist "gbpbot" (
    call :log "INFO" "Création du répertoire principal..."
    mkdir "gbpbot" 2>nul
    call :check_success "Création du répertoire principal"
)

if not exist "gbpbot\start.py" (
    call :log "WARNING" "Le fichier de démarrage start.py n'existe pas. Création d'un fichier minimal..."
    
    (
        echo #!/usr/bin/env python
        echo # -*- coding: utf-8 -*-
        echo """
        echo GBPBot - Point d'entrée principal
        echo """
        echo.
        echo import sys
        echo import os
        echo import argparse
        echo from pathlib import Path
        echo.
        echo # Ajouter le répertoire parent au chemin d'importation
        echo sys.path.insert^(0, str^(Path^(__file__^).parent.parent^)^)
        echo.
        echo def main^(^):
        echo     """Point d'entrée principal du GBPBot"""
        echo     parser = argparse.ArgumentParser^(description="GBPBot - Trading Bot pour Solana, AVAX et Sonic"^)
        echo     parser.add_argument^("--config", "-c", help="Chemin vers le fichier de configuration"^)
        echo     parser.add_argument^("--debug", "-d", action="store_true", help="Activer le mode debug"^)
        echo     parser.add_argument^("--version", "-v", action="store_true", help="Afficher la version"^)
        echo     args = parser.parse_args^(^)
        echo.
        echo     if args.version:
        echo         print^("GBPBot v0.1.0"^)
        echo         return 0
        echo.
        echo     print^("============================================================"^)
        echo     print^("                    GBPBot - Menu Principal"^)
        echo     print^("============================================================"^)
        echo     print^("Bienvenue dans GBPBot, votre assistant de trading sur Avalanche!"^)
        echo     print^(^)
        echo     print^("Veuillez choisir une option:"^)
        echo     print^("1. Démarrer le Bot"^)
        echo     print^("2. Configurer les paramètres"^)
        echo     print^("3. Afficher la configuration actuelle"^)
        echo     print^("4. Statistiques et Logs"^)
        echo     print^("5. Afficher les Modules Disponibles"^)
        echo     print^("6. Quitter"^)
        echo     print^(^)
        echo.
        echo     # Placeholder pour l'interface utilisateur
        echo     choice = input^("Votre choix: "^)
        echo     print^(f"Option {choice} sélectionnée. Cette fonctionnalité n'est pas encore implémentée."^)
        echo.
        echo     return 0
        echo.
        echo if __name__ == "__main__":
        echo     sys.exit^(main^(^)^)
    ) > "gbpbot\start.py"
    
    call :check_success "Création du fichier de démarrage minimal"
)

:: Finalisation
call :log "STEP" "Installation terminée!"
call :log "INFO" "GBPBot a été installé avec succès."
call :log "INFO" "Pour démarrer GBPBot, exécutez: start_gbpbot.bat"
call :log "INFO" "N'oubliez pas de configurer vos clés privées dans le fichier .env avant de commencer."
call :log "INFO" "Le log d'installation est disponible dans: %LOG_FILE%"

echo.
echo ============================================================
echo            Installation terminée!
echo ============================================================
echo.
echo Appuyez sur une touche pour quitter...
pause >nul
exit /b 0

:error
call :log "ERROR" "Une erreur s'est produite pendant l'installation."
call :log "INFO" "Consultez le fichier log pour plus de détails: %LOG_FILE%"
echo.
echo Appuyez sur une touche pour quitter...
pause >nul
exit /b 1 