#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test des connexions aux blockchains pour GBPBot
===============================================

Ce script vérifie que les connexions aux différentes blockchains
(Solana, Avalanche, etc.) sont fonctionnelles.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("blockchain_test")

# Charger les variables d'environnement
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Variables d'environnement chargées depuis .env")
except ImportError:
    logger.warning("Module python-dotenv non trouvé. Les variables d'environnement ne seront pas chargées depuis .env.")
    logger.warning("Installez avec: pip install python-dotenv")

def test_solana_connection(rpc_url: Optional[str] = None) -> bool:
    """
    Teste la connexion au RPC Solana
    
    Args:
        rpc_url: URL du RPC Solana (optionnel, sinon utilise la variable d'environnement)
        
    Returns:
        bool: True si la connexion est établie, False sinon
    """
    if not rpc_url:
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    logger.info(f"Test de connexion Solana: {rpc_url}")
    
    headers = {"Content-Type": "application/json"}
    data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getHealth",
        "params": []
    }
    
    try:
        start_time = time.time()
        response = requests.post(rpc_url, headers=headers, json=data, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Solana RPC répond en {elapsed:.2f}s: {result}")
            
            if "result" in result and result["result"] == "ok":
                logger.info("Connexion Solana établie avec succès")
                return True
            else:
                logger.warning(f"Solana RPC a répondu avec un statut anormal: {result}")
                return False
        else:
            logger.error(f"Erreur HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors du test de connexion Solana: {e}")
        return False

def test_avalanche_connection(rpc_url: Optional[str] = None) -> bool:
    """
    Teste la connexion au RPC Avalanche
    
    Args:
        rpc_url: URL du RPC Avalanche (optionnel, sinon utilise la variable d'environnement)
        
    Returns:
        bool: True si la connexion est établie, False sinon
    """
    if not rpc_url:
        rpc_url = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
    
    logger.info(f"Test de connexion Avalanche: {rpc_url}")
    
    headers = {"Content-Type": "application/json"}
    data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_chainId",
        "params": []
    }
    
    try:
        start_time = time.time()
        response = requests.post(rpc_url, headers=headers, json=data, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Avalanche RPC répond en {elapsed:.2f}s: {result}")
            
            if "result" in result:
                logger.info("Connexion Avalanche établie avec succès")
                return True
            else:
                logger.warning(f"Avalanche RPC a répondu avec un statut anormal: {result}")
                return False
        else:
            logger.error(f"Erreur HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors du test de connexion Avalanche: {e}")
        return False

def test_dex_connection(dex_name: str, rpc_url: str) -> bool:
    """
    Teste la connexion à un DEX spécifique
    
    Args:
        dex_name: Nom du DEX à tester
        rpc_url: URL du RPC à utiliser
        
    Returns:
        bool: True si la connexion est établie, False sinon
    """
    logger.info(f"Test de connexion au DEX {dex_name}: {rpc_url}")
    
    headers = {"Content-Type": "application/json"}
    
    # Les paramètres de requête dépendent du DEX
    if "traderjoe" in dex_name.lower():
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_blockNumber",
            "params": []
        }
    elif "raydium" in dex_name.lower():
        # Pour Raydium sur Solana, on utilise les endpoints Solana
        return test_solana_connection(rpc_url)
    else:
        # Requête générique pour les autres DEX basés sur EVM
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_blockNumber",
            "params": []
        }
    
    try:
        start_time = time.time()
        response = requests.post(rpc_url, headers=headers, json=data, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"DEX {dex_name} répond en {elapsed:.2f}s: {result}")
            
            if "result" in result:
                logger.info(f"Connexion au DEX {dex_name} établie avec succès")
                return True
            else:
                logger.warning(f"DEX {dex_name} a répondu avec un statut anormal: {result}")
                return False
        else:
            logger.error(f"Erreur HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors du test de connexion au DEX {dex_name}: {e}")
        return False

def generate_report(results: Dict[str, bool]) -> None:
    """
    Génère un rapport des tests de connexion
    
    Args:
        results: Dictionnaire des résultats de test par blockchain/DEX
    """
    print("\n" + "="*50)
    print(" "*15 + "RAPPORT DE CONNEXION")
    print("="*50)
    
    all_success = True
    
    for name, success in results.items():
        status = "✓ OK" if success else "✗ ÉCHEC"
        print(f"{name:20s}: {status}")
        all_success = all_success and success
    
    print("-"*50)
    overall = "TOUTES LES CONNEXIONS OK" if all_success else "CERTAINES CONNEXIONS ONT ÉCHOUÉ"
    print(f"Résultat global: {overall}")
    print("="*50 + "\n")
    
    if not all_success:
        print("Recommandations:")
        print("1. Vérifiez votre connexion internet")
        print("2. Vérifiez que les URL RPC dans le fichier .env sont correctes")
        print("3. Certains RPC publics peuvent être temporairement indisponibles, essayez plus tard")
        print("4. Envisagez d'utiliser des RPC privés pour une meilleure fiabilité")
        print()

def create_env_from_example():
    """Crée un fichier .env à partir du fichier .env.example s'il n'existe pas"""
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        logger.info("Fichier .env non trouvé, création à partir de .env.example")
        try:
            with open(".env.example", "r") as example_file:
                with open(".env", "w") as env_file:
                    env_file.write(example_file.read())
            logger.info("Fichier .env créé avec succès")
            
            # Recharger les variables d'environnement
            from dotenv import load_dotenv
            load_dotenv()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création du fichier .env: {e}")
            return False
    return False

def main():
    """Fonction principale pour tester les connexions aux blockchains"""
    print("\n" + "="*50)
    print(" "*10 + "GBPBot - Test des Connexions Blockchain")
    print("="*50 + "\n")
    
    # Vérifier si le fichier .env existe, sinon le créer
    if not os.path.exists(".env"):
        logger.warning("Fichier .env non trouvé")
        created = create_env_from_example()
        if created:
            logger.info("Fichier .env créé à partir de .env.example")
            logger.info("Veuillez éditer le fichier .env avec vos propres clés API et paramètres")
            logger.info("Puis relancez ce script")
            return
        else:
            logger.warning("Impossible de créer le fichier .env. Utilisation des variables d'environnement système")
    
    # Tester les connexions
    results = {}
    
    # Test Solana
    solana_rpc = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    results["Solana"] = test_solana_connection(solana_rpc)
    
    # Test Avalanche
    avalanche_rpc = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
    results["Avalanche"] = test_avalanche_connection(avalanche_rpc)
    
    # Test DEX - TraderJoe sur Avalanche
    traderjoe_rpc = os.getenv("TRADERJOE_RPC_URL", avalanche_rpc)
    results["TraderJoe (DEX)"] = test_dex_connection("traderjoe", traderjoe_rpc)
    
    # Test DEX - Raydium sur Solana
    raydium_rpc = os.getenv("RAYDIUM_RPC_URL", solana_rpc)
    results["Raydium (DEX)"] = test_dex_connection("raydium", raydium_rpc)
    
    # Générer le rapport
    generate_report(results)

if __name__ == "__main__":
    main() 