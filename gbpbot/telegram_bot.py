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
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext
    TELEGRAM_IMPORTS_OK = True
except ImportError:
    TELEGRAM_IMPORTS_OK = False
    print("Telegram modules not available. Run 'pip install python-telegram-bot'")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gbpbot.telegram_bot")

# Import conditionnel des modules d'IA
try:
    from gbpbot.ai import create_ai_client, get_prompt_manager
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    AI_IMPORTS_OK = True
except ImportError:
    AI_IMPORTS_OK = False
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
    
    def __init__(self, token: str = None, config: Dict = None, bot_state: Any = None):
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
        
        # Initialisation de l'analyseur IA si disponible
        self.ai_market_analyzer = None
        self._initialize_ai()
        
        logger.info("Bot Telegram initialisé")
    
    def _initialize_ai(self) -> None:
        """Initialise les fonctionnalités d'IA pour le bot Telegram"""
        if not AI_IMPORTS_OK:
            logger.warning("Les fonctionnalités d'IA ne sont pas disponibles pour le bot Telegram")
            return
            
        try:
            # Créer un client d'IA
            ai_provider = self.config.get("ai_provider", os.environ.get("AI_PROVIDER", "auto"))
            ai_client = create_ai_client(provider=ai_provider)
            
            if ai_client is None:
                logger.warning("Impossible de créer le client d'IA pour le bot Telegram")
                return
                
            # Créer le gestionnaire de prompts
            prompt_manager = get_prompt_manager()
            
            # Créer l'analyseur de marché
            self.ai_market_analyzer = MarketAnalyzer(ai_client, prompt_manager)
            logger.info("Analyseur de marché IA initialisé avec succès pour le bot Telegram")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'IA pour le bot Telegram: {str(e)}")
            self.ai_market_analyzer = None
    
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
            
        if not TELEGRAM_IMPORTS_OK or not self.token:
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
            
            # Ajouter le gestionnaire de callbacks pour les boutons inline
            self.application.add_handler(CallbackQueryHandler(self._button_callback))
            
            # Démarrer le bot dans un thread séparé pour ne pas bloquer
            threading.Thread(target=self._run_bot, daemon=True).start()
            
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
        """Affiche l'aide du bot"""
        user_id = update.effective_user.id
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        help_text = """
<b>🤖 GBPBot - Commandes disponibles</b>

<b>Commandes de base:</b>
/start - Démarrer le bot Telegram
/help - Afficher ce message d'aide
/status - Vérifier l'état du GBPBot
/modules - Gérer les modules actifs

<b>Contrôle du GBPBot:</b>
/start_bot - Démarrer les modules du GBPBot
/stop_bot - Arrêter les modules du GBPBot

<b>Statistiques et performance:</b>
/stats - Afficher les statistiques de trading
/profits - Montrer les profits réalisés

<b>Analyse IA:</b>
/analyze_market - Analyser les conditions actuelles du marché
/analyze_token [symbole] - Analyser un token spécifique
/predict [symbole] [durée] - Prédire le mouvement de prix
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
        """Gestionnaire pour les callbacks des boutons inline"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not self._is_user_authorized(user_id):
            await query.edit_message_text("❌ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
        
        callback_data = query.data
        
        if callback_data == "back_to_main":
            # Retour au menu principal
            await query.edit_message_text(
                "🏠 <b>Menu Principal</b>\n\n"
                "Utilisez /help pour voir les commandes disponibles.",
                parse_mode="HTML"
            )
            return
        
        if callback_data.startswith("toggle_module:"):
            # Activer/désactiver un module
            _, module_name = callback_data.split(":", 1)
            
            if not self.bot_state:
                await query.edit_message_text("❌ Impossible de récupérer l'état du bot.")
                return
                
            if not self.bot_state.running:
                await query.edit_message_text("❌ Le bot doit être démarré pour gérer les modules.")
                return
                
            # Inverser l'état du module
            current_state = self.bot_state.active_modules.get(module_name, False)
            
            try:
                if current_state:
                    # Désactiver le module
                    # Idéalement, nous appellerions une fonction asynchrone pour arrêter le module
                    # mais cela dépend de l'implémentation du GBPBot
                    self.bot_state.active_modules[module_name] = False
                    await query.edit_message_text(f"✅ Module {module_name} désactivé avec succès.")
                else:
                    # Activer le module
                    # Idéalement, nous appellerions une fonction asynchrone pour démarrer le module
                    # mais cela dépend de l'implémentation du GBPBot
                    self.bot_state.active_modules[module_name] = True
                    await query.edit_message_text(f"✅ Module {module_name} activé avec succès.")
                    
                # Recréer le menu des modules après un court délai
                await asyncio.sleep(1)
                await self._command_modules(update, context)
                
            except Exception as e:
                await query.edit_message_text(f"❌ Erreur lors de la gestion du module: {str(e)}")
    
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
        """Analyse les conditions actuelles du marché avec l'IA"""
        user_id = update.effective_user.id
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not AI_IMPORTS_OK or not self.ai_market_analyzer:
            await update.message.reply_text("❌ Les fonctionnalités d'IA ne sont pas disponibles.")
            return
            
        waiting_message = await update.message.reply_text("⏳ Analyse du marché en cours, veuillez patienter...")
        
        try:
            # Récupérer les données du marché (en situation réelle, on utiliserait des données live)
            # Ici nous utilisons des données simulées pour la démonstration
            market_data = self._get_simulated_market_data()
            
            # Analyser les données du marché
            analysis = self.ai_market_analyzer.analyze_market_data(market_data)
            
            # Formater et envoyer la réponse
            response = f"""
<b>📊 Analyse du Marché</b>

<b>Tendance:</b> {analysis.get('trend', 'Inconnue')}
<b>Confiance:</b> {analysis.get('confidence', 0) * 100:.1f}%
<b>Sentiment:</b> {analysis.get('market_sentiment', 'Neutre')}

<b>Indicateurs clés:</b>
{self._format_indicators(analysis.get('key_indicators', []))}

<b>Prédiction:</b> {analysis.get('prediction', 'Aucune prédiction disponible')}

<b>Recommandation:</b> {analysis.get('recommendation', 'Aucune recommandation disponible')}

<b>Niveau de risque:</b> {analysis.get('risk_level', 'Inconnu')}

<i>Analyse générée par IA le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}</i>
"""
            await waiting_message.edit_text(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {str(e)}")
            await waiting_message.edit_text(f"❌ Erreur lors de l'analyse du marché: {str(e)}")
    
    async def _command_analyze_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Analyse un token spécifique avec l'IA"""
        user_id = update.effective_user.id
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not AI_IMPORTS_OK or not self.ai_market_analyzer:
            await update.message.reply_text("❌ Les fonctionnalités d'IA ne sont pas disponibles.")
            return
            
        # Vérifier si un symbole a été fourni
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("⚠️ Veuillez spécifier un symbole de token. Exemple: /analyze_token SOL")
            return
            
        symbol = context.args[0].upper()
        waiting_message = await update.message.reply_text(f"⏳ Analyse du token {symbol} en cours, veuillez patienter...")
        
        try:
            # Récupérer les données du token (en situation réelle, on utiliserait des données live)
            # Ici nous utilisons des données simulées pour la démonstration
            token_data = self._get_simulated_token_data(symbol)
            
            # Évaluer le score du token
            token_score = self.ai_market_analyzer.evaluate_token_score({"token": token_data})
            
            # Analyser les patterns pour ce token
            pattern_analysis = self.ai_market_analyzer.detect_pattern(token_data)
            
            # Formater et envoyer la réponse
            response = f"""
<b>🧐 Analyse du Token {symbol}</b>

<b>Score AI:</b> {token_score:.2f}/1.00
<b>Tendance détectée:</b> {pattern_analysis.get('pattern_type', 'Aucun pattern clair')}
<b>Probabilité:</b> {pattern_analysis.get('confidence', 0) * 100:.1f}%

<b>Points forts:</b>
{self._format_bullet_points(pattern_analysis.get('strengths', []))}

<b>Points faibles:</b>
{self._format_bullet_points(pattern_analysis.get('weaknesses', []))}

<b>Recommendation:</b> {pattern_analysis.get('recommendation', 'Aucune recommandation disponible')}

<i>Analyse générée par IA le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}</i>
"""
            await waiting_message.edit_text(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du token {symbol}: {str(e)}")
            await waiting_message.edit_text(f"❌ Erreur lors de l'analyse du token {symbol}: {str(e)}")
    
    async def _command_predict(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prédit le mouvement de prix d'un token sur une période donnée"""
        user_id = update.effective_user.id
        if not self._is_user_authorized(user_id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser ce bot.")
            return
            
        if not AI_IMPORTS_OK or not self.ai_market_analyzer:
            await update.message.reply_text("❌ Les fonctionnalités d'IA ne sont pas disponibles.")
            return
            
        # Vérifier si les arguments nécessaires sont fournis
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("⚠️ Usage: /predict [symbole] [heures=24]")
            return
            
        symbol = context.args[0].upper()
        timeframe_hours = 24  # Par défaut
        
        # Si une durée est spécifiée
        if len(context.args) >= 2:
            try:
                timeframe_hours = int(context.args[1])
            except ValueError:
                await update.message.reply_text("⚠️ La durée doit être un nombre entier d'heures.")
                return
        
        waiting_message = await update.message.reply_text(
            f"⏳ Prédiction pour {symbol} sur {timeframe_hours}h en cours..."
        )
        
        try:
            # Récupérer les données du token (simulation)
            token_data = self._get_simulated_token_data(symbol)
            
            # Prédire le mouvement de prix
            prediction = self.ai_market_analyzer.predict_price_movement(token_data, timeframe_hours)
            
            # Calculer l'emoji en fonction de la prédiction
            if prediction.get('predicted_direction', '') == 'up':
                direction_emoji = '🟢 HAUSSE'
            elif prediction.get('predicted_direction', '') == 'down':
                direction_emoji = '🔴 BAISSE'
            else:
                direction_emoji = '⚪ STABLE'
            
            # Formater et envoyer la réponse
            response = f"""
<b>🔮 Prédiction pour {symbol} ({timeframe_hours}h)</b>

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
            await waiting_message.edit_text(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction pour {symbol}: {str(e)}")
            await waiting_message.edit_text(f"❌ Erreur lors de la prédiction pour {symbol}: {str(e)}")
    
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