# Script d'analyse de sécurité pour GBPBot
# Ce script exécute une série d'analyses de sécurité et de qualité de code sur le projet GBPBot

# Vérifier si les outils nécessaires sont installés
$tools = @("bandit", "pylint", "ruff", "safety")
$missing_tools = @()

foreach ($tool in $tools) {
    try {
        $null = Invoke-Expression "$tool --version"
        Write-Host "✅ $tool est installé" -ForegroundColor Green
    } catch {
        $missing_tools += $tool
        Write-Host "❌ $tool n'est pas installé" -ForegroundColor Red
    }
}

# Installer les outils manquants
if ($missing_tools.Count -gt 0) {
    Write-Host "Installation des outils manquants..." -ForegroundColor Yellow
    pip install $missing_tools
}

# Créer le répertoire de rapports
$reports_dir = "security_reports"
if (-not (Test-Path $reports_dir)) {
    New-Item -ItemType Directory -Path $reports_dir | Out-Null
    New-Item -ItemType Directory -Path "$reports_dir\custom" | Out-Null
}

Write-Host "`n🔍 Démarrage de l'analyse de sécurité pour GBPBot..." -ForegroundColor Cyan

# Exécuter Bandit (analyse de sécurité Python)
Write-Host "`n🛡️ Exécution de Bandit pour l'analyse de sécurité..." -ForegroundColor Cyan
bandit -r gbpbot -x venv,venv_310,venv_new,env,tests -f json -o "$reports_dir\bandit-report.json"
bandit -r gbpbot -x venv,venv_310,venv_new,env,tests -f html -o "$reports_dir\bandit-report.html"

# Exécuter Pylint (qualité du code)
Write-Host "`n📊 Exécution de Pylint pour l'analyse de qualité du code..." -ForegroundColor Cyan
pylint gbpbot --output-format=text > "$reports_dir\pylint-report.txt"

# Exécuter Ruff (linter rapide)
Write-Host "`n🚀 Exécution de Ruff pour l'analyse rapide..." -ForegroundColor Cyan
ruff check gbpbot --output-format=text > "$reports_dir\ruff-report.txt"

# Exécuter Safety (vérification des dépendances)
Write-Host "`n📦 Vérification des vulnérabilités dans les dépendances avec Safety..." -ForegroundColor Cyan
safety check -r requirements.txt --json > "$reports_dir\safety-report.json"
safety check -r requirements.txt --full-report > "$reports_dir\safety-report.txt"

# Recherche de patterns sensibles
Write-Host "`n🔎 Recherche de patterns sensibles dans le code..." -ForegroundColor Cyan
$sensitive_patterns = Select-String -Path "gbpbot\*.py" -Pattern "private_key|wallet_key|secret_key|mnemonic" -AllMatches
$sensitive_patterns | Out-File -FilePath "$reports_dir\custom\sensitive-patterns.txt"

# Vérification d'imports circulaires
Write-Host "`n🔄 Vérification des imports circulaires..." -ForegroundColor Cyan
$circular_imports = Select-String -Path "gbpbot\*.py" -Pattern "^from .* import" -AllMatches
$circular_imports | Out-File -FilePath "$reports_dir\custom\circular_imports_check.txt"

# Résumé
Write-Host "`n✅ Analyse de sécurité terminée!" -ForegroundColor Green
Write-Host "Les rapports sont disponibles dans le répertoire: $reports_dir" -ForegroundColor Cyan

# Ouvrir le rapport HTML de Bandit
$bandit_report = Resolve-Path "$reports_dir\bandit-report.html"
Write-Host "Ouverture du rapport Bandit: $bandit_report" -ForegroundColor Cyan
Start-Process $bandit_report 