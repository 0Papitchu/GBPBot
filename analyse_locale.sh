#!/bin/bash
# Script d'analyse locale du code GBPBot
# Permet d'exécuter les mêmes analyses que dans le pipeline CI/CD

echo "===== Analyse de sécurité locale du GBPBot ====="
echo "1. Installation des outils d'analyse..."

# Vérifier si Python est disponible
if ! command -v python &> /dev/null; then
    echo "Python n'est pas installé. Veuillez l'installer avant de continuer."
    exit 1
fi

# Créer un environnement virtuel s'il n'existe pas
if [ ! -d "venv_analyse" ]; then
    python -m venv venv_analyse
fi

# Activer l'environnement virtuel (adapté pour bash)
if [ -f "venv_analyse/bin/activate" ]; then
    source venv_analyse/bin/activate
elif [ -f "venv_analyse/Scripts/activate" ]; then
    source venv_analyse/Scripts/activate
else
    echo "Impossible d'activer l'environnement virtuel."
    exit 1
fi

# Installer les outils d'analyse
pip install -q bandit pylint ruff safety pytest pytest-cov

echo "2. Analyse avec Bandit (détection des vulnérabilités)..."
bandit -r . -x venv,venv_310,venv_new,env,venv_analyse -f json -o bandit-report.json
bandit -r . -x venv,venv_310,venv_new,env,venv_analyse -f txt -o bandit-report.txt
echo

echo "3. Analyse avec Pylint (qualité du code)..."
pylint --output-format=text gbpbot > pylint-report.txt || true
echo

echo "4. Analyse avec Safety (vulnérabilités des dépendances)..."
safety check -r requirements-core.txt --output json > safety-report.json || true
echo

echo "5. Analyse avec Ruff (linting rapide)..."
ruff check . --exclude venv,venv_310,venv_new,env,venv_analyse --output-format=text > ruff-report.txt || true
echo

echo "6. Exécution des tests avec couverture..."
pytest --cov=. --cov-report=xml:coverage.xml || true
echo

echo "===== Résumé des résultats ====="
echo "Les rapports ont été générés dans les fichiers suivants :"
echo "- bandit-report.json/txt : Vulnérabilités de sécurité"
echo "- pylint-report.txt : Qualité du code"
echo "- safety-report.json : Vulnérabilités des dépendances"
echo "- ruff-report.txt : Problèmes de style et erreurs potentielles"
echo "- coverage.xml : Couverture des tests"
echo
echo "Pour une analyse complète, veuillez consulter ces rapports."

# Désactiver l'environnement virtuel
deactivate 