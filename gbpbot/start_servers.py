import subprocess
import sys
import os
import time
from loguru import logger

# Configuration du logger
logger.add("servers.log", rotation="1 MB", retention="7 days", level="INFO")

def start_servers():
    """Démarrer les serveurs API et dashboard"""
    logger.info("Démarrage des serveurs GBPBot...")
    
    # Chemin vers l'interpréteur Python actuel
    python_executable = sys.executable
    
    # Chemin du répertoire courant
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Commandes pour démarrer les serveurs
    api_command = [python_executable, os.path.join(current_dir, "api_server.py")]
    dashboard_command = [python_executable, os.path.join(current_dir, "web_dashboard.py")]
    
    try:
        # Démarrer le serveur API
        logger.info("Démarrage du serveur API sur http://127.0.0.1:5000")
        api_process = subprocess.Popen(api_command, 
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True)
        
        # Attendre un peu pour s'assurer que l'API démarre avant le dashboard
        time.sleep(2)
        
        # Démarrer le serveur dashboard
        logger.info("Démarrage du dashboard web sur http://127.0.0.1:5001")
        dashboard_process = subprocess.Popen(dashboard_command,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True)
        
        logger.info("Serveurs démarrés avec succès!")
        logger.info("API: http://127.0.0.1:5000")
        logger.info("Dashboard: http://127.0.0.1:5001")
        
        print("\n=== GBPBot Servers ===")
        print("API: http://127.0.0.1:5000")
        print("Dashboard: http://127.0.0.1:5001")
        print("Appuyez sur Ctrl+C pour arrêter les serveurs")
        
        # Attendre que les processus se terminent
        while True:
            if api_process.poll() is not None:
                logger.error("Le serveur API s'est arrêté de manière inattendue")
                break
            if dashboard_process.poll() is not None:
                logger.error("Le serveur dashboard s'est arrêté de manière inattendue")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Arrêt des serveurs...")
        
        # Arrêter les processus
        if 'api_process' in locals():
            api_process.terminate()
        if 'dashboard_process' in locals():
            dashboard_process.terminate()
            
        logger.info("Serveurs arrêtés")
        print("Serveurs arrêtés")
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage des serveurs: {str(e)}")
        print(f"Erreur: {str(e)}")
        
if __name__ == "__main__":
    start_servers() 