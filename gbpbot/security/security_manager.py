#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Sécurité pour GBPBot
====================================

Ce module fournit des fonctionnalités de sécurité avancées pour protéger les fonds
contre les scams, rug pulls, et autres risques liés au trading de crypto-monnaies.

Il implémente diverses protections:
- Détection de rug pulls
- Protection contre les honeypots
- Limites de trading (pertes max, volume max)
- Analyse de contrats
- Vérification du liquidity lock
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import hmac
import hashlib
import re

from gbpbot.utils.logger import setup_logger

# Configuration du logger
logger = setup_logger("SecurityManager", logging.INFO)

class SecurityManager:
    """
    Gestionnaire de sécurité qui protège contre divers risques de trading.
    
    Cette classe fournit des protections contre:
    - Les rug pulls
    - Les honeypots
    - Les pertes excessives
    - Les tokens malveillants
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de sécurité.
        
        Args:
            config: Configuration du gestionnaire de sécurité
        """
        self.config = config
        
        # Paramètres de sécurité généraux
        self.max_daily_trades = int(os.environ.get("MAX_DAILY_TRADES", "100"))
        self.max_loss_per_trade = float(os.environ.get("MAX_LOSS_PER_TRADE", "0.05"))  # 5%
        self.max_daily_loss = float(os.environ.get("MAX_DAILY_LOSS", "0.15"))  # 15%
        self.max_slippage = float(os.environ.get("MAX_SLIPPAGE", "0.05"))  # 5%
        
        # Protection contre les rug pulls
        self.rugpull_protection = RugPullProtection(
            min_liquidity=float(os.environ.get("MIN_LIQUIDITY_USD", "10000")),
            max_owner_tokens=float(os.environ.get("MAX_OWNER_TOKENS_PERCENT", "0.3")),
            min_holders=int(os.environ.get("MIN_HOLDERS", "50")),
            max_tax=float(os.environ.get("MAX_TOKEN_TAX", "0.05"))
        )
        
        # Protection contre les honeypots
        self.honeypot_protection = HoneypotProtection(
            simulate_sell=os.environ.get("SIMULATE_SELL_BEFORE_BUY", "true").lower() == "true",
            min_sell_tx_count=int(os.environ.get("MIN_SELL_TX_COUNT", "10"))
        )
        
        # Statistiques de trading
        self.trade_stats = {
            "daily_trades": 0,
            "total_trades": 0,
            "daily_profit_loss": 0.0,
            "total_profit_loss": 0.0,
            "blocked_tokens": [],
            "last_reset": datetime.now().isoformat()
        }
        
        # Liste des tokens blacklistés
        self.blacklisted_tokens = self._load_blacklist()
        
        # Cache des vérifications récentes
        self.security_checks_cache = {}
        
        logger.info("Gestionnaire de sécurité initialisé")
    
    async def check_token_security(self, token_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Effectue une vérification complète de sécurité sur un token.
        
        Args:
            token_data: Données du token à vérifier
            
        Returns:
            Tuple (sécurisé, détails) où sécurisé est un booléen
            et détails sont les informations de sécurité
        """
        token_address = token_data.get("address", "").lower()
        blockchain = token_data.get("blockchain", "unknown").lower()
        
        # Vérifier le cache pour éviter des requêtes répétées
        cache_key = f"{blockchain}:{token_address}"
        if cache_key in self.security_checks_cache:
            cache_entry = self.security_checks_cache[cache_key]
            # Utiliser le cache seulement s'il est récent (moins de 5 minutes)
            if datetime.now() - cache_entry["timestamp"] < timedelta(minutes=5):
                logger.info(f"Utilisation des résultats en cache pour {token_address}")
                return cache_entry["is_safe"], cache_entry["details"]
        
        # Vérifier si le token est blacklisté
        if token_address in self.blacklisted_tokens:
            details = {"reason": "Token blacklisté", "source": "blacklist"}
            return False, details
        
        # Initialiser les résultats
        is_safe = True
        details = {
            "timestamp": datetime.now().isoformat(),
            "token_address": token_address,
            "blockchain": blockchain,
            "checks": {}
        }
        
        # 1. Vérification du rug pull
        rugpull_safe, rugpull_details = await self.rugpull_protection.check_token(token_data)
        details["checks"]["rugpull"] = rugpull_details
        if not rugpull_safe:
            is_safe = False
        
        # 2. Vérification du honeypot
        honeypot_safe, honeypot_details = await self.honeypot_protection.check_token(token_data)
        details["checks"]["honeypot"] = honeypot_details
        if not honeypot_safe:
            is_safe = False
        
        # 3. Vérification du contrat
        contract_safe, contract_details = await self._check_contract_security(token_data)
        details["checks"]["contract"] = contract_details
        if not contract_safe:
            is_safe = False
        
        # Ajouter au cache
        self.security_checks_cache[cache_key] = {
            "timestamp": datetime.now(),
            "is_safe": is_safe,
            "details": details
        }
        
        # Si le token est dangereux, l'ajouter à la blacklist
        if not is_safe:
            self._add_to_blacklist(token_address, details)
        
        logger.info(f"Vérification de sécurité pour {token_address}: {'Sécurisé' if is_safe else 'Non sécurisé'}")
        return is_safe, details
    
    async def check_trade_limits(self, trade_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Vérifie si un trade respecte les limites de sécurité.
        
        Args:
            trade_data: Données du trade à vérifier
            
        Returns:
            Tuple (autorisé, raison) où autorisé est un booléen
            et raison est la raison du refus (si refusé)
        """
        # Vérifier les limites quotidiennes
        if self.trade_stats["daily_trades"] >= self.max_daily_trades:
            return False, "Limite quotidienne de trades atteinte"
        
        # Vérifier la perte maximale par trade
        if trade_data.get("potential_loss_percent", 0) > self.max_loss_per_trade * 100:
            return False, f"Perte potentielle trop élevée: {trade_data.get('potential_loss_percent')}% > {self.max_loss_per_trade * 100}%"
        
        # Vérifier la perte quotidienne maximale
        if self.trade_stats["daily_profit_loss"] < -self.max_daily_loss * 100:
            return False, f"Perte quotidienne maximale atteinte: {abs(self.trade_stats['daily_profit_loss'])}% > {self.max_daily_loss * 100}%"
        
        # Vérifier le slippage
        if trade_data.get("expected_slippage", 0) > self.max_slippage * 100:
            return False, f"Slippage trop élevé: {trade_data.get('expected_slippage')}% > {self.max_slippage * 100}%"
        
        return True, None
    
    def update_trade_stats(self, trade_result: Dict[str, Any]):
        """
        Met à jour les statistiques de trading.
        
        Args:
            trade_result: Résultat du trade
        """
        # Vérifier si on doit réinitialiser les stats quotidiennes
        last_reset = datetime.fromisoformat(self.trade_stats["last_reset"])
        if datetime.now() - last_reset > timedelta(days=1):
            self.trade_stats["daily_trades"] = 0
            self.trade_stats["daily_profit_loss"] = 0.0
            self.trade_stats["last_reset"] = datetime.now().isoformat()
        
        # Mettre à jour les compteurs
        self.trade_stats["daily_trades"] += 1
        self.trade_stats["total_trades"] += 1
        
        # Mettre à jour les profits/pertes
        profit_loss = trade_result.get("profit_loss_percent", 0)
        self.trade_stats["daily_profit_loss"] += profit_loss
        self.trade_stats["total_profit_loss"] += profit_loss
        
        logger.info(f"Statistiques de trading mises à jour: {self.trade_stats}")
    
    async def _check_contract_security(self, token_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Vérifie la sécurité du contrat d'un token.
        
        Args:
            token_data: Données du token à vérifier
            
        Returns:
            Tuple (sécurisé, détails)
        """
        # Implémentation simplifiée, à enrichir avec une analyse de contrat réelle
        return True, {"verified": True, "issues": []}
    
    def _load_blacklist(self) -> List[str]:
        """
        Charge la liste des tokens blacklistés.
        
        Returns:
            Liste d'adresses de tokens blacklistés
        """
        blacklist_path = os.path.join(os.path.dirname(__file__), "data", "blacklisted_tokens.json")
        try:
            if os.path.exists(blacklist_path):
                with open(blacklist_path, "r") as f:
                    return [addr.lower() for addr in json.load(f)]
            return []
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la blacklist: {str(e)}")
            return []
    
    def _add_to_blacklist(self, token_address: str, reason: Dict[str, Any]):
        """
        Ajoute un token à la blacklist.
        
        Args:
            token_address: Adresse du token
            reason: Raison de l'ajout à la blacklist
        """
        if token_address.lower() not in self.blacklisted_tokens:
            self.blacklisted_tokens.append(token_address.lower())
            self.trade_stats["blocked_tokens"].append({
                "address": token_address,
                "timestamp": datetime.now().isoformat(),
                "reason": reason
            })
            
            # Sauvegarder la blacklist
            try:
                blacklist_path = os.path.join(os.path.dirname(__file__), "data", "blacklisted_tokens.json")
                os.makedirs(os.path.dirname(blacklist_path), exist_ok=True)
                with open(blacklist_path, "w") as f:
                    json.dump(self.blacklisted_tokens, f)
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde de la blacklist: {str(e)}")
            
            logger.warning(f"Token {token_address} ajouté à la blacklist: {reason}")


class RugPullProtection:
    """Protection contre les rug pulls"""
    
    def __init__(
        self,
        min_liquidity: float = 10000.0,  # USD
        max_owner_tokens: float = 0.3,   # 30%
        min_holders: int = 50,
        max_tax: float = 0.05            # 5%
    ):
        """
        Initialise la protection contre les rug pulls.
        
        Args:
            min_liquidity: Liquidité minimale en USD
            max_owner_tokens: Pourcentage maximal de tokens détenus par le créateur
            min_holders: Nombre minimal de détenteurs
            max_tax: Taxe maximale sur les transactions
        """
        self.min_liquidity = min_liquidity
        self.max_owner_tokens = max_owner_tokens
        self.min_holders = min_holders
        self.max_tax = max_tax
        self.logger = logging.getLogger("gbpbot.security.rugpull")
    
    async def check_token(self, token_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Vérifie si un token présente des risques de rug pull.
        
        Args:
            token_data: Données du token à vérifier
            
        Returns:
            Tuple (sécurisé, détails)
        """
        token_address = token_data.get("address", "")
        liquidity_usd = token_data.get("liquidity_usd", 0)
        owner_percentage = token_data.get("owner_percentage", 0)
        tax = token_data.get("tax", 0)
        holders_count = token_data.get("holders_count", 0)
        locked_liquidity = token_data.get("locked_liquidity", False)
        
        # Analyser les risques
        is_safe = True
        risks = []
        
        # 1. Vérifier la liquidité
        if liquidity_usd < self.min_liquidity:
            is_safe = False
            risks.append(f"Liquidité insuffisante: {liquidity_usd}$ < {self.min_liquidity}$")
        
        # 2. Vérifier la concentration des tokens
        if owner_percentage > self.max_owner_tokens * 100:
            is_safe = False
            risks.append(f"Concentration élevée: {owner_percentage}% > {self.max_owner_tokens * 100}%")
        
        # 3. Vérifier les taxes
        if tax > self.max_tax * 100:
            is_safe = False
            risks.append(f"Taxe excessive: {tax}% > {self.max_tax * 100}%")
        
        # 4. Vérifier le nombre de détenteurs
        if holders_count < self.min_holders:
            is_safe = False
            risks.append(f"Trop peu de détenteurs: {holders_count} < {self.min_holders}")
        
        # 5. Vérifier si la liquidité est verrouillée
        if not locked_liquidity:
            is_safe = False
            risks.append("Liquidité non verrouillée")
        
        details = {
            "is_safe": is_safe,
            "risks": risks,
            "liquidity_usd": liquidity_usd,
            "owner_percentage": owner_percentage,
            "tax": tax,
            "holders_count": holders_count,
            "locked_liquidity": locked_liquidity
        }
        
        if not is_safe:
            self.logger.warning(f"Risque de rug pull détecté pour {token_address}: {risks}")
        
        return is_safe, details


class HoneypotProtection:
    """Protection contre les honeypots"""
    
    def __init__(self, simulate_sell: bool = True, min_sell_tx_count: int = 10):
        """
        Initialise la protection contre les honeypots.
        
        Args:
            simulate_sell: Simuler une vente avant d'acheter
            min_sell_tx_count: Nombre minimal de transactions de vente
                pour considérer le token comme sûr
        """
        self.simulate_sell = simulate_sell
        self.min_sell_tx_count = min_sell_tx_count
        self.logger = logging.getLogger("gbpbot.security.honeypot")
    
    async def check_token(self, token_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Vérifie si un token est un honeypot.
        
        Args:
            token_data: Données du token à vérifier
            
        Returns:
            Tuple (sécurisé, détails)
        """
        token_address = token_data.get("address", "")
        sell_tx_count = token_data.get("sell_tx_count", 0)
        can_sell_simulated = token_data.get("can_sell_simulated", False)
        
        # Analyser les risques
        is_safe = True
        risks = []
        
        # 1. Vérifier si la simulation de vente est possible
        if self.simulate_sell and not can_sell_simulated:
            is_safe = False
            risks.append("Impossible de simuler une vente")
        
        # 2. Vérifier le nombre de transactions de vente
        if sell_tx_count < self.min_sell_tx_count:
            is_safe = False
            risks.append(f"Trop peu de transactions de vente: {sell_tx_count} < {self.min_sell_tx_count}")
        
        details = {
            "is_safe": is_safe,
            "risks": risks,
            "sell_tx_count": sell_tx_count,
            "can_sell_simulated": can_sell_simulated
        }
        
        if not is_safe:
            self.logger.warning(f"Honeypot potentiel détecté pour {token_address}: {risks}")
        
        return is_safe, details 