#!/bin/bash

echo "==================================================="
echo "    GBPBot - Démarrage des Outils d'Optimisation"
echo "==================================================="
echo

echo "[1/4] Vérification de l'environnement..."
if [ ! -f "monitor_performance.py" ]; then
    echo "ERREUR: Le fichier monitor_performance.py est introuvable."
    exit 1
fi
if [ ! -f "auto_optimizer.py" ]; then
    echo "ERREUR: Le fichier auto_optimizer.py est introuvable."
    exit 1
fi

echo "[2/4] Démarrage du moniteur de performances..."
python3 monitor_performance.py --no-gui &
MONITOR_PID=$!
if [ $? -ne 0 ]; then
    echo "ERREUR: Impossible de démarrer le moniteur de performances."
    exit 1
fi

echo "[3/4] Attente de démarrage du moniteur (2 secondes)..."
sleep 2

echo "[4/4] Démarrage de l'optimiseur automatique..."
python3 auto_optimizer.py &
OPTIMIZER_PID=$!
if [ $? -ne 0 ]; then
    echo "ERREUR: Impossible de démarrer l'optimiseur automatique."
    kill $MONITOR_PID 2>/dev/null
    exit 1
fi

echo
echo "==================================================="
echo "           Outils d'optimisation démarrés !"
echo "==================================================="
echo
echo "Les outils suivants sont en cours d'exécution :"
echo " - Moniteur de Performances (PID: $MONITOR_PID)"
echo " - Optimiseur Automatique (PID: $OPTIMIZER_PID)"
echo
echo "Pour arrêter les outils, exécutez:"
echo "kill $MONITOR_PID $OPTIMIZER_PID"
echo
echo "Processus démarrés en arrière-plan. Vous pouvez fermer cette fenêtre."
echo "Un fichier 'gbpbot_performance.log' sera créé pour le moniteur."
echo "Un fichier 'auto_optimizer_*.log' sera créé pour l'optimiseur."
echo

# Création d'un fichier pour faciliter l'arrêt ultérieur
cat > stop_all_tools.sh << EOF
#!/bin/bash
echo "Arrêt des outils d'optimisation GBPBot..."
kill $MONITOR_PID $OPTIMIZER_PID 2>/dev/null
echo "Terminé."
EOF

chmod +x stop_all_tools.sh
echo "Un script d'arrêt a été créé: stop_all_tools.sh" 