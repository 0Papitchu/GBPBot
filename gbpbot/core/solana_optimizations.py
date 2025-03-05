"""
Solana optimizations for high-speed sniping and MEV protection
This module provides specialized components to optimize Solana transactions
for memecoin sniping, including priority fee optimization and transaction bundling.
"""

import time
import uuid
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any

class SolanaPriorityFeeOptimizer:
    """
    Optimizes priority fees for Solana transactions based on network congestion
    and transaction importance for high-speed sniping operations.
    """
    
    def __init__(self, connection, config: Dict):
        """
        Initialize the Solana priority fee optimizer
        
        Args:
            connection: Solana RPC connection
            config: Configuration dictionary containing fee settings
        """
        self.connection = connection
        self.config = config
        self.recent_fee_cache = []
        self.last_cache_update = 0
        self.cache_ttl = config.get("priority_fee_cache_ttl", 5)  # Default 5 seconds
        self.logger = logging.getLogger("SolanaPriorityFeeOptimizer")
    
    async def get_recent_prioritization_fees(self):
        """
        Fetch recent prioritization fees from the Solana network
        
        Returns:
            List of recent fees or None if fetch failed
        """
        try:
            # Use getRecentPrioritizationFees to get recent fees
            response = await self.connection.request_aiohttp_post(
                self.connection._provider.endpoint_uri,
                {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "getRecentPrioritizationFees",
                    "params": []
                }
            )
            
            if response and 'result' in response:
                return response['result']
            return None
        except Exception as e:
            self.logger.error(f"Error fetching recent prioritization fees: {e}")
            return None
    
    async def get_optimal_priority_fee(self, transaction_type: str = "normal") -> int:
        """
        Calculate the optimal priority fee based on recent network activity
        and transaction importance.
        
        Args:
            transaction_type: Type of transaction ('normal', 'high', 'urgent', 'sniping')
            
        Returns:
            Optimal priority fee in micro-lamports
        """
        current_time = time.time()
        
        # Refresh cache if needed
        if current_time - self.last_cache_update > self.cache_ttl:
            recent_fees = await self.get_recent_prioritization_fees()
            if recent_fees:
                self.recent_fee_cache = recent_fees
                self.last_cache_update = current_time
        
        # Calculate optimal fee based on percentile
        if self.recent_fee_cache:
            fees = [fee['prioritizationFee'] for fee in self.recent_fee_cache]
            fees.sort()
            
            # Different percentiles based on transaction type
            if transaction_type == "urgent" or transaction_type == "sniping":
                # 90th percentile for urgent/sniping transactions (outbid 90% of transactions)
                percentile = 0.9
                multiplier = 1.5  # 50% higher for sniping
            elif transaction_type == "high":
                # 75th percentile for high priority
                percentile = 0.75
                multiplier = 1.2
            else:
                # 50th percentile (median) for normal transactions
                percentile = 0.5
                multiplier = 1.0
            
            if len(fees) > 0:
                optimal_fee = fees[min(int(len(fees) * percentile), len(fees) - 1)]
                
                # Apply multiplier
                optimal_fee = int(optimal_fee * multiplier)
                
                # Anti-MEV protection - ensure minimum fee for sniping
                if transaction_type == "sniping" and self.config.get("anti_mev_enabled", True):
                    min_anti_mev_fee = self.config.get("min_anti_mev_fee", 2000)  # 0.002 SOL in microlamports
                    optimal_fee = max(optimal_fee, min_anti_mev_fee)
                
                return max(optimal_fee, self.config.get("min_priority_fee", 1000))
        
        # Default if no data available
        default_fees = {
            "normal": self.config.get("default_priority_fee", 5000),
            "high": self.config.get("default_high_priority_fee", 10000),
            "urgent": self.config.get("default_urgent_priority_fee", 20000),
            "sniping": self.config.get("default_sniping_priority_fee", 25000)
        }
        
        return default_fees.get(transaction_type, default_fees["normal"])
    
    async def optimize_transaction(self, transaction, transaction_type: str = "normal"):
        """
        Add optimal priority fee to a transaction
        
        Args:
            transaction: The transaction to optimize
            transaction_type: Type of transaction ('normal', 'high', 'urgent', 'sniping')
            
        Returns:
            Tuple of (optimized transaction, priority fee used)
        """
        priority_fee = await self.get_optimal_priority_fee(transaction_type)
        
        self.logger.info(f"Using priority fee: {priority_fee} microlamports for {transaction_type} transaction")
        
        # Create compute budget instruction for priority fee
        from solana.rpc.types import TxOpts
        from solders.compute_budget import ComputeBudgetProgram
        
        # Set compute unit limit if specified in config
        compute_unit_limit = None
        if transaction_type == "sniping":
            compute_unit_limit = self.config.get("sniping_compute_unit_limit", 200000)
        elif transaction_type in ["urgent", "high"]:
            compute_unit_limit = self.config.get("high_compute_unit_limit", 150000)
        
        # Create compute budget instructions
        compute_budget_instructions = []
        
        # Set compute unit price (priority fee)
        compute_budget_instructions.append(
            ComputeBudgetProgram.set_compute_unit_price(priority_fee)
        )
        
        # Set compute unit limit if specified
        if compute_unit_limit:
            compute_budget_instructions.append(
                ComputeBudgetProgram.set_compute_unit_limit(compute_unit_limit)
            )
        
        # Add compute budget instructions to the beginning of transaction instructions
        if hasattr(transaction, 'message'):
            # For VersionedTransaction
            tx_instructions = list(transaction.message.instructions())
            all_instructions = compute_budget_instructions + tx_instructions
            
            # Create new message with updated instructions
            from solders.message import Message
            message = Message.new_with_blockhash(
                all_instructions,
                transaction.message.header(),
                transaction.message.recent_blockhash
            )
            
            # Create new transaction with updated message
            from solders.transaction import Transaction
            optimized_transaction = Transaction.new_with_payer(
                message,
                transaction.signatures[0].pubkey
            )
            
            return optimized_transaction, priority_fee
        else:
            # For legacy Transaction
            transaction.add(compute_budget_instructions[0], 0)
            if len(compute_budget_instructions) > 1:
                transaction.add(compute_budget_instructions[1], 1)
            
            return transaction, priority_fee


class SolanaTransactionBundler:
    """
    Handles transaction bundling for MEV protection on Solana using Jito bundles
    and other bundling techniques for high-speed sniping operations.
    """
    
    def __init__(self, connection, config: Dict):
        """
        Initialize the Solana transaction bundler
        
        Args:
            connection: Solana RPC connection
            config: Configuration dictionary containing bundling settings
        """
        self.connection = connection
        self.config = config
        self.priority_fee_optimizer = SolanaPriorityFeeOptimizer(connection, config)
        self.logger = logging.getLogger("SolanaTransactionBundler")
        self.jito_enabled = config.get("jito_enabled", False)
        self.jito_endpoint = config.get("jito_endpoint", "https://mainnet.jito.wtf")
        self.jito_auth_token = config.get("jito_auth_token", "")
        self.retry_count = config.get("tx_retry_count", 3)
        self.parallel_submission = config.get("parallel_submission", True)
    
    async def create_transaction_bundle(self, 
                                       instructions_list: List[List], 
                                       wallet, 
                                       tx_type: str = "sniping") -> List:
        """
        Create a bundle of transactions that will be submitted together
        
        Args:
            instructions_list: List of instruction lists to be bundled
            wallet: Wallet to sign the transactions
            tx_type: Type of transaction ('normal', 'high', 'urgent', 'sniping')
            
        Returns:
            List of prepared transactions
        """
        bundle = []
        recent_blockhash = await self._get_latest_blockhash()
        
        # Process each instruction set into a transaction
        for instructions in instructions_list:
            try:
                # Create and optimize transaction with priority fees
                from solders.transaction import Transaction
                from solders.message import Message
                
                # Create message
                message = Message.new_with_blockhash(
                    instructions,
                    wallet.pubkey(),
                    recent_blockhash
                )
                
                # Create transaction
                transaction = Transaction.new_unsigned(message)
                
                # Optimize transaction with priority fees
                optimized_tx, fee = await self.priority_fee_optimizer.optimize_transaction(
                    transaction, tx_type
                )
                
                # Sign transaction
                signed_tx = await self._sign_transaction(optimized_tx, wallet)
                
                bundle.append(signed_tx)
                
            except Exception as e:
                self.logger.error(f"Error creating transaction in bundle: {e}")
                continue
        
        return bundle
    
    async def _get_latest_blockhash(self):
        """Get the latest blockhash from the Solana network"""
        try:
            blockhash_resp = await self.connection.get_latest_blockhash()
            if hasattr(blockhash_resp, 'value'):
                return blockhash_resp.value.blockhash
            return blockhash_resp['result']['value']['blockhash']
        except Exception as e:
            self.logger.error(f"Error getting latest blockhash: {e}")
            raise
    
    async def _sign_transaction(self, transaction, wallet):
        """Sign a transaction with the provided wallet"""
        try:
            return wallet.sign_transaction(transaction)
        except Exception as e:
            self.logger.error(f"Error signing transaction: {e}")
            raise
    
    async def submit_bundle(self, bundle: List, wait_for_confirmation: bool = True) -> Dict:
        """
        Submit a bundle of transactions to the Solana network with MEV protection
        
        Args:
            bundle: List of signed transactions to submit
            wait_for_confirmation: Whether to wait for confirmation
            
        Returns:
            Dictionary with transaction results
        """
        results = {}
        
        if self.jito_enabled and self.jito_auth_token:
            # Submit via Jito bundle for MEV protection
            results = await self._submit_jito_bundle(bundle, wait_for_confirmation)
        elif self.parallel_submission and len(bundle) > 1:
            # Submit transactions in parallel
            results = await self._submit_parallel(bundle, wait_for_confirmation)
        else:
            # Submit transactions sequentially
            results = await self._submit_sequential(bundle, wait_for_confirmation)
        
        return results
    
    async def _submit_jito_bundle(self, bundle: List, wait_for_confirmation: bool) -> Dict:
        """Submit transactions as a bundle via Jito for MEV protection"""
        try:
            import aiohttp
            
            # Prepare the bundle data
            bundle_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "sendBundle",
                "params": [
                    {
                        "transactions": [tx.to_json() for tx in bundle],
                        "options": {
                            "skipPreFlight": True
                        }
                    }
                ]
            }
            
            # Set up headers with auth token
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.jito_auth_token}"
            }
            
            # Send the bundle
            async with aiohttp.ClientSession() as session:
                async with session.post(self.jito_endpoint, json=bundle_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.logger.info(f"Successfully submitted Jito bundle: {result}")
                        
                        # Wait for confirmation if requested
                        if wait_for_confirmation and 'result' in result:
                            bundle_id = result['result']
                            confirmation = await self._wait_for_jito_bundle(bundle_id)
                            return {
                                "success": True,
                                "type": "jito_bundle",
                                "bundle_id": bundle_id,
                                "confirmation": confirmation
                            }
                        
                        return {
                            "success": True,
                            "type": "jito_bundle",
                            "bundle_id": result.get('result', None)
                        }
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to submit Jito bundle: {error_text}")
                        
                        # Fall back to parallel submission
                        self.logger.info("Falling back to parallel submission")
                        return await self._submit_parallel(bundle, wait_for_confirmation)
            
        except Exception as e:
            self.logger.error(f"Error submitting Jito bundle: {e}")
            # Fall back to parallel submission
            self.logger.info("Falling back to parallel submission due to error")
            return await self._submit_parallel(bundle, wait_for_confirmation)
    
    async def _wait_for_jito_bundle(self, bundle_id: str, timeout: int = 60) -> Dict:
        """Wait for a Jito bundle to be confirmed"""
        import aiohttp
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Prepare the request data
                request_data = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "getBundleStatus",
                    "params": [bundle_id]
                }
                
                # Set up headers with auth token
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.jito_auth_token}"
                }
                
                # Send the request
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.jito_endpoint, json=request_data, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if 'result' in result:
                                status = result['result']
                                
                                if status.get('status') == 'confirmed':
                                    return {
                                        "success": True,
                                        "status": "confirmed",
                                        "details": status
                                    }
                                elif status.get('status') == 'rejected':
                                    return {
                                        "success": False,
                                        "status": "rejected",
                                        "details": status
                                    }
                        
            except Exception as e:
                self.logger.error(f"Error checking Jito bundle status: {e}")
            
            # Wait before trying again
            await asyncio.sleep(2)
        
        return {
            "success": False,
            "status": "timeout",
            "message": f"Timed out waiting for bundle confirmation after {timeout} seconds"
        }
    
    async def _submit_parallel(self, bundle: List, wait_for_confirmation: bool) -> Dict:
        """Submit transactions in parallel"""
        # Prepare tasks for parallel submission
        tasks = []
        for tx in bundle:
            tasks.append(self._submit_and_confirm(tx, wait_for_confirmation))
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        success_count = 0
        failures = []
        tx_details = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failures.append({
                    "index": i,
                    "error": str(result)
                })
            elif result.get("success", False):
                success_count += 1
                tx_details.append(result)
            else:
                failures.append({
                    "index": i,
                    "error": result.get("error", "Unknown error")
                })
        
        return {
            "success": success_count > 0,
            "type": "parallel_submission",
            "total": len(bundle),
            "successful": success_count,
            "failed": len(failures),
            "failures": failures,
            "tx_details": tx_details
        }
    
    async def _submit_sequential(self, bundle: List, wait_for_confirmation: bool) -> Dict:
        """Submit transactions sequentially"""
        results = []
        
        for tx in bundle:
            result = await self._submit_and_confirm(tx, wait_for_confirmation)
            results.append(result)
            
            # If a transaction fails, stop processing the rest
            if not result.get("success", False):
                break
        
        success_count = sum(1 for r in results if r.get("success", False))
        
        return {
            "success": success_count > 0,
            "type": "sequential_submission",
            "total": len(bundle),
            "successful": success_count,
            "results": results
        }
    
    async def _submit_and_confirm(self, transaction, wait_confirmation: bool) -> Dict:
        """Submit a single transaction and optionally wait for confirmation"""
        from solders.rpc.responses import RpcResponseAndContext, SendTransactionResp
        
        # Try multiple times if configured
        for attempt in range(self.retry_count):
            try:
                # Send transaction
                tx_bytes = transaction.serialize()
                response = await self.connection.send_raw_transaction(
                    tx_bytes,
                    opts=self.connection.opts
                )
                
                # Extract transaction signature
                if isinstance(response, RpcResponseAndContext) or isinstance(response, SendTransactionResp):
                    tx_sig = str(response.value)
                elif isinstance(response, dict) and 'result' in response:
                    tx_sig = response['result']
                else:
                    tx_sig = str(response)
                
                self.logger.info(f"Transaction submitted: {tx_sig}")
                
                # Wait for confirmation if requested
                if wait_confirmation:
                    confirmed = await self._wait_for_confirmation(tx_sig)
                    if confirmed:
                        return {
                            "success": True,
                            "signature": tx_sig,
                            "confirmed": True
                        }
                    else:
                        # If not confirmed, try again
                        self.logger.warning(f"Transaction not confirmed, retrying: {tx_sig}")
                        continue
                else:
                    return {
                        "success": True,
                        "signature": tx_sig,
                        "confirmed": False
                    }
                    
            except Exception as e:
                self.logger.error(f"Error submitting transaction (attempt {attempt+1}/{self.retry_count}): {e}")
                # Sleep briefly before retrying
                await asyncio.sleep(0.5)
        
        return {
            "success": False,
            "error": f"Failed to submit transaction after {self.retry_count} attempts"
        }
    
    async def _wait_for_confirmation(self, tx_sig: str, timeout: int = 60) -> bool:
        """Wait for a transaction to be confirmed"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check transaction status
                response = await self.connection.get_signature_statuses([tx_sig])
                
                # Extract status
                if hasattr(response, 'value'):
                    statuses = response.value
                else:
                    statuses = response['result']['value']
                
                if statuses and statuses[0]:
                    status = statuses[0]
                    
                    # Check if confirmed
                    if status.get('confirmationStatus') == 'confirmed' or status.get('confirmations', 0) > 0:
                        return True
                
            except Exception as e:
                self.logger.error(f"Error checking transaction status: {e}")
            
            # Wait before trying again
            await asyncio.sleep(1)
        
        return False


class SolanaSnipingOptimizer:
    """
    Comprehensive optimizer for Solana sniping operations, combining fee optimization,
    transaction bundling, and smart routing strategies.
    """
    
    def __init__(self, connection, config: Dict):
        """
        Initialize the Solana sniping optimizer
        
        Args:
            connection: Solana RPC connection
            config: Configuration dictionary
        """
        self.connection = connection
        self.config = config
        self.logger = logging.getLogger("SolanaSnipingOptimizer")
        self.priority_fee_optimizer = SolanaPriorityFeeOptimizer(connection, config)
        self.transaction_bundler = SolanaTransactionBundler(connection, config)
        
        # Precomputed routes for popular DEXes
        self.routes = {}
        self.last_route_update = 0
        self.route_update_interval = config.get("route_update_interval", 300)  # 5 minutes
        
        # Performance monitoring metrics
        self.performance_metrics = {
            "avg_transaction_time": 0,
            "success_rate": 1.0,
            "total_transactions": 0,
            "successful_transactions": 0,
            "last_transactions": []
        }
    
    async def execute_snipe(self, token_address: str, amount_in: float, wallet, 
                           slippage: float = 1.0, base_token: str = "SOL") -> Dict:
        """
        Execute a high-speed snipe operation for a token
        
        Args:
            token_address: Address of token to snipe
            amount_in: Amount of base token to spend
            wallet: Wallet to use for the transaction
            slippage: Maximum acceptable slippage percentage
            base_token: Base token to use (SOL, USDC, etc.)
            
        Returns:
            Dict: Result of the snipe operation
        """
        try:
            start_time = time.time()
            
            # Log snipe initiation
            self.logger.info(f"Initiating snipe for token {token_address} with {amount_in} {base_token}")
            
            # Get base token address
            base_token_address = self._resolve_token_address(base_token)
            
            # Find optimal route to execute the swap
            route = await self._find_optimal_route(token_address, base_token_address)
            
            if not route:
                self.logger.error(f"No viable route found for {base_token} -> {token_address}")
                return {
                    "success": False,
                    "error": "No viable route found",
                    "token": token_address,
                    "base_token": base_token
                }
            
            self.logger.info(f"Selected route via {route['name']} DEX")
            
            # Prepare swap instructions
            instructions = await self._prepare_swap_instructions(
                base_token_address, 
                token_address,
                amount_in,
                slippage,
                route
            )
            
            if not instructions:
                self.logger.error(f"Failed to prepare swap instructions for {base_token} -> {token_address}")
                return {
                    "success": False,
                    "error": "Failed to prepare swap instructions",
                    "token": token_address,
                    "base_token": base_token
                }
            
            # Create bundle of transactions (primary + backup with higher fees)
            bundle = await self.transaction_bundler.create_transaction_bundle(
                [instructions],  # Just our main instruction set for now
                wallet,
                "sniping"
            )
            
            # Submit the bundle
            result = await self.transaction_bundler.submit_bundle(
                bundle,
                wait_for_confirmation=True
            )
            
            # Add additional details to the result
            execution_time = time.time() - start_time
            
            result.update({
                "token": token_address,
                "base_token": base_token,
                "amount_in": amount_in,
                "slippage": slippage,
                "execution_time": execution_time,
                "route": route['name']
            })
            
            # Update performance metrics
            self._update_performance_metrics(result, execution_time)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing snipe: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "token": token_address,
                "base_token": base_token
            }
    
    async def _find_optimal_route(self, token_address: str, base_token_address: str) -> Dict:
        """
        Find the optimal route to execute a swap
        
        Args:
            token_address: Target token address
            base_token_address: Base token address
            
        Returns:
            Dict: Route information
        """
        # Simple implementation - in a complete version, this would:
        # 1. Check multiple DEXes for the best price/liquidity
        # 2. Consider transaction costs
        # 3. Consider historical success rates
        
        # For now, just return a route via Raydium
        return {
            "name": "raydium",
            "program_id": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            "swap_authority": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
            "token_program": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        }
    
    async def _prepare_swap_instructions(self, base_token_address: str, token_address: str,
                                       amount_in: float, slippage: float, route: Dict) -> List:
        """
        Prepare instructions for a swap
        
        Args:
            base_token_address: Base token address
            token_address: Target token address
            amount_in: Amount of base token to spend
            slippage: Maximum acceptable slippage percentage
            route: Route information
            
        Returns:
            List: Instructions for the swap
        """
        # This is a placeholder - actual implementation would depend on the DEX SDK
        from solders.instruction import Instruction
        
        # For now, return a placeholder instruction
        return [
            Instruction(
                program_id=route["program_id"],
                accounts=[],
                data=b""
            )
        ]
    
    def _resolve_token_address(self, token_symbol: str) -> str:
        """
        Resolve a token symbol to its address
        
        Args:
            token_symbol: Token symbol (e.g., SOL, USDC)
            
        Returns:
            str: Token address
        """
        # Common token addresses on Solana
        token_addresses = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
        }
        
        return token_addresses.get(token_symbol.upper(), token_symbol)
    
    def _update_performance_metrics(self, result: Dict, execution_time: float):
        """
        Update performance metrics based on the result of a sniping operation
        
        Args:
            result: Result of the sniping operation
            execution_time: Time taken to execute the snipe
        """
        success = result.get("success", False)
        
        # Update total and successful transaction counts
        self.performance_metrics["total_transactions"] += 1
        if success:
            self.performance_metrics["successful_transactions"] += 1
        
        # Update success rate
        self.performance_metrics["success_rate"] = (
            self.performance_metrics["successful_transactions"] / 
            self.performance_metrics["total_transactions"]
        )
        
        # Update average transaction time
        if self.performance_metrics["avg_transaction_time"] == 0:
            self.performance_metrics["avg_transaction_time"] = execution_time
        else:
            # Exponential moving average with 0.1 weight
            self.performance_metrics["avg_transaction_time"] = (
                0.9 * self.performance_metrics["avg_transaction_time"] +
                0.1 * execution_time
            )
        
        # Add to recent transactions
        self.performance_metrics["last_transactions"].append({
            "token": result.get("token"),
            "success": success,
            "execution_time": execution_time,
            "time": time.time()
        })
        
        # Keep only the last 20 transactions
        if len(self.performance_metrics["last_transactions"]) > 20:
            self.performance_metrics["last_transactions"] = self.performance_metrics["last_transactions"][-20:] 