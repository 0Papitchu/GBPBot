from typing import Dict, List, Optional, Set
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import asyncio
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class WhaleTransaction:
    """Represents a whale transaction"""
    token_address: str
    wallet_address: str
    transaction_hash: str
    timestamp: datetime
    amount: float
    type: str  # 'buy' or 'sell'
    price_impact: float
    is_contract: bool

class WhaleTracker:
    def __init__(self, blockchain_client, price_feed):
        """
        Initialize whale tracker
        
        Args:
            blockchain_client: Blockchain client instance
            price_feed: Price feed instance
        """
        self.blockchain = blockchain_client
        self.price_feed = price_feed
        
        # Store whale wallets and their transactions
        self.whale_wallets: Set[str] = set()
        self.whale_transactions: Dict[str, List[WhaleTransaction]] = defaultdict(list)
        
        # Track whale positions
        self.whale_positions: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Configuration
        self.config = {
            "min_whale_amount": 10,  # Minimum amount in AVAX to be considered whale
            "min_whale_holding": 1,  # Minimum % of total supply to be considered whale
            "max_transaction_age": 24 * 3600,  # Maximum age of transactions to keep (24 hours)
            "scan_interval": 10,  # Seconds between scans
            "price_impact_threshold": 2.0,  # Minimum price impact % to track
            "suspicious_contract_patterns": [
                "bot",
                "sniper",
                "arbitrage",
                "sandwich"
            ]
        }
    
    async def start_monitoring(self):
        """Start monitoring whale activities"""
        logger.info("🐋 Starting whale activity monitoring")
        
        while True:
            try:
                # Scan for new whale transactions
                await self._scan_new_transactions()
                
                # Update whale positions
                await self._update_whale_positions()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Wait before next scan
                await asyncio.sleep(self.config["scan_interval"])
                
            except Exception as e:
                logger.error(f"Error in whale monitoring: {str(e)}")
                await asyncio.sleep(self.config["scan_interval"])
    
    async def get_recent_activity(self, token_address: str) -> List[Dict]:
        """
        Get recent whale activity for a token
        
        Args:
            token_address: Token address to check
            
        Returns:
            List of recent whale transactions
        """
        try:
            recent_txs = []
            current_time = datetime.now()
            
            # Get transactions from last hour
            for tx in self.whale_transactions.get(token_address, []):
                if (current_time - tx.timestamp).total_seconds() <= 3600:
                    recent_txs.append({
                        "type": tx.type,
                        "amount": tx.amount,
                        "price_impact": tx.price_impact,
                        "timestamp": tx.timestamp,
                        "is_contract": tx.is_contract
                    })
            
            return recent_txs
            
        except Exception as e:
            logger.error(f"Error getting recent whale activity: {str(e)}")
            return []
    
    async def get_whale_sentiment(self, token_address: str) -> Dict:
        """
        Get whale sentiment analysis for a token
        
        Args:
            token_address: Token address to analyze
            
        Returns:
            Dictionary containing whale sentiment metrics
        """
        try:
            # Get recent transactions
            recent_txs = await self.get_recent_activity(token_address)
            
            if not recent_txs:
                return {
                    "sentiment": "neutral",
                    "confidence": 0,
                    "buy_pressure": 0,
                    "sell_pressure": 0,
                    "holding_time": 0
                }
            
            # Calculate metrics
            buy_volume = sum(tx["amount"] for tx in recent_txs if tx["type"] == "buy")
            sell_volume = sum(tx["amount"] for tx in recent_txs if tx["type"] == "sell")
            total_volume = buy_volume + sell_volume
            
            # Calculate pressures
            buy_pressure = buy_volume / total_volume if total_volume > 0 else 0
            sell_pressure = sell_volume / total_volume if total_volume > 0 else 0
            
            # Calculate average holding time
            holding_times = await self._calculate_holding_times(token_address)
            avg_holding_time = np.mean(holding_times) if holding_times else 0
            
            # Determine sentiment
            if buy_pressure > 0.7:
                sentiment = "bullish"
                confidence = buy_pressure
            elif sell_pressure > 0.7:
                sentiment = "bearish"
                confidence = sell_pressure
            else:
                sentiment = "neutral"
                confidence = max(buy_pressure, sell_pressure)
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "buy_pressure": buy_pressure,
                "sell_pressure": sell_pressure,
                "holding_time": avg_holding_time
            }
            
        except Exception as e:
            logger.error(f"Error calculating whale sentiment: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 0,
                "buy_pressure": 0,
                "sell_pressure": 0,
                "holding_time": 0
            }
    
    async def _scan_new_transactions(self):
        """Scan for new whale transactions"""
        try:
            # Get latest block
            latest_block = await self.blockchain.get_latest_block()
            
            # Get transactions from last few blocks
            transactions = await self._get_recent_transactions(latest_block)
            
            for tx in transactions:
                # Check if transaction amount qualifies as whale
                if not self._is_whale_transaction(tx):
                    continue
                
                # Get transaction details
                tx_details = await self._get_transaction_details(tx)
                
                if not tx_details:
                    continue
                
                # Create whale transaction object
                whale_tx = WhaleTransaction(
                    token_address=tx_details["token_address"],
                    wallet_address=tx_details["wallet_address"],
                    transaction_hash=tx["hash"],
                    timestamp=datetime.fromtimestamp(tx["timestamp"]),
                    amount=tx_details["amount"],
                    type=tx_details["type"],
                    price_impact=tx_details["price_impact"],
                    is_contract=tx_details["is_contract"]
                )
                
                # Add to tracking
                self.whale_transactions[tx_details["token_address"]].append(whale_tx)
                self.whale_wallets.add(tx_details["wallet_address"])
                
                # Log significant transactions
                if tx_details["price_impact"] > self.config["price_impact_threshold"]:
                    logger.info(
                        f"🐋 Whale {tx_details['type']}: {tx_details['amount']:.2f} AVAX "
                        f"({tx_details['price_impact']:.2f}% impact) in {tx_details['token_address']}"
                    )
                
        except Exception as e:
            logger.error(f"Error scanning for whale transactions: {str(e)}")
    
    async def _update_whale_positions(self):
        """Update tracked whale positions"""
        try:
            for token_address in self.whale_transactions.keys():
                for wallet in self.whale_wallets:
                    # Get current balance
                    balance = await self._get_token_balance(token_address, wallet)
                    
                    if balance > 0:
                        # Update position
                        self.whale_positions[token_address][wallet] = balance
                    else:
                        # Remove if no balance
                        self.whale_positions[token_address].pop(wallet, None)
                
        except Exception as e:
            logger.error(f"Error updating whale positions: {str(e)}")
    
    def _cleanup_old_data(self):
        """Clean up old transaction data"""
        try:
            current_time = datetime.now()
            max_age = self.config["max_transaction_age"]
            
            # Clean up old transactions
            for token_address in list(self.whale_transactions.keys()):
                self.whale_transactions[token_address] = [
                    tx for tx in self.whale_transactions[token_address]
                    if (current_time - tx.timestamp).total_seconds() <= max_age
                ]
                
                # Remove empty lists
                if not self.whale_transactions[token_address]:
                    del self.whale_transactions[token_address]
            
            # Update whale wallets based on recent transactions
            active_wallets = set()
            for txs in self.whale_transactions.values():
                for tx in txs:
                    active_wallets.add(tx.wallet_address)
            
            self.whale_wallets = active_wallets
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
    
    def _is_whale_transaction(self, transaction: Dict) -> bool:
        """
        Check if a transaction qualifies as a whale transaction
        
        Args:
            transaction: Transaction data
            
        Returns:
            bool: True if whale transaction
        """
        try:
            # Check transaction value
            value = float(transaction.get("value", 0))
            return value >= self.config["min_whale_amount"]
            
        except Exception as e:
            logger.error(f"Error checking whale transaction: {str(e)}")
            return False
    
    async def _get_transaction_details(self, transaction: Dict) -> Optional[Dict]:
        """
        Get detailed information about a transaction
        
        Args:
            transaction: Transaction data
            
        Returns:
            Dictionary with transaction details or None
        """
        try:
            # Get token transfer details
            token_address = await self._get_token_address(transaction)
            
            if not token_address:
                return None
            
            # Get transaction type and amount
            tx_type = await self._determine_transaction_type(transaction)
            amount = float(transaction.get("value", 0))
            
            # Calculate price impact
            price_impact = await self._calculate_price_impact(token_address, amount, tx_type)
            
            # Check if sender is a contract
            is_contract = await self._is_contract_address(transaction["from"])
            
            return {
                "token_address": token_address,
                "wallet_address": transaction["from"],
                "type": tx_type,
                "amount": amount,
                "price_impact": price_impact,
                "is_contract": is_contract
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {str(e)}")
            return None
    
    async def _calculate_holding_times(self, token_address: str) -> List[float]:
        """
        Calculate holding times for whale positions
        
        Args:
            token_address: Token address to analyze
            
        Returns:
            List of holding times in hours
        """
        try:
            holding_times = []
            
            # Get buy transactions
            buy_txs = [tx for tx in self.whale_transactions.get(token_address, [])
                      if tx.type == "buy"]
            
            for buy_tx in buy_txs:
                # Find next sell from same wallet
                sell_tx = next(
                    (tx for tx in self.whale_transactions.get(token_address, [])
                     if tx.type == "sell" and 
                     tx.wallet_address == buy_tx.wallet_address and
                     tx.timestamp > buy_tx.timestamp),
                    None
                )
                
                if sell_tx:
                    holding_time = (sell_tx.timestamp - buy_tx.timestamp).total_seconds() / 3600
                    holding_times.append(holding_time)
            
            return holding_times
            
        except Exception as e:
            logger.error(f"Error calculating holding times: {str(e)}")
            return []
    
    async def _get_recent_transactions(self, latest_block: Dict) -> List[Dict]:
        """Get recent transactions from blockchain"""
        # TODO: Implement transaction retrieval
        return []
    
    async def _get_token_address(self, transaction: Dict) -> Optional[str]:
        """Get token address from transaction"""
        # TODO: Implement token address extraction
        return None
    
    async def _determine_transaction_type(self, transaction: Dict) -> str:
        """Determine if transaction is buy or sell"""
        # TODO: Implement transaction type detection
        return "buy"
    
    async def _calculate_price_impact(self, token_address: str, amount: float, tx_type: str) -> float:
        """Calculate price impact of transaction"""
        # TODO: Implement price impact calculation
        return 0.0
    
    async def _is_contract_address(self, address: str) -> bool:
        """Check if address is a contract"""
        # TODO: Implement contract detection
        return False
    
    async def _get_token_balance(self, token_address: str, wallet_address: str) -> float:
        """Get token balance for wallet"""
        # TODO: Implement balance checking
        return 0.0 