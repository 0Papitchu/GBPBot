#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de commandes Telegram pour l'optimisation automatique des stratégies du GBPBot.

Ce module fournit des commandes pour lancer des optimisations de stratégies et consulter 
les résultats des optimisations précédentes.

Fonctionnalités:
- Lancement d'optimisations de paramètres pour les stratégies
- Affichage des résultats d'optimisation
- Visualisation graphique des performances
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union, cast
from datetime import datetime, timedelta

# Imports conditionnels des modules Telegram
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("Modules Telegram non disponibles. Fonctionnalités d'optimisation désactivées.")

# Imports internes conditionnels
try:
    from gbpbot.ai.optimization.auto_optimizer import AutoOptimizer, OptimizationResult
    from gbpbot.ai.optimization.visualization import PerformanceVisualizer
    AUTO_OPTIMIZER_AVAILABLE = True
except ImportError:
    AUTO_OPTIMIZER_AVAILABLE = False
    logging.warning("Module d'optimisation automatique non disponible.")

# Logger
logger = logging.getLogger(__name__)

# Constantes
OPTIMIZATION_STRATEGIES = ["token_sniper", "arbitrage", "scalping", "smart_trading"]
DEFAULT_OPTIMIZATION_PARAMS = {
    "iterations": 50,
    "population_size": 30,
    "mutation_rate": 0.1,
    "crossover_rate": 0.7
}

# Cache pour les optimisations en cours et les résultats
RUNNING_OPTIMIZATIONS: Dict[str, Dict[str, Any]] = {}
OPTIMIZATION_RESULTS: Dict[str, Dict[str, Any]] = {}

async def run_optimization_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Lance une optimisation automatique des paramètres d'une stratégie.
    
    Usage: /optimize [stratégie] [jours_historique] [--mode=bayesian|genetic|grid] [--detail]
    
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
    
    # Vérifier si l'optimiseur automatique est disponible
    if not AUTO_OPTIMIZER_AVAILABLE:
        await update.effective_message.reply_text(
            "❌ Le module d'optimisation automatique n'est pas disponible. "
            "Assurez-vous que les dépendances sont installées."
        )
        return
    
    # Traiter les arguments de la commande
    args = context.args if context.args else []
    strategy = args[0] if len(args) > 0 and args[0] in OPTIMIZATION_STRATEGIES else "token_sniper"
    history_days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30
    
    # Extraire les options supplémentaires
    options = {}
    for arg in args:
        if arg.startswith("--"):
            parts = arg[2:].split("=")
            if len(parts) == 2:
                key, value = parts
                options[key] = value
    
    # Mode d'optimisation (bayesian, genetic, grid)
    optimization_mode = options.get("mode", "bayesian").lower()
    if optimization_mode not in ["bayesian", "genetic", "grid"]:
        optimization_mode = "bayesian"
    
    # Niveau de détail
    detailed = "--detail" in args or options.get("detail") == "true"
    
    # Générer un ID unique pour cette optimisation
    optimization_id = f"{strategy}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Message d'attente
    wait_message = await update.effective_message.reply_text(
        f"⏳ Préparation de l'optimisation de la stratégie <b>{strategy}</b>...\n"
        f"📊 Données historiques: <b>{history_days}</b> jours\n"
        f"🧠 Mode: <b>{optimization_mode.title()}</b>\n\n"
        "L'optimisation peut prendre quelques minutes...",
        parse_mode="HTML"
    )
    
    # Configurer l'optimisation
    try:
        # Stocker les informations de cette optimisation
        RUNNING_OPTIMIZATIONS[optimization_id] = {
            "strategy": strategy,
            "history_days": history_days,
            "mode": optimization_mode,
            "start_time": datetime.now(),
            "status": "running",
            "user_id": update.effective_user.id,
            "chat_id": update.effective_chat.id if update.effective_chat else None
        }
        
        # Lancer l'optimisation en arrière-plan
        optimization_task = _run_optimization_task(
            optimization_id=optimization_id, 
            strategy=strategy, 
            history_days=history_days, 
            mode=optimization_mode, 
            detailed=detailed
        )
        
        # Ajouter des boutons pour voir les optimisations en cours/terminées
        keyboard = [
            [
                InlineKeyboardButton("🔄 Optimisations en cours", callback_data=f"opt_running"),
                InlineKeyboardButton("✅ Résultats précédents", callback_data=f"opt_results")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await wait_message.edit_text(
            f"🚀 <b>Optimisation lancée</b> 🚀\n\n"
            f"ID: <code>{optimization_id}</code>\n"
            f"Stratégie: <b>{strategy}</b>\n"
            f"Données historiques: <b>{history_days}</b> jours\n"
            f"Mode: <b>{optimization_mode.title()}</b>\n\n"
            f"Pour voir le statut: <code>/optimization_status {optimization_id}</code>\n"
            f"Pour voir les résultats: <code>/optimization_results {optimization_id}</code>\n\n"
            f"Vous serez notifié lorsque l'optimisation sera terminée.",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
        logger.info(f"Optimisation {optimization_id} lancée pour la stratégie {strategy}")
        
    except Exception as e:
        logger.error(f"Erreur lors du lancement de l'optimisation: {str(e)}")
        await wait_message.edit_text(
            f"❌ <b>Erreur lors du lancement de l'optimisation</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )
        
        # Nettoyer l'optimisation en erreur
        if optimization_id in RUNNING_OPTIMIZATIONS:
            RUNNING_OPTIMIZATIONS[optimization_id]["status"] = "failed"
            RUNNING_OPTIMIZATIONS[optimization_id]["error"] = str(e)

async def view_optimization_results_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Affiche les résultats d'une optimisation précédente.
    
    Usage: /optimization_results [optimization_id]
    
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
    
    # Vérifier les arguments
    args = context.args if context.args else []
    
    # Si aucun ID n'est fourni, afficher la liste des optimisations disponibles
    if not args:
        await _list_available_optimizations(update, context)
        return
    
    optimization_id = args[0]
    
    # Vérifier si l'optimisation existe
    optimization_data = OPTIMIZATION_RESULTS.get(optimization_id)
    if not optimization_data:
        # Vérifier si c'est une optimisation en cours
        running_optimization = RUNNING_OPTIMIZATIONS.get(optimization_id)
        if running_optimization:
            status = running_optimization.get("status", "unknown")
            if status == "running":
                start_time = running_optimization.get("start_time", datetime.now())
                elapsed = datetime.now() - start_time
                
                await update.effective_message.reply_text(
                    f"⏳ <b>Optimisation en cours</b>\n\n"
                    f"ID: <code>{optimization_id}</code>\n"
                    f"Stratégie: <b>{running_optimization.get('strategy', 'unknown')}</b>\n"
                    f"Démarrée il y a: <b>{_format_timedelta(elapsed)}</b>\n\n"
                    f"Veuillez patienter jusqu'à la fin de l'optimisation pour voir les résultats.",
                    parse_mode="HTML"
                )
            else:
                await update.effective_message.reply_text(
                    f"❌ <b>Optimisation terminée avec erreur</b>\n\n"
                    f"ID: <code>{optimization_id}</code>\n"
                    f"Statut: <b>{status}</b>\n"
                    f"Erreur: {running_optimization.get('error', 'Inconnue')}",
                    parse_mode="HTML"
                )
        else:
            await update.effective_message.reply_text(
                f"❌ Aucune optimisation trouvée avec l'ID <code>{optimization_id}</code>.\n\n"
                f"Utilisez la commande sans argument pour voir la liste des optimisations disponibles:",
                parse_mode="HTML"
            )
        return
    
    # Récupérer les résultats de l'optimisation
    results = optimization_data.get("results", {})
    best_params = results.get("best_params", {})
    metrics = results.get("metrics", {})
    
    # Formats les résultats
    best_params_str = "\n".join([f"• <b>{k}</b>: {v}" for k, v in best_params.items()])
    
    message = (
        f"✅ <b>Résultats d'optimisation</b>\n\n"
        f"ID: <code>{optimization_id}</code>\n"
        f"Stratégie: <b>{optimization_data.get('strategy', 'unknown')}</b>\n"
        f"Mode: <b>{optimization_data.get('mode', 'unknown').title()}</b>\n"
        f"Durée: <b>{optimization_data.get('duration', 'N/A')}</b>\n\n"
        f"<b>Meilleurs Paramètres:</b>\n{best_params_str}\n\n"
        f"<b>Performances:</b>\n"
        f"• ROI: <b>{metrics.get('roi', 0):.2f}%</b>\n"
        f"• Profit moyen: <b>{metrics.get('avg_profit', 0):.2f}%</b>\n"
        f"• Win rate: <b>{metrics.get('win_rate', 0):.2f}%</b>\n"
        f"• Trades: <b>{metrics.get('total_trades', 0)}</b>\n"
        f"• Sharpe ratio: <b>{metrics.get('sharpe_ratio', 0):.2f}</b>"
    )
    
    # Ajouter des boutons pour les actions supplémentaires
    keyboard = [
        [
            InlineKeyboardButton("📊 Graphique performance", callback_data=f"opt_chart_{optimization_id}"),
            InlineKeyboardButton("📋 Rapport détaillé", callback_data=f"opt_report_{optimization_id}")
        ],
        [
            InlineKeyboardButton("✅ Appliquer paramètres", callback_data=f"opt_apply_{optimization_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.effective_message.reply_text(
        message,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def optimization_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère les callbacks des boutons liés aux optimisations.
    
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
    
    # Acquitter le callback
    await query.answer()
    
    # Traiter les différents types de callbacks
    if data == "opt_running":
        # Afficher les optimisations en cours
        message = "<b>🔄 Optimisations en cours</b>\n\n"
        running_count = 0
        
        for opt_id, opt_data in RUNNING_OPTIMIZATIONS.items():
            if opt_data.get("status") == "running":
                running_count += 1
                start_time = opt_data.get("start_time", datetime.now())
                elapsed = datetime.now() - start_time
                
                message += (
                    f"• ID: <code>{opt_id}</code>\n"
                    f"  Stratégie: <b>{opt_data.get('strategy', 'unknown')}</b>\n"
                    f"  Démarrée il y a: <b>{_format_timedelta(elapsed)}</b>\n\n"
                )
        
        if running_count == 0:
            message += "Aucune optimisation en cours."
        
        await query.edit_message_text(
            message,
            parse_mode="HTML"
        )
    
    elif data == "opt_results":
        # Afficher les résultats d'optimisations précédentes
        message = "<b>✅ Résultats d'optimisations précédentes</b>\n\n"
        results_count = 0
        
        for opt_id, opt_data in OPTIMIZATION_RESULTS.items():
            results_count += 1
            completion_time = opt_data.get("completion_time", datetime.now())
            time_ago = datetime.now() - completion_time
            
            message += (
                f"• ID: <code>{opt_id}</code>\n"
                f"  Stratégie: <b>{opt_data.get('strategy', 'unknown')}</b>\n"
                f"  Terminée il y a: <b>{_format_timedelta(time_ago)}</b>\n"
                f"  ROI: <b>{opt_data.get('results', {}).get('metrics', {}).get('roi', 0):.2f}%</b>\n\n"
            )
            
            # Limiter la longueur du message
            if results_count >= 5:
                message += f"... et {len(OPTIMIZATION_RESULTS) - 5} autres optimisations."
                break
        
        if results_count == 0:
            message += "Aucun résultat d'optimisation disponible."
        
        await query.edit_message_text(
            message,
            parse_mode="HTML"
        )
    
    elif data.startswith("opt_chart_"):
        # Afficher le graphique de performance
        optimization_id = data.replace("opt_chart_", "")
        
        # Vérifier si l'optimisation existe
        if optimization_id not in OPTIMIZATION_RESULTS:
            await query.edit_message_text(
                f"❌ Aucune optimisation trouvée avec l'ID <code>{optimization_id}</code>.",
                parse_mode="HTML"
            )
            return
        
        # Générer et envoyer le graphique (simulé ici)
        await query.edit_message_text(
            "🔄 Génération du graphique de performance...",
            parse_mode="HTML"
        )
        
        # Dans une implémentation réelle, générer le graphique avec matplotlib 
        # et l'envoyer comme photo
        try:
            # Simuler un délai pour la génération du graphique
            if context.application:
                chart_path = _generate_performance_chart(optimization_id)
                
                # Restaurer le message original avec un lien vers le graphique
                opt_data = OPTIMIZATION_RESULTS.get(optimization_id, {})
                
                # Envoyer le graphique
                if update.effective_message:
                    with open(chart_path, "rb") as chart_file:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id if update.effective_chat else update.effective_user.id,
                            photo=chart_file,
                            caption=f"📊 <b>Graphique de performance</b>\nOptimisation: <code>{optimization_id}</code>",
                            parse_mode="HTML"
                        )
        except Exception as e:
            logger.error(f"Erreur lors de la génération du graphique: {str(e)}")
            await query.edit_message_text(
                f"❌ Erreur lors de la génération du graphique: {str(e)}",
                parse_mode="HTML"
            )
    
    elif data.startswith("opt_report_"):
        # Afficher le rapport détaillé
        optimization_id = data.replace("opt_report_", "")
        
        # Vérifier si l'optimisation existe
        if optimization_id not in OPTIMIZATION_RESULTS:
            await query.edit_message_text(
                f"❌ Aucune optimisation trouvée avec l'ID <code>{optimization_id}</code>.",
                parse_mode="HTML"
            )
            return
        
        # Récupérer les résultats détaillés
        opt_data = OPTIMIZATION_RESULTS.get(optimization_id, {})
        results = opt_data.get("results", {})
        detailed_metrics = results.get("detailed_metrics", {})
        
        # Formater le rapport détaillé
            message = (
            f"📋 <b>Rapport détaillé d'optimisation</b>\n\n"
            f"ID: <code>{optimization_id}</code>\n"
            f"Stratégie: <b>{opt_data.get('strategy', 'unknown')}</b>\n"
            f"Mode: <b>{opt_data.get('mode', 'unknown').title()}</b>\n\n"
            f"<b>Métriques détaillées:</b>\n"
        )
        
        # Ajouter les métriques détaillées
        for metric_name, metric_value in detailed_metrics.items():
            if isinstance(metric_value, (int, float)):
                message += f"• <b>{metric_name}</b>: {metric_value:.4f}\n"
        else:
                message += f"• <b>{metric_name}</b>: {metric_value}\n"
        
        # Ajouter les informations sur l'évolution de l'optimisation
        iterations = results.get("iterations", [])
        if iterations:
            message += f"\n<b>Évolution de l'optimisation:</b>\n"
            
            # Prendre 5 points de l'évolution (début, 25%, 50%, 75%, fin)
            total_iterations = len(iterations)
            points = [0, total_iterations // 4, total_iterations // 2, 3 * total_iterations // 4, total_iterations - 1]
            
            for i, point in enumerate(points):
                if point < total_iterations:
                    iteration_data = iterations[point]
                    message += (
                        f"• <b>Itération {iteration_data.get('iteration', point)}</b>:\n"
                        f"  ROI: {iteration_data.get('roi', 0):.2f}%\n"
                        f"  Win rate: {iteration_data.get('win_rate', 0):.2f}%\n"
                    )
        
        # Ajouter un bouton pour revenir aux résultats
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Retour aux résultats", callback_data=f"opt_view_{optimization_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    
    elif data.startswith("opt_apply_"):
        # Appliquer les paramètres optimisés
        optimization_id = data.replace("opt_apply_", "")
        
        # Vérifier si l'optimisation existe
        if optimization_id not in OPTIMIZATION_RESULTS:
            await query.edit_message_text(
                f"❌ Aucune optimisation trouvée avec l'ID <code>{optimization_id}</code>.",
                parse_mode="HTML"
            )
            return
        
        # Récupérer les paramètres optimisés
        opt_data = OPTIMIZATION_RESULTS.get(optimization_id, {})
        best_params = opt_data.get("results", {}).get("best_params", {})
        strategy = opt_data.get("strategy", "unknown")
        
        # Appliquer les paramètres (simulé ici)
        success = _apply_optimized_parameters(strategy, best_params)
        
        if success:
            message = (
                f"✅ <b>Paramètres appliqués avec succès</b>\n\n"
                f"Stratégie: <b>{strategy}</b>\n"
                f"ID optimisation: <code>{optimization_id}</code>\n\n"
                f"Les paramètres suivants ont été appliqués:\n"
            )
            
            # Formatter les paramètres
            for param_name, param_value in best_params.items():
                message += f"• <b>{param_name}</b>: {param_value}\n"
                
            # Ajouter des boutons d'action
            keyboard = [
                [
                    InlineKeyboardButton("▶️ Démarrer stratégie", callback_data=f"start_strategy_{strategy}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                f"❌ <b>Erreur lors de l'application des paramètres</b>\n\n"
                f"Impossible d'appliquer les paramètres à la stratégie <b>{strategy}</b>.",
                parse_mode="HTML"
            )
    
    elif data.startswith("opt_view_"):
        # Revenir à la vue des résultats
        optimization_id = data.replace("opt_view_", "")
        
        # Simuler une commande de visualisation des résultats
        context.args = [optimization_id]
        await view_optimization_results_command(update, context)

# Fonctions utilitaires internes

async def _list_available_optimizations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Liste les optimisations disponibles."""
    # Construire le message avec les optimisations disponibles
    message = "<b>📋 Optimisations disponibles</b>\n\n"
    
    # Optimisations terminées
    if OPTIMIZATION_RESULTS:
        message += "<b>Optimisations terminées:</b>\n"
        for opt_id, opt_data in OPTIMIZATION_RESULTS.items():
            completion_time = opt_data.get("completion_time", datetime.now())
            time_ago = datetime.now() - completion_time
            
            message += (
                f"• <code>{opt_id}</code> - {opt_data.get('strategy')}\n"
                f"  Terminée il y a {_format_timedelta(time_ago)}\n"
                f"  ROI: {opt_data.get('results', {}).get('metrics', {}).get('roi', 0):.2f}%\n\n"
            )
    else:
        message += "Aucune optimisation terminée.\n\n"
    
    # Optimisations en cours
    running_optimizations = {opt_id: opt_data for opt_id, opt_data in RUNNING_OPTIMIZATIONS.items() 
                            if opt_data.get("status") == "running"}
    
    if running_optimizations:
        message += "<b>Optimisations en cours:</b>\n"
        for opt_id, opt_data in running_optimizations.items():
            start_time = opt_data.get("start_time", datetime.now())
            elapsed = datetime.now() - start_time
            
            message += (
                f"• <code>{opt_id}</code> - {opt_data.get('strategy')}\n"
                f"  En cours depuis {_format_timedelta(elapsed)}\n\n"
            )
    
    # Ajouter des instructions
    message += (
        "\nPour voir les résultats d'une optimisation, utilisez:\n"
        "<code>/optimization_results [optimization_id]</code>"
    )
    
    await update.effective_message.reply_text(
        message,
        parse_mode="HTML"
    )

def _format_timedelta(delta: timedelta) -> str:
    """Formate un timedelta en chaîne lisible."""
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h {int((seconds % 3600) / 60)}m"
    else:
        return f"{int(seconds / 86400)}j {int((seconds % 86400) / 3600)}h"

def _generate_performance_chart(optimization_id: str) -> str:
    """
    Génère un graphique de performance pour une optimisation.
    
    Args:
        optimization_id: ID de l'optimisation
    
    Returns:
        Chemin vers le fichier du graphique généré
    """
    # Simuler la génération d'un graphique
    # Dans une implémentation réelle, utiliser matplotlib
    
    # Créer un chemin temporaire pour le graphique
    import tempfile
    import os
    
    # Pour ce test, retourner simplement un chemin factice
    # Normalement, on génèrerait un vrai graphique
    chart_path = os.path.join(tempfile.gettempdir(), f"optimization_{optimization_id}_chart.png")
    
    # Créer un fichier vide (pour le test)
    with open(chart_path, "w") as f:
        f.write("Test chart")
    
    return chart_path

def _apply_optimized_parameters(strategy: str, params: Dict[str, Any]) -> bool:
    """
    Applique les paramètres optimisés à une stratégie.
    
    Args:
        strategy: Nom de la stratégie
        params: Paramètres optimisés
    
    Returns:
        True si les paramètres ont été appliqués avec succès, False sinon
    """
    # Simuler l'application des paramètres
    # Dans une implémentation réelle, mettre à jour la configuration de la stratégie
    logger.info(f"Application des paramètres optimisés pour la stratégie {strategy}: {params}")
    
    # Toujours retourner True pour cette simulation
    return True

async def _run_optimization_task(optimization_id: str, strategy: str, history_days: int, 
                                mode: str, detailed: bool) -> None:
    """
    Exécute une tâche d'optimisation en arrière-plan.
    
    Args:
        optimization_id: ID de l'optimisation
        strategy: Nom de la stratégie
        history_days: Nombre de jours d'historique
        mode: Mode d'optimisation
        detailed: Niveau de détail
    """
    # Dans un cas réel, cette fonction serait exécutée dans un thread/processus séparé
    # ou utiliserait asyncio.create_task pour ne pas bloquer le bot
    
    try:
        # Simuler le processus d'optimisation
        logger.info(f"Démarrage de l'optimisation {optimization_id} pour {strategy}")
        
        # Simuler une optimisation qui dure quelques secondes
        await asyncio.sleep(5)
        
        # Stocker les résultats (simulés ici)
        OPTIMIZATION_RESULTS[optimization_id] = {
            "strategy": strategy,
            "history_days": history_days,
            "mode": mode,
            "start_time": RUNNING_OPTIMIZATIONS[optimization_id]["start_time"],
            "completion_time": datetime.now(),
            "duration": _format_timedelta(datetime.now() - RUNNING_OPTIMIZATIONS[optimization_id]["start_time"]),
            "results": {
                "best_params": {
                    "entry_threshold": 0.85,
                    "exit_threshold": 0.65,
                    "stop_loss": 0.05,
                    "take_profit": 0.15,
                    "max_slippage": 0.02
                },
                "metrics": {
                    "roi": 32.5,
                    "avg_profit": 8.7,
                    "win_rate": 72.3,
                    "total_trades": 42,
                    "sharpe_ratio": 1.8
                },
                "detailed_metrics": {
                    "max_drawdown": 12.4,
                    "volatility": 14.2,
                    "avg_hold_time": "2.3h",
                    "profit_factor": 2.1,
                    "recovery_factor": 3.2,
                    "calmar_ratio": 1.5,
                    "sortino_ratio": 2.3
                },
                "iterations": [
                    {"iteration": 0, "roi": 5.2, "win_rate": 45.0},
                    {"iteration": 10, "roi": 15.8, "win_rate": 55.2},
                    {"iteration": 25, "roi": 22.3, "win_rate": 62.1},
                    {"iteration": 40, "roi": 29.7, "win_rate": 68.4},
                    {"iteration": 49, "roi": 32.5, "win_rate": 72.3}
                ]
            }
        }
        
        # Mettre à jour le statut de l'optimisation
        RUNNING_OPTIMIZATIONS[optimization_id]["status"] = "completed"
        
        # Envoyer une notification à l'utilisateur
        chat_id = RUNNING_OPTIMIZATIONS[optimization_id].get("chat_id")
        if chat_id:
            from telegram.ext import ApplicationBuilder
            application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN", "")).build()
            
            await application.bot.send_message(
                chat_id=chat_id,
                text=f"✅ <b>Optimisation terminée</b>\n\n"
                     f"ID: <code>{optimization_id}</code>\n"
                     f"Stratégie: <b>{strategy}</b>\n"
                     f"ROI optimal: <b>{OPTIMIZATION_RESULTS[optimization_id]['results']['metrics']['roi']:.2f}%</b>\n\n"
                     f"Pour voir les résultats: <code>/optimization_results {optimization_id}</code>",
                parse_mode="HTML"
            )
    
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation {optimization_id}: {str(e)}")
        
        # Mettre à jour le statut en cas d'erreur
        if optimization_id in RUNNING_OPTIMIZATIONS:
            RUNNING_OPTIMIZATIONS[optimization_id]["status"] = "failed"
            RUNNING_OPTIMIZATIONS[optimization_id]["error"] = str(e)
            
            # Notification d'erreur
            chat_id = RUNNING_OPTIMIZATIONS[optimization_id].get("chat_id")
            if chat_id:
                from telegram.ext import ApplicationBuilder
                application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN", "")).build()
                
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ <b>Erreur d'optimisation</b>\n\n"
                         f"ID: <code>{optimization_id}</code>\n"
                         f"Stratégie: <b>{strategy}</b>\n"
                         f"Erreur: {str(e)}",
                    parse_mode="HTML"
                )

def register_optimization_command_handlers(application: Any) -> None:
    """
    Enregistre les gestionnaires de commandes pour les optimisations.
    
    Args:
        application: Application Telegram
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Modules Telegram non disponibles. Commandes d'optimisation non enregistrées.")
        return
    
    application.add_handler(CommandHandler("optimize", run_optimization_command))
    application.add_handler(CommandHandler("optimization_results", view_optimization_results_command))
    application.add_handler(CallbackQueryHandler(optimization_callback_handler, pattern=r"^opt_"))
    
    logger.info("Gestionnaires de commandes d'optimisation enregistrés avec succès.") 