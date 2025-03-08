# Script PowerShell pour la vérification du code et les tests
# ----------------------------------------------------------------
# GBPBot - Script de validation du code
# ----------------------------------------------------------------

param (
    [switch]$lint = $false,
    [switch]$format = $false,
    [switch]$test = $false,
    [switch]$all = $false,
    [switch]$help = $false
)

# Vérifier si l'utilisateur a demandé l'aide
if ($help) {
    Write-Host "Script de validation du code pour GBPBot"
    Write-Host "----------------------------------------"
    Write-Host "Options:"
    Write-Host "  -lint   : Exécute pylint et flake8 pour analyser le code"
    Write-Host "  -format : Exécute black et isort pour formater le code"
    Write-Host "  -test   : Exécute les tests avec pytest"
    Write-Host "  -all    : Exécute toutes les vérifications (lint, format, test)"
    Write-Host "  -help   : Affiche cette aide"
    Write-Host ""
    Write-Host "Exemple: .\verify_code.ps1 -all"
    exit 0
}

# Si aucune option n'est spécifiée, afficher un message et quitter
if (-not $lint -and -not $format -and -not $test -and -not $all) {
    Write-Host "Aucune action spécifiée. Utilisez -help pour voir les options disponibles."
    exit 1
}

# Si l'option 'all' est spécifiée, activer toutes les options
if ($all) {
    $lint = $true
    $format = $true
    $test = $true
}

# Vérifier que nous sommes dans le répertoire racine du projet
if (-not (Test-Path "gbpbot")) {
    Write-Host "Erreur: Ce script doit être exécuté depuis le répertoire racine du projet GBPBot." -ForegroundColor Red
    exit 1
}

# Fonction pour exécuter une commande et gérer les erreurs
function Invoke-Command {
    param (
        [string]$Command,
        [string]$Description
    )
    
    Write-Host "`n=== $Description ===" -ForegroundColor Cyan
    Write-Host "Commande: $Command" -ForegroundColor Gray
    
    try {
        Invoke-Expression $Command
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -ne 0) {
            Write-Host "La commande a échoué avec le code de sortie: $exitCode" -ForegroundColor Red
            return $false
        }
        
        Write-Host "Terminé avec succès!" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "Erreur lors de l'exécution de la commande: $_" -ForegroundColor Red
        return $false
    }
}

# Vérifier la présence des outils requis
function Test-Command {
    param (
        [string]$CommandName,
        [string]$PackageName
    )
    
    try {
        $null = Invoke-Expression "python -m $CommandName --version" -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -ne 0) {
            throw "Commande non trouvée"
        }
    }
    catch {
        Write-Host "Le package '$PackageName' n'est pas installé. Installation en cours..." -ForegroundColor Yellow
        Invoke-Expression "pip install $PackageName"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Échec de l'installation de $PackageName. Assurez-vous que pip est installé et accessible." -ForegroundColor Red
            exit 1
        }
    }
}

# Vérifier les outils nécessaires
if ($lint) {
    Test-Command -CommandName "pylint" -PackageName "pylint"
    Test-Command -CommandName "flake8" -PackageName "flake8"
}

if ($format) {
    Test-Command -CommandName "black" -PackageName "black"
    Test-Command -CommandName "isort" -PackageName "isort"
}

if ($test) {
    Test-Command -CommandName "pytest" -PackageName "pytest pytest-cov"
}

# Tableau pour suivre les résultats
$results = @{}

# Exécuter les linters
if ($lint) {
    $results["pylint"] = Invoke-Command -Command "python -m pylint gbpbot" -Description "Exécution de pylint"
    $results["flake8"] = Invoke-Command -Command "python -m flake8 gbpbot" -Description "Exécution de flake8"
}

# Exécuter les formateurs de code
if ($format) {
    $results["black_check"] = Invoke-Command -Command "python -m black --check gbpbot" -Description "Vérification du formatage avec black"
    
    if (-not $results["black_check"]) {
        $response = Read-Host "Voulez-vous formater le code avec black? (O/N)"
        if ($response -eq "O" -or $response -eq "o") {
            $results["black_format"] = Invoke-Command -Command "python -m black gbpbot" -Description "Formatage du code avec black"
        }
    }
    
    $results["isort_check"] = Invoke-Command -Command "python -m isort --check-only --profile black gbpbot" -Description "Vérification de l'ordre des imports avec isort"
    
    if (-not $results["isort_check"]) {
        $response = Read-Host "Voulez-vous réorganiser les imports avec isort? (O/N)"
        if ($response -eq "O" -or $response -eq "o") {
            $results["isort_format"] = Invoke-Command -Command "python -m isort --profile black gbpbot" -Description "Réorganisation des imports avec isort"
        }
    }
}

# Exécuter les tests
if ($test) {
    $results["pytest"] = Invoke-Command -Command "python -m pytest" -Description "Exécution des tests avec pytest"
}

# Afficher un résumé
Write-Host "`n=== Résumé des vérifications ===" -ForegroundColor Cyan
$allPassed = $true

foreach ($key in $results.Keys) {
    $status = if ($results[$key]) { "Réussi" } else { "Échoué"; $allPassed = $false }
    $color = if ($results[$key]) { "Green" } else { "Red" }
    Write-Host "$key : $status" -ForegroundColor $color
}

if ($allPassed) {
    Write-Host "`nToutes les vérifications ont réussi!" -ForegroundColor Green
}
else {
    Write-Host "`nCertaines vérifications ont échoué. Veuillez corriger les problèmes indiqués ci-dessus." -ForegroundColor Yellow
}

# Afficher des conseils sur la façon de corriger les problèmes courants
if (-not $results["pylint"] -or -not $results["flake8"]) {
    Write-Host "`n=== Conseils pour corriger les problèmes de lint ===" -ForegroundColor Cyan
    Write-Host "1. Pour les erreurs d'importation, vérifiez l'ordre des imports et supprimez les imports inutilisés."
    Write-Host "2. Pour les problèmes de docstring, assurez-vous que chaque fonction, classe et module a une documentation appropriée."
    Write-Host "3. Pour les problèmes de nommage, suivez les conventions PEP8 (snake_case pour les variables et fonctions, PascalCase pour les classes)."
    Write-Host "4. Pour les problèmes de complexité, essayez de diviser les fonctions longues en fonctions plus petites et plus ciblées."
}

if (-not $results["black_check"] -or -not $results["isort_check"]) {
    Write-Host "`n=== Conseils pour le formatage du code ===" -ForegroundColor Cyan
    Write-Host "1. Exécutez 'python -m black gbpbot' pour formater automatiquement le code selon les conventions de black."
    Write-Host "2. Exécutez 'python -m isort --profile black gbpbot' pour réorganiser les imports."
}

if (-not $results["pytest"]) {
    Write-Host "`n=== Conseils pour les tests ===" -ForegroundColor Cyan
    Write-Host "1. Vérifiez les messages d'erreur des tests échoués pour comprendre ce qui ne va pas."
    Write-Host "2. Assurez-vous que tous les tests sont bien écrits et testent correctement les fonctionnalités."
    Write-Host "3. Pour les problèmes de couverture, ajoutez des tests pour les parties du code qui ne sont pas couvertes."
} 