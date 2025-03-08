#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation automatique de la configuration .env
===============================================

Ce script permet de valider automatiquement la configuration du fichier .env
en vérifiant la présence des variables requises, en testant les connexions RPC,
et en validant les formats des clés API.
"""

import os
import re
import sys
import json
import time
import logging
import asyncio
import platform
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional, Any, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("validate_env")

# Constantes
REQUIRED_VARS = [
    "SOLANA_RPC_URL",
    "AVALANCHE_RPC_URL",
    "ETH_RPC_URL",
    "TELEGRAM_BOT_TOKEN",
    "ETHERSCAN_API_KEY"
]

OPTIONAL_VARS = [
    "SONIC_RPC_URL",
    "OPENSEA_API_KEY",
    "COINGECKO_API_KEY",
    "ALCHEMY_API_KEY",
    "INFURA_API_KEY",
    "MNEMONIC",
    "PRIVATE_KEY"
]

RPC_VARS = {
    "SOLANA_RPC_URL": {"chain": "solana", "method": "getHealth", "params": []},
    "AVALANCHE_RPC_URL": {"chain": "avax", "method": "info.isBootstrapped", "params": {"chain": "C"}},
    "ETH_RPC_URL": {"chain": "ethereum", "method": "eth_blockNumber", "params": []},
    "SONIC_RPC_URL": {"chain": "sonic", "method": "eth_blockNumber", "params": []}
}

API_KEY_FORMATS = {
    "ETHERSCAN_API_KEY": r"^[A-Za-z0-9]{34}$",
    "TELEGRAM_BOT_TOKEN": r"^\d+:[A-Za-z0-9_-]{35}$", 
    "ALCHEMY_API_KEY": r"^[A-Za-z0-9]{32}$",
    "INFURA_API_KEY": r"^[A-Za-z0-9]{32}$",
    "COINGECKO_API_KEY": r"^CG-[A-Za-z0-9]{24}$",
    "OPENSEA_API_KEY": r"^[A-Za-z0-9]{40}$"
}

def load_env_file(env_path: Optional[str] = None) -> Dict[str, str]:
    """
    Charge les variables d'environnement depuis un fichier .env.
    
    Args:
        env_path: Chemin vers le fichier .env (optionnel)
    
    Returns:
        Dict[str, str]: Dictionnaire des variables d'environnement
    """
    # Déterminer le chemin du fichier .env
    if env_path is None:
        env_path = os.path.join(os.getcwd(), ".env")
    
    # Charger les variables d'environnement
    load_dotenv(env_path)
    
    # Récupérer les variables d'environnement
    env_vars = {}
    for var in REQUIRED_VARS + OPTIONAL_VARS:
        value = os.getenv(var)
        if value:
            # Masquer les clés privées et mnémoniques
            if var in ["PRIVATE_KEY", "MNEMONIC"]:
                env_vars[var] = "********" if value else None
            else:
                env_vars[var] = value
        else:
            env_vars[var] = None
    
    return env_vars

def validate_required_vars(env_vars: Dict[str, str]) -> List[str]:
    """
    Vérifie que toutes les variables requises sont présentes.
    
    Args:
        env_vars: Dictionnaire des variables d'environnement
    
    Returns:
        List[str]: Liste des variables manquantes
    """
    missing_vars = []
    for var in REQUIRED_VARS:
        if var not in env_vars or env_vars[var] is None:
            missing_vars.append(var)
    
    return missing_vars

def validate_api_key_format(env_vars: Dict[str, str]) -> Dict[str, bool]:
    """
    Vérifie le format des clés API.
    
    Args:
        env_vars: Dictionnaire des variables d'environnement
    
    Returns:
        Dict[str, bool]: Résultats de validation pour chaque clé API
    """
    validation_results = {}
    
    for var, pattern in API_KEY_FORMATS.items():
        if var in env_vars and env_vars[var]:
            is_valid = bool(re.match(pattern, env_vars[var]))
            validation_results[var] = is_valid
    
    return validation_results

def test_rpc_connection(rpc_url: str, chain: str, method: str, params: Any) -> Tuple[bool, str]:
    """
    Teste la connexion à un RPC.
    
    Args:
        rpc_url: URL du RPC à tester
        chain: Nom de la blockchain
        method: Méthode RPC à appeler
        params: Paramètres de la méthode
    
    Returns:
        Tuple[bool, str]: (Succès, Message)
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        response = requests.post(rpc_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if "error" in result:
                return False, f"Erreur RPC: {result['error']['message']}"
            else:
                return True, f"Connexion RPC {chain} établie avec succès"
        else:
            return False, f"Erreur HTTP {response.status_code}"
    
    except requests.RequestException as e:
        return False, f"Erreur de connexion: {str(e)}"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def validate_rpc_connections(env_vars: Dict[str, str]) -> Dict[str, Tuple[bool, str]]:
    """
    Valide les connexions RPC.
    
    Args:
        env_vars: Dictionnaire des variables d'environnement
    
    Returns:
        Dict[str, Tuple[bool, str]]: Résultats de validation pour chaque RPC
    """
    rpc_results = {}
    
    for var, rpc_info in RPC_VARS.items():
        if var in env_vars and env_vars[var]:
            success, message = test_rpc_connection(
                env_vars[var], 
                rpc_info["chain"], 
                rpc_info["method"], 
                rpc_info["params"]
            )
            rpc_results[var] = (success, message)
    
    return rpc_results

def print_validation_results(
    missing_vars: List[str],
    api_key_results: Dict[str, bool],
    rpc_results: Dict[str, Tuple[bool, str]]
) -> None:
    """
    Affiche les résultats de validation.
    
    Args:
        missing_vars: Liste des variables manquantes
        api_key_results: Résultats de validation des clés API
        rpc_results: Résultats de validation des RPC
    """
    print("\n=== Résultats de validation de la configuration ===\n")
    
    # Variables manquantes
    if missing_vars:
        print("❌ Variables requises manquantes:")
        for var in missing_vars:
            print(f"   - {var}")
    else:
        print("✅ Toutes les variables requises sont présentes")
    
    print("\n=== Format des clés API ===")
    for var, is_valid in api_key_results.items():
        status = "✅" if is_valid else "❌"
        print(f"{status} {var}: {'Format valide' if is_valid else 'Format invalide'}")
    
    print("\n=== Connexions RPC ===")
    for var, (success, message) in rpc_results.items():
        status = "✅" if success else "❌"
        print(f"{status} {var}: {message}")

def generate_suggestions(
    missing_vars: List[str],
    api_key_results: Dict[str, bool],
    rpc_results: Dict[str, Tuple[bool, str]]
) -> List[str]:
    """
    Génère des suggestions pour résoudre les problèmes détectés.
    
    Args:
        missing_vars: Liste des variables manquantes
        api_key_results: Résultats de validation des clés API
        rpc_results: Résultats de validation des RPC
    
    Returns:
        List[str]: Liste des suggestions
    """
    suggestions = []
    
    # Suggestions pour variables manquantes
    if missing_vars:
        suggestions.append("Variables requises manquantes:")
        for var in missing_vars:
            if var == "SOLANA_RPC_URL":
                suggestions.append("  - SOLANA_RPC_URL: Créez un compte sur https://solana.com/rpc ou utilisez https://api.mainnet-beta.solana.com")
            elif var == "AVALANCHE_RPC_URL":
                suggestions.append("  - AVALANCHE_RPC_URL: Utilisez https://api.avax.network/ext/bc/C/rpc")
            elif var == "ETH_RPC_URL":
                suggestions.append("  - ETH_RPC_URL: Créez un compte sur Infura ou Alchemy")
            elif var == "TELEGRAM_BOT_TOKEN":
                suggestions.append("  - TELEGRAM_BOT_TOKEN: Créez un bot via @BotFather sur Telegram")
            elif var == "ETHERSCAN_API_KEY":
                suggestions.append("  - ETHERSCAN_API_KEY: Créez un compte sur https://etherscan.io/apis")
    
    # Suggestions pour clés API invalides
    invalid_keys = [var for var, is_valid in api_key_results.items() if not is_valid]
    if invalid_keys:
        suggestions.append("\nClés API au format invalide:")
        for var in invalid_keys:
            if var == "ETHERSCAN_API_KEY":
                suggestions.append("  - ETHERSCAN_API_KEY: Doit être une chaîne de 34 caractères alphanumériques")
            elif var == "TELEGRAM_BOT_TOKEN":
                suggestions.append("  - TELEGRAM_BOT_TOKEN: Format attendu: '[0-9]+:[A-Za-z0-9_-]{35}'")
            elif var == "ALCHEMY_API_KEY":
                suggestions.append("  - ALCHEMY_API_KEY: Doit être une chaîne de 32 caractères alphanumériques")
            elif var == "INFURA_API_KEY":
                suggestions.append("  - INFURA_API_KEY: Doit être une chaîne de 32 caractères alphanumériques")
    
    # Suggestions pour RPC défaillants
    failed_rpcs = [var for var, (success, _) in rpc_results.items() if not success]
    if failed_rpcs:
        suggestions.append("\nConnexions RPC défaillantes:")
        for var in failed_rpcs:
            if var == "SOLANA_RPC_URL":
                suggestions.append("  - SOLANA_RPC_URL: Vérifiez l'URL ou essayez une alternative comme https://api.mainnet-beta.solana.com")
            elif var == "AVALANCHE_RPC_URL":
                suggestions.append("  - AVALANCHE_RPC_URL: Vérifiez l'URL ou essayez https://api.avax.network/ext/bc/C/rpc")
            elif var == "ETH_RPC_URL":
                suggestions.append("  - ETH_RPC_URL: Vérifiez votre clé Infura/Alchemy ou essayez une alternative")
            elif var == "SONIC_RPC_URL":
                suggestions.append("  - SONIC_RPC_URL: Vérifiez l'URL ou contactez l'équipe Sonic pour une URL valide")
    
    return suggestions

def configure_asyncio():
    """Configure asyncio selon le système d'exploitation."""
    if platform.system() == 'Windows':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Politique d'événement WindowsSelectorEventLoopPolicy configurée pour Windows")
        except ImportError:
            logger.warning("Impossible de configurer la politique d'événement pour Windows")

def interactive_fix_env(
    env_path: str,
    missing_vars: List[str],
    invalid_api_keys: List[str],
    failed_rpcs: List[str]
) -> bool:
    """
    Permet à l'utilisateur de corriger interactivement les problèmes du fichier .env.
    
    Args:
        env_path: Chemin vers le fichier .env
        missing_vars: Liste des variables manquantes
        invalid_api_keys: Liste des clés API au format invalide
        failed_rpcs: Liste des connexions RPC défaillantes
    
    Returns:
        bool: True si des modifications ont été effectuées
    """
    print("\n=== Correction interactive du fichier .env ===\n")
    
    # Charger le contenu actuel du fichier .env
    env_content = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # Variables à corriger
    vars_to_fix = missing_vars + invalid_api_keys + failed_rpcs
    if not vars_to_fix:
        print("Aucune correction nécessaire.")
        return False
    
    modified = False
    
    # Demander des valeurs pour chaque variable à corriger
    for var in vars_to_fix:
        print(f"Variable: {var}")
        
        # Afficher la valeur actuelle si elle existe
        current_value = env_content.get(var, "")
        if var in ["PRIVATE_KEY", "MNEMONIC"] and current_value:
            current_value = "********"
        
        if current_value:
            print(f"  Valeur actuelle: {current_value}")
        
        # Suggérer une valeur par défaut selon le type de variable
        default_value = ""
        if var == "SOLANA_RPC_URL" and var in missing_vars:
            default_value = "https://api.mainnet-beta.solana.com"
        elif var == "AVALANCHE_RPC_URL" and var in missing_vars:
            default_value = "https://api.avax.network/ext/bc/C/rpc"
        
        # Demander une nouvelle valeur
        prompt = f"  Nouvelle valeur"
        if default_value:
            prompt += f" (Appuyez sur Entrée pour utiliser '{default_value}')"
        prompt += ": "
        
        new_value = input(prompt)
        if not new_value and default_value:
            new_value = default_value
        
        if new_value:
            env_content[var] = new_value
            modified = True
    
    # Sauvegarder les modifications si nécessaire
    if modified:
        # Sauvegarder une copie de sauvegarde du fichier .env original
        if os.path.exists(env_path):
            backup_path = f"{env_path}.backup_{int(time.time())}"
            try:
                with open(env_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                print(f"Sauvegarde du fichier .env créée: {backup_path}")
            except Exception as e:
                print(f"Erreur lors de la création de la sauvegarde: {e}")
        
        # Écrire le nouveau fichier .env
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            print("Fichier .env mis à jour avec succès.")
        except Exception as e:
            print(f"Erreur lors de la mise à jour du fichier .env: {e}")
            return False
    
    return modified

def main():
    """Fonction principale."""
    print("=== Validation de la configuration GBPBot ===")
    
    # Configurer asyncio
    configure_asyncio()
    
    # Charger les variables d'environnement
    print("Chargement du fichier .env...")
    env_vars = load_env_file()
    
    # Valider les variables requises
    print("Vérification des variables requises...")
    missing_vars = validate_required_vars(env_vars)
    
    # Valider le format des clés API
    print("Validation du format des clés API...")
    api_key_results = validate_api_key_format(env_vars)
    
    # Valider les connexions RPC
    print("Test des connexions RPC...")
    rpc_results = validate_rpc_connections(env_vars)
    
    # Afficher les résultats
    print_validation_results(missing_vars, api_key_results, rpc_results)
    
    # Générer des suggestions
    suggestions = generate_suggestions(missing_vars, api_key_results, rpc_results)
    if suggestions:
        print("\n=== Suggestions ===")
        for suggestion in suggestions:
            print(suggestion)
    
    # Liste des problèmes
    invalid_api_keys = [var for var, is_valid in api_key_results.items() if not is_valid]
    failed_rpcs = [var for var, (success, _) in rpc_results.items() if not success]
    
    # Proposer une correction interactive
    if missing_vars or invalid_api_keys or failed_rpcs:
        print("\nDes problèmes ont été détectés dans votre configuration.")
        fix_now = input("Voulez-vous corriger ces problèmes maintenant? (o/n): ").lower()
        if fix_now in ["o", "oui", "y", "yes"]:
            interactive_fix_env(".env", missing_vars, invalid_api_keys, failed_rpcs)
    else:
        print("\n✅ Félicitations! Votre configuration est valide.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 