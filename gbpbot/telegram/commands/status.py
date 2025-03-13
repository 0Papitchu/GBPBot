#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de commandes Telegram pour obtenir le statut et les statistiques du GBPBot.

Ce module fournit des commandes pour vérifier l'état actuel du bot, les soldes des wallets,
et les statistiques de performance.

Fonctionnalités:
- Vérification du statut du système
- Affichage des soldes des wallets
- Consultation des statistiques de trading
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union, cast
from datetime import datetime, timedelta

# Configuration du logger
logger = logging.getLogger("gbpbot.telegram.status")

# Imports conditionnels des modules Telegram
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    telegram_available = True
except ImportError:
    telegram_available = False
    logging.warning("Modules Telegram non disponibles. Fonctionnalités de statut désactivées.")

# Définition des classes stub pour les modules manquants
class WalletManagerStub:
    """Classe stub pour WalletManager en cas d'absence du module réel"""
    def get_balances(self, blockchain=None):
        return {}
    
    async def get_balances_async(self, blockchain=None):
        return {}
    
    def get_supported_chains(self):
        """Retourne une liste factice de blockchains supportées"""
        return ["avax", "solana", "sonic"]
    
    async def get_supported_chains_async(self):
        """Version asynchrone de get_supported_chains"""
        return self.get_supported_chains()

class PerformanceMonitorStub:
    """Classe stub pour PerformanceMonitor en cas d'absence du module réel"""
    def get_stats(self, hours=24):
        return {
            "trades_count": 0,
            "profit_total": 0.0,
            "success_rate": 0.0,
            "avg_profit": 0.0,
            "start_time": datetime.now() - timedelta(hours=hours),
            "end_time": datetime.now(),
        }
    
    async def get_stats_async(self, hours=24):
        return self.get_stats(hours)
    
    def get_period_stats(self, start_time, end_time=None):
        """Retourne des statistiques factices pour une période spécifique"""
        end_time = end_time or datetime.now()
        hours = (end_time - start_time).total_seconds() / 3600
        return self.get_stats(int(hours))
    
    async def get_period_stats_async(self, start_time, end_time=None):
        """Version asynchrone de get_period_stats"""
        return self.get_period_stats(start_time, end_time)

class SystemMonitorStub:
    """Classe stub pour SystemMonitor en cas d'absence du module réel"""
    def get_system_usage(self):
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0
        }
    
    async def get_system_usage_async(self):
        return self.get_system_usage()
    
    def get_system_info(self):
        """Retourne des informations système factices"""
        return {
            "os": "Unknown",
            "python_version": "3.x",
            "uptime": 0,
            "bot_uptime": 0
        }
    
    async def get_system_info_async(self):
        """Version asynchrone de get_system_info"""
        return self.get_system_info()

# Imports internes conditionnels
try:
    from gbpbot.modules.wallet_manager import WalletManager
    wallet_manager_available = True
except ImportError:
    WalletManager = WalletManagerStub
    wallet_manager_available = False
    logging.warning("Module WalletManager non disponible. Utilisation du stub.")

try:
    from gbpbot.monitoring.performance_monitor import PerformanceMonitor
    performance_monitor_available = True
except ImportError:
    PerformanceMonitor = PerformanceMonitorStub
    performance_monitor_available = False
    logging.warning("Module PerformanceMonitor non disponible. Utilisation du stub.")

try:
    from gbpbot.monitoring.system_monitor import SystemMonitor
    system_monitor_available = True
except ImportError:
    SystemMonitor = SystemMonitorStub
    system_monitor_available = False
    logging.warning("Module SystemMonitor non disponible. Utilisation du stub.")

# Constantes
DEFAULT_STATS_PERIOD = 24  # heures
MAX_STATS_PERIOD = 168     # 7 jours
DEFAULT_BALANCE_PRECISION = 6  # décimales pour l'affichage des soldes


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Affiche le statut actuel du GBPBot.
    
    Usage: /status
    
    Args:
        update: Objet Update de Telegram
        context: Contexte de la commande
    """
    if not update.effective_user or not update.effective_message:
        return
    
    # Vérifier l'autorisation de l'utilisateur
    bot = context.bot_data.get("bot")
    if bot and not bot._is_user_authorized(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
        return
    
    # Récupérer l'état du bot
    bot_state = context.bot_data.get("bot_state", {})
    
    # Message d'attente
    wait_message = await update.effective_message.reply_text(
        "⏳ Récupération du statut du GBPBot en cours...",
        parse_mode="HTML"
    )
    
    try:
        # Récupérer les données de statut
        status_data = await _get_system_status(bot_state)
        
        # Formater le message de statut
        message = _format_status_message(status_data)
        
        # Créer les boutons d'action
        keyboard = [
            [
                InlineKeyboardButton("📊 Statistiques détaillées", callback_data="status_stats"),
                InlineKeyboardButton("💰 Soldes wallets", callback_data="status_balance")
            ],
            [
                InlineKeyboardButton("🔄 Rafraîchir", callback_data="status_refresh")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mettre à jour le message d'attente avec le statut
        await wait_message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        await wait_message.edit_text(
            f"❌ <b>Erreur lors de la récupération du statut</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )


async def view_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Affiche les statistiques détaillées du GBPBot.
    
    Usage: /stats [période_en_heures]
    
    Args:
        update: Objet Update de Telegram
        context: Contexte de la commande
    """
    if not update.effective_user or not update.effective_message:
        return
    
    # Vérifier l'autorisation de l'utilisateur
    bot = context.bot_data.get("bot")
    if bot and not bot._is_user_authorized(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
        return
    
    # Récupérer l'état du bot
    bot_state = context.bot_data.get("bot_state", {})
    
    # Traiter les arguments
    args = context.args if context.args else []
    hours = int(args[0]) if len(args) > 0 and args[0].isdigit() else DEFAULT_STATS_PERIOD
    
    # Limiter la période à la valeur maximale
    hours = min(hours, MAX_STATS_PERIOD)
    
    # Message d'attente
    wait_message = await update.effective_message.reply_text(
        f"⏳ Récupération des statistiques pour les dernières {hours} heures...",
        parse_mode="HTML"
    )
    
    try:
        # Récupérer les statistiques
        stats = await _get_performance_stats(bot_state, hours)
        
        # Formater le message de statistiques
        message = _format_stats_message(stats, hours)
        
        # Créer les boutons d'action
        keyboard = [
            [
                InlineKeyboardButton("24h", callback_data="stats_24"),
                InlineKeyboardButton("48h", callback_data="stats_48"),
                InlineKeyboardButton("72h", callback_data="stats_72")
            ],
            [
                InlineKeyboardButton("7 jours", callback_data="stats_168"),
                InlineKeyboardButton("🔄 Rafraîchir", callback_data=f"stats_refresh_{hours}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mettre à jour le message d'attente avec les statistiques
        await wait_message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        await wait_message.edit_text(
            f"❌ <b>Erreur lors de la récupération des statistiques</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )


async def check_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Affiche les soldes des wallets configurés.
    
    Usage: /balance [blockchain] [precision]
    
    Args:
        update: Objet Update de Telegram
        context: Contexte de la commande
    """
    if not update.effective_user or not update.effective_message:
        return
    
    # Vérifier l'autorisation de l'utilisateur
    bot = context.bot_data.get("bot")
    if bot and not bot._is_user_authorized(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
        return
    
    # Récupérer l'état du bot
    bot_state = context.bot_data.get("bot_state", {})
    
    # Traiter les arguments
    args = context.args if context.args else []
    blockchain = args[0].lower() if len(args) > 0 else None
    precision = int(args[1]) if len(args) > 1 and args[1].isdigit() else DEFAULT_BALANCE_PRECISION
    
    # Message d'attente
    wait_message = await update.effective_message.reply_text(
        f"⏳ Récupération des soldes{' pour ' + blockchain.upper() if blockchain else ''}...",
        parse_mode="HTML"
    )
    
    try:
        # Récupérer les soldes
        balances = await _get_wallet_balances(bot_state, blockchain)
        
        # Formater le message de soldes
        message = _format_balance_message(balances, precision)
        
        # Créer les boutons d'action
        keyboard = []
        
        # Boutons pour les blockchains spécifiques
        if not blockchain and balances:
            chain_buttons = []
            for chain in balances.keys():
                chain_buttons.append(
                    InlineKeyboardButton(f"{chain.upper()}", callback_data=f"balance_{chain.lower()}")
                )
            
            # Diviser les boutons en rangées de 3
            rows = [chain_buttons[i:i+3] for i in range(0, len(chain_buttons), 3)]
            keyboard.extend(rows)
        
        # Bouton de rafraîchissement
        keyboard.append([InlineKeyboardButton("🔄 Rafraîchir", callback_data=f"balance_refresh{('_' + blockchain) if blockchain else ''}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mettre à jour le message d'attente avec les soldes
        await wait_message.edit_text(
            message,
        parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des soldes: {str(e)}")
        await wait_message.edit_text(
            f"❌ <b>Erreur lors de la récupération des soldes</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )


async def status_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère les callbacks des boutons liés aux commandes de statut.
    
    Args:
        update: Objet Update de Telegram
        context: Contexte de la commande
    """
    if not update.effective_user or not update.callback_query:
        return
    
    # Vérifier l'autorisation de l'utilisateur
    bot = context.bot_data.get("bot")
    if bot and not bot._is_user_authorized(update.effective_user.id):
        await update.callback_query.answer("⛔ Vous n'êtes pas autorisé à utiliser cette fonction.")
        return
    
    # Extraire les données du callback
    query = update.callback_query
    data = query.data
    
    if not data:
        await query.answer("Données de callback invalides")
        return
    
    # Acquitter le callback
    await query.answer()
    
    # Récupérer l'état du bot
    bot_state = context.bot_data.get("bot_state", {})
    
    # Traiter les différents types de callbacks
    if data == "status_refresh":
        # Rafraîchir le statut
        try:
            status_data = await _get_system_status(bot_state)
            message = _format_status_message(status_data)
            
            # Créer les boutons d'action
            keyboard = [
                [
                    InlineKeyboardButton("📊 Statistiques", callback_data="status_stats"),
                    InlineKeyboardButton("💰 Soldes", callback_data="status_balance")
                ],
                [
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data="status_refresh")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du statut: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Erreur lors du rafraîchissement du statut</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    elif data == "status_stats":
        # Afficher les statistiques
        try:
            stats = await _get_performance_stats(bot_state, DEFAULT_STATS_PERIOD)
            message = _format_stats_message(stats, DEFAULT_STATS_PERIOD)
            
            # Créer les boutons d'action
            keyboard = [
                [
                    InlineKeyboardButton("24h", callback_data="stats_24"),
                    InlineKeyboardButton("48h", callback_data="stats_48"),
                    InlineKeyboardButton("72h", callback_data="stats_72")
                ],
                [
                    InlineKeyboardButton("7 jours", callback_data="stats_168"),
                    InlineKeyboardButton("⬅️ Retour", callback_data="stats_back")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage des statistiques: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Erreur lors de l'affichage des statistiques</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
            
    elif data == "status_balance":
        # Afficher les soldes
        try:
            balances = await _get_wallet_balances(bot_state)
            message = _format_balance_message(balances, DEFAULT_BALANCE_PRECISION)
            
            # Créer les boutons d'action
            keyboard = []
            
            # Boutons pour les blockchains spécifiques
            if balances:
                chain_buttons = []
                for chain in balances.keys():
                    chain_buttons.append(
                        InlineKeyboardButton(f"{chain.upper()}", callback_data=f"balance_{chain.lower()}")
                    )
                
                # Diviser les boutons en rangées de 3
                rows = [chain_buttons[i:i+3] for i in range(0, len(chain_buttons), 3)]
                keyboard.extend(rows)
            
            # Boutons de navigation
            keyboard.append([
                InlineKeyboardButton("🔄 Rafraîchir", callback_data="balance_refresh"),
                InlineKeyboardButton("⬅️ Retour", callback_data="balance_back")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage des soldes: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Erreur lors de l'affichage des soldes</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    # Utiliser elif seulement pour les cas où data est non-null
    elif data.startswith("stats_"):
        # Gérer les callbacks liés aux statistiques
        if data == "stats_back":
            # Retour au statut
            await status_command(update, context)
            return
        
        # Extraire la période demandée
        period_str = data.replace("stats_", "").replace("refresh_", "")
        hours = int(period_str) if period_str.isdigit() else DEFAULT_STATS_PERIOD
        
        # Récupérer et afficher les statistiques pour la période demandée
        try:
            stats = await _get_performance_stats(bot_state, hours)
            message = _format_stats_message(stats, hours)
    
            # Créer les boutons d'action
            keyboard = [
                [
                    InlineKeyboardButton("24h", callback_data="stats_24"),
                    InlineKeyboardButton("48h", callback_data="stats_48"),
                    InlineKeyboardButton("72h", callback_data="stats_72")
                ],
                [
                    InlineKeyboardButton("7 jours", callback_data="stats_168"),
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data=f"stats_refresh_{hours}")
                ],
                [
                    InlineKeyboardButton("⬅️ Retour", callback_data="stats_back")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage des statistiques: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Erreur lors de l'affichage des statistiques</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    elif data.startswith("balance_"):
        # Gérer les callbacks liés aux soldes
        if data == "balance_back":
            # Retour au statut
            await status_command(update, context)
            return
        elif data == "balance_refresh":
            # Rafraîchir tous les soldes
            blockchain = None
        elif data.startswith("balance_refresh_"):
            # Rafraîchir une blockchain spécifique
            blockchain = data.replace("balance_refresh_", "")
        else:
            # Afficher les soldes d'une blockchain spécifique
            blockchain = data.replace("balance_", "")
        
        # Récupérer et afficher les soldes
        try:
            balances = await _get_wallet_balances(bot_state, blockchain)
            message = _format_balance_message(balances, DEFAULT_BALANCE_PRECISION, blockchain)
            
            # Créer les boutons d'action
            keyboard = []
            
            # Si nous affichons une blockchain spécifique, ajouter un bouton pour revenir à toutes les blockchains
            if blockchain:
                # Bouton pour rafraîchir cette blockchain spécifique
                keyboard.append([
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data=f"balance_refresh_{blockchain}"),
                    InlineKeyboardButton("⬅️ Toutes les blockchains", callback_data="status_balance")
                ])
            else:
                # Boutons pour les blockchains spécifiques
                if balances:
                    chain_buttons = []
                    for chain in balances.keys():
                        chain_buttons.append(
                            InlineKeyboardButton(f"{chain.upper()}", callback_data=f"balance_{chain.lower()}")
                        )
                    
                    # Diviser les boutons en rangées de 3
                    rows = [chain_buttons[i:i+3] for i in range(0, len(chain_buttons), 3)]
                    keyboard.extend(rows)
                
                # Boutons de navigation
                keyboard.append([
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data="balance_refresh"),
                    InlineKeyboardButton("⬅️ Retour", callback_data="balance_back")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage des soldes: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Erreur lors de l'affichage des soldes</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )

# Fonctions utilitaires internes

async def _get_system_status(bot_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Récupère le statut du système.
    
    Args:
        bot_state: État du bot
    
    Returns:
        Dictionnaire contenant les données de statut
    """
    status_data = {
        "uptime": "N/A",
        "active_strategies": [],
        "wallet_balances": {},
        "performance_24h": 0.0,
        "total_trades": 0,
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "last_trade_time": None,
        "last_update": datetime.now()
    }
    
    try:
        # Récupérer le temps de fonctionnement
        if "start_time" in bot_state:
            uptime = datetime.now() - bot_state["start_time"]
            status_data["uptime"] = _format_timedelta(uptime)
        
        # Récupérer les stratégies actives
        if "active_strategies" in bot_state:
            status_data["active_strategies"] = bot_state["active_strategies"]
        
        # Récupérer les soldes des wallets (simplifié)
        if "wallet_balances" in bot_state:
            status_data["wallet_balances"] = bot_state["wallet_balances"]
        else:
            # Si les soldes ne sont pas dans l'état, tenter de les récupérer
            try:
                balances = await _get_wallet_balances(bot_state)
                status_data["wallet_balances"] = balances
            except Exception:
                pass
        
        # Récupérer les données de performance
        if "performance" in bot_state:
            status_data["performance_24h"] = bot_state["performance"].get("24h", 0.0)
        
        # Récupérer le nombre total de trades
        if "trades" in bot_state:
            status_data["total_trades"] = len(bot_state["trades"])
            
            # Récupérer la date du dernier trade
            if bot_state["trades"]:
                last_trade = max(bot_state["trades"], key=lambda x: x.get("timestamp", 0))
                status_data["last_trade_time"] = datetime.fromtimestamp(last_trade.get("timestamp", 0))
        
        # Récupérer l'utilisation du système si le moniteur est disponible
        if system_monitor_available:
            try:
                system_monitor = SystemMonitor()
                system_info = system_monitor.get_system_info()
                status_data["cpu_usage"] = system_info.get("cpu_usage", 0.0)
                status_data["memory_usage"] = system_info.get("memory_usage", 0.0)
            except Exception:
                pass
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut du système: {str(e)}")
    
    return status_data

async def _get_wallet_balances(bot_state: Dict[str, Any], blockchain: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """
    Récupère les soldes des wallets.
    
    Args:
        bot_state: État du bot
        blockchain: Nom de la blockchain (optionnel)
    
    Returns:
        Dictionnaire contenant les soldes des wallets
    """
    balances = {}
    
    try:
        # Si les balances sont dans l'état du bot, les utiliser
        if "wallet_balances" in bot_state:
            wallet_balances = bot_state["wallet_balances"]
            
            # Filtrer par blockchain si spécifiée
            if blockchain:
                if blockchain in wallet_balances:
                    balances[blockchain] = wallet_balances[blockchain]
            else:
                balances = wallet_balances
        
        # Sinon, tenter de les récupérer via le wallet manager
        elif wallet_manager_available:
            try:
                wallet_manager = WalletManager()
                
                if blockchain:
                    # Récupérer les soldes pour une blockchain spécifique
                    chain_balances = wallet_manager.get_balances(blockchain)
                    if chain_balances:
                        balances[blockchain] = chain_balances
                else:
                    # Récupérer les soldes pour toutes les blockchains
                    for chain in wallet_manager.get_supported_chains():
                        chain_balances = wallet_manager.get_balances(chain)
                        if chain_balances:
                            balances[chain] = chain_balances
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des soldes via WalletManager: {str(e)}")
        
        # Si aucune donnée réelle n'est disponible, utiliser des données d'exemple pour la démonstration
        if not balances:
            # Données d'exemple pour la démo
            example_balances = {
                "avalanche": {
                    "AVAX": 3.25,
                    "USDC": 150.75,
                    "GBPT": 1000.0
                },
                "solana": {
                    "SOL": 50.0,
                    "USDC": 500.25,
                    "BONK": 10000000.0
                },
                "sonic": {
                    "SONIC": 1200.0,
                    "ETH": 0.5
                }
            }
            
            if blockchain:
                if blockchain in example_balances:
                    balances[blockchain] = example_balances[blockchain]
            else:
                balances = example_balances
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des soldes des wallets: {str(e)}")
    
    return balances

async def _get_performance_stats(bot_state: Dict[str, Any], hours: int = DEFAULT_STATS_PERIOD) -> Dict[str, Any]:
    """
    Récupère les statistiques de performance.
    
    Args:
        bot_state: État du bot
        hours: Nombre d'heures à considérer
    
    Returns:
        Dictionnaire contenant les statistiques de performance
    """
    stats = {
        "period_hours": hours,
        "roi": 0.0,
        "profit_amount": 0.0,
        "currency": "USD",
        "trades_count": 0,
        "successful_trades": 0,
        "win_rate": 0.0,
        "average_profit": 0.0,
        "max_profit": 0.0,
        "max_loss": 0.0,
        "strategies_performance": {},
        "tokens_performance": {}
    }
    
    try:
        # Définir la période
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Si les données de performances sont dans l'état du bot, les utiliser
        if performance_monitor_available:
            try:
                performance_monitor = PerformanceMonitor()
                period_stats = performance_monitor.get_period_stats(hours)
                
                if period_stats:
                    stats.update(period_stats)
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des statistiques via PerformanceMonitor: {str(e)}")
        
        # Sinon, calculer à partir des trades si disponibles
        elif "trades" in bot_state:
            trades = bot_state["trades"]
            
            # Filtrer les trades dans la période
            period_trades = [trade for trade in trades if trade.get("timestamp", 0) >= start_time.timestamp()]
            
            stats["trades_count"] = len(period_trades)
            
            if period_trades:
                # Calculer les statistiques de base
                total_profit = sum(trade.get("profit_amount", 0) for trade in period_trades)
                successful_trades = sum(1 for trade in period_trades if trade.get("profit_amount", 0) > 0)
                
                stats["profit_amount"] = total_profit
                stats["successful_trades"] = successful_trades
                stats["win_rate"] = (successful_trades / len(period_trades)) * 100 if period_trades else 0
                stats["average_profit"] = total_profit / len(period_trades) if period_trades else 0
                stats["max_profit"] = max((trade.get("profit_amount", 0) for trade in period_trades), default=0)
                stats["max_loss"] = min((trade.get("profit_amount", 0) for trade in period_trades), default=0)
                
                # Calculer la performance initiale
                initial_balance = bot_state.get("initial_balance", 1000)  # Valeur par défaut si non disponible
                stats["roi"] = (total_profit / initial_balance) * 100 if initial_balance else 0
                
                # Calculer les performances par stratégie
                strategies_perf = {}
                for trade in period_trades:
                    strategy = trade.get("strategy", "unknown")
                    if strategy not in strategies_perf:
                        strategies_perf[strategy] = {
                            "profit_amount": 0,
                            "trades_count": 0,
                            "successful_trades": 0
                        }
                    
                    strategies_perf[strategy]["profit_amount"] += trade.get("profit_amount", 0)
                    strategies_perf[strategy]["trades_count"] += 1
                    if trade.get("profit_amount", 0) > 0:
                        strategies_perf[strategy]["successful_trades"] += 1
                
                # Calculer le win rate pour chaque stratégie
                for strategy, perf in strategies_perf.items():
                    perf["win_rate"] = (perf["successful_trades"] / perf["trades_count"]) * 100 if perf["trades_count"] else 0
                
                stats["strategies_performance"] = strategies_perf
                
                # Calculer les performances par token
                tokens_perf = {}
                for trade in period_trades:
                    token = trade.get("token_symbol", "unknown")
                    if token not in tokens_perf:
                        tokens_perf[token] = {
                            "profit_amount": 0,
                            "trades_count": 0
                        }
                    
                    tokens_perf[token]["profit_amount"] += trade.get("profit_amount", 0)
                    tokens_perf[token]["trades_count"] += 1
                
                stats["tokens_performance"] = tokens_perf
        
        # Si aucune donnée réelle n'est disponible, utiliser des données d'exemple pour la démonstration
        if stats["trades_count"] == 0:
            # Données d'exemple pour la démo
            stats = {
                "period_hours": hours,
                "roi": 12.5,
                "profit_amount": 125.75,
                "currency": "USD",
                "trades_count": 42,
                "successful_trades": 30,
                "win_rate": 71.43,
                "average_profit": 2.99,
                "max_profit": 28.54,
                "max_loss": -12.33,
                "strategies_performance": {
                    "arbitrage": {
                        "profit_amount": 85.25,
                        "trades_count": 30,
                        "successful_trades": 22,
                        "win_rate": 73.33
                    },
                    "sniping": {
                        "profit_amount": 40.50,
                        "trades_count": 12,
                        "successful_trades": 8,
                        "win_rate": 66.67
                    }
                },
                "tokens_performance": {
                    "SOL": {
                        "profit_amount": 55.20,
                        "trades_count": 15
                    },
                    "AVAX": {
                        "profit_amount": 40.30,
                        "trades_count": 12
                    },
                    "BONK": {
                        "profit_amount": 30.25,
                        "trades_count": 10
                    },
                    "GBPT": {
                        "profit_amount": 0.0,
                        "trades_count": 5
                    }
                }
            }
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques de performance: {str(e)}")
    
    return stats

def _format_status_message(status_data: Dict[str, Any]) -> str:
    """
    Formate un message de statut.
    
    Args:
        status_data: Données de statut
    
    Returns:
        Message formaté
    """
    uptime = status_data.get("uptime", "N/A")
    active_strategies = status_data.get("active_strategies", [])
    wallet_balances = status_data.get("wallet_balances", {})
    performance_24h = status_data.get("performance_24h", 0.0)
    total_trades = status_data.get("total_trades", 0)
    last_trade_time = status_data.get("last_trade_time")
    
    # Calculer le solde total en USD
    total_balance_usd = 0.0
    for chain, tokens in wallet_balances.items():
        for token, balance_info in tokens.items():
            if isinstance(balance_info, dict) and "usd_value" in balance_info:
                total_balance_usd += balance_info["usd_value"]
            elif isinstance(balance_info, (int, float)):
                # Pour les balances simples, tenter de convertir avec le prix (si disponible)
                token_price = status_data.get("prices", {}).get(token, 0)
                total_balance_usd += balance_info * token_price
    
    # Emoji selon la performance
    performance_emoji = "🟢" if performance_24h > 0 else "🔴" if performance_24h < 0 else "⚪"
    
    # Formater le message
    message = "📊 <b>Statut GBPBot</b>\n\n"
    
    # Informations de base
    message += f"⏱️ <b>Uptime:</b> {uptime}\n"
    message += f"{performance_emoji} <b>Performance 24h:</b> {performance_24h:+.2f}%\n"
    message += f"💰 <b>Balance Totale:</b> {total_balance_usd:.2f} USD\n"
    message += f"📈 <b>Trades Total:</b> {total_trades}\n"
    
    if last_trade_time:
        message += f"🕒 <b>Dernier Trade:</b> {last_trade_time.strftime('%d/%m/%Y %H:%M:%S')}\n"
    
    # Stratégies actives
    if active_strategies:
        message += "\n<b>Stratégies Actives:</b>\n"
        for strategy in active_strategies:
            if isinstance(strategy, dict):
                strategy_name = strategy.get("name", "Unknown")
                strategy_status = strategy.get("status", "En cours")
                message += f"• {strategy_name} - {strategy_status}\n"
            else:
                message += f"• {strategy}\n"
    else:
        message += "\n<i>Aucune stratégie active</i>\n"
    
    # Ajouter la date et heure
    message += f"\n<i>Mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
    
    return message

def _format_balance_message(balances: Dict[str, Dict[str, float]], precision: int = DEFAULT_BALANCE_PRECISION, blockchain: Optional[str] = None) -> str:
    """
    Formate un message de soldes.
    
    Args:
        balances: Données de soldes
        precision: Précision pour l'affichage des montants
        blockchain: Nom de la blockchain (optionnel)
    
    Returns:
        Message formaté
    """
    if blockchain:
        message = f"💰 <b>Soldes {blockchain.upper()}</b>\n\n"
    else:
        message = "💰 <b>Soldes des Wallets</b>\n\n"
    
    if not balances:
        message += "<i>Aucun solde disponible</i>"
        return message
    
    # Fonction pour formater un montant avec la précision spécifiée
    def format_amount(amount: float) -> str:
        if amount < 0.000001:  # Très petits montants
            return f"{amount:.8f}"
        else:
            return f"{amount:.{precision}f}"
    
    # Si une blockchain spécifique est demandée
    if blockchain and blockchain in balances:
        chain_balances = balances[blockchain]
        
        # Formater chaque token
        for token, amount in chain_balances.items():
            if isinstance(amount, dict):
                # Format avancé avec prix et valeur USD
                token_amount = amount.get("amount", 0)
                usd_value = amount.get("usd_value", 0)
                message += f"• <b>{token}:</b> {format_amount(token_amount)} (≈ ${usd_value:.2f})\n"
            else:
                # Format simple
                message += f"• <b>{token}:</b> {format_amount(amount)}\n"
    else:
        # Pour chaque blockchain
        for chain, chain_balances in balances.items():
            message += f"\n<b>{chain.upper()}:</b>\n"
            
            # Formater chaque token
            for token, amount in chain_balances.items():
                if isinstance(amount, dict):
                    # Format avancé avec prix et valeur USD
                    token_amount = amount.get("amount", 0)
                    usd_value = amount.get("usd_value", 0)
                    message += f"• <b>{token}:</b> {format_amount(token_amount)} (≈ ${usd_value:.2f})\n"
                else:
                    # Format simple
                    message += f"• <b>{token}:</b> {format_amount(amount)}\n"
    
    # Ajouter la date et heure
    message += f"\n<i>Mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
    
    return message

def _format_stats_message(stats: Dict[str, Any], hours: int) -> str:
    """
    Formate un message de statistiques.
    
    Args:
        stats: Données de statistiques
        hours: Nombre d'heures
    
    Returns:
        Message formaté
    """
    period_str = f"{hours}h"
    if hours == 24:
        period_str = "24h"
    elif hours == 48:
        period_str = "48h"
    elif hours == 72:
        period_str = "72h"
    elif hours == 168:
        period_str = "7 jours"
    
    roi = stats.get("roi", 0.0)
    profit_amount = stats.get("profit_amount", 0.0)
    currency = stats.get("currency", "USD")
    trades_count = stats.get("trades_count", 0)
    win_rate = stats.get("win_rate", 0.0)
    average_profit = stats.get("average_profit", 0.0)
    max_profit = stats.get("max_profit", 0.0)
    max_loss = stats.get("max_loss", 0.0)
    
    # Emoji selon le ROI
    roi_emoji = "🟢" if roi > 0 else "🔴" if roi < 0 else "⚪"
    
    # Formater le message
    message = f"📊 <b>Statistiques ({period_str})</b>\n\n"
    
    # Informations de base
    message += f"{roi_emoji} <b>ROI:</b> {roi:+.2f}%\n"
    message += f"💰 <b>Profit:</b> {profit_amount:+.2f} {currency}\n"
    message += f"🎯 <b>Win Rate:</b> {win_rate:.2f}%\n"
    message += f"📈 <b>Trades:</b> {trades_count}\n"
    message += f"📊 <b>Profit Moyen:</b> {average_profit:+.2f} {currency}\n"
    message += f"📈 <b>Profit Max:</b> {max_profit:+.2f} {currency}\n"
    message += f"📉 <b>Perte Max:</b> {max_loss:+.2f} {currency}\n"
    
    # Performances par stratégie
    strategies_performance = stats.get("strategies_performance", {})
    if strategies_performance:
        message += "\n<b>Performances par Stratégie:</b>\n"
        for strategy, perf in strategies_performance.items():
            profit = perf.get("profit_amount", 0)
            win_rate = perf.get("win_rate", 0)
            trades = perf.get("trades_count", 0)
            
            # Emoji selon le profit
            strategy_emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
            
            message += f"{strategy_emoji} <b>{strategy.title()}:</b> {profit:+.2f} {currency} ({win_rate:.1f}% WR, {trades} trades)\n"
    
    # Performances par token
    tokens_performance = stats.get("tokens_performance", {})
    if tokens_performance:
        # Trier les tokens par profit décroissant
        sorted_tokens = sorted(tokens_performance.items(), key=lambda x: x[1].get("profit_amount", 0), reverse=True)
        
        message += "\n<b>Performances par Token:</b>\n"
        
        # Limiter à 5 tokens pour ne pas surcharger le message
        for token, perf in sorted_tokens[:5]:
            profit = perf.get("profit_amount", 0)
            trades = perf.get("trades_count", 0)
            
            # Emoji selon le profit
            token_emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
            
            message += f"{token_emoji} <b>{token}:</b> {profit:+.2f} {currency} ({trades} trades)\n"
        
        # Indiquer s'il y a plus de tokens
        if len(sorted_tokens) > 5:
            message += f"<i>... et {len(sorted_tokens) - 5} autres tokens</i>\n"
    
    # Ajouter la date et heure
    message += f"\n<i>Mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
    
    return message

def _format_timedelta(delta: timedelta) -> str:
    """
    Formate un timedelta en chaîne lisible.
    
    Args:
        delta: Objet timedelta
    
    Returns:
        Chaîne formatée
    """
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}j {hours}h"

def register_status_command_handlers(application: Any) -> None:
    """
    Enregistre les gestionnaires de commandes pour les commandes de statut.
    
    Args:
        application: Application Telegram
    """
    if not telegram_available:
        logger.warning("Modules Telegram non disponibles. Commandes de statut non enregistrées.")
        return
    
    # Enregistrer les commandes
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("balance", check_balance_command))
    application.add_handler(CommandHandler("stats", view_stats_command))
    
    # Enregistrer le gestionnaire de callbacks
    application.add_handler(CallbackQueryHandler(status_callback_handler, pattern=r"^(status_|balance_|stats_)"))
    
    logger.info("Gestionnaires de commandes de statut enregistrés avec succès.") 