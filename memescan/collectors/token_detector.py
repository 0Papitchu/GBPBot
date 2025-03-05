import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from loguru import logger
from web3 import Web3
from web3.exceptions import ExtraDataLengthError

from memescan.utils.config import Config
from memescan.storage.database import Database

# Fonction pour créer un middleware personnalisé pour les chaînes PoA
# Fonction supprimée car non nécessaire avec web3.py v7.8.0

class TokenDetector:
    """Détecteur en temps réel de nouveaux tokens sur les DEX"""
    
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.known_tokens = set()  # Cache des tokens déjà détectés
        self.last_scan_block = {}  # Dernier bloc scanné par chaîne
        
        # Initialiser les connexions Web3
        self.web3_connections = {}
        self._init_web3_connections()
        
        # Événements à surveiller (création de paires sur les DEX)
        self.dex_factory_events = {
            "avalanche": {
                "trader_joe": {
                    "address": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10",  # TraderJoe Factory
                    "event": "PairCreated",
                    "abi": [{"anonymous":False,"inputs":[{"indexed":True,"name":"token0","type":"address"},{"indexed":True,"name":"token1","type":"address"},{"indexed":False,"name":"pair","type":"address"},{"indexed":False,"name":"","type":"uint256"}],"name":"PairCreated","type":"event"}]
                }
            },
            "solana": {
                # Pour Solana, nous utiliserons une approche différente via l'API
            },
            "sonic": {
                "pump_fun": {
                    "address": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",  # Exemple d'adresse (à remplacer)
                    "event": "PairCreated",
                    "abi": [{"anonymous":False,"inputs":[{"indexed":True,"name":"token0","type":"address"},{"indexed":True,"name":"token1","type":"address"},{"indexed":False,"name":"pair","type":"address"},{"indexed":False,"name":"","type":"uint256"}],"name":"PairCreated","type":"event"}]
                }
            }
        }
        
        # Adresses des tokens stables pour identifier les nouvelles paires
        self.stable_tokens = {
            "avalanche": [
                "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",  # USDC
                "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",  # USDT
                "0xd586E7F844cEa2F87f50152665BCbc2C279D8d70",  # DAI
                "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",  # WETH
                "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"   # WAVAX
            ],
            "sonic": [
                # Adresses des stablecoins sur Sonic (à compléter)
            ]
        }
        
        # Seuils de détection
        self.min_liquidity_usd = 500  # Liquidité minimale en USD
        self.max_initial_mcap = 15000  # Market cap maximum pour considérer un token comme "très tôt"
        
    def _init_web3_connections(self):
        """Initialise les connexions Web3 pour chaque chaîne"""
        # Avalanche
        self.web3_avax = Web3(Web3.HTTPProvider(self.config['rpc_endpoints']['avalanche']))
        # Middleware PoA non nécessaire avec web3.py v7.8.0
        
        # Sonic
        self.web3_sonic = Web3(Web3.HTTPProvider(self.config['rpc_endpoints']['sonic']))
        # Middleware PoA non nécessaire avec web3.py v7.8.0
        
        # Logger les connexions initialisées
        self.web3_connections = {
            "avalanche": self.web3_avax,
            "sonic": self.web3_sonic
        }
        logger.info(f"Web3 connections initialized for {len(self.web3_connections)} chains")
    
    async def start_monitoring(self):
        """Démarre la surveillance en temps réel des nouveaux tokens"""
        logger.info("Starting real-time token detection")
        
        # Charger les tokens connus depuis la base de données
        await self._load_known_tokens()
        
        # Démarrer les tâches de surveillance pour chaque chaîne
        tasks = []
        for chain in self.web3_connections:
            if chain in self.dex_factory_events:
                for dex_name, dex_info in self.dex_factory_events[chain].items():
                    tasks.append(
                        asyncio.create_task(
                            self._monitor_dex_factory(chain, dex_name, dex_info)
                        )
                    )
        
        # Ajouter la tâche pour Solana (via API)
        tasks.append(asyncio.create_task(self._monitor_solana_new_tokens()))
        
        # Exécuter toutes les tâches en parallèle
        await asyncio.gather(*tasks)
    
    async def _load_known_tokens(self):
        """Charge les tokens connus depuis la base de données"""
        try:
            query = "SELECT address FROM tokens"
            async with self.db.async_session() as session:
                result = await session.execute(query)
                addresses = [row[0] for row in result]
                
            self.known_tokens = set(addresses)
            logger.info(f"Loaded {len(self.known_tokens)} known tokens from database")
            
        except Exception as e:
            logger.error(f"Error loading known tokens: {str(e)}")
    
    async def _monitor_dex_factory(self, chain: str, dex_name: str, dex_info: Dict):
        """Surveille les événements de création de paires sur un DEX"""
        logger.info(f"Starting monitoring for new tokens on {chain}/{dex_name}")
        
        web3 = self.web3_connections.get(chain)
        if not web3:
            logger.error(f"No Web3 connection available for {chain}")
            return
            
        # Créer le contrat pour l'usine de paires
        factory_contract = web3.eth.contract(
            address=web3.to_checksum_address(dex_info["address"]),
            abi=dex_info["abi"]
        )
        
        # Obtenir le dernier bloc
        if chain not in self.last_scan_block:
            self.last_scan_block[chain] = web3.eth.block_number - 1000  # Commencer 1000 blocs en arrière
        
        while True:
            try:
                current_block = web3.eth.block_number
                from_block = self.last_scan_block[chain] + 1
                to_block = current_block
                
                # Éviter de scanner trop de blocs à la fois
                if to_block - from_block > 5000:
                    to_block = from_block + 5000
                
                if from_block <= to_block:
                    logger.debug(f"Scanning {chain}/{dex_name} from block {from_block} to {to_block}")
                    
                    # Obtenir les événements de création de paires
                    pair_events = factory_contract.events[dex_info["event"]].get_logs(
                        fromBlock=from_block,
                        toBlock=to_block
                    )
                    
                    # Traiter chaque événement
                    for event in pair_events:
                        await self._process_pair_created_event(chain, dex_name, event)
                    
                    # Mettre à jour le dernier bloc scanné
                    self.last_scan_block[chain] = to_block
                    
                # Attendre avant la prochaine vérification
                # Temps d'attente court pour être très réactif
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error monitoring {chain}/{dex_name}: {str(e)}")
                await asyncio.sleep(10)  # Attendre plus longtemps en cas d'erreur
    
    async def _process_pair_created_event(self, chain: str, dex_name: str, event):
        """Traite un événement de création de paire pour détecter de nouveaux tokens"""
        try:
            # Extraire les adresses des tokens
            token0 = event["args"]["token0"]
            token1 = event["args"]["token1"]
            pair_address = event["args"]["pair"]
            
            # Vérifier si l'un des tokens est un stablecoin ou token majeur
            stable_tokens = self.stable_tokens.get(chain, [])
            
            new_token = None
            paired_with = None
            
            if token0.lower() in [t.lower() for t in stable_tokens]:
                new_token = token1
                paired_with = token0
            elif token1.lower() in [t.lower() for t in stable_tokens]:
                new_token = token0
                paired_with = token1
            
            # Si nous avons identifié un nouveau token potentiel
            if new_token and new_token.lower() not in [t.lower() for t in self.known_tokens]:
                # Analyser immédiatement le token
                token_info = await self._analyze_new_token(chain, dex_name, new_token, paired_with, pair_address)
                
                if token_info:
                    # Vérifier si le market cap est suffisamment bas (entrée très tôt)
                    if token_info.get("market_cap", float("inf")) <= self.max_initial_mcap:
                        # Enregistrer le token dans la base de données
                        await self._store_new_token(token_info)
                        
                        # Déclencher l'analyse et le sniping automatique
                        await self._trigger_sniping_analysis(token_info)
                        
                        logger.info(f"🚀 NEW TOKEN DETECTED: {token_info['symbol']} on {chain}/{dex_name} - Market Cap: ${token_info.get('market_cap', 'N/A')}")
                    else:
                        logger.debug(f"New token {token_info['symbol']} detected but market cap too high: ${token_info.get('market_cap', 'N/A')}")
                
        except Exception as e:
            logger.error(f"Error processing pair event: {str(e)}")
    
    async def _analyze_new_token(self, chain: str, dex_name: str, token_address: str, paired_with: str, pair_address: str) -> Optional[Dict]:
        """Analyse un nouveau token pour déterminer s'il est intéressant"""
        try:
            web3 = self.web3_connections.get(chain)
            if not web3:
                return None
                
            # ABI minimal pour un token ERC20
            token_abi = [
                {"constant":True,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":False,"stateMutability":"view","type":"function"},
                {"constant":True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":False,"stateMutability":"view","type":"function"},
                {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":False,"stateMutability":"view","type":"function"},
                {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"}
            ]
            
            # ABI minimal pour une paire
            pair_abi = [
                {"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"payable":False,"stateMutability":"view","type":"function"},
                {"constant":True,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"},
                {"constant":True,"inputs":[],"name":"token1","outputs":[{"name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"}
            ]
            
            # Créer les contrats
            token_contract = web3.eth.contract(address=web3.to_checksum_address(token_address), abi=token_abi)
            pair_contract = web3.eth.contract(address=web3.to_checksum_address(pair_address), abi=pair_abi)
            
            # Obtenir les informations de base du token
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            total_supply = token_contract.functions.totalSupply().call() / (10 ** decimals)
            
            # Vérifier si c'est un meme coin (heuristique simple)
            is_meme = self._check_if_meme_coin(name, symbol)
            
            # Obtenir les réserves de la paire
            reserves = pair_contract.functions.getReserves().call()
            token0 = pair_contract.functions.token0().call().lower()
            
            # Déterminer quelle réserve correspond au nouveau token
            if token_address.lower() == token0:
                token_reserve = reserves[0] / (10 ** decimals)
                stable_reserve = reserves[1] / (10 ** 6)  # Supposons 6 décimales pour le stablecoin
            else:
                token_reserve = reserves[1] / (10 ** decimals)
                stable_reserve = reserves[0] / (10 ** 6)
            
            # Calculer le prix et la liquidité
            if token_reserve > 0:
                price = stable_reserve / token_reserve
            else:
                price = 0
                
            liquidity_usd = stable_reserve * 2  # Approximation de la liquidité totale
            market_cap = total_supply * price
            
            # Vérifier si la liquidité est suffisante
            if liquidity_usd < self.min_liquidity_usd:
                logger.debug(f"Token {symbol} has insufficient liquidity: ${liquidity_usd}")
                return None
            
            # Créer l'objet token
            token_info = {
                "address": token_address,
                "name": name,
                "symbol": symbol,
                "chain": chain,
                "decimals": decimals,
                "total_supply": total_supply,
                "price": price,
                "liquidity_usd": liquidity_usd,
                "market_cap": market_cap,
                "paired_with": paired_with,
                "pair_address": pair_address,
                "dex": dex_name,
                "is_meme": is_meme,
                "created_at": datetime.now().isoformat(),
                "holders": 1,  # Valeur par défaut, sera mise à jour plus tard
                "transactions_24h": 0
            }
            
            return token_info
            
        except Exception as e:
            logger.error(f"Error analyzing new token {token_address}: {str(e)}")
            return None
    
    def _check_if_meme_coin(self, name: str, symbol: str) -> bool:
        """Vérifie si un token est probablement un meme coin basé sur son nom et symbole"""
        name_lower = name.lower()
        symbol_lower = symbol.lower()
        
        # Liste de mots-clés associés aux meme coins
        meme_keywords = [
            "doge", "shib", "inu", "elon", "moon", "safe", "cum", "chad", "pepe",
            "wojak", "cat", "kitty", "baby", "rocket", "mars", "moon", "lambo",
            "diamond", "hands", "ape", "gorilla", "banana", "tendies", "stonk",
            "meme", "coin", "token", "ai", "gpt", "chat", "floki", "cheems"
        ]
        
        # Vérifier si l'un des mots-clés est présent
        for keyword in meme_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return True
                
        return False
    
    async def _store_new_token(self, token_info: Dict):
        """Stocke un nouveau token dans la base de données"""
        try:
            # Insérer le token dans la table tokens
            query = """
                INSERT INTO tokens (
                    address, name, symbol, chain, decimals, 
                    total_supply, created_at, is_meme
                ) VALUES (
                    :address, :name, :symbol, :chain, :decimals,
                    :total_supply, :created_at, :is_meme
                )
                ON CONFLICT (address) DO NOTHING
            """
            
            async with self.db.async_session() as session:
                await session.execute(query, token_info)
                
                # Insérer les métriques initiales
                metrics_query = """
                    INSERT INTO token_metrics (
                        token_address, price, volume_24h, volume_1h,
                        tvl, holders, transactions_24h, timestamp
                    ) VALUES (
                        :address, :price, 0, 0,
                        :liquidity_usd, :holders, :transactions_24h, NOW()
                    )
                """
                
                await session.execute(metrics_query, token_info)
                await session.commit()
                
            # Ajouter à l'ensemble des tokens connus
            self.known_tokens.add(token_info["address"])
            
        except Exception as e:
            logger.error(f"Error storing new token: {str(e)}")
    
    async def _trigger_sniping_analysis(self, token_info: Dict):
        """Déclenche l'analyse de sniping et l'action automatique si nécessaire"""
        try:
            # Créer un événement de sniping
            sniping_event = {
                "token_address": token_info["address"],
                "token_symbol": token_info["symbol"],
                "chain": token_info["chain"],
                "dex": token_info["dex"],
                "price": token_info["price"],
                "liquidity": token_info["liquidity_usd"],
                "market_cap": token_info["market_cap"],
                "is_meme": token_info["is_meme"],
                "detection_time": datetime.now().isoformat(),
                "status": "detected"
            }
            
            # Stocker l'événement dans la base de données
            query = """
                INSERT INTO sniping_events (
                    token_address, token_symbol, chain, dex,
                    price, liquidity, market_cap, is_meme,
                    detection_time, status
                ) VALUES (
                    :token_address, :token_symbol, :chain, :dex,
                    :price, :liquidity, :market_cap, :is_meme,
                    :detection_time, :status
                )
                RETURNING id
            """
            
            async with self.db.async_session() as session:
                result = await session.execute(query, sniping_event)
                event_id = result.scalar_one()
                await session.commit()
            
            # Publier l'événement pour traitement par le module de sniping
            # (Ceci sera implémenté via un système de message ou un appel direct)
            logger.info(f"Triggered sniping analysis for {token_info['symbol']} (ID: {event_id})")
            
        except Exception as e:
            logger.error(f"Error triggering sniping analysis: {str(e)}")
    
    async def _monitor_solana_new_tokens(self):
        """Surveille les nouveaux tokens sur Solana via API"""
        logger.info("Starting monitoring for new tokens on Solana")
        
        while True:
            try:
                # Implémentation à venir - utilisation de l'API Solana
                # pour détecter les nouveaux tokens
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error monitoring Solana: {str(e)}")
                await asyncio.sleep(30) 