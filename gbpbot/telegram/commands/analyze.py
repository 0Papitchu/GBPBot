"""
Module de commandes d'analyse pour le bot Telegram
==================================================

Ce module implémente les commandes pour l'analyse du marché et des tokens spécifiques
via l'interface Telegram du GBPBot.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import traceback
from datetime import datetime
import json

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext, CommandHandler, CallbackQueryHandler

# Logger
logger = logging.getLogger("gbpbot.telegram.commands.analyze")

# Importation conditionnelle des modules d'IA et d'analyse
try:
    from gbpbot.ai import create_market_intelligence, get_prompt_manager
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    MARKET_ANALYZER_AVAILABLE = True
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False
    logger.warning("Module MarketAnalyzer non disponible")

try:
    from gbpbot.ai.token_analyzer import TokenAnalyzer
    TOKEN_ANALYZER_AVAILABLE = True
except ImportError:
    TOKEN_ANALYZER_AVAILABLE = False
    logger.warning("Module TokenAnalyzer non disponible")

# Commande /analyze_market - Analyse le marché crypto actuel
async def analyze_market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Analyse le marché crypto actuel et fournit des insights.
    Usage: /analyze_market [options]
    Options: --detailed, --focus=solana, --time=24h
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Vérifier si le module d'analyse est disponible
    if not MARKET_ANALYZER_AVAILABLE:
        await update.message.reply_text(
            "❌ <b>Module d'analyse de marché non disponible</b>\n\n"
            "Cette fonctionnalité nécessite l'installation du module MarketAnalyzer.",
            parse_mode="HTML"
        )
        return
    
    # Message de processing
    processing_message = await update.message.reply_text(
        "🔍 <b>Analyse du marché en cours...</b>\n\n"
        "Veuillez patienter pendant que j'analyse les tendances actuelles du marché.",
        parse_mode="HTML"
    )
    
    # Extraire les options
    options = {}
    detailed = False
    focus = "global"
    time_period = "24h"
    
    if context.args:
        for arg in context.args:
            if arg == "--detailed":
                detailed = True
                options["detailed"] = True
            elif arg.startswith("--focus="):
                focus = arg.split("=")[1].lower()
                options["focus"] = focus
            elif arg.startswith("--time="):
                time_period = arg.split("=")[1].lower()
                options["time_period"] = time_period
    
    try:
        # Créer le module d'analyse de marché
        market_analyzer = MarketAnalyzer(context.bot_data.get('bot_state', {}))
        
        # Exécuter l'analyse
        result = await market_analyzer.analyze_market(
            focus=focus,
            time_period=time_period,
            detailed=detailed
        )
        
        # Formater la réponse
        if result and "analysis" in result:
            analysis = result["analysis"]
            market_trend = result.get("market_trend", "neutral")
            
            # Emoji pour la tendance
            trend_emoji = "🟢" if market_trend == "bullish" else "🔴" if market_trend == "bearish" else "⚪"
            
            # Construire le message
            message = f"{trend_emoji} <b>Analyse du Marché Crypto</b>\n\n"
            
            # Informations principales
            message += f"<b>Tendance:</b> {market_trend.title()}\n"
            message += f"<b>Focus:</b> {focus.title()}\n"
            message += f"<b>Période:</b> {time_period}\n\n"
            
            # Analyse détaillée
            message += f"<b>Analyse:</b>\n{analysis}\n\n"
            
            # Opportunités détectées
            if "opportunities" in result and result["opportunities"]:
                message += "<b>Opportunités Détectées:</b>\n"
                for opp in result["opportunities"]:
                    message += f"• {opp['name']} ({opp['symbol']}): {opp['reason']}\n"
            
            # Risques détectés
            if "risks" in result and result["risks"]:
                message += "\n<b>Risques Détectés:</b>\n"
                for risk in result["risks"]:
                    message += f"• {risk['description']}\n"
            
            # Source des données
            message += f"\n<i>Analyse générée le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</i>"
            
            # Boutons pour actions supplémentaires
            keyboard = [
                [InlineKeyboardButton("📊 Vue Détaillée", callback_data=f"analyze_market_detailed_{focus}_{time_period}")],
                [InlineKeyboardButton("💰 Opportunités d'Arbitrage", callback_data="analyze_arbitrage")],
                [InlineKeyboardButton("🚀 Tokens Prometteurs", callback_data="analyze_promising_tokens")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Envoyer la réponse et supprimer le message de processing
            await processing_message.delete()
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await processing_message.delete()
            await update.message.reply_text(
                "❌ <b>Erreur lors de l'analyse du marché</b>\n\n"
                "Aucun résultat d'analyse n'a été obtenu. Veuillez réessayer plus tard.",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du marché: {str(e)}")
        traceback.print_exc()
        await processing_message.delete()
        await update.message.reply_text(
            f"❌ <b>Erreur lors de l'analyse du marché</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Commande /analyze_token - Analyse un token spécifique
async def analyze_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Analyse un token spécifique et fournit des insights.
    Usage: /analyze_token <token_symbol_ou_adresse> [options]
    Options: --detailed, --risk, --chain=solana
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Vérifier si le module d'analyse est disponible
    if not TOKEN_ANALYZER_AVAILABLE:
        await update.message.reply_text(
            "❌ <b>Module d'analyse de token non disponible</b>\n\n"
            "Cette fonctionnalité nécessite l'installation du module TokenAnalyzer.",
            parse_mode="HTML"
        )
        return
    
    # Vérifier si un token a été spécifié
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "ℹ️ <b>Token non spécifié</b>\n\n"
            "Usage: <code>/analyze_token &lt;token_symbol_ou_adresse&gt;</code>\n\n"
            "Exemples:\n"
            "• <code>/analyze_token SOL</code>\n"
            "• <code>/analyze_token 0x1234...abcd</code>\n"
            "• <code>/analyze_token SOL --detailed --chain=solana</code>",
            parse_mode="HTML"
        )
        return
    
    # Extraire le token et les options
    token_identifier = context.args[0]
    options = {}
    detailed = False
    risk_analysis = False
    chain = "solana"  # Par défaut
    
    if len(context.args) > 1:
        for arg in context.args[1:]:
            if arg == "--detailed":
                detailed = True
                options["detailed"] = True
            elif arg == "--risk":
                risk_analysis = True
                options["risk_analysis"] = True
            elif arg.startswith("--chain="):
                chain = arg.split("=")[1].lower()
                options["chain"] = chain
    
    # Message de processing
    processing_message = await update.message.reply_text(
        f"🔍 <b>Analyse du token {token_identifier} en cours...</b>\n\n"
        f"Veuillez patienter pendant que j'analyse ce token sur {chain.title()}.",
        parse_mode="HTML"
    )
    
    try:
        # Créer le module d'analyse de token
        token_analyzer = TokenAnalyzer(context.bot_data.get('bot_state', {}))
        
        # Exécuter l'analyse
        result = await token_analyzer.analyze_token(
            token_identifier,
            chain=chain,
            detailed=detailed,
            risk_analysis=risk_analysis
        )
        
        # Formater la réponse
        if result and "token_info" in result:
            token_info = result["token_info"]
            risk_score = result.get("risk_score", 0)
            
            # Determiner l'emoji de risque
            risk_emoji = "🟢" if risk_score < 30 else "🟠" if risk_score < 70 else "🔴"
            
            # Construire le message
            message = f"🪙 <b>Analyse du Token: {token_info.get('name', token_identifier)}</b>\n\n"
            
            # Informations principales
            message += f"<b>Symbole:</b> {token_info.get('symbol', 'N/A')}\n"
            message += f"<b>Blockchain:</b> {chain.title()}\n"
            if "address" in token_info:
                address = token_info["address"]
                # Tronquer l'adresse si elle est trop longue
                if len(address) > 16:
                    address = f"{address[:8]}...{address[-8:]}"
                message += f"<b>Adresse:</b> <code>{address}</code>\n"
            message += f"<b>Prix:</b> {token_info.get('price', 'N/A')} USD\n"
            
            # Variation de prix
            if "price_change_24h" in token_info:
                change_24h = token_info["price_change_24h"]
                change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                message += f"<b>Variation 24h:</b> {change_emoji} {change_24h:.2f}%\n"
            
            # Capitalisation et liquidité
            if "market_cap" in token_info:
                message += f"<b>Capitalisation:</b> {token_info['market_cap']:,} USD\n"
            if "liquidity" in token_info:
                message += f"<b>Liquidité:</b> {token_info['liquidity']:,} USD\n"
            
            # Risque
            message += f"\n{risk_emoji} <b>Score de Risque:</b> {risk_score}/100\n"
            
            # Analyse détaillée
            if "analysis" in result:
                message += f"\n<b>Analyse:</b>\n{result['analysis']}\n"
            
            # Indicateurs techniques
            if "technical_indicators" in result and result["technical_indicators"]:
                message += "\n<b>Indicateurs Techniques:</b>\n"
                indicators = result["technical_indicators"]
                message += f"• RSI: {indicators.get('rsi', 'N/A')}\n"
                message += f"• MACD: {indicators.get('macd', 'N/A')}\n"
                message += f"• Tendance: {indicators.get('trend', 'N/A')}\n"
            
            # Risques spécifiques
            if risk_analysis and "risks" in result and result["risks"]:
                message += "\n<b>Risques Détectés:</b>\n"
                for risk in result["risks"]:
                    message += f"• {risk['description']} ({risk['severity']})\n"
            
            # Recommandation
            if "recommendation" in result:
                message += f"\n<b>Recommandation:</b> {result['recommendation']}\n"
            
            # Source des données
            message += f"\n<i>Analyse générée le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</i>"
            
            # Boutons pour actions supplémentaires
            keyboard = [
                [InlineKeyboardButton("📊 Graphique", callback_data=f"token_chart_{token_info.get('symbol', token_identifier)}_{chain}")],
                [InlineKeyboardButton("🔍 Analyse des Risques", callback_data=f"token_risk_{token_info.get('symbol', token_identifier)}_{chain}")],
                [InlineKeyboardButton("💰 Opportunités", callback_data=f"token_opportunities_{token_info.get('symbol', token_identifier)}_{chain}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Envoyer la réponse et supprimer le message de processing
            await processing_message.delete()
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await processing_message.delete()
            await update.message.reply_text(
                f"❌ <b>Erreur lors de l'analyse du token {token_identifier}</b>\n\n"
                "Aucune information n'a été trouvée pour ce token. Vérifiez l'identifiant ou l'adresse du token.",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du token: {str(e)}")
        traceback.print_exc()
        await processing_message.delete()
        await update.message.reply_text(
            f"❌ <b>Erreur lors de l'analyse du token {token_identifier}</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Commande /list_trending - Liste les tokens en tendance
async def list_trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Liste les tokens en tendance actuellement.
    Usage: /list_trending [options]
    Options: --chain=solana, --limit=10
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Vérifier l'autorisation
    if hasattr(context.bot_data.get('bot'), '_is_user_authorized'):
        if not context.bot_data.get('bot')._is_user_authorized(user.id):
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    
    # Vérifier si le module d'analyse est disponible
    if not MARKET_ANALYZER_AVAILABLE:
        await update.message.reply_text(
            "❌ <b>Module d'analyse de marché non disponible</b>\n\n"
            "Cette fonctionnalité nécessite l'installation du module MarketAnalyzer.",
            parse_mode="HTML"
        )
        return
    
    # Extraire les options
    chain = "all"
    limit = 10
    
    if context.args:
        for arg in context.args:
            if arg.startswith("--chain="):
                chain = arg.split("=")[1].lower()
            elif arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=")[1])
                    limit = max(1, min(limit, 20))  # Limiter entre 1 et 20
                except ValueError:
                    pass
    
    # Message de processing
    processing_message = await update.message.reply_text(
        f"🔍 <b>Recherche des tokens en tendance...</b>\n\n"
        f"Veuillez patienter pendant que je recherche les {limit} tokens les plus en tendance"
        f"{' sur ' + chain.title() if chain != 'all' else ''}.",
        parse_mode="HTML"
    )
    
    try:
        # Créer le module d'analyse de marché
        market_analyzer = MarketAnalyzer(context.bot_data.get('bot_state', {}))
        
        # Récupérer les tokens en tendance
        trending_tokens = await market_analyzer.get_trending_tokens(chain=chain, limit=limit)
        
        if trending_tokens and len(trending_tokens) > 0:
            # Construire le message
            message = f"🔥 <b>Top {len(trending_tokens)} Tokens en Tendance</b>"
            message += f"{' sur ' + chain.title() if chain != 'all' else ''}\n\n"
            
            # Lister les tokens
            for i, token in enumerate(trending_tokens, 1):
                price_change = token.get("price_change_24h", 0)
                change_emoji = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"
                volume = token.get("volume_24h", 0)
                
                message += (
                    f"{i}. <b>{token.get('name', 'Inconnu')}</b> ({token.get('symbol', 'N/A')})\n"
                    f"   💲 Prix: {token.get('price', 'N/A')} USD\n"
                    f"   {change_emoji} 24h: {price_change:+.2f}%\n"
                    f"   💰 Volume: {volume:,.0f} USD\n"
                )
                
                # Ajouter un séparateur entre les tokens sauf pour le dernier
                if i < len(trending_tokens):
                    message += "\n"
            
            # Source des données
            message += f"\n<i>Données actualisées le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</i>"
            
            # Boutons pour actions supplémentaires
            keyboard = []
            chains = ["all", "solana", "avax", "sonic"]
            chain_buttons = []
            
            for c in chains:
                if c != chain:  # Ne pas afficher la chaîne actuelle
                    emoji = "🔄" if c == "all" else "⚡" if c == "solana" else "🔺" if c == "avax" else "🔊"
                    chain_buttons.append(InlineKeyboardButton(f"{emoji} {c.title()}", callback_data=f"trending_tokens_{c}_{limit}"))
            
            # Diviser les boutons en rangées de 3 maximum
            for i in range(0, len(chain_buttons), 3):
                keyboard.append(chain_buttons[i:i+3])
            
            # Ajouter un bouton pour analyser un token spécifique
            keyboard.append([InlineKeyboardButton("🔍 Analyser un token...", callback_data="analyze_token_prompt")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Envoyer la réponse et supprimer le message de processing
            await processing_message.delete()
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await processing_message.delete()
            await update.message.reply_text(
                "❌ <b>Aucun token en tendance trouvé</b>\n\n"
                "Aucune information n'a pu être récupérée. Veuillez réessayer plus tard ou vérifier vos paramètres.",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tokens en tendance: {str(e)}")
        traceback.print_exc()
        await processing_message.delete()
        await update.message.reply_text(
            "❌ <b>Erreur lors de la récupération des tokens en tendance</b>\n\n"
            f"Détails: {str(e)}",
            parse_mode="HTML"
        )

# Gestionnaire pour les callbacks liés aux analyses
async def analyze_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère les callbacks des boutons liés aux analyses.
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
    
    if callback_data.startswith("analyze_market_detailed_"):
        # Format: analyze_market_detailed_<focus>_<time_period>
        parts = callback_data.split("_")
        if len(parts) >= 4:
            focus = parts[3]
            time_period = parts[4] if len(parts) > 4 else "24h"
            
            # Message de processing
            await query.edit_message_text(
                "🔍 <b>Génération de l'analyse détaillée en cours...</b>\n\n"
                "Veuillez patienter pendant que je prépare une analyse approfondie.",
                parse_mode="HTML"
            )
            
            try:
                # Créer le module d'analyse de marché avec l'option détaillée
                market_analyzer = MarketAnalyzer(context.bot_data.get('bot_state', {}))
                result = await market_analyzer.analyze_market(
                    focus=focus,
                    time_period=time_period,
                    detailed=True
                )
                
                if result and "analysis" in result:
                    # Formater la réponse détaillée
                    # (code de formatage similaire à la commande de base, mais avec plus de détails)
                    detailed_analysis = result.get("detailed_analysis", result["analysis"])
                    
                    message = f"📊 <b>Analyse Détaillée du Marché ({focus.title()})</b>\n\n"
                    message += f"{detailed_analysis}\n\n"
                    
                    # Ajouter des statistiques supplémentaires
                    if "stats" in result:
                        stats = result["stats"]
                        message += "<b>Statistiques de Marché:</b>\n"
                        for key, value in stats.items():
                            message += f"• {key}: {value}\n"
                    
                    # Ajouter plus d'informations sur les opportunités et risques
                    # (code similaire à la commande de base, mais avec plus de détails)
                    
                    # Bouton pour revenir à l'analyse normale
                    keyboard = [[InlineKeyboardButton("◀️ Retour", callback_data=f"analyze_market_basic_{focus}_{time_period}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await query.edit_message_text(
                        "❌ <b>Erreur lors de l'analyse détaillée du marché</b>\n\n"
                        "Aucun résultat d'analyse n'a été obtenu. Veuillez réessayer plus tard.",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse détaillée du marché: {str(e)}")
                traceback.print_exc()
                await query.edit_message_text(
                    "❌ <b>Erreur lors de l'analyse détaillée du marché</b>\n\n"
                    f"Détails: {str(e)}",
                    parse_mode="HTML"
                )
    
    elif callback_data.startswith("analyze_token_prompt"):
        # Demander à l'utilisateur de spécifier un token à analyser
        message = (
            "🔍 <b>Analyse de Token</b>\n\n"
            "Pour analyser un token, utilisez la commande:\n"
            "<code>/analyze_token &lt;symbole_ou_adresse&gt;</code>\n\n"
            "Exemples:\n"
            "• <code>/analyze_token SOL</code>\n"
            "• <code>/analyze_token 0x1234...abcd</code>\n"
            "• <code>/analyze_token SOL --detailed --chain=solana</code>"
        )
        await query.edit_message_text(message, parse_mode="HTML")
    
    elif callback_data.startswith("token_chart_"):
        # Format: token_chart_<symbol>_<chain>
        parts = callback_data.split("_")
        if len(parts) >= 3:
            symbol = parts[2]
            chain = parts[3] if len(parts) > 3 else "solana"
            
            # Message de processing
            await query.edit_message_text(
                f"📊 <b>Génération du graphique pour {symbol}...</b>\n\n"
                "Veuillez patienter pendant que je prépare le graphique.",
                parse_mode="HTML"
            )
            
            try:
                # Cette fonctionnalité nécessiterait d'envoyer une image de graphique
                # Comme Telegram ne peut pas afficher d'images directement dans les messages édités,
                # On pourrait soit envoyer un nouveau message avec l'image, soit rediriger vers un graphique en ligne
                
                # Pour l'instant, simulons cette fonctionnalité avec un message d'information
                message = (
                    f"📊 <b>Graphique pour {symbol}</b>\n\n"
                    f"Le graphique pour {symbol} sur {chain.title()} serait affiché ici.\n\n"
                    f"Pour voir le graphique en ligne, vous pouvez visiter:\n"
                )
                
                # Liens vers des graphiques selon la blockchain
                if chain.lower() == "solana":
                    message += f"• <a href='https://dexscreener.com/solana/{symbol.lower()}'>DexScreener</a>\n"
                    message += f"• <a href='https://birdeye.so/token/{symbol.lower()}?chain=solana'>Birdeye</a>"
                elif chain.lower() == "avax":
                    message += f"• <a href='https://dexscreener.com/avalanche/{symbol.lower()}'>DexScreener</a>\n"
                    message += f"• <a href='https://traderjoe.xyz/avalanche/trade/v2/{symbol.lower()}'>TraderJoe</a>"
                else:
                    message += f"• <a href='https://dexscreener.com/search/{symbol.lower()}'>DexScreener</a>\n"
                
                # Bouton pour revenir à l'analyse du token
                keyboard = [[InlineKeyboardButton("◀️ Retour à l'analyse", callback_data=f"analyze_token_{symbol}_{chain}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Erreur lors de la génération du graphique: {str(e)}")
                traceback.print_exc()
                await query.edit_message_text(
                    f"❌ <b>Erreur lors de la génération du graphique pour {symbol}</b>\n\n"
                    f"Détails: {str(e)}",
                    parse_mode="HTML"
                )
    
    elif callback_data.startswith("trending_tokens_"):
        # Format: trending_tokens_<chain>_<limit>
        parts = callback_data.split("_")
        if len(parts) >= 3:
            chain = parts[2]
            limit = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 10
            
            # Message de processing
            await query.edit_message_text(
                f"🔍 <b>Recherche des tokens en tendance...</b>\n\n"
                f"Veuillez patienter pendant que je recherche les {limit} tokens les plus en tendance"
                f"{' sur ' + chain.title() if chain != 'all' else ''}.",
                parse_mode="HTML"
            )
            
            try:
                # Créer le module d'analyse de marché
                market_analyzer = MarketAnalyzer(context.bot_data.get('bot_state', {}))
                
                # Récupérer les tokens en tendance
                trending_tokens = await market_analyzer.get_trending_tokens(chain=chain, limit=limit)
                
                # Le reste du code est similaire à la commande list_trending_command
                # (formater la réponse, ajouter les boutons, etc.)
                
                # Pour éviter les duplications, on pourrait extraire ce code dans une fonction séparée
                # qui serait utilisée à la fois par la commande et par le callback
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des tokens en tendance: {str(e)}")
                traceback.print_exc()
                await query.edit_message_text(
                    "❌ <b>Erreur lors de la récupération des tokens en tendance</b>\n\n"
                    f"Détails: {str(e)}",
                    parse_mode="HTML"
                )

# Fonction pour enregistrer les gestionnaires de commandes
def register_analyze_command_handlers(application):
    """
    Enregistre les gestionnaires de commandes liées aux analyses.
    """
    application.add_handler(CommandHandler("analyze_market", analyze_market_command))
    application.add_handler(CommandHandler("analyze_token", analyze_token_command))
    application.add_handler(CommandHandler("list_trending", list_trending_command))
    
    # Gestionnaire pour les callbacks des boutons
    application.add_handler(CallbackQueryHandler(
        analyze_button_callback, 
        pattern="^(analyze_market_|token_chart_|token_risk_|token_opportunities_|analyze_token_|trending_tokens_)"
    )) 