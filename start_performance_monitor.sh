#!/bin/bash
# Script de démarrage du moniteur de performances GBPBot
# Auteur: GBPBot Team
# Date: 2025-03-06

echo "==================================================="
echo "   GBPBot - Démarrage du Moniteur de Performances"
echo "==================================================="
echo ""

# Vérification de Python
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python 3 n'est pas installé ou n'est pas dans le PATH."
    echo "Veuillez installer Python 3.7+ et réessayer."
    exit 1
fi

# Vérification du fichier moniteur
if [ ! -f "monitor_performance.py" ]; then
    echo "[ERREUR] Le fichier monitor_performance.py est introuvable."
    echo "Assurez-vous d'être dans le bon répertoire."
    exit 1
fi

# Vérification des dépendances
echo "[INFO] Vérification des dépendances..."
if ! python3 -c "import psutil, matplotlib" &> /dev/null; then
    echo "[INFO] Installation des dépendances requises..."
    python3 install_performance_monitor.py
    if [ $? -ne 0 ]; then
        echo "[ERREUR] L'installation des dépendances a échoué."
        exit 1
    fi
fi

echo ""
echo "[INFO] Démarrage du moniteur de performances..."
echo "[INFO] Appuyez sur Ctrl+C pour arrêter le moniteur."
echo ""

# Recherche du processus GBPBot
GBPBOT_PID=$(ps aux | grep -E "python.*[g]bpbot|python.*[m]ain.py" | awk '{print $2}' | head -1)

if [ -n "$GBPBOT_PID" ]; then
    echo "[INFO] Processus GBPBot trouvé avec PID: $GBPBOT_PID"
    echo "[INFO] Surveillance du processus GBPBot (PID: $GBPBOT_PID)"
    python3 monitor_performance.py --pid $GBPBOT_PID
else
    echo "[INFO] Aucun processus GBPBot trouvé, surveillance du système uniquement."
    python3 monitor_performance.py
fi

echo ""
echo "[INFO] Moniteur de performances arrêté." 