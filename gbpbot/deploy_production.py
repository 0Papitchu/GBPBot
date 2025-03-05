#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de déploiement en production pour GBPBot.
Ce script automatise le processus de déploiement en production en effectuant
les vérifications nécessaires, en générant les certificats SSL, et en démarrant
les services en mode production.
"""

import os
import sys
import time
import subprocess
import argparse
import shutil
import json
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import asyncio

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("deployment.log", rotation="10 MB", level="DEBUG")

class ProductionDeployer:
    """Classe pour déployer GBPBot en production."""
    
    def __init__(self, config_file=None):
        """
        Initialiser le déployeur de production.
        
        Args:
            config_file: Chemin vers le fichier de configuration de déploiement
        """
        # Charger les variables d'environnement
        load_dotenv()
        
        # Chemin du répertoire courant
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Charger la configuration de déploiement
        self.config = self._load_config(config_file)
        
        # Chemin vers l'interpréteur Python actuel
        self.python_executable = sys.executable
        
        # Processus des serveurs
        self.server_processes = []
    
    def _load_config(self, config_file):
        """
        Charger la configuration de déploiement.
        
        Args:
            config_file: Chemin vers le fichier de configuration
            
        Returns:
            dict: Configuration de déploiement
        """
        # Configuration par défaut
        default_config = {
            "api_host": "127.0.0.1",
            "api_port": 5000,
            "dashboard_host": "127.0.0.1",
            "dashboard_port": 5001,
            "use_https": True,
            "generate_ssl_cert": True,
            "ssl_cert_path": os.path.join(self.current_dir, "ssl", "cert.pem"),
            "ssl_key_path": os.path.join(self.current_dir, "ssl", "key.pem"),
            "ssl_days_valid": 365,
            "backup_before_deploy": True,
            "backup_dir": os.path.join(self.current_dir, "backups"),
            "log_dir": os.path.join(self.current_dir, "logs"),
            "run_tests_before_deploy": True,
            "auto_restart_on_crash": True,
            "max_restart_attempts": 3,
            "restart_cooldown": 10,  # en secondes
            "environment": "production"
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
    
    async def deploy(self):
        """Déployer GBPBot en production."""
        logger.info("Démarrage du déploiement en production...")
        
        try:
            # Créer les répertoires nécessaires
            self._create_directories()
            
            # Sauvegarder les fichiers existants si nécessaire
            if self.config["backup_before_deploy"]:
                self._backup_files()
            
            # Générer les certificats SSL si nécessaire
            if self.config["use_https"] and self.config["generate_ssl_cert"]:
                self._generate_ssl_certificates()
            
            # Mettre à jour les variables d'environnement
            self._update_env_variables()
            
            # Exécuter les tests avant le déploiement si nécessaire
            if self.config["run_tests_before_deploy"]:
                await self._run_tests()
            
            # Démarrer les serveurs
            self._start_servers()
            
            # Vérifier que les serveurs sont bien démarrés
            await self._check_servers()
            
            logger.success("Déploiement en production terminé avec succès!")
            
        except Exception as e:
            logger.error(f"Erreur lors du déploiement: {str(e)}")
            # Arrêter les serveurs en cas d'erreur
            self._stop_servers()
    
    def _create_directories(self):
        """Créer les répertoires nécessaires."""
        logger.info("Création des répertoires nécessaires...")
        
        # Créer le répertoire de sauvegarde
        if self.config["backup_before_deploy"]:
            os.makedirs(self.config["backup_dir"], exist_ok=True)
        
        # Créer le répertoire de logs
        os.makedirs(self.config["log_dir"], exist_ok=True)
        
        # Créer le répertoire SSL si nécessaire
        if self.config["use_https"] and self.config["generate_ssl_cert"]:
            ssl_dir = os.path.dirname(self.config["ssl_cert_path"])
            os.makedirs(ssl_dir, exist_ok=True)
    
    def _backup_files(self):
        """Sauvegarder les fichiers existants."""
        logger.info("Sauvegarde des fichiers existants...")
        
        # Créer un répertoire de sauvegarde avec la date et l'heure actuelles
        backup_dir = os.path.join(
            self.config["backup_dir"],
            f"backup_{time.strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(backup_dir, exist_ok=True)
        
        # Fichiers à sauvegarder
        files_to_backup = [
            "*.py",
            "*.log",
            "*.json",
            "*.env",
            "*.md"
        ]
        
        # Sauvegarder les fichiers
        for pattern in files_to_backup:
            for file_path in Path(self.current_dir).glob(pattern):
                if os.path.isfile(file_path):
                    dest_path = os.path.join(backup_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
        
        logger.success(f"Sauvegarde terminée dans {backup_dir}")
    
    def _generate_ssl_certificates(self):
        """Générer les certificats SSL."""
        logger.info("Génération des certificats SSL...")
        
        # Vérifier si le script de génération de certificats existe
        ssl_script = os.path.join(self.current_dir, "generate_ssl_cert.py")
        if not os.path.exists(ssl_script):
            logger.error("Le script de génération de certificats SSL n'existe pas")
            raise FileNotFoundError("Le script de génération de certificats SSL n'existe pas")
        
        # Exécuter le script de génération de certificats
        cmd = [
            self.python_executable,
            ssl_script,
            "--output-dir", os.path.dirname(self.config["ssl_cert_path"]),
            "--days", str(self.config["ssl_days_valid"]),
            "--common-name", self.config["api_host"]
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.success("Certificats SSL générés avec succès")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de la génération des certificats SSL: {e.stderr}")
            raise
    
    def _update_env_variables(self):
        """Mettre à jour les variables d'environnement."""
        logger.info("Mise à jour des variables d'environnement...")
        
        # Charger le fichier .env existant
        env_file = os.path.join(self.current_dir, ".env")
        env_vars = {}
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # Mettre à jour les variables d'environnement pour la production
        env_vars["GBPBOT_ENVIRONMENT"] = self.config["environment"]
        env_vars["GBPBOT_API_HOST"] = self.config["api_host"]
        env_vars["GBPBOT_API_PORT"] = str(self.config["api_port"])
        env_vars["GBPBOT_DASHBOARD_HOST"] = self.config["dashboard_host"]
        env_vars["GBPBOT_DASHBOARD_PORT"] = str(self.config["dashboard_port"])
        
        if self.config["use_https"]:
            env_vars["GBPBOT_SSL_CERT"] = self.config["ssl_cert_path"]
            env_vars["GBPBOT_SSL_KEY"] = self.config["ssl_key_path"]
        
        # Sauvegarder le fichier .env
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        logger.success("Variables d'environnement mises à jour")
    
    async def _run_tests(self):
        """Exécuter les tests avant le déploiement."""
        logger.info("Exécution des tests avant le déploiement...")
        
        # Vérifier si le script de test existe
        test_script = os.path.join(self.current_dir, "production_test.py")
        if not os.path.exists(test_script):
            logger.error("Le script de test n'existe pas")
            raise FileNotFoundError("Le script de test n'existe pas")
        
        # Exécuter le script de test
        cmd = [self.python_executable, test_script]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.success("Tests exécutés avec succès")
            
            # Vérifier si les tests ont réussi
            if "Tous les tests ont réussi" not in result.stdout and "Tous les tests ont réussi" not in result.stderr:
                logger.error("Certains tests ont échoué")
                logger.error(result.stdout)
                logger.error(result.stderr)
                raise Exception("Certains tests ont échoué")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'exécution des tests: {e.stderr}")
            raise
    
    def _start_servers(self):
        """Démarrer les serveurs."""
        logger.info("Démarrage des serveurs...")
        
        # Commandes pour démarrer les serveurs
        api_cmd = [
            self.python_executable,
            os.path.join(self.current_dir, "api_server.py"),
            "--host", self.config["api_host"],
            "--port", str(self.config["api_port"])
        ]
        
        dashboard_cmd = [
            self.python_executable,
            os.path.join(self.current_dir, "web_dashboard.py"),
            "--host", self.config["dashboard_host"],
            "--port", str(self.config["dashboard_port"])
        ]
        
        # Démarrer le serveur API
        logger.info(f"Démarrage du serveur API sur {self.config['api_host']}:{self.config['api_port']}")
        api_process = subprocess.Popen(
            api_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.server_processes.append(api_process)
        
        # Attendre un peu pour s'assurer que l'API démarre avant le dashboard
        time.sleep(2)
        
        # Démarrer le serveur dashboard
        logger.info(f"Démarrage du dashboard web sur {self.config['dashboard_host']}:{self.config['dashboard_port']}")
        dashboard_process = subprocess.Popen(
            dashboard_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.server_processes.append(dashboard_process)
        
        # Attendre un peu pour s'assurer que les serveurs sont bien démarrés
        time.sleep(5)
        
        logger.success("Serveurs démarrés avec succès")
    
    async def _check_servers(self):
        """Vérifier que les serveurs sont bien démarrés."""
        logger.info("Vérification des serveurs...")
        
        # Vérifier le serveur API
        api_url = f"http{'s' if self.config['use_https'] else ''}://{self.config['api_host']}:{self.config['api_port']}/health"
        dashboard_url = f"http{'s' if self.config['use_https'] else ''}://{self.config['dashboard_host']}:{self.config['dashboard_port']}/"
        
        # Attendre que les serveurs soient prêts
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Tentative de connexion aux serveurs ({attempt}/{max_attempts})...")
            
            # Vérifier si les processus sont toujours en cours d'exécution
            for i, process in enumerate(self.server_processes):
                if process.poll() is not None:
                    server_type = "API" if i == 0 else "Dashboard"
                    logger.error(f"Le serveur {server_type} s'est arrêté de manière inattendue")
                    stdout, stderr = process.communicate()
                    logger.error(f"Sortie standard: {stdout}")
                    logger.error(f"Erreur standard: {stderr}")
                    raise Exception(f"Le serveur {server_type} s'est arrêté de manière inattendue")
            
            # Vérifier si les serveurs répondent
            try:
                # Utiliser subprocess pour éviter les problèmes de certificats auto-signés
                api_check = subprocess.run(
                    ["curl", "-s", "-k", api_url],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                dashboard_check = subprocess.run(
                    ["curl", "-s", "-k", dashboard_url],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if api_check.returncode == 0 and "status" in api_check.stdout and dashboard_check.returncode == 0:
                    logger.success("Les serveurs sont opérationnels")
                    return
            except Exception as e:
                logger.warning(f"Erreur lors de la vérification des serveurs: {str(e)}")
            
            # Attendre avant la prochaine tentative
            await asyncio.sleep(2)
        
        # Si on arrive ici, c'est que les serveurs ne répondent pas
        logger.error("Impossible de se connecter aux serveurs après plusieurs tentatives")
        self._stop_servers()
        raise Exception("Impossible de se connecter aux serveurs après plusieurs tentatives")
    
    def _stop_servers(self):
        """Arrêter les serveurs."""
        logger.info("Arrêt des serveurs...")
        
        for process in self.server_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt d'un serveur: {str(e)}")
                try:
                    process.kill()
                except:
                    pass
        
        self.server_processes = []
        logger.info("Serveurs arrêtés")
    
    def create_systemd_service(self):
        """Créer un service systemd pour démarrer GBPBot au démarrage."""
        logger.info("Création du service systemd...")
        
        # Vérifier si l'utilisateur a les droits sudo
        try:
            subprocess.run(["sudo", "-n", "true"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            logger.error("Vous devez avoir les droits sudo pour créer un service systemd")
            return False
        
        # Chemin absolu vers le script de démarrage
        start_script = os.path.abspath(os.path.join(self.current_dir, "start_servers.py"))
        
        # Contenu du fichier service
        service_content = f"""[Unit]
Description=GBPBot Trading Bot
After=network.target

[Service]
User={os.getenv('USER')}
WorkingDirectory={self.current_dir}
ExecStart={self.python_executable} {start_script}
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=gbpbot

[Install]
WantedBy=multi-user.target
"""
        
        # Écrire le fichier service
        service_file = "/tmp/gbpbot.service"
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        # Copier le fichier service dans le répertoire systemd
        try:
            subprocess.run(["sudo", "cp", service_file, "/etc/systemd/system/"], check=True)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "gbpbot"], check=True)
            
            logger.success("Service systemd créé avec succès")
            logger.info("Vous pouvez maintenant démarrer le service avec: sudo systemctl start gbpbot")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de la création du service systemd: {str(e)}")
            return False

async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Déploiement de GBPBot en production")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration de déploiement")
    parser.add_argument("--create-service", action="store_true", help="Créer un service systemd")
    args = parser.parse_args()
    
    deployer = ProductionDeployer(args.config)
    
    if args.create_service:
        deployer.create_systemd_service()
    else:
        await deployer.deploy()

if __name__ == "__main__":
    asyncio.run(main()) 