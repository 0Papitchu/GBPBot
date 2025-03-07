#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Notifications pour GBPBot
========================================

Ce module fournit des fonctionnalités pour envoyer des notifications
via différents canaux (console, Telegram, etc.).
"""

import os
import logging
import json
import datetime
from typing import Dict, List, Any, Optional, Union, Literal
import asyncio
from pathlib import Path

from gbpbot.config.config_manager import config_manager

# Configuration du logger
logger = logging.getLogger("gbpbot.utils.notification_manager")

# Types de notification
NotificationType = Literal["info", "warning", "error", "success", "trade"]

class NotificationManager:
    """
    Gestionnaire de notifications pour GBPBot.
    
    Cette classe fournit des méthodes pour envoyer des notifications
    via différents canaux (console, Telegram, etc.).
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire de notifications.
        """
        logger.info("Initialisation du gestionnaire de notifications")
        
        # Charger la configuration
        self.config = config_manager.get_config().get("notifications", {})
        
        # Vérifier les canaux activés
        self.console_enabled = self.config.get("console", {}).get("enabled", True)
        self.telegram_enabled = self.config.get("telegram", {}).get("enabled", False)
        self.file_enabled = self.config.get("file", {}).get("enabled", True)
        
        # Configuration Telegram
        self.telegram_token = self.config.get("telegram", {}).get("token", "")
        self.telegram_chat_id = self.config.get("telegram", {}).get("chat_id", "")
        self.telegram_client = None
        
        # Fichier de log des notifications
        self.notification_log_file = self.config.get("file", {}).get("path", "logs/notifications.log")
        
        # Statistiques
        self.stats = {
            "total_notifications": 0,
            "by_type": {
                "info": 0,
                "warning": 0,
                "error": 0,
                "success": 0,
                "trade": 0
            },
            "by_channel": {
                "console": 0,
                "telegram": 0,
                "file": 0
            }
        }
        
        # Initialiser les canaux
        self._init_channels()
        
        logger.info("Gestionnaire de notifications initialisé")
    
    def _init_channels(self):
        """
        Initialise les canaux de notification.
        """
        # Initialiser le client Telegram si activé
        if self.telegram_enabled:
            try:
                self._init_telegram()
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de Telegram: {str(e)}")
                self.telegram_enabled = False
        
        # Initialiser le fichier de log si activé
        if self.file_enabled:
            try:
                self._init_log_file()
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du fichier de log: {str(e)}")
                self.file_enabled = False
    
    def _init_telegram(self):
        """
        Initialise le client Telegram.
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Token ou chat ID Telegram non configuré")
            self.telegram_enabled = False
            return
        
        try:
            # Tentative d'import de la bibliothèque Telegram
            import telegram
            
            # Créer le client Telegram
            self.telegram_client = telegram.Bot(token=self.telegram_token)
            
            logger.info("Client Telegram initialisé")
            
        except ImportError:
            logger.warning("Module telegram non disponible. Installez-le avec 'pip install python-telegram-bot'")
            self.telegram_enabled = False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Telegram: {str(e)}")
            self.telegram_enabled = False
    
    def _init_log_file(self):
        """
        Initialise le fichier de log des notifications.
        """
        # Créer le répertoire de logs si nécessaire
        Path(os.path.dirname(self.notification_log_file)).mkdir(parents=True, exist_ok=True)
        
        # Vérifier si le fichier est accessible en écriture
        try:
            with open(self.notification_log_file, "a") as f:
                pass
            
            logger.info(f"Fichier de log des notifications initialisé: {self.notification_log_file}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du fichier de log: {str(e)}")
            self.file_enabled = False
    
    def send_notification(
        self, 
        notification_type: NotificationType, 
        title: str, 
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None
    ):
        """
        Envoie une notification via les canaux configurés.
        
        Args:
            notification_type: Type de notification (info, warning, error, success, trade)
            title: Titre de la notification
            message: Message de la notification
            data: Données supplémentaires (optionnel)
            channels: Canaux spécifiques à utiliser (optionnel, tous par défaut)
        """
        # Mettre à jour les statistiques
        self.stats["total_notifications"] += 1
        self.stats["by_type"][notification_type] += 1
        
        # Préparer la notification
        notification = {
            "type": notification_type,
            "title": title,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": data or {}
        }
        
        # Déterminer les canaux à utiliser
        if channels is None:
            channels = []
            if self.console_enabled:
                channels.append("console")
            if self.telegram_enabled:
                channels.append("telegram")
            if self.file_enabled:
                channels.append("file")
        
        # Envoyer la notification sur chaque canal
        for channel in channels:
            try:
                if channel == "console":
                    self._send_to_console(notification)
                    self.stats["by_channel"]["console"] += 1
                elif channel == "telegram":
                    asyncio.create_task(self._send_to_telegram(notification))
                    self.stats["by_channel"]["telegram"] += 1
                elif channel == "file":
                    self._send_to_file(notification)
                    self.stats["by_channel"]["file"] += 1
                else:
                    logger.warning(f"Canal de notification inconnu: {channel}")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de la notification via {channel}: {str(e)}")
    
    def _send_to_console(self, notification: Dict[str, Any]):
        """
        Envoie une notification à la console.
        
        Args:
            notification: Notification à envoyer
        """
        # Formatage selon le type
        if notification["type"] == "info":
            color = "\033[94m"  # Bleu
        elif notification["type"] == "warning":
            color = "\033[93m"  # Jaune
        elif notification["type"] == "error":
            color = "\033[91m"  # Rouge
        elif notification["type"] == "success":
            color = "\033[92m"  # Vert
        elif notification["type"] == "trade":
            color = "\033[95m"  # Violet
        else:
            color = "\033[0m"   # Défaut
        
        reset = "\033[0m"
        bold = "\033[1m"
        
        # Formater le message
        console_message = f"{color}{bold}[{notification['type'].upper()}] {notification['title']}{reset}: {notification['message']}"
        
        # Afficher le message
        print(console_message)
        
        # Afficher les données si présentes et en mode verbose
        if self.config.get("console", {}).get("verbose", False) and notification["data"]:
            print(f"  Données: {json.dumps(notification['data'], indent=2)}")
    
    async def _send_to_telegram(self, notification: Dict[str, Any]):
        """
        Envoie une notification via Telegram.
        
        Args:
            notification: Notification à envoyer
        """
        if not self.telegram_enabled or not self.telegram_client:
            logger.warning("Telegram non configuré ou désactivé")
            return
        
        try:
            # Formater le message
            emoji = self._get_type_emoji(notification["type"])
            message = f"{emoji} *{notification['title']}*\n{notification['message']}"
            
            # Ajouter les données si présentes
            if notification["data"] and self.config.get("telegram", {}).get("include_data", True):
                data_str = json.dumps(notification["data"], indent=2)
                message += f"\n```\n{data_str}\n```"
            
            # Envoyer le message
            await self.telegram_client.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.debug("Notification Telegram envoyée")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi via Telegram: {str(e)}")
    
    def _send_to_file(self, notification: Dict[str, Any]):
        """
        Envoie une notification au fichier de log.
        
        Args:
            notification: Notification à envoyer
        """
        if not self.file_enabled:
            logger.warning("Fichier de log désactivé")
            return
        
        try:
            # Formater la notification en JSON
            notification_json = json.dumps(notification)
            
            # Écrire dans le fichier
            with open(self.notification_log_file, "a") as f:
                f.write(f"{notification_json}\n")
            
            logger.debug("Notification écrite dans le fichier de log")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture dans le fichier de log: {str(e)}")
    
    def _get_type_emoji(self, notification_type: str) -> str:
        """
        Retourne l'emoji correspondant au type de notification.
        
        Args:
            notification_type: Type de notification
            
        Returns:
            Emoji correspondant
        """
        if notification_type == "info":
            return "ℹ️"
        elif notification_type == "warning":
            return "⚠️"
        elif notification_type == "error":
            return "❌"
        elif notification_type == "success":
            return "✅"
        elif notification_type == "trade":
            return "💰"
        else:
            return "🔔"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques des notifications.
        
        Returns:
            Statistiques des notifications
        """
        return self.stats

# Singleton
_notification_manager_instance = None

def get_notification_manager() -> NotificationManager:
    """
    Récupère l'instance unique du gestionnaire de notifications.
    
    Returns:
        Instance du gestionnaire de notifications
    """
    global _notification_manager_instance
    
    if _notification_manager_instance is None:
        _notification_manager_instance = NotificationManager()
    
    return _notification_manager_instance

def send_notification(
    notification_type: NotificationType, 
    title: str, 
    message: str,
    data: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None
):
    """
    Fonction utilitaire pour envoyer une notification.
    
    Args:
        notification_type: Type de notification (info, warning, error, success, trade)
        title: Titre de la notification
        message: Message de la notification
        data: Données supplémentaires (optionnel)
        channels: Canaux spécifiques à utiliser (optionnel, tous par défaut)
    """
    manager = get_notification_manager()
    manager.send_notification(notification_type, title, message, data, channels) 