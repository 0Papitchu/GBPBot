"""
Module Telegram pour GBPBot
===========================

Ce module permet d'interagir avec le GBPBot via Telegram, offrant une interface
pour contrôler et surveiller toutes les fonctionnalités du bot à distance.

Il fournit une structure modulaire avec différentes commandes pour:
- Démarrer/arrêter les stratégies de trading
- Surveiller les performances et statuts
- Recevoir des alertes et notifications
- Effectuer des analyses de marché et de tokens
- Gérer le backtesting et les simulations
"""

import logging
from typing import Dict, Any

# Import des modules de commandes
from gbpbot.telegram.commands import (
    start,
    help,
    status,
    balance,
    trading,
    settings,
    arbitrage,
    sniping,
    backtesting,
    ai_assistant,
    auto_optimization,  # Module d'automatisation intelligente
)

logger = logging.getLogger(__name__)

def setup_telegram_bot(bot_context: Dict[str, Any], token: str) -> None:
    """
    Configure et démarre le bot Telegram.
    
    Args:
        bot_context: Le contexte du bot contenant toutes les références aux composants
        token: Le token d'API Telegram
    """
    from telegram.ext import ApplicationBuilder
    
    # Création de l'application
    application = ApplicationBuilder().token(token).build()
    
    # Stocker le contexte du bot
    application.bot_data['bot_context'] = bot_context
    
    # Enregistrement des gestionnaires de commandes
    start.register_handlers(application)
    help.register_handlers(application)
    status.register_handlers(application)
    balance.register_handlers(application)
    trading.register_handlers(application)
    settings.register_handlers(application)
    arbitrage.register_handlers(application)
    sniping.register_handlers(application)
    backtesting.register_handlers(application)
    ai_assistant.register_handlers(application)
    auto_optimization.register_handlers(application)  # Enregistrer les handlers d'automatisation
    
    logger.info("Bot Telegram configuré et démarré")
    
    # Démarrer le bot
    application.run_polling()

def send_notification(bot_context: Dict[str, Any], message: str, keyboard=None) -> None:
    """
    Envoie une notification à tous les utilisateurs autorisés.
    
    Args:
        bot_context: Le contexte du bot
        message: Le message à envoyer
        keyboard: Clavier optionnel à joindre au message
    """
    from telegram import Bot
    
    config = bot_context.get('config', {}).get('telegram', {})
    token = config.get('token')
    allowed_users = config.get('allowed_users', [])
    
    if not token:
        logger.error("Token Telegram manquant, impossible d'envoyer des notifications")
        return
    
    try:
        bot = Bot(token=token)
        
        for user_id in allowed_users:
            try:
                bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                logger.debug(f"Notification envoyée à l'utilisateur {user_id}")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de notification à l'utilisateur {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du bot pour les notifications: {e}")

__all__ = ['setup_telegram_bot', 'send_notification'] 