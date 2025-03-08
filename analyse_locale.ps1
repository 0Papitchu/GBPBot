# Script d'analyse locale pour GBPBot
# Ce script permet d'exécuter une analyse complète du code pour détecter les problèmes potentiels.

Write-Host "=== GBPBot - Analyse de Code Locale ===" -ForegroundColor Cyan
Write-Host "Ce script va exécuter une analyse complète du code pour détecter les problèmes potentiels." -ForegroundColor Cyan
Write-Host ""

# Vérifier si Python est installé
try {
    $pythonVersion = python --version
    Write-Host "✅ Python détecté: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python n'est pas installé ou n'est pas dans le PATH" -ForegroundColor Red
    exit 1
}

# Vérifier si les dépendances nécessaires sont installées
Write-Host "Vérification des dépendances d'analyse..." -ForegroundColor Yellow
$dependencies = @("pylint", "bandit", "pytest", "pytest-cov", "safety")
$missing = @()

foreach ($dep in $dependencies) {
    try {
        $null = python -c "import $dep"
        Write-Host "✅ $dep est installé" -ForegroundColor Green
    } catch {
        $missing += $dep
        Write-Host "❌ $dep n'est pas installé" -ForegroundColor Red
    }
}

# Installer les dépendances manquantes
if ($missing.Count -gt 0) {
    Write-Host "Installation des dépendances manquantes..." -ForegroundColor Yellow
    foreach ($dep in $missing) {
        Write-Host "Installation de $dep..." -ForegroundColor Yellow
        pip install $dep
    }
}

# Créer le dossier de rapports s'il n'existe pas
if (-not (Test-Path -Path "reports")) {
    New-Item -ItemType Directory -Path "reports" | Out-Null
}

# Exécuter pylint
Write-Host "`n=== Exécution de Pylint ===" -ForegroundColor Cyan
pylint gbpbot --output-format=text:reports/pylint-report.txt,colorized

# Exécuter bandit pour l'analyse de sécurité
Write-Host "`n=== Exécution de Bandit (Analyse de Sécurité) ===" -ForegroundColor Cyan
bandit -r gbpbot -f json -o reports/bandit-report.json
bandit -r gbpbot -f txt -o reports/bandit-report.txt

# Exécuter les tests avec couverture
Write-Host "`n=== Exécution des Tests avec Couverture ===" -ForegroundColor Cyan
pytest --cov=gbpbot --cov-report=xml:reports/coverage.xml --cov-report=term

# Vérifier les dépendances pour les vulnérabilités
Write-Host "`n=== Vérification des Vulnérabilités dans les Dépendances ===" -ForegroundColor Cyan
safety check -r requirements-core.txt --output text --save reports/safety-report.txt

# Résumé
Write-Host "`n=== Résumé de l'Analyse ===" -ForegroundColor Cyan
Write-Host "Les rapports ont été générés dans le dossier 'reports':" -ForegroundColor White
Write-Host "- Rapport Pylint: reports/pylint-report.txt" -ForegroundColor White
Write-Host "- Rapport Bandit: reports/bandit-report.txt et reports/bandit-report.json" -ForegroundColor White
Write-Host "- Rapport de Couverture: reports/coverage.xml" -ForegroundColor White
Write-Host "- Rapport de Sécurité des Dépendances: reports/safety-report.txt" -ForegroundColor White

Write-Host "`nPour une analyse complète avec SonarQube, exécutez:" -ForegroundColor Yellow
Write-Host "sonar-scanner -Dsonar.projectKey=GBPBot -Dsonar.sources=. -Dsonar.host.url=http://localhost:9000 -Dsonar.login=votre_token" -ForegroundColor Yellow

Write-Host "`n=== Analyse Terminée ===" -ForegroundColor Cyan 