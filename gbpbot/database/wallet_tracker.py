"""
Wallet Tracker for Smart Money Identification

This module tracks wallet behaviors across multiple blockchains to identify smart money,
diamond hands, and paper hands. It maintains a database of wallet behaviors and analyzes
transaction patterns to determine which wallets have a history of successful trades.
"""

import os
import json
import time
import sqlite3
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime, timedelta
import aiohttp
import asyncio

from gbpbot.utils.logger import setup_logger
from gbpbot.utils.cache_manager import CacheManager

class WalletTracker:
    """
    Tracks and analyzes wallet behaviors across multiple blockchains
    to identify smart money, diamond hands, and paper hands.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the wallet tracker
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db_path = config.get("database", {}).get("path", "data/wallets.db")
        
        # Configure logger
        self.logger = setup_logger("WalletTracker", logging.INFO)
        self.logger.info("Initializing Wallet Tracker")
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        
        # Cache for frequently accessed data
        self.cache = CacheManager(
            max_size=1000, 
            ttl=config.get("cache", {}).get("wallet_cache_ttl", 3600)
        )
        
        # Wallet classification thresholds
        self.whale_min_holdings_usd = config.get("analysis", {}).get("whale_tracking", {}).get("min_holdings_usd", 50000)
        self.min_transactions = config.get("analysis", {}).get("whale_tracking", {}).get("min_transactions", 5)
        self.successful_exit_rate = config.get("analysis", {}).get("whale_tracking", {}).get("successful_exit_rate", 70)
        
        # Define diamond hands holding time
        self.diamond_hands_hours = config.get("analysis", {}).get("diamond_hands_min_hours", 48)
        
        # Define paper hands max holding time
        self.paper_hands_minutes = config.get("analysis", {}).get("paper_hands_max_minutes", 5)
        
        self.logger.info("Wallet Tracker initialized")
        
    def _initialize_database(self):
        """Initialize SQLite database for wallet tracking"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create wallets table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                blockchain TEXT NOT NULL,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                total_trades INTEGER DEFAULT 0,
                successful_trades INTEGER DEFAULT 0,
                paper_hands_count INTEGER DEFAULT 0,
                diamond_hands_count INTEGER DEFAULT 0,
                avg_holding_time_minutes REAL DEFAULT 0,
                total_profit_usd REAL DEFAULT 0,
                max_holdings_usd REAL DEFAULT 0,
                score INTEGER DEFAULT 50,
                classification TEXT DEFAULT 'unknown'
            )
            ''')
            
            # Create transactions table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                blockchain TEXT NOT NULL,
                token_address TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                usd_value REAL,
                timestamp TIMESTAMP NOT NULL,
                block_number INTEGER,
                tx_hash TEXT,
                exit_timestamp TIMESTAMP,
                exit_tx_hash TEXT,
                exit_usd_value REAL,
                profit_usd REAL,
                holding_time_minutes REAL,
                is_profitable BOOLEAN,
                FOREIGN KEY (wallet_address) REFERENCES wallets(address)
            )
            ''')
            
            # Create token involvement table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_involvement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                blockchain TEXT NOT NULL,
                smart_money_count INTEGER DEFAULT 0,
                paper_hands_count INTEGER DEFAULT 0,
                diamond_hands_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP
            )
            ''')
            
            # Create indexes for performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_wallet_blockchain ON wallets (blockchain)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_token ON transactions (token_address)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_wallet ON transactions (wallet_address)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_token_involvement ON token_involvement (token_address, blockchain)')
            
            self.conn.commit()
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise
            
    async def record_transaction(self, wallet_address: str, blockchain: str, 
                                token_address: str, transaction_type: str,
                                amount: float, usd_value: float, 
                                timestamp: str, block_number: int = None,
                                tx_hash: str = None) -> bool:
        """
        Record a wallet transaction
        
        Args:
            wallet_address: Wallet address
            blockchain: Blockchain name
            token_address: Token address
            transaction_type: Transaction type (buy/sell)
            amount: Token amount
            usd_value: USD value of transaction
            timestamp: ISO format timestamp
            block_number: Block number (optional)
            tx_hash: Transaction hash (optional)
            
        Returns:
            bool: Success status
        """
        try:
            # Ensure wallet exists in wallet table
            await self._ensure_wallet_exists(wallet_address, blockchain)
            
            # Record transaction
            self.cursor.execute('''
            INSERT INTO transactions (
                wallet_address, blockchain, token_address, transaction_type, 
                amount, usd_value, timestamp, block_number, tx_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                wallet_address, blockchain, token_address, transaction_type,
                amount, usd_value, timestamp, block_number, tx_hash
            ))
            
            # If this is a sell transaction, update the corresponding buy transaction
            if transaction_type.lower() == 'sell':
                await self._update_buy_transaction(wallet_address, token_address, timestamp, usd_value, tx_hash)
                
            # Update wallet statistics
            await self._update_wallet_stats(wallet_address)
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording transaction for {wallet_address}: {str(e)}")
            return False
            
    async def _ensure_wallet_exists(self, wallet_address: str, blockchain: str):
        """
        Ensure wallet exists in wallet table
        
        Args:
            wallet_address: Wallet address
            blockchain: Blockchain name
        """
        current_time = datetime.now().isoformat()
        
        self.cursor.execute('SELECT address FROM wallets WHERE address = ?', (wallet_address,))
        if not self.cursor.fetchone():
            self.cursor.execute('''
            INSERT INTO wallets (address, blockchain, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            ''', (wallet_address, blockchain, current_time, current_time))
        else:
            self.cursor.execute('''
            UPDATE wallets SET last_seen = ? WHERE address = ?
            ''', (current_time, wallet_address))
            
    async def _update_buy_transaction(self, wallet_address: str, token_address: str, 
                                    sell_timestamp: str, exit_usd_value: float,
                                    exit_tx_hash: str):
        """
        Update the corresponding buy transaction when a sell occurs
        
        Args:
            wallet_address: Wallet address
            token_address: Token address
            sell_timestamp: Sell timestamp
            exit_usd_value: Exit USD value
            exit_tx_hash: Exit transaction hash
        """
        # Find the most recent buy transaction without an exit timestamp
        self.cursor.execute('''
        SELECT id, usd_value, timestamp FROM transactions
        WHERE wallet_address = ? AND token_address = ? AND transaction_type = 'buy' AND exit_timestamp IS NULL
        ORDER BY timestamp DESC LIMIT 1
        ''', (wallet_address, token_address))
        
        buy_transaction = self.cursor.fetchone()
        if buy_transaction:
            buy_id, buy_usd_value, buy_timestamp = buy_transaction
            
            # Calculate profit and holding time
            buy_time = datetime.fromisoformat(buy_timestamp)
            sell_time = datetime.fromisoformat(sell_timestamp)
            holding_time_minutes = (sell_time - buy_time).total_seconds() / 60
            
            profit_usd = exit_usd_value - buy_usd_value
            is_profitable = profit_usd > 0
            
            # Update the buy transaction
            self.cursor.execute('''
            UPDATE transactions SET 
                exit_timestamp = ?,
                exit_tx_hash = ?,
                exit_usd_value = ?,
                profit_usd = ?,
                holding_time_minutes = ?,
                is_profitable = ?
            WHERE id = ?
            ''', (
                sell_timestamp, exit_tx_hash, exit_usd_value,
                profit_usd, holding_time_minutes, is_profitable, buy_id
            ))
            
    async def _update_wallet_stats(self, wallet_address: str):
        """
        Update wallet statistics based on transaction history
        
        Args:
            wallet_address: Wallet address
        """
        # Get all completed transactions (buys with sells)
        self.cursor.execute('''
        SELECT 
            holding_time_minutes, 
            is_profitable, 
            profit_usd, 
            usd_value
        FROM transactions
        WHERE wallet_address = ? AND transaction_type = 'buy' AND exit_timestamp IS NOT NULL
        ''', (wallet_address,))
        
        transactions = self.cursor.fetchall()
        
        if not transactions:
            return
            
        # Calculate statistics
        total_trades = len(transactions)
        successful_trades = sum(1 for t in transactions if t[1])  # is_profitable
        total_profit_usd = sum(t[2] for t in transactions if t[2] is not None)  # profit_usd
        max_holdings_usd = max(t[3] for t in transactions if t[3] is not None)  # usd_value
        
        # Calculate average holding time
        holding_times = [t[0] for t in transactions if t[0] is not None]
        avg_holding_time_minutes = sum(holding_times) / len(holding_times) if holding_times else 0
        
        # Count paper hands vs diamond hands behaviors
        paper_hands_count = sum(1 for t in transactions if t[0] is not None and t[0] < self.paper_hands_minutes)
        diamond_hands_count = sum(1 for t in transactions if t[0] is not None and t[0] > self.diamond_hands_hours * 60)
        
        # Determine classification
        classification = self._classify_wallet(
            total_trades, 
            successful_trades, 
            total_profit_usd, 
            max_holdings_usd,
            paper_hands_count,
            diamond_hands_count
        )
        
        # Calculate score (0-100)
        score = self._calculate_wallet_score(
            total_trades,
            successful_trades,
            total_profit_usd,
            max_holdings_usd,
            paper_hands_count,
            diamond_hands_count,
            avg_holding_time_minutes
        )
        
        # Update wallet record
        self.cursor.execute('''
        UPDATE wallets SET 
            total_trades = ?,
            successful_trades = ?,
            paper_hands_count = ?,
            diamond_hands_count = ?,
            avg_holding_time_minutes = ?,
            total_profit_usd = ?,
            max_holdings_usd = ?,
            score = ?,
            classification = ?
        WHERE address = ?
        ''', (
            total_trades, successful_trades, paper_hands_count, diamond_hands_count,
            avg_holding_time_minutes, total_profit_usd, max_holdings_usd,
            score, classification, wallet_address
        ))
        
        # Invalidate cache
        self.cache.delete(f"wallet_{wallet_address}")
        
    def _classify_wallet(self, total_trades: int, successful_trades: int, 
                       total_profit_usd: float, max_holdings_usd: float,
                       paper_hands_count: int, diamond_hands_count: int) -> str:
        """
        Classify a wallet based on its behavior
        
        Args:
            total_trades: Total number of trades
            successful_trades: Number of profitable trades
            total_profit_usd: Total profit in USD
            max_holdings_usd: Maximum holdings in USD
            paper_hands_count: Number of paper hands behaviors
            diamond_hands_count: Number of diamond hands behaviors
            
        Returns:
            str: Wallet classification
        """
        # Not enough data to classify
        if total_trades < self.min_transactions:
            return "unknown"
            
        # Calculate success rate
        success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Smart money criteria
        is_whale = max_holdings_usd >= self.whale_min_holdings_usd
        is_successful = success_rate >= self.successful_exit_rate
        
        # Behavior analysis
        paper_hands_ratio = paper_hands_count / total_trades if total_trades > 0 else 0
        diamond_hands_ratio = diamond_hands_count / total_trades if total_trades > 0 else 0
        
        # Classification
        if is_whale and is_successful:
            if diamond_hands_ratio > 0.5:
                return "smart_money_diamond"
            return "smart_money"
        elif is_successful:
            if diamond_hands_ratio > 0.5:
                return "successful_diamond"
            return "successful_trader"
        elif paper_hands_ratio > 0.7:
            return "paper_hands"
        elif diamond_hands_ratio > 0.7:
            return "diamond_hands"
        elif total_profit_usd < 0:
            return "losing_trader"
            
        return "average_trader"
        
    def _calculate_wallet_score(self, total_trades: int, successful_trades: int,
                              total_profit_usd: float, max_holdings_usd: float,
                              paper_hands_count: int, diamond_hands_count: int,
                              avg_holding_time_minutes: float) -> int:
        """
        Calculate a wallet score for ranking wallets
        
        Args:
            total_trades: Total number of trades
            successful_trades: Number of profitable trades
            total_profit_usd: Total profit in USD
            max_holdings_usd: Maximum holdings in USD
            paper_hands_count: Number of paper hands behaviors
            diamond_hands_count: Number of diamond hands behaviors
            avg_holding_time_minutes: Average holding time in minutes
            
        Returns:
            int: Wallet score (0-100)
        """
        score = 50  # Start with neutral score
        
        # Not enough data for accurate scoring
        if total_trades < 3:
            return score
            
        # Success rate component (up to +/-30 points)
        success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
        if success_rate >= 80:
            score += 30
        elif success_rate >= 60:
            score += 20
        elif success_rate >= 50:
            score += 10
        elif success_rate <= 20:
            score -= 30
        elif success_rate <= 40:
            score -= 15
            
        # Profit component (up to +20 points)
        if total_profit_usd > 10000:
            score += 20
        elif total_profit_usd > 5000:
            score += 15
        elif total_profit_usd > 1000:
            score += 10
        elif total_profit_usd > 100:
            score += 5
            
        # Whale factor (up to +15 points)
        if max_holdings_usd > 100000:
            score += 15
        elif max_holdings_usd > 50000:
            score += 10
        elif max_holdings_usd > 10000:
            score += 5
            
        # Behavior factor
        paper_hands_ratio = paper_hands_count / total_trades if total_trades > 0 else 0
        diamond_hands_ratio = diamond_hands_count / total_trades if total_trades > 0 else 0
        
        # Paper hands penalty (up to -15 points)
        if paper_hands_ratio > 0.8:
            score -= 15
        elif paper_hands_ratio > 0.6:
            score -= 10
        elif paper_hands_ratio > 0.4:
            score -= 5
            
        # Diamond hands bonus (up to +10 points)
        if diamond_hands_ratio > 0.8:
            score += 10
        elif diamond_hands_ratio > 0.5:
            score += 5
            
        # Cap score between 0-100
        return max(0, min(100, score))
        
    async def get_wallet_info(self, wallet_address: str) -> Dict:
        """
        Get comprehensive information about a wallet
        
        Args:
            wallet_address: Wallet address
            
        Returns:
            Dict: Wallet information
        """
        # Check cache first
        cache_key = f"wallet_{wallet_address}"
        cached_info = self.cache.get(cache_key)
        if cached_info is not None:
            return cached_info
            
        try:
            # Get wallet details
            self.cursor.execute('''
            SELECT 
                address, blockchain, first_seen, last_seen, total_trades, 
                successful_trades, paper_hands_count, diamond_hands_count,
                avg_holding_time_minutes, total_profit_usd, max_holdings_usd,
                score, classification
            FROM wallets
            WHERE address = ?
            ''', (wallet_address,))
            
            wallet = self.cursor.fetchone()
            if not wallet:
                return {
                    "address": wallet_address,
                    "found": False
                }
                
            # Get recent transactions
            self.cursor.execute('''
            SELECT 
                token_address, transaction_type, amount, usd_value, 
                timestamp, is_profitable, profit_usd
            FROM transactions
            WHERE wallet_address = ?
            ORDER BY timestamp DESC
            LIMIT 10
            ''', (wallet_address,))
            
            transactions = [{
                "token_address": t[0],
                "type": t[1],
                "amount": t[2],
                "usd_value": t[3],
                "timestamp": t[4],
                "is_profitable": t[5],
                "profit_usd": t[6]
            } for t in self.cursor.fetchall()]
            
            # Compile wallet info
            wallet_info = {
                "address": wallet[0],
                "blockchain": wallet[1],
                "first_seen": wallet[2],
                "last_seen": wallet[3],
                "total_trades": wallet[4],
                "successful_trades": wallet[5],
                "paper_hands_count": wallet[6],
                "diamond_hands_count": wallet[7],
                "avg_holding_time_minutes": wallet[8],
                "total_profit_usd": wallet[9],
                "max_holdings_usd": wallet[10],
                "score": wallet[11],
                "classification": wallet[12],
                "success_rate": (wallet[5] / wallet[4] * 100) if wallet[4] > 0 else 0,
                "transactions": transactions,
                "found": True
            }
            
            # Cache the result
            self.cache.set(cache_key, wallet_info, ttl=300)  # 5 minute cache
            
            return wallet_info
            
        except Exception as e:
            self.logger.error(f"Error getting wallet info for {wallet_address}: {str(e)}")
            return {
                "address": wallet_address,
                "found": False,
                "error": str(e)
            }
            
    async def get_top_wallets(self, classification: Optional[str] = None, 
                            min_score: int = 0, limit: int = 20) -> List[Dict]:
        """
        Get top-ranked wallets optionally filtered by classification
        
        Args:
            classification: Optional wallet classification filter
            min_score: Minimum wallet score
            limit: Maximum number of wallets to return
            
        Returns:
            List[Dict]: List of top wallets
        """
        try:
            # Build query based on filters
            query = '''
            SELECT 
                address, blockchain, score, classification, 
                successful_trades, total_trades, total_profit_usd
            FROM wallets
            WHERE score >= ?
            '''
            
            params = [min_score]
            
            if classification:
                query += ' AND classification = ?'
                params.append(classification)
                
            query += ' ORDER BY score DESC LIMIT ?'
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            wallets = [{
                "address": w[0],
                "blockchain": w[1],
                "score": w[2],
                "classification": w[3],
                "successful_trades": w[4],
                "total_trades": w[5],
                "total_profit_usd": w[6],
                "success_rate": (w[4] / w[5] * 100) if w[5] > 0 else 0
            } for w in self.cursor.fetchall()]
            
            return wallets
            
        except Exception as e:
            self.logger.error(f"Error getting top wallets: {str(e)}")
            return []
            
    async def check_smart_money_involvement(self, token_address: str, blockchain: str) -> bool:
        """
        Check if smart money wallets are involved with a token
        
        Args:
            token_address: Token address
            blockchain: Blockchain name
            
        Returns:
            bool: True if smart money is involved
        """
        # Check cache
        cache_key = f"smart_money_{token_address}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        try:
            # Get wallets that traded this token
            self.cursor.execute('''
            SELECT DISTINCT w.address, w.score, w.classification
            FROM transactions t
            JOIN wallets w ON t.wallet_address = w.address
            WHERE t.token_address = ? AND t.blockchain = ?
            ''', (token_address, blockchain))
            
            wallets = self.cursor.fetchall()
            
            # Check if any smart money wallets are involved
            smart_money_involved = any(
                w[2] in ['smart_money', 'smart_money_diamond'] or w[1] >= 80
                for w in wallets
            )
            
            # Update token involvement record
            await self._update_token_involvement(token_address, blockchain, wallets)
            
            # Cache the result
            self.cache.set(cache_key, smart_money_involved, ttl=300)
            
            return smart_money_involved
            
        except Exception as e:
            self.logger.error(f"Error checking smart money involvement for {token_address}: {str(e)}")
            return False
            
    async def _update_token_involvement(self, token_address: str, blockchain: str, wallets: List[Tuple]):
        """
        Update token involvement metrics
        
        Args:
            token_address: Token address
            blockchain: Blockchain name
            wallets: List of wallet data tuples (address, score, classification)
        """
        # Count wallet types
        smart_money_count = sum(1 for w in wallets if w[2] in ['smart_money', 'smart_money_diamond'] or w[1] >= 80)
        paper_hands_count = sum(1 for w in wallets if w[2] == 'paper_hands')
        diamond_hands_count = sum(1 for w in wallets if 'diamond' in w[2])
        
        # Check if token exists in involvement table
        self.cursor.execute('''
        SELECT id FROM token_involvement
        WHERE token_address = ? AND blockchain = ?
        ''', (token_address, blockchain))
        
        token_record = self.cursor.fetchone()
        current_time = datetime.now().isoformat()
        
        if token_record:
            # Update existing record
            self.cursor.execute('''
            UPDATE token_involvement SET
                smart_money_count = ?,
                paper_hands_count = ?,
                diamond_hands_count = ?,
                last_updated = ?
            WHERE token_address = ? AND blockchain = ?
            ''', (
                smart_money_count, paper_hands_count, diamond_hands_count,
                current_time, token_address, blockchain
            ))
        else:
            # Create new record
            self.cursor.execute('''
            INSERT INTO token_involvement (
                token_address, blockchain, smart_money_count,
                paper_hands_count, diamond_hands_count, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                token_address, blockchain, smart_money_count,
                paper_hands_count, diamond_hands_count, current_time
            ))
            
        self.conn.commit()
        
    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
            
    def __del__(self):
        """Destructor to ensure database is closed"""
        self.close()

    # Additional methods for wallet analysis could be added here 