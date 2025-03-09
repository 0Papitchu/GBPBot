from typing import Dict, List, Optional
import random
from datetime import datetime, timedelta
from loguru import logger
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path

# Importer notre nouveau chargeur de wallets
from gbpbot.utils.wallet_loader import get_wallets

@dataclass
class WalletConfig:
    """Configuration for a wallet"""
    address: str
    private_key: str
    chain: str
    last_used: datetime
    cooldown_minutes: int
    transaction_count: int

class StealthMode:
    def __init__(self, config_path: str = "config/wallets.json"):
        """
        Initialize stealth mode manager
        
        Args:
            config_path: Path to wallet configuration file
        """
        self.config_path = Path(config_path)
        self.wallets: Dict[str, WalletConfig] = {}
        self.current_wallet: Optional[WalletConfig] = None
        
        # Configuration améliorée de la furtivité
        self.config = {
            "min_delay_ms": 50,  # Réduit pour plus de réactivité
            "max_delay_ms": 1000,  # Réduit pour plus de réactivité
            "wallet_rotation_threshold": 25,  # Rotation plus fréquente
            "min_cooldown_minutes": 15,  # Réduit pour plus de réactivité
            "max_cooldown_minutes": 60,  # Réduit pour plus de réactivité
            "transaction_variance": 0.25,  # Augmenté pour plus de variation
            "gas_price_variance": 0.15,  # Augmenté pour plus de variation
            "nonce_randomization": True,  # Randomisation des nonces
            "data_padding": True,  # Ajout de données aléatoires
            "smart_timing": True,  # Timing intelligent des transactions
            "signature_variance": True,  # Variation des signatures
            "max_consecutive_trades": 3,  # Maximum de trades consécutifs
            "min_block_interval": 2,  # Intervalle minimum entre les blocs
        }
        
        # Statistiques avancées
        self.stats = {
            "total_transactions": 0,
            "detected_patterns": 0,
            "wallet_rotations": 0,
            "average_delay": 0,
            "pattern_alerts": [],
            "last_block_used": None,
            "consecutive_trades": 0
        }
        
        self._load_wallets()
    
    def _load_wallets(self):
        """Charger les wallets depuis le système sécurisé"""
        try:
            # Utiliser notre nouveau chargeur de wallets
            wallet_data = get_wallets()
            
            if not wallet_data:
                logger.warning(f"Aucun wallet valide trouvé via le chargeur sécurisé")
                return
            
            for wallet in wallet_data:
                self.wallets[wallet["address"]] = WalletConfig(
                    address=wallet["address"],
                    private_key=wallet["private_key"],
                    chain=wallet["chain"],
                    last_used=datetime.now() - timedelta(hours=24),
                    cooldown_minutes=random.randint(
                        self.config["min_cooldown_minutes"],
                        self.config["max_cooldown_minutes"]
                    ),
                    transaction_count=0
                )
            
            logger.info(f"Chargé {len(self.wallets)} wallets avec le système sécurisé")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des wallets: {str(e)}")
    
    async def get_active_wallet(self, chain: str) -> Optional[WalletConfig]:
        """
        Get an active wallet for the specified chain
        
        Args:
            chain: Blockchain to use (e.g., 'avax', 'eth')
            
        Returns:
            Active wallet configuration or None
        """
        try:
            # Check if current wallet can be reused
            if self.current_wallet and self.current_wallet.chain == chain:
                if self._can_reuse_wallet(self.current_wallet):
                    return self.current_wallet
            
            # Find new wallet
            available_wallets = [
                w for w in self.wallets.values()
                if w.chain == chain and self._can_use_wallet(w)
            ]
            
            if not available_wallets:
                logger.warning(f"No available wallets for chain {chain}")
                return None
            
            # Select random wallet
            self.current_wallet = random.choice(available_wallets)
            self.current_wallet.last_used = datetime.now()
            self.current_wallet.transaction_count = 0
            
            logger.info(f"Selected new wallet: {self.current_wallet.address[:8]}...")
            return self.current_wallet
            
        except Exception as e:
            logger.error(f"Error getting active wallet: {str(e)}")
            return None
    
    def _can_reuse_wallet(self, wallet: WalletConfig) -> bool:
        """Check if wallet can be reused"""
        if wallet.transaction_count >= self.config["wallet_rotation_threshold"]:
            return False
        return True
    
    def _can_use_wallet(self, wallet: WalletConfig) -> bool:
        """Check if wallet is available for use"""
        cooldown_passed = (datetime.now() - wallet.last_used).total_seconds() / 60
        return cooldown_passed >= wallet.cooldown_minutes
    
    async def add_transaction_delay(self):
        """Ajoute un délai intelligent avant la transaction"""
        try:
            if self.config["smart_timing"]:
                # Calcul du délai basé sur l'activité récente
                base_delay = random.randint(
                    self.config["min_delay_ms"],
                    self.config["max_delay_ms"]
                )
                
                # Ajustement selon les patterns détectés
                if self.stats["detected_patterns"] > 0:
                    base_delay *= (1 + (self.stats["detected_patterns"] * 0.1))
                
                # Ajustement selon les trades consécutifs
                if self.stats["consecutive_trades"] > 1:
                    base_delay *= self.stats["consecutive_trades"]
                
                await asyncio.sleep(base_delay / 1000)
                
                # Mise à jour des stats
                self.stats["average_delay"] = (
                    (self.stats["average_delay"] * self.stats["total_transactions"] + base_delay) /
                    (self.stats["total_transactions"] + 1)
                )
                
        except Exception as e:
            logger.error(f"Error adding transaction delay: {str(e)}")
            await asyncio.sleep(random.randint(100, 500) / 1000)
            
    def randomize_transaction_data(self, tx_data: Dict) -> Dict:
        """Randomise les données de la transaction pour la rendre unique"""
        try:
            if not self.config["data_padding"]:
                return tx_data
                
            # Ajout de données aléatoires
            if "data" in tx_data:
                random_bytes = bytes([random.randint(0, 255) for _ in range(random.randint(1, 32))])
                tx_data["data"] = tx_data["data"] + random_bytes.hex()
            
            # Variation du gas limit
            if "gas" in tx_data:
                variance = random.uniform(-0.05, 0.05)
                tx_data["gas"] = int(tx_data["gas"] * (1 + variance))
            
            # Randomisation du nonce si activé
            if self.config["nonce_randomization"] and "nonce" in tx_data:
                tx_data["nonce"] += random.randint(0, 2)
                
            return tx_data
            
        except Exception as e:
            logger.error(f"Error randomizing transaction data: {str(e)}")
            return tx_data
            
    def _can_execute_trade(self) -> bool:
        """Vérifie si un trade peut être exécuté selon les règles de furtivité"""
        try:
            # Vérifier le nombre de trades consécutifs
            if self.stats["consecutive_trades"] >= self.config["max_consecutive_trades"]:
                logger.warning("Maximum consecutive trades reached, cooling down")
                return False
                
            # Vérifier l'intervalle entre les blocs
            if (self.stats["last_block_used"] and 
                self.current_block - self.stats["last_block_used"] < self.config["min_block_interval"]):
                return False
                
            # Vérifier les patterns de détection
            if self.stats["detected_patterns"] > 3:
                logger.warning("Too many detection patterns, increasing stealth")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking trade execution: {str(e)}")
            return False
    
    def randomize_amount(self, base_amount: float) -> float:
        """
        Add random variance to transaction amount
        
        Args:
            base_amount: Original transaction amount
            
        Returns:
            Modified amount with random variance
        """
        variance = random.uniform(
            -self.config["transaction_variance"],
            self.config["transaction_variance"]
        )
        return base_amount * (1 + variance)
    
    def randomize_gas_price(self, base_gas_price: int) -> int:
        """
        Add random variance to gas price
        
        Args:
            base_gas_price: Original gas price
            
        Returns:
            Modified gas price with random variance
        """
        variance = random.uniform(
            -self.config["gas_price_variance"],
            self.config["gas_price_variance"]
        )
        return int(base_gas_price * (1 + variance))
    
    def update_wallet_stats(self, wallet_address: str):
        """Update wallet statistics after transaction"""
        if wallet_address in self.wallets:
            self.wallets[wallet_address].transaction_count += 1
            self.wallets[wallet_address].last_used = datetime.now() 