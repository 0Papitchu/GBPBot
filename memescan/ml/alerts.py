from typing import Dict, List, Optional, Union
import asyncio
import json
import aiohttp
from datetime import datetime
from loguru import logger

from ..utils.config import Config
from ..storage.database import Database
from .ml_predictor import MLPredictor

class AlertSystem:
    """Système d'alertes pour les tokens à fort potentiel"""
    
    def __init__(self, config: Config, db: Database, predictor: MLPredictor):
        """
        Initialise le système d'alertes
        
        Args:
            config: Configuration du système
            db: Instance de la base de données
            predictor: Instance du prédicteur ML
        """
        self.config = config
        self.db = db
        self.predictor = predictor
        
        # Configuration des alertes
        self.alert_interval = 3600  # 1 heure en secondes
        self.min_confidence = 0.8  # Confiance minimale pour envoyer une alerte
        self.max_alerts_per_day = 10  # Nombre maximum d'alertes par jour
        self.sent_alerts = set()  # Ensemble des tokens pour lesquels une alerte a été envoyée
        
        # Charger les configurations depuis l'environnement
        self._load_alert_config()
        
    def _load_alert_config(self):
        """Charge la configuration des alertes depuis l'environnement"""
        try:
            # Intervalle entre les alertes (en secondes)
            self.alert_interval = int(self.config.ALERT_INTERVAL) if hasattr(self.config, 'ALERT_INTERVAL') else 3600
            
            # Confiance minimale pour envoyer une alerte
            self.min_confidence = float(self.config.ALERT_MIN_CONFIDENCE) if hasattr(self.config, 'ALERT_MIN_CONFIDENCE') else 0.8
            
            # Nombre maximum d'alertes par jour
            self.max_alerts_per_day = int(self.config.ALERT_MAX_PER_DAY) if hasattr(self.config, 'ALERT_MAX_PER_DAY') else 10
            
            # Webhook Discord
            self.discord_webhook = getattr(self.config, 'DISCORD_WEBHOOK_URL', None)
            
            # Webhook Telegram
            self.telegram_bot_token = getattr(self.config, 'TELEGRAM_BOT_TOKEN', None)
            self.telegram_chat_id = getattr(self.config, 'TELEGRAM_CHAT_ID', None)
            
            logger.info("Alert configuration loaded")
            
        except Exception as e:
            logger.error(f"Error loading alert configuration: {str(e)}")
            
    async def check_and_send_alerts(self):
        """Vérifie les prédictions et envoie des alertes si nécessaire"""
        try:
            # Obtenir les prédictions actuelles
            predictions = await self.predictor.predict(force=False)
            
            if not predictions:
                logger.warning("No predictions available for alerts")
                return
                
            # Récupérer les tokens à fort potentiel
            high_potential = predictions.get(MLPredictor.HIGH_POTENTIAL, [])
            
            # Filtrer par confiance et exclure les tokens déjà alertés
            alert_candidates = [
                token for token in high_potential
                if token["confidence"] >= self.min_confidence
                and token["address"] not in self.sent_alerts
            ]
            
            # Limiter le nombre d'alertes
            alert_candidates = alert_candidates[:self.max_alerts_per_day]
            
            if not alert_candidates:
                logger.info("No new high potential tokens to alert")
                return
                
            # Envoyer les alertes
            for token in alert_candidates:
                await self._send_alert(token)
                self.sent_alerts.add(token["address"])
                
            logger.info(f"Sent alerts for {len(alert_candidates)} tokens")
            
        except Exception as e:
            logger.error(f"Error checking and sending alerts: {str(e)}")
            
    async def _send_alert(self, token: Dict):
        """
        Envoie une alerte pour un token
        
        Args:
            token: Informations du token
        """
        try:
            # Construire le message d'alerte
            message = self._format_alert_message(token)
            
            # Envoyer via Discord si configuré
            if self.discord_webhook:
                await self._send_discord_alert(message, token)
                
            # Envoyer via Telegram si configuré
            if self.telegram_bot_token and self.telegram_chat_id:
                await self._send_telegram_alert(message, token)
                
            # Enregistrer l'alerte dans la base de données
            await self._store_alert(token)
            
        except Exception as e:
            logger.error(f"Error sending alert for token {token['address']}: {str(e)}")
            
    def _format_alert_message(self, token: Dict) -> str:
        """
        Formate le message d'alerte
        
        Args:
            token: Informations du token
            
        Returns:
            Message formaté
        """
        try:
            # Formater le prix avec la bonne précision
            price_str = f"{token['price']:.8f}" if token['price'] < 0.01 else f"{token['price']:.4f}"
            
            # Formater le market cap
            market_cap_str = f"${token['market_cap']:,.0f}" if token['market_cap'] >= 1 else "N/A"
            
            # Construire le message
            message = (
                f"🚀 **Token à Fort Potentiel Détecté** 🚀\n\n"
                f"**Nom:** {token['name']} ({token['symbol']})\n"
                f"**Chaîne:** {token['chain']}\n"
                f"**Prix:** ${price_str}\n"
                f"**Volume 24h:** ${token['volume_24h']:,.0f}\n"
                f"**Market Cap:** {market_cap_str}\n"
                f"**Score de Confiance:** {token['confidence']:.2f}\n\n"
                f"**Adresse:** `{token['address']}`\n\n"
                f"*Détecté le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}*"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting alert message: {str(e)}")
            return f"Alerte: Token à fort potentiel détecté - {token['symbol']}"
            
    async def _send_discord_alert(self, message: str, token: Dict):
        """
        Envoie une alerte via Discord
        
        Args:
            message: Message à envoyer
            token: Informations du token
        """
        try:
            # Construire l'embed Discord
            embed = {
                "title": f"🚀 Token à Fort Potentiel: {token['symbol']}",
                "description": message,
                "color": 3066993,  # Vert
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "MemeScan ML Predictor"
                },
                "fields": [
                    {
                        "name": "Chaîne",
                        "value": token['chain'],
                        "inline": True
                    },
                    {
                        "name": "Prix",
                        "value": f"${token['price']:.8f}" if token['price'] < 0.01 else f"${token['price']:.4f}",
                        "inline": True
                    },
                    {
                        "name": "Confiance",
                        "value": f"{token['confidence']:.2f}",
                        "inline": True
                    }
                ]
            }
            
            # Préparer la payload
            payload = {
                "content": "Nouveau token à fort potentiel détecté!",
                "embeds": [embed]
            }
            
            # Envoyer la requête
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 204:
                        logger.warning(f"Discord webhook returned status {response.status}")
                    else:
                        logger.info(f"Discord alert sent for {token['symbol']}")
                        
        except Exception as e:
            logger.error(f"Error sending Discord alert: {str(e)}")
            
    async def _send_telegram_alert(self, message: str, token: Dict):
        """
        Envoie une alerte via Telegram
        
        Args:
            message: Message à envoyer
            token: Informations du token
        """
        try:
            # URL de l'API Telegram
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            # Préparer la payload
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            # Envoyer la requête
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.warning(f"Telegram API returned status {response.status}")
                    else:
                        logger.info(f"Telegram alert sent for {token['symbol']}")
                        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {str(e)}")
            
    async def _store_alert(self, token: Dict):
        """
        Enregistre l'alerte dans la base de données
        
        Args:
            token: Informations du token
        """
        try:
            # Préparer les données
            alert_data = {
                "token_address": token["address"],
                "alert_type": "high_potential",
                "alert_time": datetime.now(),
                "confidence": token["confidence"],
                "price": token["price"],
                "additional_data": json.dumps({
                    "volume_24h": token["volume_24h"],
                    "market_cap": token["market_cap"],
                    "chain": token["chain"],
                    "symbol": token["symbol"]
                })
            }
            
            # Insérer dans la base de données
            async with self.db.async_session() as session:
                query = """
                    INSERT INTO token_alerts (
                        token_address, alert_type, alert_time,
                        confidence, price, additional_data
                    ) VALUES (
                        :token_address, :alert_type, :alert_time,
                        :confidence, :price, :additional_data
                    )
                """
                
                await session.execute(query, alert_data)
                await session.commit()
                
            logger.info(f"Alert stored in database for token {token['symbol']}")
            
        except Exception as e:
            logger.error(f"Error storing alert in database: {str(e)}")
            
    async def run_alert_loop(self):
        """Exécute la boucle d'alertes périodique"""
        try:
            logger.info(f"Starting alert loop with interval of {self.alert_interval} seconds")
            
            while True:
                # Vérifier et envoyer les alertes
                await self.check_and_send_alerts()
                
                # Attendre l'intervalle configuré
                await asyncio.sleep(self.alert_interval)
                
                # Réinitialiser les alertes envoyées à minuit
                now = datetime.now()
                if now.hour == 0 and now.minute < 5:
                    self.sent_alerts.clear()
                    logger.info("Reset sent alerts list")
                    
        except Exception as e:
            logger.error(f"Error in alert loop: {str(e)}")
            
    async def send_test_alert(self, token_data: Dict):
        """
        Envoie une alerte de test
        
        Args:
            token_data: Données du token pour le test
        """
        try:
            logger.info("Sending test alert")
            
            # Valeurs par défaut pour les champs manquants
            default_data = {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "chain": "solana",
                "name": "Test Token",
                "symbol": "TEST",
                "price": 0.001,
                "volume_24h": 100000,
                "market_cap": 1000000,
                "confidence": 0.95,
                "prediction_time": datetime.now().isoformat()
            }
            
            # Fusionner avec les données fournies
            token = {**default_data, **token_data}
            
            # Envoyer l'alerte
            await self._send_alert(token)
            
            logger.info("Test alert sent")
            
        except Exception as e:
            logger.error(f"Error sending test alert: {str(e)}")
            
    async def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """
        Récupère les alertes récentes
        
        Args:
            limit: Nombre maximum d'alertes à récupérer
            
        Returns:
            Liste des alertes récentes
        """
        try:
            # Requête SQL
            query = """
                SELECT 
                    token_address, alert_type, alert_time,
                    confidence, price, additional_data
                FROM token_alerts
                ORDER BY alert_time DESC
                LIMIT :limit
            """
            
            # Exécuter la requête
            async with self.db.async_session() as session:
                result = await session.execute(query, {"limit": limit})
                rows = [dict(row) for row in result]
                
            # Traiter les résultats
            alerts = []
            for row in rows:
                # Convertir les données additionnelles
                additional_data = json.loads(row["additional_data"]) if isinstance(row["additional_data"], str) else {}
                
                # Fusionner les données
                alert = {**row, **additional_data}
                alert["alert_time"] = alert["alert_time"].isoformat() if hasattr(alert["alert_time"], "isoformat") else alert["alert_time"]
                
                # Supprimer le champ brut
                if "additional_data" in alert:
                    del alert["additional_data"]
                    
                alerts.append(alert)
                
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {str(e)}")
            return [] 