#!/usr/bin/env python3
"""
Module pour l'exécution des trades sur les DEX et CEX.
"""

import asyncio
from typing import Dict, Optional
from decimal import Decimal
from web3 import Web3
from eth_account.messages import encode_defunct
from loguru import logger
import time

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.rpc.rpc_manager import RPCManager
from gbpbot.core.monitoring.monitor import BotMonitor
from .cex_executor import CEXTradeExecutor

class TradeExecutor:
    """Gestionnaire principal des trades."""

    def __init__(self):
        """Initialise le TradeExecutor avec la configuration."""
        self.config = ConfigManager().get_config()
        self.rpc_manager = RPCManager()
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_manager.get_best_rpc_url()))
        self.cex_executor = CEXTradeExecutor()
        self.monitor = BotMonitor(self.config)
        
        # Charger le wallet
        self.private_key = self.config["wallet"]["private_key"]
        self.address = self.web3.eth.account.from_key(self.private_key).address
        
        # Métriques de trading
        self.pending_transactions = set()
        self.last_nonce = None
        
        # Démarrer le monitoring
        self.monitor.bot_status['is_running'] = True
        
    async def execute_arbitrage(self, opportunity: Dict) -> bool:
        """
        Exécute une opportunité d'arbitrage.
        
        Args:
            opportunity: Dictionnaire contenant les détails de l'opportunité
            
        Returns:
            bool: True si l'arbitrage a réussi, False sinon
        """
        start_time = time.time()
        trade_info = {
            'status': 'pending',
            'type': 'arbitrage',
            'opportunity': opportunity,
            'start_time': start_time
        }
        
        try:
            # Vérification des conditions de marché sur le DEX
            if not await self._verify_market_conditions(opportunity):
                trade_info.update({
                    'status': 'failed',
                    'reason': 'market_conditions',
                    'end_time': time.time()
                })
                await self.monitor.track_trade(trade_info)
                return False

            # Préparation de la transaction DEX
            tx = await self._prepare_dex_transaction(opportunity)
            if not tx or not self._check_slippage(tx):
                trade_info.update({
                    'status': 'failed',
                    'reason': 'slippage',
                    'end_time': time.time()
                })
                await self.monitor.track_trade(trade_info)
                return False

            # Exécution du trade sur le CEX
            cex_success = await self.cex_executor.execute_trade(opportunity)
            if not cex_success:
                trade_info.update({
                    'status': 'failed',
                    'reason': 'cex_execution',
                    'end_time': time.time()
                })
                await self.monitor.track_trade(trade_info)
                return False

            # Envoi de la transaction DEX
            tx_hash = await self._send_transaction(tx)
            if not tx_hash:
                trade_info.update({
                    'status': 'failed',
                    'reason': 'dex_execution',
                    'end_time': time.time()
                })
                await self.monitor.track_trade(trade_info)
                return False

            # Attente de la confirmation
            success = await self._wait_for_confirmation(tx_hash)
            
            # Mise à jour des métriques
            trade_info.update({
                'status': 'success' if success else 'failed',
                'reason': 'confirmation' if not success else None,
                'end_time': time.time(),
                'duration': time.time() - start_time,
                'tx_hash': tx_hash,
                'gas_used': tx.get('gas', 0),
                'gas_price': Web3.from_wei(tx.get('maxFeePerGas', 0), 'gwei')
            })
            
            # Calculer le profit réel
            if success:
                profit = self._calculate_profit(opportunity, tx)
                trade_info['profit'] = str(profit)
                
            await self.monitor.track_trade(trade_info)
            return success

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'arbitrage: {str(e)}")
            trade_info.update({
                'status': 'failed',
                'reason': 'error',
                'error': str(e),
                'end_time': time.time()
            })
            await self.monitor.track_trade(trade_info)
            return False
            
    async def _verify_market_conditions(self, opportunity: Dict) -> bool:
        """Vérifie que les conditions de marché sont toujours favorables."""
        try:
            # Vérifier que le prix n'a pas trop changé
            current_price = await self._get_current_price(
                opportunity["token_address"],
                opportunity["dex_name"]
            )
            if not current_price:
                await self.monitor.track_error({
                    'type': 'price_fetch',
                    'message': 'Impossible de récupérer le prix actuel'
                })
                return False
                
            price_change = abs(current_price - opportunity["dex_price"]) / opportunity["dex_price"]
            if price_change > self.config["security"]["max_price_change"]:
                await self.monitor.track_error({
                    'type': 'price_change',
                    'message': f"Prix changé de {price_change*100:.2f}%",
                    'change': price_change
                })
                return False
                
            # Vérifier la liquidité actuelle
            current_liquidity = await self._check_current_liquidity(
                opportunity["token_address"],
                opportunity["dex_name"]
            )
            if not current_liquidity or current_liquidity < self.config["arbitrage"]["min_liquidity"]:
                await self.monitor.track_error({
                    'type': 'liquidity',
                    'message': 'Liquidité insuffisante',
                    'current': current_liquidity
                })
                return False
                
            # Mise à jour des métriques de marché
            await self.monitor.update_market_metrics({
                'price': current_price,
                'liquidity': current_liquidity,
                'spread': price_change * 100
            })
                
            return True
            
        except Exception as e:
            await self.monitor.track_error({
                'type': 'market_check',
                'message': str(e)
            })
            return False
            
    async def _prepare_dex_transaction(self, opportunity: Dict) -> Optional[Dict]:
        """Prépare la transaction pour le DEX."""
        try:
            # Obtenir le contrat du router
            router_address = self.config["dex"][opportunity["dex_name"]]["router_address"]
            router_contract = self.web3.eth.contract(
                address=router_address,
                abi=self.config["dex"][opportunity["dex_name"]]["router_abi"]
            )
            
            # Calculer le montant optimal
            amount_in = min(
                Web3.to_wei(self.config["arbitrage"]["max_trade_amount"], 'ether'),
                Web3.to_wei(float(opportunity["liquidity"]) * 0.3, 'ether')  # Max 30% de la liquidité
            )
            
            # Construire la transaction
            nonce = await self._get_next_nonce()
            
            # Préparer les paramètres de la transaction
            tx_params = {
                'from': self.address,
                'nonce': nonce,
                'gas': self.config["arbitrage"]["estimated_gas_limit"],
                'maxFeePerGas': await self._get_max_fee_per_gas(),
                'maxPriorityFeePerGas': await self._get_max_priority_fee(),
            }
            
            # Construire la transaction selon le type d'arbitrage
            if float(opportunity["price_difference"]) > 0:  # Achat sur DEX
                tx = router_contract.functions.swapExactAVAXForTokens(
                    amount_in,  # Amount in
                    0,  # Min amount out (sera calculé avec slippage)
                    [self.config["tokens"]["weth"], opportunity["token_address"]],  # Path
                    self.address,  # To
                    int(time.time()) + 60  # Deadline
                ).build_transaction(tx_params)
            else:  # Vente sur DEX
                tx = router_contract.functions.swapExactTokensForAVAX(
                    amount_in,  # Amount in
                    0,  # Min amount out (sera calculé avec slippage)
                    [opportunity["token_address"], self.config["tokens"]["weth"]],  # Path
                    self.address,  # To
                    int(time.time()) + 60  # Deadline
                ).build_transaction(tx_params)
                
            return tx
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation de la transaction: {str(e)}")
            return None
            
    def _check_slippage(self, tx: Dict) -> bool:
        """Vérifie que le slippage est acceptable."""
        try:
            # Calculer le slippage attendu
            amount_in = tx['value'] if 'value' in tx else tx['amount']
            expected_out = amount_in * float(opportunity["dex_price"])
            min_out = expected_out * (1 - self.config["security"]["max_slippage"])
            
            # Vérifier le montant minimum
            if 'minAmountOut' in tx:
                return tx['minAmountOut'] >= min_out
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du slippage: {str(e)}")
            return False
            
    async def _send_transaction(self, tx: Dict) -> Optional[str]:
        """Envoie la transaction de manière sécurisée."""
        try:
            # Signer la transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            
            # Envoyer la transaction
            tx_hash = await self.rpc_manager.call_rpc(
                "eth_sendRawTransaction",
                [signed_tx.rawTransaction.hex()]
            )
            
            if tx_hash:
                self.pending_transactions.add(tx_hash)
                logger.info(f"Transaction envoyée: {tx_hash}")
                return tx_hash
                
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la transaction: {str(e)}")
            return None
            
    async def _wait_for_confirmation(self, tx_hash: str) -> bool:
        """Attend la confirmation de la transaction."""
        try:
            for _ in range(self.config["security"]["max_confirmation_attempts"]):
                receipt = await self.rpc_manager.call_rpc(
                    "eth_getTransactionReceipt",
                    [tx_hash]
                )
                
                if receipt:
                    if receipt["status"] == "0x1":
                        self.pending_transactions.remove(tx_hash)
                        logger.info(f"Transaction confirmée: {tx_hash}")
                        return True
                    else:
                        logger.error(f"Transaction échouée: {tx_hash}")
                        return False
                        
                await asyncio.sleep(1)
                
            logger.warning(f"Timeout en attendant la confirmation: {tx_hash}")
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de l'attente de confirmation: {str(e)}")
            return False
            
    async def _get_next_nonce(self) -> int:
        """Obtient le prochain nonce valide."""
        try:
            # Obtenir le nonce on-chain
            nonce = await self.rpc_manager.call_rpc(
                "eth_getTransactionCount",
                [self.address, "latest"]
            )
            
            # Mettre à jour le dernier nonce
            if self.last_nonce is None or nonce > self.last_nonce:
                self.last_nonce = nonce
            else:
                self.last_nonce += 1
                
            return self.last_nonce
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du nonce: {str(e)}")
            return 0
            
    async def _get_max_fee_per_gas(self) -> int:
        """Calcule le maxFeePerGas optimal."""
        try:
            base_fee = await self.rpc_manager.call_rpc("eth_baseFee", [])
            priority_fee = await self._get_max_priority_fee()
            
            # Ajouter une marge de 20% au base fee
            max_fee = int(base_fee * 1.2) + priority_fee
            
            # Ne pas dépasser le maximum configuré
            return min(
                max_fee,
                Web3.to_wei(self.config["security"]["max_gas_price"], 'gwei')
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du maxFeePerGas: {str(e)}")
            return Web3.to_wei(50, 'gwei')  # Valeur par défaut sécurisée
            
    async def _get_max_priority_fee(self) -> int:
        """Calcule le maxPriorityFeePerGas optimal."""
        try:
            # Utiliser eth_maxPriorityFeePerGas si disponible
            priority_fee = await self.rpc_manager.call_rpc("eth_maxPriorityFeePerGas", [])
            if priority_fee:
                return int(priority_fee)
                
            # Sinon utiliser une valeur par défaut
            return Web3.to_wei(2, 'gwei')
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du maxPriorityFee: {str(e)}")
            return Web3.to_wei(2, 'gwei')  # Valeur par défaut sécurisée
            
    def _calculate_profit(self, opportunity: Dict, tx: Dict) -> Decimal:
        """Calcule le profit réel d'un trade."""
        try:
            # Calculer le profit brut
            amount_in = Decimal(str(tx.get('value', 0)))
            amount_out = Decimal(str(tx.get('amount_out', 0)))
            
            # Soustraire les frais
            gas_cost = Decimal(str(tx['gas'])) * Decimal(str(tx['maxFeePerGas']))
            total_fees = gas_cost + Decimal(str(self.config['dex'][opportunity['dex_name']]['fee']))
            
            # Calculer le profit net
            profit = amount_out - amount_in - total_fees
            profit_percentage = (profit / amount_in) * Decimal('100')
            
            return profit_percentage
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du profit: {str(e)}")
            return Decimal('0')

    async def close(self):
        """Ferme proprement les connexions."""
        await self.cex_executor.close()
        await self.monitor.close()
        self.monitor.bot_status['is_running'] = False 