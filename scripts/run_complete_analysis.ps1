# Script d'analyse complète pour GBPBot
# Ce script exécute tous les outils d'analyse et importe les résultats dans SonarQube

# Couleurs pour les messages
$Green = [System.ConsoleColor]::Green
$Cyan = [System.ConsoleColor]::Cyan
$Yellow = [System.ConsoleColor]::Yellow
$Red = [System.ConsoleColor]::Red

# Vérifier si SonarQube est en cours d'exécution
function Test-SonarQubeRunning {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9000/api/system/status" -UseBasicParsing -ErrorAction SilentlyContinue
        $status = $response.Content | ConvertFrom-Json
        return $status.status -eq "UP"
    } catch {
        return $false
    }
}

# Afficher un message de début
Write-Host "`n🔍 Démarrage de l'analyse complète pour GBPBot..." -ForegroundColor $Cyan

# Étape 1: Vérifier si SonarQube est en cours d'exécution
Write-Host "`n📋 Vérification de SonarQube..." -ForegroundColor $Cyan
if (-not (Test-SonarQubeRunning)) {
    Write-Host "❌ SonarQube n'est pas en cours d'exécution. Veuillez démarrer SonarQube avant de continuer." -ForegroundColor $Red
    Write-Host "   Exécutez StartSonar.bat dans le dossier bin\windows-x86-64 de votre installation SonarQube." -ForegroundColor $Yellow
    exit 1
} else {
    Write-Host "✅ SonarQube est en cours d'exécution" -ForegroundColor $Green
}

# Étape 2: Exécuter les tests avec couverture
Write-Host "`n📋 Exécution des tests avec couverture..." -ForegroundColor $Cyan
try {
    pip install pytest pytest-cov -q
    pytest --cov=gbpbot --cov-report=xml:coverage.xml
    Write-Host "✅ Tests exécutés avec succès" -ForegroundColor $Green
} catch {
    Write-Host "⚠️ Erreur lors de l'exécution des tests. Continuons avec l'analyse..." -ForegroundColor $Yellow
}

# Étape 3: Exécuter l'analyse de sécurité
Write-Host "`n📋 Exécution de l'analyse de sécurité..." -ForegroundColor $Cyan
try {
    & "$PSScriptRoot\run_security_analysis.ps1"
    Write-Host "✅ Analyse de sécurité terminée" -ForegroundColor $Green
} catch {
    Write-Host "⚠️ Erreur lors de l'analyse de sécurité. Continuons avec SonarQube..." -ForegroundColor $Yellow
}

# Étape 4: Vérifier si SonarScanner est installé
Write-Host "`n📋 Vérification de SonarScanner..." -ForegroundColor $Cyan
$toolsDir = "tools"
$sonarScannerVersion = "4.8.0.2856"
$sonarScannerDir = "sonar-scanner-$sonarScannerVersion-windows"
$sonarScannerPath = Join-Path $toolsDir $sonarScannerDir

if (-not (Test-Path $sonarScannerPath)) {
    Write-Host "⚠️ SonarScanner n'est pas installé. Installation en cours..." -ForegroundColor $Yellow
    & "$PSScriptRoot\setup_sonarqube.ps1"
} else {
    Write-Host "✅ SonarScanner est installé" -ForegroundColor $Green
}

# Étape 5: Demander le token SonarQube
Write-Host "`n📋 Configuration de l'analyse SonarQube..." -ForegroundColor $Cyan
Write-Host "Veuillez entrer votre token SonarQube:" -ForegroundColor $Cyan
$sonarToken = Read-Host -Prompt "> "

if ([string]::IsNullOrWhiteSpace($sonarToken)) {
    Write-Host "❌ Token SonarQube non fourni. Impossible de continuer." -ForegroundColor $Red
    exit 1
}

# Étape 6: Exécuter l'analyse SonarQube
Write-Host "`n📋 Exécution de l'analyse SonarQube..." -ForegroundColor $Cyan

# Ajouter SonarScanner au PATH temporairement
$env:Path += ";$sonarScannerPath\bin"

# Exécuter SonarScanner
try {
    $sonarScannerCmd = "sonar-scanner.bat -D sonar.login=$sonarToken"
    Invoke-Expression $sonarScannerCmd
    Write-Host "✅ Analyse SonarQube terminée" -ForegroundColor $Green
} catch {
    Write-Host "❌ Erreur lors de l'analyse SonarQube:" -ForegroundColor $Red
    Write-Host $_.Exception.Message -ForegroundColor $Red
    exit 1
}

# Étape 7: Afficher les résultats
Write-Host "`n✅ Analyse complète terminée!" -ForegroundColor $Green
Write-Host "📊 Consultez les résultats sur http://localhost:9000/dashboard?id=GBPBot" -ForegroundColor $Cyan

# Ouvrir le dashboard dans le navigateur
Start-Process "http://localhost:9000/dashboard?id=GBPBot" 