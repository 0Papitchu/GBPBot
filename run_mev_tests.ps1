# Script PowerShell pour exécuter les tests du module MEV/Frontrunning
# Usage: .\run_mev_tests.ps1 [test]
# Où [test] peut être: all, mempool, analysis, gas (par défaut: all)

param (
    [string]$test = "all",
    [string]$configPath = "config/testnet_config.json"
)

# Configuration de l'environnement
$env:PYTHONPATH = $PWD.Path
$env:GBPBOT_TEST_MODE = "1"
$env:GBPBOT_LOG_LEVEL = "INFO"

# Vérifier que le répertoire de configuration existe
$configDir = ".\config"
if (-not (Test-Path $configDir)) {
    Write-Host "Création du répertoire de configuration..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

# Création d'un fichier de configuration de test si nécessaire
if (-not (Test-Path $configPath)) {
    Write-Host "Création du fichier de configuration de test: $configPath" -ForegroundColor Yellow
    
    @"
{
    "blockchain": "avax",
    "testnet": true,
    "min_profit_threshold": 0.002,
    "min_sandwich_profit_threshold": 0.005,
    "max_gas_price_gwei": 100.0,
    "gas_boost_percentage": 10.0,
    "monitoring_duration_seconds": 30,
    "simulation_only": true,
    "pairs_to_monitor": [
        {"token0": "WAVAX", "token1": "USDC"},
        {"token0": "WAVAX", "token1": "USDT"},
        {"token0": "JOE", "token1": "USDC"}
    ]
}
"@ | Set-Content -Path $configPath
}

# Vérifier si le test spécifié est valide
$validTests = @("all", "mempool", "analysis", "gas")
if ($validTests -notcontains $test) {
    Write-Host "Test invalide: $test" -ForegroundColor Red
    Write-Host "Tests disponibles: $($validTests -join ', ')" -ForegroundColor Yellow
    exit 1
}

# Afficher les informations sur le test à exécuter
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "Exécution des tests MEV/Frontrunning: $test" -ForegroundColor Cyan
Write-Host "Configuration: $configPath" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Démarrer le test
try {
    Write-Host "Démarrage des tests..." -ForegroundColor Green
    python -m gbpbot.tests.real_environment_mev_test --config=$configPath --test=$test
} catch {
    Write-Host "Erreur lors de l'exécution des tests: $_" -ForegroundColor Red
}

Write-Host "Tests terminés." -ForegroundColor Green 