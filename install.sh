#!/bin/bash
# =================================================================
# GBPBot - Script d'Installation Universel
# =================================================================
# Ce script installe GBPBot et configure l'environnement nécessaire
# Compatible avec: Linux, macOS et Windows (via WSL)
# =================================================================

# Configuration des couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Répertoire de base
BASE_DIR=$(pwd)
LOG_FILE="$BASE_DIR/installation.log"

# Fonction pour l'affichage des logs
log() {
    local level=$1
    local message=$2
    local color=$NC
    
    case $level in
        "INFO") color=$GREEN ;;
        "WARNING") color=$YELLOW ;;
        "ERROR") color=$RED ;;
        "STEP") color=$BLUE ;;
    esac
    
    # Affichage dans la console
    echo -e "${color}[$level] $message${NC}"
    
    # Enregistrement dans le fichier de log
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
}

# Fonction pour vérifier la réussite d'une commande
check_success() {
    if [ $? -eq 0 ]; then
        log "INFO" "✅ Succès: $1"
        return 0
    else
        log "ERROR" "❌ Échec: $1"
        return 1
    fi
}

# Fonction pour détecter le système d'exploitation
detect_os() {
    log "STEP" "Détection du système d'exploitation..."
    
    if [ -f /etc/os-release ]; then
        # Linux
        source /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log "INFO" "Système Linux détecté: $OS $VER"
        PACKAGE_MANAGER=""
        
        if [ -x "$(command -v apt)" ]; then
            PACKAGE_MANAGER="apt"
        elif [ -x "$(command -v dnf)" ]; then
            PACKAGE_MANAGER="dnf"
        elif [ -x "$(command -v yum)" ]; then
            PACKAGE_MANAGER="yum"
        elif [ -x "$(command -v zypper)" ]; then
            PACKAGE_MANAGER="zypper"
        elif [ -x "$(command -v pacman)" ]; then
            PACKAGE_MANAGER="pacman"
        fi
        
        log "INFO" "Gestionnaire de paquets détecté: $PACKAGE_MANAGER"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        OS="macOS"
        VER=$(sw_vers -productVersion)
        PACKAGE_MANAGER="brew"
        log "INFO" "Système macOS détecté: $OS $VER"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        OS="Windows"
        VER=$(cmd.exe /c ver 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "inconnu")
        PACKAGE_MANAGER="choco"
        log "INFO" "Système Windows détecté: $OS $VER"
        log "WARNING" "Certaines fonctionnalités peuvent être limitées sous Windows. L'utilisation de WSL est recommandée."
    else
        # Autre
        OS="inconnu"
        VER="inconnu"
        PACKAGE_MANAGER=""
        log "WARNING" "Système d'exploitation non reconnu. L'installation pourrait échouer."
    fi
}

# Fonction pour installer les dépendances système
install_system_dependencies() {
    log "STEP" "Installation des dépendances système..."
    
    case $PACKAGE_MANAGER in
        "apt")
            log "INFO" "Mise à jour des paquets..."
            sudo apt update
            check_success "Mise à jour des paquets"
            
            log "INFO" "Installation des paquets requis..."
            sudo apt install -y python3 python3-pip python3-venv git curl wget nodejs npm
            check_success "Installation des paquets Python et Node.js"
            
            # Paquets optionnels pour l'IA
            log "INFO" "Installation des paquets pour l'IA (CUDA, etc.)..."
            sudo apt install -y python3-dev build-essential
            check_success "Installation des paquets pour l'IA"
            ;;
            
        "dnf" | "yum")
            log "INFO" "Mise à jour des paquets..."
            sudo $PACKAGE_MANAGER update -y
            check_success "Mise à jour des paquets"
            
            log "INFO" "Installation des paquets requis..."
            sudo $PACKAGE_MANAGER install -y python3 python3-pip python3-devel git curl wget nodejs npm
            check_success "Installation des paquets Python et Node.js"
            
            # Paquets optionnels pour l'IA
            log "INFO" "Installation des paquets pour l'IA (CUDA, etc.)..."
            sudo $PACKAGE_MANAGER install -y gcc-c++ make
            check_success "Installation des paquets pour l'IA"
            ;;
            
        "pacman")
            log "INFO" "Mise à jour des paquets..."
            sudo pacman -Syu --noconfirm
            check_success "Mise à jour des paquets"
            
            log "INFO" "Installation des paquets requis..."
            sudo pacman -S --noconfirm python python-pip git curl wget nodejs npm
            check_success "Installation des paquets Python et Node.js"
            
            # Paquets optionnels pour l'IA
            log "INFO" "Installation des paquets pour l'IA (CUDA, etc.)..."
            sudo pacman -S --noconfirm base-devel
            check_success "Installation des paquets pour l'IA"
            ;;
            
        "zypper")
            log "INFO" "Mise à jour des paquets..."
            sudo zypper refresh
            check_success "Mise à jour des paquets"
            
            log "INFO" "Installation des paquets requis..."
            sudo zypper install -y python3 python3-pip python3-devel git curl wget nodejs npm
            check_success "Installation des paquets Python et Node.js"
            
            # Paquets optionnels pour l'IA
            log "INFO" "Installation des paquets pour l'IA (CUDA, etc.)..."
            sudo zypper install -y -t pattern devel_basis
            check_success "Installation des paquets pour l'IA"
            ;;
            
        "brew")
            log "INFO" "Mise à jour des paquets..."
            brew update
            check_success "Mise à jour des paquets"
            
            log "INFO" "Installation des paquets requis..."
            brew install python3 git curl wget node
            check_success "Installation des paquets Python et Node.js"
            ;;
            
        "choco")
            log "INFO" "Installation des paquets requis avec Chocolatey..."
            choco install -y python nodejs git curl wget
            check_success "Installation des paquets Python et Node.js"
            ;;
            
        *)
            log "WARNING" "Gestionnaire de paquets non pris en charge. Veuillez installer manuellement Python 3.11+, pip, git, curl, wget, Node.js et npm."
            read -p "Appuyez sur Entrée pour continuer une fois que vous avez installé les dépendances manuellement..."
            ;;
    esac
}

# Fonction pour vérifier les versions
check_versions() {
    log "STEP" "Vérification des versions installées..."
    
    # Vérifier Python
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 --version)
        log "INFO" "Python installé: $PYTHON_VERSION"
    elif command -v python &>/dev/null; then
        PYTHON_VERSION=$(python --version)
        log "INFO" "Python installé: $PYTHON_VERSION"
    else
        log "ERROR" "Python n'est pas installé. L'installation ne peut pas continuer."
        exit 1
    fi
    
    # Vérifier Node.js
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version)
        log "INFO" "Node.js installé: $NODE_VERSION"
    else
        log "WARNING" "Node.js n'est pas installé. L'adaptateur Solana Web3.js ne fonctionnera pas."
    fi
    
    # Vérifier npm
    if command -v npm &>/dev/null; then
        NPM_VERSION=$(npm --version)
        log "INFO" "npm installé: $NPM_VERSION"
    else
        log "WARNING" "npm n'est pas installé. L'adaptateur Solana Web3.js ne fonctionnera pas."
    fi
}

# Fonction pour configurer l'environnement Python
setup_python_environment() {
    log "STEP" "Configuration de l'environnement Python..."
    
    # Créer un environnement virtuel
    log "INFO" "Création d'un environnement virtuel..."
    python3 -m venv venv || python -m venv venv
    check_success "Création de l'environnement virtuel"
    
    # Activer l'environnement virtuel
    log "INFO" "Activation de l'environnement virtuel..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        log "ERROR" "Impossible d'activer l'environnement virtuel."
        exit 1
    fi
    check_success "Activation de l'environnement virtuel"
    
    # Mettre à jour pip
    log "INFO" "Mise à jour de pip..."
    pip install --upgrade pip
    check_success "Mise à jour de pip"
    
    # Installer les dépendances Python
    log "INFO" "Installation des dépendances Python..."
    pip install -r requirements.txt
    check_success "Installation des dépendances Python"
}

# Fonction pour configurer l'adaptateur Solana Web3.js
setup_solana_adapter() {
    log "STEP" "Configuration de l'adaptateur Solana Web3.js..."
    
    # Vérifier si Node.js et npm sont installés
    if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
        log "WARNING" "Node.js ou npm n'est pas installé. L'adaptateur Solana Web3.js ne sera pas configuré."
        return 1
    fi
    
    # Créer le répertoire de l'adaptateur si nécessaire
    log "INFO" "Création du répertoire de l'adaptateur..."
    mkdir -p gbpbot/adapters/node_bridge
    check_success "Création du répertoire de l'adaptateur"
    
    # Se déplacer dans le répertoire de l'adaptateur
    cd gbpbot/adapters/node_bridge
    
    # Initialiser le projet Node.js
    log "INFO" "Initialisation du projet Node.js..."
    npm init -y
    check_success "Initialisation du projet Node.js"
    
    # Installer les dépendances Node.js
    log "INFO" "Installation de @solana/web3.js..."
    npm install @solana/web3.js
    check_success "Installation de @solana/web3.js"
    
    # Revenir au répertoire de base
    cd "$BASE_DIR"
}

# Fonction pour configurer le fichier .env
setup_env_file() {
    log "STEP" "Configuration du fichier .env..."
    
    if [ -f ".env" ]; then
        log "INFO" "Le fichier .env existe déjà."
        
        # Demander s'il faut remplacer le fichier
        read -p "Voulez-vous remplacer le fichier .env existant? (o/n): " replace_env
        if [[ $replace_env != "o" && $replace_env != "O" ]]; then
            log "INFO" "Conservation du fichier .env existant."
            return 0
        fi
    fi
    
    log "INFO" "Création du fichier .env..."
    
    # Créer le fichier .env
    cat > .env << EOL
# Configuration GBPBot
# Généré par le script d'installation

# Configuration générale
DEBUG=false
LOG_LEVEL=info
ENVIRONMENT=production

# Configuration Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
# SOLANA_PRIVATE_KEY=votre_clé_privée_ici

# Configuration AVAX
AVAX_RPC_URL=https://api.avax.network/ext/bc/C/rpc
# AVAX_PRIVATE_KEY=votre_clé_privée_ici

# Configuration Sonic
SONIC_RPC_URL=https://rpc.sonic.fantom.network/
# SONIC_PRIVATE_KEY=votre_clé_privée_ici

# Paramètres trading
MAX_SLIPPAGE=1.0
GAS_PRIORITY=medium
MAX_TRANSACTION_AMOUNT=0.1
ENABLE_SNIPING=true
ENABLE_ARBITRAGE=false
ENABLE_AUTO_MODE=false

# Sécurité
REQUIRE_CONTRACT_ANALYSIS=true
ENABLE_STOP_LOSS=true
DEFAULT_STOP_LOSS_PERCENTAGE=5

# Interface utilisateur
ENABLE_WEB_DASHBOARD=true
WEB_DASHBOARD_PORT=8080

# IA et Machine Learning
ENABLE_AI_ANALYSIS=true
USE_LOCAL_MODELS=true
USE_OPENAI_API=false
# OPENAI_API_KEY=votre_clé_api_ici

# Configuration avancée
MEMPOOL_MONITORING=true
MEV_PROTECTION=true
ENABLE_ANTI_RUGPULL=true
EOL
    
    check_success "Création du fichier .env"
    log "INFO" "⚠️ N'oubliez pas de modifier le fichier .env avec vos clés privées et configurations spécifiques."
}

# Fonction pour créer les scripts de démarrage
create_startup_scripts() {
    log "STEP" "Création des scripts de démarrage..."
    
    # Script pour Linux/macOS
    log "INFO" "Création du script de démarrage pour Linux/macOS..."
    cat > start_gbpbot.sh << EOL
#!/bin/bash
# Script de démarrage pour GBPBot (Linux/macOS)

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "L'environnement virtuel n'existe pas. Exécutez d'abord install.sh."
    exit 1
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Démarrer GBPBot
python gbpbot/start.py "\$@"
EOL
    
    chmod +x start_gbpbot.sh
    check_success "Création du script de démarrage pour Linux/macOS"
    
    # Script pour Windows
    log "INFO" "Création du script de démarrage pour Windows..."
    cat > start_gbpbot.bat << EOL
@echo off
REM Script de démarrage pour GBPBot (Windows)

REM Vérifier si l'environnement virtuel existe
if not exist "venv\Scripts\activate.bat" (
    echo L'environnement virtuel n'existe pas. Exécutez d'abord install.bat.
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Démarrer GBPBot
python gbpbot/start.py %*
EOL
    
    check_success "Création du script de démarrage pour Windows"
}

# Fonction principale
main() {
    echo "============================================================"
    echo "            GBPBot - Script d'Installation"
    echo "============================================================"
    echo ""
    
    # Initialiser le fichier de log
    echo "# Log d'installation de GBPBot - $(date)" > "$LOG_FILE"
    
    # Détecter le système d'exploitation
    detect_os
    
    # Installer les dépendances système
    install_system_dependencies
    
    # Vérifier les versions
    check_versions
    
    # Configurer l'environnement Python
    setup_python_environment
    
    # Configurer l'adaptateur Solana Web3.js
    setup_solana_adapter
    
    # Configurer le fichier .env
    setup_env_file
    
    # Créer les scripts de démarrage
    create_startup_scripts
    
    # Finalisation
    log "STEP" "Installation terminée!"
    log "INFO" "GBPBot a été installé avec succès."
    log "INFO" "Pour démarrer GBPBot sous Linux/macOS, exécutez: ./start_gbpbot.sh"
    log "INFO" "Pour démarrer GBPBot sous Windows, exécutez: start_gbpbot.bat"
    log "INFO" "N'oubliez pas de configurer vos clés privées dans le fichier .env avant de commencer."
    log "INFO" "Le log d'installation est disponible dans: $LOG_FILE"
    
    echo ""
    echo "============================================================"
    echo "            Installation terminée!"
    echo "============================================================"
}

# Exécuter la fonction principale
main 