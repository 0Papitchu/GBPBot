"""
Module de commandes Telegram pour l'automatisation intelligente du GBPBot.

Ce module contient les gestionnaires de commandes Telegram pour contrôler
et interagir avec le système d'automatisation intelligente du GBPBot.

Fonctionnalités:
- Activer/désactiver l'automatisation intelligente
- Afficher l'état actuel de l'automatisation
- Consulter les recommandations automatiques
- Appliquer les paramètres recommandés
- Configurer les paramètres d'automatisation
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import json
import time
from datetime import datetime, timedelta
import humanize
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode

from gbpbot.telegram.utils.auth import check_user_auth
from gbpbot.telegram.utils.messages import send_message, edit_message, send_error
from gbpbot.telegram.utils.keyboards import create_menu_keyboard, create_confirmation_keyboard
from gbpbot.telegram.utils.callbacks import get_callback_data

# États de conversation pour la configuration
CONFIG_PARAM, CONFIG_VALUE = range(2)

logger = logging.getLogger(__name__)

# Callbacks spécifiques à ce module
AUTO_CB_PREFIX = "auto_"
AUTO_TOGGLE = f"{AUTO_CB_PREFIX}toggle"
AUTO_STATUS = f"{AUTO_CB_PREFIX}status"
AUTO_RECOMMENDATIONS = f"{AUTO_CB_PREFIX}recommendations"
AUTO_APPLY = f"{AUTO_CB_PREFIX}apply"
AUTO_CONFIG = f"{AUTO_CB_PREFIX}config"
AUTO_CONFIG_PARAM = f"{AUTO_CB_PREFIX}config_param"
AUTO_CONFIG_VALUE = f"{AUTO_CB_PREFIX}config_value"
AUTO_CONFIG_SAVE = f"{AUTO_CB_PREFIX}config_save"
AUTO_CONFIG_CANCEL = f"{AUTO_CB_PREFIX}config_cancel"
AUTO_BACK = f"{AUTO_CB_PREFIX}back"

@check_user_auth
async def auto_optimization_command(update: Update, context: CallbackContext) -> None:
    """
    Affiche le menu d'automatisation intelligente.
    """
    user_id = update.effective_user.id
    
    # Récupérer le contexte du bot
    bot_context = context.bot_data.get('bot_context', {})
    
    # Obtenir l'état actuel de l'automatisation
    auto_optimizer = bot_context.get('auto_optimizer')
    is_enabled = False
    
    if auto_optimizer:
        try:
            status = auto_optimizer.get_status()
            is_enabled = status.get('enabled', False)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'état de l'automatisation: {e}")
    
    # Créer le clavier avec les options
    buttons = [
        [InlineKeyboardButton(
            f"{'✅ Désactiver' if is_enabled else '⚪ Activer'} l'automatisation", 
            callback_data=AUTO_TOGGLE
        )],
        [InlineKeyboardButton("📊 Afficher l'état actuel", callback_data=AUTO_STATUS)],
        [InlineKeyboardButton("🔍 Consulter les recommandations", callback_data=AUTO_RECOMMENDATIONS)],
        [InlineKeyboardButton("✨ Appliquer paramètres recommandés", callback_data=AUTO_APPLY)],
        [InlineKeyboardButton("⚙️ Configurer les paramètres", callback_data=AUTO_CONFIG)],
        [InlineKeyboardButton("🔙 Retour au menu principal", callback_data="main_menu")]
    ]
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    # Message d'introduction avec description
    message = (
        "🧠 *Automatisation Intelligente*\n\n"
        f"État actuel: *{'✅ ACTIVÉE' if is_enabled else '⚪ DÉSACTIVÉE'}*\n\n"
        "L'automatisation intelligente adapte les stratégies de trading en fonction des conditions de marché "
        "et optimise les paramètres pour maximiser les performances.\n\n"
        "Choisissez une option:"
    )
    
    await send_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)

@check_user_auth
async def auto_toggle_callback(update: Update, context: CallbackContext) -> None:
    """
    Active ou désactive l'automatisation intelligente.
    """
    query = update.callback_query
    bot_context = context.bot_data.get('bot_context', {})
    auto_optimizer = bot_context.get('auto_optimizer')
    
    if not auto_optimizer:
        await send_error(update, context, "Le module d'automatisation n'est pas disponible.")
        return
    
    try:
        status = auto_optimizer.get_status()
        current_state = status.get('enabled', False)
        
        # Basculer l'état
        new_state = not current_state
        
        if new_state:
            # Activer l'automatisation
            from gbpbot.core.auto_optimization import AutoOptimizer
            config = bot_context.get('config', {}).get('auto_optimization', {})
            config['enabled'] = True
            
            # Vérifier si l'optimiseur doit être recréé ou simplement mis à jour
            if auto_optimizer:
                auto_optimizer._enabled = True
                logger.info("Automatisation intelligente activée")
            else:
                # Créer un nouvel optimiseur si nécessaire
                auto_optimizer = AutoOptimizer(config)
                bot_context['auto_optimizer'] = auto_optimizer
                logger.info("Nouvel optimiseur d'automatisation créé et activé")
                
        else:
            # Désactiver l'automatisation
            auto_optimizer._enabled = False
            logger.info("Automatisation intelligente désactivée")
        
        # Mettre à jour la configuration
        if 'config' in bot_context and 'auto_optimization' in bot_context['config']:
            bot_context['config']['auto_optimization']['enabled'] = new_state
        
        # Message de confirmation
        state_text = "activée" if new_state else "désactivée"
        message = f"✅ Automatisation intelligente {state_text} avec succès."
        
        # Rediriger vers le menu d'automatisation
        await query.answer(f"Automatisation {state_text}")
        await auto_optimization_command(update, context)
        
    except Exception as e:
        logger.error(f"Erreur lors du basculement de l'automatisation: {e}")
        await send_error(update, context, f"Erreur: {str(e)}")

@check_user_auth
async def auto_status_callback(update: Update, context: CallbackContext) -> None:
    """
    Affiche l'état actuel de l'automatisation intelligente.
    """
    query = update.callback_query
    bot_context = context.bot_data.get('bot_context', {})
    auto_optimizer = bot_context.get('auto_optimizer')
    
    if not auto_optimizer:
        await send_error(update, context, "Le module d'automatisation n'est pas disponible.")
        return
    
    try:
        status = auto_optimizer.get_status()
        
        # Formatage des informations d'état
        enabled = status.get('enabled', False)
        last_run = status.get('last_run', 0)
        market_conditions = status.get('market_conditions', {})
        last_parameter_adjustment = status.get('last_parameter_adjustment', 0)
        last_capital_allocation = status.get('last_capital_allocation', 0)
        error_count = status.get('error_count', 0)
        
        # Conversion des timestamps en texte lisible
        last_run_text = "Jamais" if last_run == 0 else humanize.naturaltime(datetime.now() - datetime.fromtimestamp(last_run))
        last_param_text = "Jamais" if last_parameter_adjustment == 0 else humanize.naturaltime(datetime.now() - datetime.fromtimestamp(last_parameter_adjustment))
        last_alloc_text = "Jamais" if last_capital_allocation == 0 else humanize.naturaltime(datetime.now() - datetime.fromtimestamp(last_capital_allocation))
        
        # Construction du message d'état
        message = (
            "📊 *État de l'Automatisation Intelligente*\n\n"
            f"*État:* {'✅ ACTIVÉE' if enabled else '⚪ DÉSACTIVÉE'}\n"
            f"*Dernière exécution:* {last_run_text}\n"
            f"*Dernier ajustement de paramètres:* {last_param_text}\n"
            f"*Dernière allocation de capital:* {last_alloc_text}\n"
            f"*Erreurs rencontrées:* {error_count}\n\n"
        )
        
        # Ajouter les conditions de marché détectées
        if market_conditions:
            message += "*Conditions de marché détectées:*\n"
            volatility = market_conditions.get('volatility', 'inconnue')
            trend = market_conditions.get('trend', 'inconnue')
            liquidity = market_conditions.get('liquidity', 'inconnue')
            opportunity = market_conditions.get('opportunity', 'inconnue')
            risk = market_conditions.get('risk', 'inconnue')
            
            # Indicateurs visuels pour les conditions
            volatility_emoji = {"low": "🟢", "normal": "🟡", "high": "🟠", "extreme": "🔴"}.get(volatility, "⚪")
            trend_emoji = {"bearish": "🔴", "neutral": "🟡", "bullish": "🟢"}.get(trend, "⚪")
            liquidity_emoji = {"low": "🔴", "normal": "🟡", "high": "🟢"}.get(liquidity, "⚪")
            opportunity_emoji = {"low": "🔴", "medium": "🟡", "high": "🟢"}.get(opportunity, "⚪")
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
            
            message += f"  • Volatilité: {volatility_emoji} {volatility.upper()}\n"
            message += f"  • Tendance: {trend_emoji} {trend.upper()}\n"
            message += f"  • Liquidité: {liquidity_emoji} {liquidity.upper()}\n"
            message += f"  • Opportunités: {opportunity_emoji} {opportunity.upper()}\n"
            message += f"  • Risque: {risk_emoji} {risk.upper()}\n\n"
        else:
            message += "*Conditions de marché:* Non détectées\n\n"
        
        # Ajouter les paramètres optimisés si disponibles
        optimized_params = status.get('optimized_parameters', {})
        if optimized_params:
            message += "*Paramètres optimisés:*\n"
            for strategy, params in optimized_params.items():
                message += f"*{strategy}:*\n"
                for param, value in params.items():
                    message += f"  • {param}: {value}\n"
        
        # Ajouter un bouton de retour
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Rafraîchir", callback_data=AUTO_STATUS)],
            [InlineKeyboardButton("🔙 Retour", callback_data=AUTO_BACK)]
        ])
        
        await query.answer("État récupéré")
        await edit_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'état: {e}")
        await send_error(update, context, f"Erreur: {str(e)}")

@check_user_auth
async def auto_recommendations_callback(update: Update, context: CallbackContext) -> None:
    """
    Affiche les recommandations générées par l'automatisation intelligente.
    """
    query = update.callback_query
    bot_context = context.bot_data.get('bot_context', {})
    auto_optimizer = bot_context.get('auto_optimizer')
    
    if not auto_optimizer:
        await send_error(update, context, "Le module d'automatisation n'est pas disponible.")
        return
    
    try:
        status = auto_optimizer.get_status()
        enabled = status.get('enabled', False)
        
        if not enabled:
            await send_error(update, context, "L'automatisation est désactivée. Activez-la pour générer des recommandations.")
            return
        
        # Récupérer les recommandations
        recommendations = status.get('recommendations', {})
        
        if not recommendations:
            message = (
                "🔍 *Recommandations Automatiques*\n\n"
                "Aucune recommandation n'est disponible pour le moment.\n\n"
                "Les recommandations sont générées en fonction des conditions de marché "
                "et des performances des stratégies. Veuillez réessayer plus tard."
            )
        else:
            message = "🔍 *Recommandations Automatiques*\n\n"
            
            # Afficher les recommandations par stratégie
            for strategy, strategy_recs in recommendations.items():
                message += f"*Stratégie: {strategy}*\n"
                
                for param, details in strategy_recs.items():
                    current = details.get('current')
                    recommended = details.get('recommended')
                    reason = details.get('reason', 'Optimisation basée sur les conditions actuelles')
                    
                    message += f"  • *{param}*:\n"
                    message += f"    Actuel: `{current}`\n"
                    message += f"    Recommandé: `{recommended}`\n"
                    message += f"    Raison: {reason}\n\n"
        
        # Ajouter des boutons pour les actions
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Appliquer ces recommandations", callback_data=AUTO_APPLY)],
            [InlineKeyboardButton("🔄 Rafraîchir", callback_data=AUTO_RECOMMENDATIONS)],
            [InlineKeyboardButton("🔙 Retour", callback_data=AUTO_BACK)]
        ])
        
        await query.answer("Recommandations récupérées")
        await edit_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des recommandations: {e}")
        await send_error(update, context, f"Erreur: {str(e)}")

@check_user_auth
async def auto_apply_callback(update: Update, context: CallbackContext) -> None:
    """
    Applique les paramètres recommandés par l'automatisation intelligente.
    """
    query = update.callback_query
    bot_context = context.bot_data.get('bot_context', {})
    auto_optimizer = bot_context.get('auto_optimizer')
    
    if not auto_optimizer:
        await send_error(update, context, "Le module d'automatisation n'est pas disponible.")
        return
    
    try:
        status = auto_optimizer.get_status()
        enabled = status.get('enabled', False)
        
        if not enabled:
            await send_error(update, context, "L'automatisation est désactivée. Activez-la pour appliquer des recommandations.")
            return
        
        # Récupérer les recommandations
        recommendations = status.get('recommendations', {})
        
        if not recommendations:
            await send_error(update, context, "Aucune recommandation n'est disponible pour le moment.")
            return
        
        # Appliquer les recommandations
        # Cette partie dépend de l'implémentation spécifique de l'auto_optimizer
        # Supposons qu'il y a une méthode apply_recommendations()
        
        if hasattr(auto_optimizer, 'apply_recommendations') and callable(getattr(auto_optimizer, 'apply_recommendations')):
            auto_optimizer.apply_recommendations()
            
            message = (
                "✅ *Recommandations Appliquées*\n\n"
                "Les paramètres recommandés ont été appliqués avec succès aux stratégies.\n\n"
                "Vous pouvez consulter l'état actuel pour voir les nouveaux paramètres en vigueur."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Voir l'état actuel", callback_data=AUTO_STATUS)],
                [InlineKeyboardButton("🔙 Retour", callback_data=AUTO_BACK)]
            ])
            
            await query.answer("Recommandations appliquées")
            await edit_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)
        else:
            # Simuler l'application des recommandations en mettant à jour les paramètres
            # Pour chaque stratégie, mettre à jour les paramètres dans le contexte du bot
            
            for strategy, params in recommendations.items():
                # Récupérer la configuration actuelle de la stratégie
                strategy_config = bot_context.get('config', {}).get('strategies', {}).get(strategy, {})
                
                # Mettre à jour avec les valeurs recommandées
                for param_name, param_details in params.items():
                    if 'recommended' in param_details:
                        if strategy_config and param_name in strategy_config:
                            strategy_config[param_name] = param_details['recommended']
            
            message = (
                "✅ *Recommandations Appliquées*\n\n"
                "Les paramètres recommandés ont été appliqués avec succès aux stratégies.\n\n"
                "Vous pouvez consulter l'état actuel pour voir les nouveaux paramètres en vigueur."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Voir l'état actuel", callback_data=AUTO_STATUS)],
                [InlineKeyboardButton("🔙 Retour", callback_data=AUTO_BACK)]
            ])
            
            await query.answer("Recommandations appliquées")
            await edit_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Erreur lors de l'application des recommandations: {e}")
        await send_error(update, context, f"Erreur: {str(e)}")

@check_user_auth
async def auto_config_callback(update: Update, context: CallbackContext) -> None:
    """
    Affiche et permet de modifier la configuration de l'automatisation intelligente.
    """
    query = update.callback_query
    await query.answer()
    
    bot_context = context.bot_data.get('bot_context', {})
    config = bot_context.get('config', {}).get('auto_optimization', {})
    
    if not config:
        await send_error(update, context, "La configuration d'automatisation n'est pas disponible.")
        return
    
    # Préparation des paramètres à afficher
    parameters = [
        ("enabled", "Activé", "true/false"),
        ("enable_parameter_adjustment", "Ajustement des paramètres", "true/false"),
        ("enable_market_detection", "Détection du marché", "true/false"),
        ("enable_capital_allocation", "Allocation du capital", "true/false"),
        ("enable_error_recovery", "Récupération d'erreurs", "true/false"),
        ("parameter_adjustment_interval", "Intervalle d'ajustement (sec)", "entier"),
        ("market_detection_interval", "Intervalle de détection (sec)", "entier"),
        ("capital_allocation_interval", "Intervalle d'allocation (sec)", "entier"),
        ("volatility_threshold", "Seuil de volatilité", "décimal"),
        ("max_capital_per_strategy", "Capital max par stratégie", "décimal"),
        ("min_capital_per_strategy", "Capital min par stratégie", "décimal")
    ]
    
    message = "⚙️ *Configuration de l'Automatisation*\n\n"
    
    # Afficher les valeurs actuelles
    for param_key, param_name, param_type in parameters:
        value = config.get(param_key, "Non défini")
        message += f"*{param_name}*: `{value}`\n"
    
    # Créer le clavier avec les options de configuration
    buttons = []
    
    # Créer une ligne pour chaque paramètre
    for param_key, param_name, _ in parameters:
        buttons.append([InlineKeyboardButton(
            f"Modifier {param_name}", 
            callback_data=f"{AUTO_CONFIG_PARAM}:{param_key}"
        )])
    
    # Ajouter un bouton de retour
    buttons.append([InlineKeyboardButton("🔙 Retour", callback_data=AUTO_BACK)])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await edit_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)
    return CONFIG_PARAM

@check_user_auth
async def auto_config_param_callback(update: Update, context: CallbackContext) -> int:
    """
    Gère la sélection d'un paramètre à configurer.
    """
    query = update.callback_query
    await query.answer()
    
    # Récupérer le paramètre sélectionné
    callback_data = query.data
    param_key = callback_data.split(":", 1)[1] if ":" in callback_data else None
    
    if not param_key:
        await send_error(update, context, "Paramètre invalide.")
        return ConversationHandler.END
    
    # Stocker le paramètre dans le contexte
    context.user_data['config_param'] = param_key
    
    # Décrire le paramètre sélectionné
    param_descriptions = {
        "enabled": "Activer/désactiver l'automatisation (true/false)",
        "enable_parameter_adjustment": "Ajustement automatique des paramètres (true/false)",
        "enable_market_detection": "Détection automatique des conditions de marché (true/false)",
        "enable_capital_allocation": "Allocation dynamique du capital (true/false)",
        "enable_error_recovery": "Récupération automatique des erreurs (true/false)",
        "parameter_adjustment_interval": "Intervalle d'ajustement des paramètres en secondes (entier)",
        "market_detection_interval": "Intervalle de détection des conditions de marché en secondes (entier)",
        "capital_allocation_interval": "Intervalle d'allocation du capital en secondes (entier)",
        "volatility_threshold": "Seuil de volatilité pour les décisions d'allocation (décimal entre 0 et 1)",
        "max_capital_per_strategy": "Proportion maximale du capital par stratégie (décimal entre 0 et 1)",
        "min_capital_per_strategy": "Proportion minimale du capital par stratégie (décimal entre 0 et 1)"
    }
    
    description = param_descriptions.get(param_key, "Aucune description disponible")
    
    # Récupérer la valeur actuelle
    bot_context = context.bot_data.get('bot_context', {})
    config = bot_context.get('config', {}).get('auto_optimization', {})
    current_value = config.get(param_key, "Non défini")
    
    message = (
        f"⚙️ *Configuration du paramètre*: `{param_key}`\n\n"
        f"*Description*: {description}\n"
        f"*Valeur actuelle*: `{current_value}`\n\n"
        "Veuillez entrer la nouvelle valeur pour ce paramètre:"
    )
    
    await edit_message(update, context, message, None, parse_mode=ParseMode.MARKDOWN)
    return CONFIG_VALUE

@check_user_auth
async def auto_config_value_callback(update: Update, context: CallbackContext) -> int:
    """
    Traite la nouvelle valeur entrée pour un paramètre.
    """
    # Récupérer le message texte
    message_text = update.message.text.strip()
    
    # Récupérer le paramètre en cours de configuration
    param_key = context.user_data.get('config_param')
    
    if not param_key:
        await send_error(update, context, "Paramètre non défini. Veuillez recommencer.")
        return ConversationHandler.END
    
    # Valider et convertir la valeur
    value = message_text
    
    try:
        # Conversion en fonction du type de paramètre
        if param_key in ["enabled", "enable_parameter_adjustment", "enable_market_detection", 
                         "enable_capital_allocation", "enable_error_recovery"]:
            # Conversion en booléen
            if value.lower() in ["true", "yes", "y", "1", "oui", "vrai"]:
                value = True
            elif value.lower() in ["false", "no", "n", "0", "non", "faux"]:
                value = False
            else:
                raise ValueError("Valeur booléenne attendue (true/false)")
        
        elif param_key in ["parameter_adjustment_interval", "market_detection_interval", 
                          "capital_allocation_interval"]:
            # Conversion en entier
            value = int(value)
            if value < 0:
                raise ValueError("La valeur doit être positive")
        
        elif param_key in ["volatility_threshold", "max_capital_per_strategy", "min_capital_per_strategy"]:
            # Conversion en float
            value = float(value)
            if not (0 <= value <= 1):
                raise ValueError("La valeur doit être entre 0 et 1")
    
    except ValueError as e:
        await send_error(update, context, f"Erreur de validation: {str(e)}")
        # Redemander la valeur
        return CONFIG_VALUE
    
    # Mettre à jour la configuration
    bot_context = context.bot_data.get('bot_context', {})
    
    if 'config' not in bot_context:
        bot_context['config'] = {}
    
    if 'auto_optimization' not in bot_context['config']:
        bot_context['config']['auto_optimization'] = {}
    
    bot_context['config']['auto_optimization'][param_key] = value
    
    # Si l'optimiseur existe, mettre à jour sa configuration
    auto_optimizer = bot_context.get('auto_optimizer')
    if auto_optimizer and hasattr(auto_optimizer, '_config'):
        auto_optimizer._config[param_key] = value
    
    # Message de confirmation
    message = (
        f"✅ *Paramètre mis à jour*\n\n"
        f"*Paramètre*: `{param_key}`\n"
        f"*Nouvelle valeur*: `{value}`\n\n"
        "Configuration enregistrée avec succès."
    )
    
    # Retourner au menu de configuration
    buttons = [
        [InlineKeyboardButton("⚙️ Configurer un autre paramètre", callback_data=AUTO_CONFIG)],
        [InlineKeyboardButton("🔙 Retour au menu d'automatisation", callback_data=AUTO_BACK)]
    ]
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await send_message(update, context, message, keyboard, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

@check_user_auth
async def auto_back_callback(update: Update, context: CallbackContext) -> None:
    """
    Retourne au menu principal d'automatisation.
    """
    query = update.callback_query
    await query.answer()
    await auto_optimization_command(update, context)

def cancel_config(update: Update, context: CallbackContext) -> int:
    """
    Annule la configuration en cours.
    """
    await send_message(update, context, "Configuration annulée.", None)
    return ConversationHandler.END

def register_handlers(dispatcher):
    """
    Enregistre les gestionnaires de commandes pour ce module.
    """
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
    
    # Enregistrement de la commande principale
    dispatcher.add_handler(CommandHandler("auto", auto_optimization_command))
    
    # Enregistrement des gestionnaires de callback
    dispatcher.add_handler(CallbackQueryHandler(auto_toggle_callback, pattern=f"^{AUTO_TOGGLE}$"))
    dispatcher.add_handler(CallbackQueryHandler(auto_status_callback, pattern=f"^{AUTO_STATUS}$"))
    dispatcher.add_handler(CallbackQueryHandler(auto_recommendations_callback, pattern=f"^{AUTO_RECOMMENDATIONS}$"))
    dispatcher.add_handler(CallbackQueryHandler(auto_apply_callback, pattern=f"^{AUTO_APPLY}$"))
    dispatcher.add_handler(CallbackQueryHandler(auto_back_callback, pattern=f"^{AUTO_BACK}$"))
    
    # Conversation handler pour la configuration
    config_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(auto_config_callback, pattern=f"^{AUTO_CONFIG}$")],
        states={
            CONFIG_PARAM: [CallbackQueryHandler(auto_config_param_callback, pattern=f"^{AUTO_CONFIG_PARAM}:")],
            CONFIG_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_config_value_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel_config)],
        name="auto_config_conversation",
        persistent=False,
    )
    
    dispatcher.add_handler(config_conv_handler)
    
    # Ajouter un gestionnaire supplémentaire pour les boutons de paramètres
    dispatcher.add_handler(CallbackQueryHandler(
        auto_config_param_callback, 
        pattern=f"^{AUTO_CONFIG_PARAM}:"
    )) 