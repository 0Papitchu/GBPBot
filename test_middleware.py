#!/usr/bin/env python
"""
Script de test pour vérifier la connexion à Avalanche sans middleware spécifique.
"""

from web3 import Web3

def main():
    """Fonction principale"""
    print("Test de connexion à Avalanche sans middleware spécifique...")
    
    # Initialiser Web3 avec un provider Avalanche
    provider_url = "https://api.avax.network/ext/bc/C/rpc"
    provider = Web3.HTTPProvider(provider_url)
    web3 = Web3(provider)
    
    # Vérifier la connexion
    if web3.is_connected():
        print(f"Connecté au réseau via {provider_url}")
        try:
            chain_id = web3.eth.chain_id
            print(f"Chain ID: {chain_id}")
            print(f"Block number: {web3.eth.block_number}")
            print("La connexion fonctionne correctement !")
        except Exception as e:
            print(f"Erreur lors de l'accès aux données de la blockchain: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Échec de connexion à {provider_url}")
        print("La connexion ne fonctionne pas correctement.")

if __name__ == "__main__":
    main() 