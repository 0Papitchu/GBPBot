#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module Stealth Manager pour GBPBot
==================================

Ce module étend les capacités anti-détection avec des fonctionnalités avancées:
- Simulation comportementale multi-niveau (débutant, intermédiaire, expert)
- Randomisation intelligente basée sur patterns humains réels
- Dissimulation des signatures de transactions (obfuscation)
- Rotation intelligente de wallets avec gestion de réputation
- Anti-pattern pour éviter les séquences récurrentes détectables
- Mécanismes anti-corrélation pour éviter les détections statistiques
"""

import os
import json
import time
import random
import logging
import asyncio
import hashlib
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union, Callable, TypedDict
from dataclasses import dataclass, field

# Importations internes
from gbpbot.security.anti_detection import AntiDetectionSystem, create_anti_detection_system
from gbpbot.utils.logger import setup_logger
from gbpbot.ai.profile_intelligence import ProfileIntelligence, create_profile_intelligence

# Configuration du logger
logger = setup_logger("stealth_manager", logging.INFO)

class TradingPattern(TypedDict, total=False):
    """Type pour définir des patterns de trading humains."""
    entry_split: List[float]  # Division des montants d'entrée (ex: [0.3, 0.7])
    exit_split: List[float]   # Division des montants de sortie (ex: [0.2, 0.3, 0.5])
    time_window: Tuple[int, int]  # Fenêtre temporelle en minutes entre transactions
    gas_behavior: str  # "economic", "normal", "aggressive"
    slippage_tolerance: float  # Tolérance au slippage (%)
    typical_delays: List[int]  # Délais typiques entre actions (ms)
    tx_frequency: float  # Fréquence de transactions par heure

@dataclass
class TraderProfile:
    """Profil de trader pour la simulation comportementale."""
    name: str
    risk_profile: str  # "conservative", "moderate", "aggressive"
    experience_level: str  # "beginner", "intermediate", "expert"
    trading_patterns: List[TradingPattern]
    session_habits: Dict[str, Any]  # Habitudes de session (durée, pauses, etc.)
    
    # Caractéristiques de comportement
    buys_during_pumps: bool = True  # Tendance à acheter pendant les pumps
    sells_during_dumps: bool = False  # Tendance à vendre pendant les dumps
    uses_limit_orders: bool = False  # Utilisation d'ordres limites vs market
    splits_large_orders: bool = True  # Division des gros ordres
    
    # Paramètres d'aléatorisation
    randomization_factors: Dict[str, float] = field(default_factory=dict)

@dataclass
class StealthConfig:
    """Configuration du système de discrétion."""
    enabled: bool = True
    
    # Configuration des profils
    active_profile: str = "intermediate_trader"
    rotation_enabled: bool = True
    profile_rotation_interval_hours: Tuple[int, int] = (4, 12)
    
    # Anti-pattern
    max_consecutive_similar_txs: int = 3
    pattern_variation_threshold: float = 0.15
    
    # Obfuscation des transactions
    tx_obfuscation_enabled: bool = True
    amount_variation_range: Tuple[float, float] = (0.01, 0.05)  # 1-5% de variation
    dust_transaction_probability: float = 0.1  # 10% de chance de transactions "poussière"
    
    # Paramètres temporels
    time_randomization_strength: float = 0.65  # Force de randomisation des délais
    variance_increase_after_hours: int = 3  # Augmenter la variance après X heures
    
    # Contre-mesures avancées
    anti_correlation_measures: bool = True
    wallet_reputation_tracking: bool = True
    behavior_adaptive_learning: bool = True
    
    # Gestion IA des profils
    ai_profile_management: bool = True
    performance_priority: float = 0.7  # 0.0-1.0 (0 = discrétion max, 1 = performance max)

class StealthManager:
    """
    Gestionnaire de furtivité avancé pour rendre le GBPBot indétectable.
    S'intègre avec l'AntiDetectionSystem existant pour fournir des couches
    supplémentaires de protection.
    """
    
    def __init__(
        self,
        config: Optional[StealthConfig] = None,
        anti_detection_system: Optional[AntiDetectionSystem] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialise le StealthManager avec la configuration spécifiée.
        
        Args:
            config: Configuration du système de discrétion
            anti_detection_system: Instance existante de AntiDetectionSystem
            config_path: Chemin vers le fichier de configuration
        """
        self.config = config or StealthConfig()
        self.anti_detection_system = anti_detection_system
        
        # Charger la configuration si un chemin est spécifié
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        
        # Initialiser l'AntiDetectionSystem si non fourni
        if not self.anti_detection_system:
            self.anti_detection_system = create_anti_detection_system()
        
        # Initialiser le système d'intelligence de profil
        profile_config = {
            "enable_ai_profile_management": self.config.ai_profile_management,
            "performance_priority": self.config.performance_priority,
            "default_profile": self.config.active_profile
        }
        self.profile_intelligence = create_profile_intelligence(config=profile_config)
        
        # Charger les profils de trading
        self.profiles = self._load_trader_profiles()
        
        # Sélectionner le profil actif
        self.active_profile = self.profiles.get(
            self.config.active_profile, 
            self._create_default_profile()
        )
        
        # État interne
        self.last_profile_rotation = datetime.now()
        self.transaction_history = []
        self.current_session_start = datetime.now()
        self.wallet_reputation_scores = {}
        self.pattern_detection_state = {}
        
        # Statistiques
        self.total_obfuscated_txs = 0
        self.total_dust_txs = 0
        self.total_profile_rotations = 0
        
        logger.info(f"StealthManager initialisé avec profil: {self.active_profile.name}")
    
    def _load_config(self, config_path: str) -> None:
        """Charge la configuration depuis un fichier JSON."""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Mettre à jour la configuration
            for key, value in config_data.get('stealth_config', {}).items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    
            logger.info(f"Configuration chargée depuis {config_path}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
    
    def _load_trader_profiles(self) -> Dict[str, TraderProfile]:
        """Charge ou crée les profils de trading disponibles."""
        # Emplacement des profils prédéfinis
        profiles_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "trader_profiles.json"
        )
        
        profiles = {}
        
        # Essayer de charger les profils existants
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, 'r') as f:
                    profiles_data = json.load(f)
                
                for profile_id, profile_data in profiles_data.items():
                    profiles[profile_id] = TraderProfile(
                        name=profile_data.get('name', profile_id),
                        risk_profile=profile_data.get('risk_profile', 'moderate'),
                        experience_level=profile_data.get('experience_level', 'intermediate'),
                        trading_patterns=profile_data.get('trading_patterns', []),
                        session_habits=profile_data.get('session_habits', {}),
                        buys_during_pumps=profile_data.get('buys_during_pumps', True),
                        sells_during_dumps=profile_data.get('sells_during_dumps', False),
                        uses_limit_orders=profile_data.get('uses_limit_orders', False),
                        splits_large_orders=profile_data.get('splits_large_orders', True),
                        randomization_factors=profile_data.get('randomization_factors', {})
                    )
                
                logger.info(f"Chargé {len(profiles)} profils de trader")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des profils: {str(e)}")
        
        # Assurer des profils par défaut si aucun n'a été chargé
        if not profiles:
            logger.info("Création des profils de trader par défaut")
            profiles = self._create_default_profiles()
        
        return profiles
    
    def _create_default_profiles(self) -> Dict[str, TraderProfile]:
        """Crée un ensemble de profils de trader par défaut."""
        return {
            "beginner_trader": TraderProfile(
                name="Trader Débutant",
                risk_profile="conservative",
                experience_level="beginner",
                trading_patterns=[
                    {
                        "entry_split": [1.0],  # Entre d'un coup
                        "exit_split": [0.5, 0.5],  # Sort en deux fois
                        "time_window": (1, 30),  # 1-30 minutes entre transactions
                        "gas_behavior": "normal",
                        "slippage_tolerance": 2.0,  # 2% slippage accepté
                        "typical_delays": [5000, 10000, 15000],  # Délais en ms
                        "tx_frequency": 2.0  # 2 transactions par heure
                    }
                ],
                session_habits={
                    "session_length_minutes": (20, 60),
                    "sessions_per_day": (1, 3),
                    "preferred_hours": [9, 10, 11, 12, 13, 19, 20, 21]
                },
                buys_during_pumps=True,
                sells_during_dumps=True,
                uses_limit_orders=False,
                splits_large_orders=False,
                randomization_factors={
                    "amount": 0.05,  # 5% de variation
                    "timing": 0.2,   # 20% de variation temporelle
                    "gas": 0.1       # 10% de variation gas
                }
            ),
            "intermediate_trader": TraderProfile(
                name="Trader Intermédiaire",
                risk_profile="moderate",
                experience_level="intermediate",
                trading_patterns=[
                    {
                        "entry_split": [0.4, 0.6],  # Entre en deux fois
                        "exit_split": [0.3, 0.4, 0.3],  # Sort en trois fois
                        "time_window": (5, 45),  # 5-45 minutes entre transactions
                        "gas_behavior": "economic",
                        "slippage_tolerance": 1.0,  # 1% slippage accepté
                        "typical_delays": [2000, 5000, 8000],  # Délais en ms
                        "tx_frequency": 5.0  # 5 transactions par heure
                    }
                ],
                session_habits={
                    "session_length_minutes": (45, 120),
                    "sessions_per_day": (2, 5),
                    "preferred_hours": [8, 9, 10, 11, 12, 13, 14, 19, 20, 21, 22]
                },
                buys_during_pumps=False,
                sells_during_dumps=False,
                uses_limit_orders=True,
                splits_large_orders=True,
                randomization_factors={
                    "amount": 0.03,  # 3% de variation
                    "timing": 0.15,  # 15% de variation temporelle
                    "gas": 0.08      # 8% de variation gas
                }
            ),
            "expert_trader": TraderProfile(
                name="Trader Expert",
                risk_profile="aggressive",
                experience_level="expert",
                trading_patterns=[
                    {
                        "entry_split": [0.2, 0.3, 0.5],  # Entre en trois fois
                        "exit_split": [0.15, 0.25, 0.35, 0.25],  # Sort en quatre fois
                        "time_window": (2, 60),  # 2-60 minutes entre transactions
                        "gas_behavior": "aggressive",
                        "slippage_tolerance": 0.5,  # 0.5% slippage accepté
                        "typical_delays": [1000, 3000, 5000],  # Délais en ms
                        "tx_frequency": 8.0  # 8 transactions par heure
                    }
                ],
                session_habits={
                    "session_length_minutes": (60, 240),
                    "sessions_per_day": (3, 8),
                    "preferred_hours": list(range(24))  # Toutes les heures
                },
                buys_during_pumps=False,
                sells_during_dumps=False,
                uses_limit_orders=True,
                splits_large_orders=True,
                randomization_factors={
                    "amount": 0.02,  # 2% de variation
                    "timing": 0.1,   # 10% de variation temporelle
                    "gas": 0.05      # 5% de variation gas
                }
            )
        }
    
    def _create_default_profile(self) -> TraderProfile:
        """Crée un profil de trader par défaut."""
        return self._create_default_profiles()["intermediate_trader"]
    
    async def maybe_rotate_profile(self) -> None:
        """
        Effectue une rotation de profil si nécessaire, basée sur
        l'intervalle configuré et l'aléatorisation.
        """
        # Cette méthode est maintenant une façade pour le système d'intelligence IA
        # La logique est déportée vers le système ProfileIntelligence
        if not self.config.rotation_enabled and not self.config.ai_profile_management:
            return

        # Rotation non-IA simplifiée si la gestion IA est désactivée
        if not self.config.ai_profile_management:
            now = datetime.now()
            hours_since_last_rotation = (now - self.last_profile_rotation).total_seconds() / 3600
            
            min_interval, max_interval = self.config.profile_rotation_interval_hours
            should_rotate = hours_since_last_rotation >= random.uniform(min_interval, max_interval)
            
            if should_rotate:
                # Sélectionner un nouveau profil différent de l'actuel
                available_profiles = [p for p_id, p in self.profiles.items() 
                                    if p.name != self.active_profile.name]
                
                if available_profiles:
                    self.active_profile = random.choice(available_profiles)
                    self.last_profile_rotation = now
                    self.total_profile_rotations += 1
                    
                    logger.info(f"Rotation de profil aléatoire effectuée: {self.active_profile.name}")
    
    async def get_transaction_parameters(
        self, 
        tx_type: str, 
        base_amount: float,
        token_symbol: str,
        is_entry: bool = True
    ) -> Dict[str, Any]:
        """
        Obtient des paramètres de transaction optimisés pour l'anti-détection.
        
        Args:
            tx_type: Type d'opération ("swap", "transfer", "approval", etc.)
            base_amount: Montant de base de la transaction
            token_symbol: Symbole du token concerné
            is_entry: True pour une entrée en position, False pour une sortie
            
        Returns:
            Dictionnaire de paramètres optimisés pour l'anti-détection
        """
        # Détecter la blockchain et le type d'opération à partir du tx_type
        # Format attendu: "blockchain:operation" (ex: "solana:swap")
        blockchain = "solana"  # Blockchain par défaut
        operation_type = "standard"  # Type d'opération par défaut
        
        if ":" in tx_type:
            parts = tx_type.split(":")
            if len(parts) == 2:
                blockchain, operation = parts
                
                # Mapper les opérations aux types d'opérations standards
                if operation in ["snipe", "buy_new_token"]:
                    operation_type = "sniping"
                elif operation in ["arb", "arbitrage", "flash_arb"]:
                    operation_type = "arbitrage"
                else:
                    operation_type = "standard"
        
        # Utiliser le système d'intelligence de profil pour déterminer le meilleur profil
        if self.config.ai_profile_management:
            try:
                profile_name = await self.profile_intelligence.select_optimal_profile(
                    blockchain=blockchain,
                    operation_type=operation_type,
                    token_symbol=token_symbol
                )
                
                # Mettre à jour le profil actif si différent
                if profile_name != self.active_profile.name and profile_name in self.profiles:
                    self.active_profile = self.profiles[profile_name]
                    self.last_profile_rotation = datetime.now()
                    self.total_profile_rotations += 1
                    logger.info(f"Profil optimisé par l'IA: {profile_name} pour {operation_type} sur {blockchain}")
            except Exception as e:
                logger.warning(f"Erreur lors de la sélection du profil par l'IA: {str(e)}")
                # Fallback sur la rotation manuelle
                await self.maybe_rotate_profile()
        else:
            # Rotation du profil classique si la gestion IA est désactivée
            await self.maybe_rotate_profile()
        
        # Obtenir les paramètres de base de l'AntiDetectionSystem
        if not self.anti_detection_system:
            delay_ms, gas_mult, amount_mult = 1000, 1.0, 1.0
            logger.warning("AntiDetectionSystem non initialisé, utilisation de valeurs par défaut")
        else:
            delay_ms, gas_mult, amount_mult = await self.anti_detection_system.apply_humanization(tx_type)
        
        # Appliquer les modifications du profil actif
        profile = self.active_profile
        pattern = random.choice(profile.trading_patterns) if profile.trading_patterns else {}
        
        # Calculer les splits
        splits = pattern.get("entry_split", [1.0]) if is_entry else pattern.get("exit_split", [1.0])
        current_split = splits[0] if splits else 1.0
        
        # Appliquer la randomisation basée sur le profil
        amount_variation = profile.randomization_factors.get("amount", 0.03)
        random_factor = 1.0 + random.uniform(-amount_variation, amount_variation)
        
        # Variation additionnelle pour l'obfuscation si activée
        if self.config.tx_obfuscation_enabled:
            min_var, max_var = self.config.amount_variation_range
            obfuscation_factor = 1.0 + random.uniform(min_var, max_var) * random.choice([-1, 1])
            random_factor *= obfuscation_factor
            self.total_obfuscated_txs += 1
        
        # Ajouter une transaction "poussière" occasionnellement
        dust_amount = 0.0
        if self.config.tx_obfuscation_enabled and random.random() < self.config.dust_transaction_probability:
            dust_amount = base_amount * 0.001 * random.uniform(0.5, 2.0)  # 0.05%-0.2% du montant principal
            self.total_dust_txs += 1
        
        # Calculer le montant final
        final_amount = (base_amount * current_split * amount_mult * random_factor) + dust_amount
        
        # Adapter le gas en fonction du comportement du profil
        gas_behavior = pattern.get("gas_behavior", "normal")
        gas_behavior_multipliers = {
            "economic": 0.85,
            "normal": 1.0,
            "aggressive": 1.2
        }
        gas_mult *= gas_behavior_multipliers.get(gas_behavior, 1.0)
        
        # Ajuster le délai en fonction du profil
        timing_variation = profile.randomization_factors.get("timing", 0.15)
        delay_factor = 1.0 + random.uniform(-timing_variation, timing_variation)
        final_delay_ms = int(delay_ms * delay_factor)
        
        # Tracking pour anti-pattern
        self._update_transaction_history(tx_type, final_amount, token_symbol)
        
        # Mettre à jour le statut de la blockchain si une transaction a échoué ou réussi
        if self.config.ai_profile_management:
            # Cela sera fait après l'exécution par update_wallet_reputation
            pass
        
        return {
            "amount": final_amount,
            "gas_multiplier": gas_mult,
            "delay_ms": final_delay_ms,
            "slippage_tolerance": pattern.get("slippage_tolerance", 1.0),
            "remaining_splits": len(splits) - 1 if splits else 0,
            "split_amounts": splits[1:] if len(splits) > 1 else [],
            "uses_limit_order": profile.uses_limit_orders and random.random() < 0.8,  # 80% de chance si le profil utilise des limit orders
            "transaction_id": self._generate_tx_id(tx_type, token_symbol, final_amount)
        }
    
    def _update_transaction_history(self, tx_type: str, amount: float, token_symbol: str) -> None:
        """Met à jour l'historique des transactions pour la détection de patterns."""
        now = datetime.now()
        
        # Enregistrer la transaction
        self.transaction_history.append({
            "timestamp": now,
            "type": tx_type,
            "amount": amount,
            "token": token_symbol
        })
        
        # Garder seulement les 100 dernières transactions
        if len(self.transaction_history) > 100:
            self.transaction_history = self.transaction_history[-100:]
        
        # Vérifier les patterns
        self._detect_and_break_patterns(tx_type, token_symbol)
    
    def _detect_and_break_patterns(self, tx_type: str, token_symbol: str) -> None:
        """Détecte et brise les patterns récurrents."""
        if len(self.transaction_history) < 5:
            return
        
        # Compter les transactions similaires consécutives
        recent_txs = self.transaction_history[-5:]
        similar_count = 1
        
        for i in range(len(recent_txs) - 1, 0, -1):
            if (recent_txs[i]["type"] == recent_txs[i-1]["type"] and
                recent_txs[i]["token"] == recent_txs[i-1]["token"]):
                similar_count += 1
            else:
                break
        
        # Si trop de transactions similaires consécutives, enregistrer le pattern
        if similar_count >= self.config.max_consecutive_similar_txs:
            pattern_key = f"{tx_type}_{token_symbol}"
            self.pattern_detection_state[pattern_key] = self.pattern_detection_state.get(pattern_key, 0) + 1
            
            logger.warning(
                f"Pattern détecté: {similar_count} transactions similaires consécutives "
                f"de type {tx_type} pour {token_symbol}. Augmentation de la variance."
            )
    
    def _generate_tx_id(self, tx_type: str, token_symbol: str, amount: float) -> str:
        """Génère un ID unique pour le suivi des transactions."""
        now_str = datetime.now().isoformat()
        unique_str = f"{tx_type}_{token_symbol}_{amount}_{now_str}_{random.random()}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    async def apply_wallet_rotation_strategy(self, current_wallet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique une stratégie avancée de rotation de wallets pour éviter la détection.
        
        Args:
            current_wallet: Wallet actuellement utilisé
            
        Returns:
            Wallet à utiliser pour la prochaine transaction
        """
        if not self.config.wallet_reputation_tracking:
            # Utiliser la stratégie de base si le tracking de réputation est désactivé
            if not self.anti_detection_system:
                logger.warning("AntiDetectionSystem non initialisé, utilisation du wallet actuel")
                return current_wallet
            return await self.anti_detection_system.get_next_wallet()
        
        # Obtenir tous les wallets disponibles
        wallet_key = current_wallet.get("public_key", "")
        
        # Si le wallet actuel a une mauvaise réputation, le changer
        current_reputation = self.wallet_reputation_scores.get(wallet_key, 100)
        if current_reputation < 70:
            logger.info(f"Rotation de wallet forcée en raison d'une réputation faible: {current_reputation}/100")
            if not self.anti_detection_system:
                logger.warning("AntiDetectionSystem non initialisé, utilisation du wallet actuel")
                return current_wallet
            return await self.anti_detection_system.get_next_wallet()
        
        # Appliquer la stratégie standard avec une composante aléatoire
        if random.random() < 0.2:  # 20% de chance de changer de wallet même si pas nécessaire
            if not self.anti_detection_system:
                logger.warning("AntiDetectionSystem non initialisé, utilisation du wallet actuel")
                return current_wallet
            return await self.anti_detection_system.get_next_wallet()
        
        # Sinon continuer avec le wallet actuel
        return current_wallet
    
    async def update_wallet_reputation(
        self, 
        wallet_key: str, 
        transaction_success: bool, 
        dex_flags: Optional[List[str]] = None
    ) -> None:
        """
        Met à jour la réputation d'un wallet basée sur ses transactions.
        
        Args:
            wallet_key: Clé publique du wallet
            transaction_success: Si la transaction a réussi
            dex_flags: Éventuels drapeaux/avertissements du DEX
        """
        if not self.config.wallet_reputation_tracking:
            return
        
        # Initialiser la réputation si nécessaire
        if wallet_key not in self.wallet_reputation_scores:
            self.wallet_reputation_scores[wallet_key] = 100  # Score de départ optimal
        
        current_score = self.wallet_reputation_scores[wallet_key]
        
        # Ajuster le score en fonction du succès de la transaction
        if transaction_success:
            # Petite augmentation pour transactions réussies
            new_score = min(100, current_score + 1)
        else:
            # Pénalité pour échec
            new_score = max(0, current_score - 10)
        
        # Pénalités additionnelles pour les flags DEX
        if dex_flags:
            penalty = len(dex_flags) * 15  # 15 points par flag
            new_score = max(0, new_score - penalty)
            
            if penalty > 0:
                logger.warning(
                    f"Wallet {wallet_key[:8]}... a reçu une pénalité de {penalty} points "
                    f"en raison de flags DEX: {', '.join(dex_flags)}"
                )
        
        # Mettre à jour le score
        self.wallet_reputation_scores[wallet_key] = new_score
        
        # Alerte si score critique
        if new_score < 50:
            logger.warning(f"Wallet {wallet_key[:8]}... a une réputation critique: {new_score}/100")
        
        # Mettre à jour le statut de la blockchain pour le système d'intelligence de profil
        if self.config.ai_profile_management:
            # Extraire la blockchain de la dernière transaction
            blockchain = "solana"  # Par défaut
            detection_events = 1 if dex_flags else 0
            failed_transactions = 0 if transaction_success else 1
            
            # Trouver la dernière transaction pour déterminer la blockchain
            if self.transaction_history and len(self.transaction_history) > 0:
                last_tx_type = self.transaction_history[-1]["type"]
                if ":" in last_tx_type:
                    blockchain = last_tx_type.split(":")[0]
            
            try:
                await self.profile_intelligence.update_blockchain_status(
                    blockchain=blockchain,
                    detection_events=detection_events,
                    failed_transactions=failed_transactions,
                    total_transactions=1
                )
            except Exception as e:
                logger.warning(f"Erreur lors de la mise à jour du statut blockchain: {str(e)}")
    
    def get_optimal_transaction_timing(self, token_symbol: str, tx_type: str) -> int:
        """
        Détermine le timing optimal pour une transaction afin d'éviter la détection.
        
        Args:
            token_symbol: Symbole du token
            tx_type: Type de transaction
            
        Returns:
            Délai recommandé en millisecondes avant la transaction
        """
        now = datetime.now()
        
        # Déterminer si nous sommes dans une session active
        session_duration = (now - self.current_session_start).total_seconds() / 60
        session_habits = self.active_profile.session_habits
        max_session_length = session_habits.get("session_length_minutes", (60, 120))[1]
        
        # Démarrer une nouvelle session si nécessaire
        if session_duration > max_session_length:
            self.current_session_start = now
            min_break, max_break = session_habits.get("break_between_sessions_minutes", (5, 20))
            return random.randint(min_break * 60 * 1000, max_break * 60 * 1000)  # Convertir en ms
        
        # Obtenir le délai de base du profil actif
        pattern = random.choice(self.active_profile.trading_patterns) if self.active_profile.trading_patterns else {}
        typical_delays = pattern.get("typical_delays", [2000, 5000, 8000])
        base_delay = random.choice(typical_delays)
        
        # Augmenter la variance si patterns détectés
        pattern_key = f"{tx_type}_{token_symbol}"
        pattern_count = self.pattern_detection_state.get(pattern_key, 0)
        
        variance_multiplier = 1.0
        if pattern_count > 0:
            variance_multiplier += pattern_count * 0.2  # +20% par pattern détecté
        
        # Appliquer la randomisation
        randomization_strength = self.config.time_randomization_strength
        time_variation = base_delay * randomization_strength * variance_multiplier
        final_delay = base_delay + random.uniform(-time_variation, time_variation)
        
        # Augmenter la variance après plusieurs heures d'activité
        hours_active = session_duration / 60
        if hours_active > self.config.variance_increase_after_hours:
            extra_variance = (hours_active - self.config.variance_increase_after_hours) * 0.1  # +10% par heure
            final_delay *= (1.0 + min(extra_variance, 0.5))  # Max +50%
        
        return max(100, int(final_delay))  # Minimum 100ms
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le StealthManager.
        
        Returns:
            Dictionnaire de statistiques
        """
        stats = {
            "active_profile": self.active_profile.name,
            "total_profile_rotations": self.total_profile_rotations,
            "total_obfuscated_txs": self.total_obfuscated_txs,
            "total_dust_txs": self.total_dust_txs,
            "wallet_reputation_tracking": len(self.wallet_reputation_scores),
            "patterns_detected": sum(self.pattern_detection_state.values()),
            "current_session_duration_minutes": (datetime.now() - self.current_session_start).total_seconds() / 60,
            "anti_detection_stats": self.anti_detection_system.get_stats() if self.anti_detection_system else {}
        }
        
        # Ajouter les statistiques du système d'intelligence de profil
        if self.config.ai_profile_management:
            stats["profile_intelligence"] = self.profile_intelligence.get_stats()
        
        return stats

def create_stealth_manager(
    config_path: Optional[str] = None,
    stealth_config: Optional[StealthConfig] = None,
    anti_detection_system: Optional[AntiDetectionSystem] = None
) -> StealthManager:
    """
    Crée et retourne une instance de StealthManager.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        stealth_config: Configuration du système de discrétion
        anti_detection_system: Instance existante de AntiDetectionSystem
        
    Returns:
        Instance de StealthManager
    """
    return StealthManager(
        config=stealth_config,
        anti_detection_system=anti_detection_system,
        config_path=config_path
    ) 