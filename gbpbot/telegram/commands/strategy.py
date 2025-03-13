"""
Module de commandes de stratégie pour le bot Telegram
====================================================

Ce module implémente les commandes pour démarrer, arrêter et configurer
les différentes stratégies de trading du GBPBot via Telegram.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
import traceback
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext, CommandHandler, CallbackQueryHandler

# Logger
logger = logging.getLogger("gbpbot.telegram.commands.strategy")

# Modules internes
try:
    from gbpbot.modules.token_sniper import TokenSniper
    TOKEN_SNIPER_AVAILABLE = True
except ImportError:
    TOKEN_SNIPER_AVAILABLE = False
    logger.warning("Module TokenSniper non disponible")

try:
    from gbpbot.modules.arbitrage_engine import ArbitrageEngine
    ARBITRAGE_ENGINE_AVAILABLE = True
except ImportError:
    ARBITRAGE_ENGINE_AVAILABLE = False
    logger.warning("Module ArbitrageEngine non disponible")

try:
    from gbpbot.modules.smart_profit_taker import SmartProfitTaker
    PROFIT_TAKER_AVAILABLE = True
except ImportError:
    PROFIT_TAKER_AVAILABLE = False
    logger.warning("Module SmartProfitTaker non disponible")

try:
    from gbpbot.modules.auto_trader import AutoTrader
    AUTO_TRADER_AVAILABLE = True
except ImportError:
    AUTO_TRADER_AVAILABLE = False
    logger.warning("Module AutoTrader non disponible")

# Placeholder pour la gestion d'état du bot (sera injecté)
BOT_STATE = None

# Commande /start_strategy - Démarre une stratégie de trading
async def start_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Démarre une stratégie de trading spécifiée.
    Usage: /start_strategy <nom_stratégie> [params]
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Si pas de paramètres, afficher les stratégies disponibles
    if not context.args or len(context.args) < 1:
        keyboard = [
            [InlineKeyboardButton("🚀 Sniping Token", callback_data="start_strategy_sniper")],
            [InlineKeyboardButton("⚖️ Arbitrage", callback_data="start_strategy_arbitrage")],
            [InlineKeyboardButton("💰 Prise de Profit Intelligente", callback_data="start_strategy_profit_taker")],
            [InlineKeyboardButton("🤖 Mode Automatique", callback_data="start_strategy_auto")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚀 <b>Démarrer une Stratégie</b>\n\n"
            "Choisissez la stratégie que vous souhaitez démarrer:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    
    # Récupérer la stratégie demandée
    strategy_name = context.args[0].lower()
    
    # Extraire les paramètres
    params = {}
    if len(context.args) > 1:
        for arg in context.args[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                # Convertir les valeurs en types appropriés
                if value.lower() == 'true':
                    params[key] = True
                elif value.lower() == 'false':
                    params[key] = False
                elif value.isdigit():
                    params[key] = int(value)
                elif value.replace('.', '', 1).isdigit():
                    params[key] = float(value)
                else:
                    params[key] = value
    
    try:
        result = await _start_strategy_internal(strategy_name, params, context.bot_data.get('bot_state'))
        if result['success']:
            await update.message.reply_text(
                f"✅ <b>Stratégie {strategy_name} démarrée avec succès!</b>\n\n"
                f"{result.get('message', '')}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Erreur lors du démarrage de la stratégie {strategy_name}</b>\n\n"
                f"{result.get('error', 'Erreur inconnue')}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de la stratégie: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ <b>Erreur lors du démarrage de la stratégie</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Commande /stop_strategy - Arrête une stratégie de trading
async def stop_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Arrête une stratégie de trading en cours.
    Usage: /stop_strategy <nom_stratégie>
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Si pas de paramètres, afficher les stratégies actives
    active_strategies = await _get_active_strategies(context.bot_data.get('bot_state'))
    
    if not context.args or len(context.args) < 1:
        if not active_strategies:
            await update.message.reply_text(
                "ℹ️ <b>Aucune stratégie active</b>\n\n"
                "Il n'y a actuellement aucune stratégie en cours d'exécution.",
                parse_mode="HTML"
            )
            return
            
        keyboard = []
        for strategy in active_strategies:
            keyboard.append([
                InlineKeyboardButton(
                    f"⏹️ {strategy['name']} ({strategy['type']})", 
                    callback_data=f"stop_strategy_{strategy['id']}"
                )
            ])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⏹️ <b>Arrêter une Stratégie</b>\n\n"
            "Choisissez la stratégie que vous souhaitez arrêter:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    
    # Récupérer la stratégie demandée
    strategy_name = context.args[0].lower()
    
    try:
        result = await _stop_strategy_internal(strategy_name, context.bot_data.get('bot_state'))
        if result['success']:
            await update.message.reply_text(
                f"✅ <b>Stratégie {strategy_name} arrêtée avec succès!</b>\n\n"
                f"{result.get('message', '')}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Erreur lors de l'arrêt de la stratégie {strategy_name}</b>\n\n"
                f"{result.get('error', 'Erreur inconnue')}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt de la stratégie: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ <b>Erreur lors de l'arrêt de la stratégie</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Commande /list_strategies - Liste toutes les stratégies et leur état
async def list_strategies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Liste toutes les stratégies disponibles et leur état actuel.
    Usage: /list_strategies
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    try:
        # Récupérer les stratégies actives
        active_strategies = await _get_active_strategies(context.bot_data.get('bot_state'))
        
        # Construire le message
        message = "📋 <b>Liste des Stratégies</b>\n\n"
        
        # Stratégies disponibles
        message += "<b>Stratégies Disponibles:</b>\n"
        
        if TOKEN_SNIPER_AVAILABLE:
            active = any(s['type'] == 'token_sniper' for s in active_strategies)
            message += f"{'🟢' if active else '⚪'} <b>Sniping Token</b> - Détecte et achète les nouveaux tokens prometteurs\n"
        
        if ARBITRAGE_ENGINE_AVAILABLE:
            active = any(s['type'] == 'arbitrage' for s in active_strategies)
            message += f"{'🟢' if active else '⚪'} <b>Arbitrage</b> - Exploite les écarts de prix entre différents DEX\n"
        
        if PROFIT_TAKER_AVAILABLE:
            active = any(s['type'] == 'profit_taker' for s in active_strategies)
            message += f"{'🟢' if active else '⚪'} <b>Prise de Profit Intelligente</b> - Optimise les prises de profit\n"
        
        if AUTO_TRADER_AVAILABLE:
            active = any(s['type'] == 'auto_trader' for s in active_strategies)
            message += f"{'🟢' if active else '⚪'} <b>Mode Automatique</b> - Exécute automatiquement les meilleures stratégies\n"
        
        # Stratégies actives
        if active_strategies:
            message += "\n<b>Stratégies Actives:</b>\n"
            for strategy in active_strategies:
                start_time = strategy.get('start_time', datetime.now())
                elapsed = (datetime.now() - start_time).total_seconds()
                hours, remainder = divmod(int(elapsed), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                message += (
                    f"🟢 <b>{strategy['name']}</b> ({strategy['type']})\n"
                    f"   ⏱️ En cours depuis: {hours}h {minutes}m {seconds}s\n"
                    f"   📊 Transactions: {strategy.get('transactions', 0)}\n"
                    f"   💰 Profit: {strategy.get('profit', 0):.4f} {strategy.get('currency', 'USD')}\n"
                )
        else:
            message += "\n<i>Aucune stratégie actuellement active</i>"
        
        # Envoyer le message
        await update.message.reply_text(message, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stratégies: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ <b>Erreur lors de la récupération des stratégies</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Commande /configure_strategy - Configure une stratégie de trading
async def configure_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Configure les paramètres d'une stratégie de trading.
    Usage: /configure_strategy <nom_stratégie> param1=valeur1 param2=valeur2 ...
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Si pas de paramètres, afficher l'aide
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚙️ <b>Configuration de Stratégie</b>\n\n"
            "Usage: <code>/configure_strategy &lt;nom_stratégie&gt; param1=valeur1 param2=valeur2 ...</code>\n\n"
            "Stratégies disponibles:\n"
            "- <code>sniper</code> - Sniping de Token\n"
            "- <code>arbitrage</code> - Arbitrage entre DEX\n"
            "- <code>profit_taker</code> - Prise de Profit Intelligente\n"
            "- <code>auto</code> - Mode Automatique\n\n"
            "Exemple: <code>/configure_strategy sniper max_gas=200 slippage=2.5</code>",
            parse_mode="HTML"
        )
        return
    
    # Récupérer la stratégie demandée
    strategy_name = context.args[0].lower()
    
    # Extraire les paramètres
    params = {}
    if len(context.args) > 1:
        for arg in context.args[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                # Convertir les valeurs en types appropriés
                if value.lower() == 'true':
                    params[key] = True
                elif value.lower() == 'false':
                    params[key] = False
                elif value.isdigit():
                    params[key] = int(value)
                elif value.replace('.', '', 1).isdigit():
                    params[key] = float(value)
                else:
                    params[key] = value
    
    try:
        result = await _configure_strategy_internal(strategy_name, params, context.bot_data.get('bot_state'))
        if result['success']:
            await update.message.reply_text(
                f"✅ <b>Stratégie {strategy_name} configurée avec succès!</b>\n\n"
                f"{result.get('message', '')}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Erreur lors de la configuration de la stratégie {strategy_name}</b>\n\n"
                f"{result.get('error', 'Erreur inconnue')}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de la stratégie: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ <b>Erreur lors de la configuration de la stratégie</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Fonctions internes pour gérer les stratégies
async def _start_strategy_internal(strategy_name: str, params: Dict[str, Any], bot_state: Any) -> Dict[str, Any]:
    """
    Fonction interne pour démarrer une stratégie.
    """
    global BOT_STATE
    BOT_STATE = bot_state
    
    strategy_map = {
        'sniper': 'token_sniper',
        'token_sniper': 'token_sniper',
        'arbitrage': 'arbitrage',
        'profit_taker': 'profit_taker',
        'smart_profit_taker': 'profit_taker',
        'auto': 'auto_trader',
        'auto_trader': 'auto_trader'
    }
    
    normalized_name = strategy_map.get(strategy_name.lower())
    if not normalized_name:
        return {'success': False, 'error': f"Stratégie '{strategy_name}' non reconnue"}
    
    # Vérifier si la stratégie est disponible
    if normalized_name == 'token_sniper' and not TOKEN_SNIPER_AVAILABLE:
        return {'success': False, 'error': "Module Token Sniper non disponible"}
    elif normalized_name == 'arbitrage' and not ARBITRAGE_ENGINE_AVAILABLE:
        return {'success': False, 'error': "Module Arbitrage Engine non disponible"}
    elif normalized_name == 'profit_taker' and not PROFIT_TAKER_AVAILABLE:
        return {'success': False, 'error': "Module Smart Profit Taker non disponible"}
    elif normalized_name == 'auto_trader' and not AUTO_TRADER_AVAILABLE:
        return {'success': False, 'error': "Module Auto Trader non disponible"}
    
    # Créer un ID unique pour cette stratégie
    strategy_id = f"{normalized_name}_{int(datetime.now().timestamp())}"
    
    # Initialiser et démarrer la stratégie
    try:
        if normalized_name == 'token_sniper':
            strategy = TokenSniper(params)
            await strategy.start()
        elif normalized_name == 'arbitrage':
            strategy = ArbitrageEngine(params)
            await strategy.start()
        elif normalized_name == 'profit_taker':
            strategy = SmartProfitTaker(params)
            await strategy.start()
        elif normalized_name == 'auto_trader':
            strategy = AutoTrader(params)
            await strategy.start()
        
        # Stocker la stratégie dans l'état du bot
        if BOT_STATE and hasattr(BOT_STATE, 'active_strategies'):
            if not hasattr(BOT_STATE, 'active_strategies'):
                BOT_STATE.active_strategies = {}
            
            BOT_STATE.active_strategies[strategy_id] = {
                'id': strategy_id,
                'type': normalized_name,
                'name': strategy.name if hasattr(strategy, 'name') else normalized_name.title(),
                'instance': strategy,
                'params': params,
                'start_time': datetime.now(),
                'transactions': 0,
                'profit': 0.0,
                'currency': 'USD'
            }
        
        return {
            'success': True, 
            'message': f"Stratégie {normalized_name} démarrée avec les paramètres:\n" + 
                      "\n".join([f"- {k}: {v}" for k, v in params.items()]) if params else "Aucun paramètre spécifié"
        }
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de la stratégie {normalized_name}: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

async def _stop_strategy_internal(strategy_id_or_name: str, bot_state: Any) -> Dict[str, Any]:
    """
    Fonction interne pour arrêter une stratégie.
    """
    global BOT_STATE
    BOT_STATE = bot_state
    
    if not BOT_STATE or not hasattr(BOT_STATE, 'active_strategies'):
        return {'success': False, 'error': "Aucune stratégie active"}
    
    # Chercher la stratégie par ID ou par nom
    strategy_found = None
    strategy_id = None
    
    for sid, strategy in BOT_STATE.active_strategies.items():
        if sid == strategy_id_or_name or strategy['type'] == strategy_id_or_name:
            strategy_found = strategy
            strategy_id = sid
            break
    
    if not strategy_found:
        return {'success': False, 'error': f"Stratégie '{strategy_id_or_name}' non trouvée"}
    
    # Arrêter la stratégie
    try:
        instance = strategy_found.get('instance')
        if instance and hasattr(instance, 'stop'):
            await instance.stop()
        
        # Retirer la stratégie de l'état du bot
        del BOT_STATE.active_strategies[strategy_id]
        
        return {
            'success': True,
            'message': f"Stratégie {strategy_found['name']} arrêtée avec succès."
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt de la stratégie {strategy_id}: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

async def _get_active_strategies(bot_state: Any) -> List[Dict[str, Any]]:
    """
    Fonction interne pour récupérer les stratégies actives.
    """
    global BOT_STATE
    BOT_STATE = bot_state
    
    if not BOT_STATE or not hasattr(BOT_STATE, 'active_strategies'):
        return []
    
    # Créer une liste des stratégies actives sans l'instance (pour éviter des problèmes de sérialisation)
    result = []
    for strategy_id, strategy in BOT_STATE.active_strategies.items():
        strategy_copy = strategy.copy()
        if 'instance' in strategy_copy:
            del strategy_copy['instance']
        result.append(strategy_copy)
    
    return result

async def _configure_strategy_internal(strategy_name: str, params: Dict[str, Any], bot_state: Any) -> Dict[str, Any]:
    """
    Fonction interne pour configurer une stratégie.
    """
    global BOT_STATE
    BOT_STATE = bot_state
    
    strategy_map = {
        'sniper': 'token_sniper',
        'token_sniper': 'token_sniper',
        'arbitrage': 'arbitrage',
        'profit_taker': 'profit_taker',
        'smart_profit_taker': 'profit_taker',
        'auto': 'auto_trader',
        'auto_trader': 'auto_trader'
    }
    
    normalized_name = strategy_map.get(strategy_name.lower())
    if not normalized_name:
        return {'success': False, 'error': f"Stratégie '{strategy_name}' non reconnue"}
    
    # Vérifier si la stratégie est disponible
    if normalized_name == 'token_sniper' and not TOKEN_SNIPER_AVAILABLE:
        return {'success': False, 'error': "Module Token Sniper non disponible"}
    elif normalized_name == 'arbitrage' and not ARBITRAGE_ENGINE_AVAILABLE:
        return {'success': False, 'error': "Module Arbitrage Engine non disponible"}
    elif normalized_name == 'profit_taker' and not PROFIT_TAKER_AVAILABLE:
        return {'success': False, 'error': "Module Smart Profit Taker non disponible"}
    elif normalized_name == 'auto_trader' and not AUTO_TRADER_AVAILABLE:
        return {'success': False, 'error': "Module Auto Trader non disponible"}
    
    # Si la stratégie est active, mettre à jour sa configuration
    if BOT_STATE and hasattr(BOT_STATE, 'active_strategies'):
        for strategy_id, strategy in BOT_STATE.active_strategies.items():
            if strategy['type'] == normalized_name:
                # Mettre à jour les paramètres
                instance = strategy.get('instance')
                if instance and hasattr(instance, 'configure'):
                    await instance.configure(params)
                
                # Mettre à jour les paramètres dans l'état
                strategy['params'].update(params)
                
                return {
                    'success': True,
                    'message': f"Configuration de {strategy['name']} mise à jour avec:\n" + 
                              "\n".join([f"- {k}: {v}" for k, v in params.items()])
                }
    
    # Si la stratégie n'est pas active, stocker les paramètres pour une utilisation future
    if not hasattr(BOT_STATE, 'strategy_configs'):
        BOT_STATE.strategy_configs = {}
    
    if normalized_name not in BOT_STATE.strategy_configs:
        BOT_STATE.strategy_configs[normalized_name] = {}
    
    BOT_STATE.strategy_configs[normalized_name].update(params)
    
    return {
        'success': True,
        'message': f"Configuration de {normalized_name} stockée pour une utilisation future:\n" + 
                  "\n".join([f"- {k}: {v}" for k, v in params.items()])
    }

# Gestionnaire pour les callbacks des boutons
async def strategy_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère les callbacks des boutons liés aux stratégies.
    """
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await query.edit_message_text("⛔ Vous n'êtes pas autorisé à utiliser cette fonction.")
            return
    
    # Traiter la callback data
    callback_data = query.data
    
    if callback_data.startswith("start_strategy_"):
        strategy_type = callback_data.replace("start_strategy_", "")
        try:
            result = await _start_strategy_internal(strategy_type, {}, context.bot_data.get('bot_state'))
            if result['success']:
                await query.edit_message_text(
                    f"✅ <b>Stratégie {strategy_type} démarrée avec succès!</b>\n\n"
                    f"{result.get('message', '')}",
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    f"❌ <b>Erreur lors du démarrage de la stratégie {strategy_type}</b>\n\n"
                    f"{result.get('error', 'Erreur inconnue')}",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la stratégie: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                f"❌ <b>Erreur lors du démarrage de la stratégie</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    elif callback_data.startswith("stop_strategy_"):
        strategy_id = callback_data.replace("stop_strategy_", "")
        try:
            result = await _stop_strategy_internal(strategy_id, context.bot_data.get('bot_state'))
            if result['success']:
                await query.edit_message_text(
                    f"✅ <b>Stratégie arrêtée avec succès!</b>\n\n"
                    f"{result.get('message', '')}",
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    f"❌ <b>Erreur lors de l'arrêt de la stratégie</b>\n\n"
                    f"{result.get('error', 'Erreur inconnue')}",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la stratégie: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                f"❌ <b>Erreur lors de l'arrêt de la stratégie</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )

# Fonction pour enregistrer les gestionnaires de commandes
def register_strategy_command_handlers(application):
    """
    Enregistre les gestionnaires de commandes liées aux stratégies.
    """
    application.add_handler(CommandHandler("start_strategy", start_strategy_command))
    application.add_handler(CommandHandler("stop_strategy", stop_strategy_command))
    application.add_handler(CommandHandler("list_strategies", list_strategies_command))
    application.add_handler(CommandHandler("configure_strategy", configure_strategy_command))
    
    # Gestionnaire pour les callbacks des boutons
    application.add_handler(CallbackQueryHandler(
        strategy_button_callback, 
        pattern="^(start_strategy_|stop_strategy_)"
    )) 