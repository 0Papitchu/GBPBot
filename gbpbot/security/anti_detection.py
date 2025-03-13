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
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from gbpbot.utils.logger import setup_logger
from gbpbot.config.settings import get_settings
import re
import ipaddress
import platform
import uuid
import hashlib

# Configuration du logger
logger = setup_logger("anti_detection", logging.INFO)

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

class HumanBehaviorSimulator:
    """
    Simule un comportement de trading humain naturel pour éviter la détection
    par les mécanismes anti-bot des DEX.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le simulateur de comportement humain.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or {}
        self.settings = get_settings()
        
        # Paramètres de comportement humain
        self.typing_speed = self.config.get("typing_speed", (0.5, 2.0))  # secondes par action
        self.reaction_time = self.config.get("reaction_time", (1.0, 5.0))  # secondes pour réagir
        self.decision_time = self.config.get("decision_time", (3.0, 15.0))  # secondes pour décider
        self.error_probability = self.config.get("error_probability", 0.05)  # 5% de chance d'erreur
        self.correction_time = self.config.get("correction_time", (1.0, 3.0))  # temps pour corriger
        
        # Historique des comportements pour créer des patterns cohérents
        self.behavior_history = []
        self.last_interaction_time = datetime.now()
        
        # Modèles de distribution pour les délais
        self._build_delay_models()
    
    def _build_delay_models(self):
        """Crée des modèles de distribution pour les délais humains naturels."""
        # Utilise une distribution log-normale pour les délais (plus réaliste)
        self.delay_models = {
            "typing": lambda: np.random.lognormal(mean=0.0, sigma=0.6) * 
                            (self.typing_speed[1] - self.typing_speed[0]) + self.typing_speed[0],
            "reaction": lambda: np.random.lognormal(mean=0.3, sigma=0.5) * 
                              (self.reaction_time[1] - self.reaction_time[0]) + self.reaction_time[0],
            "decision": lambda: np.random.lognormal(mean=0.5, sigma=0.7) * 
                              (self.decision_time[1] - self.decision_time[0]) + self.decision_time[0],
            "correction": lambda: np.random.lognormal(mean=0.0, sigma=0.4) * 
                                (self.correction_time[1] - self.correction_time[0]) + self.correction_time[0],
        }
        
        # Modèle pour les erreurs de trading (achats/ventes interrompus, annulations, etc.)
        self.error_model = lambda: random.random() < self.error_probability
    
    async def simulate_delay(self, action_type: str = "reaction") -> float:
        """
        Simule un délai naturel en fonction du type d'action.
        
        Args:
            action_type: Type de délai à simuler (typing, reaction, decision, correction)
            
        Returns:
            Délai simulé en secondes
        """
        if action_type not in self.delay_models:
            action_type = "reaction"  # type par défaut
            
        # Calcule le délai en tenant compte de l'heure de la journée
        base_delay = self.delay_models[action_type]()
        
        # Ajuste en fonction du temps écoulé depuis la dernière interaction
        time_since_last = (datetime.now() - self.last_interaction_time).total_seconds()
        if time_since_last > 300:  # 5 minutes sans interaction
            # Simule un utilisateur qui revient après une pause
            base_delay *= 1.5
            
        # Simule le délai
        delay = max(0.1, base_delay)  # Évite les délais négatifs ou trop courts
        logger.debug(f"Simulant un délai de comportement humain de {delay:.2f}s pour une action de type '{action_type}'")
        
        await asyncio.sleep(delay)
        self.last_interaction_time = datetime.now()
        self.behavior_history.append((action_type, delay, datetime.now()))
        
        return delay
    
    def should_make_error(self) -> bool:
        """
        Détermine si une erreur de trading doit être simulée.
        
        Returns:
            True si une erreur doit être simulée, sinon False
        """
        return self.error_model()
    
    async def get_randomized_amount(self, base_amount: float, variance_percent: float = 10.0) -> float:
        """
        Génère un montant légèrement différent du montant de base pour simuler un comportement humain.
        
        Args:
            base_amount: Montant de base
            variance_percent: Pourcentage de variance (défaut 10%)
            
        Returns:
            Montant randomisé
        """
        await self.simulate_delay("decision")
        
        # Génère une variance aléatoire autour du montant de base
        variance_factor = 1.0 + (random.random() * 2 - 1) * (variance_percent / 100)
        
        # Arrondis à une précision humaine (évite les nombres très précis comme 1.23456789)
        randomized = base_amount * variance_factor
        significant_digits = random.randint(1, 3)  # Humains utilisent généralement 1-3 chiffres significatifs
        
        # Formatte pour "arrondir" à un nombre de chiffres significatifs
        if randomized < 1:
            # Pour les petits montants, garde plus de décimales
            decimal_places = random.randint(4, 6)
            randomized = round(randomized, decimal_places)
        else:
            # Pour les montants plus grands, réduit les décimales
            decimal_places = random.randint(1, 3)
            randomized = round(randomized, decimal_places)
        
        logger.debug(f"Montant de base {base_amount} randomisé à {randomized}")
        return randomized
    
    async def simulate_social_activity(self) -> None:
        """
        Simule périodiquement une activité sociale (comme consulter Twitter, Discord, etc.)
        pour créer un pattern d'utilisation plus réaliste.
        """
        social_delay = random.uniform(5, 15)  # minutes
        logger.debug(f"Planification d'une activité sociale dans {social_delay} minutes")
        await asyncio.sleep(social_delay * 60)
        
        # Simule une activité sociale (en réalité, juste un délai)
        activity_time = random.uniform(1, 5)  # minutes
        logger.info(f"Simulation d'activité sociale pendant {activity_time} minutes")
        await asyncio.sleep(activity_time * 60)
        
        # Mise à jour de l'historique
        self.behavior_history.append(("social_activity", activity_time, datetime.now()))
    
    async def create_realistic_session(self) -> None:
        """
        Crée une session réaliste qui comprend des activités normales entre les transactions.
        """
        # Détermine la durée de la session
        session_length = random.uniform(30, 90)  # minutes
        logger.info(f"Création d'une session réaliste de {session_length:.1f} minutes")
        
        # Nombre d'actions de trading dans cette session
        num_actions = random.randint(3, 8)
        
        # Répartit les actions de trading sur la durée de la session
        time_points = sorted([random.random() * session_length for _ in range(num_actions)])
        
        # Crée une boucle d'événements
        for i, time_point in enumerate(time_points):
            if i > 0:
                wait_time = time_points[i] - time_points[i-1]
                logger.debug(f"Attente de {wait_time:.1f} minutes avant la prochaine action")
                await asyncio.sleep(wait_time * 60)
            
            # 20% de chance d'activité sociale entre les actions
            if random.random() < 0.2:
                await self.simulate_social_activity()
            
            logger.info(f"Action de trading {i+1}/{num_actions}")
            # Ici, le reste du code appellera prepare_transaction, etc.
        
        # En fin de session, simule une pause plus longue
        end_pause = random.uniform(15, 45)  # minutes
        logger.info(f"Fin de session. Pause de {end_pause:.1f} minutes avant la prochaine session")
        await asyncio.sleep(end_pause * 60)

class TransactionRandomizer:
    """
    Système avancé de randomisation des transactions pour éviter la détection
    des patterns de trading par les DEX.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le randomisateur de transactions.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or {}
        self.settings = get_settings()
        self.human_simulator = HumanBehaviorSimulator(config)
        
        # Paramètres de randomisation
        self.amount_variance = self.config.get("amount_variance", 15.0)  # % de variance sur les montants
        self.timing_variance = self.config.get("timing_variance", 30.0)  # % de variance sur le timing
        self.split_probability = self.config.get("split_probability", 0.3)  # 30% de chance de diviser une transaction
        self.max_splits = self.config.get("max_splits", 3)  # Nombre max de divisions
        
        # État interne
        self.recent_transactions = []
        self.transaction_patterns = {}
    
    async def randomize_transaction_amount(self, amount: float) -> float:
        """
        Randomise le montant d'une transaction pour éviter les patterns détectables.
        
        Args:
            amount: Montant initial prévu
            
        Returns:
            Montant randomisé
        """
        return await self.human_simulator.get_randomized_amount(amount, self.amount_variance)
    
    async def randomize_transaction_timing(self, base_delay: float) -> float:
        """
        Randomise le timing d'une transaction pour éviter les patterns détectables.
        
        Args:
            base_delay: Délai de base en secondes
            
        Returns:
            Délai randomisé en secondes
        """
        # Calcule un délai aléatoire basé sur le délai de base
        variance = base_delay * (self.timing_variance / 100)
        random_delay = base_delay + random.uniform(-variance, variance)
        
        # Assure que le délai reste positif et raisonnable
        randomized_delay = max(0.1, random_delay)
        
        logger.debug(f"Délai de base {base_delay}s randomisé à {randomized_delay}s")
        await asyncio.sleep(randomized_delay)
        
        return randomized_delay
    
    async def should_split_transaction(self, amount: float) -> Tuple[bool, int]:
        """
        Détermine si une transaction doit être divisée en plusieurs transactions
        plus petites pour éviter la détection.
        
        Args:
            amount: Montant de la transaction
            
        Returns:
            (doit_diviser, nombre_de_divisions)
        """
        # Plus le montant est élevé, plus la probabilité de division augmente
        amount_factor = min(1.0, amount / 1000.0)  # Normalisé jusqu'à 1000 unités
        adjusted_probability = self.split_probability * (1 + amount_factor)
        
        should_split = random.random() < adjusted_probability
        
        if should_split:
            # Détermine le nombre de divisions en fonction du montant
            splits = min(
                self.max_splits,
                max(2, int(amount_factor * self.max_splits))
            )
            return True, splits
        
        return False, 1
    
    async def get_split_amounts(self, total_amount: float, num_splits: int) -> List[float]:
        """
        Génère plusieurs montants qui se somment au montant total pour diviser
        une transaction de manière réaliste.
        
        Args:
            total_amount: Montant total à diviser
            num_splits: Nombre de divisions souhaitées
            
        Returns:
            Liste des montants divisés
        """
        # Utilise une distribution Dirichlet pour générer des ratios qui somment à 1
        alphas = [random.uniform(0.5, 1.5) for _ in range(num_splits)]
        ratios = np.random.dirichlet(alphas)
        
        # Calcule les montants en fonction des ratios
        amounts = [total_amount * ratio for ratio in ratios]
        
        # Randomise légèrement chaque montant divisé
        randomized_amounts = []
        for amount in amounts:
            randomized = await self.randomize_transaction_amount(amount)
            randomized_amounts.append(randomized)
        
        # Ajuste le dernier montant pour s'assurer que la somme est exactement le montant total
        adjustment = total_amount - sum(randomized_amounts[:-1])
        randomized_amounts[-1] = max(0.001, adjustment)  # Assure que le montant est positif
        
        logger.debug(f"Transaction de {total_amount} divisée en {randomized_amounts}")
        return randomized_amounts
    
    async def get_execution_delays(self, num_transactions: int, base_window: float) -> List[float]:
        """
        Génère des délais d'exécution pour plusieurs transactions qui semblent naturels.
        
        Args:
            num_transactions: Nombre de transactions à exécuter
            base_window: Fenêtre de temps totale pour les transactions (en secondes)
            
        Returns:
            Liste des délais entre chaque transaction
        """
        # Distribue les transactions sur la fenêtre de temps
        if num_transactions <= 1:
            return [0.0]
            
        # Génère des points de temps aléatoires dans la fenêtre
        time_points = sorted([random.random() * base_window for _ in range(num_transactions - 1)])
        time_points = [0.0] + time_points + [base_window]
        
        # Calcule les délais entre les points de temps
        delays = [time_points[i+1] - time_points[i] for i in range(num_transactions)]
        
        # Randomise chaque délai pour plus de naturel
        randomized_delays = []
        for delay in delays:
            randomized = await self.randomize_transaction_timing(delay)
            randomized_delays.append(randomized)
        
        logger.debug(f"Délais d'exécution générés: {randomized_delays}")
        return randomized_delays
    
    async def create_natural_order_size(self, base_amount: float, market_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Crée une taille d'ordre qui semble naturelle en tenant compte des données du marché.
        
        Args:
            base_amount: Montant de base suggéré
            market_data: Données de marché optionnelles (volumes, prix récents, etc.)
            
        Returns:
            Taille d'ordre naturelle
        """
        # Les humains préfèrent certains chiffres (arrondis, nombres simples)
        human_preferences = [
            # Chiffres ronds
            lambda x: round(x),
            lambda x: round(x, 1),
            lambda x: round(x, 2),
            # Nombres se terminant par 5 ou 0
            lambda x: round(x * 2) / 2,
            lambda x: round(x * 20) / 20,
            # Nombres "psychologiques"
            lambda x: round(x * 0.99, 2),  # Juste en dessous d'un nombre rond
            lambda x: round(x * 1.01, 2),  # Juste au-dessus d'un nombre rond
        ]
        
        # Choisir une préférence aléatoire
        preference = random.choice(human_preferences)
        natural_amount = preference(base_amount)
        
        # Si nous avons des données de marché, ajustons en fonction des volumes typiques
        if market_data and "average_order_size" in market_data:
            avg_order = market_data["average_order_size"]
            # Mélange entre notre montant et la moyenne du marché
            blend_factor = random.uniform(0.3, 0.7)
            adjusted_amount = (natural_amount * blend_factor) + (avg_order * (1 - blend_factor))
            natural_amount = preference(adjusted_amount)  # Réappliquer la préférence
        
        logger.debug(f"Montant de base {base_amount} transformé en ordre naturel de {natural_amount}")
        return natural_amount
    
    async def create_transaction_batches(self, total_volume: float, time_window: float) -> List[Dict[str, Any]]:
        """
        Crée un plan de batches de transactions qui semble naturel pour un volume total donné.
        
        Args:
            total_volume: Volume total à trader
            time_window: Fenêtre de temps disponible (minutes)
            
        Returns:
            Liste de spécifications de transactions
        """
        # Détermine le nombre de batches en fonction du volume
        volume_factor = min(1.0, total_volume / 5000)  # Normalisé jusqu'à 5000 unités
        base_batches = 1 + int(volume_factor * 5)  # 1 à 6 batches
        num_batches = random.randint(base_batches, base_batches + 2)
        
        # Distribue le volume entre les batches (pas uniformément)
        if num_batches == 1:
            volumes = [total_volume]
            else:
            # Plus de volume au début ou à la fin (50/50)
            if random.random() < 0.5:
                # Front-loaded (plus au début)
                weights = [max(0.1, 1.0 - (i * 0.15)) for i in range(num_batches)]
            else:
                # Back-loaded (plus à la fin)
                weights = [max(0.1, 0.3 + (i * 0.15)) for i in range(num_batches)]
            
            # Normalise les poids
            total_weight = sum(weights)
            norm_weights = [w / total_weight for w in weights]
            
            # Calcule les volumes
            volumes = [total_volume * w for w in norm_weights]
        
        # Distribue les timestamps sur la fenêtre de temps
        if num_batches == 1:
            timestamps = [time_window / 2]  # Milieu de la fenêtre
        else:
            # Répartition non uniforme des timestamps
            raw_points = [random.random() ** 1.5 for _ in range(num_batches)]
            total_raw = sum(raw_points)
            norm_points = [p / total_raw for p in raw_points]
            timestamps = [time_window * (sum(norm_points[:i+1]) - norm_points[i]/2) 
                        for i in range(num_batches)]
        
        # Crée les spécifications de transactions
        transactions = []
        for i in range(num_batches):
            # Divise potentiellement chaque batch en multiples transactions
            should_split, num_splits = await self.should_split_transaction(volumes[i])
            
            if should_split and num_splits > 1:
                split_volumes = await self.get_split_amounts(volumes[i], num_splits)
                
                # Fenêtre de temps plus petite pour ce batch (±15% du temps entre batches)
                if i < len(timestamps) - 1:
                    next_time = timestamps[i+1]
                else:
                    next_time = time_window
                
                batch_window = min(5, max(0.5, (next_time - timestamps[i]) * 0.3))
                split_delays = await self.get_execution_delays(num_splits, batch_window)
                
                # Crée une transaction par split
                base_time = timestamps[i]
                for j in range(num_splits):
                    delay = sum(split_delays[:j]) if j > 0 else 0
                    transactions.append({
                        "volume": split_volumes[j],
                        "timestamp": base_time + delay,
                        "is_split": True,
                        "batch_id": i,
                        "split_id": j
                    })
            else:
                transactions.append({
                    "volume": volumes[i],
                    "timestamp": timestamps[i],
                    "is_split": False,
                    "batch_id": i,
                    "split_id": 0
                })
        
        # Trie par timestamp
        transactions.sort(key=lambda x: x["timestamp"])
        logger.info(f"Plan de {len(transactions)} transactions créé pour un volume total de {total_volume}")
        return transactions

class AddressRotationManager:
    """
    Gère la rotation des adresses pour éviter d'être détecté ou blacklisté par les DEX.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de rotation d'adresses.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or {}
        self.settings = get_settings()
        
        # Paramètres de rotation
        self.rotation_threshold = self.config.get("rotation_threshold", 5)  # Nb de transactions avant rotation
        self.max_usage_time = self.config.get("max_usage_time", 24)  # Heures max d'utilisation d'une adresse
        self.cool_down_period = self.config.get("cool_down_period", 48)  # Heures de repos entre usages
        
        # État interne
        self.address_usage = {}  # {address: {"transactions": count, "last_used": datetime, "first_used": datetime}}
        self.active_addresses = set()
        self.cool_down_addresses = set()
        
    def register_address(self, address: str):
        """
        Enregistre une nouvelle adresse dans le système de rotation.
        
        Args:
            address: Adresse à enregistrer
        """
        if address not in self.address_usage:
            self.address_usage[address] = {
                "transactions": 0,
                "last_used": None,
                "first_used": None,
                "total_volume": 0.0
            }
            logger.info(f"Nouvelle adresse enregistrée dans le système de rotation: {address[:10]}...")
    
    def record_transaction(self, address: str, volume: float = 0.0):
        """
        Enregistre une transaction pour une adresse et met à jour son utilisation.
        
        Args:
            address: Adresse utilisée pour la transaction
            volume: Volume de la transaction (optionnel)
        """
        if address not in self.address_usage:
            self.register_address(address)
        
        now = datetime.now()
        
        # Initialise first_used si c'est la première transaction
        if self.address_usage[address]["first_used"] is None:
            self.address_usage[address]["first_used"] = now
            self.active_addresses.add(address)
        
        # Met à jour les statistiques
        self.address_usage[address]["transactions"] += 1
        self.address_usage[address]["last_used"] = now
        self.address_usage[address]["total_volume"] += volume
        
        logger.debug(f"Transaction enregistrée pour l'adresse {address[:10]}... " +
                  f"(total: {self.address_usage[address]['transactions']})")
    
    def should_rotate(self, address: str) -> bool:
        """
        Détermine si une adresse doit être mise en rotation (retirée temporairement de l'utilisation).
        
        Args:
            address: Adresse à vérifier
        
        Returns:
            True si l'adresse doit être mise en rotation, sinon False
        """
        if address not in self.address_usage:
            return False
        
        usage = self.address_usage[address]
        now = datetime.now()
        
        # Vérifie si le nombre de transactions dépasse le seuil
        if usage["transactions"] >= self.rotation_threshold:
            return True
        
        # Vérifie si l'adresse est utilisée depuis trop longtemps
        if usage["first_used"] and (now - usage["first_used"]) > timedelta(hours=self.max_usage_time):
            return True
        
        return False
    
    def rotate_address(self, address: str):
        """
        Met une adresse en rotation (retirée temporairement de l'utilisation).
        
        Args:
            address: Adresse à mettre en rotation
        """
        if address in self.active_addresses:
            self.active_addresses.remove(address)
            self.cool_down_addresses.add(address)
            logger.info(f"Adresse {address[:10]}... mise en rotation après " +
                      f"{self.address_usage[address]['transactions']} transactions")
    
    def get_available_address(self, current_address: str) -> Optional[str]:
        """
        Retourne une adresse disponible pour la rotation, différente de l'adresse actuelle.
        
        Args:
            current_address: Adresse actuellement utilisée
        
        Returns:
            Nouvelle adresse à utiliser, ou None si aucune adresse n'est disponible
        """
        # Vérifie si des adresses en période de repos peuvent être réactivées
        now = datetime.now()
        for addr in list(self.cool_down_addresses):
            last_used = self.address_usage[addr]["last_used"]
            if last_used and (now - last_used) > timedelta(hours=self.cool_down_period):
                self.cool_down_addresses.remove(addr)
                self.active_addresses.add(addr)
                # Réinitialise les compteurs d'utilisation
                self.address_usage[addr]["transactions"] = 0
                self.address_usage[addr]["first_used"] = None
                logger.info(f"Adresse {addr[:10]}... réactivée après période de repos")
        
        # Filtre les adresses actives différentes de l'adresse actuelle
        candidates = [addr for addr in self.active_addresses if addr != current_address]
        
        if not candidates:
            logger.warning("Aucune adresse alternative disponible pour la rotation")
            return None
        
        # Sélectionne l'adresse la moins utilisée
        return min(candidates, key=lambda a: self.address_usage[a]["transactions"])
    
    def get_rotation_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur la rotation des adresses.
        
        Returns:
            Dictionnaire de statistiques
        """
        return {
            "active_addresses": len(self.active_addresses),
            "cooling_down_addresses": len(self.cool_down_addresses),
            "total_managed_addresses": len(self.address_usage),
            "rotation_threshold": self.rotation_threshold,
            "max_usage_time_hours": self.max_usage_time,
            "cool_down_period_hours": self.cool_down_period
        }
    
    def get_behavioral_identifiers(self, address: str) -> Dict[str, Any]:
        """
        Génère un ensemble d'identifiants comportementaux uniques à associer à une adresse.
        Ces identifiants aident à maintenir des comportements cohérents par adresse.
        
        Args:
            address: Adresse à analyser
        
        Returns:
            Dictionnaire d'identifiants comportementaux
        """
        if address not in self.address_usage:
            self.register_address(address)
        
        # Utilise un hash de l'adresse comme seed pour la génération de caractéristiques
        addr_hash = hashlib.md5(address.encode()).hexdigest()
        hash_int = int(addr_hash, 16)
        
        # Génère des caractéristiques pseudo-aléatoires mais déterministes pour cette adresse
        random.seed(hash_int)
        
        # Caractéristiques comportementales
        behavior = {
            # Préférences de trading
            "prefers_round_numbers": random.random() < 0.6,
            "typical_order_size_factor": random.uniform(0.8, 1.2),
            "risk_tolerance": random.uniform(0.3, 0.8),
            "patience": random.uniform(0.4, 0.9),
            
            # Habitudes temporelles
            "trading_time_preference": random.choice(["morning", "afternoon", "evening", "night"]),
            "weekend_trader": random.random() < 0.4,
            "average_session_length_minutes": random.randint(20, 120),
            
            # Style d'interaction
            "transaction_frequency": random.choice(["low", "medium", "high"]),
            "trading_style": random.choice(["conservative", "balanced", "aggressive"]),
            "multi_dex_trader": random.random() < 0.7,
            
            # "Personnalité" de trading
            "reactive_to_market": random.random() < 0.65,
            "follows_trends": random.random() < 0.55,
            "contrarian": random.random() < 0.25,
            
            # Identifiants techniques simulés (facteurs d'empreinte digitale)
            "user_agent_group": random.randint(1, 10),
            "screen_resolution_group": random.randint(1, 8),
            "timezone_offset": random.choice([-8, -7, -5, -4, 0, 1, 2, 3, 8, 9])
        }
        
        # Réinitialise le générateur aléatoire pour éviter les effets secondaires
        random.seed()
        
        return behavior
    
    def optimize_rotation_strategy(self) -> None:
        """
        Analyse les patterns d'utilisation et optimise la stratégie de rotation
        pour éviter la détection.
        """
        # Calcule les métriques actuelles
        now = datetime.now()
        active_count = len(self.active_addresses)
        total_count = len(self.address_usage)
        
        # Analyse les volumes récents
        recent_volumes = []
        high_volume_addresses = []
        
        for addr, data in self.address_usage.items():
            if data["last_used"] and (now - data["last_used"]) < timedelta(hours=24):
                recent_volumes.append(data["total_volume"])
                
                # Identifie les adresses à haut volume
                if data["total_volume"] > (sum(recent_volumes) / len(recent_volumes) * 2):
                    high_volume_addresses.append(addr)
        
        # Ajuste les paramètres de rotation en fonction de l'activité
        if high_volume_addresses and len(high_volume_addresses) < active_count * 0.2:
            # Si quelques adresses concentrent beaucoup de volume, réduit le seuil de rotation
            old_threshold = self.rotation_threshold
            self.rotation_threshold = max(3, int(self.rotation_threshold * 0.8))
            logger.info(f"Optimisation: seuil de rotation ajusté de {old_threshold} à {self.rotation_threshold} " +
                      f"en raison de la concentration de volume sur {len(high_volume_addresses)} adresses")
        
        # Ajuste la période de repos en fonction du nombre d'adresses disponibles
        if active_count < 3 and self.cool_down_period > 24:
            # Réduire la période de repos si peu d'adresses sont disponibles
            old_period = self.cool_down_period
            self.cool_down_period = max(12, int(self.cool_down_period * 0.7))
            logger.info(f"Optimisation: période de repos ajustée de {old_period}h à {self.cool_down_period}h " +
                      f"en raison du faible nombre d'adresses actives ({active_count})")

class DEXDetectionCountermeasures:
    """
    Implémente des contre-mesures spécifiques aux mécanismes de détection
    des DEX les plus populaires.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise les contre-mesures de détection DEX.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or {}
        self.settings = get_settings()
        
        # Paramètres de configuration
        self.enable_browser_fingerprinting = self.config.get("enable_browser_fingerprinting", True)
        self.enable_contract_interaction_patterns = self.config.get("enable_contract_interaction_patterns", True)
        self.enable_metadata_obfuscation = self.config.get("enable_metadata_obfuscation", True)
        
        # Statistiques des DEX connus
        self.dex_detection_methods = {
            "uniswap": ["ip_tracking", "wallet_patterns", "transaction_timing", "gas_patterns"],
            "pancakeswap": ["browser_fingerprinting", "wallet_patterns", "contract_interactions"],
            "sushiswap": ["ip_tracking", "wallet_patterns", "node_detection"],
            "traderjoe": ["transaction_timing", "wallet_patterns", "metadata"],
            "raydium": ["transaction_patterns", "wallet_velocity", "contract_interactions"],
            "orca": ["metadata", "transaction_timing", "wallet_patterns"],
            "serum": ["wallet_velocity", "transaction_patterns", "node_detection"]
        }
        
        # Historique des contre-mesures appliquées
        self.countermeasures_history = []
        
        logger.info("Contre-mesures de détection DEX initialisées")
    
    def get_dex_countermeasures(self, dex_name: str) -> Dict[str, Any]:
        """
        Récupère les contre-mesures spécifiques pour un DEX particulier.
        
        Args:
            dex_name: Nom du DEX (ex: "uniswap", "raydium")
            
        Returns:
            Dictionnaire de contre-mesures à appliquer
        """
        dex_name = dex_name.lower()
        detection_methods = self.dex_detection_methods.get(
            dex_name, ["wallet_patterns", "transaction_timing"])
        
        countermeasures = {
            "ip_tracking": {
                "apply": "ip_tracking" in detection_methods,
                "rotate_ip": True,
                "use_proxy": True
            },
            "browser_fingerprinting": {
                "apply": "browser_fingerprinting" in detection_methods and self.enable_browser_fingerprinting,
                "randomize_useragent": True,
                "spoof_canvas": True,
                "block_webrtc": True
            },
            "wallet_patterns": {
                "apply": "wallet_patterns" in detection_methods,
                "rotate_wallets": True,
                "minimize_volume_per_wallet": True
            },
            "transaction_timing": {
                "apply": "transaction_timing" in detection_methods,
                "add_random_delays": True,
                "avoid_patterns": True,
                "simulate_human_timing": True
            },
            "contract_interactions": {
                "apply": "contract_interactions" in detection_methods and self.enable_contract_interaction_patterns,
                "diversify_function_calls": True,
                "simulate_ui_interactions": True,
                "randomize_gas": True
            },
            "metadata": {
                "apply": "metadata" in detection_methods and self.enable_metadata_obfuscation,
                "clean_transaction_data": True,
                "randomize_input_data": True
            }
        }
        
        logger.debug(f"Contre-mesures générées pour {dex_name}: " +
                   f"{[k for k, v in countermeasures.items() if v['apply']]}")
        return countermeasures
    
    def apply_dex_countermeasures(self, transaction_data: Dict[str, Any], dex_name: str) -> Dict[str, Any]:
        """
        Applique les contre-mesures spécifiques au DEX sur les données de transaction.
        
        Args:
            transaction_data: Données de transaction à modifier
            dex_name: Nom du DEX cible
            
        Returns:
            Données de transaction modifiées
        """
        countermeasures = self.get_dex_countermeasures(dex_name)
        result = transaction_data.copy()
        
        # Enregistre l'application des contre-mesures
        applied = [key for key, value in countermeasures.items() if value["apply"]]
        self.countermeasures_history.append({
            "timestamp": datetime.now().isoformat(),
            "dex": dex_name,
            "applied_countermeasures": applied,
            "transaction_id": result.get("id", str(uuid.uuid4()))
        })
        
        # Applique les contre-mesures spécifiques
        if countermeasures["transaction_timing"]["apply"]:
            # Ajoute un retard aléatoire supplémentaire pour ce DEX spécifique
            if "delay_seconds" not in result:
                result["delay_seconds"] = 0
            
            # Délais spécifiques au DEX
            if dex_name == "raydium":
                result["delay_seconds"] += random.uniform(0.8, 2.5)
            elif dex_name == "traderjoe":
                result["delay_seconds"] += random.uniform(1.0, 3.0)
            else:
                result["delay_seconds"] += random.uniform(0.5, 2.0)
        
        if countermeasures["contract_interactions"]["apply"]:
            # Randomise légèrement les paramètres de gas
            if "gas_price" in result:
                variation = random.uniform(-0.02, 0.06)  # -2% à +6%
                result["gas_price"] = result["gas_price"] * (1 + variation)
            
            if "gas_limit" in result:
                # Les humains surestiment souvent la limite de gas
                result["gas_limit"] = int(result["gas_limit"] * random.uniform(1.05, 1.15))
        
        if countermeasures["metadata"]["apply"]:
            # Ajoute un nonce aléatoire aux données
            if "extra_data" not in result:
                result["extra_data"] = {}
            
            result["extra_data"]["client_timestamp"] = int(time.time() * 1000)
            result["extra_data"]["session_id"] = str(uuid.uuid4())
        
        logger.debug(f"Contre-mesures appliquées pour {dex_name}: {applied}")
        return result

class AntiDetectionSystem:
    """
    Système complet d'anti-détection qui combine la randomisation des transactions,
    la simulation de comportement humain et la rotation des adresses.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le système d'anti-détection.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or {}
        self.settings = get_settings()
        
        # Initialise les composants
        self.transaction_randomizer = TransactionRandomizer(self.config.get("transaction_randomizer"))
        self.human_simulator = HumanBehaviorSimulator(self.config.get("human_simulator"))
        self.address_manager = AddressRotationManager(self.config.get("address_manager"))
        self.dex_countermeasures = DEXDetectionCountermeasures(self.config.get("dex_countermeasures"))
        
        logger.info("Système anti-détection initialisé avec tous les composants")
    
    async def prepare_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prépare une transaction en appliquant les techniques d'anti-détection.
        
        Args:
            transaction_data: Données de la transaction (montant, adresse, etc.)
        
        Returns:
            Données de transaction modifiées pour éviter la détection
        """
        result = transaction_data.copy()
        
        # 1. Vérifier si l'adresse doit être mise en rotation
        if "address" in result:
            address = result["address"]
            self.address_manager.record_transaction(address, result.get("amount", 0.0))
            
            if self.address_manager.should_rotate(address):
                new_address = self.address_manager.get_available_address(address)
                if new_address:
                    logger.info(f"Rotation d'adresse: {address[:10]}... -> {new_address[:10]}...")
                    self.address_manager.rotate_address(address)
                    result["address"] = new_address
        
        # 2. Vérifier si la transaction doit être divisée
        amount = result.get("amount", 0.0)
        should_split, num_splits = await self.transaction_randomizer.should_split_transaction(amount)
        
        if should_split and num_splits > 1:
            split_amounts = await self.transaction_randomizer.get_split_amounts(amount, num_splits)
            execution_delays = await self.transaction_randomizer.get_execution_delays(
                num_splits, base_window=60.0)  # 1 minute pour toutes les transactions
            
            result["split_transaction"] = True
            result["split_amounts"] = split_amounts
            result["execution_delays"] = execution_delays
            logger.info(f"Transaction de {amount} divisée en {num_splits} parties")
        else:
            # 3. Si pas de division, randomiser le montant
            if "amount" in result:
                result["amount"] = await self.transaction_randomizer.randomize_transaction_amount(amount)
        
        # 4. Simuler un délai humain avant l'exécution
        await self.human_simulator.simulate_delay("decision")
        
        # 5. Vérifier si une erreur doit être simulée
        if self.human_simulator.should_make_error():
            logger.info("Simulation d'une erreur de trading pour paraître plus humain")
            result["simulate_error"] = True
        
        # Appliquer les contre-mesures spécifiques au DEX
        if "dex" in result:
            result = self.dex_countermeasures.apply_dex_countermeasures(result, result["dex"])
        
        return result
    
    async def post_transaction_delay(self):
        """
        Applique un délai aléatoire après une transaction pour simuler
        un comportement humain.
        """
        return await self.human_simulator.simulate_delay("reaction")
    
    async def create_natural_trading_session(self, duration_minutes: float = 60) -> Dict[str, Any]:
        """
        Crée un plan complet de session de trading naturelle.
    
    Args:
            duration_minutes: Durée totale de la session en minutes
        
    Returns:
            Plan de session avec transactions planifiées
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        logger.info(f"Création d'une session de trading naturelle de {duration_minutes:.1f} minutes")
        
        # Simuler une activité humaine générale
        await self.human_simulator.simulate_delay("decision")
        
        # Déterminer le nombre total de transactions dans cette session
        intensity_factor = random.uniform(0.7, 1.3)  # Variation de l'intensité
        base_tx_count = int(duration_minutes / 15)  # En moyenne une transaction toutes les 15 minutes
        tx_count = max(1, int(base_tx_count * intensity_factor))
        
        # Générer un plan de trading
        trading_plan = await self.transaction_randomizer.create_transaction_batches(
            total_volume=random.uniform(0.1, 2.0),  # Volume fictif pour le plan
            time_window=duration_minutes
        )
        
        # Ajouter des activités sociales et pauses
        activities = []
        for tx in trading_plan:
            # Ajouter la transaction au plan
            activities.append({
                "type": "transaction",
                "time_offset": tx["timestamp"],
                "data": tx
            })
            
            # 20% de chance d'ajouter une activité sociale après une transaction
            if random.random() < 0.2:
                social_offset = tx["timestamp"] + random.uniform(1, 5)
                if social_offset < duration_minutes:
                    activities.append({
                        "type": "social",
                        "time_offset": social_offset,
                        "duration": random.uniform(2, 10)
                    })
            
            # 30% de chance d'ajouter une pause après une transaction
            if random.random() < 0.3:
                pause_offset = tx["timestamp"] + random.uniform(1, 3)
                if pause_offset < duration_minutes:
                    activities.append({
                        "type": "pause",
                        "time_offset": pause_offset,
                        "duration": random.uniform(3, 15)
                    })
        
        # Trier toutes les activités par temps
        activities.sort(key=lambda x: x["time_offset"])
        
        # Créer le plan final de la session
        session_plan = {
            "session_id": session_id,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(minutes=duration_minutes)).isoformat(),
            "duration_minutes": duration_minutes,
            "transaction_count": tx_count,
            "activities": activities,
            "behavioral_profile": {
                "patience": random.uniform(0.3, 0.9),
                "risk_tolerance": random.uniform(0.2, 0.8),
                "trading_style": random.choice(["conservative", "balanced", "aggressive"]),
                "preferred_dex": random.choice(["raydium", "orca", "traderjoe", "uniswap"])
            }
        }
        
        logger.info(f"Plan de session créé avec {len(activities)} activités sur {duration_minutes} minutes")
        return session_plan
    
    def optimize_anti_detection_strategy(self) -> None:
        """
        Analyse les données historiques et optimise la stratégie d'anti-détection.
        """
        # Optimise la stratégie de rotation d'adresses
        self.address_manager.optimize_rotation_strategy()
        
        # Optimisations supplémentaires basées sur l'historique
        if len(self.transaction_randomizer.recent_transactions) > 20:
            patterns = self._analyze_transaction_patterns()
            
            # Si des patterns sont détectés, ajuste les paramètres
            if patterns.get("timing_predictable", False):
                old_variance = self.transaction_randomizer.timing_variance
                self.transaction_randomizer.timing_variance = min(80, old_variance * 1.5)
                logger.info(f"Variance de timing augmentée de {old_variance} à {self.transaction_randomizer.timing_variance} " +
                          "pour éviter les patterns détectables")
            
            if patterns.get("amounts_predictable", False):
                old_variance = self.transaction_randomizer.amount_variance
                self.transaction_randomizer.amount_variance = min(30, old_variance * 1.3)
                logger.info(f"Variance des montants augmentée de {old_variance} à {self.transaction_randomizer.amount_variance} " +
                          "pour éviter les patterns détectables")
    
    def _analyze_transaction_patterns(self) -> Dict[str, bool]:
        """
        Analyse les transactions récentes pour détecter des patterns prédictibles.
        
        Returns:
            Dictionnaire d'indicateurs de pattern
        """
        result = {
            "timing_predictable": False,
            "amounts_predictable": False,
            "split_pattern_visible": False
        }
        
        # Minimum de transactions pour l'analyse
        if len(self.transaction_randomizer.recent_transactions) < 10:
            return result
        
        # Extraire les séries temporelles
        timestamps = [tx.get("timestamp") for tx in self.transaction_randomizer.recent_transactions
                     if "timestamp" in tx]
        amounts = [tx.get("amount") for tx in self.transaction_randomizer.recent_transactions
                 if "amount" in tx]
        
        # Si nous avons des timestamps consécutifs, calculer les délais
        if len(timestamps) > 5:
            delays = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            
            # Calculer l'écart-type des délais
            if delays:
                std_dev = np.std(delays)
                mean_delay = np.mean(delays)
                
                # Si l'écart-type est faible par rapport à la moyenne, pattern détecté
                if std_dev < mean_delay * 0.3:
                    result["timing_predictable"] = True
        
        # Analyser les montants
        if len(amounts) > 5:
            # Vérifier si les montants suivent un pattern (ex: toujours des multiples de 0.1)
            rounded_counts = 0
            for amount in amounts:
                if abs(amount - round(amount, 1)) < 0.001:
                    rounded_counts += 1
            
            if rounded_counts / len(amounts) > 0.7:
                result["amounts_predictable"] = True
        
        return result
        
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "address_rotation": self.address_manager.get_rotation_stats(),
            "last_human_interaction": self.human_simulator.last_interaction_time.isoformat(),
            "behavior_history_count": len(self.human_simulator.behavior_history),
            "dex_countermeasures": {
                "history_count": len(self.dex_countermeasures.countermeasures_history),
                "supported_dex": list(self.dex_countermeasures.dex_detection_methods.keys())
            }
        }
        
        # Ajouter les statistiques d'optimisation
        self.optimize_anti_detection_strategy()
        
        return stats

# Rendre les classes disponibles à l'importation
__all__ = [
    "AntiDetectionSystem",
    "TransactionRandomizer",
    "HumanBehaviorSimulator",
    "AddressRotationManager",
    "DEXDetectionCountermeasures"
] 