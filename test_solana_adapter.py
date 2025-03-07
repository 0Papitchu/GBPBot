#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test simplifié pour l'adaptateur Solana Web3.js.

Ce script teste directement l'adaptateur sans dépendre d'autres modules GBPBot.
"""

import os
import sys
import logging
import json
import subprocess
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_node_installation():
    """Vérifie si Node.js est installé et disponible."""
    try:
        result = subprocess.run(
            ["node", "-v"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logger.info(f"Node.js est installé: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Node.js n'est pas installé ou n'est pas disponible: {e}")
        return False

def test_npm_installation():
    """Vérifie si npm est installé et disponible."""
    try:
        result = subprocess.run(
            ["npm", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logger.info(f"npm est installé: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"npm n'est pas installé ou n'est pas disponible: {e}")
        return False

def setup_node_bridge():
    """Configure les fichiers Node.js nécessaires pour l'adaptateur."""
    # Créer un répertoire temporaire pour les fichiers
    bridge_dir = Path("./temp_node_bridge")
    bridge_dir.mkdir(exist_ok=True)
    
    # Créer le fichier package.json
    package_json_path = bridge_dir / "package.json"
    package_json = {
        "name": "solana-bridge-test",
        "version": "1.0.0",
        "description": "Test bridge for Solana Web3.js",
        "main": "solana_bridge.js",
        "dependencies": {
            "@solana/web3.js": "^1.78.0"
        }
    }
    
    with open(package_json_path, "w") as f:
        json.dump(package_json, f, indent=2)
    
    # Créer le fichier JavaScript
    bridge_script_path = bridge_dir / "solana_bridge.js"
    with open(bridge_script_path, "w") as f:
        f.write("""
const { Connection, PublicKey } = require('@solana/web3.js');

// Fonction pour obtenir le solde d'une adresse
async function getBalance(rpcUrl, address, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const publicKey = new PublicKey(address);
    const balance = await connection.getBalance(publicKey);
    return { success: true, balance };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Point d'entrée pour les commandes
if (process.argv.length >= 3) {
  const command = process.argv[2];
  const args = JSON.parse(process.argv[3] || '{}');
  
  switch (command) {
    case 'getBalance':
      getBalance(args.rpcUrl, args.address, args.commitment)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    default:
      console.error(JSON.stringify({ success: false, error: `Unknown command: ${command}` }));
  }
}
        """)
    
    # Installer les dépendances
    logger.info("Installation des dépendances Node.js...")
    try:
        subprocess.run(
            ["npm", "install"], 
            cwd=bridge_dir, 
            check=True,
            capture_output=True
        )
        logger.info("Dépendances installées avec succès")
        return str(bridge_dir)
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'installation des dépendances: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return None

def test_solana_connection():
    """Teste la connexion à Solana en utilisant l'adaptateur."""
    bridge_dir = setup_node_bridge()
    if not bridge_dir:
        return False
    
    # Tester avec une adresse Solana connue
    test_address = "Ey9dqpS9PBRuMDGVj3Ec2W5d3mfnHNcHMYLMmJ17GVD1"
    rpc_url = "https://api.mainnet-beta.solana.com"
    
    # Exécuter la commande pour obtenir le solde
    try:
        script_path = os.path.join(bridge_dir, "solana_bridge.js")
        args = {
            "rpcUrl": rpc_url,
            "address": test_address,
            "commitment": "confirmed"
        }
        
        process = subprocess.run(
            ["node", script_path, "getBalance", json.dumps(args)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Analyser la sortie JSON
        result = json.loads(process.stdout)
        
        if result.get("success"):
            balance_lamports = result["balance"]
            balance_sol = balance_lamports / 1_000_000_000  # Convertir lamports en SOL
            logger.info(f"Solde de {test_address}: {balance_sol} SOL")
            return True
        else:
            logger.error(f"Erreur lors de la récupération du solde: {result.get('error')}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution de la commande: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON: {e}")
        logger.error(f"Sortie: {process.stdout}")
        return False
    finally:
        # Nettoyer les fichiers temporaires
        import shutil
        shutil.rmtree(bridge_dir, ignore_errors=True)

def main():
    """Fonction principale du script de test."""
    logger.info("Démarrage du test de l'adaptateur Solana Web3.js...")
    
    # Vérifier les prérequis
    if not test_node_installation() or not test_npm_installation():
        logger.error("Les prérequis ne sont pas satisfaits. Impossible de continuer.")
        sys.exit(1)
    
    # Tester la connexion à Solana
    if test_solana_connection():
        logger.info("Test de connexion à Solana réussi!")
        sys.exit(0)
    else:
        logger.error("Test de connexion à Solana échoué.")
        sys.exit(1)

if __name__ == "__main__":
    main() 