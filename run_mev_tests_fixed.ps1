# Script PowerShell pour exécuter les tests du module MEV/Frontrunning avec correctifs
# Usage: .\run_mev_tests_fixed.ps1 [test]
# Où [test] peut être: all, mempool, analysis, gas (par défaut: all)

param (
    [string]$test = "all",
    [string]$configPath = "config/testnet_config.json",
    [switch]$skipCorrections = $false
)

# Fonction pour afficher des messages en couleur
function Write-ColorMessage {
    param (
        [string]$Message,
        [string]$ForegroundColor = "White"
    )
    Write-Host $Message -ForegroundColor $ForegroundColor
}

# Configuration de l'environnement
$env:PYTHONPATH = $PWD.Path
$env:GBPBOT_TEST_MODE = "1"
$env:GBPBOT_LOG_LEVEL = "INFO"
$env:PYTHONIOENCODING = "UTF-8"
$env:PYTHONUNBUFFERED = "1"

# Appliquer les corrections avant d'exécuter les tests
if (-not $skipCorrections) {
    Write-ColorMessage "Application des corrections pour les tests MEV..." "Yellow"
    
    # Vérifier si les scripts de correction existent
    $fixCircular = ".\fix_circular_import.py"
    $fixRPC = ".\fix_rpc_manager.py"
    
    if (-not (Test-Path $fixCircular)) {
        Write-ColorMessage "Script de correction d'importation cyclique non trouvé: $fixCircular" "Red"
        return
    }
    
    if (-not (Test-Path $fixRPC)) {
        Write-ColorMessage "Script de correction du RPCManager non trouvé: $fixRPC" "Red"
        return
    }
    
    # Exécuter les scripts de correction
    Write-ColorMessage "1. Correction de l'importation cyclique..." "Cyan"
    python $fixCircular
    
    Write-ColorMessage "2. Correction du RPCManager..." "Cyan"
    python $fixRPC
}

# Vérifier que le répertoire de configuration existe
$configDir = ".\config"
if (-not (Test-Path $configDir)) {
    Write-ColorMessage "Création du répertoire de configuration..." "Yellow"
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

# Création d'un fichier de configuration de test si nécessaire
if (-not (Test-Path $configPath)) {
    Write-ColorMessage "Création du fichier de configuration de test: $configPath" "Yellow"
    
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
    Write-ColorMessage "Test invalide: $test" "Red"
    Write-ColorMessage "Tests disponibles: $($validTests -join ', ')" "Yellow"
    exit 1
}

# Afficher les informations sur le test à exécuter
Write-ColorMessage "=====================================================" "Cyan"
Write-ColorMessage "Exécution des tests MEV/Frontrunning (CORRIGÉS): $test" "Cyan"
Write-ColorMessage "Configuration: $configPath" "Cyan"
Write-ColorMessage "=====================================================" "Cyan"

# Créer un script Python temporaire pour exécuter le test
$tempScriptPath = [System.IO.Path]::GetTempFileName() + ".py"
@"
import asyncio
import sys
import os
import importlib.util
import json
from pathlib import Path

# Assurez-vous que le chemin racine est dans sys.path
ROOT_DIR = os.path.abspath(os.path.curdir)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Charger le module de test
test_module_path = os.path.join(ROOT_DIR, 'gbpbot', 'tests', 'real_environment_mev_test.py')
spec = importlib.util.spec_from_file_location("real_environment_mev_test", test_module_path)
test_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_module)

# Charger la configuration
config_path = os.path.join(ROOT_DIR, '$configPath')
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except Exception as e:
    print(f"Erreur lors du chargement de la configuration: {str(e)}")
    sys.exit(1)

# Exécuter la fonction appropriée selon le test spécifié
async def run_test():
    # Initialiser les modules
    if not await test_module.initialize():
        print("Échec de l'initialisation. Arrêt des tests.")
        return

    test_name = '$test'
    
    if test_name == 'all':
        # Exécuter tous les tests disponibles
        tests = {
            "mempool": test_module.test_mempool_monitoring,
            "analysis": test_module.test_transaction_analysis,
            "gas": test_module.test_gas_optimization
        }
        
        for name, test_func in tests.items():
            print(f"=== Test: {name} ===")
            success = await test_func(config)
            print(f"Résultat: {'Succès' if success else 'Échec'}")
            print("=" * 40)
    else:
        # Exécuter le test spécifique
        test_func = None
        if test_name == 'mempool':
            test_func = test_module.test_mempool_monitoring
        elif test_name == 'analysis':
            test_func = test_module.test_transaction_analysis
        elif test_name == 'gas':
            test_func = test_module.test_gas_optimization
        
        if test_func:
            print(f"=== Test: {test_name} ===")
            success = await test_func(config)
            print(f"Résultat: {'Succès' if success else 'Échec'}")
        else:
            print(f"Test inconnu: {test_name}")

# Exécuter la fonction de test de manière asynchrone
if __name__ == "__main__":
    asyncio.run(run_test())
"@ | Set-Content -Path $tempScriptPath -Encoding UTF8

# Démarrer le test
try {
    Write-ColorMessage "Démarrage des tests..." "Green"
    python $tempScriptPath
    $exitCode = $LASTEXITCODE
    
    # Supprimer le script temporaire
    Remove-Item -Path $tempScriptPath -Force
    
    if ($exitCode -eq 0) {
        Write-ColorMessage "Tests terminés avec succès." "Green"
    } else {
        Write-ColorMessage "Tests terminés avec des erreurs (code $exitCode)." "Yellow"
    }
} catch {
    Write-ColorMessage "Erreur lors de l'exécution des tests: $_" "Red"
    # Supprimer le script temporaire en cas d'erreur
    if (Test-Path $tempScriptPath) {
        Remove-Item -Path $tempScriptPath -Force
    }
}

Write-ColorMessage "Tests terminés." "Green" 