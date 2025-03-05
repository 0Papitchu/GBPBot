#!/usr/bin/env python3
"""
Script de validation de la configuration pour GBPBot.
Vérifie que la configuration est valide et complète pour le bon fonctionnement du bot.
"""

import argparse
import logging
import sys
import os
import yaml
import json
import re
from pathlib import Path
from web3 import Web3
import requests

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/validate_config.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("validate_config")

# Schéma de validation pour la configuration
CONFIG_SCHEMA = {
    "required_sections": [
        "network", "rpc", "gas", "trading", "security", "monitoring", 
        "tokens", "dex", "cex", "wallet"
    ],
    "section_requirements": {
        "rpc": ["endpoints", "max_retries", "timeout", "cache_ttl"],
        "gas": ["max_base_fee_gwei", "max_priority_fee_gwei", "min_priority_fee_gwei", 
                "base_fee_multiplier", "priority_fee_multiplier", "max_total_fee_gwei", 
                "update_interval", "history_size"],
        "trading": ["max_slippage", "min_profit", "max_gas_price_gwei", 
                   "confirmation_timeout", "max_pending_transactions", 
                   "emergency_shutdown_threshold"],
        "security": ["max_price_change", "min_liquidity", "max_gas_price_gwei", 
                    "min_confirmations", "max_confirmation_attempts"],
        "monitoring": ["update_interval", "alert_thresholds"],
        "wallet": ["address", "private_key", "min_balance_eth"]
    }
}

def validate_config(config_path, args):
    """
    Valide la configuration du bot.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        args: Arguments de la ligne de commande
        
    Returns:
        bool: True si la configuration est valide, False sinon
    """
    try:
        logger.info(f"Validation de la configuration: {config_path}")
        
        # Vérifier que le fichier existe
        if not os.path.exists(config_path):
            logger.error(f"Le fichier de configuration n'existe pas: {config_path}")
            return False
            
        # Charger la configuration
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        if not config:
            logger.error("La configuration est vide ou invalide")
            return False
            
        # Vérifier les sections requises
        missing_sections = []
        for section in CONFIG_SCHEMA["required_sections"]:
            if section not in config:
                missing_sections.append(section)
                
        if missing_sections:
            logger.error(f"Sections manquantes dans la configuration: {', '.join(missing_sections)}")
            return False
            
        # Vérifier les paramètres requis dans chaque section
        missing_params = {}
        for section, required_params in CONFIG_SCHEMA["section_requirements"].items():
            if section in config:
                section_missing = []
                for param in required_params:
                    if param not in config[section]:
                        section_missing.append(param)
                        
                if section_missing:
                    missing_params[section] = section_missing
                    
        if missing_params:
            for section, params in missing_params.items():
                logger.error(f"Paramètres manquants dans la section '{section}': {', '.join(params)}")
            return False
            
        # Vérifier les valeurs spécifiques
        validation_errors = []
        
        # Vérifier le réseau
        if config["network"] not in ["mainnet", "goerli", "sepolia"]:
            validation_errors.append(f"Réseau non supporté: {config['network']}")
            
        # Vérifier les endpoints RPC
        if not config["rpc"]["endpoints"]:
            validation_errors.append("Aucun endpoint RPC configuré")
        else:
            # Tester la connexion aux endpoints RPC si demandé
            if args.test_connections:
                for endpoint in config["rpc"]["endpoints"]:
                    if "url" not in endpoint:
                        validation_errors.append(f"URL manquante pour un endpoint RPC: {endpoint}")
                        continue
                        
                    try:
                        # Remplacer les placeholders d'API key si nécessaire
                        url = endpoint["url"]
                        if "YOUR_API_KEY" in url:
                            validation_errors.append(f"Clé API non configurée pour l'endpoint: {url}")
                            continue
                            
                        # Tester la connexion
                        web3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 5}))
                        if not web3.is_connected():
                            validation_errors.append(f"Impossible de se connecter à l'endpoint RPC: {url}")
                        else:
                            logger.info(f"Connexion réussie à l'endpoint RPC: {url}")
                    except Exception as e:
                        validation_errors.append(f"Erreur lors de la connexion à l'endpoint RPC {url}: {str(e)}")
                        
        # Vérifier les adresses de wallet
        if "address" in config["wallet"]:
            if not Web3.is_address(config["wallet"]["address"]):
                validation_errors.append(f"Adresse de wallet invalide: {config['wallet']['address']}")
                
        # Vérifier les adresses de tokens
        for token in config["tokens"]:
            if "address" not in token:
                validation_errors.append(f"Adresse manquante pour le token: {token}")
            elif not Web3.is_address(token["address"]):
                validation_errors.append(f"Adresse invalide pour le token {token.get('symbol', 'inconnu')}: {token['address']}")
                
        # Vérifier les adresses DEX
        for dex_name, dex_config in config["dex"].items():
            for key in ["router_address", "factory_address"]:
                if key in dex_config and not Web3.is_address(dex_config[key]):
                    validation_errors.append(f"Adresse {key} invalide pour {dex_name}: {dex_config[key]}")
                    
        # Vérifier les valeurs numériques
        if float(config["trading"]["max_slippage"]) > 0.1:
            validation_errors.append(f"Slippage maximum trop élevé: {config['trading']['max_slippage']}")
            
        if float(config["trading"]["min_profit"]) <= 0:
            validation_errors.append(f"Profit minimum invalide: {config['trading']['min_profit']}")
            
        # Vérifier les API CEX si demandé
        if args.test_connections and "exchanges" in config["cex"]:
            for exchange in config["cex"]["exchanges"]:
                if "api_url" not in exchange:
                    validation_errors.append(f"URL d'API manquante pour l'exchange: {exchange.get('name', 'inconnu')}")
                    continue
                    
                try:
                    # Tester la connexion à l'API publique
                    response = requests.get(f"{exchange['api_url']}/ping", timeout=5)
                    if response.status_code != 200:
                        validation_errors.append(f"Impossible de se connecter à l'API de l'exchange {exchange.get('name', 'inconnu')}")
                    else:
                        logger.info(f"Connexion réussie à l'API de l'exchange: {exchange.get('name', 'inconnu')}")
                except Exception as e:
                    validation_errors.append(f"Erreur lors de la connexion à l'API de l'exchange {exchange.get('name', 'inconnu')}: {str(e)}")
                    
        # Afficher les erreurs de validation
        if validation_errors:
            for error in validation_errors:
                logger.error(f"Erreur de validation: {error}")
            return False
            
        # Vérifier les avertissements
        warnings = []
        
        # Vérifier les valeurs de gaz
        if float(config["gas"]["max_base_fee_gwei"]) > 1000:
            warnings.append(f"Base fee maximum très élevé: {config['gas']['max_base_fee_gwei']} gwei")
            
        if float(config["gas"]["max_priority_fee_gwei"]) > 100:
            warnings.append(f"Priority fee maximum très élevé: {config['gas']['max_priority_fee_gwei']} gwei")
            
        # Vérifier le mode test
        if "test_mode" in config and config["test_mode"].get("enabled", False):
            warnings.append("Le bot est configuré en mode test")
            
        # Afficher les avertissements
        for warning in warnings:
            logger.warning(f"Avertissement: {warning}")
            
        # Validation réussie
        logger.info("La configuration est valide")
        
        # Afficher un résumé de la configuration
        if args.verbose:
            print_config_summary(config)
            
        return True
        
    except Exception as e:
        logger.critical(f"Erreur lors de la validation de la configuration: {str(e)}", exc_info=True)
        return False
        
def print_config_summary(config):
    """
    Affiche un résumé de la configuration.
    
    Args:
        config: Configuration du bot
    """
    print("\n" + "="*80)
    print("RÉSUMÉ DE LA CONFIGURATION")
    print("="*80)
    
    print(f"\nRéseau: {config['network'].upper()}")
    
    print("\nEndpoints RPC:")
    for endpoint in config['rpc']['endpoints']:
        print(f"  - {endpoint['url']} (poids: {endpoint.get('weight', 1)})")
        
    print("\nTokens configurés:")
    for token in config['tokens']:
        print(f"  - {token.get('symbol', 'inconnu')}: {token['address']}")
        
    print("\nDEX configurés:")
    for dex_name, dex_config in config['dex'].items():
        print(f"  - {dex_name}")
        for key, value in dex_config.items():
            if key.endswith('_address'):
                print(f"    {key}: {value}")
                
    print("\nCEX configurés:")
    if "exchanges" in config['cex']:
        for exchange in config['cex']['exchanges']:
            print(f"  - {exchange.get('name', 'inconnu')}: {exchange.get('api_url', 'URL non spécifiée')}")
            if "symbols" in exchange:
                print(f"    Symboles: {', '.join(exchange['symbols'])}")
    else:
        print("  Aucun")
        
    print("\nParamètres de trading:")
    print(f"  - Slippage maximum: {config['trading']['max_slippage']}")
    print(f"  - Profit minimum: {config['trading']['min_profit']}")
    print(f"  - Prix du gaz maximum: {config['trading']['max_gas_price_gwei']} gwei")
    
    print("\nParamètres de sécurité:")
    print(f"  - Changement de prix maximum: {config['security']['max_price_change']}")
    print(f"  - Liquidité minimum: {config['security']['min_liquidity']}")
    print(f"  - Confirmations minimum: {config['security']['min_confirmations']}")
    
    if "test_mode" in config and config["test_mode"].get("enabled", False):
        print("\nMode test activé:")
        print(f"  - Simulation uniquement: {config['test_mode'].get('simulation_only', False)}")
        print(f"  - Trades maximum par jour: {config['test_mode'].get('max_trades_per_day', 'Non spécifié')}")
        print(f"  - Capital maximum: {config['test_mode'].get('max_capital', 'Non spécifié')}")
        
    print("\n" + "="*80)
    
def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script de validation de la configuration pour GBPBot")
    
    parser.add_argument("--config", default="config/active_config.yaml", help="Chemin vers le fichier de configuration à valider")
    parser.add_argument("--test-connections", action="store_true", help="Tester les connexions aux endpoints RPC et API")
    parser.add_argument("--verbose", "-v", action="store_true", help="Afficher un résumé détaillé de la configuration")
    
    args = parser.parse_args()
    
    # Valider la configuration
    is_valid = validate_config(args.config, args)
    
    # Sortir avec le code approprié
    sys.exit(0 if is_valid else 1)
    
if __name__ == "__main__":
    main() 