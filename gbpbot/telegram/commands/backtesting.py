"""
Module de commandes de backtesting pour le bot Telegram
====================================================

Ce module implémente les commandes pour exécuter et gérer les backtests
via l'interface Telegram du GBPBot.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import traceback
from datetime import datetime, timedelta
import json

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext, CommandHandler, CallbackQueryHandler

# Logger
logger = logging.getLogger("gbpbot.telegram.commands.backtesting")

# Importation conditionnelle des modules de backtesting
try:
    from gbpbot.backtesting.engine import BacktestingEngine
    from gbpbot.backtesting.data_loader import DataLoader
    from gbpbot.backtesting.performance_analyzer import PerformanceAnalyzer
    BACKTESTING_AVAILABLE = True
except ImportError:
    BACKTESTING_AVAILABLE = False
    logger.warning("Module de backtesting non disponible")

# Commande /run_backtest - Lance un backtest
async def run_backtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Lance un backtest avec les paramètres spécifiés.
    Usage: /run_backtest <stratégie> [options]
    Options:
    --start=YYYY-MM-DD  Date de début
    --end=YYYY-MM-DD    Date de fin (défaut: aujourd'hui)
    --chain=solana      Blockchain à utiliser
    --capital=1000      Capital initial en USD
    --detailed          Analyse détaillée des résultats
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Vérifier si le module de backtesting est disponible
    if not BACKTESTING_AVAILABLE:
        await update.message.reply_text(
            "❌ <b>Module de backtesting non disponible</b>\n\n"
            "Cette fonctionnalité nécessite l'installation du module de backtesting.",
            parse_mode="HTML"
        )
        return
    
    # Si pas de paramètres, afficher l'aide et les stratégies disponibles
    if not context.args or len(context.args) < 1:
        keyboard = [
            [InlineKeyboardButton("🎯 Sniping Token", callback_data="backtest_sniper")],
            [InlineKeyboardButton("⚖️ Arbitrage", callback_data="backtest_arbitrage")],
            [InlineKeyboardButton("💰 Prise de Profit", callback_data="backtest_profit_taker")],
            [InlineKeyboardButton("🤖 Mode Automatique", callback_data="backtest_auto")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔄 <b>Backtesting de Stratégie</b>\n\n"
            "Choisissez la stratégie à tester ou utilisez la commande avec des paramètres:\n\n"
            "<code>/run_backtest &lt;stratégie&gt; [options]</code>\n\n"
            "Options disponibles:\n"
            "• <code>--start=YYYY-MM-DD</code> Date de début\n"
            "• <code>--end=YYYY-MM-DD</code> Date de fin\n"
            "• <code>--chain=solana</code> Blockchain\n"
            "• <code>--capital=1000</code> Capital initial\n"
            "• <code>--detailed</code> Analyse détaillée\n\n"
            "Exemple:\n"
            "<code>/run_backtest sniper --start=2024-01-01 --chain=solana --capital=1000</code>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return
    
    # Extraire la stratégie et les options
    strategy = context.args[0].lower()
    options = {
        "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "chain": "solana",
        "capital": 1000.0,
        "detailed": False
    }
    
    # Parser les options
    if len(context.args) > 1:
        for arg in context.args[1:]:
            if arg.startswith("--start="):
                options["start_date"] = arg.split("=")[1]
            elif arg.startswith("--end="):
                options["end_date"] = arg.split("=")[1]
            elif arg.startswith("--chain="):
                options["chain"] = arg.split("=")[1].lower()
            elif arg.startswith("--capital="):
                try:
                    options["capital"] = float(arg.split("=")[1])
                except ValueError:
                    await update.message.reply_text(
                        "❌ <b>Erreur de paramètre</b>\n\n"
                        "Le capital doit être un nombre valide.",
                        parse_mode="HTML"
                    )
                    return
            elif arg == "--detailed":
                options["detailed"] = True
    
    # Message de processing
    processing_message = await update.message.reply_text(
        f"🔄 <b>Lancement du backtest...</b>\n\n"
        f"Stratégie: {strategy}\n"
        f"Période: {options['start_date']} → {options['end_date']}\n"
        f"Blockchain: {options['chain'].title()}\n"
        f"Capital: {options['capital']} USD\n\n"
        "Veuillez patienter pendant l'exécution du backtest...",
        parse_mode="HTML"
    )
    
    try:
        # Créer le moteur de backtesting
        engine = BacktestingEngine(context.bot_data.get('bot_state', {}))
        
        # Charger les données historiques
        data_loader = DataLoader()
        historical_data = await data_loader.load_data(
            chain=options["chain"],
            start_date=options["start_date"],
            end_date=options["end_date"]
        )
        
        # Exécuter le backtest
        result = await engine.run_backtest(
            strategy=strategy,
            data=historical_data,
            initial_capital=options["capital"],
            detailed=options["detailed"]
        )
        
        # Analyser les performances
        analyzer = PerformanceAnalyzer()
        performance = await analyzer.analyze_results(result)
        
        # Formater la réponse
        if result and performance:
            # Calculer les métriques principales
            total_return = performance["total_return"]
            total_trades = performance["total_trades"]
            win_rate = performance["win_rate"]
            profit_factor = performance.get("profit_factor", 0)
            max_drawdown = performance.get("max_drawdown", 0)
            sharpe_ratio = performance.get("sharpe_ratio", 0)
            
            # Emoji pour le résultat global
            result_emoji = "🟢" if total_return > 0 else "🔴" if total_return < 0 else "⚪"
            
            # Construire le message
            message = f"{result_emoji} <b>Résultats du Backtest</b>\n\n"
            
            # Informations de base
            message += f"<b>Stratégie:</b> {strategy.title()}\n"
            message += f"<b>Période:</b> {options['start_date']} → {options['end_date']}\n"
            message += f"<b>Blockchain:</b> {options['chain'].title()}\n"
            message += f"<b>Capital Initial:</b> {options['capital']:,.2f} USD\n\n"
            
            # Performances
            message += "<b>Performances:</b>\n"
            message += f"• Capital Final: {options['capital'] * (1 + total_return/100):,.2f} USD\n"
            message += f"• Rendement Total: {total_return:+.2f}%\n"
            message += f"• Nombre de Trades: {total_trades}\n"
            message += f"• Win Rate: {win_rate:.1f}%\n"
            message += f"• Profit Factor: {profit_factor:.2f}\n"
            message += f"• Drawdown Max: {max_drawdown:.2f}%\n"
            message += f"• Ratio de Sharpe: {sharpe_ratio:.2f}\n"
            
            # Statistiques détaillées si demandées
            if options["detailed"] and "detailed_stats" in performance:
                stats = performance["detailed_stats"]
                message += "\n<b>Statistiques Détaillées:</b>\n"
                
                if "monthly_returns" in stats:
                    message += "\n<b>Rendements Mensuels:</b>\n"
                    for month, ret in stats["monthly_returns"].items():
                        message += f"• {month}: {ret:+.2f}%\n"
                
                if "best_trades" in stats:
                    message += "\n<b>Meilleurs Trades:</b>\n"
                    for trade in stats["best_trades"][:3]:  # Top 3
                        message += (
                            f"• {trade['symbol']}: {trade['return']:+.2f}% "
                            f"({trade['date']})\n"
                        )
                
                if "worst_trades" in stats:
                    message += "\n<b>Pires Trades:</b>\n"
                    for trade in stats["worst_trades"][:3]:  # Top 3
                        message += (
                            f"• {trade['symbol']}: {trade['return']:+.2f}% "
                            f"({trade['date']})\n"
                        )
            
            # Boutons pour actions supplémentaires
            keyboard = [
                [InlineKeyboardButton("📊 Graphique de Performance", callback_data=f"backtest_chart_{strategy}")],
                [InlineKeyboardButton("📈 Analyse Détaillée", callback_data=f"backtest_analysis_{strategy}")],
                [InlineKeyboardButton("💾 Exporter Résultats", callback_data=f"backtest_export_{strategy}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Envoyer la réponse et supprimer le message de processing
            await processing_message.delete()
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await processing_message.delete()
            await update.message.reply_text(
                "❌ <b>Erreur lors du backtest</b>\n\n"
                "Aucun résultat n'a été obtenu. Vérifiez les paramètres et réessayez.",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors du backtest: {str(e)}")
        traceback.print_exc()
        await processing_message.delete()
        await update.message.reply_text(
            f"❌ <b>Erreur lors du backtest</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Commande /list_backtests - Liste les backtests récents
async def list_backtests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Liste les backtests récents et leurs résultats.
    Usage: /list_backtests [options]
    Options: --limit=10, --strategy=sniper
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Vérifier si le module de backtesting est disponible
    if not BACKTESTING_AVAILABLE:
        await update.message.reply_text(
            "❌ <b>Module de backtesting non disponible</b>\n\n"
            "Cette fonctionnalité nécessite l'installation du module de backtesting.",
            parse_mode="HTML"
        )
        return
    
    # Extraire les options
    limit = 10
    strategy = None
    
    if context.args:
        for arg in context.args:
            if arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=")[1])
                    limit = max(1, min(limit, 50))  # Limiter entre 1 et 50
                except ValueError:
                    pass
            elif arg.startswith("--strategy="):
                strategy = arg.split("=")[1].lower()
    
    try:
        # Créer le moteur de backtesting
        engine = BacktestingEngine(context.bot_data.get('bot_state', {}))
        
        # Récupérer l'historique des backtests
        backtests = await engine.get_backtest_history(limit=limit, strategy=strategy)
        
        if backtests and len(backtests) > 0:
            # Construire le message
            message = "📋 <b>Historique des Backtests</b>\n\n"
            
            # Filtrer par stratégie si spécifié
            if strategy:
                message += f"Stratégie: {strategy.title()}\n\n"
            
            # Lister les backtests
            for i, test in enumerate(backtests, 1):
                # Emoji pour le résultat
                result_emoji = "🟢" if test["return"] > 0 else "🔴" if test["return"] < 0 else "⚪"
                
                message += (
                    f"{i}. {result_emoji} <b>{test['strategy'].title()}</b>\n"
                    f"   📅 {test['date']}\n"
                    f"   💰 Return: {test['return']:+.2f}%\n"
                    f"   📊 Trades: {test['trades']} (Win Rate: {test['win_rate']:.1f}%)\n"
                )
                
                # Ajouter un séparateur entre les backtests sauf pour le dernier
                if i < len(backtests):
                    message += "\n"
            
            # Boutons pour filtrer par stratégie
            keyboard = []
            strategies = ["all", "sniper", "arbitrage", "profit_taker", "auto"]
            strategy_buttons = []
            
            for s in strategies:
                if s != strategy:  # Ne pas afficher la stratégie actuelle
                    emoji = "🔄" if s == "all" else "🎯" if s == "sniper" else "⚖️" if s == "arbitrage" else "💰" if s == "profit_taker" else "🤖"
                    strategy_buttons.append(InlineKeyboardButton(f"{emoji} {s.title()}", callback_data=f"list_backtests_{s}_{limit}"))
            
            # Diviser les boutons en rangées de 3 maximum
            for i in range(0, len(strategy_buttons), 3):
                keyboard.append(strategy_buttons[i:i+3])
            
            # Ajouter un bouton pour lancer un nouveau backtest
            keyboard.append([InlineKeyboardButton("🔄 Nouveau Backtest", callback_data="run_backtest")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Envoyer la réponse
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                "ℹ️ <b>Aucun backtest trouvé</b>\n\n"
                "Aucun backtest n'a été exécuté avec les critères spécifiés.",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique des backtests: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            "❌ <b>Erreur lors de la récupération de l'historique</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Gestionnaire pour les callbacks liés aux backtests
async def backtest_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère les callbacks des boutons liés aux backtests.
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
    
    if callback_data.startswith("backtest_chart_"):
        # Format: backtest_chart_<strategy>
        strategy = callback_data.replace("backtest_chart_", "")
        
        # Message de processing
        await query.edit_message_text(
            f"📊 <b>Génération du graphique de performance...</b>\n\n"
            "Veuillez patienter pendant que je prépare le graphique.",
            parse_mode="HTML"
        )
        
        try:
            # Cette fonctionnalité nécessiterait d'envoyer une image de graphique
            # Comme Telegram ne peut pas afficher d'images directement dans les messages édités,
            # On pourrait soit envoyer un nouveau message avec l'image, soit proposer un lien de téléchargement
            
            # Pour l'instant, simulons cette fonctionnalité avec un message d'information
            message = (
                f"📊 <b>Graphique de Performance - {strategy.title()}</b>\n\n"
                "Le graphique de performance serait affiché ici.\n\n"
                "Pour télécharger le graphique complet:\n"
                "• Utilisez la commande <code>/export_backtest_chart</code>\n"
                "• Ou cliquez sur le bouton ci-dessous"
            )
            
            # Boutons pour actions supplémentaires
            keyboard = [
                [InlineKeyboardButton("💾 Télécharger Graphique", callback_data=f"download_chart_{strategy}")],
                [InlineKeyboardButton("◀️ Retour aux Résultats", callback_data=f"backtest_results_{strategy}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Erreur lors de la génération du graphique: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                "❌ <b>Erreur lors de la génération du graphique</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    elif callback_data.startswith("backtest_analysis_"):
        # Format: backtest_analysis_<strategy>
        strategy = callback_data.replace("backtest_analysis_", "")
        
        # Message de processing
        await query.edit_message_text(
            f"🔍 <b>Génération de l'analyse détaillée...</b>\n\n"
            "Veuillez patienter pendant que je prépare l'analyse approfondie.",
            parse_mode="HTML"
        )
        
        try:
            # Créer le moteur de backtesting et l'analyseur de performance
            engine = BacktestingEngine(context.bot_data.get('bot_state', {}))
            analyzer = PerformanceAnalyzer()
            
            # Récupérer les résultats détaillés du dernier backtest pour cette stratégie
            results = await engine.get_last_backtest_results(strategy)
            if results:
                # Analyser les performances en détail
                analysis = await analyzer.analyze_results(results, detailed=True)
                
                if analysis:
                    # Formater l'analyse détaillée
                    message = f"📊 <b>Analyse Détaillée - {strategy.title()}</b>\n\n"
                    
                    # Ajouter les différentes sections d'analyse
                    # (code similaire à la commande de base, mais avec plus de détails)
                    
                    # Boutons pour actions supplémentaires
                    keyboard = [
                        [InlineKeyboardButton("📊 Voir Graphique", callback_data=f"backtest_chart_{strategy}")],
                        [InlineKeyboardButton("◀️ Retour aux Résultats", callback_data=f"backtest_results_{strategy}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await query.edit_message_text(
                        "❌ <b>Erreur lors de l'analyse détaillée</b>\n\n"
                        "Impossible d'analyser les résultats du backtest.",
                        parse_mode="HTML"
                    )
            else:
                await query.edit_message_text(
                    "❌ <b>Aucun résultat trouvé</b>\n\n"
                    "Aucun backtest récent n'a été trouvé pour cette stratégie.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse détaillée: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                "❌ <b>Erreur lors de l'analyse détaillée</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    elif callback_data.startswith("backtest_export_"):
        # Format: backtest_export_<strategy>
        strategy = callback_data.replace("backtest_export_", "")
        
        # Message de processing
        await query.edit_message_text(
            f"💾 <b>Préparation de l'export...</b>\n\n"
            "Veuillez patienter pendant que je prépare les fichiers d'export.",
            parse_mode="HTML"
        )
        
        try:
            # Créer le moteur de backtesting
            engine = BacktestingEngine(context.bot_data.get('bot_state', {}))
            
            # Récupérer les résultats du dernier backtest pour cette stratégie
            results = await engine.get_last_backtest_results(strategy)
            
            if results:
                # Préparer les différents formats d'export
                message = (
                    f"💾 <b>Export des Résultats - {strategy.title()}</b>\n\n"
                    "Choisissez le format d'export souhaité:\n\n"
                    "• CSV: Données brutes pour analyse dans Excel\n"
                    "• JSON: Format complet pour import/export\n"
                    "• PDF: Rapport détaillé avec graphiques\n"
                    "• HTML: Version web interactive"
                )
                
                # Boutons pour les différents formats
                keyboard = [
                    [
                        InlineKeyboardButton("📊 CSV", callback_data=f"export_csv_{strategy}"),
                        InlineKeyboardButton("🔧 JSON", callback_data=f"export_json_{strategy}"),
                        InlineKeyboardButton("📄 PDF", callback_data=f"export_pdf_{strategy}"),
                        InlineKeyboardButton("🌐 HTML", callback_data=f"export_html_{strategy}")
                    ],
                    [InlineKeyboardButton("◀️ Retour aux Résultats", callback_data=f"backtest_results_{strategy}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await query.edit_message_text(
                    "❌ <b>Aucun résultat à exporter</b>\n\n"
                    "Aucun backtest récent n'a été trouvé pour cette stratégie.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Erreur lors de la préparation de l'export: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                "❌ <b>Erreur lors de la préparation de l'export</b>\n\n"
                f"Détails: {str(e)}",
                parse_mode="HTML"
            )
    
    elif callback_data.startswith("list_backtests_"):
        # Format: list_backtests_<strategy>_<limit>
        parts = callback_data.split("_")
        if len(parts) >= 3:
            strategy = parts[2]
            limit = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 10
            
            # Rediriger vers la commande list_backtests avec les bons paramètres
            context.args = []
            if strategy != "all":
                context.args.append(f"--strategy={strategy}")
            context.args.append(f"--limit={limit}")
            
            await list_backtests_command(update, context)

# Fonction pour enregistrer les gestionnaires de commandes
def register_backtest_command_handlers(application):
    """
    Enregistre les gestionnaires de commandes liées au backtesting.
    """
    application.add_handler(CommandHandler("run_backtest", run_backtest_command))
    application.add_handler(CommandHandler("list_backtests", list_backtests_command))
    
    # Gestionnaire pour les callbacks des boutons
    application.add_handler(CallbackQueryHandler(
        backtest_button_callback,
        pattern="^(backtest_|list_backtests_|export_)"
    )) 