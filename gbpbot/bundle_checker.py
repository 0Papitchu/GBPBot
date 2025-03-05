#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de détection des bundles de transactions.
Ce module permet d'identifier les transactions groupées (bundles) qui peuvent indiquer
une manipulation de marché ou une opportunité de trading.
"""

import os
import sys
import time
import json
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional, Tuple
from web3 import Web3
from loguru import logger
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("bundle_checker.log", rotation="10 MB", level="DEBUG")

class BundleChecker:
    """Classe pour la détection des bundles de transactions."""
    
    def __init__(self, 
                 web3_provider: str = None,
                 bundle_threshold: int = 3,
                 time_window: int = 60,  # en secondes
                 target_tokens: List[str] = None,
                 target_dexes: List[str] = None):
        """
        Initialiser le module de détection des bundles.
        
        Args:
            web3_provider: URL du fournisseur Web3 (ex: Infura, Alchemy)
            bundle_threshold: Nombre minimum de transactions pour considérer un bundle
            time_window: Fenêtre de temps pour regrouper les transactions (en secondes)
            target_tokens: Liste des tokens à surveiller (adresses)
            target_dexes: Liste des DEX à surveiller (adresses des routeurs)
        """
        # Configuration Web3
        self.web3_provider = web3_provider or os.getenv("WEB3_PROVIDER_URL")
        
        if not self.web3_provider:
            raise ValueError("Web3 provider URL is required")
        
        self.web3 = Web3(Web3.HTTPProvider(self.web3_provider))
        
        # Vérifier la connexion
        if not self.web3.is_connected():
            raise ConnectionError("Failed to connect to Web3 provider")
        
        # Configuration de la détection
        self.bundle_threshold = bundle_threshold
        self.time_window = time_window
        
        # Tokens à surveiller
        self.target_tokens = target_tokens or []
        self.target_tokens = [addr.lower() for addr in self.target_tokens]
        
        # DEX à surveiller (adresses des routeurs)
        self.target_dexes = target_dexes or [
            # Uniswap V2 Router
            "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            # PancakeSwap Router
            "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            # SushiSwap Router
            "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
        ]
        self.target_dexes = [addr.lower() for addr in self.target_dexes]
        
        # Données de suivi
        self.recent_transactions = []
        self.detected_bundles = []
        self.token_transactions = defaultdict(list)
        self.wallet_transactions = defaultdict(list)
        
        # Signatures des fonctions de swap
        self.swap_signatures = [
            # Uniswap/PancakeSwap swapExactETHForTokens
            "0x7ff36ab5",
            # Uniswap/PancakeSwap swapExactTokensForETH
            "0x18cbafe5",
            # Uniswap/PancakeSwap swapExactTokensForTokens
            "0x38ed1739",
            # Uniswap/PancakeSwap swapETHForExactTokens
            "0xfb3bdb41",
            # Uniswap/PancakeSwap swapTokensForExactETH
            "0x4a25d94a",
            # Uniswap/PancakeSwap swapTokensForExactTokens
            "0x8803dbee"
        ]
        
        logger.info("Bundle checker module initialized")
    
    def analyze_block(self, block_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Analyser un bloc pour détecter les bundles de transactions.
        
        Args:
            block_number: Numéro du bloc à analyser (None pour le dernier bloc)
            
        Returns:
            List[Dict[str, Any]]: Liste des bundles détectés
        """
        try:
            # Obtenir le bloc
            if block_number is None:
                block_number = self.web3.eth.block_number
            
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            
            logger.info(f"Analyzing block {block_number} with {len(block.transactions)} transactions")
            
            # Réinitialiser les données temporaires
            current_transactions = []
            token_txs = defaultdict(list)
            wallet_txs = defaultdict(list)
            
            # Analyser chaque transaction
            for tx in block.transactions:
                # Vérifier si la transaction est un swap sur un DEX ciblé
                if self._is_swap_transaction(tx):
                    # Extraire les informations de la transaction
                    tx_info = self._extract_transaction_info(tx)
                    
                    if tx_info:
                        current_transactions.append(tx_info)
                        
                        # Regrouper par token
                        if "token_address" in tx_info:
                            token_txs[tx_info["token_address"]].append(tx_info)
                        
                        # Regrouper par wallet
                        wallet_txs[tx_info["from_address"]].append(tx_info)
            
            # Mettre à jour les données globales
            self.recent_transactions.extend(current_transactions)
            
            # Limiter la taille des données historiques
            max_history = 1000
            if len(self.recent_transactions) > max_history:
                self.recent_transactions = self.recent_transactions[-max_history:]
            
            # Mettre à jour les transactions par token
            for token, txs in token_txs.items():
                self.token_transactions[token].extend(txs)
                
                # Limiter la taille des données historiques par token
                if len(self.token_transactions[token]) > max_history:
                    self.token_transactions[token] = self.token_transactions[token][-max_history:]
            
            # Mettre à jour les transactions par wallet
            for wallet, txs in wallet_txs.items():
                self.wallet_transactions[wallet].extend(txs)
                
                # Limiter la taille des données historiques par wallet
                if len(self.wallet_transactions[wallet]) > max_history:
                    self.wallet_transactions[wallet] = self.wallet_transactions[wallet][-max_history:]
            
            # Détecter les bundles
            bundles = self._detect_bundles(token_txs)
            
            # Ajouter les bundles détectés à l'historique
            self.detected_bundles.extend(bundles)
            
            # Limiter la taille des données historiques
            if len(self.detected_bundles) > max_history:
                self.detected_bundles = self.detected_bundles[-max_history:]
            
            return bundles
            
        except Exception as e:
            logger.error(f"Error analyzing block {block_number}: {e}")
            return []
    
    def _is_swap_transaction(self, tx) -> bool:
        """
        Vérifier si une transaction est un swap sur un DEX ciblé.
        
        Args:
            tx: Transaction à analyser
            
        Returns:
            bool: True si c'est un swap, False sinon
        """
        try:
            # Vérifier si la transaction a des données et est destinée à un DEX ciblé
            if not tx.to or not tx.input or len(tx.input) < 10:
                return False
            
            # Vérifier si la transaction est destinée à un DEX ciblé
            if tx.to.lower() not in self.target_dexes:
                return False
            
            # Vérifier si la fonction appelée est un swap
            function_signature = tx.input[:10]
            return function_signature in self.swap_signatures
            
        except Exception as e:
            logger.error(f"Error checking if transaction is swap: {e}")
            return False
    
    def _extract_transaction_info(self, tx) -> Optional[Dict[str, Any]]:
        """
        Extraire les informations d'une transaction de swap.
        
        Args:
            tx: Transaction à analyser
            
        Returns:
            Optional[Dict[str, Any]]: Informations de la transaction ou None si erreur
        """
        try:
            # Extraire les informations de base
            tx_info = {
                "tx_hash": tx.hash.hex(),
                "from_address": tx.get("from", "").lower(),
                "to_address": tx.to.lower() if tx.to else "",
                "value": self.web3.from_wei(tx.value, "ether"),
                "gas_price": self.web3.from_wei(tx.gasPrice, "gwei"),
                "block_number": tx.blockNumber,
                "timestamp": time.time(),
                "function": tx.input[:10]
            }
            
            # Extraire l'adresse du token en fonction de la fonction appelée
            token_address = self._extract_token_address(tx)
            if token_address:
                tx_info["token_address"] = token_address.lower()
            
            return tx_info
            
        except Exception as e:
            logger.error(f"Error extracting transaction info: {e}")
            return None
    
    def _extract_token_address(self, tx) -> Optional[str]:
        """
        Extraire l'adresse du token d'une transaction de swap.
        
        Args:
            tx: Transaction à analyser
            
        Returns:
            Optional[str]: Adresse du token ou None si non trouvée
        """
        try:
            # Pour swapExactETHForTokens, le token est le dernier dans le chemin
            if tx.input.startswith("0x7ff36ab5"):
                # Décoder les paramètres (simplifié)
                # Le chemin est généralement le deuxième paramètre
                # Format: function_selector + amountOutMin (32 bytes) + path_offset (32 bytes) + ...
                
                # Cette extraction est simplifiée et peut nécessiter une analyse plus approfondie
                # des données de la transaction en fonction du DEX spécifique
                
                # Pour une implémentation complète, il faudrait utiliser l'ABI du routeur
                # pour décoder correctement les paramètres
                
                # Exemple simplifié pour Uniswap V2 / PancakeSwap
                # Nous supposons que le chemin est [WETH, token]
                token_address = "0x" + tx.input[154:194]  # Position approximative
                return self.web3.to_checksum_address(token_address)
            
            # Pour d'autres fonctions de swap, l'extraction serait différente
            # Cette implémentation est simplifiée
            
        except Exception as e:
            logger.error(f"Error extracting token address: {e}")
        
        return None
    
    def _detect_bundles(self, token_txs: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Détecter les bundles de transactions.
        
        Args:
            token_txs: Dictionnaire des transactions par token
            
        Returns:
            List[Dict[str, Any]]: Liste des bundles détectés
        """
        bundles = []
        
        # Parcourir les transactions par token
        for token_address, txs in token_txs.items():
            # Ignorer les tokens avec trop peu de transactions
            if len(txs) < self.bundle_threshold:
                continue
            
            # Vérifier si les transactions sont dans la même fenêtre de temps
            # et proviennent de wallets différents
            wallets = set(tx["from_address"] for tx in txs)
            
            # Si plusieurs wallets différents ont interagi avec le même token
            if len(wallets) >= self.bundle_threshold:
                # Créer un bundle
                bundle = {
                    "token_address": token_address,
                    "transaction_count": len(txs),
                    "unique_wallets": len(wallets),
                    "transactions": txs,
                    "detected_at": time.time(),
                    "manipulation_score": self._calculate_manipulation_score(txs, wallets)
                }
                
                bundles.append(bundle)
                
                logger.info(f"Bundle detected for token {token_address}: {len(txs)} transactions from {len(wallets)} wallets")
        
        return bundles
    
    def _calculate_manipulation_score(self, txs: List[Dict[str, Any]], wallets: Set[str]) -> float:
        """
        Calculer un score de manipulation pour un bundle.
        
        Args:
            txs: Liste des transactions
            wallets: Ensemble des wallets impliqués
            
        Returns:
            float: Score de manipulation (0-100)
        """
        # Facteurs de score
        wallet_diversity = min(1.0, len(wallets) / 10)  # Plus de wallets = score plus élevé
        tx_volume = min(1.0, len(txs) / 20)  # Plus de transactions = score plus élevé
        
        # Vérifier si les transactions sont rapprochées dans le temps
        timestamps = [tx.get("timestamp", 0) for tx in txs]
        if timestamps:
            time_range = max(timestamps) - min(timestamps)
            time_factor = max(0, 1.0 - (time_range / self.time_window))
        else:
            time_factor = 0
        
        # Vérifier si les montants sont similaires (indice de coordination)
        values = [tx.get("value", 0) for tx in txs]
        if values and max(values) > 0:
            value_std = self._calculate_std(values)
            value_mean = sum(values) / len(values)
            value_cv = value_std / value_mean if value_mean > 0 else 1
            value_similarity = max(0, 1.0 - value_cv)
        else:
            value_similarity = 0
        
        # Calculer le score final (0-100)
        score = (wallet_diversity * 0.3 + tx_volume * 0.2 + time_factor * 0.3 + value_similarity * 0.2) * 100
        
        return round(score, 2)
    
    def _calculate_std(self, values: List[float]) -> float:
        """
        Calculer l'écart-type d'une liste de valeurs.
        
        Args:
            values: Liste des valeurs
            
        Returns:
            float: Écart-type
        """
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def get_recent_bundles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtenir les bundles récemment détectés.
        
        Args:
            limit: Nombre maximum de bundles à retourner
            
        Returns:
            List[Dict[str, Any]]: Liste des bundles récents
        """
        # Trier par score de manipulation (décroissant)
        sorted_bundles = sorted(
            self.detected_bundles,
            key=lambda x: x.get("manipulation_score", 0),
            reverse=True
        )
        
        return sorted_bundles[:limit]
    
    def get_token_bundles(self, token_address: str) -> List[Dict[str, Any]]:
        """
        Obtenir les bundles pour un token spécifique.
        
        Args:
            token_address: Adresse du token
            
        Returns:
            List[Dict[str, Any]]: Liste des bundles pour ce token
        """
        token_address = token_address.lower()
        
        return [
            bundle for bundle in self.detected_bundles
            if bundle.get("token_address") == token_address
        ]
    
    def is_token_manipulated(self, token_address: str, threshold: float = 70.0) -> Tuple[bool, float]:
        """
        Vérifier si un token est potentiellement manipulé.
        
        Args:
            token_address: Adresse du token
            threshold: Seuil de score pour considérer une manipulation
            
        Returns:
            Tuple[bool, float]: (est_manipulé, score_de_manipulation)
        """
        token_address = token_address.lower()
        
        # Obtenir les bundles pour ce token
        bundles = self.get_token_bundles(token_address)
        
        if not bundles:
            return False, 0.0
        
        # Utiliser le score le plus élevé
        max_score = max(bundle.get("manipulation_score", 0) for bundle in bundles)
        
        return max_score >= threshold, max_score
    
    def get_manipulation_report(self) -> Dict[str, Any]:
        """
        Générer un rapport sur les manipulations détectées.
        
        Returns:
            Dict[str, Any]: Rapport de manipulation
        """
        # Compter les bundles par token
        token_counts = defaultdict(int)
        token_scores = defaultdict(list)
        
        for bundle in self.detected_bundles:
            token = bundle.get("token_address")
            if token:
                token_counts[token] += 1
                token_scores[token].append(bundle.get("manipulation_score", 0))
        
        # Calculer les scores moyens
        token_avg_scores = {}
        for token, scores in token_scores.items():
            if scores:
                token_avg_scores[token] = sum(scores) / len(scores)
            else:
                token_avg_scores[token] = 0
        
        # Trier les tokens par score moyen
        sorted_tokens = sorted(
            token_avg_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Générer le rapport
        report = {
            "total_bundles": len(self.detected_bundles),
            "unique_tokens": len(token_counts),
            "top_manipulated_tokens": [
                {
                    "token_address": token,
                    "bundle_count": token_counts[token],
                    "avg_manipulation_score": score
                }
                for token, score in sorted_tokens[:10]  # Top 10
            ],
            "generated_at": time.time()
        }
        
        return report
    
    def add_target_token(self, token_address: str):
        """
        Ajouter un token à la liste des tokens ciblés.
        
        Args:
            token_address: Adresse du token à ajouter
        """
        token_address = token_address.lower()
        if token_address not in self.target_tokens:
            self.target_tokens.append(token_address)
            logger.info(f"Token added to target list: {token_address}")
    
    def remove_target_token(self, token_address: str):
        """
        Retirer un token de la liste des tokens ciblés.
        
        Args:
            token_address: Adresse du token à retirer
        """
        token_address = token_address.lower()
        if token_address in self.target_tokens:
            self.target_tokens.remove(token_address)
            logger.info(f"Token removed from target list: {token_address}")
    
    def clear_history(self):
        """Effacer l'historique des transactions et des bundles."""
        self.recent_transactions = []
        self.detected_bundles = []
        self.token_transactions = defaultdict(list)
        self.wallet_transactions = defaultdict(list)
        logger.info("Transaction and bundle history cleared")

# Exemple d'utilisation
def main():
    """Fonction principale pour tester le module."""
    # Créer une instance du module de détection
    checker = BundleChecker()
    
    # Analyser le dernier bloc
    bundles = checker.analyze_block()
    
    # Afficher les bundles détectés
    for bundle in bundles:
        print(f"Bundle detected for token {bundle['token_address']}:")
        print(f"  - Transactions: {bundle['transaction_count']}")
        print(f"  - Unique wallets: {bundle['unique_wallets']}")
        print(f"  - Manipulation score: {bundle['manipulation_score']}")
        print()
    
    # Générer un rapport
    report = checker.get_manipulation_report()
    print(f"Total bundles detected: {report['total_bundles']}")
    print(f"Unique tokens: {report['unique_tokens']}")
    print("Top manipulated tokens:")
    for token in report['top_manipulated_tokens']:
        print(f"  - {token['token_address']}: Score {token['avg_manipulation_score']}")

if __name__ == "__main__":
    main() 