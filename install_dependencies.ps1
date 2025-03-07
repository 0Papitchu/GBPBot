# Script PowerShell pour installer les dépendances de GBPBot
Write-Host "Installation des dépendances pour GBPBot..." -ForegroundColor Green

# Vérifier si Python est installé
try {
    $pythonVersion = python -V
    Write-Host "Python détecté: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python n'est pas installé ou n'est pas dans le PATH." -ForegroundColor Red
    Write-Host "Veuillez installer Python 3.10+ et réessayer." -ForegroundColor Red
    exit 1
}

# Vérifier si l'environnement virtuel existe
if (-not (Test-Path "venv_310")) {
    Write-Host "Création de l'environnement virtuel..." -ForegroundColor Yellow
    python -m venv venv_310
    if (-not $?) {
        Write-Host "Échec de la création de l'environnement virtuel." -ForegroundColor Red
        exit 1
    }
}

# Activer l'environnement virtuel
Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
& .\venv_310\Scripts\Activate.ps1

# Mettre à jour pip
Write-Host "Mise à jour de pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Installer les dépendances essentielles
Write-Host "Installation des dépendances essentielles..." -ForegroundColor Yellow
pip install aiohttp requests python-dotenv asyncio websockets

# Installer les dépendances pour l'IA
Write-Host "Installation des dépendances pour l'IA..." -ForegroundColor Yellow
pip install numpy pandas scikit-learn

# Installer les dépendances pour les interfaces
Write-Host "Installation des dépendances pour les interfaces..." -ForegroundColor Yellow
pip install fastapi uvicorn jinja2 python-telegram-bot

# Installer les dépendances pour la blockchain
Write-Host "Installation des dépendances pour la blockchain..." -ForegroundColor Yellow
pip install web3 eth-account

# Vérifier l'installation de Node.js
try {
    $nodeVersion = node -v
    Write-Host "Node.js détecté: $nodeVersion" -ForegroundColor Green
    
    # Vérifier l'installation de npm
    $npmVersion = npm -v
    Write-Host "npm détecté: $npmVersion" -ForegroundColor Green
    
    # Installer @solana/web3.js si nécessaire
    if (-not (Test-Path "gbpbot\adapters\node_bridge\node_modules\@solana\web3.js")) {
        Write-Host "Installation de @solana/web3.js..." -ForegroundColor Yellow
        
        # Créer le répertoire si nécessaire
        if (-not (Test-Path "gbpbot\adapters\node_bridge")) {
            New-Item -ItemType Directory -Path "gbpbot\adapters\node_bridge" -Force | Out-Null
        }
        
        # Se déplacer dans le répertoire
        Push-Location "gbpbot\adapters\node_bridge"
        
        # Initialiser le projet Node.js si nécessaire
        if (-not (Test-Path "package.json")) {
            npm init -y
        }
        
        # Installer @solana/web3.js
        npm install @solana/web3.js
        
        # Revenir au répertoire précédent
        Pop-Location
    } else {
        Write-Host "@solana/web3.js est déjà installé." -ForegroundColor Green
    }
} catch {
    Write-Host "Node.js n'est pas installé ou n'est pas dans le PATH." -ForegroundColor Red
    Write-Host "Veuillez installer Node.js 16+ et réessayer." -ForegroundColor Red
}

Write-Host "Installation des dépendances terminée!" -ForegroundColor Green
Write-Host "Vous pouvez maintenant démarrer GBPBot avec la commande:" -ForegroundColor Green
Write-Host "python -m gbpbot --minimal --log-level info" -ForegroundColor Cyan 