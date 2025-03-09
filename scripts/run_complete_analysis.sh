#!/bin/bash
# Script d'analyse complète pour GBPBot
# Ce script exécute tous les outils d'analyse et importe les résultats dans SonarQube

# Couleurs pour les messages
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Vérifier si SonarQube est en cours d'exécution
function check_sonarqube_running {
    if curl -s http://localhost:9000/api/system/status | grep -q '"status":"UP"'; then
        return 0
    else
        return 1
    fi
}

# Afficher un message de début
echo -e "\n${CYAN}🔍 Démarrage de l'analyse complète pour GBPBot...${NC}"

# Étape 1: Vérifier si SonarQube est en cours d'exécution
echo -e "\n${CYAN}📋 Vérification de SonarQube...${NC}"
if ! check_sonarqube_running; then
    echo -e "${RED}❌ SonarQube n'est pas en cours d'exécution. Veuillez démarrer SonarQube avant de continuer.${NC}"
    echo -e "${YELLOW}   Exécutez sonar.sh start dans le dossier bin/[OS] de votre installation SonarQube.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ SonarQube est en cours d'exécution${NC}"
fi

# Étape 2: Exécuter les tests avec couverture
echo -e "\n${CYAN}📋 Exécution des tests avec couverture...${NC}"
pip install pytest pytest-cov -q
if pytest --cov=gbpbot --cov-report=xml:coverage.xml; then
    echo -e "${GREEN}✅ Tests exécutés avec succès${NC}"
else
    echo -e "${YELLOW}⚠️ Erreur lors de l'exécution des tests. Continuons avec l'analyse...${NC}"
fi

# Étape 3: Exécuter l'analyse de sécurité
echo -e "\n${CYAN}📋 Exécution de l'analyse de sécurité...${NC}"
if bash "$(dirname "$0")/run_security_analysis.sh"; then
    echo -e "${GREEN}✅ Analyse de sécurité terminée${NC}"
else
    echo -e "${YELLOW}⚠️ Erreur lors de l'analyse de sécurité. Continuons avec SonarQube...${NC}"
fi

# Étape 4: Vérifier si SonarScanner est installé
echo -e "\n${CYAN}📋 Vérification de SonarScanner...${NC}"
TOOLS_DIR="tools"
SONAR_SCANNER_VERSION="4.8.0.2856"
OS_TYPE=$(uname -s | tr '[:upper:]' '[:lower:]')

if [ "$OS_TYPE" == "darwin" ]; then
    SONAR_SCANNER_DIR="sonar-scanner-$SONAR_SCANNER_VERSION-macosx"
else
    SONAR_SCANNER_DIR="sonar-scanner-$SONAR_SCANNER_VERSION-linux"
fi

SONAR_SCANNER_PATH="$TOOLS_DIR/$SONAR_SCANNER_DIR"

if [ ! -d "$SONAR_SCANNER_PATH" ]; then
    echo -e "${YELLOW}⚠️ SonarScanner n'est pas installé. Installation en cours...${NC}"
    bash "$(dirname "$0")/setup_sonarqube.sh"
else
    echo -e "${GREEN}✅ SonarScanner est installé${NC}"
fi

# Étape 5: Demander le token SonarQube
echo -e "\n${CYAN}📋 Configuration de l'analyse SonarQube...${NC}"
echo -e "${CYAN}Veuillez entrer votre token SonarQube:${NC}"
read -p "> " SONAR_TOKEN

if [ -z "$SONAR_TOKEN" ]; then
    echo -e "${RED}❌ Token SonarQube non fourni. Impossible de continuer.${NC}"
    exit 1
fi

# Étape 6: Exécuter l'analyse SonarQube
echo -e "\n${CYAN}📋 Exécution de l'analyse SonarQube...${NC}"

# Ajouter SonarScanner au PATH temporairement
export PATH="$PATH:$SONAR_SCANNER_PATH/bin"

# Exécuter SonarScanner
if sonar-scanner -D sonar.login="$SONAR_TOKEN"; then
    echo -e "${GREEN}✅ Analyse SonarQube terminée${NC}"
else
    echo -e "${RED}❌ Erreur lors de l'analyse SonarQube${NC}"
    exit 1
fi

# Étape 7: Afficher les résultats
echo -e "\n${GREEN}✅ Analyse complète terminée!${NC}"
echo -e "${CYAN}📊 Consultez les résultats sur http://localhost:9000/dashboard?id=GBPBot${NC}"

# Ouvrir le dashboard dans le navigateur
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:9000/dashboard?id=GBPBot" &
elif command -v open >/dev/null 2>&1; then
    open "http://localhost:9000/dashboard?id=GBPBot" &
else
    echo -e "${YELLOW}Ouvrez manuellement http://localhost:9000/dashboard?id=GBPBot dans votre navigateur.${NC}"
fi 