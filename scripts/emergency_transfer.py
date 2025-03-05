#!/usr/bin/env python3
"""
Script de transfert d'urgence pour GBPBot.
Transfère tous les actifs vers une adresse sécurisée.
"""

import argparse
import asyncio
import logging
import sys
import os
import json
import datetime
from pathlib import Path
from decimal import Decimal
from web3 import Web3

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

from gbpbot.core.gas.gas_manager import GasManager
from gbpbot.core.monitoring.advanced_monitor import AdvancedMonitor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/emergency_transfer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("emergency_transfer")

# ABI minimal pour les tokens ERC20
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
]

async def emergency_transfer(args):
    """
    Exécute la procédure de transfert d'urgence.
    
    Args:
        args: Arguments de la ligne de commande
    """
    try:
        logger.info(f"Démarrage de la procédure de transfert d'urgence vers {args.to}")
        
        # Charger la configuration
        config_path = args.config or "config/default_config.yaml"
        if not os.path.exists(config_path):
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            return 1
            
        # Charger la configuration
        with open(config_path, "r") as f:
            import yaml
            config = yaml.safe_load(f)
            
        # Initialiser le moniteur
        monitor = AdvancedMonitor(config_path)
        await monitor.start()
        
        # Initialiser Web3
        rpc_url = args.rpc or config.get("rpc", {}).get("primary_endpoint", "http://localhost:8545")
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not web3.is_connected():
            logger.error(f"Impossible de se connecter au nœud Ethereum: {rpc_url}")
            return 1
            
        # Initialiser le gestionnaire de gas
        gas_manager = GasManager(config, web3)
        await gas_manager.start()
        
        # Vérifier l'adresse de destination
        if not web3.is_address(args.to):
            logger.error(f"Adresse de destination invalide: {args.to}")
            return 1
            
        to_address = web3.to_checksum_address(args.to)
        
        # Récupérer la clé privée
        private_key = config.get("wallet", {}).get("private_key")
        if not private_key:
            logger.error("Clé privée non trouvée dans la configuration")
            return 1
            
        # Récupérer l'adresse du wallet
        account = web3.eth.account.from_key(private_key)
        from_address = account.address
        
        logger.info(f"Transfert depuis {from_address} vers {to_address}")
        
        # Récupérer la liste des tokens à transférer
        tokens = args.tokens.split(",") if args.tokens else []
        
        # Ajouter ETH à la liste des actifs à transférer
        assets_to_transfer = [{"symbol": "ETH", "address": None}]
        
        # Ajouter les tokens ERC20 à la liste
        for token_address in tokens:
            if web3.is_address(token_address):
                token_contract = web3.eth.contract(
                    address=web3.to_checksum_address(token_address),
                    abi=ERC20_ABI
                )
                
                try:
                    symbol = token_contract.functions.symbol().call()
                    assets_to_transfer.append({
                        "symbol": symbol,
                        "address": token_address,
                        "contract": token_contract
                    })
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération des informations du token {token_address}: {str(e)}")
                    
        # Enregistrer l'opération
        transfer_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        transfer_data = {
            "id": transfer_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "from_address": from_address,
            "to_address": to_address,
            "assets": [asset["symbol"] for asset in assets_to_transfer],
            "reason": args.reason
        }
        
        # Sauvegarder les détails du transfert
        transfers_dir = Path("data/transfers")
        transfers_dir.mkdir(parents=True, exist_ok=True)
        
        with open(transfers_dir / f"transfer_{transfer_id}.json", "w") as f:
            json.dump(transfer_data, f, indent=2)
            
        # Transférer chaque actif
        results = []
        
        for asset in assets_to_transfer:
            try:
                if asset["symbol"] == "ETH":
                    # Transférer ETH
                    result = await transfer_eth(
                        web3, gas_manager, private_key,
                        from_address, to_address,
                        args.gas_priority
                    )
                else:
                    # Transférer un token ERC20
                    result = await transfer_erc20(
                        web3, gas_manager, private_key,
                        from_address, to_address,
                        asset["contract"], asset["symbol"],
                        args.gas_priority
                    )
                    
                results.append(result)
                
            except Exception as e:
                logger.error(f"Erreur lors du transfert de {asset['symbol']}: {str(e)}")
                results.append({
                    "asset": asset["symbol"],
                    "success": False,
                    "error": str(e)
                })
                
        # Mettre à jour le fichier de transfert avec les résultats
        transfer_data["results"] = results
        
        with open(transfers_dir / f"transfer_{transfer_id}.json", "w") as f:
            json.dump(transfer_data, f, indent=2)
            
        # Afficher le résumé
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"Transfert d'urgence terminé. {success_count}/{len(results)} actifs transférés avec succès.")
        
        # Afficher les détails
        print("\n" + "="*80)
        print("RÉSUMÉ DU TRANSFERT D'URGENCE")
        print(f"ID: {transfer_id}")
        print(f"De: {from_address}")
        print(f"Vers: {to_address}")
        print("\nRésultats:")
        
        for result in results:
            status = "✅ Succès" if result["success"] else "❌ Échec"
            print(f"  {result['asset']}: {status}")
            if not result["success"] and "error" in result:
                print(f"    Erreur: {result['error']}")
                
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.critical(f"Erreur lors de la procédure de transfert d'urgence: {str(e)}", exc_info=True)
        return 1
        
async def transfer_eth(web3, gas_manager, private_key, from_address, to_address, gas_priority):
    """
    Transfère tout l'ETH vers l'adresse de secours.
    
    Args:
        web3: Instance Web3
        gas_manager: Gestionnaire de gas
        private_key: Clé privée du wallet
        from_address: Adresse source
        to_address: Adresse de destination
        gas_priority: Priorité du gas (low, medium, high)
        
    Returns:
        dict: Résultat du transfert
    """
    # Récupérer le solde ETH
    balance = web3.eth.get_balance(from_address)
    
    if balance == 0:
        logger.warning(f"Solde ETH nul, rien à transférer")
        return {
            "asset": "ETH",
            "success": True,
            "amount": "0",
            "tx_hash": None
        }
        
    # Estimer le gas nécessaire pour le transfert
    gas_limit = 21000  # Gas fixe pour un transfert ETH
    
    # Récupérer les paramètres de gas
    gas_params = await gas_manager.get_gas_params(gas_priority)
    
    # Calculer le coût en gas
    gas_cost = gas_limit * gas_params["maxFeePerGas"]
    
    # Calculer le montant à transférer (solde - coût du gas)
    amount_to_transfer = balance - gas_cost
    
    if amount_to_transfer <= 0:
        logger.warning(f"Solde ETH insuffisant pour couvrir les frais de gas")
        return {
            "asset": "ETH",
            "success": False,
            "error": "Solde insuffisant pour couvrir les frais de gas"
        }
        
    # Préparer la transaction
    tx = {
        "from": from_address,
        "to": to_address,
        "value": amount_to_transfer,
        "gas": gas_limit,
        "maxFeePerGas": gas_params["maxFeePerGas"],
        "maxPriorityFeePerGas": gas_params["maxPriorityFeePerGas"],
        "nonce": web3.eth.get_transaction_count(from_address),
        "chainId": web3.eth.chain_id
    }
    
    # Signer et envoyer la transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    logger.info(f"Transaction ETH envoyée: {tx_hash.hex()}")
    
    # Attendre la confirmation
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt["status"] == 1:
        logger.info(f"Transfert ETH réussi: {web3.from_wei(amount_to_transfer, 'ether')} ETH")
        return {
            "asset": "ETH",
            "success": True,
            "amount": str(web3.from_wei(amount_to_transfer, 'ether')),
            "tx_hash": tx_hash.hex()
        }
    else:
        logger.error(f"Échec du transfert ETH: {tx_hash.hex()}")
        return {
            "asset": "ETH",
            "success": False,
            "tx_hash": tx_hash.hex(),
            "error": "Transaction échouée"
        }
        
async def transfer_erc20(web3, gas_manager, private_key, from_address, to_address, token_contract, symbol, gas_priority):
    """
    Transfère tous les tokens ERC20 vers l'adresse de secours.
    
    Args:
        web3: Instance Web3
        gas_manager: Gestionnaire de gas
        private_key: Clé privée du wallet
        from_address: Adresse source
        to_address: Adresse de destination
        token_contract: Contrat du token
        symbol: Symbole du token
        gas_priority: Priorité du gas (low, medium, high)
        
    Returns:
        dict: Résultat du transfert
    """
    # Récupérer le solde du token
    balance = token_contract.functions.balanceOf(from_address).call()
    decimals = token_contract.functions.decimals().call()
    
    if balance == 0:
        logger.warning(f"Solde {symbol} nul, rien à transférer")
        return {
            "asset": symbol,
            "success": True,
            "amount": "0",
            "tx_hash": None
        }
        
    # Estimer le gas nécessaire pour le transfert
    gas_limit = token_contract.functions.transfer(to_address, balance).estimate_gas({"from": from_address})
    
    # Ajouter une marge de sécurité
    gas_limit = int(gas_limit * 1.2)
    
    # Récupérer les paramètres de gas
    gas_params = await gas_manager.get_gas_params(gas_priority)
    
    # Préparer la transaction
    tx = token_contract.functions.transfer(to_address, balance).build_transaction({
        "from": from_address,
        "gas": gas_limit,
        "maxFeePerGas": gas_params["maxFeePerGas"],
        "maxPriorityFeePerGas": gas_params["maxPriorityFeePerGas"],
        "nonce": web3.eth.get_transaction_count(from_address),
        "chainId": web3.eth.chain_id
    })
    
    # Signer et envoyer la transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    logger.info(f"Transaction {symbol} envoyée: {tx_hash.hex()}")
    
    # Attendre la confirmation
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt["status"] == 1:
        amount = Decimal(balance) / Decimal(10**decimals)
        logger.info(f"Transfert {symbol} réussi: {amount} {symbol}")
        return {
            "asset": symbol,
            "success": True,
            "amount": str(amount),
            "tx_hash": tx_hash.hex()
        }
    else:
        logger.error(f"Échec du transfert {symbol}: {tx_hash.hex()}")
        return {
            "asset": symbol,
            "success": False,
            "tx_hash": tx_hash.hex(),
            "error": "Transaction échouée"
        }
        
def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script de transfert d'urgence pour GBPBot")
    
    parser.add_argument("--to", required=True, help="Adresse de destination pour le transfert")
    parser.add_argument("--tokens", help="Liste des adresses de tokens à transférer, séparées par des virgules")
    parser.add_argument("--reason", default="Transfert d'urgence", help="Raison du transfert d'urgence")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration")
    parser.add_argument("--rpc", help="URL du nœud RPC Ethereum")
    parser.add_argument("--gas-priority", choices=["low", "medium", "high"], default="high", help="Priorité du gas")
    
    args = parser.parse_args()
    
    # Exécuter la procédure de transfert d'urgence
    exit_code = asyncio.run(emergency_transfer(args))
    sys.exit(exit_code)
    
if __name__ == "__main__":
    main() 