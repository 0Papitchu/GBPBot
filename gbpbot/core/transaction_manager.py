from typing import Dict, Optional
from web3 import Web3
from loguru import logger
import time
from eth_account.account import Account
import asyncio

class TransactionManager:
    """Gestionnaire de transactions optimisé pour l'arbitrage"""
    
    def __init__(self, web3: Web3, account: Account, simulation_mode: bool = False):
        self.web3 = web3
        self.account = account
        self.pending_transactions = {}
        self.nonce = None
        self.simulation_mode = simulation_mode
        
        # Configuration par défaut
        self.max_priority_fee = Web3.to_wei(2, 'gwei')  # 2 GWEI de pourboire max
        self.max_fee_per_gas = Web3.to_wei(50, 'gwei')  # 50 GWEI max total
        self.min_priority_fee = Web3.to_wei(0.1, 'gwei')  # 0.1 GWEI minimum
        self.gas_multiplier = 1.2  # +20% sur l'estimation de gas
        
    async def prepare_transaction(self, to: str, data: bytes, value: int = 0, priority: str = "normal") -> Dict:
        """Prépare une transaction avec gestion optimisée du gas"""
        try:
            # Récupérer le nonce
            if self.nonce is None:
                self.nonce = self.web3.eth.get_transaction_count(self.account.address)
            
            # Récupérer les prix du gas
            base_fee = self.web3.eth.get_block('latest')['baseFeePerGas']
            
            # Ajuster les frais selon la priorité
            if priority == "high":
                priority_fee = min(base_fee * 0.3, self.max_priority_fee)  # 30% du base fee
                max_fee = min(base_fee * 2 + priority_fee, self.max_fee_per_gas)
            elif priority == "low":
                priority_fee = self.min_priority_fee
                max_fee = base_fee * 1.1 + priority_fee  # +10% sur le base fee
            else:  # normal
                priority_fee = min(base_fee * 0.15, self.max_priority_fee)  # 15% du base fee
                max_fee = min(base_fee * 1.5 + priority_fee, self.max_fee_per_gas)
            
            # Construire la transaction
            tx = {
                "from": self.account.address,
                "to": to,
                "value": value,
                "nonce": self.nonce,
                "chainId": self.web3.eth.chain_id,
                "maxPriorityFeePerGas": int(priority_fee),
                "maxFeePerGas": int(max_fee),
                "type": 2  # EIP-1559
            }
            
            # Estimer le gas avec une marge de sécurité
            try:
                estimated_gas = self.web3.eth.estimate_gas(tx)
                tx["gas"] = int(estimated_gas * self.gas_multiplier)
            except Exception as e:
                logger.warning(f"Erreur lors de l'estimation du gas: {str(e)}")
                tx["gas"] = 300000  # Valeur par défaut
            
            return tx
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation de la transaction: {str(e)}")
            raise
            
    async def send_transaction(self, tx: Dict, wait_confirmation: bool = True) -> Optional[str]:
        """
        Envoie une transaction et attend optionnellement sa confirmation
        
        Args:
            tx: Transaction préparée
            wait_confirmation: Attendre la confirmation de la transaction
            
        Returns:
            Hash de la transaction ou None en cas d'échec
        """
        if self.simulation_mode:
            # En mode simulation, on simule une transaction réussie
            logger.info(f"[SIMULATION] Transaction simulée vers {tx.get('to', 'inconnu')}")
            # Générer un faux hash de transaction
            fake_tx_hash = Web3.keccak(text=f"simulation_{time.time()}").hex()
            # Incrémenter le nonce pour les futures transactions
            self.nonce += 1
            return fake_tx_hash
            
        if not self.account:
            logger.error("Impossible d'envoyer une transaction sans compte configuré")
            return None
            
        try:
            # Signer la transaction
            signed_tx = self.account.sign_transaction(tx)
            
            # Envoyer la transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
            
            # Stocker la transaction en attente
            self.pending_transactions[tx_hash] = {
                "timestamp": time.time(),
                "nonce": tx["nonce"],
                "gas_price": tx.get("gasPrice", 0) or tx.get("maxFeePerGas", 0)
            }
            
            # Incrémenter le nonce pour les futures transactions
            self.nonce += 1
            
            logger.info(f"Transaction envoyée: {tx_hash}")
            
            # Attendre la confirmation si demandé
            if wait_confirmation:
                receipt = await self.wait_for_transaction(tx_hash)
                if receipt and receipt.get("status") == 1:
                    logger.success(f"Transaction confirmée: {tx_hash}")
                    return tx_hash
                else:
                    logger.error(f"Transaction échouée: {tx_hash}")
                    return None
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la transaction: {str(e)}")
            return None
            
    async def wait_for_transaction(self, tx_hash: str, timeout: int = 180) -> Dict:
        """
        Attend la confirmation d'une transaction
        
        Args:
            tx_hash: Hash de la transaction
            timeout: Délai d'attente maximum en secondes
            
        Returns:
            Reçu de la transaction ou None en cas d'échec
        """
        if self.simulation_mode:
            # En mode simulation, on retourne un faux reçu de transaction
            logger.info(f"[SIMULATION] Confirmation simulée pour la transaction {tx_hash}")
            return {
                "status": 1,
                "transactionHash": tx_hash,
                "blockNumber": 0,
                "gasUsed": 100000
            }
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    return dict(receipt)
            except Exception as e:
                logger.debug(f"En attente de la confirmation de {tx_hash}: {str(e)}")
            
            await asyncio.sleep(2)
        
        logger.warning(f"Délai d'attente dépassé pour la transaction {tx_hash}")
        return None
            
    async def replace_transaction(self, old_tx_hash: str, new_gas_price: int) -> Optional[str]:
        """
        Remplace une transaction en attente par une nouvelle avec un prix de gas plus élevé
        
        Args:
            old_tx_hash: Hash de la transaction à remplacer
            new_gas_price: Nouveau prix du gas en wei
            
        Returns:
            Hash de la nouvelle transaction ou None en cas d'échec
        """
        if self.simulation_mode:
            # En mode simulation, on simule un remplacement de transaction
            logger.info(f"[SIMULATION] Remplacement simulé de la transaction {old_tx_hash}")
            # Générer un faux hash de transaction
            fake_tx_hash = Web3.keccak(text=f"simulation_replace_{time.time()}").hex()
            return fake_tx_hash
            
        if old_tx_hash not in self.pending_transactions:
            logger.error(f"Transaction {old_tx_hash} non trouvée dans les transactions en attente")
            return None
            
        pending_tx = self.pending_transactions[old_tx_hash]
        
        try:
            # Récupérer la transaction originale
            tx = self.web3.eth.get_transaction(old_tx_hash)
            if not tx:
                logger.error(f"Transaction {old_tx_hash} non trouvée sur la blockchain")
                return None
                
            # Vérifier que la transaction n'est pas déjà confirmée
            receipt = self.web3.eth.get_transaction_receipt(old_tx_hash)
            if receipt:
                logger.warning(f"Transaction {old_tx_hash} déjà confirmée, impossible de la remplacer")
                return None
                
            # Créer une nouvelle transaction avec le même nonce mais un gas price plus élevé
            new_tx = {
                "from": tx["from"],
                "to": tx["to"],
                "value": tx["value"],
                "nonce": tx["nonce"],
                "data": tx["input"],
                "chainId": tx["chainId"]
            }
            
            # Utiliser EIP-1559 si disponible
            if hasattr(tx, "maxFeePerGas"):
                new_tx["maxFeePerGas"] = new_gas_price
                new_tx["maxPriorityFeePerGas"] = min(new_gas_price // 2, self.max_priority_fee)
            else:
                new_tx["gasPrice"] = new_gas_price
                
            # Estimer le gas
            try:
                gas_estimate = self.web3.eth.estimate_gas(new_tx)
                new_tx["gas"] = int(gas_estimate * self.gas_multiplier)
            except Exception as e:
                logger.warning(f"Erreur lors de l'estimation du gas: {str(e)}")
                new_tx["gas"] = tx["gas"]
                
            # Envoyer la nouvelle transaction
            signed_tx = self.account.sign_transaction(new_tx)
            new_tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
            
            logger.info(f"Transaction remplacée: {old_tx_hash} -> {new_tx_hash}")
            
            # Mettre à jour les transactions en attente
            self.pending_transactions[new_tx_hash] = pending_tx
            self.pending_transactions[new_tx_hash]["gas_price"] = new_gas_price
            del self.pending_transactions[old_tx_hash]
            
            return new_tx_hash
            
        except Exception as e:
            logger.error(f"Erreur lors du remplacement de la transaction: {str(e)}")
            return None
            
    def get_optimal_gas_price(self) -> int:
        """Calcule le prix du gas optimal en fonction des conditions du réseau"""
        try:
            # Récupérer les derniers blocks
            latest_block = self.web3.eth.get_block("latest")
            base_fee = latest_block["baseFeePerGas"]
            
            # Calculer la congestion du réseau
            gas_used_percent = latest_block["gasUsed"] / latest_block["gasLimit"]
            
            # Ajuster le prix en fonction de la congestion
            if gas_used_percent > 0.8:  # Réseau très congestionné
                priority_fee = self.max_priority_fee
            elif gas_used_percent > 0.5:  # Congestion moyenne
                priority_fee = self.max_priority_fee * 0.5
            else:  # Faible congestion
                priority_fee = self.min_priority_fee
                
            return base_fee + priority_fee
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul du gas optimal: {str(e)}")
            return self.web3.eth.gas_price  # Fallback sur le prix standard 