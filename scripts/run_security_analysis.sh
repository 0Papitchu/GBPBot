#!/bin/bash
# Script d'analyse de sécurité pour GBPBot
# Ce script exécute une série d'analyses de sécurité et de qualité de code sur le projet GBPBot

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Vérifier si les outils nécessaires sont installés
tools=("bandit" "pylint" "ruff" "safety")
missing_tools=()

for tool in "${tools[@]}"; do
    if command -v $tool >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $tool est installé${NC}"
    else
        missing_tools+=($tool)
        echo -e "${RED}❌ $tool n'est pas installé${NC}"
    fi
done

# Installer les outils manquants
if [ ${#missing_tools[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installation des outils manquants...${NC}"
    pip install "${missing_tools[@]}"
fi

# Créer le répertoire de rapports
reports_dir="security_reports"
mkdir -p "$reports_dir/custom"

echo -e "\n${CYAN}🔍 Démarrage de l'analyse de sécurité pour GBPBot...${NC}"

# Exécuter Bandit (analyse de sécurité Python)
echo -e "\n${CYAN}🛡️ Exécution de Bandit pour l'analyse de sécurité...${NC}"
bandit -r gbpbot -x venv,venv_310,venv_new,env,tests -f json -o "$reports_dir/bandit-report.json"
bandit -r gbpbot -x venv,venv_310,venv_new,env,tests -f html -o "$reports_dir/bandit-report.html"

# Exécuter Pylint (qualité du code)
echo -e "\n${CYAN}📊 Exécution de Pylint pour l'analyse de qualité du code...${NC}"
pylint gbpbot --output-format=text > "$reports_dir/pylint-report.txt" || true

# Exécuter Ruff (linter rapide)
echo -e "\n${CYAN}🚀 Exécution de Ruff pour l'analyse rapide...${NC}"
ruff check gbpbot --output-format=text > "$reports_dir/ruff-report.txt" || true

# Exécuter Safety (vérification des dépendances)
echo -e "\n${CYAN}📦 Vérification des vulnérabilités dans les dépendances avec Safety...${NC}"
safety check -r requirements.txt --json > "$reports_dir/safety-report.json" || true
safety check -r requirements.txt --full-report > "$reports_dir/safety-report.txt" || true

# Recherche de patterns sensibles
echo -e "\n${CYAN}🔎 Recherche de patterns sensibles dans le code...${NC}"
grep -r --include="*.py" -E "(private_key|wallet_key|secret_key|mnemonic)" gbpbot > "$reports_dir/custom/sensitive-patterns.txt" || true

# Vérification d'imports circulaires
echo -e "\n${CYAN}🔄 Vérification des imports circulaires...${NC}"
grep -r "^from .* import" --include="*.py" gbpbot | sort > "$reports_dir/custom/circular_imports_check.txt" || true

# Résumé
echo -e "\n${GREEN}✅ Analyse de sécurité terminée!${NC}"
echo -e "${CYAN}Les rapports sont disponibles dans le répertoire: $reports_dir${NC}"

# Ouvrir le rapport HTML de Bandit (si possible)
bandit_report="$(pwd)/$reports_dir/bandit-report.html"
echo -e "${CYAN}Rapport Bandit: $bandit_report${NC}"

# Tenter d'ouvrir le rapport avec le navigateur par défaut
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$bandit_report" &
elif command -v open >/dev/null 2>&1; then
    open "$bandit_report" &
else
    echo -e "${YELLOW}Ouvrez manuellement le rapport HTML dans votre navigateur.${NC}"
fi 