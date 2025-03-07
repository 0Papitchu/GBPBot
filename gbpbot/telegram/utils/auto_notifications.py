"""
Utilitaires pour les notifications d'automatisation intelligente via Telegram.

Ce module fournit des fonctions pour envoyer des notifications automatiques
concernant le système d'automatisation intelligente du GBPBot via Telegram.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from gbpbot.telegram import send_notification

logger = logging.getLogger(__name__)

def format_market_conditions(market_conditions: Dict[str, str]) -> str:
    """
    Formate les conditions de marché pour l'affichage dans une notification.
    
    Args:
        market_conditions: Dictionnaire de conditions de marché
        
    Returns:
        Message formaté pour l'affichage
    """
    if not market_conditions:
        return "Conditions de marché: Non détectées"
    
    # Indicateurs visuels pour les conditions
    volatility = market_conditions.get('volatility', 'inconnue')
    trend = market_conditions.get('trend', 'inconnue')
    liquidity = market_conditions.get('liquidity', 'inconnue')
    opportunity = market_conditions.get('opportunity', 'inconnue')
    risk = market_conditions.get('risk', 'inconnue')
    
    volatility_emoji = {"low": "🟢", "normal": "🟡", "high": "🟠", "extreme": "🔴"}.get(volatility, "⚪")
    trend_emoji = {"bearish": "🔴", "neutral": "🟡", "bullish": "🟢"}.get(trend, "⚪")
    liquidity_emoji = {"low": "🔴", "normal": "🟡", "high": "🟢"}.get(liquidity, "⚪")
    opportunity_emoji = {"low": "🔴", "medium": "🟡", "high": "🟢"}.get(opportunity, "⚪")
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
    
    message = "*Conditions de marché détectées:*\n"
    message += f"• Volatilité: {volatility_emoji} {volatility.upper()}\n"
    message += f"• Tendance: {trend_emoji} {trend.upper()}\n"
    message += f"• Liquidité: {liquidity_emoji} {liquidity.upper()}\n"
    message += f"• Opportunités: {opportunity_emoji} {opportunity.upper()}\n"
    message += f"• Risque: {risk_emoji} {risk.upper()}"
    
    return message

def notify_market_conditions_change(bot_context: Dict[str, Any], market_conditions: Dict[str, str]) -> None:
    """
    Envoie une notification lorsque les conditions de marché changent significativement.
    
    Args:
        bot_context: Contexte du bot
        market_conditions: Nouvelles conditions de marché
    """
    # Vérifier si les notifications sont activées
    config = bot_context.get('config', {}).get('auto_optimization', {})
    notify_market_changes = config.get('notify_market_changes', True)
    
    if not notify_market_changes:
        logger.debug("Notifications de changement de marché désactivées")
        return
    
    # Vérifier si les conditions ont suffisamment changé pour justifier une notification
    prev_conditions = bot_context.get('prev_market_conditions', {})
    
    significant_change = False
    
    # Vérifier les changements importants
    for key in ['volatility', 'trend', 'risk']:
        if key in market_conditions and key in prev_conditions:
            if market_conditions[key] != prev_conditions.get(key):
                significant_change = True
                break
    
    if not significant_change and prev_conditions:
        logger.debug("Pas de changement significatif des conditions de marché")
        return
    
    # Mettre à jour les conditions précédentes
    bot_context['prev_market_conditions'] = market_conditions.copy()
    
    # Créer le message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"🔄 *Changement des conditions de marché* - {timestamp}\n\n"
        f"{format_market_conditions(market_conditions)}\n\n"
    )
    
    # Ajouter des recommandations selon les conditions
    if market_conditions.get('volatility') == 'high' or market_conditions.get('volatility') == 'extreme':
        message += "\n⚠️ *Forte volatilité détectée* - Ajustement automatique des stratégies en cours..."
    
    if market_conditions.get('risk') == 'high':
        message += "\n🛑 *Risque élevé détecté* - Réduction automatique de l'exposition..."
    
    if market_conditions.get('opportunity') == 'high' and market_conditions.get('risk') != 'high':
        message += "\n✨ *Opportunités élevées détectées* - Augmentation de l'allocation de capital..."
    
    # Ajouter un clavier pour les actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Voir détails", callback_data="auto_status")],
        [InlineKeyboardButton("⚙️ Configurer", callback_data="auto_config")]
    ])
    
    # Envoyer la notification
    send_notification(bot_context, message, keyboard)
    logger.info("Notification de changement de conditions de marché envoyée")

def notify_parameter_adjustment(bot_context: Dict[str, Any], strategy: str, params_changed: Dict[str, Dict[str, Any]]) -> None:
    """
    Envoie une notification lorsque des paramètres de stratégie sont ajustés automatiquement.
    
    Args:
        bot_context: Contexte du bot
        strategy: Nom de la stratégie modifiée
        params_changed: Dictionnaire des paramètres modifiés avec leurs anciennes et nouvelles valeurs
    """
    # Vérifier si les notifications sont activées
    config = bot_context.get('config', {}).get('auto_optimization', {})
    notify_parameter_changes = config.get('notify_parameter_changes', True)
    
    if not notify_parameter_changes:
        logger.debug("Notifications de changement de paramètres désactivées")
        return
    
    # Créer le message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"⚙️ *Ajustement automatique des paramètres* - {timestamp}\n\n"
        f"*Stratégie:* {strategy}\n\n"
        "*Paramètres ajustés:*\n"
    )
    
    # Ajouter les détails des paramètres modifiés
    for param, details in params_changed.items():
        old_value = details.get('old')
        new_value = details.get('new')
        reason = details.get('reason', 'Optimisation basée sur les conditions actuelles')
        
        message += f"• *{param}*:\n"
        message += f"  - Avant: `{old_value}`\n"
        message += f"  - Après: `{new_value}`\n"
        message += f"  - Raison: {reason}\n\n"
    
    # Ajouter un clavier pour les actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Voir détails", callback_data="auto_status")],
        [InlineKeyboardButton("↩️ Annuler changements", callback_data="auto_revert")]
    ])
    
    # Envoyer la notification
    send_notification(bot_context, message, keyboard)
    logger.info(f"Notification d'ajustement de paramètres pour {strategy} envoyée")

def notify_capital_allocation(bot_context: Dict[str, Any], allocations: Dict[str, float], 
                             previous_allocations: Dict[str, float]) -> None:
    """
    Envoie une notification lorsque l'allocation de capital est modifiée.
    
    Args:
        bot_context: Contexte du bot
        allocations: Nouvelles allocations par stratégie
        previous_allocations: Anciennes allocations par stratégie
    """
    # Vérifier si les notifications sont activées
    config = bot_context.get('config', {}).get('auto_optimization', {})
    notify_allocation_changes = config.get('notify_allocation_changes', True)
    
    if not notify_allocation_changes:
        logger.debug("Notifications de changement d'allocation désactivées")
        return
    
    # Vérifier si les allocations ont suffisamment changé
    significant_change = False
    for strategy, allocation in allocations.items():
        prev_allocation = previous_allocations.get(strategy, 0.0)
        if abs(allocation - prev_allocation) > 0.05:  # 5% de changement minimum
            significant_change = True
            break
    
    if not significant_change:
        logger.debug("Pas de changement significatif dans l'allocation de capital")
        return
    
    # Créer le message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"💰 *Réallocation automatique du capital* - {timestamp}\n\n"
        "*Nouvelles allocations:*\n"
    )
    
    # Ajouter les détails des allocations
    for strategy, allocation in allocations.items():
        prev_allocation = previous_allocations.get(strategy, 0.0)
        change = allocation - prev_allocation
        change_text = f"(+{change:.1%})" if change > 0 else f"({change:.1%})"
        
        # Emoji basé sur le changement
        emoji = "🔺" if change > 0.1 else "🔻" if change < -0.1 else "↔️"
        
        message += f"• *{strategy}*: {allocation:.1%} {change_text} {emoji}\n"
    
    # Ajouter la raison
    auto_optimizer = bot_context.get('auto_optimizer')
    market_conditions = {}
    
    if auto_optimizer:
        status = auto_optimizer.get_status()
        market_conditions = status.get('market_conditions', {})
    
    if market_conditions:
        message += f"\n{format_market_conditions(market_conditions)}"
    
    # Ajouter un clavier pour les actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Voir détails", callback_data="auto_status")],
        [InlineKeyboardButton("↩️ Annuler réallocation", callback_data="auto_revert_allocation")]
    ])
    
    # Envoyer la notification
    send_notification(bot_context, message, keyboard)
    logger.info("Notification de réallocation de capital envoyée")

def notify_error_recovery(bot_context: Dict[str, Any], error_type: str, action_taken: str, 
                         success: bool, details: str = "") -> None:
    """
    Envoie une notification lorsqu'un mécanisme de récupération d'erreur est activé.
    
    Args:
        bot_context: Contexte du bot
        error_type: Type d'erreur rencontrée
        action_taken: Action entreprise pour récupérer
        success: Si la récupération a réussi
        details: Détails supplémentaires
    """
    # Vérifier si les notifications sont activées
    config = bot_context.get('config', {}).get('auto_optimization', {})
    notify_error_recovery = config.get('notify_error_recovery', True)
    
    if not notify_error_recovery:
        logger.debug("Notifications de récupération d'erreur désactivées")
        return
    
    # Créer le message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_emoji = "✅" if success else "❌"
    
    message = (
        f"🔧 *Récupération automatique d'erreur* - {timestamp}\n\n"
        f"*Type d'erreur:* {error_type}\n"
        f"*Action entreprise:* {action_taken}\n"
        f"*Statut:* {status_emoji} {'Réussite' if success else 'Échec'}\n"
    )
    
    if details:
        message += f"*Détails:* {details}\n"
    
    # Ajouter un clavier pour les actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Voir l'état système", callback_data="auto_status")],
        [InlineKeyboardButton("🔍 Consulter les logs", callback_data="show_logs")]
    ])
    
    # Niveau de log en fonction du succès
    if success:
        logger.info(f"Récupération réussie pour l'erreur {error_type}")
    else:
        logger.warning(f"Échec de récupération pour l'erreur {error_type}")
    
    # Envoyer la notification
    send_notification(bot_context, message, keyboard)

def notify_performance_report(bot_context: Dict[str, Any], performance_data: Dict[str, Any]) -> None:
    """
    Envoie un rapport de performance automatisé via Telegram.
    
    Args:
        bot_context: Contexte du bot
        performance_data: Données de performance à inclure dans le rapport
    """
    # Vérifier si les notifications sont activées
    config = bot_context.get('config', {}).get('auto_optimization', {})
    notify_performance = config.get('notify_performance_reports', True)
    
    if not notify_performance:
        logger.debug("Notifications de rapport de performance désactivées")
        return
    
    # Extraire les données de performance
    total_pnl = performance_data.get('total_pnl', 0.0)
    period_pnl = performance_data.get('period_pnl', 0.0)
    period_text = performance_data.get('period', '24h')
    strategies = performance_data.get('strategies', {})
    
    # Créer le message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Emoji basé sur la performance
    emoji = "🔥" if period_pnl > 5.0 else "📈" if period_pnl > 0 else "📉" if period_pnl < 0 else "↔️"
    
    message = (
        f"{emoji} *Rapport de Performance Automatisé* - {timestamp}\n\n"
        f"*Performance {period_text}:* {period_pnl:+.2f}%\n"
        f"*PnL total:* {total_pnl:+.2f}%\n\n"
    )
    
    # Ajouter les performances par stratégie
    if strategies:
        message += "*Performance par stratégie:*\n"
        
        for strategy, data in strategies.items():
            strategy_pnl = data.get('pnl', 0.0)
            trades = data.get('trades', 0)
            win_rate = data.get('win_rate', 0.0)
            
            # Emoji basé sur la performance de la stratégie
            strategy_emoji = "🟢" if strategy_pnl > 3.0 else "🟡" if strategy_pnl > 0 else "🔴"
            
            message += f"• {strategy_emoji} *{strategy}*: {strategy_pnl:+.2f}% ({trades} trades, {win_rate:.1f}% win)\n"
    
    # Ajouter les recommandations d'optimisation
    recommendations = performance_data.get('recommendations', [])
    
    if recommendations:
        message += "\n*Recommandations d'optimisation:*\n"
        
        for rec in recommendations:
            message += f"• {rec}\n"
    
    # Ajouter un clavier pour les actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Voir rapport détaillé", callback_data="trading_stats")],
        [InlineKeyboardButton("⚙️ Optimisations recommandées", callback_data="auto_recommendations")]
    ])
    
    # Envoyer la notification
    send_notification(bot_context, message, keyboard)
    logger.info("Rapport de performance automatisé envoyé")

__all__ = [
    'notify_market_conditions_change',
    'notify_parameter_adjustment',
    'notify_capital_allocation',
    'notify_error_recovery',
    'notify_performance_report',
] 