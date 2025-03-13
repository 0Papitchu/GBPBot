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
import traceback

# Importer les modules Telegram
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    TELEGRAM_IMPORTS_OK = True
except ImportError:
    TELEGRAM_IMPORTS_OK = False
    print("Modules Telegram non disponibles. Exécutez 'pip install python-telegram-bot'")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gbpbot.telegram.bot")

# Import des commandes
from gbpbot.telegram.commands import register_all_commands

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
    
    def __init__(self, token: Optional[str] = None, config: Optional[Dict[str, Any]] = None, bot_state: Optional[Any] = None):
        """
        Initialise le bot Telegram.
        
        Args:
            token: Token du bot Telegram
            config: Configuration du bot
            bot_state: État du bot (partagé avec le GBPBot principal)
        """
        self.token = token
        self.config = config or {}
        self.bot_state = bot_state
        self.application = None
        self.authorized_users: List[int] = self._load_authorized_users()
        self.is_running = False
        self._last_message_time: Dict[int, float] = {}
        
        # Charger la configuration
        self._load_config()
        
        # Configurer le logging
        self.logger = logging.getLogger("gbpbot.telegram.bot")
        
        # Vérifier si les modules Telegram sont disponibles
        if not TELEGRAM_IMPORTS_OK:
            self.logger.error("Modules Telegram non disponibles. Bot Telegram désactivé.")
            return
            
        self.logger.info("Bot Telegram initialisé avec succès.")
    
    def _load_config(self) -> None:
        """Charge la configuration du bot."""
        # Charger la configuration depuis l'environnement ou le fichier de config
        if not self.token:
            self.token = os.environ.get("TELEGRAM_BOT_TOKEN", self.config.get("token"))
        
        # Vérifier si le token est disponible
        if not self.token:
            self.logger.warning("Token Telegram non configuré. Bot Telegram désactivé.")
    
    def _load_authorized_users(self) -> List[int]:
        """
        Charge la liste des utilisateurs autorisés à utiliser le bot.
        
        Returns:
            Liste des IDs utilisateurs autorisés
        """
        # Essayer de charger depuis l'environnement
        auth_users_str = os.environ.get("TELEGRAM_AUTHORIZED_USERS", "")
        
        # Si pas disponible dans l'environnement, vérifier la configuration
        if not auth_users_str and self.config and "authorized_users" in self.config:
            auth_users = self.config["authorized_users"]
            if isinstance(auth_users, list):
                return [int(user_id) for user_id in auth_users if str(user_id).isdigit()]
            auth_users_str = str(auth_users)
        
        # Convertir la chaîne en liste d'entiers
        if auth_users_str:
            return [int(user_id.strip()) for user_id in auth_users_str.split(",") if user_id.strip().isdigit()]
        
        # Valeur par défaut si aucun utilisateur autorisé n'est configuré
        self.logger.warning("Aucun utilisateur autorisé configuré. L'accès sera restreint.")
        return []
    
    def _is_user_authorized(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur est autorisé à utiliser le bot.
        
        Args:
            user_id: ID de l'utilisateur Telegram
            
        Returns:
            True si l'utilisateur est autorisé, False sinon
        """
        # Si aucun utilisateur autorisé n'est configuré, autoriser tous les utilisateurs
        if not self.authorized_users:
            self.logger.warning(f"Accès accordé à l'utilisateur {user_id} (aucune restriction configurée)")
            return True
        
        is_authorized = user_id in self.authorized_users
        if not is_authorized:
            self.logger.warning(f"Tentative d'accès non autorisé de l'utilisateur {user_id}")
        
        return is_authorized
    
    async def start(self) -> None:
        """Démarre le bot Telegram."""
        if not TELEGRAM_IMPORTS_OK:
            self.logger.error("Modules Telegram non disponibles. Bot Telegram non démarré.")
            return
        
        if not self.token:
            self.logger.error("Token Telegram non configuré. Bot Telegram non démarré.")
            return
        
        try:
            # Initialiser l'application
            self.application = Application.builder().token(self.token).build()
            
            # Initialiser les gestionnaires de commandes
            self._setup_handlers()
            
            # Stocker une référence au bot et à l'état dans les données de l'application
            self.application.bot_data["bot"] = self
            self.application.bot_data["bot_state"] = self.bot_state
            
            # Démarrer le polling en arrière-plan
            self.application.run_polling(close_loop=False)
            
            self.is_running = True
            self.logger.info("Bot Telegram démarré avec succès.")
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du bot Telegram: {str(e)}")
            traceback.print_exc()
    
    async def stop(self) -> None:
        """Arrête le bot Telegram."""
        if self.is_running and self.application:
            try:
                self.logger.info("Arrêt du bot Telegram...")
                await self.application.stop()
                self.is_running = False
                self.logger.info("Bot Telegram arrêté avec succès.")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'arrêt du bot Telegram: {str(e)}")
                traceback.print_exc()
    
    def _setup_handlers(self) -> None:
        """Configure les gestionnaires de commandes pour le bot."""
        if not self.application:
            return
        
        # Enregistrer toutes les commandes
        register_all_commands(self.application)
    
    async def send_notification(self, message: str, chat_id: Optional[int] = None, parse_mode: str = "HTML", 
                               disable_web_page_preview: bool = True, rate_limit: int = 0) -> None:
        """
        Envoie une notification à un chat spécifique ou à tous les utilisateurs autorisés.
        
        Args:
            message: Message à envoyer
            chat_id: ID du chat (si None, envoie à tous les utilisateurs autorisés)
            parse_mode: Mode de formatage du message
            disable_web_page_preview: Désactiver la prévisualisation des liens
            rate_limit: Limite de temps (en secondes) entre les messages au même chat
        """
        if not self.is_running or not self.application:
            self.logger.error("Bot Telegram non démarré. Impossible d'envoyer des notifications.")
            return
        
        try:
            # Si chat_id est spécifié, envoyer uniquement à ce chat
            if chat_id is not None:
                # Vérifier le rate limiting
                if rate_limit > 0 and chat_id in self._last_message_time:
                    time_since_last = time.time() - self._last_message_time[chat_id]
                    if time_since_last < rate_limit:
                        self.logger.debug(f"Message à {chat_id} limité par rate limit ({time_since_last:.1f}s < {rate_limit}s)")
                        return
                
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview
                )
                self._last_message_time[chat_id] = time.time()
                self.logger.debug(f"Notification envoyée à {chat_id}")
            
            # Sinon, envoyer à tous les utilisateurs autorisés
            else:
                for user_id in self.authorized_users:
                    # Vérifier le rate limiting
                    if rate_limit > 0 and user_id in self._last_message_time:
                        time_since_last = time.time() - self._last_message_time[user_id]
                        if time_since_last < rate_limit:
                            self.logger.debug(f"Message à {user_id} limité par rate limit ({time_since_last:.1f}s < {rate_limit}s)")
                            continue
                    
                    try:
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode=parse_mode,
                            disable_web_page_preview=disable_web_page_preview
                        )
                        self._last_message_time[user_id] = time.time()
                        self.logger.debug(f"Notification envoyée à {user_id}")
                    except Exception as e:
                        self.logger.error(f"Erreur lors de l'envoi de notification à {user_id}: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi de notification: {str(e)}")
            traceback.print_exc()
    
    async def send_alert(self, message: str, urgency: str = "normal", chat_id: Optional[int] = None) -> None:
        """
        Envoie une alerte avec un niveau d'urgence spécifique.
        
        Args:
            message: Message d'alerte
            urgency: Niveau d'urgence ("low", "normal", "high", "critical")
            chat_id: ID du chat (si None, envoie à tous les utilisateurs autorisés)
        """
        # Ajouter un emoji selon le niveau d'urgence
        urgency_emoji = {
            "low": "ℹ️",
            "normal": "⚠️",
            "high": "🚨",
            "critical": "🔴"
        }.get(urgency.lower(), "⚠️")
        
        # Formater le message avec le niveau d'urgence
        formatted_message = f"{urgency_emoji} <b>Alerte {urgency.title()}</b>\n\n{message}"
        
        # Rate limit selon le niveau d'urgence (pour éviter le spam)
        rate_limits = {
            "low": 300,  # 5 minutes
            "normal": 120,  # 2 minutes
            "high": 60,  # 1 minute
            "critical": 0  # Pas de limite
        }
        
        await self.send_notification(
            message=formatted_message,
            chat_id=chat_id,
            parse_mode="HTML",
            rate_limit=rate_limits.get(urgency.lower(), 120)
        )
    
    async def send_profit_notification(self, profit_data: Dict[str, Any], chat_id: Optional[int] = None) -> None:
        """
        Envoie une notification de profit.
        
        Args:
            profit_data: Données du profit réalisé
            chat_id: ID du chat (si None, envoie à tous les utilisateurs autorisés)
        """
        # Extraire les données de profit
        token_name = profit_data.get("token_name", "Unknown")
        token_symbol = profit_data.get("token_symbol", "???")
        profit_amount = profit_data.get("profit_amount", 0)
        profit_percentage = profit_data.get("profit_percentage", 0)
        currency = profit_data.get("currency", "USD")
        strategy = profit_data.get("strategy", "trading")
        
        # Emoji selon le profit (positif ou négatif)
        emoji = "🟢" if profit_amount > 0 else "🔴"
        
        # Formater le message
        message = (
            f"{emoji} <b>Profit {strategy.title()}</b>\n\n"
            f"<b>Token:</b> {token_name} ({token_symbol})\n"
            f"<b>Profit:</b> {profit_amount:+.4f} {currency} ({profit_percentage:+.2f}%)\n"
            f"<b>Stratégie:</b> {strategy.title()}\n"
            f"<b>Date:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
        
        # Envoyer la notification avec un rate limit de 30 secondes
        await self.send_notification(
            message=message,
            chat_id=chat_id,
            parse_mode="HTML",
            rate_limit=30
        )
    
    async def send_status_update(self, status_data: Dict[str, Any], chat_id: Optional[int] = None) -> None:
        """
        Envoie une mise à jour de statut périodique.
        
        Args:
            status_data: Données de statut du bot
            chat_id: ID du chat (si None, envoie à tous les utilisateurs autorisés)
        """
        # Extraire les données de statut
        uptime = status_data.get("uptime", "N/A")
        active_strategies = status_data.get("active_strategies", [])
        wallet_balances = status_data.get("wallet_balances", {})
        performance_24h = status_data.get("performance_24h", 0)
        total_trades = status_data.get("total_trades", 0)
        
        # Emoji selon la performance sur 24h
        performance_emoji = "🟢" if performance_24h > 0 else "🔴" if performance_24h < 0 else "⚪"
        
        # Formater le message
        message = (
            "📊 <b>Statut GBPBot</b>\n\n"
            f"⏱️ <b>Uptime:</b> {uptime}\n"
            f"{performance_emoji} <b>Performance 24h:</b> {performance_24h:+.2f}%\n"
            f"📈 <b>Trades Total:</b> {total_trades}\n\n"
        )
        
        # Ajouter les stratégies actives
        if active_strategies:
            message += "<b>Stratégies Actives:</b>\n"
            for strategy in active_strategies:
                message += f"• {strategy['name']} - {strategy.get('status', 'En cours')}\n"
        else:
            message += "<i>Aucune stratégie active</i>\n"
        
        # Ajouter les soldes des wallets
        if wallet_balances:
            message += "\n<b>Soldes Wallets:</b>\n"
            for chain, balance in wallet_balances.items():
                message += f"• {chain.title()}: {balance} $\n"
        
        # Ajouter la date et heure
        message += f"\n<i>Mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
        
        # Envoyer la notification avec un rate limit élevé (pour les mises à jour périodiques)
        await self.send_notification(
            message=message,
            chat_id=chat_id,
            parse_mode="HTML",
            rate_limit=600  # 10 minutes
        )

# Fonction pour créer une instance du bot Telegram
def create_telegram_bot(token: Optional[str] = None, config: Optional[Dict[str, Any]] = None, bot_state: Optional[Any] = None) -> TelegramBot:
    """
    Crée et configure une instance du bot Telegram.
    
    Args:
        token: Token du bot Telegram
        config: Configuration du bot
        bot_state: État du bot (partagé avec le GBPBot principal)
        
    Returns:
        Instance de TelegramBot configurée
    """
    return TelegramBot(token=token, config=config, bot_state=bot_state) 