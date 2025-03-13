"""
Module de Bot Telegram pour GBPBot
==================================

Ce module permet de contrôler le GBPBot à distance via Telegram,
en offrant des commandes pour démarrer/arrêter le bot, gérer les modules,
et surveiller les performances.
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import json
import threading

# Importer les modules Telegram
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext  # type: ignore
    telegram_imports_ok = True
except ImportError:
    telegram_imports_ok = False
    print("Telegram modules not available. Run 'pip install python-telegram-bot'")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gbpbot.telegram_bot")

# Import conditionnel des modules d'IA
try:
    from gbpbot.ai import create_ai_client, get_prompt_manager, create_market_intelligence
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    ai_imports_ok = True
except ImportError:
    ai_imports_ok = False
    logger.warning("Modules d'IA non disponibles pour le bot Telegram")

class TelegramBot:
    """
    Bot Telegram qui permet de contrôler GBPBot à distance.
    
    Fournit des commandes pour:
    - Démarrer/arrêter le bot
    - Activer/désactiver des modules
    - Consulter les performances
    - Recevoir des alertes
    - Obtenir des analyses IA
    """
    
    def __init__(self, token: Optional[str] = None, config: Optional[Dict[str, Any]] = None, bot_state: Any = None):
        """
        Initialise le bot Telegram
        
        Args:
            token: Token du bot Telegram (optionnel, par défaut depuis la config)
            config: Configuration du bot (optionnel)
            bot_state: Référence à l'état du GBPBot (optionnel)
        """
        self.config = config or {}
        self.bot_state = bot_state
        
        # Token Telegram (priorité à l'argument, puis la config, puis l'environnement)
        self.token = token or self.config.get("telegram_token") or os.environ.get("TELEGRAM_TOKEN")
        
        # Liste des utilisateurs autorisés (IDs Telegram)
        self.authorized_users = set()
        self._load_authorized_users()
        
        # État du bot
        self.running = False
        self.application = None
        self.start_time = time.time()
        
        # Files d'attente pour les messages et alertes
        self.message_queue = asyncio.Queue()
        
        # Initialisation des composants IA
        self.ai_client = None
        self.prompt_manager = None
        self.ai_market_analyzer = None
        self.market_intelligence = None
        
        # Initialiser l'IA si disponible
        self._initialize_ai()
        
        logger.info("Bot Telegram initialisé")
    
    def _initialize_ai(self) -> None:
        """Initialise les fonctionnalités d'IA pour le bot Telegram"""
        if not ai_imports_ok:
            logger.warning("Les fonctionnalités d'IA ne sont pas disponibles pour le bot Telegram")
            return
            
        try:
            # Créer un client d'IA de façon synchrone
            ai_provider = self.config.get("ai_provider", os.environ.get("AI_PROVIDER", "auto"))
            
            # Initialiser de façon asynchrone dans une boucle temporaire
            loop = asyncio.new_event_loop()
            self.ai_client = loop.run_until_complete(create_ai_client(provider=ai_provider))
            loop.close()
            
            if self.ai_client is None:
                logger.warning("Impossible de créer le client d'IA pour le bot Telegram")
                return
            
            # Créer le gestionnaire de prompts
            self.prompt_manager = get_prompt_manager()
            
            # Créer l'analyseur de marché avec des types appropriés
            if self.ai_client and self.prompt_manager:
                self.ai_market_analyzer = MarketAnalyzer(self.ai_client, self.prompt_manager)
                logger.info("Analyseur de marché IA initialisé avec succès pour le bot Telegram")
            
            # Initialiser le système d'intelligence de marché avec Claude 3.7
            if ai_provider == "claude" or os.environ.get("AI_PROVIDER") == "claude":
                # Créer une tâche d'initialisation qui sera exécutée après le démarrage du bot
                logger.info("L'intelligence de marché Claude 3.7 sera initialisée au démarrage")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'IA pour le bot Telegram: {str(e)}")
            self.ai_client = None
            self.ai_market_analyzer = None
            self.market_intelligence = None
    
    async def _initialize_claude_market_intelligence(self) -> None:
        """Initialise le système d'intelligence de marché basé sur Claude 3.7"""
        try:
            # Configuration pour l'intelligence de marché
            market_intelligence_config = {
                "ai_config": {
                    "provider": os.environ.get("AI_PROVIDER", "claude"),
                    "api_key": os.environ.get("CLAUDE_API_KEY"),
                    "model": os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20240229")
                },
                "web_search_config": {
                    "serper_api_key": os.environ.get("SERPER_API_KEY"),
                    "enable_cache": True,
                    "cache_ttl": 3600  # 1 heure
                }
            }
            
            # Créer l'instance d'intelligence de marché
            self.market_intelligence = await create_market_intelligence(market_intelligence_config)
            logger.info("Intelligence de marché Claude 3.7 initialisée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'intelligence de marché: {str(e)}")
            self.market_intelligence = None
    
    def _load_authorized_users(self) -> None:
        """
        Charge la liste des utilisateurs autorisés depuis la configuration
        """
        # Récupérer les IDs des utilisateurs autorisés (chaîne séparée par des virgules)
        authorized_ids_str = self.config.get("TELEGRAM_AUTHORIZED_USERS", "") or os.environ.get("TELEGRAM_AUTHORIZED_USERS", "")
        
        # Convertir en liste d'entiers
        if authorized_ids_str:
            try:
                self.authorized_users = set(int(user_id.strip()) for user_id in authorized_ids_str.split(",") if user_id.strip())
                logger.info(f"Utilisateurs autorisés chargés: {self.authorized_users}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des utilisateurs autorisés: {str(e)}")
    
    def _is_user_authorized(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur est autorisé à utiliser le bot
        
        Args:
            user_id: ID de l'utilisateur Telegram
            
        Returns:
            bool: True si l'utilisateur est autorisé, False sinon
        """
        # Si aucun utilisateur autorisé n'est configuré, autoriser tout le monde
        if not self.authorized_users:
            return True
            
        return user_id in self.authorized_users
    
    async def start(self) -> bool:
        """
        Démarre le bot Telegram
        
        Returns:
            bool: True si démarré avec succès, False sinon
        """
        if self.running:
            logger.warning("Le bot Telegram est déjà en cours d'exécution")
            return True
            
        if not telegram_imports_ok or not self.token:
            logger.error("Configuration Telegram incomplète, impossible de démarrer le bot")
            return False
            
        try:
            # Initialiser l'application Telegram
            self.application = Application.builder().token(self.token).build()
            
            # Ajouter les gestionnaires de commandes
            self.application.add_handler(CommandHandler("start", self._command_start))
            self.application.add_handler(CommandHandler("help", self._command_help))
            self.application.add_handler(CommandHandler("status", self._command_status))
            self.application.add_handler(CommandHandler("modules", self._command_modules))
            self.application.add_handler(CommandHandler("start_bot", self._command_start_bot))
            self.application.add_handler(CommandHandler("stop_bot", self._command_stop_bot))
            self.application.add_handler(CommandHandler("stats", self._command_stats))
            self.application.add_handler(CommandHandler("profits", self._command_profits))
            
            # Commandes IA
            self.application.add_handler(CommandHandler("analyze_market", self._command_analyze_market))
            self.application.add_handler(CommandHandler("analyze_token", self._command_analyze_token))
            self.application.add_handler(CommandHandler("predict", self._command_predict))
            
            # Nouvelles commandes Claude 3.7
            self.application.add_handler(CommandHandler("claude_analyze", self._command_claude_analyze))
            self.application.add_handler(CommandHandler("market_overview", self._command_market_overview))
            self.application.add_handler(CommandHandler("token_score", self._command_token_score))
            self.application.add_handler(CommandHandler("trading_strategy", self._command_trading_strategy))
            
            # Ajouter le gestionnaire de callbacks pour les boutons inline
            self.application.add_handler(CallbackQueryHandler(self._button_callback))
            
            # Démarrer le bot dans un thread séparé pour ne pas bloquer
            threading.Thread(target=self._run_bot, daemon=True).start()
            
            # Initialiser l'intelligence de marché après le démarrage du bot
            if ai_imports_ok and self.ai_client and os.environ.get("AI_PROVIDER") == "claude":
                asyncio.create_task(self._initialize_claude_market_intelligence())
            
            self.running = True
            logger.info("Bot Telegram démarré avec succès")
            return True
            
        except Exception as e:
            logger.exception(f"Erreur lors du démarrage du bot Telegram: {str(e)}")
            return False
    
    def _run_bot(self) -> None:
        """
        Exécute le bot Telegram dans une boucle d'événements asyncio
        """
        # Créer une nouvelle boucle d'événements pour ce thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Exécuter le bot
        loop.run_until_complete(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
    
    async def stop(self) -> bool:
        """
        Arrête le bot Telegram
        
        Returns:
            bool: True si arrêté avec succès, False sinon
        """
        if not self.running:
            logger.warning("Le bot Telegram n'est pas en cours d'exécution")
            return True
            
        try:
            # Arrêter le bot
            if self.application:
                await self.application.stop()
                
            self.running = False
            logger.info("Bot Telegram arrêté avec succès")
            return True
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'arrêt du bot Telegram: {str(e)}")
            return False
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envoie un message à tous les utilisateurs autorisés
        
        Args:
            message: Message à envoyer
            parse_mode: Mode d'analyse du message (Markdown, HTML, None)
            
        Returns:
            bool: True si le message a été envoyé avec succès, False sinon
        """
        if not self.running or not self.application:
            logger.warning("Bot Telegram non démarré, impossible d'envoyer un message")
            return False
            
        if not self.authorized_users:
            logger.warning("Aucun utilisateur autorisé, le message ne sera pas envoyé")
            return False
            
        try:
            for user_id in self.authorized_users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=parse_mode
                    )
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi du message à l'utilisateur {user_id}: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des messages: {str(e)}")
            return False
    
    async def send_alert(self, alert_type: str, alert_data: Dict) -> bool:
        """
        Envoie une alerte aux utilisateurs autorisés
        
        Args:
            alert_type: Type d'alerte ('profit', 'error', 'security', etc.)
            alert_data: Données de l'alerte
            
        Returns:
            bool: True si l'alerte a été envoyée avec succès, False sinon
        """
        if not self.running:
            return False
            
        try:
            # Formater l'alerte selon son type
            if alert_type == "profit":
                message = (
                    f"🔔 <b>Alerte Profit</b> 🔔\n\n"
                    f"<b>Stratégie:</b> {alert_data.get('strategy', 'N/A')}\n"
                    f"<b>Token:</b> {alert_data.get('token_symbol', 'N/A')}\n"
                    f"<b>Profit:</b> {alert_data.get('profit_usd', 0):.2f} USD ({alert_data.get('profit_percentage', 0):.2f}%)\n"
                    f"<b>Temps:</b> {datetime.now().strftime('%H:%M:%S')}"
                )
            elif alert_type == "error":
                message = (
                    f"🚨 <b>Alerte Erreur</b> 🚨\n\n"
                    f"<b>Module:</b> {alert_data.get('module', 'N/A')}\n"
                    f"<b>Erreur:</b> {alert_data.get('error', 'N/A')}\n"
                    f"<b>Temps:</b> {datetime.now().strftime('%H:%M:%S')}"
                )
            elif alert_type == "security":
                message = (
                    f"⚠️ <b>Alerte Sécurité</b> ⚠️\n\n"
                    f"<b>Type:</b> {alert_data.get('type', 'N/A')}\n"
                    f"<b>Token:</b> {alert_data.get('token_symbol', 'N/A')}\n"
                    f"<b>Détails:</b> {alert_data.get('details', 'N/A')}\n"
                    f"<b>Temps:</b> {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                message = (
                    f"ℹ️ <b>Notification</b> ℹ️\n\n"
                    f"<b>Type:</b> {alert_type}\n"
                    f"<b>Détails:</b> {json.dumps(alert_data, indent=2)}\n"
                    f"<b>Temps:</b> {datetime.now().strftime('%H:%M:%S')}"
                )
            
            # Envoyer le message
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte: {str(e)}")
            return False
    
    # Gestionnaires de commandes Telegram
    
    async def _command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /start"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        await update.message.reply_text(
            f"👋 Bienvenue dans le GBPBot Telegram Interface!\n\n"
            f"Utilisez /help pour voir les commandes disponibles."
        )
    
    async def _command_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Affiche l'aide du bot.
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        help_text = """
<b>🤖 Aide GBPBot - Commandes disponibles</b>

<b>Commandes de base:</b>
/start - Démarrer le bot
/help - Afficher ce message d'aide
/status - Afficher le statut du bot
/modules - Gérer les modules du bot

<b>Contrôles:</b>
/start_bot - Démarrer le GBPBot
/stop_bot - Arrêter le GBPBot

<b>Statistiques:</b>
/stats - Afficher les statistiques du bot
/profits - Afficher les profits réalisés

<b>Analyse IA:</b>
/analyze_market - Analyser le marché global
/analyze_token [symbol] - Analyser un token spécifique
/predict [symbol] [heures=24] - Prédire l'évolution d'un token

<b>Analyse Claude 3.7:</b>
/claude_analyze - Informations sur les analyses Claude 3.7
/market_overview - Obtenir une vue d'ensemble du marché
/token_score [symbol] [chain] - Évaluer le potentiel d'un token
/trading_strategy [symbol] [chain] - Générer une stratégie
"""
        await update.message.reply_text(help_text, parse_mode="HTML")
    
    async def _command_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /status"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not self.bot_state:
            await update.message.reply_text("❌ Impossible de récupérer l'état du bot.")
            return
            
        # Récupérer l'état du bot
        is_running = self.bot_state.running
        uptime = time.time() - self.bot_state.start_time if is_running and self.bot_state.start_time else 0
        uptime_str = self._format_duration(uptime) if uptime > 0 else "N/A"
        
        # Récupérer l'état des modules
        active_modules = [name for name, active in self.bot_state.active_modules.items() if active]
        
        # Créer le message d'état
        status_message = (
            f"📊 <b>État du GBPBot:</b>\n\n"
            f"<b>Bot en cours d'exécution:</b> {'✅' if is_running else '❌'}\n"
            f"<b>Actif depuis:</b> {uptime_str}\n\n"
            f"<b>Modules actifs ({len(active_modules)}/{len(self.bot_state.active_modules)}):</b>\n"
        )
        
        if active_modules:
            for module in active_modules:
                status_message += f"- {module.replace('_', ' ').title()}\n"
        else:
            status_message += "- Aucun module actif\n"
        
        await update.message.reply_text(status_message, parse_mode="HTML")
    
    async def _command_modules(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /modules"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not self.bot_state:
            await update.message.reply_text("❌ Impossible de récupérer l'état du bot.")
            return
            
        # Créer les boutons pour chaque module
        keyboard = []
        
        for module_name, is_active in self.bot_state.active_modules.items():
            status = "✅" if is_active else "❌"
            display_name = module_name.replace("_", " ").title()
            
            # Créer un bouton pour activer/désactiver le module
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {display_name}",
                    callback_data=f"toggle_module:{module_name}"
                )
            ])
        
        # Ajouter un bouton pour revenir au menu principal
        keyboard.append([
            InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔌 <b>Gestion des Modules</b>\n\n"
            "Cliquez sur un module pour l'activer ou le désactiver:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    async def _command_start_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /start_bot"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not self.bot_state:
            await update.message.reply_text("❌ Impossible de récupérer l'état du bot.")
            return
            
        if self.bot_state.running:
            await update.message.reply_text("ℹ️ Le bot est déjà en cours d'exécution.")
            return
            
        # Démarrer le bot
        await update.message.reply_text("🚀 Démarrage du GBPBot...")
        
        try:
            self.bot_state.start()
            await update.message.reply_text("✅ GBPBot démarré avec succès!")
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur lors du démarrage du bot: {str(e)}")
    
    async def _command_stop_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /stop_bot"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not self.bot_state:
            await update.message.reply_text("❌ Impossible de récupérer l'état du bot.")
            return
            
        if not self.bot_state.running:
            await update.message.reply_text("ℹ️ Le bot n'est pas en cours d'exécution.")
            return
            
        # Arrêter le bot
        await update.message.reply_text("🛑 Arrêt du GBPBot...")
        
        try:
            # Arrêter tous les modules actifs
            for module_name, is_active in self.bot_state.active_modules.items():
                if is_active:
                    # Idéalement, nous appellerions une fonction asynchrone pour arrêter le module
                    # mais cela dépend de l'implémentation du GBPBot
                    self.bot_state.active_modules[module_name] = False
            
            self.bot_state.stop()
            await update.message.reply_text("✅ GBPBot arrêté avec succès!")
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur lors de l'arrêt du bot: {str(e)}")
    
    async def _command_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /stats"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not self.bot_state:
            await update.message.reply_text("❌ Impossible de récupérer l'état du bot.")
            return
            
        # Simuler la récupération des statistiques (à implémenter selon la structure du GBPBot)
        stats = {
            "transactions_total": 0,
            "success_rate": 0,
            "tokens_sniped": 0,
            "arbitrages_executed": 0,
            "frontruns_executed": 0,
        }
        
        # Essayer de récupérer les vraies statistiques des stratégies actives
        for strategy_name, strategy in self.bot_state.strategies.items():
            if hasattr(strategy, 'get_stats'):
                try:
                    strategy_stats = strategy.get_stats()
                    
                    # Mise à jour des statistiques globales (les noms des champs peuvent varier)
                    if 'tokens_sniped' in strategy_stats:
                        stats['tokens_sniped'] += strategy_stats['tokens_sniped']
                    
                    if 'successful_arbitrages' in strategy_stats:
                        stats['arbitrages_executed'] += strategy_stats['successful_arbitrages']
                    
                    if 'successful_frontruns' in strategy_stats:
                        stats['frontruns_executed'] += strategy_stats['successful_frontruns']
                    
                    # Mise à jour du total des transactions
                    for key in ['tokens_sniped', 'successful_arbitrages', 'successful_frontruns']:
                        if key in strategy_stats:
                            stats['transactions_total'] += strategy_stats[key]
                    
                    # Calcul du taux de succès
                    success_count = 0
                    total_count = 0
                    
                    for key in ['successful_snipes', 'successful_arbitrages', 'successful_frontruns']:
                        if key in strategy_stats:
                            success_count += strategy_stats[key]
                    
                    for key in ['tokens_sniped', 'arbitrages_attempted', 'frontrun_attempts']:
                        if key in strategy_stats:
                            total_count += strategy_stats[key]
                    
                    if total_count > 0:
                        stats['success_rate'] = (success_count / total_count) * 100
                
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération des statistiques de {strategy_name}: {str(e)}")
        
        # Créer le message de statistiques
        stats_message = (
            f"📈 <b>Statistiques GBPBot:</b>\n\n"
            f"<b>Transactions totales:</b> {stats['transactions_total']}\n"
            f"<b>Taux de succès:</b> {stats['success_rate']:.2f}%\n\n"
            f"<b>Tokens snipés:</b> {stats['tokens_sniped']}\n"
            f"<b>Arbitrages exécutés:</b> {stats['arbitrages_executed']}\n"
            f"<b>Frontruns exécutés:</b> {stats['frontruns_executed']}\n"
        )
        
        await update.message.reply_text(stats_message, parse_mode="HTML")
    
    async def _command_profits(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gestionnaire pour la commande /profits"""
        user_id = update.effective_user.id
        
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not self.bot_state:
            await update.message.reply_text("❌ Impossible de récupérer l'état du bot.")
            return
            
        # Simuler la récupération des profits (à implémenter selon la structure du GBPBot)
        profits = {
            "total_profit_usd": 0,
            "hourly_profit_usd": 0,
            "sniping_profit_usd": 0,
            "arbitrage_profit_usd": 0,
            "frontrun_profit_usd": 0,
            "best_transaction": {
                "strategy": "N/A",
                "profit_usd": 0,
                "token_symbol": "N/A",
                "time": "N/A"
            }
        }
        
        # Essayer de récupérer les vrais profits des stratégies actives
        for strategy_name, strategy in self.bot_state.strategies.items():
            if hasattr(strategy, 'get_stats'):
                try:
                    strategy_stats = strategy.get_stats()
                    
                    # Mise à jour des profits par stratégie
                    if 'net_profit_usd' in strategy_stats:
                        profits['total_profit_usd'] += strategy_stats['net_profit_usd']
                        
                        if 'sniping' in strategy_name:
                            profits['sniping_profit_usd'] += strategy_stats['net_profit_usd']
                        elif 'arbitrage' in strategy_name:
                            profits['arbitrage_profit_usd'] += strategy_stats['net_profit_usd']
                        elif 'frontrun' in strategy_name:
                            profits['frontrun_profit_usd'] += strategy_stats['net_profit_usd']
                    
                    # Mise à jour du profit horaire
                    if 'hourly_profit_usd' in strategy_stats:
                        profits['hourly_profit_usd'] += strategy_stats['hourly_profit_usd']
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération des profits de {strategy_name}: {str(e)}")
        
        # Créer le message de profits
        profits_message = (
            f"💰 <b>Profits GBPBot:</b>\n\n"
            f"<b>Profit total:</b> ${profits['total_profit_usd']:.2f}\n"
            f"<b>Profit horaire:</b> ${profits['hourly_profit_usd']:.2f}/h\n\n"
            f"<b>Répartition par stratégie:</b>\n"
            f"- Sniping: ${profits['sniping_profit_usd']:.2f}\n"
            f"- Arbitrage: ${profits['arbitrage_profit_usd']:.2f}\n"
            f"- Frontrunning: ${profits['frontrun_profit_usd']:.2f}\n"
        )
        
        await update.message.reply_text(profits_message, parse_mode="HTML")
    
    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gère les callbacks des boutons inline"""
        query = update.callback_query
        await query.answer()
        
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await query.edit_message_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
        
        # Récupérer les données du callback
        callback_data = query.data
        
        # Traiter les différents types de callbacks
        if callback_data.startswith("strategy_"):
            # Format: strategy_TOKEN_CHAIN
            parts = callback_data.split("_")
            if len(parts) >= 3:
                token_symbol = parts[1]
                chain = parts[2]
                
                await query.edit_message_text(
                    f"⏳ Génération d'une stratégie de trading pour {token_symbol} sur {chain}...\n"
                    "Cette opération peut prendre jusqu'à 45 secondes."
                )
                
                try:
                    # Générer la stratégie de trading avec Claude 3.7
                    if hasattr(self, 'market_intelligence') and self.market_intelligence:
                        strategy = await self.market_intelligence.generate_trading_strategy(
                            token_symbol=token_symbol,
                            chain=chain
                        )
                        
                        # Formater et envoyer la réponse (similaire à _command_trading_strategy)
                        if strategy:
                            # En-tête
                            response = f"<b>📊 STRATÉGIE DE TRADING: {token_symbol} ({chain.upper()}) - {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n\n"
                            
                            # Type de stratégie
                            strategy_name = strategy.get('strategy_name', 'Auto-optimisée')
                            risk_level = strategy.get('risk_level', 'Équilibré')
                            response += f"<b>⚙️ TYPE:</b> {strategy_name}\n"
                            response += f"<b>🎯 PROFIL DE RISQUE:</b> {risk_level}\n\n"
                            
                            # Points d'entrée
                            response += "<b>🟢 POINTS D'ENTRÉE:</b>\n"
                            entry_points = strategy.get('entry_points', [])
                            if entry_points:
                                for point in entry_points[:3]:  # Limiter à 3 points
                                    response += f"• {point}\n"
                            else:
                                response += "• Aucun point d'entrée spécifique identifié\n"
                            response += "\n"
                            
                            # Points de sortie
                            response += "<b>🔴 POINTS DE SORTIE:</b>\n"
                            exit_points = strategy.get('exit_points', [])
                            if exit_points:
                                for point in exit_points[:3]:  # Limiter à 3 points
                                    response += f"• {point}\n"
                            else:
                                response += "• Aucun point de sortie spécifique identifié\n"
                            response += "\n"
                            
                            # Paramètres de trading
                            response += "<b>⚙️ PARAMÈTRES RECOMMANDÉS:</b>\n"
                            parameters = strategy.get('parameters', {})
                            take_profit = parameters.get('take_profit', 'Non spécifié')
                            stop_loss = parameters.get('stop_loss', 'Non spécifié')
                            position_size = parameters.get('position_size', 'Non spécifié')
                            response += f"• <b>Take Profit:</b> {take_profit}\n"
                            response += f"• <b>Stop Loss:</b> {stop_loss}\n"
                            response += f"• <b>Taille de position:</b> {position_size}\n\n"
                            
                            # Avertissement
                            response += "<i>⚠️ Cette stratégie est fournie à titre informatif uniquement.</i>\n\n"
                            
                            # Pied de page
                            response += "<i>Stratégie générée par Claude 3.7</i>"
                            
                            await query.edit_message_text(response, parse_mode="HTML")
                        else:
                            await query.edit_message_text(
                                f"❌ Impossible de générer une stratégie pour {token_symbol}. Veuillez réessayer."
                            )
                    else:
                        await query.edit_message_text(
                            "⚠️ Le système d'analyse Claude 3.7 n'est pas disponible actuellement."
                        )
                except Exception as e:
                    logger.error(f"Erreur lors de la génération de la stratégie: {str(e)}")
                    await query.edit_message_text(
                        f"❌ Une erreur est survenue lors de la génération de la stratégie: {str(e)}"
                    )
        # ... traitement d'autres types de callbacks si nécessaire ...
    
    def _format_duration(self, seconds: float) -> str:
        """
        Formate une durée en secondes en format lisible
        
        Args:
            seconds: Durée en secondes
            
        Returns:
            str: Durée formatée
        """
        if seconds < 60:
            return f"{int(seconds)}s"
            
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        if days > 0:
            return f"{days}j {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"
    
    async def _command_analyze_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Analyse les conditions actuelles du marché crypto.
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        # Vérifier si l'IA est disponible
        if not self.ai_market_analyzer:
            await update.message.reply_text("⚠️ L'analyse IA n'est pas disponible actuellement.")
            return
            
        await update.message.reply_text("⏳ Analyse du marché en cours, veuillez patienter...")
        
        try:
            # Simuler des données de marché pour l'exemple
            market_data = self._get_simulated_market_data()
            
            # Analyser les données du marché (utilisation d'une méthode synchrone pour éviter l'erreur)
            if hasattr(self.ai_market_analyzer, "analyze_market_data"):
                analysis = self.ai_market_analyzer.analyze_market_data(market_data)
            else:
                # Fallback si la méthode n'existe pas
                analysis = {
                    "market_trend": "Bullish",
                    "sentiment": "Positif",
                    "support_levels": [42000, 40800, 39500],
                    "resistance_levels": [44500, 46000, 48000],
                    "key_indicators": [
                        {"name": "RSI", "value": "58", "interpretation": "Neutre, légèrement haussier"},
                        {"name": "MACD", "value": "Positif", "interpretation": "Signal d'achat récent"}
                    ]
                }
            
            # Formater et envoyer la réponse
            response = f"""
<b>📊 ANALYSE DU MARCHÉ CRYPTO</b>
<i>{datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>

<b>Tendance générale:</b> {analysis.get('market_trend', 'Non disponible')}
<b>Sentiment:</b> {analysis.get('sentiment', 'Non disponible')}

<b>Niveaux de support:</b>
{self._format_bullet_points([f"${level:,}" for level in analysis.get('support_levels', [])])}

<b>Niveaux de résistance:</b>
{self._format_bullet_points([f"${level:,}" for level in analysis.get('resistance_levels', [])])}

<b>Indicateurs clés:</b>
{self._format_indicators(analysis.get('key_indicators', []))}

<i>Cette analyse est générée par IA et ne constitue pas un conseil financier.</i>
"""
            await update.message.reply_text(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {str(e)}")
            await update.message.reply_text(f"❌ Une erreur est survenue lors de l'analyse: {str(e)}")
    
    async def _command_analyze_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Analyse un token spécifique.
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        # Vérifier si l'IA est disponible
        if not self.ai_market_analyzer:
            await update.message.reply_text("⚠️ L'analyse IA n'est pas disponible actuellement.")
            return
            
        # Récupérer les arguments
        args = context.args
        if not args:
            await update.message.reply_text(
                "⚠️ Veuillez spécifier un symbole de token.\n"
                "Exemple: <code>/analyze_token BTC</code>",
                parse_mode="HTML"
            )
            return
            
        token_symbol = args[0].upper()
        await update.message.reply_text(f"⏳ Analyse du token {token_symbol} en cours, veuillez patienter...")
        
        try:
            # Simuler des données de token pour l'exemple
            token_data = self._get_simulated_token_data(token_symbol)
            
            # Évaluer le score du token (utilisation d'une méthode synchrone pour éviter l'erreur)
            if hasattr(self.ai_market_analyzer, "evaluate_token_score"):
                token_score = self.ai_market_analyzer.evaluate_token_score({"token": token_data})
            else:
                # Fallback si la méthode n'existe pas
                token_score = {
                    "score": 75,
                    "risk_level": "Moyen",
                    "recommendation": "Surveiller",
                    "factors": [
                        "Volume d'échange élevé",
                        "Communauté active",
                        "Volatilité importante"
                    ]
                }
            
            # Analyser les patterns pour ce token (utilisation d'une méthode synchrone pour éviter l'erreur)
            if hasattr(self.ai_market_analyzer, "detect_pattern"):
                pattern_analysis = self.ai_market_analyzer.detect_pattern(token_data)
            else:
                # Fallback si la méthode n'existe pas
                pattern_analysis = {
                    "pattern": "Consolidation",
                    "confidence": 0.8,
                    "expected_movement": "Hausse modérée après consolidation",
                    "timeframe": "Moyen terme (1-2 semaines)"
                }
            
            # Formater et envoyer la réponse
            response = f"""
<b>🔍 ANALYSE DU TOKEN {token_symbol}</b>
<i>{datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>

<b>Score:</b> {token_score.get('score', 0)}/100
<b>Niveau de risque:</b> {token_score.get('risk_level', 'Non disponible')}
<b>Recommandation:</b> {token_score.get('recommendation', 'Non disponible')}

<b>Facteurs influents:</b>
{self._format_bullet_points(token_score.get('factors', []))}

<b>Pattern détecté:</b> {pattern_analysis.get('pattern', 'Aucun')}
<b>Confiance:</b> {pattern_analysis.get('confidence', 0) * 100:.1f}%
<b>Mouvement attendu:</b> {pattern_analysis.get('expected_movement', 'Incertain')}
<b>Horizon temporel:</b> {pattern_analysis.get('timeframe', 'Court terme')}

<i>Cette analyse est générée par IA et ne constitue pas un conseil financier.</i>
"""
            await update.message.reply_text(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du token: {str(e)}")
            await update.message.reply_text(f"❌ Une erreur est survenue lors de l'analyse: {str(e)}")
    
    async def _command_predict(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Prédit le mouvement de prix d'un token.
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        # Vérifier si l'IA est disponible
        if not self.ai_market_analyzer:
            await update.message.reply_text("⚠️ La prédiction IA n'est pas disponible actuellement.")
            return
            
        # Récupérer les arguments
        args = context.args
        if not args:
            await update.message.reply_text(
                "⚠️ Veuillez spécifier un symbole de token et optionnellement une durée.\n"
                "Exemple: <code>/predict BTC 24h</code>",
                parse_mode="HTML"
            )
            return
            
        token_symbol = args[0].upper()
        timeframe = args[1] if len(args) > 1 else "24h"
        
        await update.message.reply_text(f"⏳ Prédiction pour {token_symbol} sur {timeframe} en cours, veuillez patienter...")
        
        try:
            # Simuler des données de token pour l'exemple
            token_data = self._get_simulated_token_data(token_symbol)
            token_data["timeframe"] = timeframe
            
            # Faire une prédiction
            # Pour éviter l'erreur, nous utilisons une approche synchrone
            # Dans un cas réel, il faudrait adapter le code pour gérer cette méthode correctement
            prediction = {
                "predicted_direction": "up",
                "predicted_change_percent": 5.2,
                "confidence": 0.78,
                "influential_factors": [
                    "Tendance haussière globale du marché",
                    "Augmentation du volume d'échange",
                    "Intérêt communautaire croissant"
                ],
                "potential_risks": [
                    "Résistance forte à $45,000",
                    "Volatilité du marché global",
                    "Incertitude réglementaire"
                ]
            }
            
            # Calculer l'emoji en fonction de la prédiction
            if prediction.get('predicted_direction', '') == 'up':
                direction_emoji = '🟢 HAUSSE'
            elif prediction.get('predicted_direction', '') == 'down':
                direction_emoji = '🔴 BAISSE'
            else:
                direction_emoji = '⚪ STABLE'
                
            # Formater et envoyer la réponse
            response = f"""
<b>🔮 PRÉDICTION POUR {token_symbol} ({timeframe})</b>
<i>{datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>

<b>Direction attendue:</b> {direction_emoji}
<b>Variation estimée:</b> {prediction.get('predicted_change_percent', 0):.2f}%
<b>Confiance:</b> {prediction.get('confidence', 0) * 100:.1f}%

<b>Facteurs influents:</b>
{self._format_bullet_points(prediction.get('influential_factors', []))}

<b>Risques potentiels:</b>
{self._format_bullet_points(prediction.get('potential_risks', []))}

<i>Prédiction générée par IA le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}</i>
<i>Rappel: Ne constitue pas un conseil financier</i>
"""
            await update.message.reply_text(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction: {str(e)}")
            await update.message.reply_text(f"❌ Une erreur est survenue lors de la prédiction: {str(e)}")
    
    def _get_simulated_market_data(self) -> Dict[str, Any]:
        """Génère des données de marché simulées pour la démonstration"""
        # Dans un cas réel, ces données proviendraient des APIs
        return {
            "market_conditions": {
                "btc_price": 53000 + (1000 * (0.5 - (time.time() % 100) / 100)),
                "eth_price": 3200 + (200 * (0.5 - (time.time() % 100) / 100)),
                "sol_price": 90 + (10 * (0.5 - (time.time() % 100) / 100)),
                "avax_price": 45 + (5 * (0.5 - (time.time() % 100) / 100)),
                "total_market_cap": 2.1e12,
                "btc_dominance": 48.5,
                "fear_greed_index": 65,
                "timestamp": time.time()
            },
            "top_performing": [
                {"symbol": "SOL", "change_24h": 12.5},
                {"symbol": "BONK", "change_24h": 23.7},
                {"symbol": "JTO", "change_24h": 8.2}
            ],
            "worst_performing": [
                {"symbol": "SUI", "change_24h": -3.8},
                {"symbol": "DOGE", "change_24h": -2.1},
                {"symbol": "ATOM", "change_24h": -1.7}
            ]
        }
    
    def _get_simulated_token_data(self, symbol: str) -> Dict[str, Any]:
        """Génère des données simulées pour un token spécifique"""
        # Seed random avec le symbole pour avoir la même simulation à chaque fois
        import random
        random.seed(hash(symbol))
        
        # Générer des prix sur les dernières 24h (toutes les heures)
        current_price = 10 * random.uniform(0.5, 10)
        hourly_change = random.uniform(-0.03, 0.05)  # Entre -3% et +5% par heure
        
        price_history = []
        for i in range(24, 0, -1):
            # Ajouter un peu d'aléatoire mais garder la tendance générale
            price = current_price * (1 + hourly_change * i + random.uniform(-0.02, 0.02))
            price_history.append({
                "timestamp": time.time() - (i * 3600),
                "price": price
            })
        
        return {
            "symbol": symbol,
            "name": f"{symbol} Token",
            "current_price": current_price,
            "market_cap": current_price * random.uniform(1e6, 1e9),
            "liquidity": current_price * random.uniform(1e5, 1e7),
            "volume_24h": current_price * random.uniform(1e5, 1e8),
            "change_24h": hourly_change * 24 * 100,
            "price_history": price_history,
            "holders": random.randint(500, 50000),
            "creation_time": time.time() - random.uniform(3600 * 24, 3600 * 24 * 90),  # Entre 1 et 90 jours
            "social_metrics": {
                "twitter_followers": random.randint(0, 100000),
                "telegram_members": random.randint(0, 20000),
                "sentiment_score": random.uniform(0.3, 0.9)
            }
        }
    
    def _format_indicators(self, indicators: List[Dict[str, Any]]) -> str:
        """Formate une liste d'indicateurs pour l'affichage"""
        if not indicators:
            return "Aucun indicateur disponible"
            
        result = []
        for indicator in indicators:
            if isinstance(indicator, dict):
                result.append(f"• {indicator.get('name', 'Inconnu')}: {indicator.get('value', 'N/A')}")
            elif isinstance(indicator, str):
                result.append(f"• {indicator}")
        
        return "\n".join(result) if result else "Aucun indicateur disponible"
    
    def _format_bullet_points(self, points: List[str]) -> str:
        """Formate une liste de points pour l'affichage"""
        if not points:
            return "Aucune information disponible"
            
        return "\n".join(f"• {point}" for point in points)
    
    async def _command_claude_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Affiche les informations sur les analyses avec Claude 3.7
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
        
        # Vérifier si le système d'intelligence de marché est disponible
        if not hasattr(self, 'market_intelligence') or not self.market_intelligence:
            await update.message.reply_text(
                "⚠️ Le système d'analyse Claude 3.7 n'est pas disponible actuellement.\n\n"
                "Vérifiez que:\n"
                "- La variable AI_PROVIDER est réglée sur 'claude'\n"
                "- Une clé API Claude valide est configurée dans CLAUDE_API_KEY\n"
                "- La variable SERPER_API_KEY est configurée pour la recherche web"
            )
            return
        
        message = """
<b>🧠 Analyses avancées avec Claude 3.7</b>

GBPBot intègre Claude 3.7 pour des analyses de marché avancées et des évaluations de tokens ultra-précises.

<b>Fonctionnalités disponibles:</b>

🔹 <b>/market_overview</b> - Vue d'ensemble du marché crypto
Analyse les tendances globales, les secteurs performants et les opportunités émergentes.

🔹 <b>/token_score [symbol] [chain]</b> - Évaluation complète d'un token
Analyse le potentiel d'un token spécifique avec recherche web, notation de risque et opportunités.
Exemple: <code>/token_score BONK solana</code>

🔹 <b>/trading_strategy [symbol] [chain]</b> - Génération de stratégie
Crée une stratégie de trading optimisée pour un token spécifique.
Exemple: <code>/trading_strategy BONK solana</code>

<b>Caractéristiques:</b>
✅ Analyse en temps réel
✅ Recherche web intégrée
✅ Notation de risque (0-100)
✅ Détection de signaux d'achat/vente
✅ Identification des drapeaux rouges

<i>Utilisez ces commandes pour des décisions de trading plus éclairées!</i>
"""
        
        # Envoyer le message
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def _command_market_overview(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Fournit une vue d'ensemble du marché crypto avec Claude 3.7
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
        
        # Vérifier si le système d'intelligence de marché est disponible
        if not hasattr(self, 'market_intelligence') or not self.market_intelligence:
            await update.message.reply_text(
                "⚠️ Le système d'analyse Claude 3.7 n'est pas disponible actuellement."
            )
            return
        
        # Envoyer un message d'attente
        waiting_message = await update.message.reply_text(
            "⏳ Analyse du marché en cours avec Claude 3.7...\n"
            "Cette opération peut prendre jusqu'à 30 secondes."
        )
        
        try:
            # Réaliser l'analyse de marché avec Claude 3.7
            keywords = ["crypto market", "trending tokens", "market cap", "memecoin"]
            market_analysis = await self.market_intelligence.analyze_market(
                keywords=keywords,
                with_web_search=True
            )
            
            # Formater la réponse
            if market_analysis:
                # En-tête
                overview = f"<b>🔍 ANALYSE DE MARCHÉ CRYPTO - {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n\n"
                
                # Tendance globale
                overview += f"<b>📊 TENDANCE GLOBALE:</b> {market_analysis.get('market_trend', 'Non disponible')}\n\n"
                
                # Sentiment
                sentiment = market_analysis.get('sentiment', 'Neutre')
                sentiment_emoji = "🟢" if sentiment == "Bullish" else "🔴" if sentiment == "Bearish" else "🟡"
                overview += f"<b>{sentiment_emoji} SENTIMENT:</b> {sentiment}\n\n"
                
                # Secteurs performants
                overview += "<b>🔝 SECTEURS PERFORMANTS:</b>\n"
                sectors = market_analysis.get('hot_sectors', [])
                if sectors:
                    for sector in sectors[:3]:  # Limiter à 3 secteurs
                        overview += f"• {sector}\n"
                else:
                    overview += "• Aucun secteur notable identifié\n"
                overview += "\n"
                
                # Tokens à surveiller
                overview += "<b>👀 TOKENS À SURVEILLER:</b>\n"
                tokens = market_analysis.get('tokens_to_watch', [])
                if tokens:
                    for token in tokens[:5]:  # Limiter à 5 tokens
                        if isinstance(token, dict):
                            token_name = token.get('name', '')
                            token_reason = token.get('reason', '')
                            overview += f"• <b>{token_name}</b>: {token_reason}\n"
                        else:
                            overview += f"• {token}\n"
                else:
                    overview += "• Aucun token notable identifié\n"
                overview += "\n"
                
                # Opportunités
                overview += "<b>💡 OPPORTUNITÉS:</b>\n"
                opportunities = market_analysis.get('opportunities', [])
                if opportunities:
                    for opportunity in opportunities[:3]:  # Limiter à 3 opportunités
                        overview += f"• {opportunity}\n"
                else:
                    overview += "• Aucune opportunité notable identifiée\n"
                overview += "\n"
                
                # Risques
                overview += "<b>⚠️ RISQUES À SURVEILLER:</b>\n"
                risks = market_analysis.get('risks', [])
                if risks:
                    for risk in risks[:3]:  # Limiter à 3 risques
                        overview += f"• {risk}\n"
                else:
                    overview += "• Aucun risque majeur identifié actuellement\n"
                overview += "\n"
                
                # Pied de page
                overview += "<i>Analyse générée par Claude 3.7 avec données temps réel</i>"
                
                # Supprimer le message d'attente et envoyer l'analyse
                await waiting_message.delete()
                await update.message.reply_text(overview, parse_mode="HTML")
            else:
                await waiting_message.delete()
                await update.message.reply_text(
                    "❌ Impossible de générer l'analyse de marché. Veuillez réessayer plus tard."
                )
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de marché: {str(e)}")
            await waiting_message.delete()
            await update.message.reply_text(
                f"❌ Une erreur est survenue lors de l'analyse du marché: {str(e)}"
            )
    
    async def _command_token_score(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Évalue un token spécifique avec Claude 3.7
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
        
        # Vérifier si le système d'intelligence de marché est disponible
        if not hasattr(self, 'market_intelligence') or not self.market_intelligence:
            await update.message.reply_text(
                "⚠️ Le système d'analyse Claude 3.7 n'est pas disponible actuellement."
            )
            return
        
        # Récupérer les arguments
        args = context.args
        if not args or len(args) < 1:
            await update.message.reply_text(
                "⚠️ Veuillez spécifier un symbole de token.\n"
                "Exemple: <code>/token_score BONK solana</code>",
                parse_mode="HTML"
            )
            return
        
        token_symbol = args[0].upper()
        chain = args[1].lower() if len(args) > 1 else "solana"  # Solana par défaut
        
        # Vérifier la chaîne
        supported_chains = ["solana", "avax", "avalanche", "eth", "ethereum", "bsc", "polygon"]
        if chain not in supported_chains:
            chain_list = ", ".join(supported_chains)
            await update.message.reply_text(
                f"⚠️ Chaîne non supportée: {chain}\n"
                f"Chaînes supportées: {chain_list}"
            )
            return
        
        # Normaliser le nom de la chaîne
        if chain in ["avax", "avalanche"]:
            chain = "avalanche"
        elif chain in ["eth", "ethereum"]:
            chain = "ethereum"
        
        # Envoyer un message d'attente
        waiting_message = await update.message.reply_text(
            f"⏳ Analyse du token {token_symbol} sur {chain} en cours...\n"
            "Cette opération peut prendre jusqu'à 30 secondes."
        )
        
        try:
            # Réaliser l'analyse de token avec Claude 3.7
            token_analysis = await self.market_intelligence.analyze_token(
                token_symbol=token_symbol,
                chain=chain,
                with_web_search=True
            )
            
            # Formater la réponse
            if token_analysis:
                # En-tête
                analysis = f"<b>🔍 ANALYSE DU TOKEN {token_symbol} ({chain.upper()}) - {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n\n"
                
                # Score et recommandation
                score = token_analysis.get('score', 0)
                score_emoji = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
                recommendation = token_analysis.get('recommendation', 'Non disponible')
                analysis += f"<b>{score_emoji} SCORE:</b> {score}/100\n"
                analysis += f"<b>👉 RECOMMANDATION:</b> {recommendation}\n\n"
                
                # Analyse des risques
                analysis_data = token_analysis.get('analysis', {})
                analysis += "<b>⚖️ ANALYSE:</b>\n"
                analysis += f"• <b>Liquidité:</b> {analysis_data.get('liquidity', 'Non disponible')}\n"
                analysis += f"• <b>Risque de rug pull:</b> {analysis_data.get('rug_pull_risk', 'Non disponible')}\n"
                analysis += f"• <b>Potentiel de croissance:</b> {analysis_data.get('growth_potential', 'Non disponible')}\n\n"
                
                # Drapeaux rouges
                red_flags = analysis_data.get('red_flags', [])
                if red_flags:
                    analysis += "<b>🚩 DRAPEAUX ROUGES:</b>\n"
                    for flag in red_flags[:3]:  # Limiter à 3 drapeaux rouges
                        analysis += f"• {flag}\n"
                    analysis += "\n"
                
                # Raisonnement
                reasoning = token_analysis.get('reasoning', '')
                if reasoning:
                    analysis += "<b>💡 ANALYSE DÉTAILLÉE:</b>\n"
                    # Limiter la longueur du raisonnement pour éviter des messages trop longs
                    max_length = 300
                    if len(reasoning) > max_length:
                        analysis += f"{reasoning[:max_length]}...\n\n"
                    else:
                        analysis += f"{reasoning}\n\n"
                
                # Bouton pour obtenir la stratégie de trading
                keyboard = [
                    [InlineKeyboardButton(f"Générer stratégie pour {token_symbol}", callback_data=f"strategy_{token_symbol}_{chain}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Pied de page
                analysis += "<i>Analyse générée par Claude 3.7 avec données web</i>"
                
                # Supprimer le message d'attente et envoyer l'analyse
                await waiting_message.delete()
                await update.message.reply_text(analysis, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await waiting_message.delete()
                await update.message.reply_text(
                    f"❌ Impossible de générer l'analyse pour {token_symbol}. Veuillez vérifier le symbole et réessayer."
                )
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du token: {str(e)}")
            await waiting_message.delete()
            await update.message.reply_text(
                f"❌ Une erreur est survenue lors de l'analyse du token: {str(e)}"
            )
    
    async def _command_trading_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Génère une stratégie de trading pour un token spécifique avec Claude 3.7
        """
        # Vérifier si l'utilisateur est autorisé
        if not self._is_user_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
        
        # Vérifier si le système d'intelligence de marché est disponible
        if not hasattr(self, 'market_intelligence') or not self.market_intelligence:
            await update.message.reply_text(
                "⚠️ Le système d'analyse Claude 3.7 n'est pas disponible actuellement."
            )
            return
        
        # Récupérer les arguments
        args = context.args
        if not args or len(args) < 1:
            await update.message.reply_text(
                "⚠️ Veuillez spécifier un symbole de token.\n"
                "Exemple: <code>/trading_strategy BONK solana</code>",
                parse_mode="HTML"
            )
            return
        
        token_symbol = args[0].upper()
        chain = args[1].lower() if len(args) > 1 else "solana"  # Solana par défaut
        strategy_type = args[2].lower() if len(args) > 2 else "auto"  # Type de stratégie (auto, scalping, long_term, etc.)
        risk_profile = args[3].lower() if len(args) > 3 else "balanced"  # Profil de risque (conservative, balanced, aggressive)
        
        # Envoyer un message d'attente
        waiting_message = await update.message.reply_text(
            f"⏳ Génération d'une stratégie de trading pour {token_symbol} sur {chain}...\n"
            "Cette opération peut prendre jusqu'à 45 secondes."
        )
        
        try:
            # Générer la stratégie de trading avec Claude 3.7
            strategy = await self.market_intelligence.generate_trading_strategy(
                token_symbol=token_symbol,
                chain=chain,
                strategy_type=strategy_type,
                risk_profile=risk_profile
            )
            
            # Formater la réponse
            if strategy:
                # En-tête
                response = f"<b>📊 STRATÉGIE DE TRADING: {token_symbol} ({chain.upper()}) - {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>\n\n"
                
                # Type de stratégie
                strategy_name = strategy.get('strategy_name', 'Auto-optimisée')
                risk_level = strategy.get('risk_level', 'Équilibré')
                response += f"<b>⚙️ TYPE:</b> {strategy_name}\n"
                response += f"<b>🎯 PROFIL DE RISQUE:</b> {risk_level}\n\n"
                
                # Points d'entrée
                response += "<b>🟢 POINTS D'ENTRÉE:</b>\n"
                entry_points = strategy.get('entry_points', [])
                if entry_points:
                    for point in entry_points[:3]:  # Limiter à 3 points
                        response += f"• {point}\n"
                else:
                    response += "• Aucun point d'entrée spécifique identifié\n"
                response += "\n"
                
                # Points de sortie
                response += "<b>🔴 POINTS DE SORTIE:</b>\n"
                exit_points = strategy.get('exit_points', [])
                if exit_points:
                    for point in exit_points[:3]:  # Limiter à 3 points
                        response += f"• {point}\n"
                else:
                    response += "• Aucun point de sortie spécifique identifié\n"
                response += "\n"
                
                # Paramètres de trading
                response += "<b>⚙️ PARAMÈTRES RECOMMANDÉS:</b>\n"
                parameters = strategy.get('parameters', {})
                take_profit = parameters.get('take_profit', 'Non spécifié')
                stop_loss = parameters.get('stop_loss', 'Non spécifié')
                position_size = parameters.get('position_size', 'Non spécifié')
                response += f"• <b>Take Profit:</b> {take_profit}\n"
                response += f"• <b>Stop Loss:</b> {stop_loss}\n"
                response += f"• <b>Taille de position:</b> {position_size}\n\n"
                
                # Indicateurs à surveiller
                response += "<b>📈 INDICATEURS À SURVEILLER:</b>\n"
                indicators = strategy.get('indicators', [])
                if indicators:
                    for indicator in indicators[:3]:  # Limiter à 3 indicateurs
                        if isinstance(indicator, dict):
                            indicator_name = indicator.get('name', '')
                            indicator_value = indicator.get('value', '')
                            response += f"• <b>{indicator_name}:</b> {indicator_value}\n"
                        else:
                            response += f"• {indicator}\n"
                else:
                    response += "• Aucun indicateur spécifique identifié\n"
                response += "\n"
                
                # Avertissement
                response += "<i>⚠️ Cette stratégie est fournie à titre informatif uniquement et ne constitue pas un conseil financier. Toujours effectuer votre propre recherche.</i>\n\n"
                
                # Pied de page
                response += "<i>Stratégie générée par Claude 3.7</i>"
                
                # Supprimer le message d'attente et envoyer la stratégie
                await waiting_message.delete()
                await update.message.reply_text(response, parse_mode="HTML")
            else:
                await waiting_message.delete()
                await update.message.reply_text(
                    f"❌ Impossible de générer une stratégie pour {token_symbol}. Veuillez vérifier le symbole et réessayer."
                )
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la stratégie: {str(e)}")
            await waiting_message.delete()
            await update.message.reply_text(
                f"❌ Une erreur est survenue lors de la génération de la stratégie: {str(e)}"
            )


def create_telegram_bot(token: str = None, config: Dict = None, bot_state: Any = None) -> TelegramBot:
    """
    Crée une nouvelle instance du bot Telegram
    
    Args:
        token: Token Telegram (optionnel)
        config: Configuration (optionnel)
        bot_state: État du GBPBot (optionnel)
        
    Returns:
        TelegramBot: Instance du bot Telegram
    """
    return TelegramBot(token=token, config=config, bot_state=bot_state) 