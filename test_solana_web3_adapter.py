#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour l'adaptateur Solana Web3.js
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Adresse du point d'accès Solana (utilisez une URL publique pour les tests)
RPC_URL = "https://api.mainnet-beta.solana.com"

# Adresse de test Solana (une adresse connue avec des transactions)
TEST_ADDRESS = "Ey9dqpS9PBRuMDGVj3Ec2W5d3mfnHNcHMYLMmJ17GVD1"

def run_node_command(script_path, command, args=None):
    """
    Exécute une commande via le script Node.js
    
    Args:
        script_path: Chemin vers le script solana_bridge.js
        command: Commande à exécuter
        args: Arguments pour la commande (dictionnaire)
        
    Returns:
        Résultat de la commande (JSON)
    """
    if args is None:
        args = {}
    
    try:
        process = subprocess.run(
            ["node", script_path, command, json.dumps(args)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Analyser la sortie JSON
        return json.loads(process.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution de la commande: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON: {e}")
        logger.error(f"Sortie: {process.stdout}")
        return None

def test_get_version():
    """Teste la récupération de la version du node"""
    logger.info("Test : Récupération de la version du node Solana...")
    
    script_path = "gbpbot/adapters/node_bridge/solana_bridge.js"
    result = run_node_command(script_path, "getVersion", {"rpcUrl": RPC_URL})
    
    if result and result.get("success"):
        logger.info(f"Version du node Solana: {result.get('version', 'inconnu')}")
        return True
    else:
        logger.error(f"Echec de la récupération de la version: {result}")
        return False

def test_get_balance():
    """Teste la récupération du solde d'une adresse"""
    logger.info(f"Test : Récupération du solde de {TEST_ADDRESS}...")
    
    script_path = "gbpbot/adapters/node_bridge/solana_bridge.js"
    result = run_node_command(script_path, "getBalance", {
        "rpcUrl": RPC_URL,
        "address": TEST_ADDRESS,
        "commitment": "confirmed"
    })
    
    if result and result.get("success"):
        balance_lamports = result.get("balance", 0)
        balance_sol = balance_lamports / 1_000_000_000  # Convertir lamports en SOL
        logger.info(f"Solde de {TEST_ADDRESS}: {balance_sol} SOL")
        return True
    else:
        logger.error(f"Echec de la récupération du solde: {result}")
        return False

def test_create_wallet():
    """Teste la création d'un nouveau portefeuille"""
    logger.info("Test : Création d'un nouveau portefeuille...")
    
    script_path = "gbpbot/adapters/node_bridge/solana_bridge.js"
    result = run_node_command(script_path, "createWallet")
    
    if result and result.get("success"):
        logger.info(f"Nouveau portefeuille créé: {result.get('publicKey')}")
        return True
    else:
        logger.error(f"Echec de la création du portefeuille: {result}")
        return False

def test_get_recent_blockhash():
    """Teste la récupération d'un blockhash récent"""
    logger.info("Test : Récupération d'un blockhash récent...")
    
    script_path = "gbpbot/adapters/node_bridge/solana_bridge.js"
    result = run_node_command(script_path, "getRecentBlockhash", {
        "rpcUrl": RPC_URL,
        "commitment": "confirmed"
    })
    
    if result and result.get("success"):
        logger.info(f"Blockhash récent: {result.get('blockhash')}")
        return True
    else:
        logger.error(f"Echec de la récupération du blockhash: {result}")
        return False

def main():
    """Fonction principale du script de test"""
    logger.info("Démarrage des tests de l'adaptateur Solana Web3.js...")
    
    # Vérifier que le script bridge existe
    script_path = Path("gbpbot/adapters/node_bridge/solana_bridge.js")
    if not script_path.exists():
        logger.error(f"Le script bridge n'existe pas: {script_path}")
        return False
    
    # Exécuter les tests
    tests = [
        test_get_version,
        test_get_balance,
        test_create_wallet,
        test_get_recent_blockhash
    ]
    
    success = True
    for test in tests:
        if not test():
            success = False
    
    if success:
        logger.info("Tous les tests ont réussi!")
    else:
        logger.error("Certains tests ont échoué.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 