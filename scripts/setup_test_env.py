#!/usr/bin/env python3
"""
Script de configuration de l'environnement de test pour GBPBot.
Configure l'environnement de test sur testnet ou mainnet avec les paramètres appropriés.
"""

import argparse
import logging
import sys
import os
import json
import yaml
import shutil
from pathlib import Path
from web3 import Web3
import secrets

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/setup_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("setup_test_env")

# Configurations par défaut pour les différents environnements
DEFAULT_CONFIGS = {
    "testnet": {
        "network": "goerli",
        "rpc": {
            "endpoints": [
                {"url": "https://goerli.infura.io/v3/YOUR_API_KEY", "weight": 10},
                {"url": "https://eth-goerli.g.alchemy.com/v2/YOUR_API_KEY", "weight": 10}
            ],
            "max_retries": 3,
            "timeout": 10,
            "cache_ttl": 30
        },
        "gas": {
            "max_base_fee_gwei": "50",
            "max_priority_fee_gwei": "5",
            "min_priority_fee_gwei": "1",
            "base_fee_multiplier": "1.1",
            "priority_fee_multiplier": "1.05",
            "max_total_fee_gwei": "100",
            "update_interval": 15,
            "history_size": 20
        },
        "trading": {
            "max_slippage": 0.02,
            "min_profit": 0.01,
            "max_gas_price_gwei": "50",
            "confirmation_timeout": 60,
            "max_pending_transactions": 3,
            "emergency_shutdown_threshold": 0.1
        },
        "security": {
            "max_price_change": 0.05,
            "min_liquidity": 100,
            "max_gas_price_gwei": 100,
            "min_confirmations": 1,
            "max_confirmation_attempts": 5
        },
        "monitoring": {
            "update_interval": 5,
            "alert_thresholds": {
                "low_balance": 0.1,
                "high_gas": 50,
                "low_profit": 0.005,
                "price_deviation": 0.1,
                "error_rate": 0.3
            }
        }
    },
    "mainnet": {
        "network": "mainnet",
        "rpc": {
            "endpoints": [
                {"url": "https://mainnet.infura.io/v3/YOUR_API_KEY", "weight": 10},
                {"url": "https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY", "weight": 10}
            ],
            "max_retries": 5,
            "timeout": 5,
            "cache_ttl": 15
        },
        "gas": {
            "max_base_fee_gwei": "500",
            "max_priority_fee_gwei": "50",
            "min_priority_fee_gwei": "1",
            "base_fee_multiplier": "1.125",
            "priority_fee_multiplier": "1.1",
            "max_total_fee_gwei": "1000",
            "update_interval": 15,
            "history_size": 20
        },
        "trading": {
            "max_slippage": 0.01,
            "min_profit": 0.005,
            "max_gas_price_gwei": "300",
            "confirmation_timeout": 60,
            "max_pending_transactions": 3,
            "emergency_shutdown_threshold": 0.05
        },
        "security": {
            "max_price_change": 0.02,
            "min_liquidity": 1000,
            "max_gas_price_gwei": 500,
            "min_confirmations": 2,
            "max_confirmation_attempts": 5
        },
        "monitoring": {
            "update_interval": 5,
            "alert_thresholds": {
                "low_balance": 0.05,
                "high_gas": 300,
                "low_profit": 0.001,
                "price_deviation": 0.05,
                "error_rate": 0.2
            }
        }
    }
}

def setup_test_env(args):
    """
    Configure l'environnement de test.
    
    Args:
        args: Arguments de la ligne de commande
    """
    try:
        logger.info(f"Configuration de l'environnement de test: {args.network}")
        
        # Créer les répertoires nécessaires
        dirs = ["config", "logs", "data", "data/incidents", "data/transfers", "reports"]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
        # Sélectionner la configuration de base
        if args.network not in DEFAULT_CONFIGS:
            logger.error(f"Réseau non supporté: {args.network}")
            return 1
            
        config = DEFAULT_CONFIGS[args.network].copy()
        
        # Générer un wallet de test si nécessaire
        if args.generate_wallet:
            wallet = generate_test_wallet()
            config["wallet"] = wallet
            logger.info(f"Wallet de test généré: {wallet['address']}")
            
            # Sauvegarder les informations du wallet séparément (pour sécurité)
            with open("config/wallet_info.json", "w") as f:
                json.dump(wallet, f, indent=2)
                
        # Configurer le capital de test
        if args.capital:
            config["trading"]["test_capital"] = float(args.capital)
            config["trading"]["max_trade_amount"] = float(args.capital) * 0.2  # 20% du capital par trade
            
        # Configurer les tokens à surveiller
        if args.network == "testnet":
            # Tokens de test sur Goerli/Sepolia
            config["tokens"] = [
                {"symbol": "WETH", "address": "0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6"},
                {"symbol": "DAI", "address": "0x11fE4B6AE13d2a6055C8D9cF65c55bac32B5d844"},
                {"symbol": "USDC", "address": "0x07865c6e87b9f70255377e024ace6630c1eaa37f"}
            ]
        else:
            # Tokens réels sur Mainnet
            config["tokens"] = [
                {"symbol": "WETH", "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"},
                {"symbol": "DAI", "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F"},
                {"symbol": "USDC", "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"},
                {"symbol": "USDT", "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7"}
            ]
            
        # Configurer les DEX
        if args.network == "testnet":
            # DEX sur testnet
            config["dex"] = {
                "uniswap_v2": {
                    "router_address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                    "factory_address": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
                },
                "sushiswap": {
                    "router_address": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
                    "factory_address": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4"
                }
            }
        else:
            # DEX sur mainnet
            config["dex"] = {
                "uniswap_v2": {
                    "router_address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                    "factory_address": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
                },
                "uniswap_v3": {
                    "router_address": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                    "factory_address": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
                },
                "sushiswap": {
                    "router_address": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
                    "factory_address": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"
                }
            }
            
        # Configurer les CEX (pour les tests, utiliser des API sandbox si disponibles)
        config["cex"] = {
            "exchanges": [
                {
                    "name": "binance",
                    "api_url": "https://api.binance.com/api/v3",
                    "ws_url": "wss://stream.binance.com:9443/ws",
                    "symbols": ["ETHUSDT", "BTCUSDT", "DAIETH", "USDCETH"]
                }
            ]
        }
        
        # Configurer le mode de test
        config["test_mode"] = {
            "enabled": True,
            "simulation_only": args.simulation_only,
            "max_trades_per_day": args.max_trades or 10,
            "max_capital": float(args.capital) if args.capital else 100.0
        }
        
        # Sauvegarder la configuration
        config_path = args.output or f"config/test_{args.network}_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
            
        logger.info(f"Configuration de test sauvegardée dans {config_path}")
        
        # Créer un lien symbolique vers la configuration active si demandé
        if args.set_active:
            active_config_path = "config/active_config.yaml"
            if os.path.exists(active_config_path):
                os.remove(active_config_path)
            shutil.copy(config_path, active_config_path)
            logger.info(f"Configuration active définie sur {config_path}")
            
        # Afficher les instructions
        print("\n" + "="*80)
        print(f"ENVIRONNEMENT DE TEST CONFIGURÉ: {args.network.upper()}")
        print("\nPour démarrer le bot en mode test:")
        print(f"  python scripts/start_bot.py --config={config_path} --mode=monitor-only")
        print("\nPour valider la configuration:")
        print(f"  python scripts/validate_config.py --config={config_path}")
        
        if args.generate_wallet:
            print("\nWallet de test généré:")
            print(f"  Adresse: {config['wallet']['address']}")
            print(f"  Clé privée sauvegardée dans: config/wallet_info.json")
            
            if args.network == "testnet":
                print("\nPour obtenir des tokens de test:")
                print("  Goerli: https://goerlifaucet.com/")
                print("  Sepolia: https://sepoliafaucet.com/")
                
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.critical(f"Erreur lors de la configuration de l'environnement de test: {str(e)}", exc_info=True)
        return 1
        
def generate_test_wallet():
    """
    Génère un wallet de test.
    
    Returns:
        dict: Informations du wallet
    """
    # Générer une clé privée aléatoire
    private_key = "0x" + secrets.token_hex(32)
    
    # Créer un compte à partir de la clé privée
    web3 = Web3()
    account = web3.eth.account.from_key(private_key)
    
    return {
        "address": account.address,
        "private_key": private_key,
        "min_balance_eth": "0.1"
    }
    
def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script de configuration de l'environnement de test pour GBPBot")
    
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet", help="Réseau à utiliser pour les tests")
    parser.add_argument("--capital", help="Capital de test à utiliser")
    parser.add_argument("--generate-wallet", action="store_true", help="Générer un nouveau wallet de test")
    parser.add_argument("--simulation-only", action="store_true", help="Exécuter uniquement en mode simulation")
    parser.add_argument("--max-trades", type=int, help="Nombre maximum de trades par jour")
    parser.add_argument("--output", help="Chemin de sortie pour la configuration")
    parser.add_argument("--set-active", action="store_true", help="Définir cette configuration comme active")
    
    args = parser.parse_args()
    
    # Exécuter la configuration de l'environnement de test
    exit_code = setup_test_env(args)
    sys.exit(exit_code)
    
if __name__ == "__main__":
    main() 