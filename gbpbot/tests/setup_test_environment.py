#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de configuration de l'environnement de test du GBPBot

Ce module prépare et nettoie l'environnement pour les tests unitaires.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, List

def setup_test_environment() -> Tuple[str, List[str]]:
    """
    Prépare l'environnement de test
    
    Returns:
        Tuple[str, List[str]]: Chemin du fichier d'environnement et liste des chemins des wallets
    """
    # Créer un dossier temporaire pour les tests
    test_dir = tempfile.mkdtemp(prefix="gbpbot_test_")
    
    # Créer les sous-dossiers nécessaires
    os.makedirs(os.path.join(test_dir, "keys"), exist_ok=True)
    os.makedirs(os.path.join(test_dir, "data"), exist_ok=True)
    
    # Fichiers de test
    env_file = os.path.join(test_dir, ".env")
    config_file = os.path.join(test_dir, "config.json")
    encryption_key_file = os.path.join(test_dir, "keys", "encryption.key")
    api_keys_file = os.path.join(test_dir, "keys", "api_keys.enc")
    wallets_file = os.path.join(test_dir, "keys", "wallets.enc")
    
    # Configuration de test
    test_config = {
        "general": {
            "environment": "testnet",
            "log_level": "INFO",
            "data_dir": "data",
            "max_concurrent_tasks": 10
        },
        "security": {
            "encryption_enabled": True,
            "encryption_key_file": encryption_key_file,
            "api_keys_file": api_keys_file,
            "wallets_file": wallets_file
        },
        "blockchain": {
            "avalanche": {
                "rpc_url": "https://api.avax-test.network/ext/bc/C/rpc",
                "chain_id": "43113",
                "websocket": "wss://api.avax-test.network/ext/bc/C/ws"
            },
            "solana": {
                "rpc_url": "https://api.testnet.solana.com",
                "websocket": "wss://api.testnet.solana.com"
            }
        },
        "api_keys": {
            "openai": "sk-test-key-not-real",
            "binance": "test-binance-key",
            "kucoin": "test-kucoin-key"
        },
        "wallets": {
            "avalanche": {
                "address": "0xTestWalletAddress123",
                "private_key": "test-private-key-not-real"
            },
            "solana": {
                "address": "TestSolanaAddress123",
                "private_key": "test-solana-private-key-not-real"
            }
        },
        "trading": {
            "max_slippage": 1.0,
            "gas_multiplier": 1.2,
            "default_amount_usd": 100,
            "max_amount_usd": 1000
        }
    }
    
    # Variables d'environnement de test
    test_env = {
        "GBPBOT_ENV": "test",
        "GBPBOT_CONFIG": config_file,
        "AVALANCHE_RPC_URL": test_config["blockchain"]["avalanche"]["rpc_url"],
        "AVALANCHE_CHAIN_ID": test_config["blockchain"]["avalanche"]["chain_id"],
        "AVALANCHE_WEBSOCKET": test_config["blockchain"]["avalanche"]["websocket"],
        "SOLANA_RPC_URL": test_config["blockchain"]["solana"]["rpc_url"],
        "SOLANA_WEBSOCKET_URL": test_config["blockchain"]["solana"]["websocket"]
    }
    
    # Sauvegarder la configuration
    with open(config_file, "w") as f:
        json.dump(test_config, f, indent=4)
    
    # Sauvegarder les variables d'environnement
    with open(env_file, "w") as f:
        for key, value in test_env.items():
            f.write(f"{key}={value}\n")
    
    # Liste des chemins des wallets pour le nettoyage
    wallet_paths = [
        encryption_key_file,
        api_keys_file,
        wallets_file
    ]
    
    return env_file, wallet_paths

def cleanup_test_environment(env_file: str, wallet_paths: List[str]) -> None:
    """
    Nettoie l'environnement de test
    
    Args:
        env_file (str): Chemin du fichier d'environnement
        wallet_paths (List[str]): Liste des chemins des wallets
    """
    # Supprimer les fichiers de wallets
    for path in wallet_paths:
        if os.path.exists(path):
            os.remove(path)
    
    # Supprimer le fichier d'environnement
    if os.path.exists(env_file):
        os.remove(env_file)
    
    # Supprimer le dossier parent (dossier temporaire)
    test_dir = os.path.dirname(env_file)
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(test_dir) 