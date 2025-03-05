from typing import Dict, List, Optional, Tuple
import asyncio
from loguru import logger
from web3 import Web3
import time
from datetime import datetime
import json
import requests
from sklearn.ensemble import IsolationForest
import re
from web3.exceptions import ContractLogicError

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.price_feed import PriceManager
from gbpbot.core.performance_tracker import PerformanceTracker
from gbpbot.config.trading_config import TradingConfig

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None
# Variables utilisées dans les fixtures
status = None
highest_price = None
enabled = None
percentage = None
initial = None
trailing = None
min_whale_amount = None
emergency_exit_threshold = None

class TokenDetection:
    """Module pour la détection des nouveaux tokens et l'analyse des transactions"""
    
    def __init__(self, blockchain: BlockchainClient):
        """
        Initialise le module de détection des tokens
        
        Args:
            blockchain: Instance du client blockchain
        """
        self.blockchain = blockchain
        self.web3 = blockchain.web3
        self.price_feed = PriceManager(self.web3)
        self.performance_tracker = PerformanceTracker()
        
        # Charger la configuration
        self.config = self._load_config()
        
        # Cache des tokens déjà détectés
        self.detected_tokens = set()
        
        # Abonnement aux événements blockchain
        self.event_filters = {}
        
        logger.info("✅ Module de détection des tokens initialisé")
    
    def _load_config(self) -> Dict:
        """Charge la configuration de détection des tokens"""
        # Utiliser la configuration spécifique au sniping
        config = TradingConfig.get_sniping_config()
        
        # Vérifier si une configuration "tokens" existe et la fusionner 
        # avec la configuration de sniping si disponible
        try:
            # On recherche d'abord dans le fichier de configuration principal
            from gbpbot.config.config_loader import ConfigLoader
            main_config = ConfigLoader.get_config()
            
            if "tokens" in main_config:
                # Ajouter les informations sur les tokens
                if "tokens" not in config:
                    config["tokens"] = {}
                    
                config["tokens"].update(main_config["tokens"])
                logger.info("✅ Configuration des tokens chargée avec succès")
            else:
                logger.warning("⚠️ Section de configuration non trouvée: tokens")
                
            # Vérifier si la configuration de sniping existe aussi dans le fichier principal
            if "sniping" in main_config:
                # Fusionner les configurations (priorité au fichier de configuration)
                for section, section_config in main_config["sniping"].items():
                    if section in config:
                        config[section].update(section_config)
                    else:
                        config[section] = section_config
                logger.info("✅ Configuration de sniping personnalisée chargée avec succès")
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors du chargement de la configuration: {str(e)}")
            logger.warning("⚠️ Utilisation de la configuration par défaut")
            
        return config
    
    async def start_monitoring(self):
        """Démarre le monitoring des nouveaux tokens avec analyse des transactions"""
        logger.info("🔍 Démarrage du monitoring des nouveaux tokens avec analyse des transactions")
        
        # Configurer les filtres d'événements pour les factory des DEX
        await self._setup_event_filters()
        
        # Initialiser le modèle de détection de patterns
        self.pattern_detector = IsolationForest(contamination=0.1)
        
        # Initialiser le dictionnaire des transactions actives
        self.active_trades = {}
        
        # Démarrer le thread de gestion des trades actifs
        asyncio.create_task(self._manage_active_trades())
        
        # Boucle principale de monitoring
        while True:
            try:
                # Vérifier les nouveaux tokens sur TraderJoe
                await self._check_new_pairs(self.config["trader_joe_factory"], "trader_joe")
                
                # Vérifier les nouveaux tokens sur Pangolin
                await self._check_new_pairs(self.config["pangolin_factory"], "pangolin")
                
                # Analyser les transactions initiales
                await self._analyze_initial_transactions()
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(5)  # Vérifier toutes les 5 secondes
                
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle de détection des tokens: {str(e)}")
                await asyncio.sleep(5)  # Attendre avant de réessayer
    
    async def _setup_event_filters(self):
        """Configure les filtres d'événements pour les factory des DEX"""
        factory_abi = self._load_factory_abi()
        
        try:
            # Récupérer les adresses des factories depuis la configuration
            factory_addresses = self.config["detection"]["factory_addresses"]
            
            for dex_name, factory_address in factory_addresses.items():
                logger.info(f"🔍 Configuration du filtre d'événements pour {dex_name}")
                factory_contract = self.web3.eth.contract(address=factory_address, abi=factory_abi)
                
                # Créer un filtre pour l'événement PairCreated
                self.event_filters[dex_name] = factory_contract.events.PairCreated.create_filter(fromBlock='latest')
                
                # Lancer une tâche asynchrone pour vérifier les nouvelles paires
                asyncio.create_task(self._check_new_pairs(factory_address, dex_name))
                
            logger.info(f"✅ {len(factory_addresses)} filtres d'événements configurés")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la configuration des filtres d'événements: {str(e)}")
            # Réessayer avec des valeurs par défaut si la configuration échoue
            default_factories = {
                "trader_joe": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10",
                "pangolin": "0xefa94DE7a4656D787667C749f7E1223D71E9FD88"
            }
            
            logger.info("⚠️ Utilisation des adresses de factory par défaut")
            
            for dex_name, factory_address in default_factories.items():
                logger.info(f"🔍 Configuration du filtre d'événements pour {dex_name} (défaut)")
                factory_contract = self.web3.eth.contract(address=factory_address, abi=factory_abi)
                
                # Créer un filtre pour l'événement PairCreated
                self.event_filters[dex_name] = factory_contract.events.PairCreated.create_filter(fromBlock='latest')
                
                # Lancer une tâche asynchrone pour vérifier les nouvelles paires
                asyncio.create_task(self._check_new_pairs(factory_address, dex_name))
    
    def _load_factory_abi(self) -> List:
        """Charge l'ABI du factory"""
        # TODO: Charger l'ABI depuis un fichier
        # Pour l'instant, utiliser un ABI minimal
        return [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "token0", "type": "address"},
                    {"indexed": True, "name": "token1", "type": "address"},
                    {"indexed": False, "name": "pair", "type": "address"},
                    {"indexed": False, "name": "param", "type": "uint256"}
                ],
                "name": "PairCreated",
                "type": "event"
            }
        ]
    
    async def _check_new_pairs(self, factory_address: str, dex_name: str):
        """
        Vérifie les nouveaux pairs sur un DEX
        
        Args:
            factory_address: Adresse du factory
            dex_name: Nom du DEX
        """
        try:
            # Récupérer les nouveaux événements
            events = self.event_filters[dex_name].get_new_entries()
            
            for event in events:
                token0 = event.args.token0
                token1 = event.args.token1
                pair_address = event.args.pair
                
                # Vérifier si l'un des tokens est WAVAX
                wavax_address = self.blockchain.token_addresses["WAVAX"]
                
                if token0 == wavax_address:
                    new_token = token1
                    base_token = token0
                elif token1 == wavax_address:
                    new_token = token0
                    base_token = token1
                else:
                    # Ignorer les paires qui ne contiennent pas WAVAX
                    continue
                
                # Vérifier si le token a déjà été détecté
                if new_token in self.detected_tokens:
                    continue
                
                # Ajouter le token à la liste des tokens détectés
                self.detected_tokens.add(new_token)
                
                logger.info(f"🔔 Nouveau token détecté sur {dex_name}: {new_token}")
                
                # Analyser le token
                asyncio.create_task(self._analyze_token(new_token, base_token, pair_address, dex_name))
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification des nouveaux pairs sur {dex_name}: {str(e)}")
    
    async def _analyze_token(self, token_address: str, base_token: str, pair_address: str, dex_name: str):
        """
        Analyse un nouveau token pour déterminer s'il est intéressant
        
        Args:
            token_address: Adresse du nouveau token
            base_token: Adresse du token de base (WAVAX)
            pair_address: Adresse de la paire
            dex_name: Nom du DEX
        """
        try:
            logger.info(f"🔍 Analyse du token {token_address}")
            
            # 1. Vérifier si c'est un honeypot
            is_honeypot, honeypot_info = await self._check_honeypot(token_address)
            
            if is_honeypot:
                logger.warning(f"⚠️ Token {token_address} détecté comme honeypot: {honeypot_info}")
                return
            
            # 2. Vérifier la liquidité
            liquidity = await self._check_liquidity(pair_address)
            
            if liquidity < self.config["min_liquidity"]:
                logger.warning(f"⚠️ Liquidité insuffisante pour {token_address}: {Web3.from_wei(liquidity, 'ether')} AVAX")
                return
            
            # 3. Vérifier si la liquidité est bloquée
            is_locked, lock_info = await self._check_liquidity_lock(pair_address)
            
            if not is_locked:
                logger.warning(f"⚠️ Liquidité non bloquée pour {token_address}")
                return
            
            # 4. Vérifier les taxes
            buy_tax, sell_tax = await self._check_taxes(token_address)
            
            if buy_tax > self.config["max_buy_tax"] or sell_tax > self.config["max_sell_tax"]:
                logger.warning(f"⚠️ Taxes trop élevées pour {token_address}: Buy {buy_tax}%, Sell {sell_tax}%")
                return
            
            # 5. Simuler une vente pour vérifier si le token peut être vendu
            router_address = self._get_router_address(dex_name)
            can_sell, error = await self._simulate_sell(token_address, router_address)
            
            if not can_sell:
                logger.warning(f"⚠️ Le token {token_address} ne peut pas être vendu: {error}")
                return
            
            # 6. Analyser le contrat pour détecter les fonctions dangereuses
            is_safe, contract_analysis = await self._analyze_contract_code(token_address)
            
            if not is_safe:
                logger.warning(f"⚠️ Le contrat du token {token_address} contient des fonctions dangereuses: {contract_analysis}")
                # On peut continuer mais avec prudence
            
            # Si toutes les vérifications sont passées, le token est intéressant
            logger.success(f"✅ Token {token_address} validé pour sniping!")
            
            # Exécuter le snipe avec frontrunning
            await self._prepare_and_send_transaction(token_address, base_token, dex_name)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse du token {token_address}: {str(e)}")
    
    async def _check_honeypot(self, token_address: str) -> Tuple[bool, str]:
        """
        Vérifie si un token est un honeypot
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Tuple (is_honeypot, info)
        """
        try:
            response = requests.get(f"{self.config['honeypot_checker_api']}?address={token_address}")
            if response.status_code == 200:
                data = response.json()
                if data.get('is_honeypot', False):
                    return True, "Token détecté comme honeypot"
                else:
                    return False, ""
            else:
                logger.error(f"Erreur lors de la vérification du honeypot: {response.status_code}")
                return False, "Erreur API"
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du honeypot: {str(e)}")
            return False, "Erreur Exception"
    
    async def _check_liquidity(self, pair_address: str) -> int:
        """
        Vérifie la liquidité d'une paire
        
        Args:
            pair_address: Adresse de la paire
            
        Returns:
            Liquidité en wei
        """
        try:
            pair_contract = self.web3.eth.contract(address=pair_address, abi=self._load_pair_abi())
            reserves = pair_contract.functions.getReserves().call()
            # Supposons que le token0 est WAVAX
            liquidity = reserves[0]  # Liquidité en token0 (WAVAX)
            return liquidity
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la liquidité: {str(e)}")
            return 0
    
    def _load_pair_abi(self) -> List:
        """Charge l'ABI de la paire"""
        # TODO: Charger l'ABI depuis un fichier
        # Pour l'instant, utiliser un ABI minimal
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "_reserve0", "type": "uint112"},
                    {"name": "_reserve1", "type": "uint112"},
                    {"name": "_blockTimestampLast", "type": "uint32"}
                ],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def _check_liquidity_lock(self, pair_address: str) -> Tuple[bool, Dict]:
        """
        Vérifie si la liquidité est bloquée en utilisant les API d'explorateurs de blockchain
        
        Args:
            pair_address: Adresse de la paire
            
        Returns:
            Tuple (is_locked, lock_info)
        """
        try:
            # Vérifier si la paire est verrouillée sur un locker connu
            # Liste des adresses de lockers connus
            known_lockers = [
                "0x000000000000000000000000000000000000dEaD",  # Burn address
                "0x407993575c91ce7643a4d4cCACc9A98c36eE1BBE",  # PinkLock
                "0xc3f8a0F5841aBFf777d3eefA5047e8D413a1C9AB",  # Unicrypt
                "0x86cc280D0BAC0BD4EA38BADc2E268A34432E5D8c"   # Team Finance
            ]
            
            # Vérifier les transferts de LP vers les lockers
            for locker in known_lockers:
                # Utiliser l'API Snowtrace pour vérifier les transferts
                api_url = f"https://api.snowtrace.io/api?module=account&action=tokentx&address={locker}&contractaddress={pair_address}"
                response = requests.get(api_url)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1" and len(data.get("result", [])) > 0:
                        # Calculer le pourcentage de LP verrouillé
                        locked_amount = sum(int(tx["value"]) for tx in data["result"])
                        total_supply = await self._get_pair_total_supply(pair_address)
                        
                        if total_supply > 0:
                            percent_locked = (locked_amount / total_supply) * 100
                            
                            # Vérifier si le pourcentage verrouillé est suffisant
                            if percent_locked >= self.config["min_locked_liquidity_percent"]:
                                # Vérifier la durée du lock (si disponible)
                                lock_time = self._estimate_lock_time(data["result"])
                                
                                lock_info = {
                                    "percent_locked": percent_locked,
                                    "lock_time": lock_time,
                                    "locker": locker
                                }
                                
                                return True, lock_info
            
            return False, {}
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification du lock de liquidité: {str(e)}")
            return False, {}
    
    async def _get_pair_total_supply(self, pair_address: str) -> int:
        """
        Récupère le total supply d'une paire LP
        
        Args:
            pair_address: Adresse de la paire
            
        Returns:
            Total supply
        """
        try:
            pair_contract = self.web3.eth.contract(address=pair_address, abi=self._load_pair_abi_with_supply())
            return pair_contract.functions.totalSupply().call()
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du total supply: {str(e)}")
            return 0
    
    def _load_pair_abi_with_supply(self) -> List:
        """Charge l'ABI de la paire avec la fonction totalSupply"""
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "_reserve0", "type": "uint112"},
                    {"name": "_reserve1", "type": "uint112"},
                    {"name": "_blockTimestampLast", "type": "uint32"}
                ],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _estimate_lock_time(self, transactions: List[Dict]) -> int:
        """
        Estime la durée du lock de liquidité
        
        Args:
            transactions: Liste des transactions
            
        Returns:
            Durée estimée en secondes
        """
        # Par défaut, on suppose un lock de 30 jours
        default_lock_time = 30 * 24 * 60 * 60
        
        # TODO: Implémenter une logique plus précise pour estimer la durée du lock
        # Pour l'instant, on retourne la valeur par défaut
        return default_lock_time
    
    async def _analyze_contract_code(self, token_address: str) -> Tuple[bool, Dict]:
        """
        Analyse le code du contrat pour détecter les fonctions dangereuses
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Tuple (is_safe, details)
        """
        try:
            # Récupérer le code source du contrat via l'API Snowtrace
            api_url = f"https://api.snowtrace.io/api?module=contract&action=getsourcecode&address={token_address}"
            response = requests.get(api_url)
            
            if response.status_code != 200:
                return False, {"error": "Impossible de récupérer le code source"}
            
            data = response.json()
            if data.get("status") != "1" or not data.get("result"):
                return False, {"error": "Code source non vérifié"}
            
            source_code = data["result"][0].get("SourceCode", "")
            
            # Vérifier les fonctions dangereuses
            dangerous_functions = {
                "setTaxFeePercent": "Peut modifier les taxes",
                "setMaxTxAmount": "Peut limiter les transactions",
                "excludeFromFee": "Peut exclure des adresses des frais",
                "setRouterAddress": "Peut changer le routeur",
                "transferOwnership": "Peut transférer la propriété",
                "mint": "Peut créer de nouveaux tokens",
                "pause": "Peut mettre en pause les transactions",
                "blacklist": "Peut blacklister des adresses"
            }
            
            found_dangerous = {}
            for func, description in dangerous_functions.items():
                if re.search(f"function\s+{func}\s*\(", source_code):
                    found_dangerous[func] = description
            
            is_safe = len(found_dangerous) == 0
            
            return is_safe, {"dangerous_functions": found_dangerous}
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse du contrat: {str(e)}")
            return False, {"error": str(e)}
    
    async def _simulate_sell(self, token_address: str, router_address: str) -> Tuple[bool, str]:
        """
        Simule une vente pour vérifier si le token peut être vendu
        
        Args:
            token_address: Adresse du token
            router_address: Adresse du routeur
            
        Returns:
            Tuple (can_sell, error_message)
        """
        try:
            # Charger l'ABI du routeur
            router_abi = self._load_router_abi()
            
            # Créer le contrat du routeur
            router = self.web3.eth.contract(address=router_address, abi=router_abi)
            
            # Adresse WAVAX
            wavax_address = self.blockchain.token_addresses["WAVAX"]
            
            # Montant à vendre (très petit pour la simulation)
            amount_to_sell = 1000  # Valeur symbolique
            
            # Chemin de swap
            path = [token_address, wavax_address]
            
            # Deadline
            deadline = int(time.time()) + 60  # 1 minute
            
            # Simuler la vente
            try:
                # Utiliser call() pour simuler la transaction sans l'envoyer
                router.functions.swapExactTokensForAVAX(
                    amount_to_sell,
                    0,  # Montant minimum à recevoir (0 pour la simulation)
                    path,
                    self.web3.eth.default_account,
                    deadline
                ).call()
                
                return True, ""
            except ContractLogicError as e:
                error_message = str(e)
                logger.warning(f"⚠️ Simulation de vente échouée: {error_message}")
                return False, error_message
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la simulation de vente: {str(e)}")
            return False, str(e)
    
    def _load_router_abi(self) -> List:
        """Charge l'ABI du routeur"""
        # TODO: Charger l'ABI depuis un fichier
        # Pour l'instant, utiliser un ABI minimal
        return [
            {
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "path", "type": "address[]"},
                    {"name": "to", "type": "address"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForAVAX",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    async def _prepare_and_send_transaction(self, token_address: str, base_token: str, dex_name: str):
        """Prépare et envoie une transaction pré-signée avec des frais de gas dynamiques et frontrunning"""
        logger.info(f"🚀 Préparation de la transaction pour {token_address}")
        
        # Vérifier si le token peut être vendu (anti-honeypot)
        router_address = self._get_router_address(dex_name)
        can_sell, error = await self._simulate_sell(token_address, router_address)
        
        if not can_sell:
            logger.error(f"❌ Le token {token_address} ne peut pas être vendu: {error}")
            return
        
        # Analyser le contrat pour détecter les fonctions dangereuses
        is_safe, contract_analysis = await self._analyze_contract_code(token_address)
        
        if not is_safe:
            logger.warning(f"⚠️ Le contrat du token {token_address} contient des fonctions dangereuses: {contract_analysis}")
            # On peut continuer mais avec prudence (montant plus faible)
            initial_amount = self.config["initial_buy_amount"] / 2
        else:
            initial_amount = self.config["initial_buy_amount"]
        
        # Préparer la transaction d'achat
        buy_tx = await self._prepare_swap_transaction(base_token, token_address, initial_amount, router_address)
        
        if not buy_tx:
            logger.error(f"❌ Impossible de préparer la transaction d'achat pour {token_address}")
            return
        
        # Optimiser les frais de gas pour le frontrunning
        current_gas_price = self.web3.eth.gas_price
        
        # Stratégie de frontrunning: augmenter le gas price de 30% pour passer devant les autres
        frontrun_gas_price = int(current_gas_price * 1.3)
        
        # Utiliser Flashbots si disponible (sur Avalanche)
        use_flashbots = self.config.get("use_flashbots", False)
        
        if use_flashbots:
            # TODO: Implémenter l'intégration avec Flashbots
            logger.info("💡 Utilisation de Flashbots pour le frontrunning")
            # Pour l'instant, on utilise simplement un gas price élevé
        
        # Envoyer la transaction avec priorité élevée
        tx_hash = await self.blockchain.send_transaction(
            to=router_address,
            data=buy_tx["data"],
            value=buy_tx["value"],
            gas_price=frontrun_gas_price
        )
        
        if not tx_hash:
            logger.error(f"❌ Échec de l'envoi de la transaction d'achat pour {token_address}")
            return
        
        logger.success(f"✅ Transaction de snipe envoyée: {tx_hash}")
        
        # Obtenir le prix d'entrée
        entry_price = await self.price_feed.get_token_price(base_token, token_address, dex_name)
        
        # Créer un ID unique pour ce trade
        trade_id = f"{token_address}_{int(time.time())}"
        
        # Enregistrer le trade actif
        self.active_trades[trade_id] = {
            "token_address": token_address,
            "base_token": base_token,
            "dex_name": dex_name,
            "amount": initial_amount,
            "entry_price": entry_price,
            "entry_time": time.time(),
            "tx_hash": tx_hash,
            "status": "active",
            "remaining_percentage": 100,
            "reached_tiers": [],
            "current_stop_loss": self.config["stop_loss"]
        }
        
        # Enregistrer les détails de la transaction pour le suivi
        self._track_transaction(tx_hash, token_address, initial_amount, frontrun_gas_price)
    
    def _track_transaction(self, tx_hash: str, token_address: str, amount: float, gas_price: int):
        """
        Enregistre les détails d'une transaction pour le suivi
        
        Args:
            tx_hash: Hash de la transaction
            token_address: Adresse du token
            amount: Montant de la transaction
            gas_price: Prix du gas utilisé
        """
        # TODO: Implémenter le suivi des transactions
        logger.info(f"📊 Transaction {tx_hash} enregistrée pour le suivi")
        
        # Enregistrer dans une base de données ou un fichier
        transaction_details = {
            "tx_hash": tx_hash,
            "token_address": token_address,
            "amount": amount,
            "gas_price": gas_price,
            "timestamp": int(time.time())
        }
        
        # Pour l'instant, on affiche simplement les détails
        logger.debug(f"Transaction details: {transaction_details}")
    
    def _get_router_address(self, dex_name: str) -> str:
        """
        Retourne l'adresse du routeur pour un DEX donné
        
        Args:
            dex_name: Nom du DEX
            
        Returns:
            Adresse du routeur
        """
        if dex_name == "trader_joe":
            return "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"
        elif dex_name == "pangolin":
            return "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"
        else:
            raise ValueError(f"DEX inconnu: {dex_name}")
    
    async def _prepare_swap_transaction(self, token_in: str, token_out: str, amount_in: Optional[float], router_address: str) -> Optional[Dict]:
        """
        Prépare une transaction de swap
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            amount_in: Montant à échanger (None pour tout le solde)
            router_address: Adresse du routeur
            
        Returns:
            Dictionnaire avec les données de transaction
        """
        # TODO: Implémenter la préparation de transaction
        # Pour l'instant, retourner un mock pour le développement
        return {
            "data": b'0x',  # Données de transaction encodées
            "value": Web3.to_wei(amount_in, "ether") if amount_in else 0  # Valeur en wei à envoyer
        }
    
    async def _analyze_initial_transactions(self):
        """Analyse les transactions initiales pour détecter les patterns suspects"""
        logger.info("🔍 Analyse des transactions initiales pour détecter les patterns suspects")
        
        # TODO: Implémenter la logique d'analyse des transactions
        # Utiliser le modèle IsolationForest pour détecter les anomalies
        # Exemple de données de transaction (à remplacer par des données réelles)
        transaction_data = [
            [0.1, 0.2, 0.3],  # Exemple de vecteur de caractéristiques
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        
        # Détecter les anomalies
        anomalies = self.pattern_detector.fit_predict(transaction_data)
        
        for i, anomaly in enumerate(anomalies):
            if anomaly == -1:
                logger.warning(f"⚠️ Anomalie détectée dans la transaction {i}")
    
    async def _manage_active_trades(self):
        """Gère les trades actifs (stop-loss, take-profit, suivi des whales)"""
        logger.info("📊 Démarrage du gestionnaire de trades actifs")
        
        while True:
            try:
                # Parcourir tous les trades actifs
                trades_to_remove = []
                
                for trade_id, trade_info in self.active_trades.items():
                    # Vérifier si le trade est toujours actif
                    if trade_info["status"] != "active":
                        continue
                    
                    # Récupérer les informations du trade
                    token_address = trade_info["token_address"]
                    base_token = trade_info["base_token"]
                    dex_name = trade_info["dex_name"]
                    entry_price = trade_info["entry_price"]
                    remaining_percentage = trade_info["remaining_percentage"]
                    
                    # Obtenir le prix actuel
                    current_price = await self.price_feed.get_token_price(base_token, token_address, dex_name)
                    
                    if current_price <= 0:
                        logger.warning(f"⚠️ Impossible d'obtenir le prix actuel pour {token_address}")
                        continue
                    
                    # Calculer le pourcentage de profit/perte
                    profit_percentage = ((current_price / entry_price) - 1) * 100
                    
                    # Mettre à jour le prix le plus élevé atteint
                    if current_price > trade_info.get("highest_price", 0):
                        trade_info["highest_price"] = current_price
                    
                    # 1. Vérifier les paliers de prise de profit
                    await self._check_profit_tiers(trade_id, trade_info, current_price, profit_percentage)
                    
                    # 2. Vérifier le stop-loss (statique ou dynamique)
                    if await self._check_stop_loss(trade_id, trade_info, current_price, profit_percentage):
                        trades_to_remove.append(trade_id)
                        continue
                    
                    # 3. Surveiller les mouvements des whales
                    if await self._check_whale_movements(trade_id, trade_info, token_address):
                        trades_to_remove.append(trade_id)
                        continue
                    
                    # 4. Mettre à jour le stop-loss dynamique si activé
                    if self.config["dynamic_stop_loss"]["enabled"]:
                        self._update_dynamic_stop_loss(trade_info, profit_percentage)
                
                # Supprimer les trades terminés
                for trade_id in trades_to_remove:
                    del self.active_trades[trade_id]
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(10)  # Vérifier toutes les 10 secondes
                
            except Exception as e:
                logger.error(f"❌ Erreur dans la gestion des trades actifs: {str(e)}")
                await asyncio.sleep(10)  # Attendre avant de réessayer
    
    async def _check_profit_tiers(self, trade_id: str, trade_info: Dict, current_price: float, profit_percentage: float) -> bool:
        """
        Vérifie si un palier de prise de profit a été atteint
        
        Args:
            trade_id: ID du trade
            trade_info: Informations sur le trade
            current_price: Prix actuel du token
            profit_percentage: Pourcentage de profit/perte
            
        Returns:
            True si un palier a été atteint, False sinon
        """
        # Récupérer les paliers de prise de profit
        profit_tiers = self.config["profit_tiers"]
        
        # Vérifier si des paliers ont déjà été atteints
        reached_tiers = trade_info.get("reached_tiers", [])
        
        # Parcourir les paliers non atteints
        for tier_index, tier in enumerate(profit_tiers):
            # Ignorer les paliers déjà atteints
            if tier_index in reached_tiers:
                continue
            
            # Vérifier si le palier est atteint
            multiplier = tier["multiplier"]
            tier_price = trade_info["entry_price"] * multiplier
            
            if current_price >= tier_price:
                # Calculer le montant à vendre pour ce palier
                percentage_to_sell = tier["percentage"]
                total_amount = trade_info["amount"]
                amount_to_sell = (total_amount * percentage_to_sell) / 100
                
                # Exécuter la vente
                logger.info(f"🎯 Palier de profit atteint pour {trade_info['token_address']}: x{multiplier} ({profit_percentage:.2f}%)")
                await self._execute_sell(trade_info, amount_to_sell, current_price)
                
                # Mettre à jour les informations du trade
                trade_info["reached_tiers"] = reached_tiers + [tier_index]
                trade_info["remaining_percentage"] -= percentage_to_sell
                
                # Si tous les paliers sont atteints, marquer le trade comme terminé
                if len(trade_info["reached_tiers"]) == len(profit_tiers):
                    trade_info["status"] = "completed"
                    logger.success(f"✅ Tous les paliers de profit atteints pour {trade_info['token_address']}")
                    return True
                
                return True
        
        return False
    
    async def _check_stop_loss(self, trade_id: str, trade_info: Dict, current_price: float, profit_percentage: float) -> bool:
        """
        Vérifie si le stop-loss a été atteint
        
        Args:
            trade_id: ID du trade
            trade_info: Informations sur le trade
            current_price: Prix actuel du token
            profit_percentage: Pourcentage de profit/perte
            
        Returns:
            True si le stop-loss a été atteint, False sinon
        """
        # Récupérer le stop-loss (statique ou dynamique)
        stop_loss_percentage = trade_info.get("current_stop_loss", self.config["stop_loss"])
        
        # Vérifier si le stop-loss est atteint
        if profit_percentage <= stop_loss_percentage:
            # Calculer le montant restant à vendre
            remaining_percentage = trade_info.get("remaining_percentage", 100)
            total_amount = trade_info["amount"]
            amount_to_sell = (total_amount * remaining_percentage) / 100
            
            # Exécuter la vente
            logger.warning(f"⚠️ Stop-loss atteint pour {trade_info['token_address']}: {profit_percentage:.2f}%")
            await self._execute_sell(trade_info, amount_to_sell, current_price)
            
            # Marquer le trade comme terminé
            trade_info["status"] = "stopped"
            
            return True
        
        return False
    
    def _update_dynamic_stop_loss(self, trade_info: Dict, profit_percentage: float):
        """
        Met à jour le stop-loss dynamique en fonction du profit
        
        Args:
            trade_info: Informations sur le trade
            profit_percentage: Pourcentage de profit/perte
        """
        # Récupérer la configuration du stop-loss dynamique
        dynamic_config = self.config["dynamic_stop_loss"]
        initial_stop_loss = dynamic_config["initial"]
        trailing_percentage = dynamic_config["trailing"]
        profit_threshold = dynamic_config["profit_threshold"]
        adjusted_stop_loss = dynamic_config["adjusted_stop_loss"]
        
        # Calculer le nouveau stop-loss
        if profit_percentage >= profit_threshold:
            # Si le profit dépasse le seuil, utiliser le stop-loss ajusté
            new_stop_loss = adjusted_stop_loss
        else:
            # Sinon, utiliser le trailing stop
            highest_profit = ((trade_info.get("highest_price", 0) / trade_info["entry_price"]) - 1) * 100
            new_stop_loss = max(initial_stop_loss, highest_profit - trailing_percentage)
        
        # Mettre à jour le stop-loss si nécessaire
        current_stop_loss = trade_info.get("current_stop_loss", initial_stop_loss)
        if new_stop_loss > current_stop_loss:
            trade_info["current_stop_loss"] = new_stop_loss
            logger.info(f"📈 Stop-loss dynamique mis à jour pour {trade_info['token_address']}: {new_stop_loss:.2f}%")
    
    async def _check_whale_movements(self, trade_id: str, trade_info: Dict, token_address: str) -> bool:
        """
        Surveille les mouvements des whales pour détecter les ventes massives
        
        Args:
            trade_id: ID du trade
            trade_info: Informations sur le trade
            token_address: Adresse du token
            
        Returns:
            True si une vente massive a été détectée, False sinon
        """
        # Vérifier si le suivi des whales est activé
        if not self.config["whale_tracking"]["enabled"]:
            return False
        
        try:
            # Récupérer les dernières transactions du token
            recent_txs = await self._get_recent_token_transactions(token_address)
            
            # Filtrer les transactions de vente importantes
            whale_sells = []
            for tx in recent_txs:
                # Vérifier si c'est une vente
                if tx.get("is_sell", False):
                    # Vérifier si le montant est suffisant pour être considéré comme whale
                    amount = tx.get("amount", 0)
                    if amount >= self.config["whale_tracking"]["min_whale_amount"]:
                        whale_sells.append(tx)
            
            # Vérifier s'il y a des ventes massives
            if whale_sells:
                # Calculer le pourcentage total vendu par les whales
                total_whale_sell_percentage = sum(tx.get("percentage_of_holdings", 0) for tx in whale_sells)
                
                # Si le pourcentage dépasse le seuil, exécuter une sortie d'urgence
                if total_whale_sell_percentage >= self.config["whale_tracking"]["emergency_exit_threshold"]:
                    logger.warning(f"🐋 Détection de vente massive par des whales pour {token_address}: {total_whale_sell_percentage:.2f}%")
                    
                    # Calculer le montant restant à vendre
                    remaining_percentage = trade_info.get("remaining_percentage", 100)
                    total_amount = trade_info["amount"]
                    amount_to_sell = (total_amount * remaining_percentage) / 100
                    
                    # Exécuter la vente d'urgence
                    current_price = await self.price_feed.get_token_price(
                        trade_info["base_token"], token_address, trade_info["dex_name"]
                    )
                    
                    await self._execute_sell(trade_info, amount_to_sell, current_price)
                    
                    # Marquer le trade comme terminé
                    trade_info["status"] = "emergency_exit"
                    
                    return True
        
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification des mouvements de whales: {str(e)}")
        
        return False
    
    async def _get_recent_token_transactions(self, token_address: str) -> List[Dict]:
        """
        Récupère les transactions récentes d'un token
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Liste des transactions récentes
        """
        # TODO: Implémenter la récupération des transactions récentes
        # Pour l'instant, retourner une liste vide
        return []
    
    async def _execute_sell(self, trade_info: Dict, amount_to_sell: float, current_price: float):
        """
        Exécute une vente
        
        Args:
            trade_info: Informations sur le trade
            amount_to_sell: Montant à vendre
            current_price: Prix actuel du token
        """
        try:
            token_address = trade_info["token_address"]
            base_token = trade_info["base_token"]
            dex_name = trade_info["dex_name"]
            
            logger.info(f"💰 Exécution d'une vente de {amount_to_sell} tokens {token_address}")
            
            # Préparer la transaction de vente
            router_address = self._get_router_address(dex_name)
            sell_tx = await self._prepare_swap_transaction(token_address, base_token, amount_to_sell, router_address)
            
            if not sell_tx:
                logger.error(f"❌ Impossible de préparer la transaction de vente pour {token_address}")
                return
            
            # Optimiser les frais de gas pour la vente
            current_gas_price = self.web3.eth.gas_price
            sell_gas_price = int(current_gas_price * 1.2)  # Augmenter de 20% pour priorité
            
            # Envoyer la transaction
            tx_hash = await self.blockchain.send_transaction(
                to=router_address,
                data=sell_tx["data"],
                value=sell_tx["value"],
                gas_price=sell_gas_price
            )
            
            if not tx_hash:
                logger.error(f"❌ Échec de l'envoi de la transaction de vente pour {token_address}")
                return
            
            logger.success(f"✅ Transaction de vente envoyée: {tx_hash}")
            
            # Calculer le profit réalisé
            entry_price = trade_info["entry_price"]
            profit_percentage = ((current_price / entry_price) - 1) * 100
            
            # Enregistrer les détails de la vente
            sell_details = {
                "tx_hash": tx_hash,
                "token_address": token_address,
                "amount": amount_to_sell,
                "price": current_price,
                "profit_percentage": profit_percentage,
                "timestamp": int(time.time())
            }
            
            logger.info(f"📊 Vente enregistrée: {profit_percentage:.2f}% de profit")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'exécution de la vente: {str(e)}") 