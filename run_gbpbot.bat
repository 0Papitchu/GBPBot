@echo off
REM Script de démarrage pour GBPBot avec Python 3.11 et l'adaptateur Solana Web3.js

echo ============================================================
echo                 GBPBot - Démarrage
echo ============================================================
echo.

REM Vérifier si Python est installé
python -V >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.11+ et réessayer.
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

REM Vérifier l'installation de l'adaptateur Solana Web3.js
if not exist "gbpbot\adapters\node_bridge\node_modules\@solana\web3.js" (
    echo [INFO] Installation de l'adaptateur Solana Web3.js...
    
    REM Créer le répertoire si nécessaire
    if not exist "gbpbot\adapters\node_bridge" (
        mkdir "gbpbot\adapters\node_bridge"
    )
    
    cd gbpbot\adapters\node_bridge
    npm init -y
    npm install @solana/web3.js
    cd ..\..\..
)

echo.
echo ============================================================
echo                 GBPBot - Menu de Lancement
echo ============================================================
echo 1. Démarrer GBPBot en mode minimal (sniping uniquement)
echo 2. Démarrer GBPBot en mode complet
echo 3. Configurer l'environnement
echo 4. Quitter
echo.

set /p choice=Entrez votre choix [1-4]: 

if "%choice%"=="1" (
    echo [INFO] Démarrage de GBPBot en mode minimal...
    python gbpbot/start.py --minimal --log-level info
) else if "%choice%"=="2" (
    echo [INFO] Démarrage de GBPBot en mode complet...
    python gbpbot/start.py --log-level info
) else if "%choice%"=="3" (
    echo [INFO] Lancement de la configuration...
    python scripts/update_env.py
) else if "%choice%"=="4" (
    echo [INFO] Sortie...
    exit /b 0
) else (
    echo [ERROR] Choix invalide.
    pause
    exit /b 1
)

pause 