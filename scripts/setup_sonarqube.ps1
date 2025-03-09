# Script d'installation et de configuration de SonarScanner pour GBPBot
# Ce script télécharge SonarScanner, le configure et prépare le projet pour l'analyse

# Paramètres
$sonarScannerVersion = "4.8.0.2856"
$sonarScannerZip = "sonar-scanner-cli-$sonarScannerVersion-windows.zip"
$sonarScannerUrl = "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/$sonarScannerZip"
$sonarScannerDir = "sonar-scanner-$sonarScannerVersion-windows"
$toolsDir = "tools"

# Création du répertoire tools s'il n'existe pas
if (-not (Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Path $toolsDir | Out-Null
    Write-Host "✅ Répertoire tools créé" -ForegroundColor Green
}

# Téléchargement de SonarScanner si nécessaire
$sonarScannerZipPath = Join-Path $toolsDir $sonarScannerZip
$sonarScannerPath = Join-Path $toolsDir $sonarScannerDir

if (-not (Test-Path $sonarScannerPath)) {
    Write-Host "⬇️ Téléchargement de SonarScanner $sonarScannerVersion..." -ForegroundColor Cyan
    
    if (-not (Test-Path $sonarScannerZipPath)) {
        Invoke-WebRequest -Uri $sonarScannerUrl -OutFile $sonarScannerZipPath
    }
    
    Write-Host "📦 Extraction de SonarScanner..." -ForegroundColor Cyan
    Expand-Archive -Path $sonarScannerZipPath -DestinationPath $toolsDir -Force
    
    Write-Host "✅ SonarScanner installé dans $sonarScannerPath" -ForegroundColor Green
} else {
    Write-Host "✅ SonarScanner est déjà installé dans $sonarScannerPath" -ForegroundColor Green
}

# Création du fichier de configuration sonar-project.properties
$sonarProjectProperties = @"
# Configuration du projet pour SonarQube
sonar.projectKey=GBPBot
sonar.projectName=GBPBot
sonar.projectVersion=1.0

# Chemin vers les sources
sonar.sources=gbpbot
sonar.python.coverage.reportPaths=coverage.xml

# Exclusions
sonar.exclusions=**/*.pyc,**/__pycache__/**,**/venv/**,**/venv_310/**,**/venv_new/**,**/env/**,**/tests/**,**/*.md,logs/**

# Encodage des sources
sonar.sourceEncoding=UTF-8

# Configuration Python
sonar.python.version=3.8,3.9,3.10,3.11

# Serveur SonarQube
sonar.host.url=http://localhost:9000
"@

$sonarProjectPropertiesPath = "sonar-project.properties"
Set-Content -Path $sonarProjectPropertiesPath -Value $sonarProjectProperties

Write-Host "✅ Fichier sonar-project.properties créé" -ForegroundColor Green

# Ajout de SonarScanner au PATH temporairement
$env:Path += ";$sonarScannerPath\bin"

# Vérification de l'installation
try {
    $sonarScannerVersion = Invoke-Expression "sonar-scanner.bat -v"
    Write-Host "✅ SonarScanner est correctement installé:" -ForegroundColor Green
    Write-Host $sonarScannerVersion -ForegroundColor Cyan
} catch {
    Write-Host "❌ Erreur lors de la vérification de SonarScanner. Assurez-vous qu'il est correctement installé." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# Instructions pour l'analyse
Write-Host "`n📋 Instructions pour l'analyse SonarQube:" -ForegroundColor Yellow
Write-Host "1. Assurez-vous que le serveur SonarQube est en cours d'exécution (http://localhost:9000)" -ForegroundColor White
Write-Host "2. Générez un token d'authentification dans SonarQube (Administration > Security > Users > Tokens)" -ForegroundColor White
Write-Host "3. Exécutez la commande suivante pour lancer l'analyse:" -ForegroundColor White
Write-Host "   .\tools\$sonarScannerDir\bin\sonar-scanner.bat -D sonar.login=VOTRE_TOKEN" -ForegroundColor Cyan
Write-Host "4. Consultez les résultats sur http://localhost:9000/dashboard?id=GBPBot" -ForegroundColor White

# Création d'un script d'analyse
$runSonarScannerScript = @"
@echo off
echo Exécution de l'analyse SonarQube pour GBPBot...
echo.
echo Veuillez entrer votre token SonarQube:
set /p SONAR_TOKEN="> "
echo.
.\tools\$sonarScannerDir\bin\sonar-scanner.bat -D sonar.login=%SONAR_TOKEN%
echo.
echo Analyse terminée. Consultez les résultats sur http://localhost:9000/dashboard?id=GBPBot
pause
"@

$runSonarScannerPath = "run_sonar_analysis.bat"
Set-Content -Path $runSonarScannerPath -Value $runSonarScannerScript

Write-Host "✅ Script d'analyse run_sonar_analysis.bat créé" -ForegroundColor Green
Write-Host "`n🚀 Configuration terminée! Exécutez run_sonar_analysis.bat pour lancer l'analyse." -ForegroundColor Green 