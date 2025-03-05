#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de surveillance pour GBPBot en production.
Ce script surveille l'état de santé du bot en production et prend des mesures
correctives si nécessaire (redémarrage, notifications, etc.).
"""

import os
import sys
import time
import json
import subprocess
import argparse
import requests
import smtplib
import socket
import psutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
import asyncio

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("monitor.log", rotation="10 MB", level="DEBUG")

class ProductionMonitor:
    """Classe pour surveiller GBPBot en production."""
    
    def __init__(self, config_file=None):
        """
        Initialiser le moniteur de production.
        
        Args:
            config_file: Chemin vers le fichier de configuration de surveillance
        """
        # Chemin du répertoire courant
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Charger la configuration
        self.config = self._load_config(config_file)
        
        # Chemin vers l'interpréteur Python actuel
        self.python_executable = sys.executable
        
        # État de santé
        self.health_status = {
            "api_server": True,
            "dashboard": True,
            "mempool_sniping": True,
            "gas_optimizer": True,
            "bundle_checker": True,
            "system_resources": True,
            "last_check": datetime.now().isoformat(),
            "restarts": 0,
            "alerts_sent": 0
        }
        
        # Historique des vérifications
        self.check_history = []
        
        # Dernière alerte envoyée
        self.last_alert_time = None
    
    def _load_config(self, config_file):
        """
        Charger la configuration de surveillance.
        
        Args:
            config_file: Chemin vers le fichier de configuration
            
        Returns:
            dict: Configuration de surveillance
        """
        # Configuration par défaut
        default_config = {
            "api_url": "http://127.0.0.1:5000",
            "dashboard_url": "http://127.0.0.1:5001",
            "api_key": os.getenv("GBPBOT_API_KEY", ""),
            "check_interval": 60,  # en secondes
            "max_restarts": 3,
            "restart_cooldown": 300,  # en secondes
            "alert_cooldown": 1800,  # en secondes (30 minutes)
            "cpu_threshold": 90,  # pourcentage
            "memory_threshold": 90,  # pourcentage
            "disk_threshold": 90,  # pourcentage
            "enable_email_alerts": False,
            "email_from": os.getenv("GBPBOT_EMAIL_FROM", ""),
            "email_to": os.getenv("GBPBOT_EMAIL_TO", ""),
            "email_smtp_server": os.getenv("GBPBOT_SMTP_SERVER", ""),
            "email_smtp_port": int(os.getenv("GBPBOT_SMTP_PORT", "587")),
            "email_smtp_user": os.getenv("GBPBOT_SMTP_USER", ""),
            "email_smtp_password": os.getenv("GBPBOT_SMTP_PASSWORD", ""),
            "enable_telegram_alerts": False,
            "telegram_bot_token": os.getenv("GBPBOT_TELEGRAM_TOKEN", ""),
            "telegram_chat_id": os.getenv("GBPBOT_TELEGRAM_CHAT_ID", ""),
            "log_file": "monitor.log",
            "history_file": "monitor_history.json"
        }
        
        # Si un fichier de configuration est spécifié, le charger et fusionner avec la configuration par défaut
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    
                # Fusionner les configurations
                for key, value in user_config.items():
                    default_config[key] = value
                    
                logger.info(f"Configuration chargée depuis {config_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        
        return default_config
    
    async def start_monitoring(self):
        """Démarrer la surveillance."""
        logger.info("Démarrage de la surveillance de GBPBot en production...")
        
        try:
            # Charger l'historique des vérifications
            self._load_history()
            
            # Boucle de surveillance
            while True:
                # Vérifier l'état de santé
                await self._check_health()
                
                # Sauvegarder l'historique
                self._save_history()
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(self.config["check_interval"])
                
        except KeyboardInterrupt:
            logger.info("Surveillance interrompue par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance: {str(e)}")
            # Envoyer une alerte
            self._send_alert(f"Erreur critique du moniteur: {str(e)}")
    
    async def _check_health(self):
        """Vérifier l'état de santé du bot."""
        logger.info("Vérification de l'état de santé...")
        
        # Mettre à jour la date de dernière vérification
        self.health_status["last_check"] = datetime.now().isoformat()
        
        # Vérifier les ressources système
        self._check_system_resources()
        
        # Vérifier le serveur API
        api_status = await self._check_api_server()
        self.health_status["api_server"] = api_status
        
        # Si le serveur API est en panne, essayer de le redémarrer
        if not api_status:
            logger.error("Le serveur API est en panne")
            self._send_alert("Le serveur API est en panne")
            
            # Redémarrer le serveur API
            if self.health_status["restarts"] < self.config["max_restarts"]:
                logger.info("Tentative de redémarrage du serveur API...")
                success = self._restart_service("api_server")
                if success:
                    logger.success("Serveur API redémarré avec succès")
                    self.health_status["restarts"] += 1
                else:
                    logger.error("Échec du redémarrage du serveur API")
                    self._send_alert("Échec du redémarrage du serveur API")
            else:
                logger.error(f"Nombre maximum de redémarrages atteint ({self.config['max_restarts']})")
                self._send_alert(f"Nombre maximum de redémarrages atteint ({self.config['max_restarts']})")
        
        # Vérifier le dashboard
        dashboard_status = await self._check_dashboard()
        self.health_status["dashboard"] = dashboard_status
        
        # Si le dashboard est en panne, essayer de le redémarrer
        if not dashboard_status:
            logger.error("Le dashboard est en panne")
            self._send_alert("Le dashboard est en panne")
            
            # Redémarrer le dashboard
            if self.health_status["restarts"] < self.config["max_restarts"]:
                logger.info("Tentative de redémarrage du dashboard...")
                success = self._restart_service("dashboard")
                if success:
                    logger.success("Dashboard redémarré avec succès")
                    self.health_status["restarts"] += 1
                else:
                    logger.error("Échec du redémarrage du dashboard")
                    self._send_alert("Échec du redémarrage du dashboard")
            else:
                logger.error(f"Nombre maximum de redémarrages atteint ({self.config['max_restarts']})")
        
        # Si le serveur API est opérationnel, vérifier les modules
        if api_status:
            # Vérifier le module de sniping mempool
            mempool_status = await self._check_module("mempool_sniping")
            self.health_status["mempool_sniping"] = mempool_status
            
            # Vérifier le module d'optimisation du gas
            gas_status = await self._check_module("gas_optimizer")
            self.health_status["gas_optimizer"] = gas_status
            
            # Vérifier le module de détection des bundles
            bundle_status = await self._check_module("bundle_checker")
            self.health_status["bundle_checker"] = bundle_status
        
        # Ajouter la vérification à l'historique
        self.check_history.append({
            "timestamp": datetime.now().isoformat(),
            "status": self.health_status.copy()
        })
        
        # Limiter la taille de l'historique
        if len(self.check_history) > 1000:
            self.check_history = self.check_history[-1000:]
        
        # Afficher le résumé
        self._print_summary()
    
    def _check_system_resources(self):
        """Vérifier les ressources système."""
        logger.info("Vérification des ressources système...")
        
        try:
            # Vérifier l'utilisation du CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Vérifier l'utilisation de la mémoire
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Vérifier l'utilisation du disque
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Vérifier si les seuils sont dépassés
            cpu_ok = cpu_percent < self.config["cpu_threshold"]
            memory_ok = memory_percent < self.config["memory_threshold"]
            disk_ok = disk_percent < self.config["disk_threshold"]
            
            # Mettre à jour l'état de santé
            self.health_status["system_resources"] = cpu_ok and memory_ok and disk_ok
            
            # Journaliser les résultats
            logger.info(f"CPU: {cpu_percent}% (seuil: {self.config['cpu_threshold']}%)")
            logger.info(f"Mémoire: {memory_percent}% (seuil: {self.config['memory_threshold']}%)")
            logger.info(f"Disque: {disk_percent}% (seuil: {self.config['disk_threshold']}%)")
            
            # Envoyer une alerte si nécessaire
            if not cpu_ok:
                self._send_alert(f"Utilisation CPU élevée: {cpu_percent}%")
            if not memory_ok:
                self._send_alert(f"Utilisation mémoire élevée: {memory_percent}%")
            if not disk_ok:
                self._send_alert(f"Utilisation disque élevée: {disk_percent}%")
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des ressources système: {str(e)}")
            self.health_status["system_resources"] = False
    
    async def _check_api_server(self):
        """
        Vérifier l'état du serveur API.
        
        Returns:
            bool: True si le serveur API est opérationnel, False sinon
        """
        logger.info("Vérification du serveur API...")
        
        try:
            # Vérifier si le serveur API répond
            response = requests.get(
                f"{self.config['api_url']}/health",
                headers={"x-api-key": self.config["api_key"]},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.success("Serveur API opérationnel")
                return True
            else:
                logger.error(f"Serveur API en erreur: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la connexion au serveur API: {str(e)}")
            return False
    
    async def _check_dashboard(self):
        """
        Vérifier l'état du dashboard.
        
        Returns:
            bool: True si le dashboard est opérationnel, False sinon
        """
        logger.info("Vérification du dashboard...")
        
        try:
            # Vérifier si le dashboard répond
            response = requests.get(
                self.config["dashboard_url"],
                timeout=5
            )
            
            if response.status_code == 200:
                logger.success("Dashboard opérationnel")
                return True
            else:
                logger.error(f"Dashboard en erreur: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la connexion au dashboard: {str(e)}")
            return False
    
    async def _check_module(self, module_name):
        """
        Vérifier l'état d'un module.
        
        Args:
            module_name: Nom du module à vérifier
            
        Returns:
            bool: True si le module est opérationnel, False sinon
        """
        logger.info(f"Vérification du module {module_name}...")
        
        try:
            # Vérifier si le module répond via l'API
            response = requests.get(
                f"{self.config['api_url']}/status",
                headers={"x-api-key": self.config["api_key"]},
                timeout=5
            )
            
            if response.status_code == 200:
                # Vérifier si le module est actif dans la réponse
                data = response.json()
                if module_name in data and data[module_name]["active"]:
                    logger.success(f"Module {module_name} opérationnel")
                    return True
                else:
                    logger.error(f"Module {module_name} inactif")
                    return False
            else:
                logger.error(f"Erreur lors de la vérification du module {module_name}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du module {module_name}: {str(e)}")
            return False
    
    def _restart_service(self, service_name):
        """
        Redémarrer un service.
        
        Args:
            service_name: Nom du service à redémarrer
            
        Returns:
            bool: True si le redémarrage a réussi, False sinon
        """
        logger.info(f"Redémarrage du service {service_name}...")
        
        try:
            # Vérifier si le service est géré par systemd
            if self._is_systemd_service(service_name):
                # Redémarrer le service via systemd
                subprocess.run(["sudo", "systemctl", "restart", f"gbpbot-{service_name}"], check=True)
            else:
                # Redémarrer le service manuellement
                if service_name == "api_server":
                    cmd = [
                        self.python_executable,
                        os.path.join(self.current_dir, "api_server.py")
                    ]
                elif service_name == "dashboard":
                    cmd = [
                        self.python_executable,
                        os.path.join(self.current_dir, "web_dashboard.py")
                    ]
                else:
                    logger.error(f"Service inconnu: {service_name}")
                    return False
                
                # Exécuter la commande en arrière-plan
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            # Attendre que le service démarre
            time.sleep(5)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du redémarrage du service {service_name}: {str(e)}")
            return False
    
    def _is_systemd_service(self, service_name):
        """
        Vérifier si un service est géré par systemd.
        
        Args:
            service_name: Nom du service à vérifier
            
        Returns:
            bool: True si le service est géré par systemd, False sinon
        """
        try:
            # Vérifier si le service existe
            result = subprocess.run(
                ["systemctl", "is-active", f"gbpbot-{service_name}"],
                capture_output=True,
                text=True
            )
            
            # Si la commande a réussi, le service existe
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _send_alert(self, message):
        """
        Envoyer une alerte.
        
        Args:
            message: Message d'alerte
        """
        # Vérifier si une alerte a déjà été envoyée récemment
        if self.last_alert_time:
            elapsed = (datetime.now() - self.last_alert_time).total_seconds()
            if elapsed < self.config["alert_cooldown"]:
                logger.info(f"Alerte ignorée (cooldown): {message}")
                return
        
        logger.info(f"Envoi d'une alerte: {message}")
        
        # Mettre à jour le compteur d'alertes
        self.health_status["alerts_sent"] += 1
        
        # Mettre à jour la date de dernière alerte
        self.last_alert_time = datetime.now()
        
        # Envoyer une alerte par email
        if self.config["enable_email_alerts"]:
            self._send_email_alert(message)
        
        # Envoyer une alerte par Telegram
        if self.config["enable_telegram_alerts"]:
            self._send_telegram_alert(message)
    
    def _send_email_alert(self, message):
        """
        Envoyer une alerte par email.
        
        Args:
            message: Message d'alerte
        """
        try:
            # Créer le message
            msg = MIMEMultipart()
            msg["From"] = self.config["email_from"]
            msg["To"] = self.config["email_to"]
            msg["Subject"] = f"Alerte GBPBot - {socket.gethostname()}"
            
            # Ajouter le corps du message
            body = f"""
            <html>
            <body>
                <h2>Alerte GBPBot</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Serveur:</strong> {socket.gethostname()}</p>
                <p><strong>Message:</strong> {message}</p>
                <h3>État de santé</h3>
                <ul>
                    <li>API Server: {'OK' if self.health_status['api_server'] else 'KO'}</li>
                    <li>Dashboard: {'OK' if self.health_status['dashboard'] else 'KO'}</li>
                    <li>Mempool Sniping: {'OK' if self.health_status['mempool_sniping'] else 'KO'}</li>
                    <li>Gas Optimizer: {'OK' if self.health_status['gas_optimizer'] else 'KO'}</li>
                    <li>Bundle Checker: {'OK' if self.health_status['bundle_checker'] else 'KO'}</li>
                    <li>Ressources Système: {'OK' if self.health_status['system_resources'] else 'KO'}</li>
                </ul>
                <p><strong>Redémarrages:</strong> {self.health_status['restarts']}</p>
                <p><strong>Alertes envoyées:</strong> {self.health_status['alerts_sent']}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, "html"))
            
            # Envoyer l'email
            with smtplib.SMTP(self.config["email_smtp_server"], self.config["email_smtp_port"]) as server:
                server.starttls()
                server.login(self.config["email_smtp_user"], self.config["email_smtp_password"])
                server.send_message(msg)
            
            logger.success("Alerte email envoyée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte email: {str(e)}")
    
    def _send_telegram_alert(self, message):
        """
        Envoyer une alerte par Telegram.
        
        Args:
            message: Message d'alerte
        """
        try:
            # Créer le message
            text = f"""
            🚨 *Alerte GBPBot* 🚨
            
            📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            🖥️ Serveur: {socket.gethostname()}
            
            ℹ️ Message: {message}
            
            🔍 État de santé:
            - API Server: {'✅' if self.health_status['api_server'] else '❌'}
            - Dashboard: {'✅' if self.health_status['dashboard'] else '❌'}
            - Mempool Sniping: {'✅' if self.health_status['mempool_sniping'] else '❌'}
            - Gas Optimizer: {'✅' if self.health_status['gas_optimizer'] else '❌'}
            - Bundle Checker: {'✅' if self.health_status['bundle_checker'] else '❌'}
            - Ressources Système: {'✅' if self.health_status['system_resources'] else '❌'}
            
            🔄 Redémarrages: {self.health_status['restarts']}
            📢 Alertes envoyées: {self.health_status['alerts_sent']}
            """
            
            # Envoyer le message
            url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendMessage"
            data = {
                "chat_id": self.config["telegram_chat_id"],
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data, timeout=5)
            
            if response.status_code == 200:
                logger.success("Alerte Telegram envoyée avec succès")
            else:
                logger.error(f"Erreur lors de l'envoi de l'alerte Telegram: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte Telegram: {str(e)}")
    
    def _load_history(self):
        """Charger l'historique des vérifications."""
        history_file = os.path.join(self.current_dir, self.config["history_file"])
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    self.check_history = json.load(f)
                    
                logger.info(f"Historique chargé depuis {history_file} ({len(self.check_history)} entrées)")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'historique: {str(e)}")
    
    def _save_history(self):
        """Sauvegarder l'historique des vérifications."""
        history_file = os.path.join(self.current_dir, self.config["history_file"])
        
        try:
            with open(history_file, 'w') as f:
                json.dump(self.check_history, f, indent=2)
                
            logger.debug(f"Historique sauvegardé dans {history_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'historique: {str(e)}")
    
    def _print_summary(self):
        """Afficher le résumé de l'état de santé."""
        logger.info("\n=== Résumé de l'état de santé ===")
        logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"API Server: {'OK' if self.health_status['api_server'] else 'KO'}")
        logger.info(f"Dashboard: {'OK' if self.health_status['dashboard'] else 'KO'}")
        logger.info(f"Mempool Sniping: {'OK' if self.health_status['mempool_sniping'] else 'KO'}")
        logger.info(f"Gas Optimizer: {'OK' if self.health_status['gas_optimizer'] else 'KO'}")
        logger.info(f"Bundle Checker: {'OK' if self.health_status['bundle_checker'] else 'KO'}")
        logger.info(f"Ressources Système: {'OK' if self.health_status['system_resources'] else 'KO'}")
        logger.info(f"Redémarrages: {self.health_status['restarts']}")
        logger.info(f"Alertes envoyées: {self.health_status['alerts_sent']}")

async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Surveillance de GBPBot en production")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration de surveillance")
    args = parser.parse_args()
    
    monitor = ProductionMonitor(args.config)
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main()) 