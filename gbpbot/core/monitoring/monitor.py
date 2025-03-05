#!/usr/bin/env python3
"""
Module de monitoring pour GBPBot.
Gère les métriques, les alertes et le logging.
"""

import time
from typing import Dict, List, Optional
from decimal import Decimal
import asyncio
from prometheus_client import start_http_server, Counter, Gauge, Histogram
from loguru import logger
import aiohttp
from datetime import datetime, timedelta

class BotMonitor:
    """Gestionnaire de monitoring du bot."""

    def __init__(self, config: Dict):
        """
        Initialise le système de monitoring.
        
        Args:
            config: Configuration du monitoring
        """
        self.config = config
        self.start_time = time.time()
        
        # Initialisation des métriques Prometheus
        self._init_metrics()
        
        # État du bot
        self.bot_status = {
            'is_running': False,
            'last_error': None,
            'consecutive_errors': 0,
            'last_trade_time': None
        }
        
        # Métriques de performance
        self.performance = {
            'total_profit_loss': Decimal('0'),
            'success_rate': Decimal('0'),
            'total_gas_spent': Decimal('0'),
            'trades_count': 0,
            'successful_trades': 0
        }
        
        # File d'événements
        self.events: List[Dict] = []
        self.max_events = 1000
        
        # Webhooks pour les notifications
        self.discord_webhook = config.get('monitoring', {}).get('discord_webhook')
        self.telegram_token = config.get('monitoring', {}).get('telegram_token')
        self.telegram_chat_id = config.get('monitoring', {}).get('telegram_chat_id')
        
        # Démarrage du serveur Prometheus
        self._start_prometheus_server()

    def _init_metrics(self):
        """Initialise les métriques Prometheus."""
        # Compteurs
        self.trade_counter = Counter(
            'gbpbot_trades_total',
            'Nombre total de trades exécutés',
            ['status', 'exchange']
        )
        self.error_counter = Counter(
            'gbpbot_errors_total',
            'Nombre total d\'erreurs',
            ['type']
        )
        
        # Jauges
        self.profit_gauge = Gauge(
            'gbpbot_current_profit',
            'Profit/Perte actuel en USD'
        )
        self.gas_price_gauge = Gauge(
            'gbpbot_gas_price',
            'Prix du gas en Gwei'
        )
        self.balance_gauge = Gauge(
            'gbpbot_wallet_balance',
            'Balance du wallet en ETH'
        )
        
        # Histogrammes
        self.trade_duration = Histogram(
            'gbpbot_trade_duration_seconds',
            'Durée d\'exécution des trades',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        self.price_spread = Histogram(
            'gbpbot_price_spread_percent',
            'Spread de prix entre DEX et CEX',
            buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        )

    def _start_prometheus_server(self):
        """Démarre le serveur Prometheus sur le port configuré."""
        try:
            port = self.config.get('monitoring', {}).get('metrics_port', 9090)
            start_http_server(port)
            logger.info(f"Serveur Prometheus démarré sur le port {port}")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du serveur Prometheus: {str(e)}")

    async def track_trade(self, trade_info: Dict):
        """
        Enregistre et analyse un trade.
        
        Args:
            trade_info: Informations sur le trade
        """
        try:
            # Mise à jour des compteurs
            self.trade_counter.labels(
                status=trade_info['status'],
                exchange=trade_info['exchange']
            ).inc()
            
            # Mise à jour des métriques de performance
            if trade_info['status'] == 'success':
                self.performance['successful_trades'] += 1
                self.performance['total_profit_loss'] += Decimal(str(trade_info['profit']))
                self.profit_gauge.set(float(self.performance['total_profit_loss']))
            
            self.performance['trades_count'] += 1
            self.performance['success_rate'] = (
                Decimal(self.performance['successful_trades']) /
                Decimal(self.performance['trades_count'])
            )
            
            # Enregistrement de l'événement
            self._add_event({
                'type': 'trade',
                'timestamp': datetime.now().isoformat(),
                'data': trade_info
            })
            
            # Vérification des alertes
            await self._check_alerts(trade_info)
            
        except Exception as e:
            logger.error(f"Erreur lors du tracking du trade: {str(e)}")

    async def track_error(self, error_info: Dict):
        """
        Enregistre et analyse une erreur.
        
        Args:
            error_info: Informations sur l'erreur
        """
        try:
            # Mise à jour des compteurs
            self.error_counter.labels(
                type=error_info['type']
            ).inc()
            
            # Mise à jour de l'état du bot
            self.bot_status['last_error'] = error_info
            self.bot_status['consecutive_errors'] += 1
            
            # Enregistrement de l'événement
            self._add_event({
                'type': 'error',
                'timestamp': datetime.now().isoformat(),
                'data': error_info
            })
            
            # Vérification du seuil d'erreurs consécutives
            if (self.bot_status['consecutive_errors'] >=
                self.config['security']['emergency_shutdown']['max_consecutive_errors']):
                await self._trigger_emergency_shutdown()
            
            # Envoi d'alertes si nécessaire
            await self._send_error_alert(error_info)
            
        except Exception as e:
            logger.error(f"Erreur lors du tracking de l'erreur: {str(e)}")

    async def update_market_metrics(self, market_info: Dict):
        """
        Met à jour les métriques de marché.
        
        Args:
            market_info: Informations sur le marché
        """
        try:
            # Mise à jour du spread
            if 'spread' in market_info:
                self.price_spread.observe(float(market_info['spread']))
            
            # Mise à jour du prix du gas
            if 'gas_price' in market_info:
                self.gas_price_gauge.set(float(market_info['gas_price']))
            
            # Mise à jour de la balance
            if 'wallet_balance' in market_info:
                self.balance_gauge.set(float(market_info['wallet_balance']))
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques de marché: {str(e)}")

    def _add_event(self, event: Dict):
        """
        Ajoute un événement à l'historique.
        
        Args:
            event: Événement à ajouter
        """
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)

    async def _check_alerts(self, data: Dict):
        """
        Vérifie si des alertes doivent être déclenchées.
        
        Args:
            data: Données à analyser
        """
        try:
            alerts = []
            
            # Vérification du profit
            if 'profit' in data:
                profit_threshold = self.config['monitoring']['alert_threshold']['profit']
                if float(data['profit']) < profit_threshold:
                    alerts.append(f"⚠️ Profit faible: {data['profit']}%")
            
            # Vérification du gas
            if 'gas_price' in data:
                gas_threshold = self.config['monitoring']['alert_threshold']['gas']
                if float(data['gas_price']) > gas_threshold:
                    alerts.append(f"⚠️ Gas price élevé: {data['gas_price']} gwei")
            
            # Envoi des alertes si nécessaire
            if alerts:
                await self._send_alerts(alerts)
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes: {str(e)}")

    async def _send_alerts(self, alerts: List[str]):
        """
        Envoie les alertes via les canaux configurés.
        
        Args:
            alerts: Liste des alertes à envoyer
        """
        message = "\n".join(alerts)
        
        # Discord
        if self.discord_webhook:
            await self._send_discord_alert(message)
        
        # Telegram
        if self.telegram_token and self.telegram_chat_id:
            await self._send_telegram_alert(message)

    async def _send_discord_alert(self, message: str):
        """
        Envoie une alerte via Discord.
        
        Args:
            message: Message à envoyer
        """
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(self.discord_webhook, json={'content': message})
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte Discord: {str(e)}")

    async def _send_telegram_alert(self, message: str):
        """
        Envoie une alerte via Telegram.
        
        Args:
            message: Message à envoyer
        """
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={
                    'chat_id': self.telegram_chat_id,
                    'text': message
                })
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte Telegram: {str(e)}")

    async def _trigger_emergency_shutdown(self):
        """Déclenche l'arrêt d'urgence du bot."""
        try:
            message = "🚨 ARRÊT D'URGENCE DÉCLENCHÉ 🚨\n"
            message += f"Erreurs consécutives: {self.bot_status['consecutive_errors']}\n"
            message += f"Dernière erreur: {self.bot_status['last_error']}"
            
            # Envoi des alertes d'urgence
            await self._send_alerts([message])
            
            # Mise à jour du statut
            self.bot_status['is_running'] = False
            
            # Log de l'événement
            logger.critical("Arrêt d'urgence déclenché")
            
        except Exception as e:
            logger.error(f"Erreur lors du déclenchement de l'arrêt d'urgence: {str(e)}")

    def get_status_report(self) -> Dict:
        """
        Génère un rapport d'état complet du bot.
        
        Returns:
            Dict: Rapport d'état
        """
        return {
            'status': self.bot_status,
            'performance': self.performance,
            'uptime': time.time() - self.start_time,
            'recent_events': self.events[-10:] if self.events else []
        }

    async def close(self):
        """Ferme proprement le système de monitoring."""
        # Rien à faire pour le moment, prévu pour des futures extensions
        pass 