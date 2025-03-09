#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module Anti-Détection pour GBPBot
=================================

Ce module fournit des mécanismes avancés pour éviter la détection du bot
par les DEX et autres services. Il implémente:
- Rotation automatique des adresses IP via proxies
- Rotation des wallets pour distribuer les transactions
- Randomisation des délais et montants de transactions
- Simulation de comportement humain
"""

import os
import json
import time
import random
import logging
import asyncio
import requests
from typing import Dict, List, Any, Optional, Tuple, Set, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("anti_detection")

@dataclass
class ProxyConfig:
    """Configuration pour les proxies."""
    enabled: bool = True
    proxy_list_path: Optional[str] = None
    proxy_api_url: Optional[str] = None
    proxy_api_key: Optional[str] = None
    rotation_interval_minutes: int = 30
    max_consecutive_failures: int = 3
    test_url: str = "https://api.solscan.io/v1/health"
    timeout_seconds: int = 10
    proxy_type: str = "http"  # http, socks4, socks5

@dataclass
class WalletRotationConfig:
    """Configuration pour la rotation des wallets."""
    enabled: bool = True
    wallets_directory: str = "wallets"
    max_transactions_per_wallet: int = 10
    min_balance_sol: float = 0.05
    max_balance_sol: float = 2.0
    max_consecutive_failures: int = 3
    randomize_selection: bool = True
    distribute_by_volume: bool = True

@dataclass
class HumanizationConfig:
    """Configuration pour la simulation de comportement humain."""
    enabled: bool = True
    random_delay_range_ms: Tuple[int, int] = (100, 2000)
    transaction_amount_variation_percent: float = 5.0
    random_gas_variation_percent: float = 3.0
    session_length_minutes: Tuple[int, int] = (30, 120)
    break_between_sessions_minutes: Tuple[int, int] = (5, 20)
    max_transactions_per_minute: int = 5
    natural_typing_simulation: bool = True
    realistic_browsing_patterns: bool = True

class AntiDetectionSystem:
    """
    Système anti-détection pour GBPBot.
    
    Ce système implémente plusieurs mécanismes pour éviter la détection:
    - Rotation des adresses IP via proxies
    - Rotation des wallets pour distribuer les transactions
    - Randomisation des délais et montants
    - Simulation de comportement humain
    """
    
    def __init__(
        self,
        proxy_config: Optional[ProxyConfig] = None,
        wallet_rotation_config: Optional[WalletRotationConfig] = None,
        humanization_config: Optional[HumanizationConfig] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialise le système anti-détection.
        
        Args:
            proxy_config: Configuration pour les proxies
            wallet_rotation_config: Configuration pour la rotation des wallets
            humanization_config: Configuration pour la simulation de comportement humain
            config_path: Chemin vers un fichier de configuration JSON
        """
        # Charger la configuration depuis un fichier si spécifié
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
                if proxy_config is None and "proxy" in config_data:
                    proxy_config = ProxyConfig(**config_data["proxy"])
                
                if wallet_rotation_config is None and "wallet_rotation" in config_data:
                    wallet_rotation_config = WalletRotationConfig(**config_data["wallet_rotation"])
                
                if humanization_config is None and "humanization" in config_data:
                    humanization_config = HumanizationConfig(**config_data["humanization"])
        
        # Utiliser les configurations par défaut si non spécifiées
        self.proxy_config = proxy_config or ProxyConfig()
        self.wallet_rotation_config = wallet_rotation_config or WalletRotationConfig()
        self.humanization_config = humanization_config or HumanizationConfig()
        
        # État interne
        self.current_proxy = None
        self.proxy_list = []
        self.proxy_last_rotation = time.time()
        self.proxy_failures = 0
        
        self.wallets = []
        self.current_wallet_index = 0
        self.wallet_transaction_counts = {}
        self.wallet_failures = {}
        
        self.session_start_time = time.time()
        self.transaction_times = []
        self.is_in_break = False
        
        # Statistiques
        self.stats = {
            "proxy_rotations": 0,
            "wallet_rotations": 0,
            "delays_applied": 0,
            "amount_variations_applied": 0,
            "gas_variations_applied": 0,
            "sessions_started": 1,
            "breaks_taken": 0,
            "detection_attempts_blocked": 0
        }
        
        # Initialisation
        self._load_proxies()
        self._load_wallets()
        logger.info("Système anti-détection initialisé")
    
    def _load_proxies(self) -> None:
        """Charge la liste des proxies depuis un fichier ou une API."""
        if not self.proxy_config.enabled:
            logger.info("Rotation de proxies désactivée")
            return
        
        try:
            # Charger depuis un fichier
            if self.proxy_config.proxy_list_path and os.path.exists(self.proxy_config.proxy_list_path):
                with open(self.proxy_config.proxy_list_path, 'r') as f:
                    self.proxy_list = [line.strip() for line in f if line.strip()]
                logger.info(f"Chargé {len(self.proxy_list)} proxies depuis {self.proxy_config.proxy_list_path}")
            
            # Charger depuis une API
            elif self.proxy_config.proxy_api_url and self.proxy_config.proxy_api_key:
                response = requests.get(
                    self.proxy_config.proxy_api_url,
                    headers={"Authorization": f"Bearer {self.proxy_config.proxy_api_key}"},
                    timeout=self.proxy_config.timeout_seconds
                )
                if response.status_code == 200:
                    data = response.json()
                    # Format dépend de l'API spécifique
                    if "proxies" in data and isinstance(data["proxies"], list):
                        self.proxy_list = data["proxies"]
                    elif isinstance(data, list):
                        self.proxy_list = data
                    logger.info(f"Chargé {len(self.proxy_list)} proxies depuis l'API")
                else:
                    logger.error(f"Échec du chargement des proxies depuis l'API: {response.status_code}")
            
            # Sélectionner un proxy initial
            if self.proxy_list:
                self.current_proxy = random.choice(self.proxy_list)
                logger.info(f"Proxy initial sélectionné: {self._mask_proxy(self.current_proxy)}")
            else:
                logger.warning("Aucun proxy disponible")
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement des proxies: {str(e)}")
    
    def _mask_proxy(self, proxy: str) -> str:
        """Masque une partie de l'adresse proxy pour les logs."""
        if not proxy:
            return "None"
        
        # Format typique: http://user:pass@host:port
        parts = proxy.split('@')
        if len(parts) > 1:
            auth, server = parts
            auth_parts = auth.split(':')
            if len(auth_parts) > 1:
                user, password = auth_parts
                masked_password = password[:2] + '*' * (len(password) - 4) + password[-2:] if len(password) > 4 else '****'
                return f"{auth_parts[0]}:{masked_password}@{server}"
        
        # Format simple: host:port
        parts = proxy.split(':')
        if len(parts) >= 2:
            host = parts[0]
            port = parts[1]
            masked_host = host.split('.')
            if len(masked_host) == 4:  # IPv4
                return f"{masked_host[0]}.{masked_host[1]}.***.***:{port}"
            return f"{host[:3]}***:{port}"
        
        return proxy
    
    def _load_wallets(self) -> None:
        """Charge les wallets disponibles."""
        if not self.wallet_rotation_config.enabled:
            logger.info("Rotation de wallets désactivée")
            return
        
        try:
            wallets_dir = self.wallet_rotation_config.wallets_directory
            if not os.path.exists(wallets_dir):
                os.makedirs(wallets_dir, exist_ok=True)
                logger.info(f"Répertoire de wallets créé: {wallets_dir}")
                return
            
            # Charger tous les fichiers de wallet (format .json)
            wallet_files = [f for f in os.listdir(wallets_dir) if f.endswith('.json')]
            
            for wallet_file in wallet_files:
                wallet_path = os.path.join(wallets_dir, wallet_file)
                try:
                    with open(wallet_path, 'r') as f:
                        wallet_data = json.load(f)
                        # Vérifier que le wallet a les champs requis
                        if "public_key" in wallet_data and "private_key" in wallet_data:
                            self.wallets.append(wallet_data)
                            self.wallet_transaction_counts[wallet_data["public_key"]] = 0
                            self.wallet_failures[wallet_data["public_key"]] = 0
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du wallet {wallet_file}: {str(e)}")
            
            logger.info(f"Chargé {len(self.wallets)} wallets depuis {wallets_dir}")
            
            # Mélanger les wallets pour une sélection aléatoire initiale
            if self.wallet_rotation_config.randomize_selection:
                random.shuffle(self.wallets)
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement des wallets: {str(e)}")
    
    async def rotate_proxy(self, force: bool = False) -> bool:
        """
        Effectue une rotation de proxy.
        
        Args:
            force: Forcer la rotation même si l'intervalle n'est pas atteint
            
        Returns:
            bool: True si la rotation a réussi, False sinon
        """
        if not self.proxy_config.enabled or not self.proxy_list:
            return False
        
        current_time = time.time()
        time_since_last_rotation = current_time - self.proxy_last_rotation
        
        # Vérifier si nous devons effectuer une rotation
        if not force and time_since_last_rotation < self.proxy_config.rotation_interval_minutes * 60:
            return True  # Pas besoin de rotation
        
        try:
            # Sélectionner un nouveau proxy différent de l'actuel
            available_proxies = [p for p in self.proxy_list if p != self.current_proxy]
            if not available_proxies:
                logger.warning("Pas d'autres proxies disponibles pour la rotation")
                return False
            
            new_proxy = random.choice(available_proxies)
            
            # Tester le nouveau proxy
            proxy_dict = self._proxy_to_dict(new_proxy)
            test_success = await self._test_proxy(proxy_dict)
            
            if test_success:
                old_proxy = self.current_proxy
                self.current_proxy = new_proxy
                self.proxy_last_rotation = current_time
                self.proxy_failures = 0
                self.stats["proxy_rotations"] += 1
                
                logger.info(f"Rotation de proxy: {self._mask_proxy(old_proxy)} -> {self._mask_proxy(new_proxy)}")
                return True
            else:
                logger.warning(f"Le proxy {self._mask_proxy(new_proxy)} a échoué au test, essai d'un autre")
                # Retirer ce proxy de la liste
                self.proxy_list.remove(new_proxy)
                return await self.rotate_proxy(force=True)
        
        except Exception as e:
            logger.error(f"Erreur lors de la rotation de proxy: {str(e)}")
            return False
    
    def _proxy_to_dict(self, proxy_str: str) -> Dict[str, str]:
        """Convertit une chaîne de proxy en dictionnaire pour requests."""
        proxy_type = self.proxy_config.proxy_type
        return {proxy_type: proxy_str}
    
    async def _test_proxy(self, proxy_dict: Dict[str, str]) -> bool:
        """Teste si un proxy fonctionne."""
        try:
            # Utiliser aiohttp pour un test asynchrone
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.proxy_config.test_url,
                    proxy=list(proxy_dict.values())[0],
                    timeout=aiohttp.ClientTimeout(total=self.proxy_config.timeout_seconds)
                ) as response:
                    return response.status == 200
        
        except ImportError:
            # Fallback à requests si aiohttp n'est pas disponible
            try:
                response = requests.get(
                    self.proxy_config.test_url,
                    proxies=proxy_dict,
                    timeout=self.proxy_config.timeout_seconds
                )
                return response.status_code == 200
            except:
                return False
        
        except Exception:
            return False
    
    def get_current_proxy(self) -> Optional[Dict[str, str]]:
        """
        Retourne le proxy actuel sous forme de dictionnaire.
        
        Returns:
            Dict[str, str]: Proxy au format attendu par requests/aiohttp
        """
        if not self.proxy_config.enabled or not self.current_proxy:
            return None
        
        return self._proxy_to_dict(self.current_proxy)
    
    async def get_next_wallet(self) -> Optional[Dict[str, Any]]:
        """
        Sélectionne le prochain wallet à utiliser selon la stratégie de rotation.
        
        Returns:
            Dict: Données du wallet sélectionné
        """
        if not self.wallet_rotation_config.enabled or not self.wallets:
            return None
        
        # Vérifier si nous devons effectuer une rotation basée sur le nombre de transactions
        current_wallet = self.wallets[self.current_wallet_index]
        current_pk = current_wallet["public_key"]
        
        if (self.wallet_transaction_counts[current_pk] >= self.wallet_rotation_config.max_transactions_per_wallet or
            self.wallet_failures[current_pk] >= self.wallet_rotation_config.max_consecutive_failures):
            # Rotation nécessaire
            return await self._rotate_wallet()
        
        return current_wallet
    
    async def _rotate_wallet(self) -> Optional[Dict[str, Any]]:
        """
        Effectue une rotation de wallet.
        
        Returns:
            Dict: Données du nouveau wallet
        """
        if not self.wallets:
            logger.warning("Pas de wallets disponibles pour la rotation")
            return None
        
        # Stratégie de sélection
        if self.wallet_rotation_config.randomize_selection:
            # Sélection aléatoire (éviter le wallet actuel)
            available_indices = [i for i in range(len(self.wallets)) if i != self.current_wallet_index]
            if not available_indices:
                logger.warning("Pas d'autres wallets disponibles pour la rotation")
                return self.wallets[self.current_wallet_index]
            
            self.current_wallet_index = random.choice(available_indices)
        else:
            # Sélection séquentielle
            self.current_wallet_index = (self.current_wallet_index + 1) % len(self.wallets)
        
        new_wallet = self.wallets[self.current_wallet_index]
        self.stats["wallet_rotations"] += 1
        
        logger.info(f"Rotation de wallet: {new_wallet['public_key'][:6]}...{new_wallet['public_key'][-4:]}")
        return new_wallet
    
    async def record_transaction(self, wallet_public_key: str, success: bool) -> None:
        """
        Enregistre une transaction pour un wallet.
        
        Args:
            wallet_public_key: Clé publique du wallet
            success: Si la transaction a réussi
        """
        if wallet_public_key in self.wallet_transaction_counts:
            self.wallet_transaction_counts[wallet_public_key] += 1
            
            if not success:
                self.wallet_failures[wallet_public_key] += 1
            else:
                self.wallet_failures[wallet_public_key] = 0  # Réinitialiser les échecs consécutifs
        
        # Enregistrer le temps de la transaction pour la limitation de débit
        self.transaction_times.append(time.time())
        
        # Nettoyer les anciennes transactions (plus de 1 minute)
        current_time = time.time()
        self.transaction_times = [t for t in self.transaction_times if current_time - t <= 60]
    
    async def apply_humanization(self, transaction_type: str) -> Tuple[int, float, float]:
        """
        Applique des techniques de simulation de comportement humain.
        
        Args:
            transaction_type: Type de transaction (snipe, sell, etc.)
            
        Returns:
            Tuple[int, float, float]: (Délai en ms, Variation de montant en %, Variation de gas en %)
        """
        if not self.humanization_config.enabled:
            return 0, 0.0, 0.0
        
        # Vérifier si nous sommes en pause entre sessions
        if self.is_in_break:
            current_time = time.time()
            if current_time - self.session_start_time < self.humanization_config.break_between_sessions_minutes[0] * 60:
                # Encore en pause
                logger.info(f"En pause entre sessions ({int((current_time - self.session_start_time) / 60)} minutes écoulées)")
                return 0, 0.0, 0.0
            else:
                # Fin de la pause
                self.is_in_break = False
                self.session_start_time = current_time
                self.stats["sessions_started"] += 1
                logger.info("Nouvelle session démarrée après une pause")
        
        # Vérifier si nous devons prendre une pause (fin de session)
        session_duration = time.time() - self.session_start_time
        max_session_length = self.humanization_config.session_length_minutes[1] * 60
        
        if session_duration > max_session_length:
            # Prendre une pause
            self.is_in_break = True
            self.session_start_time = time.time()
            self.stats["breaks_taken"] += 1
            
            min_break, max_break = self.humanization_config.break_between_sessions_minutes
            break_duration = random.randint(min_break, max_break)
            logger.info(f"Début d'une pause de {break_duration} minutes entre sessions")
            
            return 0, 0.0, 0.0
        
        # Vérifier la limitation de débit (transactions par minute)
        if len(self.transaction_times) >= self.humanization_config.max_transactions_per_minute:
            # Trop de transactions récentes, ajouter un délai plus important
            delay_ms = random.randint(5000, 15000)  # 5-15 secondes
            logger.info(f"Limitation de débit atteinte, ajout d'un délai de {delay_ms}ms")
            self.stats["delays_applied"] += 1
            return delay_ms, 0.0, 0.0
        
        # Délai aléatoire normal
        delay_ms = random.randint(
            self.humanization_config.random_delay_range_ms[0],
            self.humanization_config.random_delay_range_ms[1]
        )
        
        # Variation de montant
        amount_variation = random.uniform(
            -self.humanization_config.transaction_amount_variation_percent,
            self.humanization_config.transaction_amount_variation_percent
        )
        
        # Variation de gas
        gas_variation = random.uniform(
            -self.humanization_config.random_gas_variation_percent,
            self.humanization_config.random_gas_variation_percent
        )
        
        # Mettre à jour les statistiques
        self.stats["delays_applied"] += 1
        self.stats["amount_variations_applied"] += 1
        self.stats["gas_variations_applied"] += 1
        
        return delay_ms, amount_variation, gas_variation
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du système anti-détection.
        
        Returns:
            Dict[str, Any]: Statistiques
        """
        stats = self.stats.copy()
        
        # Ajouter des informations sur l'état actuel
        stats["current_proxy"] = self._mask_proxy(self.current_proxy) if self.current_proxy else None
        stats["proxy_count"] = len(self.proxy_list)
        stats["wallet_count"] = len(self.wallets)
        stats["current_wallet_index"] = self.current_wallet_index
        
        if self.wallets and self.current_wallet_index < len(self.wallets):
            current_wallet = self.wallets[self.current_wallet_index]
            stats["current_wallet"] = f"{current_wallet['public_key'][:6]}...{current_wallet['public_key'][-4:]}"
            stats["current_wallet_transactions"] = self.wallet_transaction_counts.get(current_wallet['public_key'], 0)
        
        # Informations sur la session
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        stats["current_session_duration_minutes"] = session_duration / 60
        stats["is_in_break"] = self.is_in_break
        stats["transactions_last_minute"] = len(self.transaction_times)
        
        return stats

def create_anti_detection_system(
    config_path: Optional[str] = None,
    proxy_config: Optional[ProxyConfig] = None,
    wallet_rotation_config: Optional[WalletRotationConfig] = None,
    humanization_config: Optional[HumanizationConfig] = None
) -> AntiDetectionSystem:
    """
    Crée et configure un système anti-détection.
    
    Args:
        config_path: Chemin vers un fichier de configuration JSON
        proxy_config: Configuration pour les proxies
        wallet_rotation_config: Configuration pour la rotation des wallets
        humanization_config: Configuration pour la simulation de comportement humain
        
    Returns:
        AntiDetectionSystem: Système anti-détection configuré
    """
    return AntiDetectionSystem(
        config_path=config_path,
        proxy_config=proxy_config,
        wallet_rotation_config=wallet_rotation_config,
        humanization_config=humanization_config
    ) 