# Script d'analyse locale du code GBPBot pour Windows
# Permet d'exécuter les mêmes analyses que dans le pipeline CI/CD

Write-Host "===== Analyse de sécurité locale du GBPBot =====" -ForegroundColor Cyan
Write-Host "1. Installation des outils d'analyse..." -ForegroundColor Green

# Vérifier si Python est disponible
try {
    $pythonVersion = python --version
    Write-Host "Python détecté: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python n'est pas installé ou n'est pas dans le PATH. Veuillez l'installer avant de continuer." -ForegroundColor Red
    exit 1
}

# Créer un environnement virtuel s'il n'existe pas
if (-not (Test-Path "venv_analyse")) {
    Write-Host "Création de l'environnement virtuel..." -ForegroundColor Yellow
    python -m venv venv_analyse
}

# Activer l'environnement virtuel
Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
if (Test-Path "venv_analyse\Scripts\Activate.ps1") {
    & "venv_analyse\Scripts\Activate.ps1"
} else {
    Write-Host "Impossible d'activer l'environnement virtuel." -ForegroundColor Red
    exit 1
}

# Installer les outils d'analyse
Write-Host "Installation des outils d'analyse..." -ForegroundColor Yellow
pip install -q bandit pylint ruff safety pytest pytest-cov

Write-Host "2. Analyse avec Bandit (détection des vulnérabilités)..." -ForegroundColor Green
bandit -r . -x venv,venv_310,venv_new,env,venv_analyse -f json -o bandit-report.json
bandit -r . -x venv,venv_310,venv_new,env,venv_analyse -f txt -o bandit-report.txt
Write-Host ""

Write-Host "3. Analyse avec Pylint (qualité du code)..." -ForegroundColor Green
pylint --output-format=text gbpbot > pylint-report.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pylint a détecté des problèmes. Consultez pylint-report.txt pour plus de détails." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "4. Analyse avec Safety (vulnérabilités des dépendances)..." -ForegroundColor Green
safety check -r requirements-core.txt --output json > safety-report.json
if ($LASTEXITCODE -ne 0) {
    Write-Host "Safety a détecté des vulnérabilités. Consultez safety-report.json pour plus de détails." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "5. Analyse avec Ruff (linting rapide)..." -ForegroundColor Green
ruff check . --exclude venv,venv_310,venv_new,env,venv_analyse --output-format=text > ruff-report.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ruff a détecté des problèmes. Consultez ruff-report.txt pour plus de détails." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "6. Exécution des tests avec couverture..." -ForegroundColor Green
pytest --cov=. --cov-report=xml:coverage.xml
if ($LASTEXITCODE -ne 0) {
    Write-Host "Certains tests ont échoué. Consultez coverage.xml pour plus de détails." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "===== Résumé des résultats =====" -ForegroundColor Cyan
Write-Host "Les rapports ont été générés dans les fichiers suivants :" -ForegroundColor White
Write-Host "- bandit-report.json/txt : Vulnérabilités de sécurité" -ForegroundColor White
Write-Host "- pylint-report.txt : Qualité du code" -ForegroundColor White
Write-Host "- safety-report.json : Vulnérabilités des dépendances" -ForegroundColor White
Write-Host "- ruff-report.txt : Problèmes de style et erreurs potentielles" -ForegroundColor White
Write-Host "- coverage.xml : Couverture des tests" -ForegroundColor White
Write-Host ""
Write-Host "Pour une analyse complète, veuillez consulter ces rapports." -ForegroundColor Green

# Désactiver l'environnement virtuel
deactivate 