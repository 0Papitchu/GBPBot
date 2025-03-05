from typing import Dict, List, Optional, Tuple
import random
from datetime import datetime
from loguru import logger
import numpy as np
from dataclasses import dataclass

@dataclass
class TransactionParams:
    """Parameters for a transaction"""
    amount: float
    slippage: float
    gas_price: int
    gas_limit: int
    nonce: int
    deadline: int

class TransactionObfuscator:
    def __init__(self):
        """Initialize transaction obfuscator"""
        self.config = {
            "amount_variance": (0.05, 0.15),  # 5-15% variance in amounts
            "slippage_variance": (0.01, 0.05),  # 1-5% variance in slippage
            "gas_variance": (0.05, 0.20),  # 5-20% variance in gas
            "min_fragments": 2,
            "max_fragments": 5,
            "time_variance_ms": (100, 2000),  # 0.1-2s variance in timing
            "nonce_offset": (1, 5),  # Random nonce offset
            "deadline_variance": (30, 300)  # 30-300s variance in deadlines
        }
        
        # Track transaction patterns
        self.recent_patterns: List[Dict] = []
        self.pattern_memory = 100  # Remember last 100 transactions
    
    def obfuscate_transaction(self, base_params: TransactionParams) -> List[TransactionParams]:
        """
        Split and obfuscate a transaction into multiple smaller ones
        
        Args:
            base_params: Original transaction parameters
            
        Returns:
            List of modified transaction parameters
        """
        try:
            # Determine number of fragments
            n_fragments = random.randint(
                self.config["min_fragments"],
                self.config["max_fragments"]
            )
            
            # Split amount into random fragments
            amounts = self._split_amount(base_params.amount, n_fragments)
            
            # Generate transaction parameters for each fragment
            transactions = []
            for amount in amounts:
                tx_params = TransactionParams(
                    amount=amount,
                    slippage=self._randomize_slippage(base_params.slippage),
                    gas_price=self._randomize_gas(base_params.gas_price),
                    gas_limit=self._randomize_gas(base_params.gas_limit),
                    nonce=self._generate_nonce(base_params.nonce),
                    deadline=self._randomize_deadline(base_params.deadline)
                )
                transactions.append(tx_params)
            
            # Store pattern
            self._store_transaction_pattern(transactions)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error obfuscating transaction: {str(e)}")
            return [base_params]
    
    def _split_amount(self, total_amount: float, n_fragments: int) -> List[float]:
        """Split total amount into random fragments"""
        # Generate random weights
        weights = np.random.dirichlet(np.ones(n_fragments))
        
        # Calculate amounts
        amounts = [total_amount * w for w in weights]
        
        # Add random variance to each amount
        for i in range(len(amounts)):
            variance = random.uniform(*self.config["amount_variance"])
            sign = random.choice([-1, 1])
            amounts[i] *= (1 + sign * variance)
        
        # Normalize to ensure sum equals total
        sum_amounts = sum(amounts)
        amounts = [a * (total_amount / sum_amounts) for a in amounts]
        
        return amounts
    
    def _randomize_slippage(self, base_slippage: float) -> float:
        """Add random variance to slippage"""
        variance = random.uniform(*self.config["slippage_variance"])
        sign = random.choice([-1, 1])
        return max(0.001, base_slippage * (1 + sign * variance))
    
    def _randomize_gas(self, base_gas: int) -> int:
        """Add random variance to gas values"""
        variance = random.uniform(*self.config["gas_variance"])
        sign = random.choice([-1, 1])
        return int(base_gas * (1 + sign * variance))
    
    def _generate_nonce(self, base_nonce: int) -> int:
        """Generate slightly offset nonce"""
        offset = random.randint(*self.config["nonce_offset"])
        return base_nonce + offset
    
    def _randomize_deadline(self, base_deadline: int) -> int:
        """Add random variance to transaction deadline"""
        variance = random.randint(*self.config["deadline_variance"])
        sign = random.choice([-1, 1])
        return base_deadline + sign * variance
    
    def _store_transaction_pattern(self, transactions: List[TransactionParams]):
        """Store transaction pattern for analysis"""
        pattern = {
            "timestamp": datetime.now(),
            "n_fragments": len(transactions),
            "amount_distribution": [tx.amount for tx in transactions],
            "gas_prices": [tx.gas_price for tx in transactions]
        }
        
        self.recent_patterns.append(pattern)
        if len(self.recent_patterns) > self.pattern_memory:
            self.recent_patterns.pop(0)
    
    def get_timing_variance(self) -> Tuple[int, int]:
        """Get random timing variance for transaction"""
        return (
            random.randint(*self.config["time_variance_ms"]),
            random.randint(*self.config["time_variance_ms"])
        )
    
    def simulate_human_behavior(self, base_params: TransactionParams) -> TransactionParams:
        """
        Modify transaction parameters to simulate human behavior
        
        Args:
            base_params: Original transaction parameters
            
        Returns:
            Modified transaction parameters
        """
        try:
            # Humans often use "round" numbers
            amount = self._round_human_amount(base_params.amount)
            
            # Humans typically use higher slippage for safety
            slippage = base_params.slippage * random.uniform(1.2, 1.5)
            
            # Humans often use "fast" gas prices
            gas_price = int(base_params.gas_price * random.uniform(1.1, 1.3))
            
            # Humans set longer deadlines
            deadline = base_params.deadline + random.randint(60, 600)
            
            return TransactionParams(
                amount=amount,
                slippage=slippage,
                gas_price=gas_price,
                gas_limit=base_params.gas_limit,
                nonce=base_params.nonce,
                deadline=deadline
            )
            
        except Exception as e:
            logger.error(f"Error simulating human behavior: {str(e)}")
            return base_params
    
    def _round_human_amount(self, amount: float) -> float:
        """Round amount to simulate human input"""
        # Humans often use numbers ending in 0, 5, or nice fractions
        round_choices = [
            round(amount, 2),  # Standard 2 decimal places
            round(amount),     # Whole number
            round(amount * 2) / 2,  # Half numbers
            round(amount * 4) / 4   # Quarter numbers
        ]
        return random.choice(round_choices)
    
    def analyze_patterns(self) -> Dict:
        """
        Analyze recent transaction patterns for predictability
        
        Returns:
            Dictionary with pattern analysis
        """
        if not self.recent_patterns:
            return {"predictability": 0, "recommendations": []}
        
        try:
            # Analyze timing patterns
            timestamps = [p["timestamp"] for p in self.recent_patterns]
            intervals = np.diff([t.timestamp() for t in timestamps])
            timing_variance = np.std(intervals)
            
            # Analyze amount patterns
            amounts = [p["amount_distribution"] for p in self.recent_patterns]
            amount_variance = np.mean([np.std(a) for a in amounts])
            
            # Calculate predictability score
            predictability = self._calculate_predictability(
                timing_variance,
                amount_variance
            )
            
            # Generate recommendations
            recommendations = []
            if timing_variance < 1.0:
                recommendations.append("Increase timing randomization")
            if amount_variance < 0.1:
                recommendations.append("Increase amount variance")
            
            return {
                "predictability": predictability,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {str(e)}")
            return {"predictability": 0, "recommendations": []}
    
    def _calculate_predictability(self, timing_variance: float, amount_variance: float) -> float:
        """Calculate pattern predictability score"""
        # Lower variance = higher predictability
        timing_pred = 1 / (1 + timing_variance)
        amount_pred = 1 / (1 + amount_variance)
        
        # Weighted average (timing is more important)
        return 0.7 * timing_pred + 0.3 * amount_pred 