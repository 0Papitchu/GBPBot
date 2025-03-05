#!/usr/bin/env python3
"""
Module de monitoring avancé avec métriques en temps réel et alertes.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import json
from loguru import logger

class AdvancedMonitor:
    """Système de monitoring avancé."""
    
    def __init__(self, config: Dict):
        """
        Initialise le système de monitoring.
        
        Args:
            config: Configuration du bot
        """
        self.config = config
        self.monitor_config = self.config.get('monitoring', {})
        
        # Configuration des alertes
        self.alert_thresholds = {
            'profit_loss': Decimal(str(self.monitor_config.get('profit_loss_threshold', '-0.05'))),
            'gas_price': Web3.to_wei(self.monitor_config.get('max_gas_alert', 300), 'gwei'),
            'slippage': Decimal(str(self.monitor_config.get('max_slippage_alert', '0.02'))),
            'error_rate': Decimal(str(self.monitor_config.get('error_rate_threshold', '0.10')))
        }
        
        # Métriques
        self.metrics: Dict[str, Dict] = {
            'market': {},      # Prix, spreads, liquidité
            'performance': {}, # Profits, pertes, ROI
            'system': {},     # CPU, mémoire, latence
            'errors': {},     # Taux d'erreur, types d'erreurs
            'trades': {}      # Nombre de trades, volume
        }
        
        # Historique
        self.history: Dict[str, List] = {
            'trades': [],
            'alerts': [],
            'errors': []
        }
        
        # État du monitoring
        self.is_running = False
        self.update_task = None
        self.last_update = 0
        self.update_interval = self.monitor_config.get('update_interval', 1)
        
        # Notifications
        self.notification_queue = asyncio.Queue()
        self.notification_task = None

    async def start(self):
        """Démarre le système de monitoring."""
        try:
            self.is_running = True
            
            # Démarrer la tâche de mise à jour
            self.update_task = asyncio.create_task(self._update_loop())
            
            # Démarrer la tâche de notification
            self.notification_task = asyncio.create_task(self._notification_loop())
            
            logger.info("Système de monitoring démarré")
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du monitoring: {str(e)}")
            raise

    async def stop(self):
        """Arrête le système de monitoring."""
        self.is_running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
                
        if self.notification_task:
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Système de monitoring arrêté")

    async def update_market_metrics(self, metrics: Dict[str, Any]):
        """
        Met à jour les métriques de marché.
        
        Args:
            metrics: Nouvelles métriques
        """
        try:
            self.metrics['market'].update(metrics)
            
            # Vérifier les alertes
            await self._check_market_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques de marché: {str(e)}")

    async def update_performance_metrics(self, metrics: Dict[str, Any]):
        """
        Met à jour les métriques de performance.
        
        Args:
            metrics: Nouvelles métriques
        """
        try:
            self.metrics['performance'].update(metrics)
            
            # Vérifier les alertes
            await self._check_performance_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques de performance: {str(e)}")

    async def log_trade(self, trade_info: Dict):
        """
        Enregistre un trade.
        
        Args:
            trade_info: Informations sur le trade
        """
        try:
            # Ajouter le timestamp
            trade_info['timestamp'] = time.time()
            
            # Mettre à jour les métriques
            self.metrics['trades']['total_count'] = self.metrics['trades'].get('total_count', 0) + 1
            self.metrics['trades']['total_volume'] = (
                Decimal(str(self.metrics['trades'].get('total_volume', '0'))) +
                Decimal(str(trade_info.get('volume', '0')))
            )
            
            # Ajouter à l'historique
            self.history['trades'].append(trade_info)
            
            # Nettoyer l'historique si nécessaire
            if len(self.history['trades']) > 1000:
                self.history['trades'] = self.history['trades'][-1000:]
                
            # Vérifier les alertes
            await self._check_trade_alerts(trade_info)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du trade: {str(e)}")

    async def log_error(self, error_info: Dict):
        """
        Enregistre une erreur.
        
        Args:
            error_info: Informations sur l'erreur
        """
        try:
            # Ajouter le timestamp
            error_info['timestamp'] = time.time()
            
            # Mettre à jour les métriques
            error_type = error_info.get('type', 'unknown')
            self.metrics['errors'][error_type] = self.metrics['errors'].get(error_type, 0) + 1
            
            # Ajouter à l'historique
            self.history['errors'].append(error_info)
            
            # Nettoyer l'historique si nécessaire
            if len(self.history['errors']) > 1000:
                self.history['errors'] = self.history['errors'][-1000:]
                
            # Vérifier les alertes
            await self._check_error_alerts()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'erreur: {str(e)}")

    async def get_metrics(self) -> Dict:
        """
        Récupère toutes les métriques.
        
        Returns:
            Dict: Métriques actuelles
        """
        return self.metrics.copy()

    async def get_history(self, category: str, limit: int = 100) -> List[Dict]:
        """
        Récupère l'historique d'une catégorie.
        
        Args:
            category: Catégorie (trades, alerts, errors)
            limit: Nombre maximum d'entrées
            
        Returns:
            List[Dict]: Historique
        """
        if category not in self.history:
            return []
            
        return self.history[category][-limit:]

    async def _update_loop(self):
        """Boucle de mise à jour des métriques."""
        while self.is_running:
            try:
                current_time = time.time()
                if current_time - self.last_update < self.update_interval:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Mettre à jour les métriques système
                await self._update_system_metrics()
                
                # Calculer les métriques agrégées
                await self._calculate_aggregated_metrics()
                
                self.last_update = current_time
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de mise à jour: {str(e)}")
                await asyncio.sleep(5)

    async def _notification_loop(self):
        """Boucle d'envoi des notifications."""
        while self.is_running:
            try:
                # Attendre la prochaine notification
                notification = await self.notification_queue.get()
                
                # Envoyer la notification
                await self._send_notification(notification)
                
                # Marquer comme traitée
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de notification: {str(e)}")
                await asyncio.sleep(5)

    async def _check_market_alerts(self, metrics: Dict):
        """
        Vérifie les alertes liées au marché.
        
        Args:
            metrics: Métriques à vérifier
        """
        try:
            # Vérifier le gas price
            if 'gas_price' in metrics:
                gas_price = Web3.to_wei(metrics['gas_price'], 'gwei')
                if gas_price > self.alert_thresholds['gas_price']:
                    await self._create_alert(
                        'HIGH_GAS',
                        f"Gas price élevé: {metrics['gas_price']} gwei"
                    )
                    
            # Vérifier le slippage
            if 'slippage' in metrics:
                slippage = Decimal(str(metrics['slippage']))
                if slippage > self.alert_thresholds['slippage']:
                    await self._create_alert(
                        'HIGH_SLIPPAGE',
                        f"Slippage élevé: {slippage}%"
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes marché: {str(e)}")

    async def _check_performance_alerts(self, metrics: Dict):
        """
        Vérifie les alertes liées à la performance.
        
        Args:
            metrics: Métriques à vérifier
        """
        try:
            # Vérifier le profit/perte
            if 'profit_loss' in metrics:
                profit_loss = Decimal(str(metrics['profit_loss']))
                if profit_loss < self.alert_thresholds['profit_loss']:
                    await self._create_alert(
                        'SIGNIFICANT_LOSS',
                        f"Perte significative: {profit_loss}%"
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes performance: {str(e)}")

    async def _check_trade_alerts(self, trade_info: Dict):
        """
        Vérifie les alertes liées aux trades.
        
        Args:
            trade_info: Informations sur le trade
        """
        try:
            # Vérifier le volume
            if 'volume' in trade_info:
                volume = Decimal(str(trade_info['volume']))
                if volume > Decimal('10'):  # Volume important
                    await self._create_alert(
                        'LARGE_TRADE',
                        f"Trade important: {volume} ETH"
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes trade: {str(e)}")

    async def _check_error_alerts(self):
        """Vérifie les alertes liées aux erreurs."""
        try:
            # Calculer le taux d'erreur
            total_errors = sum(self.metrics['errors'].values())
            total_trades = self.metrics['trades'].get('total_count', 0)
            
            if total_trades > 0:
                error_rate = Decimal(str(total_errors)) / Decimal(str(total_trades))
                
                if error_rate > self.alert_thresholds['error_rate']:
                    await self._create_alert(
                        'HIGH_ERROR_RATE',
                        f"Taux d'erreur élevé: {error_rate * 100}%"
                    )
                    
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes erreur: {str(e)}")

    async def _create_alert(self, alert_type: str, message: str):
        """
        Crée une nouvelle alerte.
        
        Args:
            alert_type: Type d'alerte
            message: Message de l'alerte
        """
        try:
            alert = {
                'type': alert_type,
                'message': message,
                'timestamp': time.time()
            }
            
            # Ajouter à l'historique
            self.history['alerts'].append(alert)
            
            # Nettoyer l'historique si nécessaire
            if len(self.history['alerts']) > 1000:
                self.history['alerts'] = self.history['alerts'][-1000:]
                
            # Ajouter à la queue de notification
            await self.notification_queue.put(alert)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'alerte: {str(e)}")

    async def _send_notification(self, notification: Dict):
        """
        Envoie une notification.
        
        Args:
            notification: Notification à envoyer
        """
        try:
            # Formater le message
            message = (
                f"🔔 {notification['type']}\n"
                f"📝 {notification['message']}\n"
                f"⏰ {datetime.fromtimestamp(notification['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # TODO: Implémenter l'envoi via différents canaux (Discord, Telegram, etc.)
            logger.info(f"Notification envoyée: {message}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")

    async def _update_system_metrics(self):
        """Met à jour les métriques système."""
        try:
            # TODO: Implémenter la collecte des métriques système
            self.metrics['system'].update({
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques système: {str(e)}")

    async def _calculate_aggregated_metrics(self):
        """Calcule les métriques agrégées."""
        try:
            # Calculer les moyennes mobiles
            if self.history['trades']:
                recent_trades = self.history['trades'][-100:]  # 100 derniers trades
                
                # Volume moyen
                volumes = [
                    Decimal(str(trade.get('volume', 0)))
                    for trade in recent_trades
                ]
                avg_volume = sum(volumes) / len(volumes)
                
                # Profit moyen
                profits = [
                    Decimal(str(trade.get('profit', 0)))
                    for trade in recent_trades
                ]
                avg_profit = sum(profits) / len(profits)
                
                self.metrics['performance'].update({
                    'avg_volume_100': str(avg_volume),
                    'avg_profit_100': str(avg_profit)
                })
                
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques agrégées: {str(e)}")

    def get_status(self) -> Dict:
        """
        Récupère l'état du système de monitoring.
        
        Returns:
            Dict: État du système
        """
        return {
            'is_running': self.is_running,
            'last_update': self.last_update,
            'metrics_count': {
                category: len(metrics)
                for category, metrics in self.metrics.items()
            },
            'history_count': {
                category: len(history)
                for category, history in self.history.items()
            }
        } 