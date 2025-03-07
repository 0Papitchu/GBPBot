#!/usr/bin/env python3
"""
Module d'arbitrage cross-chain entre Sonic et autres blockchains pour GBPBot.

Ce module implémente des stratégies d'arbitrage entre la blockchain Sonic et d'autres
blockchains (Avalanche, Solana), en exploitant les différences de prix entre les DEX
de ces différentes chaînes.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from decimal import Decimal

from gbpbot.blockchain.sonic_client import SonicClient
from gbpbot.core.blockchain import BlockchainClient
from gbpbot.utils.config import get_config
from gbpbot.utils.exceptions import ArbitrageError, TransactionError
from gbpbot.utils.cache_manager import cache_manager
from gbpbot.core.opportunity_analyzer import OpportunityAnalyzer
from gbpbot.core.mev_executor import MEVExecutor
from gbpbot.ai.market_analyzer import MarketAnalyzer

# Configuration du logger
logger = logging.getLogger(__name__)

class SonicCrossChainArbitrage:
    """
    Stratégie d'arbitrage cross-chain entre Sonic et autres blockchains.
    
    Cette classe implémente des stratégies pour détecter et exploiter les opportunités
    d'arbitrage entre la blockchain Sonic et d'autres blockchains comme Avalanche et Solana.
    """
    
    def __init__(self, config: Dict[str, Any], blockchain_clients: Dict[str, BlockchainClient]):
        """
        Initialise la stratégie d'arbitrage cross-chain.
        
        Args:
            config: Configuration pour la stratégie
            blockchain_clients: Dictionnaire des clients blockchain disponibles
        """
        self.config = config
        self.blockchain_clients = blockchain_clients
        
        # Vérifier que les clients nécessaires sont disponibles
        required_chains = ["sonic", "avalanche", "solana"]
        for chain in required_chains:
            if chain not in self.blockchain_clients:
                logger.warning(f"Client blockchain {chain} non disponible, certaines fonctionnalités d'arbitrage cross-chain seront limitées")
        
        # Paramètres de configuration
        self.min_profit_threshold = float(config.get("MIN_PROFIT_THRESHOLD", 0.5)) / 100  # Convertir en décimal
        self.max_arbitrage_amount_usd = float(config.get("MAX_ARBITRAGE_AMOUNT_USD", 1000))
        self.arbitrage_interval = int(config.get("ARBITRAGE_INTERVAL", 5))
        self.flash_arbitrage_enabled = config.get("FLASH_ARBITRAGE_ENABLED", "true").lower() == "true"
        self.bridge_fee_estimation = float(config.get("BRIDGE_FEE_ESTIMATION", 0.1)) / 100  # Frais de bridge estimés
        
        # Initialiser les analyseurs d'opportunités
        self.opportunity_analyzer = OpportunityAnalyzer()
        
        # Initialiser l'exécuteur MEV si disponible
        try:
            self.mev_executor = MEVExecutor()
            self.mev_available = True
        except ImportError:
            logger.warning("Module MEVExecutor non disponible, les transactions ne seront pas optimisées pour MEV")
            self.mev_executor = None
            self.mev_available = False
        
        # Initialiser l'analyseur de marché IA si disponible
        try:
            self.market_analyzer = MarketAnalyzer()
            self.ai_available = True
        except ImportError:
            logger.warning("Module MarketAnalyzer non disponible, l'analyse IA ne sera pas utilisée")
            self.market_analyzer = None
            self.ai_available = False
        
        # État de la stratégie
        self.running = False
        self.active_arbitrages = set()
        self.monitored_pairs = set()
        self.stats = {
            "opportunities_found": 0,
            "arbitrages_executed": 0,
            "total_profit_usd": 0,
            "failed_arbitrages": 0
        }
        
        # Bridges supportés
        self.supported_bridges = {
            "sonic_avalanche": ["synapse", "multichain"],
            "sonic_solana": ["wormhole", "allbridge"],
            "avalanche_solana": ["wormhole", "allbridge"]
        }
        
        logger.info("Stratégie d'arbitrage cross-chain Sonic initialisée")
    
    async def start(self):
        """Démarre la stratégie d'arbitrage."""
        if self.running:
            logger.warning("La stratégie d'arbitrage est déjà en cours d'exécution")
            return
        
        self.running = True
        logger.info("Démarrage de la stratégie d'arbitrage cross-chain Sonic")
        
        # Démarrer la boucle de surveillance
        asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Arrête la stratégie d'arbitrage."""
        if not self.running:
            logger.warning("La stratégie d'arbitrage n'est pas en cours d'exécution")
            return
        
        self.running = False
        logger.info("Arrêt de la stratégie d'arbitrage cross-chain Sonic")
        
        # Attendre que les arbitrages actifs se terminent
        if self.active_arbitrages:
            logger.info(f"Attente de la fin de {len(self.active_arbitrages)} arbitrages actifs")
            await asyncio.sleep(5)  # Donner du temps pour terminer les arbitrages
    
    async def add_monitored_pair(self, token_symbol: str, source_chain: str, target_chain: str):
        """
        Ajoute une paire à surveiller pour les opportunités d'arbitrage.
        
        Args:
            token_symbol: Symbole du token (ex: "BTC/USDT")
            source_chain: Chaîne source
            target_chain: Chaîne cible
        """
        pair_key = f"{token_symbol}:{source_chain}:{target_chain}"
        
        if pair_key in self.monitored_pairs:
            logger.warning(f"La paire {pair_key} est déjà surveillée")
            return
        
        # Vérifier que les chaînes sont supportées
        if source_chain not in self.blockchain_clients or target_chain not in self.blockchain_clients:
            logger.error(f"Chaîne non supportée: {source_chain} ou {target_chain}")
            return
        
        # Vérifier que le bridge est supporté
        bridge_key = f"{source_chain}_{target_chain}"
        if bridge_key not in self.supported_bridges and f"{target_chain}_{source_chain}" not in self.supported_bridges:
            logger.error(f"Aucun bridge supporté entre {source_chain} et {target_chain}")
            return
        
        self.monitored_pairs.add(pair_key)
        logger.info(f"Ajout de la paire {pair_key} aux paires surveillées")
    
    async def remove_monitored_pair(self, token_symbol: str, source_chain: str, target_chain: str):
        """
        Retire une paire de la surveillance.
        
        Args:
            token_symbol: Symbole du token (ex: "BTC/USDT")
            source_chain: Chaîne source
            target_chain: Chaîne cible
        """
        pair_key = f"{token_symbol}:{source_chain}:{target_chain}"
        
        if pair_key not in self.monitored_pairs:
            logger.warning(f"La paire {pair_key} n'est pas surveillée")
            return
        
        self.monitored_pairs.remove(pair_key)
        logger.info(f"Retrait de la paire {pair_key} des paires surveillées")
    
    async def get_monitored_pairs(self) -> List[Dict[str, str]]:
        """
        Obtient la liste des paires surveillées.
        
        Returns:
            Liste des paires surveillées
        """
        result = []
        
        for pair_key in self.monitored_pairs:
            token_symbol, source_chain, target_chain = pair_key.split(":")
            result.append({
                "token_symbol": token_symbol,
                "source_chain": source_chain,
                "target_chain": target_chain
            })
        
        return result
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Obtient les statistiques d'arbitrage.
        
        Returns:
            Statistiques d'arbitrage
        """
        return self.stats
    
    async def _monitoring_loop(self):
        """Boucle principale de surveillance des opportunités d'arbitrage."""
        logger.info("Démarrage de la boucle de surveillance d'arbitrage cross-chain")
        
        while self.running:
            try:
                # Vérifier chaque paire surveillée
                for pair_key in self.monitored_pairs:
                    token_symbol, source_chain, target_chain = pair_key.split(":")
                    
                    # Vérifier que les clients blockchain sont disponibles
                    if source_chain not in self.blockchain_clients or target_chain not in self.blockchain_clients:
                        logger.warning(f"Client blockchain non disponible pour {source_chain} ou {target_chain}")
                        continue
                    
                    # Vérifier l'opportunité d'arbitrage
                    try:
                        opportunity = await self._check_arbitrage_opportunity(
                            token_symbol, source_chain, target_chain
                        )
                        
                        if opportunity:
                            self.stats["opportunities_found"] += 1
                            logger.info(f"Opportunité d'arbitrage trouvée: {opportunity}")
                            
                            # Exécuter l'arbitrage si le profit est supérieur au seuil
                            if opportunity["profit_percent"] >= self.min_profit_threshold * 100:
                                asyncio.create_task(self._execute_arbitrage(opportunity))
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la vérification de l'opportunité d'arbitrage pour {pair_key}: {e}")
                
                # Attendre l'intervalle configuré
                await asyncio.sleep(self.arbitrage_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {e}")
                await asyncio.sleep(10)  # Attendre plus longtemps en cas d'erreur
    
    async def _check_arbitrage_opportunity(
        self, token_symbol: str, source_chain: str, target_chain: str
    ) -> Optional[Dict[str, Any]]:
        """
        Vérifie s'il existe une opportunité d'arbitrage pour une paire donnée.
        
        Args:
            token_symbol: Symbole du token (ex: "BTC/USDT")
            source_chain: Chaîne source
            target_chain: Chaîne cible
            
        Returns:
            Opportunité d'arbitrage ou None si aucune opportunité
        """
        # Obtenir les clients blockchain
        source_client = self.blockchain_clients[source_chain]
        target_client = self.blockchain_clients[target_chain]
        
        # Analyser le symbole du token
        token_parts = token_symbol.split("/")
        if len(token_parts) != 2:
            raise ArbitrageError(f"Format de symbole de token invalide: {token_symbol}")
        
        base_token, quote_token = token_parts
        
        # Obtenir les adresses des tokens pour chaque chaîne
        # Dans une implémentation réelle, vous auriez un registre de tokens
        # Ici, nous utilisons des adresses fictives pour l'exemple
        token_addresses = {
            "sonic": {
                "BTC": "0x...",  # Adresse fictive
                "ETH": "0x...",  # Adresse fictive
                "USDT": "0x...",  # Adresse fictive
                "USDC": "0x..."   # Adresse fictive
            },
            "avalanche": {
                "BTC": "0x...",  # Adresse fictive
                "ETH": "0x...",  # Adresse fictive
                "USDT": "0x...",  # Adresse fictive
                "USDC": "0x..."   # Adresse fictive
            },
            "solana": {
                "BTC": "...",  # Adresse fictive
                "ETH": "...",  # Adresse fictive
                "USDT": "...",  # Adresse fictive
                "USDC": "..."   # Adresse fictive
            }
        }
        
        # Vérifier que les tokens sont supportés sur les deux chaînes
        if base_token not in token_addresses[source_chain] or base_token not in token_addresses[target_chain]:
            logger.warning(f"Token {base_token} non supporté sur {source_chain} ou {target_chain}")
            return None
        
        if quote_token not in token_addresses[source_chain] or quote_token not in token_addresses[target_chain]:
            logger.warning(f"Token {quote_token} non supporté sur {source_chain} ou {target_chain}")
            return None
        
        # Obtenir les prix sur les deux chaînes
        try:
            # Prix sur la chaîne source
            source_price = await source_client.get_token_price(
                token_addresses[source_chain][base_token],
                token_addresses[source_chain][quote_token]
            )
            
            # Prix sur la chaîne cible
            target_price = await target_client.get_token_price(
                token_addresses[target_chain][base_token],
                token_addresses[target_chain][quote_token]
            )
            
            # Calculer la différence de prix
            price_diff = abs(source_price - target_price)
            price_diff_percent = (price_diff / min(source_price, target_price)) * 100
            
            # Déterminer la direction (acheter sur source, vendre sur cible ou vice versa)
            if source_price < target_price:
                direction = "source_to_target"
                buy_price = source_price
                sell_price = target_price
                buy_chain = source_chain
                sell_chain = target_chain
            else:
                direction = "target_to_source"
                buy_price = target_price
                sell_price = source_price
                buy_chain = target_chain
                sell_chain = source_chain
            
            # Calculer le profit potentiel
            # Dans une implémentation réelle, vous prendriez en compte les frais de bridge, slippage, etc.
            bridge_fee = self.bridge_fee_estimation * sell_price
            profit_percent = ((sell_price - buy_price - bridge_fee) / buy_price) * 100
            
            # Créer l'objet d'opportunité
            opportunity = {
                "token_symbol": token_symbol,
                "base_token": base_token,
                "quote_token": quote_token,
                "source_chain": source_chain,
                "target_chain": target_chain,
                "source_price": source_price,
                "target_price": target_price,
                "price_diff": price_diff,
                "price_diff_percent": price_diff_percent,
                "direction": direction,
                "buy_chain": buy_chain,
                "sell_chain": sell_chain,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "bridge_fee": bridge_fee,
                "profit_percent": profit_percent,
                "timestamp": time.time()
            }
            
            # Utiliser l'analyseur de marché IA si disponible
            if self.ai_available and self.market_analyzer:
                ai_analysis = await self.market_analyzer.analyze_arbitrage_opportunity(opportunity)
                opportunity["ai_analysis"] = ai_analysis
                
                # Ajuster le profit en fonction de l'analyse IA
                if "adjusted_profit_percent" in ai_analysis:
                    opportunity["profit_percent"] = ai_analysis["adjusted_profit_percent"]
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des prix pour {token_symbol}: {e}")
            return None
    
    async def _execute_arbitrage(self, opportunity: Dict[str, Any]):
        """
        Exécute un arbitrage cross-chain.
        
        Args:
            opportunity: Opportunité d'arbitrage
        """
        # Générer un ID unique pour cet arbitrage
        arbitrage_id = f"{opportunity['token_symbol']}:{opportunity['source_chain']}:{opportunity['target_chain']}:{int(time.time())}"
        
        # Ajouter aux arbitrages actifs
        self.active_arbitrages.add(arbitrage_id)
        
        try:
            logger.info(f"Exécution de l'arbitrage {arbitrage_id}: {opportunity['direction']} "
                      f"pour {opportunity['token_symbol']} avec profit {opportunity['profit_percent']:.2f}%")
            
            # Déterminer le montant de l'arbitrage
            # Dans une implémentation réelle, vous calculeriez cela en fonction des soldes disponibles, etc.
            trade_amount_usd = min(self.max_arbitrage_amount_usd, 100)  # Montant d'exemple
            
            # Convertir en montant de token
            token_amount = trade_amount_usd / opportunity["buy_price"]
            
            # Exécuter l'arbitrage en fonction de la direction
            if opportunity["direction"] == "source_to_target":
                # Acheter sur la chaîne source
                source_client = self.blockchain_clients[opportunity["buy_chain"]]
                target_client = self.blockchain_clients[opportunity["sell_chain"]]
                
                # Dans une implémentation réelle, vous exécuteriez ces étapes :
                # 1. Acheter le token sur la chaîne source
                # 2. Bridger le token vers la chaîne cible
                # 3. Vendre le token sur la chaîne cible
                
                # Simuler un arbitrage réussi
                await asyncio.sleep(2)  # Simuler le temps d'exécution
                
                logger.info(f"Arbitrage {arbitrage_id} terminé avec succès")
                
                # Mettre à jour les statistiques
                self.stats["arbitrages_executed"] += 1
                profit_usd = trade_amount_usd * (opportunity["profit_percent"] / 100)
                self.stats["total_profit_usd"] += profit_usd
                
            else:  # target_to_source
                # Acheter sur la chaîne cible
                target_client = self.blockchain_clients[opportunity["buy_chain"]]
                source_client = self.blockchain_clients[opportunity["sell_chain"]]
                
                # Dans une implémentation réelle, vous exécuteriez ces étapes :
                # 1. Acheter le token sur la chaîne cible
                # 2. Bridger le token vers la chaîne source
                # 3. Vendre le token sur la chaîne source
                
                # Simuler un arbitrage réussi
                await asyncio.sleep(2)  # Simuler le temps d'exécution
                
                logger.info(f"Arbitrage {arbitrage_id} terminé avec succès")
                
                # Mettre à jour les statistiques
                self.stats["arbitrages_executed"] += 1
                profit_usd = trade_amount_usd * (opportunity["profit_percent"] / 100)
                self.stats["total_profit_usd"] += profit_usd
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'arbitrage {arbitrage_id}: {e}")
            self.stats["failed_arbitrages"] += 1
        
        finally:
            # Retirer des arbitrages actifs
            self.active_arbitrages.remove(arbitrage_id)
    
    async def _get_best_bridge(self, source_chain: str, target_chain: str, token: str) -> str:
        """
        Détermine le meilleur bridge à utiliser entre deux chaînes.
        
        Args:
            source_chain: Chaîne source
            target_chain: Chaîne cible
            token: Token à bridger
            
        Returns:
            Nom du meilleur bridge
        """
        # Obtenir les bridges disponibles
        bridge_key = f"{source_chain}_{target_chain}"
        if bridge_key in self.supported_bridges:
            bridges = self.supported_bridges[bridge_key]
        else:
            bridge_key = f"{target_chain}_{source_chain}"
            if bridge_key in self.supported_bridges:
                bridges = self.supported_bridges[bridge_key]
            else:
                raise ArbitrageError(f"Aucun bridge supporté entre {source_chain} et {target_chain}")
        
        # Dans une implémentation réelle, vous compareriez les frais, la vitesse, etc.
        # Pour cet exemple, nous retournons simplement le premier bridge
        return bridges[0] 