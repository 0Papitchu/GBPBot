"""
Module des commandes de statut pour Telegram
===========================================

Ce module contient les commandes pour vérifier le statut du bot,
consulter les statistiques et les soldes des wallets.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import humanize
import json

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger("gbpbot.telegram.commands.status")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère la commande /status
    
    Affiche l'état actuel du GBPBot et des stratégies actives.
    
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
    
    # Obtenir l'état du bot depuis l'instance Telegram
    bot_state = bot.bot_state
    
    if not bot_state:
        # Mode de simulation si aucun état n'est disponible
        await update.message.reply_text(
            "📊 <b>Statut du GBPBot</b>\n\n"
            "<b>État général:</b> 🟢 En ligne\n"
            "<b>Mode:</b> Simulation (données démo)\n"
            "<b>Uptime:</b> 1h 23m\n\n"
            
            "<b>Stratégies actives:</b>\n"
            "- Arbitrage: 🟢 En cours\n"
            "- Sniping: 🔴 Arrêté\n"
            "- Auto Mode: 🔴 Arrêté\n\n"
            
            "<b>Dernière activité:</b> Scan d'arbitrage (il y a 2m)\n"
            "<b>CPU:</b> 23% | <b>RAM:</b> 456 MB\n\n"
            
            "<b>Actions:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🟢 Démarrer Sniping", callback_data="start_sniping"),
                    InlineKeyboardButton("🟢 Démarrer Auto", callback_data="start_auto_mode")
                ],
                [
                    InlineKeyboardButton("🔴 Arrêter Arbitrage", callback_data="stop_arbitrage")
                ],
                [
                    InlineKeyboardButton("📊 Statistiques", callback_data="view_stats"),
                    InlineKeyboardButton("💰 Soldes", callback_data="view_balance")
                ]
            ])
        )
        return
    
    # Obtenir les stratégies actives
    active_strategies = bot_state.get("active_strategies", [])
    
    # Construire le message de statut
    uptime = datetime.now() - bot_state.get("start_time", datetime.now())
    uptime_str = humanize.naturaldelta(uptime)
    
    status_message = (
        "📊 <b>Statut du GBPBot</b>\n\n"
        f"<b>État général:</b> 🟢 En ligne\n"
        f"<b>Mode:</b> {bot_state.get('mode', 'Normal')}\n"
        f"<b>Uptime:</b> {uptime_str}\n\n"
        
        "<b>Stratégies actives:</b>\n"
    )
    
    # Ajouter le statut de chaque stratégie
    strategies = {
        "arbitrage": "Arbitrage",
        "sniping": "Sniping",
        "auto_mode": "Auto Mode"
    }
    
    for strategy_id, strategy_name in strategies.items():
        is_active = strategy_id in active_strategies
        status_icon = "🟢" if is_active else "🔴"
        status_text = "En cours" if is_active else "Arrêté"
        status_message += f"- {strategy_name}: {status_icon} {status_text}\n"
    
    # Ajouter la dernière activité et les ressources
    last_activity = bot_state.get("last_activity", {})
    activity_name = last_activity.get("name", "Aucune")
    activity_time = last_activity.get("time", datetime.now())
    time_since = humanize.naturaltime(datetime.now() - activity_time)
    
    resources = bot_state.get("resources", {})
    cpu_usage = resources.get("cpu", 0)
    ram_usage = resources.get("ram", 0)
    
    status_message += (
        f"\n<b>Dernière activité:</b> {activity_name} ({time_since})\n"
        f"<b>CPU:</b> {cpu_usage}% | <b>RAM:</b> {ram_usage} MB\n\n"
        
        "<b>Actions:</b>"
    )
    
    # Créer les boutons d'action en fonction de l'état actuel
    buttons = []
    
    # Boutons pour démarrer les stratégies inactives
    start_buttons = []
    for strategy_id, strategy_name in strategies.items():
        if strategy_id not in active_strategies:
            start_buttons.append(
                InlineKeyboardButton(f"🟢 Démarrer {strategy_name}", callback_data=f"start_{strategy_id}")
            )
    
    # Boutons pour arrêter les stratégies actives
    stop_buttons = []
    for strategy_id, strategy_name in strategies.items():
        if strategy_id in active_strategies:
            stop_buttons.append(
                InlineKeyboardButton(f"🔴 Arrêter {strategy_name}", callback_data=f"stop_{strategy_id}")
            )
    
    # Ajouter les boutons de démarrage et d'arrêt
    if start_buttons:
        buttons.append(start_buttons[:2])  # Max 2 boutons par ligne
        if len(start_buttons) > 2:
            buttons.append(start_buttons[2:])
    
    if stop_buttons:
        buttons.append(stop_buttons[:2])
        if len(stop_buttons) > 2:
            buttons.append(stop_buttons[2:])
    
    # Ajouter les boutons de statistiques et de soldes
    buttons.append([
        InlineKeyboardButton("📊 Statistiques", callback_data="view_stats"),
        InlineKeyboardButton("💰 Soldes", callback_data="view_balance")
    ])
    
    await update.message.reply_text(
        status_message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère la commande /stats
    
    Affiche les statistiques de trading détaillées.
    
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
    
    # Obtenir l'état du bot depuis l'instance Telegram
    bot_state = bot.bot_state
    
    if not bot_state:
        # Mode de simulation
        await update.message.reply_text(
            "📈 <b>Statistiques de Trading</b> (Données Simulées)\n\n"
            "<b>Performance Globale</b>\n"
            "Total PnL: <b>+$1,245.78</b> (+12.4%)\n"
            "Trades: <b>78</b> (52 gagnants, 26 perdants)\n"
            "Taux de réussite: <b>66.7%</b>\n"
            "Profit moyen: <b>$15.97</b> par trade\n\n"
            
            "<b>Par Stratégie</b>\n"
            "Arbitrage: <b>+$523.45</b> (34 trades, 79% de réussite)\n"
            "Sniping: <b>+$722.33</b> (44 trades, 56% de réussite)\n\n"
            
            "<b>Meilleur Trade</b>\n"
            "Token: <b>PEPE</b>\n"
            "Profit: <b>+$215.60</b> (+32%)\n"
            "Date: <b>2023-06-15 14:23</b>\n\n"
            
            "<b>Pire Trade</b>\n"
            "Token: <b>WOJAK</b>\n"
            "Profit: <b>-$45.20</b> (-8%)\n"
            "Date: <b>2023-06-12 09:17</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔍 Détails Arbitrage", callback_data="stats_arbitrage"),
                    InlineKeyboardButton("🔍 Détails Sniping", callback_data="stats_sniping")
                ],
                [
                    InlineKeyboardButton("📅 Stats Journalières", callback_data="stats_daily"),
                    InlineKeyboardButton("⏱️ Stats Horaires", callback_data="stats_hourly")
                ]
            ])
        )
        return
    
    # Obtenir les statistiques réelles depuis l'état du bot
    stats = bot_state.get("stats", {})
    
    # Performance globale
    total_pnl = stats.get("total_pnl", 0)
    total_pnl_percentage = stats.get("total_pnl_percentage", 0)
    trades_count = stats.get("trades_count", 0)
    winning_trades = stats.get("winning_trades", 0)
    losing_trades = stats.get("losing_trades", 0)
    win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
    avg_profit = total_pnl / trades_count if trades_count > 0 else 0
    
    # Stats par stratégie
    strategy_stats = stats.get("strategies", {})
    
    # Meilleur et pire trade
    best_trade = stats.get("best_trade", {})
    worst_trade = stats.get("worst_trade", {})
    
    # Construire le message
    stats_message = (
        "📈 <b>Statistiques de Trading</b>\n\n"
        "<b>Performance Globale</b>\n"
        f"Total PnL: <b>${total_pnl:.2f}</b> ({total_pnl_percentage:+.1f}%)\n"
        f"Trades: <b>{trades_count}</b> ({winning_trades} gagnants, {losing_trades} perdants)\n"
        f"Taux de réussite: <b>{win_rate:.1f}%</b>\n"
        f"Profit moyen: <b>${avg_profit:.2f}</b> par trade\n\n"
        
        "<b>Par Stratégie</b>\n"
    )
    
    # Ajouter les stats par stratégie
    for strategy, strategy_data in strategy_stats.items():
        strategy_pnl = strategy_data.get("pnl", 0)
        strategy_trades = strategy_data.get("trades", 0)
        strategy_win_rate = strategy_data.get("win_rate", 0)
        
        stats_message += (
            f"{strategy.capitalize()}: <b>${strategy_pnl:.2f}</b> "
            f"({strategy_trades} trades, {strategy_win_rate:.0f}% de réussite)\n"
        )
    
    # Ajouter le meilleur et le pire trade
    if best_trade:
        stats_message += (
            "\n<b>Meilleur Trade</b>\n"
            f"Token: <b>{best_trade.get('token', 'N/A')}</b>\n"
            f"Profit: <b>${best_trade.get('profit', 0):.2f}</b> "
            f"({best_trade.get('percentage', 0):+.1f}%)\n"
            f"Date: <b>{best_trade.get('date', 'N/A')}</b>\n\n"
        )
    
    if worst_trade:
        stats_message += (
            "<b>Pire Trade</b>\n"
            f"Token: <b>{worst_trade.get('token', 'N/A')}</b>\n"
            f"Profit: <b>${worst_trade.get('profit', 0):.2f}</b> "
            f"({worst_trade.get('percentage', 0):+.1f}%)\n"
            f"Date: <b>{worst_trade.get('date', 'N/A')}</b>"
        )
    
    # Créer les boutons d'action
    buttons = [
        [
            InlineKeyboardButton("🔍 Détails Arbitrage", callback_data="stats_arbitrage"),
            InlineKeyboardButton("🔍 Détails Sniping", callback_data="stats_sniping")
        ],
        [
            InlineKeyboardButton("📅 Stats Journalières", callback_data="stats_daily"),
            InlineKeyboardButton("⏱️ Stats Horaires", callback_data="stats_hourly")
        ]
    ]
    
    await update.message.reply_text(
        stats_message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère la commande /balance
    
    Affiche les soldes des wallets.
    
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
    
    # Obtenir l'état du bot depuis l'instance Telegram
    bot_state = bot.bot_state
    
    if not bot_state:
        # Mode de simulation
        await update.message.reply_text(
            "💰 <b>Soldes des Wallets</b> (Données Simulées)\n\n"
            "<b>Solana Wallet</b>\n"
            "Adresse: <code>2Z5Pj...8xYh</code>\n"
            "SOL: <b>12.45</b> ($1,245)\n"
            "USDC: <b>2,500</b> ($2,500)\n"
            "Tokens: <b>5</b> autres tokens ($350)\n"
            "Total: <b>$4,095</b>\n\n"
            
            "<b>Avalanche Wallet</b>\n"
            "Adresse: <code>0x7F3...e9B2</code>\n"
            "AVAX: <b>25.75</b> ($750)\n"
            "USDC: <b>1,200</b> ($1,200)\n"
            "Tokens: <b>3</b> autres tokens ($180)\n"
            "Total: <b>$2,130</b>\n\n"
            
            "<b>Sonic Wallet</b>\n"
            "Adresse: <code>0x8A2...c4D7</code>\n"
            "SONIC: <b>450</b> ($675)\n"
            "USDC: <b>800</b> ($800)\n"
            "Tokens: <b>2</b> autres tokens ($120)\n"
            "Total: <b>$1,595</b>\n\n"
            
            "<b>Total Global:</b> <b>$7,820</b>",
            parse_mode="HTML"
        )
        return
    
    # Obtenir les données des wallets
    wallets = bot_state.get("wallets", {})
    
    # Construire le message
    balance_message = "💰 <b>Soldes des Wallets</b>\n\n"
    
    # Variable pour le total global
    total_global = 0
    
    # Ajouter les informations pour chaque wallet
    for blockchain, wallet_data in wallets.items():
        address = wallet_data.get("address", "N/A")
        balances = wallet_data.get("balances", {})
        
        # Calculer le total pour ce wallet
        wallet_total = 0
        for token, token_data in balances.items():
            amount = token_data.get("amount", 0)
            usd_value = token_data.get("usd_value", 0)
            wallet_total += usd_value
        
        # Obtenir les soldes natifs et stablecoins
        native_token = balances.get(blockchain.upper(), {})
        native_amount = native_token.get("amount", 0)
        native_usd = native_token.get("usd_value", 0)
        
        usdc = balances.get("USDC", {})
        usdc_amount = usdc.get("amount", 0)
        usdc_usd = usdc.get("usd_value", 0)
        
        # Compter les autres tokens
        other_tokens = {}
        for token, token_data in balances.items():
            if token != blockchain.upper() and token != "USDC":
                other_tokens[token] = token_data
        
        other_tokens_count = len(other_tokens)
        other_tokens_value = sum(token.get("usd_value", 0) for token in other_tokens.values())
        
        # Ajouter au message
        balance_message += (
            f"<b>{blockchain.capitalize()} Wallet</b>\n"
            f"Adresse: <code>{address[:4]}...{address[-4:]}</code>\n"
            f"{blockchain.upper()}: <b>{native_amount:.4f}</b> (${native_usd:.0f})\n"
            f"USDC: <b>{usdc_amount:.2f}</b> (${usdc_usd:.0f})\n"
            f"Tokens: <b>{other_tokens_count}</b> autres tokens (${other_tokens_value:.0f})\n"
            f"Total: <b>${wallet_total:.0f}</b>\n\n"
        )
        
        # Ajouter au total global
        total_global += wallet_total
    
    balance_message += f"<b>Total Global:</b> <b>${total_global:.0f}</b>"
    
    await update.message.reply_text(
        balance_message,
        parse_mode="HTML"
    )

async def profits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gère la commande /profits
    
    Affiche les profits détaillés avec un graphique.
    
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
    
    # Obtenir l'état du bot depuis l'instance Telegram
    bot_state = bot.bot_state
    
    if not bot_state:
        # Mode de simulation
        await update.message.reply_text(
            "📈 <b>Profits Détaillés</b> (Données Simulées)\n\n"
            "<b>Profits Par Période</b>\n"
            "Aujourd'hui: <b>+$145.78</b> (+1.9%)\n"
            "Cette semaine: <b>+$523.90</b> (+7.2%)\n"
            "Ce mois: <b>+$1,245.78</b> (+18.9%)\n"
            "Total: <b>+$1,245.78</b> (+18.9%)\n\n"
            
            "<b>Profits Par Stratégie</b>\n"
            "Arbitrage: <b>+$523.45</b> (42% du total)\n"
            "Sniping: <b>+$722.33</b> (58% du total)\n\n"
            
            "<b>Top 3 Tokens</b>\n"
            "1. PEPE: <b>+$215.60</b>\n"
            "2. FLOKI: <b>+$183.45</b>\n"
            "3. WOJAK: <b>+$125.78</b>\n\n"
            
            "<b>Derniers Profits</b>\n"
            "• PEPE: <b>+$25.45</b> (12m ago)\n"
            "• DOGE: <b>+$18.90</b> (34m ago)\n"
            "• SOL/AVAX arbitrage: <b>+$12.34</b> (1h ago)",
            parse_mode="HTML"
        )
        return
    
    # Obtenir les données de profits
    profits = bot_state.get("profits", {})
    
    # Profits par période
    periods = profits.get("periods", {})
    daily_profit = periods.get("daily", 0)
    daily_percentage = periods.get("daily_percentage", 0)
    weekly_profit = periods.get("weekly", 0)
    weekly_percentage = periods.get("weekly_percentage", 0)
    monthly_profit = periods.get("monthly", 0)
    monthly_percentage = periods.get("monthly_percentage", 0)
    total_profit = periods.get("total", 0)
    total_percentage = periods.get("total_percentage", 0)
    
    # Profits par stratégie
    strategy_profits = profits.get("strategies", {})
    
    # Top tokens
    top_tokens = profits.get("top_tokens", [])
    
    # Derniers profits
    recent_profits = profits.get("recent", [])
    
    # Construire le message
    profits_message = (
        "📈 <b>Profits Détaillés</b>\n\n"
        "<b>Profits Par Période</b>\n"
        f"Aujourd'hui: <b>${daily_profit:+.2f}</b> ({daily_percentage:+.1f}%)\n"
        f"Cette semaine: <b>${weekly_profit:+.2f}</b> ({weekly_percentage:+.1f}%)\n"
        f"Ce mois: <b>${monthly_profit:+.2f}</b> ({monthly_percentage:+.1f}%)\n"
        f"Total: <b>${total_profit:+.2f}</b> ({total_percentage:+.1f}%)\n\n"
        
        "<b>Profits Par Stratégie</b>\n"
    )
    
    # Ajouter les profits par stratégie
    for strategy, strategy_data in strategy_profits.items():
        profit = strategy_data.get("profit", 0)
        percentage = strategy_data.get("percentage", 0)
        
        profits_message += (
            f"{strategy.capitalize()}: <b>${profit:+.2f}</b> ({percentage:.0f}% du total)\n"
        )
    
    # Ajouter les top tokens
    if top_tokens:
        profits_message += "\n<b>Top 3 Tokens</b>\n"
        
        for i, token in enumerate(top_tokens[:3], 1):
            token_name = token.get("name", "N/A")
            token_profit = token.get("profit", 0)
            
            profits_message += f"{i}. {token_name}: <b>${token_profit:+.2f}</b>\n"
    
    # Ajouter les profits récents
    if recent_profits:
        profits_message += "\n<b>Derniers Profits</b>\n"
        
        for profit in recent_profits[:3]:
            name = profit.get("name", "N/A")
            amount = profit.get("amount", 0)
            time = profit.get("time", datetime.now())
            time_ago = humanize.naturaltime(datetime.now() - time)
            
            profits_message += f"• {name}: <b>${amount:+.2f}</b> ({time_ago})\n"
    
    await update.message.reply_text(
        profits_message,
        parse_mode="HTML"
    ) 