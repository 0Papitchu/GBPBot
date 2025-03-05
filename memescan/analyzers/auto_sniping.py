import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
import json
from loguru import logger
from web3 import Web3
from web3.exceptions import ExtraDataLengthError

from memescan.utils.config import Config
from memescan.storage.database import Database
from memescan.ml.ml_predictor import MLPredictor

# Fonction pour créer un middleware personnalisé pour les chaînes PoA
# Fonction supprimée car non nécessaire avec web3.py v7.8.0

class AutoSniper:
    """Module de sniping automatique pour les nouveaux tokens à fort potentiel"""
    
    def __init__(self, config: Config, db: Database, ml_predictor: MLPredictor):
        self.config = config
        self.db = db
        self.ml_predictor = ml_predictor
        
        # Paramètres de sniping
        self.min_liquidity = 1000  # Liquidité minimale en USD
        self.max_market_cap = 10000  # Market cap maximum pour sniping (10k$)
        self.min_confidence_score = 0.7  # Score de confiance ML minimum
        self.max_tokens_per_day = 5  # Nombre maximum de tokens à sniper par jour
        self.min_time_between_snipes = 3600  # Temps minimum entre deux snipes (1h)
        
        # État du sniping
        self.last_snipe_time = 0
        self.sniped_tokens = set()
        self.daily_snipe_count = 0
        self.last_day_reset = datetime.now().date()
        
        # Connexions Web3
        self.web3_connections = {}
        self._init_web3_connections()
        
        # Paramètres de sécurité
        self.security_checks = {
            "honeypot_detection": True,
            "contract_verification": True,
            "liquidity_lock_check": True,
            "ownership_renounced_check": True,
            "max_buy_tax": 10,  # 10%
            "max_sell_tax": 15,  # 15%
        }
        
        # Paramètres de transaction
        self.gas_boost = 1.2  # Multiplicateur de gas pour transactions rapides
        self.slippage = 10  # Slippage en pourcentage
        self.default_buy_amount = 0.05  # Montant par défaut en ETH/AVAX
        
    def _init_web3_connections(self):
        """Initialise les connexions Web3 pour différentes blockchains"""
        # Avalanche
        self.web3_avax = Web3(Web3.HTTPProvider(self.config['rpc_endpoints']['avalanche']))
        # Middleware PoA non nécessaire avec web3.py v7.8.0
        
        # Sonic
        self.web3_sonic = Web3(Web3.HTTPProvider(self.config['rpc_endpoints']['sonic']))
        # Middleware PoA non nécessaire avec web3.py v7.8.0
        
        # Initialiser le dictionnaire des connexions
        self.web3_connections = {
            "avalanche": self.web3_avax,
            "sonic": self.web3_sonic
        }
        
        logger.info(f"Web3 connections initialized for {len(self.web3_connections)} chains")
        
    async def start_auto_sniping(self):
        """Démarre le processus de sniping automatique"""
        logger.info("Starting automatic token sniping")
        
        while True:
            try:
                # Réinitialiser le compteur quotidien si nécessaire
                current_date = datetime.now().date()
                if current_date > self.last_day_reset:
                    self.daily_snipe_count = 0
                    self.last_day_reset = current_date
                    logger.info("Daily snipe counter reset")
                
                # Vérifier si nous avons atteint la limite quotidienne
                if self.daily_snipe_count >= self.max_tokens_per_day:
                    logger.info(f"Daily snipe limit reached ({self.max_tokens_per_day}). Waiting for next day.")
                    await asyncio.sleep(3600)  # Attendre 1 heure avant de vérifier à nouveau
                    continue
                
                # Vérifier le temps écoulé depuis le dernier snipe
                current_time = time.time()
                if current_time - self.last_snipe_time < self.min_time_between_snipes:
                    await asyncio.sleep(60)  # Attendre 1 minute avant de vérifier à nouveau
                    continue
                
                # Rechercher les événements de sniping en attente
                pending_events = await self._get_pending_sniping_events()
                
                if not pending_events:
                    await asyncio.sleep(10)  # Attendre 10 secondes avant de vérifier à nouveau
                    continue
                
                # Traiter chaque événement
                for event in pending_events:
                    # Analyser le token pour déterminer s'il faut le sniper
                    should_snipe, analysis_result = await self._analyze_token_for_sniping(event)
                    
                    if should_snipe:
                        # Exécuter le sniping
                        success = await self._execute_snipe(event, analysis_result)
                        
                        if success:
                            # Mettre à jour les compteurs
                            self.daily_snipe_count += 1
                            self.last_snipe_time = time.time()
                            self.sniped_tokens.add(event["token_address"])
                            
                            # Mettre à jour le statut de l'événement
                            await self._update_event_status(event["id"], "sniped", analysis_result)
                            
                            logger.info(f"🚀 SNIPED: {event['token_symbol']} on {event['chain']}/{event['dex']}")
                            
                            # Si nous avons atteint la limite quotidienne, attendre plus longtemps
                            if self.daily_snipe_count >= self.max_tokens_per_day:
                                logger.info(f"Daily snipe limit reached ({self.max_tokens_per_day})")
                                await asyncio.sleep(3600)
                                break
                            
                            # Attendre entre les snipes
                            await asyncio.sleep(self.min_time_between_snipes)
                        else:
                            # Mettre à jour le statut de l'événement
                            await self._update_event_status(event["id"], "failed", analysis_result)
                    else:
                        # Mettre à jour le statut de l'événement
                        await self._update_event_status(event["id"], "rejected", analysis_result)
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in auto sniping loop: {str(e)}")
                await asyncio.sleep(30)
    
    async def _get_pending_sniping_events(self) -> List[Dict]:
        """Récupère les événements de sniping en attente"""
        try:
            query = """
                SELECT 
                    id, token_address, token_symbol, chain, dex,
                    price, liquidity, market_cap, is_meme,
                    detection_time, status
                FROM sniping_events
                WHERE status = 'detected'
                ORDER BY detection_time ASC
                LIMIT 10
            """
            
            async with self.db.async_session() as session:
                result = await session.execute(query)
                events = [dict(row) for row in result]
                
            return events
            
        except Exception as e:
            logger.error(f"Error getting pending sniping events: {str(e)}")
            return []
    
    async def _analyze_token_for_sniping(self, event: Dict) -> tuple[bool, Dict]:
        """Analyse un token pour déterminer s'il faut le sniper"""
        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "token_address": event["token_address"],
            "token_symbol": event["token_symbol"],
            "chain": event["chain"],
            "dex": event["dex"],
            "initial_price": event["price"],
            "initial_liquidity": event["liquidity"],
            "initial_market_cap": event["market_cap"],
            "is_meme": event["is_meme"],
            "checks": {},
            "ml_score": 0,
            "final_score": 0,
            "decision": "reject",
            "reason": ""
        }
        
        try:
            # 1. Vérifier les critères de base
            if event["token_address"] in self.sniped_tokens:
                analysis_result["decision"] = "reject"
                analysis_result["reason"] = "Token already sniped"
                return False, analysis_result
                
            if event["liquidity"] < self.min_liquidity:
                analysis_result["decision"] = "reject"
                analysis_result["reason"] = f"Insufficient liquidity: ${event['liquidity']}"
                return False, analysis_result
                
            if event["market_cap"] > self.max_market_cap:
                analysis_result["decision"] = "reject"
                analysis_result["reason"] = f"Market cap too high: ${event['market_cap']}"
                return False, analysis_result
            
            # 2. Vérifications de sécurité
            security_result = await self._perform_security_checks(event)
            analysis_result["checks"] = security_result
            
            # Vérifier si des problèmes critiques ont été détectés
            if not security_result.get("passed", False):
                analysis_result["decision"] = "reject"
                analysis_result["reason"] = security_result.get("reason", "Security checks failed")
                return False, analysis_result
            
            # 3. Analyse ML
            ml_score = await self._get_ml_prediction(event)
            analysis_result["ml_score"] = ml_score
            
            if ml_score < self.min_confidence_score:
                analysis_result["decision"] = "reject"
                analysis_result["reason"] = f"ML score too low: {ml_score}"
                return False, analysis_result
            
            # 4. Calculer le score final
            # Formule: (ML score * 0.6) + (1 - market_cap/max_market_cap) * 0.2 + (liquidity/min_liquidity) * 0.2
            market_cap_factor = 1 - (event["market_cap"] / self.max_market_cap)
            liquidity_factor = min(1.0, event["liquidity"] / self.min_liquidity)
            
            final_score = (ml_score * 0.6) + (market_cap_factor * 0.2) + (liquidity_factor * 0.2)
            analysis_result["final_score"] = final_score
            
            # 5. Prendre la décision finale
            if final_score >= 0.7:
                analysis_result["decision"] = "snipe"
                analysis_result["reason"] = f"High potential token with score {final_score:.2f}"
                return True, analysis_result
            else:
                analysis_result["decision"] = "reject"
                analysis_result["reason"] = f"Final score too low: {final_score:.2f}"
                return False, analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing token for sniping: {str(e)}")
            analysis_result["decision"] = "reject"
            analysis_result["reason"] = f"Error during analysis: {str(e)}"
            return False, analysis_result
    
    async def _perform_security_checks(self, event: Dict) -> Dict:
        """Effectue des vérifications de sécurité sur le token"""
        result = {
            "passed": True,
            "honeypot": False,
            "contract_verified": False,
            "liquidity_locked": False,
            "ownership_renounced": False,
            "buy_tax": 0,
            "sell_tax": 0,
            "reason": ""
        }
        
        try:
            # Simuler les vérifications de sécurité
            # Dans une implémentation réelle, ces vérifications seraient plus complètes
            
            # 1. Vérification du contrat (via API Etherscan/Snowtrace)
            result["contract_verified"] = True
            
            # 2. Vérification du honeypot (simulation d'achat/vente)
            result["honeypot"] = False
            
            # 3. Vérification du verrouillage de liquidité
            result["liquidity_locked"] = True
            
            # 4. Vérification de la renonciation à la propriété
            result["ownership_renounced"] = True
            
            # 5. Estimation des taxes
            result["buy_tax"] = 5  # 5%
            result["sell_tax"] = 7  # 7%
            
            # Vérifier les critères de sécurité
            if self.security_checks["honeypot_detection"] and result["honeypot"]:
                result["passed"] = False
                result["reason"] = "Token is a honeypot"
                
            if self.security_checks["contract_verification"] and not result["contract_verified"]:
                result["passed"] = False
                result["reason"] = "Contract not verified"
                
            if self.security_checks["liquidity_lock_check"] and not result["liquidity_locked"]:
                result["passed"] = False
                result["reason"] = "Liquidity not locked"
                
            if self.security_checks["ownership_renounced_check"] and not result["ownership_renounced"]:
                result["passed"] = False
                result["reason"] = "Ownership not renounced"
                
            if result["buy_tax"] > self.security_checks["max_buy_tax"]:
                result["passed"] = False
                result["reason"] = f"Buy tax too high: {result['buy_tax']}%"
                
            if result["sell_tax"] > self.security_checks["max_sell_tax"]:
                result["passed"] = False
                result["reason"] = f"Sell tax too high: {result['sell_tax']}%"
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing security checks: {str(e)}")
            result["passed"] = False
            result["reason"] = f"Error during security checks: {str(e)}"
            return result
    
    async def _get_ml_prediction(self, event: Dict) -> float:
        """Obtient une prédiction ML pour le token"""
        try:
            # Préparer les données pour la prédiction
            token_data = {
                "address": event["token_address"],
                "chain": event["chain"],
                "name": event["token_symbol"],
                "symbol": event["token_symbol"],
                "price": event["price"],
                "volume_24h": 0,  # Nouveau token, pas encore de volume
                "tvl": event["liquidity"],
                "holders": 1,  # Valeur par défaut
                "transactions_24h": 0,  # Nouveau token
                "token_age_days": 0.01  # Très récent
            }
            
            # Obtenir la prédiction
            prediction = await self.ml_predictor.predict_single_token(token_data)
            
            # Retourner le score de confiance pour la catégorie HIGH_POTENTIAL
            return prediction.get("confidence", 0)
            
        except Exception as e:
            logger.error(f"Error getting ML prediction: {str(e)}")
            return 0
    
    async def _execute_snipe(self, event: Dict, analysis: Dict) -> bool:
        """Exécute l'achat du token (sniping)"""
        try:
            # Obtenir la connexion Web3 pour la chaîne
            web3 = self.web3_connections.get(event["chain"])
            if not web3:
                logger.error(f"No Web3 connection available for {event['chain']}")
                return False
            
            # Calculer le montant à acheter
            buy_amount = self.default_buy_amount
            
            # Obtenir les informations de la paire
            pair_info = await self._get_pair_info(event["token_address"], event["chain"], event["dex"])
            if not pair_info:
                logger.error(f"Could not get pair info for {event['token_symbol']}")
                return False
            
            # Préparer la transaction d'achat
            tx_data = await self._prepare_buy_transaction(
                web3, 
                event["token_address"], 
                pair_info["router_address"], 
                buy_amount,
                event["chain"]
            )
            
            if not tx_data:
                logger.error(f"Could not prepare buy transaction for {event['token_symbol']}")
                return False
            
            # Signer et envoyer la transaction
            tx_hash = await self._send_transaction(web3, tx_data, event["chain"])
            
            if not tx_hash:
                logger.error(f"Could not send buy transaction for {event['token_symbol']}")
                return False
            
            # Attendre la confirmation de la transaction
            receipt = await self._wait_for_transaction(web3, tx_hash)
            
            if not receipt or receipt.status != 1:
                logger.error(f"Buy transaction failed for {event['token_symbol']}")
                return False
            
            # Enregistrer l'achat dans la base de données
            await self._record_snipe(event, analysis, tx_hash, buy_amount)
            
            logger.info(f"Successfully sniped {event['token_symbol']} on {event['chain']}/{event['dex']}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing snipe: {str(e)}")
            return False
    
    async def _get_pair_info(self, token_address: str, chain: str, dex: str) -> Optional[Dict]:
        """Obtient les informations de la paire pour un token"""
        # Dans une implémentation réelle, cette fonction récupérerait les informations
        # de la paire depuis la blockchain ou la base de données
        
        # Exemple simplifié
        router_addresses = {
            "avalanche": {
                "trader_joe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"
            },
            "sonic": {
                "pump_fun": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
            }
        }
        
        return {
            "router_address": router_addresses.get(chain, {}).get(dex),
            "pair_address": "0x...",  # Adresse de la paire
            "path": ["0x...", token_address]  # Chemin d'échange
        }
    
    async def _prepare_buy_transaction(self, web3, token_address: str, router_address: str, amount: float, chain: str) -> Optional[Dict]:
        """Prépare une transaction d'achat"""
        # Dans une implémentation réelle, cette fonction préparerait la transaction
        # en utilisant l'ABI du routeur et les paramètres appropriés
        
        # Exemple simplifié
        return {
            "to": router_address,
            "value": web3.to_wei(amount, "ether"),
            "gas": 500000,
            "gasPrice": web3.to_wei(50, "gwei"),
            "data": "0x..."  # Données de la transaction
        }
    
    async def _send_transaction(self, web3, tx_data: Dict, chain: str) -> Optional[str]:
        """Signe et envoie une transaction"""
        # Dans une implémentation réelle, cette fonction signerait et enverrait
        # la transaction en utilisant la clé privée du portefeuille
        
        # Exemple simplifié
        return "0x..."  # Hash de la transaction
    
    async def _wait_for_transaction(self, web3, tx_hash: str) -> Optional[Dict]:
        """Attend la confirmation d'une transaction"""
        # Dans une implémentation réelle, cette fonction attendrait la confirmation
        # de la transaction et retournerait le reçu
        
        # Exemple simplifié
        return {"status": 1}  # Reçu de la transaction
    
    async def _record_snipe(self, event: Dict, analysis: Dict, tx_hash: str, amount: float):
        """Enregistre un snipe dans la base de données"""
        try:
            snipe_data = {
                "token_address": event["token_address"],
                "token_symbol": event["token_symbol"],
                "chain": event["chain"],
                "dex": event["dex"],
                "price": event["price"],
                "amount": amount,
                "tx_hash": tx_hash,
                "timestamp": datetime.now().isoformat(),
                "ml_score": analysis["ml_score"],
                "final_score": analysis["final_score"],
                "status": "active"
            }
            
            query = """
                INSERT INTO token_snipes (
                    token_address, token_symbol, chain, dex,
                    price, amount, tx_hash, timestamp,
                    ml_score, final_score, status
                ) VALUES (
                    :token_address, :token_symbol, :chain, :dex,
                    :price, :amount, :tx_hash, :timestamp,
                    :ml_score, :final_score, :status
                )
            """
            
            async with self.db.async_session() as session:
                await session.execute(query, snipe_data)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error recording snipe: {str(e)}")
    
    async def _update_event_status(self, event_id: int, status: str, analysis: Dict):
        """Met à jour le statut d'un événement de sniping"""
        try:
            query = """
                UPDATE sniping_events
                SET status = :status, analysis = :analysis
                WHERE id = :event_id
            """
            
            async with self.db.async_session() as session:
                await session.execute(query, {
                    "event_id": event_id,
                    "status": status,
                    "analysis": str(analysis)
                })
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating event status: {str(e)}")
            
    async def predict_single_token(self, token_data: Dict) -> Dict:
        """Prédit le potentiel d'un seul token"""
        try:
            # Créer un ensemble de données avec un seul token
            features = []
            
            # Extraire ou calculer les caractéristiques nécessaires
            volume_24h = float(token_data.get("volume_24h", 0))
            volume_1h = float(token_data.get("volume_1h", 0))
            price = float(token_data.get("price", 0))
            holders = int(token_data.get("holders", 1))
            transactions_24h = int(token_data.get("transactions_24h", 0))
            token_age_days = float(token_data.get("token_age_days", 0.1))
            
            # Calculer les caractéristiques dérivées
            volume_to_mcap = 0
            if "market_cap" in token_data and float(token_data["market_cap"]) > 0:
                volume_to_mcap = volume_24h / float(token_data["market_cap"])
                
            holder_concentration = 0
            if "total_supply" in token_data and float(token_data["total_supply"]) > 0:
                holder_concentration = holders / float(token_data["total_supply"])
                
            trading_activity = 0
            if holders > 0:
                trading_activity = transactions_24h / holders
            
            # Créer le vecteur de caractéristiques
            token_features = [
                volume_24h, volume_1h, price,
                holders, transactions_24h, token_age_days,
                volume_to_mcap, holder_concentration, trading_activity
            ]
            
            features.append(token_features)
            
            # Effectuer la prédiction
            prediction = self.ml_predictor.model.predict(features)
            
            # Déterminer la classe prédite et la confiance
            if len(prediction.shape) > 1 and prediction.shape[1] == 3:
                class_index = prediction[0].argmax()
                confidence = prediction[0][class_index]
            else:
                class_index = int(prediction[0])
                confidence = 1.0
                
            # Mapper l'indice à la catégorie
            category_map = {
                0: "HIGH_POTENTIAL",
                1: "NEUTRAL",
                2: "HIGH_RISK"
            }
            
            category = category_map.get(class_index, "NEUTRAL")
            
            return {
                "address": token_data["address"],
                "symbol": token_data["symbol"],
                "category": category,
                "confidence": float(confidence),
                "prediction_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error predicting single token: {str(e)}")
            return {
                "address": token_data.get("address", "unknown"),
                "symbol": token_data.get("symbol", "unknown"),
                "category": "NEUTRAL",
                "confidence": 0.0,
                "prediction_time": datetime.now().isoformat(),
                "error": str(e)
            } 