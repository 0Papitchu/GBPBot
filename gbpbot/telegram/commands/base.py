"""
Module de base pour les commandes Telegram
==========================================

Ce module contient les fonctions de base pour la gestion des commandes
Telegram, y compris l'enregistrement des gestionnaires de commandes.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Union
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger("gbpbot.telegram.commands.base")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère la commande /start
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte de la commande
    """
    user = update.effective_user
    bot = context.bot_data.get("bot_instance")
    
    # Vérifier si l'utilisateur est autorisé
    if not bot or not bot._is_user_authorized(user.id):
        await update.message.reply_text(
            "⛔ Vous n'êtes pas autorisé à utiliser ce bot.\n\n"
            "Contactez l'administrateur pour obtenir l'accès."
        )
        return
    
    # Ajouter le chat à la liste des notifications
    bot.add_chat_id(update.effective_chat.id)
    
    # Envoyer le message de bienvenue
    await update.message.reply_text(
        f"👋 Bienvenue <b>{user.first_name}</b> dans le GBPBot Telegram!\n\n"
        f"Ce bot vous permet de contrôler et surveiller votre GBPBot à distance.\n\n"
        f"Utilisez /help pour voir les commandes disponibles.",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère la commande /help
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte de la commande
    """
    user = update.effective_user
    bot = context.bot_data.get("bot_instance")
    
    # Vérifier si l'utilisateur est autorisé
    if not bot or not bot._is_user_authorized(user.id):
        await update.message.reply_text(
            "⛔ Vous n'êtes pas autorisé à utiliser ce bot."
        )
        return
    
    # Envoyer le message d'aide
    await update.message.reply_text(
        "📚 <b>Commandes Disponibles</b> 📚\n\n"
        "<b>Commandes de Base</b>\n"
        "/start - Démarrer le bot\n"
        "/help - Afficher ce message d'aide\n"
        "/status - Afficher le statut du GBPBot\n\n"
        
        "<b>Commandes de Trading</b>\n"
        "/startarbi - Démarrer l'arbitrage\n"
        "/stoparbi - Arrêter l'arbitrage\n"
        "/startsnipe - Démarrer le sniping\n"
        "/stopsnipe - Arrêter le sniping\n"
        "/startauto - Démarrer le mode automatique\n"
        "/stopauto - Arrêter le mode automatique\n\n"
        
        "<b>Commandes d'Analyse</b>\n"
        "/market - Analyser le marché\n"
        "/token <symbol> - Analyser un token spécifique\n"
        "/predict <symbol> - Prédire le mouvement de prix\n\n"
        
        "<b>Commandes de Backtesting</b>\n"
        "/backtest - Lancer un backtest\n"
        "/backtests - Voir la liste des backtests\n\n"
        
        "<b>Commandes de Statistiques</b>\n"
        "/profits - Afficher les profits\n"
        "/stats - Afficher les statistiques de trading\n"
        "/balance - Afficher les soldes des wallets\n\n"
        
        "Pour plus d'informations, consultez la documentation complète du GBPBot.",
        parse_mode="HTML"
    )

def register_command_handlers(bot_instance: Any) -> None:
    """
    Enregistre tous les gestionnaires de commandes pour le bot Telegram.
    
    Args:
        bot_instance: L'instance du bot Telegram
    """
    try:
        app = bot_instance.application
        if not app:
            logger.error("Application Telegram non initialisée.")
            return
        
        # Stocker l'instance du bot dans les données du bot pour y accéder dans les handlers
        app.bot_data["bot_instance"] = bot_instance
        
        # Enregistrer les commandes de base
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        
        # Importer et enregistrer les autres commandes
        from gbpbot.telegram.commands.status import status_command, stats_command, balance_command, profits_command
        from gbpbot.telegram.commands.strategy import start_strategy_command, stop_strategy_command
        from gbpbot.telegram.commands.analyze import analyze_market_command, analyze_token_command, predict_command
        from gbpbot.telegram.commands.backtesting import run_backtest_command, list_backtests_command
        
        # Commandes de statut
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("balance", balance_command))
        app.add_handler(CommandHandler("profits", profits_command))
        
        # Commandes de stratégie
        app.add_handler(CommandHandler("startarbi", lambda u, c: start_strategy_command(u, c, "arbitrage")))
        app.add_handler(CommandHandler("stoparbi", lambda u, c: stop_strategy_command(u, c, "arbitrage")))
        app.add_handler(CommandHandler("startsnipe", lambda u, c: start_strategy_command(u, c, "sniping")))
        app.add_handler(CommandHandler("stopsnipe", lambda u, c: stop_strategy_command(u, c, "sniping")))
        app.add_handler(CommandHandler("startauto", lambda u, c: start_strategy_command(u, c, "auto_mode")))
        app.add_handler(CommandHandler("stopauto", lambda u, c: stop_strategy_command(u, c, "auto_mode")))
        
        # Commandes d'analyse
        app.add_handler(CommandHandler("market", analyze_market_command))
        app.add_handler(CommandHandler("token", analyze_token_command))
        app.add_handler(CommandHandler("predict", predict_command))
        
        # Commandes de backtesting
        app.add_handler(CommandHandler("backtest", run_backtest_command))
        app.add_handler(CommandHandler("backtests", list_backtests_command))
        
        # Gestionnaire pour les boutons inline (callbacks)
        app.add_handler(CallbackQueryHandler(button_callback))
        
        logger.info("Gestionnaires de commandes Telegram enregistrés avec succès.")
    except Exception as e:
        logger.exception(f"Erreur lors de l'enregistrement des gestionnaires de commandes: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère les callbacks des boutons inline
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
    """
    query = update.callback_query
    bot = context.bot_data.get("bot_instance")
    
    # Assurez-vous que le bot est disponible
    if not bot:
        await query.answer("Erreur: Bot non disponible.")
        return
    
    # Vérifier si l'utilisateur est autorisé
    if not bot._is_user_authorized(query.from_user.id):
        await query.answer("Vous n'êtes pas autorisé à utiliser ce bot.")
        return
    
    try:
        # Essayer d'analyser les données du callback
        data = query.data
        
        # Notify Telegram that we've handled the callback
        await query.answer()
        
        # Traiter les différents types de callbacks
        if data.startswith("start_"):
            # Démarrer une stratégie
            strategy = data.split("_")[1]
            await start_strategy_callback(update, context, strategy)
        elif data.startswith("stop_"):
            # Arrêter une stratégie
            strategy = data.split("_")[1]
            await stop_strategy_callback(update, context, strategy)
        elif data.startswith("analyze_"):
            # Analyser un token ou le marché
            target = data.split("_")[1]
            if target == "market":
                await analyze_market_callback(update, context)
            else:
                await analyze_token_callback(update, context, target)
        elif data.startswith("backtest_"):
            # Gérer les backtests
            action = data.split("_")[1]
            if action == "run":
                await run_backtest_callback(update, context)
            elif action == "list":
                await list_backtests_callback(update, context)
        else:
            await query.edit_message_text(
                f"Action non reconnue: {data}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.exception(f"Erreur lors du traitement du callback: {str(e)}")
        await query.edit_message_text(
            f"❌ Erreur lors du traitement de la commande: {str(e)}",
            parse_mode="HTML"
        )

async def start_strategy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, strategy: str) -> None:
    """
    Callback pour démarrer une stratégie
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
        strategy: Le nom de la stratégie à démarrer
    """
    query = update.callback_query
    bot = context.bot_data.get("bot_instance")
    
    # Importer localement pour éviter les imports circulaires
    from gbpbot.telegram.commands.strategy import start_strategy_command
    
    # Créer un faux update avec le chat ID
    fake_update = Update(0, None)
    fake_update._effective_chat = update.effective_chat
    fake_update._effective_user = update.effective_user
    
    # Appeler la commande de démarrage de stratégie
    await start_strategy_command(fake_update, context, strategy)
    
    # Mettre à jour le message original
    await query.edit_message_text(
        f"✅ Stratégie {strategy} démarrée avec succès!",
        parse_mode="HTML"
    )

async def stop_strategy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, strategy: str) -> None:
    """
    Callback pour arrêter une stratégie
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
        strategy: Le nom de la stratégie à arrêter
    """
    query = update.callback_query
    bot = context.bot_data.get("bot_instance")
    
    # Importer localement pour éviter les imports circulaires
    from gbpbot.telegram.commands.strategy import stop_strategy_command
    
    # Créer un faux update avec le chat ID
    fake_update = Update(0, None)
    fake_update._effective_chat = update.effective_chat
    fake_update._effective_user = update.effective_user
    
    # Appeler la commande d'arrêt de stratégie
    await stop_strategy_command(fake_update, context, strategy)
    
    # Mettre à jour le message original
    await query.edit_message_text(
        f"✅ Stratégie {strategy} arrêtée avec succès!",
        parse_mode="HTML"
    )

async def analyze_market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback pour analyser le marché
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
    """
    query = update.callback_query
    
    # Importer localement pour éviter les imports circulaires
    from gbpbot.telegram.commands.analyze import analyze_market_command
    
    # Créer un faux update avec le chat ID
    fake_update = Update(0, None)
    fake_update._effective_chat = update.effective_chat
    fake_update._effective_user = update.effective_user
    
    # Informer l'utilisateur que l'analyse est en cours
    await query.edit_message_text(
        "🔄 Analyse du marché en cours...",
        parse_mode="HTML"
    )
    
    # Appeler la commande d'analyse
    await analyze_market_command(fake_update, context)

async def analyze_token_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> None:
    """
    Callback pour analyser un token
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
        token: Le symbole du token à analyser
    """
    query = update.callback_query
    
    # Importer localement pour éviter les imports circulaires
    from gbpbot.telegram.commands.analyze import analyze_token_command
    
    # Créer un faux update avec le chat ID
    fake_update = Update(0, None)
    fake_update._effective_chat = update.effective_chat
    fake_update._effective_user = update.effective_user
    
    # Ajouter le token comme argument
    context.args = [token]
    
    # Informer l'utilisateur que l'analyse est en cours
    await query.edit_message_text(
        f"🔄 Analyse du token {token} en cours...",
        parse_mode="HTML"
    )
    
    # Appeler la commande d'analyse
    await analyze_token_command(fake_update, context)

async def run_backtest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback pour lancer un backtest
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
    """
    query = update.callback_query
    
    # Importer localement pour éviter les imports circulaires
    from gbpbot.telegram.commands.backtesting import run_backtest_command
    
    # Créer un faux update avec le chat ID
    fake_update = Update(0, None)
    fake_update._effective_chat = update.effective_chat
    fake_update._effective_user = update.effective_user
    
    # Informer l'utilisateur que le backtest est en cours
    await query.edit_message_text(
        "🔄 Lancement du backtest en cours...",
        parse_mode="HTML"
    )
    
    # Appeler la commande de backtest
    await run_backtest_command(fake_update, context)

async def list_backtests_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback pour lister les backtests
    
    Args:
        update: L'objet Update de Telegram
        context: Le contexte du callback
    """
    query = update.callback_query
    
    # Importer localement pour éviter les imports circulaires
    from gbpbot.telegram.commands.backtesting import list_backtests_command
    
    # Créer un faux update avec le chat ID
    fake_update = Update(0, None)
    fake_update._effective_chat = update.effective_chat
    fake_update._effective_user = update.effective_user
    
    # Appeler la commande de liste des backtests
    await list_backtests_command(fake_update, context) 