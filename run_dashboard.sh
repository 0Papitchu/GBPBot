#!/bin/bash
# Script de lancement du Dashboard GBPBot pour Linux/macOS

echo "====================================="
echo "     GBPBot Dashboard Launcher"
echo "====================================="
echo ""

# Vérifier que Python est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé ou n'est pas dans le PATH."
    echo "Veuillez installer Python 3.8 ou supérieur."
    exit 1
fi

# Vérifier la version de Python
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_VERSION_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_VERSION_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_VERSION_MAJOR" -lt 3 ] || ([ "$PYTHON_VERSION_MAJOR" -eq 3 ] && [ "$PYTHON_VERSION_MINOR" -lt 8 ]); then
    echo "❌ Python 3.8 ou supérieur est requis. Version détectée: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION détecté"

# Vérifier que le dossier GBPBot existe
if [ ! -d "gbpbot" ]; then
    echo "❌ Le dossier 'gbpbot' n'existe pas dans le répertoire courant."
    echo "Veuillez exécuter ce script depuis le répertoire racine du projet GBPBot."
    exit 1
fi

# Vérifier que le module dashboard existe
if [ ! -d "gbpbot/dashboard" ]; then
    echo "❌ Le module dashboard n'existe pas dans le projet GBPBot."
    echo "Veuillez vérifier l'installation du projet."
    exit 1
fi

# Vérifier les dépendances
echo "🔍 Vérification des dépendances..."
MISSING_DEPS=0

for dep in fastapi uvicorn pydantic websockets; do
    if ! python3 -c "import $dep" &> /dev/null; then
        echo "❌ Module Python '$dep' manquant"
        MISSING_DEPS=1
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "Des dépendances sont manquantes. Voulez-vous les installer maintenant? (o/n)"
    read -r answer
    if [[ "$answer" =~ ^[Oo]$ ]]; then
        echo "Installation des dépendances..."
        pip install -r requirements.txt
    else
        echo "Installation annulée. Certaines fonctionnalités peuvent ne pas fonctionner."
    fi
fi

# Demander les options de lancement
echo ""
echo "Options de lancement du dashboard:"
echo ""
echo "1. Lancement standard (localhost:8000)"
echo "2. Accès réseau (0.0.0.0:8000)"
echo "3. Mode simulation (génération de données fictives)"
echo "4. Mode développement (simulation + debug)"
echo "5. Mode personnalisé"
echo "6. Quitter"
echo ""
read -p "Choisissez une option (1-6): " option

case $option in
    1)
        echo "🚀 Lancement du dashboard en mode standard..."
        python3 -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 8000
        ;;
    2)
        echo "🚀 Lancement du dashboard avec accès réseau..."
        python3 -m gbpbot.dashboard.run_dashboard --host 0.0.0.0 --port 8000
        ;;
    3)
        echo "🚀 Lancement du dashboard en mode simulation..."
        python3 -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 8000 --simulate
        ;;
    4)
        echo "🚀 Lancement du dashboard en mode développement..."
        python3 -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 8000 --simulate --log-level DEBUG
        ;;
    5)
        read -p "Adresse d'hôte (défaut: 127.0.0.1): " host
        host=${host:-127.0.0.1}
        
        read -p "Port (défaut: 8000): " port
        port=${port:-8000}
        
        read -p "Activer la simulation? (o/n, défaut: n): " simulate
        if [[ "$simulate" =~ ^[Oo]$ ]]; then
            simulate_flag="--simulate"
        else
            simulate_flag=""
        fi
        
        read -p "Niveau de log (DEBUG/INFO/WARNING/ERROR/CRITICAL, défaut: INFO): " log_level
        log_level=${log_level:-INFO}
        
        echo "🚀 Lancement du dashboard avec les options personnalisées..."
        python3 -m gbpbot.dashboard.run_dashboard --host "$host" --port "$port" $simulate_flag --log-level "$log_level"
        ;;
    6)
        echo "Au revoir!"
        exit 0
        ;;
    *)
        echo "❌ Option non valide"
        exit 1
        ;;
esac

exit 0 