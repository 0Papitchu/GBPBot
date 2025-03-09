#!/bin/bash
# Script d'installation et de configuration de SonarScanner pour GBPBot
# Ce script télécharge SonarScanner, le configure et prépare le projet pour l'analyse

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Paramètres
SONAR_SCANNER_VERSION="4.8.0.2856"
OS_TYPE=$(uname -s | tr '[:upper:]' '[:lower:]')

if [ "$OS_TYPE" == "darwin" ]; then
    SONAR_SCANNER_ZIP="sonar-scanner-cli-$SONAR_SCANNER_VERSION-macosx.zip"
    SONAR_SCANNER_DIR="sonar-scanner-$SONAR_SCANNER_VERSION-macosx"
else
    SONAR_SCANNER_ZIP="sonar-scanner-cli-$SONAR_SCANNER_VERSION-linux.zip"
    SONAR_SCANNER_DIR="sonar-scanner-$SONAR_SCANNER_VERSION-linux"
fi

SONAR_SCANNER_URL="https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/$SONAR_SCANNER_ZIP"
TOOLS_DIR="tools"

# Création du répertoire tools s'il n'existe pas
if [ ! -d "$TOOLS_DIR" ]; then
    mkdir -p "$TOOLS_DIR"
    echo -e "${GREEN}✅ Répertoire tools créé${NC}"
fi

# Téléchargement de SonarScanner si nécessaire
SONAR_SCANNER_ZIP_PATH="$TOOLS_DIR/$SONAR_SCANNER_ZIP"
SONAR_SCANNER_PATH="$TOOLS_DIR/$SONAR_SCANNER_DIR"

if [ ! -d "$SONAR_SCANNER_PATH" ]; then
    echo -e "${CYAN}⬇️ Téléchargement de SonarScanner $SONAR_SCANNER_VERSION...${NC}"
    
    if [ ! -f "$SONAR_SCANNER_ZIP_PATH" ]; then
        curl -L -o "$SONAR_SCANNER_ZIP_PATH" "$SONAR_SCANNER_URL"
    fi
    
    echo -e "${CYAN}📦 Extraction de SonarScanner...${NC}"
    unzip -q "$SONAR_SCANNER_ZIP_PATH" -d "$TOOLS_DIR"
    
    echo -e "${GREEN}✅ SonarScanner installé dans $SONAR_SCANNER_PATH${NC}"
else
    echo -e "${GREEN}✅ SonarScanner est déjà installé dans $SONAR_SCANNER_PATH${NC}"
fi

# Création du fichier de configuration sonar-project.properties
cat > sonar-project.properties << EOL
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
EOL

echo -e "${GREEN}✅ Fichier sonar-project.properties créé${NC}"

# Ajout de SonarScanner au PATH temporairement
export PATH="$PATH:$SONAR_SCANNER_PATH/bin"

# Vérification de l'installation
if command -v sonar-scanner >/dev/null 2>&1; then
    SONAR_SCANNER_VERSION_OUTPUT=$(sonar-scanner -v)
    echo -e "${GREEN}✅ SonarScanner est correctement installé:${NC}"
    echo -e "${CYAN}$SONAR_SCANNER_VERSION_OUTPUT${NC}"
else
    echo -e "${RED}❌ Erreur lors de la vérification de SonarScanner. Assurez-vous qu'il est correctement installé.${NC}"
fi

# Instructions pour l'analyse
echo -e "\n${YELLOW}📋 Instructions pour l'analyse SonarQube:${NC}"
echo -e "${WHITE}1. Assurez-vous que le serveur SonarQube est en cours d'exécution (http://localhost:9000)${NC}"
echo -e "${WHITE}2. Générez un token d'authentification dans SonarQube (Administration > Security > Users > Tokens)${NC}"
echo -e "${WHITE}3. Exécutez la commande suivante pour lancer l'analyse:${NC}"
echo -e "${CYAN}   $SONAR_SCANNER_PATH/bin/sonar-scanner -D sonar.login=VOTRE_TOKEN${NC}"
echo -e "${WHITE}4. Consultez les résultats sur http://localhost:9000/dashboard?id=GBPBot${NC}"

# Création d'un script d'analyse
cat > run_sonar_analysis.sh << EOL
#!/bin/bash
echo "Exécution de l'analyse SonarQube pour GBPBot..."
echo ""
echo "Veuillez entrer votre token SonarQube:"
read -p "> " SONAR_TOKEN
echo ""
$SONAR_SCANNER_PATH/bin/sonar-scanner -D sonar.login=\$SONAR_TOKEN
echo ""
echo "Analyse terminée. Consultez les résultats sur http://localhost:9000/dashboard?id=GBPBot"
EOL

chmod +x run_sonar_analysis.sh

echo -e "${GREEN}✅ Script d'analyse run_sonar_analysis.sh créé${NC}"
echo -e "\n${GREEN}🚀 Configuration terminée! Exécutez ./run_sonar_analysis.sh pour lancer l'analyse.${NC}" 