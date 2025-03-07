"""
Module principal du Bot Telegram pour GBPBot
============================================

Ce module implémente la classe TelegramBot qui gère l'interaction avec
l'API Telegram pour contrôler le GBPBot à distance.
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import json
import threading

# Importer les modules Telegram
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext
    TELEGRAM_IMPORTS_OK = True
except ImportError:
    TELEGRAM_IMPORTS_OK = False
    print("Modules Telegram non disponibles. Exécutez 'pip install python-telegram-bot'")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gbpbot.telegram.bot")

# Import des commandes
from gbpbot.telegram.commands.base import register_command_handlers
from gbpbot.telegram.commands.status import status_command
from gbpbot.telegram.commands.strategy import start_strategy_command, stop_strategy_command
from gbpbot.telegram.commands.analyze import analyze_market_command, analyze_token_command
from gbpbot.telegram.commands.backtesting import run_backtest_command

class TelegramBot:
    """
    Bot Telegram qui permet de contrôler GBPBot à distance.
    
    Fournit des commandes pour:
    - Démarrer/arrêter les stratégies
    - Monitorer les performances
    - Recevoir des alertes
    - Analyser le marché et les tokens
    - Exécuter des backtests
    """
    
    def __init__(self, token: str = None, config: Dict = None, bot_state: Any = None):
        """
        Initialise le bot Telegram.
        
        Args:
            token (str, optional): Token du bot Telegram. Si non fourni, sera lu depuis l'environnement.
            config (Dict, optional): Configuration du bot.
            bot_state (Any, optional): État global du GBPBot.
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.config = config or {}
        self.bot_state = bot_state
        self.application = None
        self.thread = None
        self.running = False
        self.authorized_users = []
        self.chat_ids = []
        
        # Vérifier que les modules Telegram sont disponibles
        if not TELEGRAM_IMPORTS_OK:
            logger.error("Les modules Telegram ne sont pas disponibles. Le bot ne peut pas être démarré.")
            return
            
        # Charger les utilisateurs autorisés
        self._load_authorized_users()
        
        logger.info("Bot Telegram initialisé avec succès.")
        
    def _load_authorized_users(self) -> None:
        """Charge la liste des utilisateurs autorisés à utiliser le bot."""
        # Utilisateurs spécifiés dans la configuration
        users = self.config.get("telegram_authorized_users", [])
        if isinstance(users, str):
            # Si c'est une chaîne, la diviser par des virgules
            users = [u.strip() for u in users.split(",") if u.strip()]
            
        # Ajouter les utilisateurs de l'environnement
        env_users = os.environ.get("TELEGRAM_AUTHORIZED_USERS", "")
        if env_users:
            users.extend([u.strip() for u in env_users.split(",") if u.strip()])
            
        # Convertir en entiers
        self.authorized_users = [int(user) for user in users if user.isdigit()]
        logger.info(f"Utilisateurs autorisés chargés: {len(self.authorized_users)}")
        
    def _is_user_authorized(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur est autorisé à utiliser le bot.
        
        Args:
            user_id (int): ID de l'utilisateur Telegram.
            
        Returns:
            bool: True si l'utilisateur est autorisé, False sinon.
        """
        # Si aucun utilisateur autorisé n'est défini, autoriser tout le monde
        if not self.authorized_users:
            return True
            
        return user_id in self.authorized_users
        
    async def start(self) -> bool:
        """
        Démarre le bot Telegram.
        
        Returns:
            bool: True si le bot a démarré avec succès, False sinon.
        """
        if not TELEGRAM_IMPORTS_OK:
            logger.error("Les modules Telegram ne sont pas disponibles. Le bot ne peut pas être démarré.")
            return False
            
        if not self.token:
            logger.error("Aucun token Telegram fourni. Le bot ne peut pas être démarré.")
            return False
            
        if self.running:
            logger.warning("Le bot Telegram est déjà en cours d'exécution.")
            return True
            
        try:
            # Initialiser l'application
            self.application = Application.builder().token(self.token).build()
            
            # Enregistrer les gestionnaires de commandes
            register_command_handlers(self)
            
            # Démarrer le bot dans un thread séparé
            self.thread = threading.Thread(target=self._run_bot, daemon=True)
            self.thread.start()
            
            self.running = True
            logger.info("Bot Telegram démarré avec succès.")
            return True
        except Exception as e:
            logger.exception(f"Erreur lors du démarrage du bot Telegram: {str(e)}")
            return False
            
    def _run_bot(self) -> None:
        """Exécute le bot Telegram dans un thread séparé."""
        try:
            # Créer une nouvelle boucle d'événements pour ce thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Démarrer l'application
            self.application.run_polling()
        except Exception as e:
            logger.exception(f"Erreur lors de l'exécution du bot Telegram: {str(e)}")
            
    async def stop(self) -> bool:
        """
        Arrête le bot Telegram.
        
        Returns:
            bool: True si le bot a été arrêté avec succès, False sinon.
        """
        if not self.running:
            logger.warning("Le bot Telegram n'est pas en cours d'exécution.")
            return True
            
        try:
            # Arrêter l'application
            if self.application:
                await self.application.stop()
                self.application = None
                
            # Attendre que le thread se termine
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
                
            self.running = False
            logger.info("Bot Telegram arrêté avec succès.")
            return True
        except Exception as e:
            logger.exception(f"Erreur lors de l'arrêt du bot Telegram: {str(e)}")
            return False
            
    async def send_message(self, message: str, parse_mode: str = "HTML", reply_markup: Any = None) -> bool:
        """
        Envoie un message à tous les chats enregistrés.
        
        Args:
            message (str): Message à envoyer.
            parse_mode (str, optional): Mode d'analyse du message. Par défaut "HTML".
            reply_markup (Any, optional): Markup de réponse (boutons, etc.)
            
        Returns:
            bool: True si le message a été envoyé avec succès, False sinon.
        """
        if not self.running or not self.application:
            logger.warning("Le bot Telegram n'est pas en cours d'exécution. Message non envoyé.")
            return False
            
        if not self.chat_ids:
            logger.warning("Aucun chat enregistré. Message non envoyé.")
            return False
            
        try:
            for chat_id in self.chat_ids:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            return True
        except Exception as e:
            logger.exception(f"Erreur lors de l'envoi du message: {str(e)}")
            return False
            
    async def send_alert(self, alert_type: str, alert_data: Dict) -> bool:
        """
        Envoie une alerte formatée aux utilisateurs.
        
        Args:
            alert_type (str): Type d'alerte ("profit", "error", "security", etc.)
            alert_data (Dict): Données de l'alerte.
            
        Returns:
            bool: True si l'alerte a été envoyée avec succès, False sinon.
        """
        if not self.running:
            logger.warning("Le bot Telegram n'est pas en cours d'exécution. Alerte non envoyée.")
            return False
            
        # Formater l'alerte en fonction de son type
        message = ""
        if alert_type == "profit":
            profit = alert_data.get("profit", 0)
            token = alert_data.get("token", "Unknown")
            strategy = alert_data.get("strategy", "Unknown")
            
            emoji = "🟢" if profit > 0 else "🔴"
            message = (
                f"{emoji} <b>Alerte Profit</b> {emoji}\n\n"
                f"<b>Token:</b> {token}\n"
                f"<b>Stratégie:</b> {strategy}\n"
                f"<b>Profit:</b> {profit:.2f} USD\n"
                f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif alert_type == "error":
            error = alert_data.get("error", "Unknown error")
            module = alert_data.get("module", "Unknown")
            
            message = (
                f"🔴 <b>Alerte Erreur</b> 🔴\n\n"
                f"<b>Module:</b> {module}\n"
                f"<b>Erreur:</b> {error}\n"
                f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif alert_type == "security":
            threat = alert_data.get("threat", "Unknown threat")
            token = alert_data.get("token", "Unknown")
            
            message = (
                f"⚠️ <b>Alerte Sécurité</b> ⚠️\n\n"
                f"<b>Token:</b> {token}\n"
                f"<b>Menace:</b> {threat}\n"
                f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            # Format générique pour les autres types d'alertes
            message = f"<b>Alerte {alert_type}</b>\n\n"
            for key, value in alert_data.items():
                message += f"<b>{key}:</b> {value}\n"
            message += f"<b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        return await self.send_message(message)

    def add_chat_id(self, chat_id: int) -> None:
        """
        Ajoute un ID de chat à la liste des chats pour les notifications.
        
        Args:
            chat_id (int): ID du chat à ajouter.
        """
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            logger.info(f"Chat ID {chat_id} ajouté à la liste des notifications.")
            
    def remove_chat_id(self, chat_id: int) -> None:
        """
        Supprime un ID de chat de la liste des chats pour les notifications.
        
        Args:
            chat_id (int): ID du chat à supprimer.
        """
        if chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)
            logger.info(f"Chat ID {chat_id} supprimé de la liste des notifications.")
            
    def _format_duration(self, seconds: float) -> str:
        """
        Formate une durée en secondes en une chaîne lisible.
        
        Args:
            seconds (float): Durée en secondes.
            
        Returns:
            str: Chaîne formatée.
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = seconds / 86400
            return f"{days:.1f}j"
            
def create_telegram_bot(token: str = None, config: Dict = None, bot_state: Any = None) -> TelegramBot:
    """
    Crée et initialise un bot Telegram pour GBPBot.
    
    Args:
        token (str, optional): Token du bot Telegram.
        config (Dict, optional): Configuration du bot.
        bot_state (Any, optional): État global du GBPBot.
        
    Returns:
        TelegramBot: Instance du bot Telegram.
    """
    bot = TelegramBot(token=token, config=config, bot_state=bot_state)
    return bot 