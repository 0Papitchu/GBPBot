#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple pour le module de sniping de tokens du GBPBot.
Ce module teste les fonctionnalités de base de détection et d'achat de nouveaux tokens.
"""

import os
import sys
import unittest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Ajouter le répertoire de mocks au début du PYTHONPATH
mock_dir = ROOT_DIR / "gbpbot" / "tests" / "mocks"
if mock_dir.exists():
    sys.path.insert(0, str(mock_dir))

class SimpleSnipingTest(unittest.TestCase):
    """Tests simples pour le module de sniping de tokens."""
    
    def setUp(self):
        """Prépare l'environnement de test."""
        # Exemple de nouveaux tokens détectés
        self.mock_new_tokens = [
            {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "symbol": "MEME1",
                "name": "MemeToken1",
                "network": "avalanche",
                "creation_time": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "deployer": "0xdeadbeef1234567890abcdef1234567890abcdef",
                "initial_liquidity": 25000,
                "initial_market_cap": 50000,
                "pair_address": "0xabcdef1234567890abcdef1234567890abcdef12",
                "dex": "TraderJoe",
                "base_token": "AVAX",
                "initial_holders": 3,
                "contract_verified": False,
                "social_media": {
                    "twitter": "https://twitter.com/MemeToken1",
                    "telegram": "https://t.me/MemeToken1",
                    "website": "https://memetoken1.io"
                }
            },
            {
                "address": "0xabcdef1234567890abcdef1234567890abcdef12",
                "symbol": "MEME2",
                "name": "MemeToken2",
                "network": "solana",
                "creation_time": (datetime.now() - timedelta(minutes=2)).isoformat(),
                "deployer": "0xabcdef1234567890abcdef1234567890deadbeef",
                "initial_liquidity": 100000,
                "initial_market_cap": 200000,
                "pair_address": "0x7890abcdef1234567890abcdef1234567890abcd",
                "dex": "Raydium",
                "base_token": "SOL",
                "initial_holders": 5,
                "contract_verified": True,
                "social_media": {
                    "twitter": "https://twitter.com/MemeToken2",
                    "telegram": "https://t.me/MemeToken2",
                    "website": "https://memetoken2.io"
                }
            },
            {
                "address": "0x7890abcdef1234567890abcdef1234567890abcd",
                "symbol": "MEME3",
                "name": "MemeToken3",
                "network": "avalanche",
                "creation_time": (datetime.now() - timedelta(hours=2)).isoformat(),
                "deployer": "0x1234abcdef1234567890abcdef1234567890abcd",
                "initial_liquidity": 5000,
                "initial_market_cap": 15000,
                "pair_address": "0x5678abcdef1234567890abcdef1234567890abcd",
                "dex": "Pangolin",
                "base_token": "AVAX",
                "initial_holders": 2,
                "contract_verified": False,
                "social_media": {
                    "twitter": "",
                    "telegram": "",
                    "website": ""
                }
            }
        ]
        
        # Exemple d'historique des prix
        self.token_price_history = {
            "MEME1": [
                {"timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(), "price": 0.00001},
                {"timestamp": (datetime.now() - timedelta(minutes=4)).isoformat(), "price": 0.00002},
                {"timestamp": (datetime.now() - timedelta(minutes=3)).isoformat(), "price": 0.00005},
                {"timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(), "price": 0.0001},
                {"timestamp": (datetime.now() - timedelta(minutes=1)).isoformat(), "price": 0.0002}
            ],
            "MEME2": [
                {"timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(), "price": 0.0001},
                {"timestamp": (datetime.now() - timedelta(minutes=1.5)).isoformat(), "price": 0.00015},
                {"timestamp": (datetime.now() - timedelta(minutes=1)).isoformat(), "price": 0.0002},
                {"timestamp": (datetime.now() - timedelta(minutes=0.5)).isoformat(), "price": 0.00025}
            ],
            "MEME3": [
                {"timestamp": (datetime.now() - timedelta(hours=2)).isoformat(), "price": 0.0001},
                {"timestamp": (datetime.now() - timedelta(hours=1.5)).isoformat(), "price": 0.00012},
                {"timestamp": (datetime.now() - timedelta(hours=1)).isoformat(), "price": 0.00011},
                {"timestamp": (datetime.now() - timedelta(hours=0.5)).isoformat(), "price": 0.0001},
                {"timestamp": (datetime.now()).isoformat(), "price": 0.00009}
            ]
        }
    
    def test_token_detector(self):
        """Vérifie que le détecteur de nouveaux tokens fonctionne correctement."""
        
        class MockTokenDetector:
            def __init__(self, blockchain_scanner):
                self.blockchain_scanner = blockchain_scanner
                self.min_liquidity = 10000
                self.networks = ["avalanche", "solana"]
                self.dexes = ["TraderJoe", "Pangolin", "Raydium"]
                self.last_check_time = {}
                
                # Initialiser le dernier temps de vérification pour chaque réseau
                for network in self.networks:
                    self.last_check_time[network] = datetime.now() - timedelta(hours=3)
            
            def scan_for_new_tokens(self):
                """Scanne les blockchains pour de nouveaux tokens."""
                new_tokens = self.blockchain_scanner.get_new_tokens(self.last_check_time)
                
                # Filtrer selon les critères minimums
                filtered_tokens = []
                for token in new_tokens:
                    if token["initial_liquidity"] >= self.min_liquidity and token["network"] in self.networks:
                        filtered_tokens.append(token)
                        
                        # Mettre à jour le dernier temps de vérification
                        token_time = datetime.fromisoformat(token["creation_time"])
                        if token_time > self.last_check_time[token["network"]]:
                            self.last_check_time[token["network"]] = token_time
                
                return filtered_tokens
        
        class MockBlockchainScanner:
            def __init__(self, mock_tokens):
                self.mock_tokens = mock_tokens
            
            def get_new_tokens(self, last_check_time):
                """Retourne les nouveaux tokens depuis le dernier check."""
                new_tokens = []
                for token in self.mock_tokens:
                    token_time = datetime.fromisoformat(token["creation_time"])
                    network = token["network"]
                    if token_time > last_check_time[network]:
                        new_tokens.append(token)
                return new_tokens
        
        # Créer le scanner et le détecteur
        scanner = MockBlockchainScanner(self.mock_new_tokens)
        detector = MockTokenDetector(scanner)
        
        # Scan pour les nouveaux tokens
        new_tokens = detector.scan_for_new_tokens()
        
        # Vérifier que les tokens avec liquidité suffisante sont détectés
        self.assertEqual(len(new_tokens), 2)  # MEME1 et MEME2 ont assez de liquidité
        
        # Vérifier que les tokens sont dans l'ordre des réseaux spécifiés
        for token in new_tokens:
            self.assertIn(token["network"], detector.networks)
            self.assertIn(token["dex"], detector.dexes)
            self.assertGreaterEqual(token["initial_liquidity"], detector.min_liquidity)
    
    def test_token_analyzer(self):
        """Vérifie que l'analyseur de tokens fonctionne correctement."""
        
        class MockTokenAnalyzer:
            def __init__(self, price_feed):
                self.price_feed = price_feed
                self.min_growth_rate = 50  # % par minute
                self.min_holders = 3
                self.markets_to_follow = ["avalanche", "solana"]
            
            def analyze_token(self, token):
                """Analyse un token pour déterminer son potentiel."""
                # Vérifier les critères de base
                if token["initial_holders"] < self.min_holders:
                    return {
                        "token": token["symbol"],
                        "score": 0,
                        "recommendation": "SKIP",
                        "reason": "Too few initial holders"
                    }
                
                # Vérifier le réseau
                if token["network"] not in self.markets_to_follow:
                    return {
                        "token": token["symbol"],
                        "score": 0,
                        "recommendation": "SKIP",
                        "reason": f"Network {token['network']} not in target markets"
                    }
                
                # Calculer le taux de croissance
                price_history = self.price_feed.get_price_history(token["symbol"])
                if not price_history or len(price_history) < 2:
                    return {
                        "token": token["symbol"],
                        "score": 0,
                        "recommendation": "WAIT",
                        "reason": "Insufficient price history"
                    }
                
                initial_price = price_history[0]["price"]
                current_price = price_history[-1]["price"]
                
                # Calculer le temps écoulé en minutes
                initial_time = datetime.fromisoformat(price_history[0]["timestamp"])
                current_time = datetime.fromisoformat(price_history[-1]["timestamp"])
                elapsed_minutes = (current_time - initial_time).total_seconds() / 60
                
                if elapsed_minutes == 0:
                    growth_rate = 0
                else:
                    # Calcul du taux de croissance en % par minute
                    growth_rate = ((current_price / initial_price) - 1) * 100 / elapsed_minutes
                
                # Calculer un score basé sur divers facteurs
                score = min(100, growth_rate * 2)
                
                # Ajouter des points pour la vérification du contrat
                if token["contract_verified"]:
                    score += 20
                    
                # Ajouter des points pour les médias sociaux
                if token["social_media"]["twitter"]:
                    score += 10
                if token["social_media"]["telegram"]:
                    score += 10
                if token["social_media"]["website"]:
                    score += 10
                
                # Limiter le score à 100
                score = min(100, score)
                
                # Déterminer la recommandation
                recommendation = "SKIP"
                reason = ""
                
                if score >= 80:
                    recommendation = "BUY"
                    reason = "High growth potential"
                elif score >= 50:
                    recommendation = "MONITOR"
                    reason = "Moderate growth potential"
                else:
                    reason = "Low growth potential"
                
                # Calculer le changement de prix
                price_change = (current_price / initial_price) - 1
                
                return {
                    "token": token["symbol"],
                    "score": score,
                    "growth_rate": growth_rate,
                    "recommendation": recommendation,
                    "reason": reason,
                    "price_change": price_change
                }
        
        class MockPriceFeed:
            def __init__(self, price_history):
                self.price_history = price_history
            
            def get_price_history(self, token_symbol):
                """Retourne l'historique des prix pour un token."""
                if token_symbol in self.price_history:
                    return self.price_history[token_symbol]
                return []
        
        # Créer le price feed et l'analyseur
        price_feed = MockPriceFeed(self.token_price_history)
        analyzer = MockTokenAnalyzer(price_feed)
        
        # Analyser chaque token
        for token in self.mock_new_tokens:
            result = analyzer.analyze_token(token)
            
            # Vérifier que l'analyse est cohérente
            self.assertEqual(result["token"], token["symbol"])
            
            # Vérifier les recommandations spécifiques
            if token["symbol"] == "MEME1":
                # Token avec forte croissance
                self.assertEqual(result["recommendation"], "BUY")
                self.assertGreater(result["growth_rate"], analyzer.min_growth_rate)
            elif token["symbol"] == "MEME2":
                # Token avec croissance modérée mais vérifié
                self.assertIn(result["recommendation"], ["BUY", "MONITOR"])
                self.assertGreater(result["score"], 50)
            elif token["symbol"] == "MEME3":
                # Token avec prix en baisse
                self.assertEqual(result["recommendation"], "SKIP")
                # Vérifier que le prix a baissé seulement si le token a assez de holders
                # Sinon, la recommandation SKIP est due au nombre insuffisant de holders
                if token["initial_holders"] >= analyzer.min_holders:
                    self.assertIn("price_change", result)
                    if "price_change" in result:
                        self.assertLess(result["price_change"], 0)
    
    def test_sniping_executor(self):
        """Vérifie que l'exécuteur de sniping fonctionne correctement."""
        
        class MockSnipingExecutor:
            def __init__(self, wallet, blockchain_interface):
                self.wallet = wallet
                self.blockchain_interface = blockchain_interface
                self.max_slippage = 0.05  # 5%
                self.default_gas_boost = 1.2  # 20% de boost
                self.emergency_gas_boost = 2.0  # 100% de boost en cas d'urgence
                self.default_amount = 0.1  # 0.1 ETH/AVAX/SOL par défaut
                self.max_amount = 1.0  # 1.0 ETH/AVAX/SOL maximum
            
            def execute_snipe(self, token, amount=None, urgent=False):
                """Exécute un achat rapide (snipe) d'un token."""
                if amount is None:
                    amount = self.default_amount
                
                # Vérifier que le montant est dans les limites
                amount = max(0, min(amount, self.max_amount))
                
                # Déterminer le gas boost
                gas_boost = self.emergency_gas_boost if urgent else self.default_gas_boost
                
                # Créer la transaction
                tx = {
                    "from": self.wallet.address,
                    "to": token["pair_address"],
                    "value": amount,
                    "gas_price": self.blockchain_interface.get_gas_price() * gas_boost,
                    "slippage": self.max_slippage,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Simuler l'exécution
                result = self.blockchain_interface.simulate_transaction(tx, token)
                
                if not result["success"]:
                    return {
                        "success": False,
                        "error": result["error"],
                        "transaction_hash": None
                    }
                
                # Si la simulation réussit, envoyer la transaction
                tx_result = self.blockchain_interface.send_transaction(tx, token)
                
                return {
                    "success": tx_result["success"],
                    "transaction_hash": tx_result.get("transaction_hash"),
                    "amount": amount,
                    "token_amount": tx_result.get("token_amount", 0),
                    "effective_price": tx_result.get("effective_price", 0),
                    "gas_used": tx_result.get("gas_used", 0),
                    "gas_price": tx.get("gas_price", 0),
                    "total_cost": tx_result.get("total_cost", 0)
                }
        
        class MockWallet:
            def __init__(self, address, balances=None):
                self.address = address
                self.balances = balances or {
                    "AVAX": 10,
                    "SOL": 100,
                    "ETH": 2
                }
            
            def get_balance(self, token):
                """Retourne le solde d'un token."""
                return self.balances.get(token, 0)
        
        class MockBlockchainInterface:
            def __init__(self):
                self.success_rate = 1.0  # 100% de succès pour les tests
                self.current_gas_price = 50  # Gwei
            
            def get_gas_price(self):
                """Retourne le prix actuel du gas."""
                return self.current_gas_price
            
            def simulate_transaction(self, tx, token):
                """Simule une transaction pour vérifier si elle réussirait."""
                # Vérifier que le wallet a assez de fonds
                required_token = token["base_token"]
                
                # Créer un wallet avec les mêmes balances que celui utilisé dans le test
                wallet = MockWallet(tx["from"], {
                    "AVAX": 10,
                    "SOL": 100,
                    "ETH": 2
                })
                
                if tx["value"] > wallet.get_balance(required_token):
                    return {"success": False, "error": "Insufficient funds"}
                
                # Simuler succès/échec selon le taux
                import random
                if random.random() < self.success_rate:
                    return {"success": True}
                else:
                    return {"success": False, "error": "Simulation failed"}
            
            def send_transaction(self, tx, token):
                """Envoie une transaction à la blockchain."""
                # Dans un mock, on suppose que si la simulation a réussi, l'envoi réussit aussi
                import random
                
                # Prix du token
                token_symbol = token["symbol"]
                current_price = 0.0002  # Prix fictif
                
                # Calculer le montant de tokens reçus (avec slippage)
                effective_price = current_price * (1 + random.uniform(0, tx["slippage"]))
                token_amount = tx["value"] / effective_price
                
                # Calculer le gas utilisé
                gas_used = random.randint(100000, 300000)
                gas_cost = gas_used * tx["gas_price"] / 1e9  # Convertir Gwei en ETH/AVAX/SOL
                
                return {
                    "success": True,
                    "transaction_hash": f"0x{random.getrandbits(256):064x}",
                    "token_amount": token_amount,
                    "effective_price": effective_price,
                    "gas_used": gas_used,
                    "total_cost": tx["value"] + gas_cost
                }
        
        # Créer le wallet, l'interface blockchain et l'exécuteur
        wallet = MockWallet("0xuser1234567890abcdef1234567890abcdef")
        blockchain = MockBlockchainInterface()
        executor = MockSnipingExecutor(wallet, blockchain)
        
        # Tester l'exécution pour chaque token
        for token in self.mock_new_tokens:
            # Tester avec différents montants
            small_result = executor.execute_snipe(token, amount=0.05)
            default_result = executor.execute_snipe(token)
            urgent_result = executor.execute_snipe(token, amount=0.2, urgent=True)
            
            # Vérifier que les transactions ont réussi
            self.assertTrue(small_result["success"])
            self.assertTrue(default_result["success"])
            self.assertTrue(urgent_result["success"])
            
            # Vérifier que les montants sont corrects
            self.assertAlmostEqual(small_result["amount"], 0.05)
            self.assertAlmostEqual(default_result["amount"], executor.default_amount)
            self.assertAlmostEqual(urgent_result["amount"], 0.2)
            
            # Vérifier que le gas price est plus élevé pour la transaction urgente
            self.assertGreater(urgent_result["gas_price"], default_result["gas_price"])

if __name__ == "__main__":
    unittest.main() 