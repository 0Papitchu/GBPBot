@echo off
REM Script de démarrage rapide pour GBPBot (Windows)
REM Ce script démarre GBPBot en mode minimal avec les fonctionnalités essentielles

echo ============================================================
echo                 GBPBot - Démarrage Minimal
echo ============================================================
echo.

REM Vérifier si Python est installé
python -V >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.10+ et réessayer.
    pause
    exit /b 1
)

REM Vérifier si Node.js est installé (requis pour l'adaptateur Solana)
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Node.js 16+ et réessayer.
    pause
    exit /b 1
)

REM Vérifier si l'environnement virtuel existe
if not exist "venv_310\Scripts\activate.bat" (
    echo [INFO] Création de l'environnement virtuel...
    python -m venv venv_310
    if %errorlevel% neq 0 (
        echo [ERROR] Échec de la création de l'environnement virtuel.
        pause
        exit /b 1
    )
)

REM Activation de l'environnement virtuel
echo [INFO] Activation de l'environnement virtuel...
call venv_310\Scripts\activate.bat

REM Vérifier si le fichier .env existe
if not exist ".env" (
    echo [WARNING] Fichier .env non trouvé. Création d'un fichier par défaut...
    echo # Configuration GBPBot > .env
    echo SOLANA_RPC_URL=https://api.mainnet-beta.solana.com >> .env
    echo # Ajoutez votre clé privée Solana ci-dessous >> .env
    echo # SOLANA_PRIVATE_KEY=votre_clé_privée_ici >> .env
    echo. >> .env
    echo # Paramètres trading >> .env
    echo MAX_SLIPPAGE=1.0 >> .env
    echo GAS_PRIORITY=medium >> .env
    echo MAX_TRANSACTION_AMOUNT=0.1 >> .env
    echo ENABLE_SNIPING=true >> .env
    echo ENABLE_ARBITRAGE=false >> .env
    echo ENABLE_AUTO_MODE=false >> .env
    echo. >> .env
    echo # Sécurité >> .env
    echo REQUIRE_CONTRACT_ANALYSIS=true >> .env
    echo ENABLE_STOP_LOSS=true >> .env
    echo DEFAULT_STOP_LOSS_PERCENTAGE=5 >> .env
    
    echo [INFO] Fichier .env créé. Veuillez le configurer avant de continuer.
    echo.
    pause
    exit /b 0
)

REM Vérifier l'installation de l'adaptateur Solana Web3.js
if not exist "gbpbot\adapters\node_bridge\node_modules\@solana\web3.js" (
    echo [INFO] Installation de l'adaptateur Solana Web3.js...
    cd gbpbot\adapters\node_bridge
    call npm install
    cd ..\..\..
)

REM Installer les dépendances manquantes
pip install -r requirements.txt >nul 2>&1

REM Exécuter le test de connexion Solana
echo [INFO] Test de connexion à Solana...
python test_solana_web3_adapter.py
if %errorlevel% neq 0 (
    echo [ERROR] Le test de connexion à Solana a échoué.
    echo Veuillez vérifier votre connexion internet et réessayer.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                 GBPBot - Menu de Lancement
echo ============================================================
echo 1. Démarrer GBPBot en mode minimal (sniping uniquement)
echo 2. Démarrer GBPBot en mode complet
echo 3. Configuration
echo 4. Quitter
echo.

set /p choice=Entrez votre choix [1-4]: 

if "%choice%"=="1" (
    echo [INFO] Démarrage de GBPBot en mode minimal...
    python -m gbpbot --minimal --log-level info
) else if "%choice%"=="2" (
    echo [INFO] Démarrage de GBPBot en mode complet...
    python -m gbpbot --log-level info
) else if "%choice%"=="3" (
    echo [INFO] Lancement de la configuration...
    python scripts/setup_run_environment.py
) else if "%choice%"=="4" (
    echo [INFO] Sortie...
    exit /b 0
) else (
    echo [ERROR] Choix invalide.
    pause
    exit /b 1
)

pause 