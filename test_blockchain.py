import asyncio
import sys
from loguru import logger
from gbpbot.core.blockchain import BlockchainClient
from web3 import Web3
from collections import OrderedDict
import time
import statistics
import secrets
from eth_account import Account
from eth_keys import Scrypt
from eth_keys import AESGCM
import json
import hashlib
import uuid
import functools
import inspect
import importlib
from collections import defaultdict
import aioredis

# Configuration du logger
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("test_blockchain.log", rotation="100 MB")

async def test_blockchain_client():
    """
    Teste les méthodes get_dex_price et get_cex_price du BlockchainClient
    """
    logger.info("🔍 Test du BlockchainClient...")
    
    # Initialiser le client blockchain en mode simulation
    blockchain = BlockchainClient(simulation_mode=True)
    
    # Tester get_dex_price
    logger.info("Test de get_dex_price...")
    
    # Définir les adresses de test
    wavax_address = blockchain.token_addresses["WAVAX"]
    usdt_address = blockchain.token_addresses["USDT"]
    usdc_address = blockchain.token_addresses["USDC"]
    weth_address = blockchain.token_addresses["WETH"]
    
    # Montant d'entrée pour le test
    amount_in = Web3.to_wei(1, "ether")  # 1 AVAX
    
    # Tester différentes paires sur différents DEX
    dex_exchanges = ["trader_joe", "pangolin", "sushi"]
    for dex in dex_exchanges:
        # WAVAX -> USDT
        price = await blockchain.get_dex_price(dex, wavax_address, usdt_address, amount_in)
        logger.info(f"Prix sur {dex} pour WAVAX -> USDT: {price}")
        
        # WAVAX -> USDC
        price = await blockchain.get_dex_price(dex, wavax_address, usdc_address, amount_in)
        logger.info(f"Prix sur {dex} pour WAVAX -> USDC: {price}")
        
        # WAVAX -> WETH
        price = await blockchain.get_dex_price(dex, wavax_address, weth_address, amount_in)
        logger.info(f"Prix sur {dex} pour WAVAX -> WETH: {price}")
    
    # Tester get_cex_price
    logger.info("Test de get_cex_price...")
    
    # Tester différentes paires sur différents CEX
    cex_exchanges = ["binance", "kucoin", "gate"]
    for cex in cex_exchanges:
        # AVAX/USDT
        price = await blockchain.get_cex_price(cex, "AVAX/USDT")
        logger.info(f"Prix sur {cex} pour AVAX/USDT: {price}")
        
        # AVAX/USDC
        price = await blockchain.get_cex_price(cex, "AVAX/USDC")
        logger.info(f"Prix sur {cex} pour AVAX/USDC: {price}")
        
        # ETH/USDT
        price = await blockchain.get_cex_price(cex, "ETH/USDT")
        logger.info(f"Prix sur {cex} pour ETH/USDT: {price}")
    
    logger.info("✅ Test du BlockchainClient réussi")
    return True

async def main():
    """
    Fonction principale
    """
    logger.info("Tests du BlockchainClient")
    logger.info("==================================================")
    
    result = await test_blockchain_client()
    
    logger.info("==================================================")
    logger.info(f"Résultat du test: {'✅ RÉUSSI' if result else '❌ ÉCHOUÉ'}")
    
    return 0 if result else 1

class EventProcessingEngine:
    def __init__(self):
        self.event_queue = asyncio.Queue()
        self.worker_tasks = []
        
    async def start_workers(self, worker_count=4):
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop(i))
            self.worker_tasks.append(task)
        
    async def _worker_loop(self, worker_id):
        while True:
            event = await self.event_queue.get()
            if event is None:
                break
            try:
                await self._process_event(event)
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
            finally:
                self.event_queue.task_done()

class OptimizedMemoryCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()  # LRU implementable
        self.max_size = max_size
        self.lock = asyncio.Lock()
        
    async def get(self, key):
        async with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
        return None
        
    async def put(self, key, value, ttl=None):
        async with self.lock:
            if len(self.cache) >= self.max_size:
                # Evict least recently used
                self.cache.popitem(last=False)
            self.cache[key] = value
            
            if ttl:
                asyncio.create_task(self._expire_after_ttl(key, ttl))
                
    async def _expire_after_ttl(self, key, ttl):
        await asyncio.sleep(ttl)
        async with self.lock:
            if key in self.cache:
                self.cache.pop(key)

class GasOptimizer:
    def __init__(self, web3, chain_id):
        self.web3 = web3
        self.chain_id = chain_id
        self.base_fee_history = collections.deque(maxlen=20)
        self.last_update = 0
        
    async def update_base_fee(self):
        current_time = time.time()
        if current_time - self.last_update < 15:  # Update at most every 15s
            return
            
        latest = await self.web3.eth.get_block('latest')
        if 'baseFeePerGas' in latest:
            self.base_fee_history.append(latest['baseFeePerGas'])
            self.last_update = current_time
            
    async def estimate_optimal_gas(self, transaction_type="fast"):
        await self.update_base_fee()
        
        if not self.base_fee_history:
            # Fallback to standard gas price
            return await self.web3.eth.gas_price
            
        base_fee = statistics.median(self.base_fee_history)
        
        # EIP-1559 parameters
        multipliers = {
            "slow": 1.05,
            "normal": 1.2,
            "fast": 1.5,
            "urgent": 2.0
        }
        
        multiplier = multipliers.get(transaction_type, 1.2)
        max_priority_fee = self._calculate_priority_fee(transaction_type)
        
        # Return EIP-1559 parameters
        return {
            'maxFeePerGas': int(base_fee * multiplier) + max_priority_fee,
            'maxPriorityFeePerGas': max_priority_fee
        }

class MEVProtection:
    def __init__(self, web3, private_relays=None):
        self.web3 = web3
        self.private_relays = private_relays or ["https://relay.flashbots.net"]
        
    async def send_private_transaction(self, signed_tx):
        """Submit transaction to private relays to avoid front-running"""
        bundle = [{
            "signed_transaction": signed_tx.rawTransaction.hex()
        }]
        
        for relay in self.private_relays:
            try:
                response = await self._submit_to_relay(relay, bundle)
                if response.get('success'):
                    return response.get('bundleHash')
            except Exception as e:
                logger.warning(f"Failed to submit to relay {relay}: {e}")
                
        # Fallback to public mempool as last resort
        logger.warning("Private transaction failed, falling back to public mempool")
        return await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

class EnhancedSecureKeyManager:
    def __init__(self, config_path, keystore_path):
        self.config_path = config_path
        self.keystore_path = keystore_path
        self.keys = {}
        self.kdf_iterations = 1000000  # Plus sécurisé
        
    def generate_keypair(self, alias):
        # Générer une paire de clés sécurisée
        private_key = secrets.token_bytes(32)
        account = Account.from_key(private_key)
        
        # Dériver la clé de chiffrement avec Argon2id
        salt = secrets.token_bytes(16)
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=2**20,  # CPU/memory cost factor
            r=8,      # Block size
            p=1       # Parallelization factor
        )
        
        # Chiffrement avec AES-GCM (authentifié)
        encryptor = AESGCM(kdf)
        nonce = secrets.token_bytes(12)
        ciphertext = encryptor.encrypt(nonce, private_key, None)
        
        # Stockage sécurisé
        keydata = {
            'address': account.address,
            'crypto': {
                'cipher': 'aes-256-gcm',
                'cipherparams': {
                    'nonce': nonce.hex()
                },
                'ciphertext': ciphertext.hex(),
                'kdf': 'scrypt',
                'kdfparams': {
                    'dklen': 32,
                    'n': 2**20,
                    'p': 1,
                    'r': 8,
                    'salt': salt.hex()
                }
            }
        }
        
        self.keys[alias] = keydata
        self._save_keystore()
        
        return account.address

class DataIntegrityVerifier:
    def __init__(self, trusted_sources):
        self.trusted_sources = trusted_sources
        self.merkle_roots = {}  # Map of source_id -> latest merkle root
        
    async def verify_price_data(self, source_id, data, signature, merkle_proof=None):
        """Verify the integrity of price data using cryptographic proofs"""
        if source_id not in self.trusted_sources:
            return False
            
        public_key = self.trusted_sources[source_id]['public_key']
        
        # 1. Verify signature
        message = self._prepare_message(data)
        is_valid = self._verify_signature(message, signature, public_key)
        if not is_valid:
            logger.warning(f"Invalid signature from source {source_id}")
            return False
            
        # 2. Verify Merkle proof if provided
        if merkle_proof and source_id in self.merkle_roots:
            root = self.merkle_roots[source_id]
            data_hash = hashlib.sha3_256(json.dumps(data).encode()).digest()
            
            if not self._verify_merkle_proof(data_hash, merkle_proof, root):
                logger.warning(f"Invalid Merkle proof from source {source_id}")
                return False
                
        return True

class AdvancedTelemetry:
    def __init__(self, app_name, instance_id=None):
        self.app_name = app_name
        self.instance_id = instance_id or uuid.uuid4().hex
        self.traces = {}
        self.metrics = defaultdict(lambda: defaultdict(float))
        self.start_time = time.time()
        
        # Instrumenter automatiquement les fonctions clés
        self._instrument_async_functions()
        
    def _instrument_async_functions(self):
        # Patch des fonctions critiques
        modules_to_instrument = [
            ('gbpbot.core.blockchain', 'BlockchainClient'),
            ('gbpbot.core.price_feed', 'PriceManager'),
            ('gbpbot.strategies', 'ArbitrageStrategy')
        ]
        
        for module_path, class_name in modules_to_instrument:
            try:
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                
                # Wrap all public async methods
                for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                    if not name.startswith('_') and inspect.iscoroutinefunction(method):
                        setattr(cls, name, self._wrap_async_method(method))
                        
            except Exception as e:
                logger.error(f"Failed to instrument {module_path}.{class_name}: {e}")
                
    def _wrap_async_method(self, method):
        """Wraps an async method with telemetry"""
        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            span_id = uuid.uuid4().hex
            
            # Start span
            self.traces[span_id] = {
                'method': method.__qualname__,
                'start_time': start,
                'args': self._sanitize_args(args),
                'kwargs': self._sanitize_args(kwargs)
            }
            
            try:
                # Execute original method
                result = await method(*args, **kwargs)
                
                # Calculate performance metrics
                duration = time.perf_counter() - start
                self.metrics[method.__module__][method.__qualname__] += duration
                
                # Update span with success
                self.traces[span_id].update({
                    'duration': duration,
                    'status': 'success',
                })
                
                return result
            except Exception as e:
                # Calculate failure metrics
                duration = time.perf_counter() - start
                self.metrics[method.__module__][method.__qualname__] += duration
                self.metrics[method.__module__][f"{method.__qualname__}_errors"] += 1
                
                # Update span with error
                self.traces[span_id].update({
                    'duration': duration,
                    'status': 'error',
                    'error': str(e),
                    'error_type': e.__class__.__name__
                })
                
                raise
            finally:
                # Prune old spans periodically
                if len(self.traces) > 10000:
                    self._prune_old_traces()
                    
        return wrapper

class PerformanceAttribution:
    def __init__(self, portfolio_manager):
        self.portfolio_manager = portfolio_manager
        self.strategy_performance = defaultdict(dict)
        self.trade_journal = []
        self.baseline_assets = {}
        
    async def record_trade(self, trade):
        """Record a trade with full context for performance attribution"""
        # Calculate immediate P&L
        token_in = trade['token_in_symbol']
        token_out = trade['token_out_symbol']
        amount_in = trade['amount_in']
        amount_out = trade['amount_out']
        
        # Record price snapshot at trade time
        prices = await self.portfolio_manager.get_market_prices([token_in, token_out])
        
        # Record complete trade data
        trade_record = {
            'timestamp': time.time(),
            'trade_id': uuid.uuid4().hex,
            'strategy': trade['strategy'],
            'type': trade['type'],  # market, limit, etc.
            'token_in': token_in,
            'token_out': token_out,
            'amount_in': amount_in,
            'amount_out': amount_out,
            'token_in_price_usd': prices[token_in],
            'token_out_price_usd': prices[token_out],
            'value_in_usd': amount_in * prices[token_in],
            'value_out_usd': amount_out * prices[token_out],
            'profit_loss_usd': (amount_out * prices[token_out]) - (amount_in * prices[token_in]),
            'gas_cost_usd': trade['gas_cost_usd'],
            'net_profit_loss': (amount_out * prices[token_out]) - 
                             (amount_in * prices[token_in]) - 
                             trade['gas_cost_usd'],
            'exchange': trade['exchange'],
            'market_conditions': {
                'volatility': trade.get('market_volatility', 0),
                'liquidity': trade.get('market_liquidity', 0),
                'spread': trade.get('market_spread', 0)
            },
            'execution_details': {
                'latency_ms': trade.get('execution_latency_ms', 0),
                'slippage_percent': trade.get('slippage_percent', 0),
                'price_impact_percent': trade.get('price_impact_percent', 0)
            }
        }
        
        self.trade_journal.append(trade_record)
        
        # Update strategy performance
        strategy = trade['strategy']
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = {
                'trades_count': 0,
                'total_volume_usd': 0,
                'total_profit_usd': 0,
                'total_loss_usd': 0,
                'net_pnl_usd': 0,
                'win_rate': 0,
                'avg_profit_per_trade': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
            
        perf = self.strategy_performance[strategy]
        perf['trades_count'] += 1
        perf['total_volume_usd'] += trade_record['value_in_usd']
        
        if trade_record['net_profit_loss'] > 0:
            perf['total_profit_usd'] += trade_record['net_profit_loss']
        else:
            perf['total_loss_usd'] += abs(trade_record['net_profit_loss'])
            
        perf['net_pnl_usd'] = perf['total_profit_usd'] - perf['total_loss_usd']
        
        if perf['trades_count'] > 0:
            wins = sum(1 for t in self.trade_journal 
                      if t['strategy'] == strategy and t['net_profit_loss'] > 0)
            perf['win_rate'] = wins / perf['trades_count']
            perf['avg_profit_per_trade'] = perf['net_pnl_usd'] / perf['trades_count']
            
        # Calculate advanced metrics periodically
        if perf['trades_count'] % 10 == 0:
            await self._calculate_advanced_metrics(strategy)
            
        return trade_record

class AdvancedMarketModel:
    def __init__(self):
        self.pool_models = {}
        self.volatility_models = {}
        self.liquidity_history = defaultdict(list)
        
    async def load_pool_data(self, pool_address):
        """Load and model a specific pool's behavior"""
        # Get pool constants
        pool_data = await self._fetch_pool_data(pool_address)
        token0, token1 = pool_data['token0'], pool_data['token1']
        fee = pool_data['fee']
        
        # Create model for constant product or other AMM formula
        if pool_data['type'] == 'uniswapv2':
            model = ConstantProductModel(token0, token1, fee)
        elif pool_data['type'] == 'curve':
            model = StableSwapModel(token0, token1, fee, pool_data['A'])
        else:
            model = GenericAMMModel(token0, token1, fee)
            
        # Initialize with current reserves
        reserves0 = pool_data['reserve0']
        reserves1 = pool_data['reserve1']
        model.update_reserves(reserves0, reserves1)
        
        # Store model
        self.pool_models[pool_address] = model
        
        # Initialize volatility model for this pair
        pair_symbol = f"{token0}_{token1}"
        self.volatility_models[pair_symbol] = VolatilityModel(window_size=100)
        
        return model
        
    async def simulate_trade(self, pool_address, token_in, amount_in):
        """Simulate a trade with current pool state"""
        if pool_address not in self.pool_models:
            await self.load_pool_data(pool_address)
            
        model = self.pool_models[pool_address]
        
        # Get amount out and price impact
        amount_out, price_impact = model.get_amount_out(token_in, amount_in)
        
        # Calculate additional metrics
        execution_price = amount_out / amount_in
        market_price = await self._get_market_price(token_in, model.other_token(token_in))
        slippage = abs(execution_price - market_price) / market_price
        
        # Predict post-trade market response
        volatility = self._get_pair_volatility(model.token0, model.token1)
        mean_reversion_expected = self._calculate_mean_reversion_probability(
            price_impact, volatility, model.fee)
            
        return {
            'amount_out': amount_out,
            'execution_price': execution_price,
            'market_price': market_price,
            'price_impact_percent': price_impact * 100,
            'slippage_percent': slippage * 100,
            'mean_reversion_probability': mean_reversion_expected,
            'optimal_hold_time': self._calculate_optimal_hold_time(price_impact, volatility)
        }

class OptimalExecutionEngine:
    def __init__(self, market_model, blockchain_client):
        self.market_model = market_model
        self.blockchain = blockchain_client
        self.order_strategies = {
            'twap': self._execute_twap,
            'vwap': self._execute_vwap,
            'iceberg': self._execute_iceberg,
            'adaptive': self._execute_adaptive
        }
        
    async def execute_order(self, order_spec):
        """Execute an order with sophisticated placement strategies"""
        strategy = order_spec.get('strategy', 'market')
        
        if strategy == 'market':
            return await self._execute_market_order(order_spec)
        elif strategy in self.order_strategies:
            return await self.order_strategies[strategy](order_spec)
        else:
            raise ValueError(f"Unknown order strategy: {strategy}")
            
    async def _execute_market_order(self, order):
        """Basic market order execution"""
        token_in = order['token_in']
        token_out = order['token_out']
        amount = order['amount']
        
        # Find optimal route
        route = await self._find_optimal_route(token_in, token_out, amount)
        
        # Check price impact
        price_impact = await self.market_model.calculate_price_impact(
            route, token_in, amount)
            
        if price_impact > order.get('max_price_impact', 0.01):
            if order.get('auto_split', False):
                # Split into smaller orders
                return await self._split_and_execute(order, price_impact)
            else:
                raise Exception(f"Price impact too high: {price_impact:.2%}")
                
        # Execute the trade
        return await self.blockchain.execute_swap(
            route,
            token_in,
            token_out,
            amount,
            order.get('min_amount_out', 0),
            order.get('deadline', int(time.time() + 60))
        )
        
    async def _execute_twap(self, order):
        """Time-Weighted Average Price execution"""
        total_amount = order['amount']
        duration = order.get('duration', 3600)  # Default 1 hour
        intervals = order.get('intervals', 10)
        
        # Calculate chunk size
        chunk_size = total_amount / intervals
        
        # Schedule executions
        execution_results = []
        interval_seconds = duration / intervals
        
        for i in range(intervals):
            # Wait until next interval
            if i > 0:
                await asyncio.sleep(interval_seconds)
                
            try:
                # Create sub-order
                sub_order = order.copy()
                sub_order['amount'] = chunk_size
                sub_order['strategy'] = 'market'
                
                # Execute chunk as market order
                result = await self._execute_market_order(sub_order)
                execution_results.append(result)
                
                # Update market models with latest execution
                await self.market_model.update_after_trade(result)
                
            except Exception as e:
                logger.error(f"TWAP chunk {i+1}/{intervals} failed: {e}")
                
                # Implement retry logic if needed
                if order.get('retry_failed', True):
                    backoff = min(30, 2 ** i)  # Exponential backoff
                    await asyncio.sleep(backoff)
                    i -= 1  # Retry same chunk
                
        return {
            'strategy': 'twap',
            'total_chunks': intervals,
            'successful_chunks': len(execution_results),
            'total_input': sum(r['amount_in'] for r in execution_results),
            'total_output': sum(r['amount_out'] for r in execution_results),
            'average_price': sum(r['amount_out'] for r in execution_results) / 
                           sum(r['amount_in'] for r in execution_results),
            'executions': execution_results
        }

class ServiceRegistry:
    """Central registry for coordinating distributed GBPBot services"""
    def __init__(self, redis_url):
        self.redis = aioredis.from_url(redis_url)
        self.services = {}
        self.service_health = {}
        
    async def register_service(self, service_id, service_type, endpoint, capabilities=None):
        """Register a service in the distributed system"""
        service_data = {
            'id': service_id,
            'type': service_type,
            'endpoint': endpoint,
            'capabilities': capabilities or {},
            'registered_at': time.time(),
            'last_heartbeat': time.time()
        }
        
        # Register in Redis with expiration
        await self.redis.hset(f"services:{service_type}", service_id, json.dumps(service_data))
        await self.redis.expire(f"services:{service_type}", 300)  # 5 minute TTL
        
        # Keep local copy
        self.services[service_id] = service_data
        
        return service_id
        
    async def discover_services(self, service_type, capability=None):
        """Discover available services of a specific type"""
        services = await self.redis.hgetall(f"services:{service_type}")
        
        result = []
        for service_id, service_json in services.items():
            service = json.loads(service_json)
            
            # Filter by capability if requested
            if capability is None or capability in service.get('capabilities', {}):
                result.append(service)
                
        return result
        
    async def heartbeat(self, service_id, metrics=None):
        """Send a heartbeat to keep service registration alive"""
        if service_id not in self.services:
            return False
            
        service = self.services[service_id]
        service['last_heartbeat'] = time.time()
        
        if metrics:
            service['metrics'] = metrics
            
        await self.redis.hset(
            f"services:{service['type']}", 
            service_id, 
            json.dumps(service)
        )
        
        # Reset expiration
        await self.redis.expire(f"services:{service['type']}", 300)
        
        return True
        
    async def start_health_monitor(self, check_interval=30):
        """Start monitoring service health"""
        while True:
            try:
                now = time.time()
                for service_type in await self.redis.keys('services:*'):
                    services = await self.redis.hgetall(service_type)
                    
                    for service_id, service_json in services.items():
                        service = json.loads(service_json)
                        last_heartbeat = service.get('last_heartbeat', 0)
                        
                        if now - last_heartbeat > 60:  # 1 minute without heartbeat
                            # Service is potentially down
                            self.service_health[service_id] = 'degraded'
                            
                        if now - last_heartbeat > 180:  # 3 minutes without heartbeat
                            # Service is probably down, clean up
                            await self.redis.hdel(service_type, service_id)
                            self.service_health[service_id] = 'offline'
                        else:
                            self.service_health[service_id] = 'healthy'
                            
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                
            await asyncio.sleep(check_interval)

class DistributedOrderManager:
    def __init__(self, registry, service_id):
        self.registry = registry
        self.service_id = service_id
        self.local_queue = asyncio.PriorityQueue()
        self.redis = registry.redis
        self.processing_lock = None
        
    async def submit_order(self, order, priority=0):
        """Submit an order to the distributed queue"""
        order_id = order.get('id', str(uuid.uuid4()))
        order['id'] = order_id
        order['submitted_at'] = time.time()
        order['priority'] = priority
        order['status'] = 'pending'
        
        # Store order data
        await self.redis.set(
            f"orders:{order_id}", 
            json.dumps(order),
            ex=3600  # 1 hour expiration
        )
        
        # Add to priority queue
        await self.redis.zadd(
            "order_queue",
            {order_id: priority}
        )
        
        # Notify other services
        await self.redis.publish(
            "new_order", 
            json.dumps({"order_id": order_id, "priority": priority})
        )
        
        return order_id
        
    async def claim_next_order(self):
        """Attempt to claim the next order with distributed locking"""
        # Get highest priority order
        next_orders = await self.redis.zrange(
            "order_queue", 
            0, 0,  # Get highest priority (lowest score)
            withscores=True
        )
        
        if not next_orders:
            return None
            
        order_id, priority = next_orders[0]
        
        # Try to acquire lock
        lock_key = f"order_lock:{order_id}"
        self.processing_lock = await self.redis.set(
            lock_key,
            self.service_id,
            nx=True,  # Only set if not exists
            ex=30      # 30 second timeout
        )
        
        if not self.processing_lock:
            # Another service claimed it
            return None
            
        # Get order data
        order_data = await self.redis.get(f"orders:{order_id}")
        if not order_data:
            # Order expired or was removed
            await self.redis.zrem("order_queue", order_id)
            return None
            
        order = json.loads(order_data)
        
        # Update status
        order['status'] = 'processing'
        order['claimed_by'] = self.service_id
        order['claimed_at'] = time.time()
        
        await self.redis.set(
            f"orders:{order_id}",
            json.dumps(order),
            ex=3600
        )
        
        # Start lock renewal task
        self._start_lock_renewal(lock_key)
        
        return order
        
    async def _renew_lock(self, lock_key):
        """Keep renewing the lock while processing"""
        while self.processing_lock:
            try:
                # Extend lock expiration
                extended = await self.redis.expire(lock_key, 30)
                if not extended:
                    # Lock was lost
                    self.processing_lock = None
                    break
                    
                await asyncio.sleep(10)  # Renew every 10 seconds
            except Exception as e:
                logger.error(f"Error renewing lock: {e}")
                self.processing_lock = None
                break
        
    def _start_lock_renewal(self, lock_key):
        """Start background task to renew lock"""
        asyncio.create_task(self._renew_lock(lock_key))
        
    async def complete_order(self, order_id, result):
        """Mark an order as completed and release the lock"""
        if not self.processing_lock:
            return False
            
        # Update order status
        order_data = await self.redis.get(f"orders:{order_id}")
        if not order_data:
            return False
            
        order = json.loads(order_data)
        order['status'] = 'completed'
        order['completed_at'] = time.time()
        order['result'] = result
        
        # Save updated order
        await self.redis.set(
            f"orders:{order_id}",
            json.dumps(order),
            ex=86400  # Keep completed orders for 24 hours
        )
        
        # Remove from queue
        await self.redis.zrem("order_queue", order_id)
        
        # Release lock
        lock_key = f"order_lock:{order_id}"
        await self.redis.delete(lock_key)
        self.processing_lock = None
        
        # Notify completion
        await self.redis.publish(
            "order_completed",
            json.dumps({"order_id": order_id, "service_id": self.service_id})
        )
        
        return True

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 