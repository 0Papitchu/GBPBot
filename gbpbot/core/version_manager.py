#!/usr/bin/env python
"""
Module de gestion des versions, des sauvegardes et des mises à jour du bot
"""

import os
import shutil
import json
import logging
import datetime
import zipfile
import asyncio
import hashlib
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class VersionManager:
    """
    Gère les versions, les sauvegardes et les mises à jour du bot
    """
    
    def __init__(self):
        """Initialise le gestionnaire de versions"""
        self.version = "1.0.0"  # Version actuelle du bot
        self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        
        # Créer les répertoires s'ils n'existent pas
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Charger l'historique des versions
        self.version_history_file = os.path.join(self.config_dir, "version_history.json")
        self.version_history = self._load_version_history()
        
        logger.info(f"VersionManager initialisé - Version actuelle: {self.version}")
    
    def _load_version_history(self) -> Dict:
        """Charge l'historique des versions depuis le fichier JSON"""
        if os.path.exists(self.version_history_file):
            try:
                with open(self.version_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'historique des versions: {str(e)}")
                return {"versions": [], "current": self.version}
        else:
            # Créer un historique par défaut
            history = {
                "versions": [
                    {
                        "version": self.version,
                        "date": datetime.datetime.now().isoformat(),
                        "changes": ["Version initiale"],
                        "status": "stable"
                    }
                ],
                "current": self.version
            }
            self._save_version_history(history)
            return history
    
    def _save_version_history(self, history: Dict) -> None:
        """Sauvegarde l'historique des versions dans le fichier JSON"""
        try:
            with open(self.version_history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'historique des versions: {str(e)}")
    
    async def prepare_update(self, new_version: str) -> bool:
        """
        Prépare une mise à jour vers une nouvelle version
        
        Args:
            new_version: Numéro de la nouvelle version
            
        Returns:
            bool: True si la préparation a réussi, False sinon
        """
        logger.info(f"Préparation de la mise à jour vers la version {new_version}")
        
        try:
            # Créer une sauvegarde avant la mise à jour
            backup_path = await self.create_backup(f"pre_update_{new_version}")
            if not backup_path:
                logger.error("Échec de la création de la sauvegarde avant la mise à jour")
                return False
            
            # Mettre à jour l'historique des versions
            self.version_history["versions"].append({
                "version": new_version,
                "date": datetime.datetime.now().isoformat(),
                "changes": ["Mise à jour automatique"],
                "status": "pending",
                "backup": backup_path
            })
            
            self._save_version_history(self.version_history)
            logger.info(f"Préparation de la mise à jour vers {new_version} terminée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation de la mise à jour: {str(e)}")
            return False
    
    async def create_backup(self, label: Optional[str] = None) -> str:
        """
        Crée une sauvegarde complète du bot
        
        Args:
            label: Étiquette optionnelle pour la sauvegarde
            
        Returns:
            str: Chemin vers le fichier de sauvegarde, ou chaîne vide en cas d'échec
        """
        try:
            # Générer un nom de fichier pour la sauvegarde
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_label = f"{label}_" if label else ""
            backup_filename = f"{backup_label}backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            logger.info(f"Création d'une sauvegarde: {backup_path}")
            
            # Répertoires à sauvegarder
            dirs_to_backup = [
                "gbpbot",
                "config",
                "data"
            ]
            
            # Fichiers à sauvegarder
            files_to_backup = [
                ".env",
                "requirements.txt",
                "setup.py",
                "config.py"
            ]
            
            # Créer l'archive ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Ajouter les répertoires
                for dir_name in dirs_to_backup:
                    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), dir_name)
                    if os.path.exists(dir_path) and os.path.isdir(dir_path):
                        for root, _, files in os.walk(dir_path):
                            for file in files:
                                if not file.endswith(('.pyc', '.pyo', '.pyd', '.so', '.dll')):
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                                    zipf.write(file_path, arcname)
                
                # Ajouter les fichiers individuels
                for file_name in files_to_backup:
                    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_name)
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        zipf.write(file_path, file_name)
            
            # Calculer le hash MD5 du fichier de sauvegarde
            md5_hash = hashlib.md5()
            with open(backup_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    md5_hash.update(byte_block)
            backup_hash = md5_hash.hexdigest()
            
            # Enregistrer les informations de la sauvegarde
            backup_info = {
                "path": backup_path,
                "timestamp": timestamp,
                "label": label,
                "hash": backup_hash,
                "size": os.path.getsize(backup_path)
            }
            
            # Mettre à jour l'historique des sauvegardes
            backup_history_file = os.path.join(self.config_dir, "backup_history.json")
            backup_history = []
            
            if os.path.exists(backup_history_file):
                try:
                    with open(backup_history_file, 'r') as f:
                        backup_history = json.load(f)
                except:
                    backup_history = []
            
            backup_history.append(backup_info)
            
            with open(backup_history_file, 'w') as f:
                json.dump(backup_history, f, indent=2)
            
            logger.info(f"Sauvegarde créée avec succès: {backup_path} ({backup_info['size'] / 1024 / 1024:.2f} Mo)")
            return backup_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la sauvegarde: {str(e)}")
            return ""
    
    async def rollback(self, backup_path: str) -> bool:
        """
        Restaure le bot à partir d'une sauvegarde
        
        Args:
            backup_path: Chemin vers le fichier de sauvegarde
            
        Returns:
            bool: True si la restauration a réussi, False sinon
        """
        logger.info(f"Restauration à partir de la sauvegarde: {backup_path}")
        
        if not os.path.exists(backup_path):
            logger.error(f"Le fichier de sauvegarde n'existe pas: {backup_path}")
            return False
        
        try:
            # Créer un répertoire temporaire pour l'extraction
            temp_dir = os.path.join(self.backup_dir, "temp_restore")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # Extraire l'archive
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Créer une sauvegarde de l'état actuel avant la restauration
            pre_rollback_backup = await self.create_backup("pre_rollback")
            if not pre_rollback_backup:
                logger.warning("Impossible de créer une sauvegarde avant la restauration")
            
            # Restaurer les fichiers
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Restaurer les répertoires
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                dest_path = os.path.join(project_root, item)
                
                if os.path.isdir(item_path):
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(item_path, dest_path)
                elif os.path.isfile(item_path):
                    shutil.copy2(item_path, dest_path)
            
            # Nettoyer le répertoire temporaire
            shutil.rmtree(temp_dir)
            
            # Mettre à jour l'historique des versions
            self.version_history = self._load_version_history()
            
            logger.info(f"Restauration terminée avec succès à partir de {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {str(e)}")
            return False
    
    def get_version_info(self) -> Dict:
        """
        Récupère les informations sur la version actuelle
        
        Returns:
            Dict: Informations sur la version
        """
        current_version = self.version_history.get("current", self.version)
        
        # Trouver les détails de la version actuelle
        version_details = None
        for version in self.version_history.get("versions", []):
            if version.get("version") == current_version:
                version_details = version
                break
        
        if not version_details:
            version_details = {
                "version": current_version,
                "date": datetime.datetime.now().isoformat(),
                "changes": ["Information non disponible"],
                "status": "unknown"
            }
        
        # Récupérer la liste des sauvegardes
        backups = []
        backup_history_file = os.path.join(self.config_dir, "backup_history.json")
        if os.path.exists(backup_history_file):
            try:
                with open(backup_history_file, 'r') as f:
                    backups = json.load(f)
            except:
                backups = []
        
        return {
            "current_version": current_version,
            "version_details": version_details,
            "available_backups": backups,
            "version_history": self.version_history.get("versions", [])
        }
    
    def list_backups(self) -> List[Dict]:
        """
        Liste toutes les sauvegardes disponibles
        
        Returns:
            List[Dict]: Liste des sauvegardes
        """
        backup_history_file = os.path.join(self.config_dir, "backup_history.json")
        if os.path.exists(backup_history_file):
            try:
                with open(backup_history_file, 'r') as f:
                    backups = json.load(f)
                
                # Vérifier que les fichiers existent toujours
                valid_backups = []
                for backup in backups:
                    if os.path.exists(backup.get("path", "")):
                        valid_backups.append(backup)
                
                return valid_backups
            except:
                return []
        return []
    
    async def verify_integrity(self) -> Dict[str, Any]:
        """
        Vérifie l'intégrité du bot
        
        Returns:
            Dict: Résultats de la vérification
        """
        results = {
            "status": "ok",
            "issues": [],
            "checked_files": 0
        }
        
        try:
            # Vérifier les fichiers Python essentiels
            essential_files = [
                "gbpbot/main.py",
                "gbpbot/core/blockchain.py",
                "gbpbot/core/price_feed.py",
                "gbpbot/strategies/arbitrage.py",
                "gbpbot/strategies/mev.py",
                "gbpbot/strategies/sniping.py"
            ]
            
            for file_path in essential_files:
                full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_path)
                if not os.path.exists(full_path):
                    results["issues"].append(f"Fichier manquant: {file_path}")
                    results["status"] = "error"
                else:
                    # Vérifier que le fichier est un fichier Python valide
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            compile(content, full_path, 'exec')
                        results["checked_files"] += 1
                    except Exception as e:
                        results["issues"].append(f"Erreur de syntaxe dans {file_path}: {str(e)}")
                        results["status"] = "error"
            
            # Vérifier les fichiers de configuration
            config_files = [".env", "config.py"]
            for file_path in config_files:
                full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_path)
                if not os.path.exists(full_path):
                    results["issues"].append(f"Fichier de configuration manquant: {file_path}")
                    results["status"] = "warning"
                else:
                    results["checked_files"] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'intégrité: {str(e)}")
            results["status"] = "error"
            results["issues"].append(f"Erreur lors de la vérification: {str(e)}")
            return results 