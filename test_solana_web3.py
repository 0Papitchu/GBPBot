#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour vérifier que l'adaptateur Solana Web3.js fonctionne correctement.

Ce script crée une connexion à Solana, vérifie le solde d'un compte et effectue
d'autres opérations pour confirmer que l'adaptateur fonctionne comme prévu.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importer les modules de notre adaptateur
try:
    from gbpbot.adapters.solana_web3 import (
        SolanaWeb3Adapter,
        PublicKey,
        Keypair,
        AsyncClient
    )
except ImportError as e:
    logger.error(f"Erreur lors de l'importation des modules: {e}")
    sys.exit(1)

async def test_solana_web3_adapter():
    """
    Teste les fonctionnalités de base de l'adaptateur Solana Web3.js.
    """
    logger.info("Démarrage du test de l'adaptateur Solana Web3.js...")
    
    # Utiliser un point de terminaison RPC public pour Solana
    rpc_url = "https://api.mainnet-beta.solana.com"
    
    # Créer une instance de l'adaptateur
    try:
        adapter = SolanaWeb3Adapter(rpc_url=rpc_url)
        logger.info(f"Adaptateur créé avec succès. URL RPC: {rpc_url}")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'adaptateur: {e}")
        return False
    
    # Créer un client asynchrone
    try:
        client = AsyncClient(endpoint=rpc_url)
        logger.info("Client asynchrone créé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la création du client: {e}")
        return False
    
    # Récupérer la version du node
    try:
        version = await client.get_version()
        logger.info(f"Version du node Solana: {version}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la version: {e}")
    
    # Tester avec une adresse Solana connue
    test_address = "Ey9dqpS9PBRuMDGVj3Ec2W5d3mfnHNcHMYLMmJ17GVD1"
    
    # Obtenir le solde de l'adresse
    try:
        balance = await client.get_balance(PublicKey(test_address))
        sol_balance = balance / 1_000_000_000  # Convertir lamports en SOL
        logger.info(f"Solde de {test_address}: {sol_balance} SOL")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du solde: {e}")
        return False
    
    # Créer un nouveau portefeuille
    try:
        new_wallet = adapter.create_wallet()
        logger.info(f"Nouveau portefeuille créé: {new_wallet['public_key']}")
    except Exception as e:
        logger.error(f"Erreur lors de la création du portefeuille: {e}")
        return False
    
    # Récupérer un blockhash récent
    try:
        blockhash = await client.get_recent_blockhash()
        logger.info(f"Blockhash récent: {blockhash['result']['value']['blockhash']}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du blockhash: {e}")
    
    # Test de fermeture
    try:
        await client.close()
        logger.info("Fermeture du client réussie")
    except Exception as e:
        logger.error(f"Erreur lors de la fermeture du client: {e}")
    
    logger.info("Test de l'adaptateur Solana Web3.js terminé avec succès")
    return True

def main():
    """
    Fonction principale du script de test.
    """
    try:
        # Exécuter la fonction de test asynchrone
        success = asyncio.run(test_solana_web3_adapter())
        
        # Sortir avec un code approprié
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Erreur non gérée: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 