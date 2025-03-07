#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion des messages pour le bot Telegram GBPBot.

Ce module fournit des fonctions utilitaires pour envoyer, éditer et formater 
des messages dans Telegram.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

# Import conditionnel pour gérer les cas où Telegram n'est pas installé
try:
    from telegram import (
        Update, Message, InlineKeyboardMarkup, ParseMode, 
        ReplyKeyboardMarkup, ReplyKeyboardRemove
    )
    from telegram.ext import CallbackContext
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("Module python-telegram-bot non disponible")
    TELEGRAM_AVAILABLE = False
    # Créer des types substituts pour permettre au code de fonctionner sans dépendance
    class Update:
        pass
    class Message:
        pass
    class InlineKeyboardMarkup:
        pass
    class ParseMode:
        MARKDOWN = "Markdown"
        HTML = "HTML"
    class ReplyKeyboardMarkup:
        pass
    class ReplyKeyboardRemove:
        pass
    class CallbackContext:
        pass
    class TelegramError(Exception):
        pass

# Configuration du logger
logger = logging.getLogger("gbpbot.telegram.messages")

# Constantes pour les émojis fréquemment utilisés
EMOJI = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "rocket": "🚀",
    "money": "💰",
    "chart": "📊",
    "alert": "🔔",
    "lock": "🔒",
    "unlock": "🔓",
    "settings": "⚙️",
    "star": "⭐",
    "clock": "⏰",
    "fire": "🔥",
    "stop": "🛑",
    "loading": "⏳",
    "ok": "👍",
    "nok": "👎",
}

async def send_message(
    update: Update, 
    context: CallbackContext, 
    text: str, 
    keyboard: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]] = None, 
    parse_mode: str = ParseMode.MARKDOWN,
    silent: bool = False
) -> Optional[Message]:
    """
    Envoie un message à l'utilisateur.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        text: Texte du message
        keyboard: Clavier optionnel (inline ou reply)
        parse_mode: Mode d'analyse du texte (Markdown ou HTML)
        silent: Si True, envoie le message en mode silencieux (sans notification)
        
    Returns:
        L'objet Message envoyé ou None en cas d'erreur
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative d'envoi de message sans dépendance Telegram")
        return None
        
    try:
        # Déterminer le chat_id selon le contexte
        if hasattr(update, 'callback_query') and update.callback_query:
            chat_id = update.callback_query.message.chat_id
            # Réponse à un callback query
            await update.callback_query.answer()
            return await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                disable_notification=silent
            )
        elif hasattr(update, 'message') and update.message:
            # Réponse à un message
            return await update.message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                disable_notification=silent
            )
        elif hasattr(update, 'effective_chat') and update.effective_chat:
            # Cas où nous n'avons que le chat
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                disable_notification=silent
            )
        else:
            logger.error("Impossible de déterminer le destinataire du message")
            return None
    except TelegramError as e:
        logger.error(f"Erreur Telegram lors de l'envoi du message: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message: {e}")
        return None


async def edit_message(
    update: Update, 
    context: CallbackContext, 
    text: str, 
    keyboard: Optional[InlineKeyboardMarkup] = None, 
    parse_mode: str = ParseMode.MARKDOWN,
    message_id: Optional[int] = None
) -> Optional[Message]:
    """
    Modifie un message existant.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        text: Nouveau texte du message
        keyboard: Nouveau clavier optionnel
        parse_mode: Mode d'analyse du texte (Markdown ou HTML)
        message_id: ID optionnel du message à modifier (si non fourni, utilise le message du callback)
        
    Returns:
        L'objet Message modifié ou None en cas d'erreur
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de modification de message sans dépendance Telegram")
        return None
        
    try:
        # Cas d'un callback query
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer()
            return await update.callback_query.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        # Cas où un ID de message est fourni
        elif message_id and hasattr(update, 'effective_chat') and update.effective_chat:
            return await context.bot.edit_message_text(
                text=text,
                chat_id=update.effective_chat.id,
                message_id=message_id,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        else:
            logger.error("Impossible de déterminer le message à modifier")
            return None
    except TelegramError as e:
        # Si le message n'a pas changé, Telegram renvoie une erreur
        if "message is not modified" in str(e).lower():
            logger.debug("Le message n'a pas été modifié (contenu identique)")
            return None
        logger.error(f"Erreur Telegram lors de la modification du message: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la modification du message: {e}")
        return None


async def delete_message(
    update: Update, 
    context: CallbackContext, 
    message_id: Optional[int] = None
) -> bool:
    """
    Supprime un message.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        message_id: ID optionnel du message à supprimer (si non fourni, utilise le message du callback)
        
    Returns:
        True si le message a été supprimé, False sinon
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de suppression de message sans dépendance Telegram")
        return False
        
    try:
        # Cas d'un callback query
        if message_id is None and hasattr(update, 'callback_query') and update.callback_query:
            chat_id = update.callback_query.message.chat_id
            message_id = update.callback_query.message.message_id
            await update.callback_query.answer()
        # Cas d'un message normal
        elif message_id is None and hasattr(update, 'message') and update.message:
            chat_id = update.message.chat_id
            message_id = update.message.message_id
        # Cas où nous avons juste le chat et un ID de message
        elif message_id and hasattr(update, 'effective_chat') and update.effective_chat:
            chat_id = update.effective_chat.id
        else:
            logger.error("Impossible de déterminer le message à supprimer")
            return False

        # Supprimer le message
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except TelegramError as e:
        logger.error(f"Erreur Telegram lors de la suppression du message: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du message: {e}")
        return False


async def send_error(
    update: Update, 
    context: CallbackContext, 
    text: str, 
    silent: bool = False
) -> Optional[Message]:
    """
    Envoie un message d'erreur formaté.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        text: Texte du message d'erreur
        silent: Si True, envoie le message en mode silencieux (sans notification)
        
    Returns:
        L'objet Message envoyé ou None en cas d'erreur
    """
    error_message = f"{EMOJI['error']} *Erreur*: {text}"
    return await send_message(update, context, error_message, silent=silent)


async def send_success(
    update: Update, 
    context: CallbackContext, 
    text: str, 
    silent: bool = False
) -> Optional[Message]:
    """
    Envoie un message de succès formaté.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        text: Texte du message de succès
        silent: Si True, envoie le message en mode silencieux (sans notification)
        
    Returns:
        L'objet Message envoyé ou None en cas d'erreur
    """
    success_message = f"{EMOJI['success']} *Succès*: {text}"
    return await send_message(update, context, success_message, silent=silent)


async def send_warning(
    update: Update, 
    context: CallbackContext, 
    text: str, 
    silent: bool = False
) -> Optional[Message]:
    """
    Envoie un message d'avertissement formaté.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        text: Texte du message d'avertissement
        silent: Si True, envoie le message en mode silencieux (sans notification)
        
    Returns:
        L'objet Message envoyé ou None en cas d'erreur
    """
    warning_message = f"{EMOJI['warning']} *Attention*: {text}"
    return await send_message(update, context, warning_message, silent=silent)


async def send_info(
    update: Update, 
    context: CallbackContext, 
    text: str, 
    silent: bool = False
) -> Optional[Message]:
    """
    Envoie un message d'information formaté.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte du callback
        text: Texte du message d'information
        silent: Si True, envoie le message en mode silencieux (sans notification)
        
    Returns:
        L'objet Message envoyé ou None en cas d'erreur
    """
    info_message = f"{EMOJI['info']} *Info*: {text}"
    return await send_message(update, context, info_message, silent=silent)


def format_coin_info(
    coin_name: str, 
    price: float, 
    change_24h: float, 
    volume_24h: float, 
    market_cap: Optional[float] = None
) -> str:
    """
    Formate les informations d'un coin pour l'affichage Telegram.
    
    Args:
        coin_name: Nom du coin
        price: Prix actuel
        change_24h: Changement de prix sur 24h (en %)
        volume_24h: Volume sur 24h
        market_cap: Capitalisation de marché (optionnel)
        
    Returns:
        Message formaté pour Telegram
    """
    # Déterminer l'emoji pour la tendance
    if change_24h > 5:
        trend_emoji = "🔥"
    elif change_24h > 0:
        trend_emoji = "📈"
    elif change_24h < -5:
        trend_emoji = "💥"
    else:
        trend_emoji = "📉"
    
    # Formater les valeurs
    price_str = f"${price:.8f}".rstrip('0').rstrip('.') if price < 0.01 else f"${price:.2f}"
    change_str = f"{change_24h:+.2f}%"
    volume_str = f"${volume_24h/1000000:.2f}M" if volume_24h >= 1000000 else f"${volume_24h/1000:.2f}K"
    
    # Construire le message
    message = f"*{coin_name}* {trend_emoji}\n"
    message += f"Prix: `{price_str}`\n"
    message += f"24h: `{change_str}`\n"
    message += f"Volume: `{volume_str}`\n"
    
    if market_cap:
        mcap_str = f"${market_cap/1000000:.2f}M" if market_cap >= 1000000 else f"${market_cap/1000:.2f}K"
        message += f"MCap: `{mcap_str}`"
    
    return message


def format_trade(
    action: str, 
    token: str, 
    amount: float, 
    price: float, 
    total: float, 
    timestamp: Optional[str] = None,
    dex: Optional[str] = None
) -> str:
    """
    Formate les informations d'une transaction pour l'affichage Telegram.
    
    Args:
        action: Action (buy/sell)
        token: Symbole du token
        amount: Quantité de tokens
        price: Prix unitaire
        total: Montant total
        timestamp: Horodatage (optionnel)
        dex: DEX utilisé (optionnel)
        
    Returns:
        Message formaté pour Telegram
    """
    # Déterminer l'emoji et la couleur
    if action.lower() == "buy":
        emoji = "🟢"
        action_str = "Achat"
    elif action.lower() == "sell":
        emoji = "🔴"
        action_str = "Vente"
    else:
        emoji = "⚪"
        action_str = action
    
    # Formater les valeurs
    amount_str = f"{amount:.8f}".rstrip('0').rstrip('.') if amount < 0.01 else f"{amount:.4f}"
    price_str = f"${price:.8f}".rstrip('0').rstrip('.') if price < 0.01 else f"${price:.4f}"
    total_str = f"${total:.2f}"
    
    # Construire le message
    message = f"{emoji} *{action_str} {token}*\n"
    message += f"Quantité: `{amount_str} {token}`\n"
    message += f"Prix: `{price_str}`\n"
    message += f"Total: `{total_str}`\n"
    
    if dex:
        message += f"DEX: `{dex}`\n"
    
    if timestamp:
        message += f"Date: `{timestamp}`"
    
    return message


def format_profit_report(
    token: str, 
    buy_price: float, 
    sell_price: float, 
    amount: float, 
    profit: float, 
    profit_percent: float,
    duration: Optional[str] = None
) -> str:
    """
    Formate un rapport de profit pour l'affichage Telegram.
    
    Args:
        token: Symbole du token
        buy_price: Prix d'achat
        sell_price: Prix de vente
        amount: Quantité de tokens
        profit: Profit réalisé
        profit_percent: Pourcentage de profit
        duration: Durée de détention (optionnel)
        
    Returns:
        Message formaté pour Telegram
    """
    # Déterminer l'emoji selon le profit
    if profit_percent > 20:
        emoji = "🤑"
    elif profit_percent > 5:
        emoji = "💰"
    elif profit_percent > 0:
        emoji = "✅"
    elif profit_percent > -5:
        emoji = "⚠️"
    else:
        emoji = "❌"
    
    # Formater les valeurs
    buy_str = f"${buy_price:.8f}".rstrip('0').rstrip('.') if buy_price < 0.01 else f"${buy_price:.4f}"
    sell_str = f"${sell_price:.8f}".rstrip('0').rstrip('.') if sell_price < 0.01 else f"${sell_price:.4f}"
    amount_str = f"{amount:.8f}".rstrip('0').rstrip('.') if amount < 0.01 else f"{amount:.4f}"
    profit_str = f"${profit:.2f}"
    
    # Construire le message
    message = f"{emoji} *Rapport de Profit {token}*\n"
    message += f"Achat: `{buy_str}`\n"
    message += f"Vente: `{sell_str}`\n"
    message += f"Quantité: `{amount_str} {token}`\n"
    message += f"Profit: `{profit_str} ({profit_percent:+.2f}%)`\n"
    
    if duration:
        message += f"Durée: `{duration}`"
    
    return message


def escape_markdown(text: str) -> str:
    """
    Échappe les caractères spéciaux Markdown dans un texte.
    
    Args:
        text: Texte à échapper
        
    Returns:
        Texte avec caractères spéciaux échappés
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)


# Fonction utilitaire pour créer des données de callback lisibles et décodables
def create_callback_data(action: str, *args) -> str:
    """
    Crée une chaîne de données de callback encodée pour les boutons inline.
    
    Args:
        action: Action à exécuter
        *args: Arguments supplémentaires
        
    Returns:
        Chaîne de données de callback
    """
    data = [action]
    data.extend(args)
    return ":".join(str(item) for item in data)


def parse_callback_data(data: str) -> Tuple[str, List[str]]:
    """
    Analyse une chaîne de données de callback.
    
    Args:
        data: Chaîne de données de callback
        
    Returns:
        Tuple (action, liste d'arguments)
    """
    parts = data.split(":")
    action = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    return action, args


# Test si exécuté directement
if __name__ == "__main__":
    print("Module de messages Telegram pour GBPBot")
    print("Ce module doit être importé, pas exécuté directement.") 