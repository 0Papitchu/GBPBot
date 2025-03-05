#!/usr/bin/env python3
"""
Script d'arrêt d'urgence pour GBPBot.
Arrête immédiatement toutes les activités du bot et enregistre la raison.
"""

import argparse
import asyncio
import logging
import sys
import os
import json
import datetime
from pathlib import Path
import requests

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

from gbpbot.core.emergency.emergency_system import EmergencySystem
from gbpbot.core.monitoring.advanced_monitor import AdvancedMonitor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/emergency.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("emergency_stop")

async def emergency_stop(args):
    """
    Exécute la procédure d'arrêt d'urgence.
    
    Args:
        args: Arguments de la ligne de commande
    """
    try:
        logger.info(f"Démarrage de la procédure d'arrêt d'urgence: {args.reason}")
        
        # Charger la configuration
        config_path = args.config or "config/default_config.yaml"
        if not os.path.exists(config_path):
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            return 1
            
        # Initialiser le moniteur
        monitor = AdvancedMonitor(config_path)
        await monitor.start()
        
        # Initialiser le système d'urgence
        emergency_system = EmergencySystem(config_path, monitor)
        await emergency_system.start()
        
        # Enregistrer l'incident
        incident_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        incident_data = {
            "id": incident_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "reason": args.reason,
            "triggered_by": "manual" if not args.auto else "automatic",
            "severity": args.severity
        }
        
        # Sauvegarder les détails de l'incident
        incidents_dir = Path("data/incidents")
        incidents_dir.mkdir(parents=True, exist_ok=True)
        
        with open(incidents_dir / f"incident_{incident_id}.json", "w") as f:
            json.dump(incident_data, f, indent=2)
            
        # Activer le mode d'urgence
        await emergency_system.handle_emergency(args.reason)
        
        # Envoyer des notifications si demandé
        if args.notify:
            await send_notifications(incident_data, config_path)
            
        # Arrêter les services en cours
        await stop_running_services()
        
        logger.info(f"Procédure d'arrêt d'urgence terminée. ID de l'incident: {incident_id}")
        
        # Afficher les instructions pour la reprise
        print("\n" + "="*80)
        print("PROCÉDURE D'ARRÊT D'URGENCE TERMINÉE")
        print(f"ID de l'incident: {incident_id}")
        print("\nPour vérifier l'état du système:")
        print("  python scripts/check_status.py")
        print("\nPour redémarrer en mode surveillance uniquement:")
        print("  python scripts/start_bot.py --mode=monitor-only")
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.critical(f"Erreur lors de la procédure d'arrêt d'urgence: {str(e)}", exc_info=True)
        return 1
        
async def send_notifications(incident_data, config_path):
    """
    Envoie des notifications d'urgence.
    
    Args:
        incident_data: Données de l'incident
        config_path: Chemin du fichier de configuration
    """
    try:
        # Charger la configuration pour les notifications
        # (Dans une implémentation réelle, charger depuis le fichier de config)
        
        # Exemple de notification Discord
        if os.environ.get("DISCORD_WEBHOOK_URL"):
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            
            message = {
                "embeds": [{
                    "title": "🚨 ALERTE CRITIQUE: Arrêt d'urgence de GBPBot",
                    "description": f"**Raison**: {incident_data['reason']}\n**ID**: {incident_data['id']}\n**Sévérité**: {incident_data['severity']}",
                    "color": 16711680,  # Rouge
                    "timestamp": incident_data['timestamp']
                }]
            }
            
            requests.post(webhook_url, json=message)
            logger.info("Notification Discord envoyée")
            
        # Exemple de notification Telegram
        if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            
            message = f"🚨 ALERTE CRITIQUE: Arrêt d'urgence de GBPBot\n\nRaison: {incident_data['reason']}\nID: {incident_data['id']}\nSévérité: {incident_data['severity']}"
            
            requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}")
            logger.info("Notification Telegram envoyée")
            
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi des notifications: {str(e)}")
        
async def stop_running_services():
    """
    Arrête tous les services en cours d'exécution.
    """
    try:
        # Rechercher le PID du processus principal
        pid_file = Path("data/gbpbot.pid")
        if pid_file.exists():
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
                
            logger.info(f"Tentative d'arrêt du processus principal (PID: {pid})")
            
            # Tenter d'arrêter proprement le processus
            try:
                import signal
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Signal SIGTERM envoyé au processus {pid}")
                
                # Attendre que le processus se termine
                for _ in range(10):
                    try:
                        os.kill(pid, 0)  # Vérifie si le processus existe encore
                        await asyncio.sleep(1)
                    except OSError:
                        logger.info(f"Processus {pid} terminé")
                        break
                else:
                    # Si le processus ne s'est pas terminé, forcer l'arrêt
                    logger.warning(f"Le processus {pid} ne répond pas, envoi de SIGKILL")
                    os.kill(pid, signal.SIGKILL)
                    
            except ProcessLookupError:
                logger.info(f"Le processus {pid} n'existe plus")
            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt du processus {pid}: {str(e)}")
                
            # Supprimer le fichier PID
            pid_file.unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt des services: {str(e)}")
        
def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script d'arrêt d'urgence pour GBPBot")
    
    parser.add_argument("--reason", required=True, help="Raison de l'arrêt d'urgence")
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="high", help="Niveau de sévérité de l'incident")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration")
    parser.add_argument("--notify", action="store_true", help="Envoyer des notifications")
    parser.add_argument("--auto", action="store_true", help="Indique si l'arrêt est automatique")
    
    args = parser.parse_args()
    
    # Exécuter la procédure d'arrêt d'urgence
    exit_code = asyncio.run(emergency_stop(args))
    sys.exit(exit_code)
    
if __name__ == "__main__":
    main() 