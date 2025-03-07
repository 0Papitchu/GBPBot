#!/bin/bash
# Script de démarrage GBPBot pour Linux/macOS
# Ce script vérifie les prérequis puis lance GBPBot

# Définir les couleurs
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

echo -e "${BLUE}============================================================${RESET}"
echo -e "${BLUE}                     GBPBot - Démarrage                     ${RESET}"
echo -e "${BLUE}============================================================${RESET}"
echo ""

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 n'est pas installé ou n'est pas dans le PATH.${RESET}"
    echo -e "${RED}Veuillez installer Python 3.9+ depuis https://www.python.org/${RESET}"
    echo ""
    exit 1
fi

# Vérifier la version de Python (doit être 3.9+)
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)

if [[ $PY_MAJOR -lt 3 || ($PY_MAJOR -eq 3 && $PY_MINOR -lt 9) ]]; then
    echo -e "${RED}Version de Python incompatible. Python 3.9+ requis.${RESET}"
    echo -e "${RED}Version installée: $PY_VERSION${RESET}"
    echo ""
    exit 1
fi

echo -e "${GREEN}Python $PY_VERSION OK${RESET}"

# Créer un environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Création de l'environnement virtuel...${RESET}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Erreur lors de la création de l'environnement virtuel.${RESET}"
        exit 1
    fi
fi

# Activer l'environnement virtuel
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur lors de l'activation de l'environnement virtuel.${RESET}"
    exit 1
fi

# Installer/mettre à jour les dépendances
echo -e "${YELLOW}Installation/mise à jour des dépendances...${RESET}"
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur lors de l'installation des dépendances.${RESET}"
    exit 1
fi

# Vérifier l'existence du fichier .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}.env non trouvé. Copie du fichier exemple...${RESET}"
        cp ".env.example" ".env"
        echo -e "${YELLOW}Veuillez configurer le fichier .env avec vos paramètres.${RESET}"
        echo -e "${YELLOW}Exécutez python scripts/setup_run_environment.py pour configurer.${RESET}"
        exit 1
    else
        echo -e "${RED}Fichier .env ou .env.example introuvable!${RESET}"
        exit 1
    fi
fi

# Vérifier si le système est prêt
echo -e "${YELLOW}Vérification de l'environnement...${RESET}"
python scripts/system_check.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Des problèmes ont été détectés lors de la vérification du système.${RESET}"
    echo -e "${YELLOW}Consultez les logs pour plus de détails.${RESET}"
    echo -e "${YELLOW}Voulez-vous continuer quand même? (o/n)${RESET}"
    read -n 1 continue_choice
    echo ""
    if [[ ! "$continue_choice" =~ ^[oO]$ ]]; then
        exit 1
    fi
fi

# Afficher le menu de démarrage
echo ""
echo -e "${BLUE}============================================================${RESET}"
echo -e "${BLUE}                   GBPBot - Mode de lancement                ${RESET}"
echo -e "${BLUE}============================================================${RESET}"
echo ""
echo -e "${YELLOW}Choisissez le mode de lancement:${RESET}"
echo -e "${YELLOW}1. Mode normal (CLI)${RESET}"
echo -e "${YELLOW}2. Mode simulation (sans transactions réelles)${RESET}"
echo -e "${YELLOW}3. Mode debug (plus de logs)${RESET}"
echo -e "${YELLOW}4. Dashboard web${RESET}"
echo -e "${YELLOW}5. Quitter${RESET}"
echo ""

read -n 1 choice
echo ""

case $choice in
    1)
        echo -e "${GREEN}Démarrage de GBPBot en mode normal...${RESET}"
        python run_gbpbot.py
        ;;
    2)
        echo -e "${GREEN}Démarrage de GBPBot en mode simulation...${RESET}"
        python run_gbpbot.py --simulation
        ;;
    3)
        echo -e "${GREEN}Démarrage de GBPBot en mode debug...${RESET}"
        python run_gbpbot.py --debug
        ;;
    4)
        echo -e "${GREEN}Démarrage du dashboard web...${RESET}"
        python run_dashboard.py
        ;;
    5)
        echo -e "${YELLOW}Au revoir!${RESET}"
        exit 0
        ;;
    *)
        echo -e "${RED}Choix invalide.${RESET}"
        exit 1
        ;;
esac

# Fin du script
echo ""
echo -e "${BLUE}============================================================${RESET}"
echo -e "${BLUE}                     GBPBot - Terminé                        ${RESET}"
echo -e "${BLUE}============================================================${RESET}"

# Désactiver l'environnement virtuel
deactivate 