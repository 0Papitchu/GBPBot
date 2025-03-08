#!/bin/bash
# Script d'analyse locale pour GBPBot
# Ce script permet d'exécuter une analyse de code locale avant de soumettre des modifications

echo -e "\e[1;36m=== GBPBot - Analyse de Code Locale ===\e[0m"
echo -e "\e[1;36mCe script va exécuter une analyse complète du code pour détecter les problèmes potentiels.\e[0m"
echo ""

# Vérifier si Python est installé
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    echo -e "\e[1;32m✅ Python détecté: $(python3 --version)\e[0m"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
    echo -e "\e[1;32m✅ Python détecté: $(python --version)\e[0m"
else
    echo -e "\e[1;31m❌ Python n'est pas installé ou n'est pas dans le PATH\e[0m"
    exit 1
fi

# Vérifier si les dépendances nécessaires sont installées
echo -e "\e[1;33mVérification des dépendances d'analyse...\e[0m"
dependencies=("pylint" "bandit" "pytest" "pytest_cov" "safety")
missing=()

for dep in "${dependencies[@]}"; do
    if ! $PYTHON_CMD -c "import $dep" &>/dev/null; then
        missing+=("$dep")
        echo -e "\e[1;31m❌ $dep n'est pas installé\e[0m"
    else
        echo -e "\e[1;32m✅ $dep est installé\e[0m"
    fi
done

# Installer les dépendances manquantes
if [ ${#missing[@]} -gt 0 ]; then
    echo -e "\e[1;33mInstallation des dépendances manquantes...\e[0m"
    for dep in "${missing[@]}"; do
        # Convertir pytest_cov en pytest-cov pour pip
        if [ "$dep" == "pytest_cov" ]; then
            dep="pytest-cov"
        fi
        echo -e "\e[1;33mInstallation de $dep...\e[0m"
        pip install "$dep"
    done
fi

# Créer le dossier de rapports s'il n'existe pas
mkdir -p reports

# Exécuter pylint
echo -e "\n\e[1;36m=== Exécution de Pylint ===\e[0m"
pylint gbpbot --output-format=text:reports/pylint-report.txt,colorized

# Exécuter bandit pour l'analyse de sécurité
echo -e "\n\e[1;36m=== Exécution de Bandit (Analyse de Sécurité) ===\e[0m"
bandit -r gbpbot -f json -o reports/bandit-report.json
bandit -r gbpbot -f txt -o reports/bandit-report.txt

# Exécuter les tests avec couverture
echo -e "\n\e[1;36m=== Exécution des Tests avec Couverture ===\e[0m"
pytest --cov=gbpbot --cov-report=xml:reports/coverage.xml --cov-report=term

# Vérifier les dépendances pour les vulnérabilités
echo -e "\n\e[1;36m=== Vérification des Vulnérabilités dans les Dépendances ===\e[0m"
safety check -r requirements-core.txt --output text --save reports/safety-report.txt

# Résumé
echo -e "\n\e[1;36m=== Résumé de l'Analyse ===\e[0m"
echo -e "Les rapports ont été générés dans le dossier 'reports':"
echo -e "- Rapport Pylint: reports/pylint-report.txt"
echo -e "- Rapport Bandit: reports/bandit-report.txt et reports/bandit-report.json"
echo -e "- Rapport de Couverture: reports/coverage.xml"
echo -e "- Rapport de Sécurité des Dépendances: reports/safety-report.txt"

echo -e "\n\e[1;33mPour une analyse complète avec SonarQube, exécutez:\e[0m"
echo -e "sonar-scanner -Dsonar.projectKey=GBPBot -Dsonar.sources=. -Dsonar.host.url=http://localhost:9000 -Dsonar.login=votre_token"

echo -e "\n\e[1;36m=== Analyse Terminée ===\e[0m" 