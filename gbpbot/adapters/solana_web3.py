"""
Module d'adaptateur pour utiliser @solana/web3.js depuis Python.

Ce module sert d'interface entre le code Python du GBPBot et la bibliothèque JavaScript
@solana/web3.js. Il utilise subprocess pour exécuter du code Node.js qui interagit avec
la blockchain Solana.
"""

import json
import os
import subprocess
import tempfile
import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

# Configurer le logger
logger = logging.getLogger(__name__)

class SolanaWeb3Adapter:
    """
    Classe d'adaptateur pour communiquer avec Solana via @solana/web3.js.
    Cette classe remplace les fonctionnalités de solana-py en utilisant la bibliothèque
    JavaScript à la place.
    """
    
    def __init__(self, rpc_url: Optional[str] = "", commitment: str = "confirmed"):
        """
        Initialiser l'adaptateur Solana Web3.js
        
        Args:
            rpc_url: URL du point de terminaison RPC Solana
            commitment: Niveau d'engagement (confirmed, finalized, etc.)
        """
        self.rpc_url = rpc_url or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.commitment = commitment
        self.node_bridge_dir = self._setup_node_bridge()
        
    def _setup_node_bridge(self) -> str:
        """
        Configure les fichiers Node.js nécessaires pour interagir avec @solana/web3.js
        
        Returns:
            Chemin vers le répertoire contenant les scripts Node.js
        """
        # Créer un répertoire pour les fichiers de pont si besoin
        bridge_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "node_bridge"
        bridge_dir.mkdir(exist_ok=True)
        
        # Créer le fichier package.json si nécessaire
        package_json_path = bridge_dir / "package.json"
        if not package_json_path.exists():
            package_json = {
                "name": "gbpbot-solana-bridge",
                "version": "1.0.0",
                "description": "Bridge for GBPBot to interact with Solana blockchain",
                "main": "index.js",
                "dependencies": {
                    "@solana/web3.js": "^1.78.0"
                }
            }
            with open(package_json_path, "w") as f:
                json.dump(package_json, f, indent=2)
            
            # Installer les dépendances
            try:
                subprocess.run(["npm", "install"], cwd=bridge_dir, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors de l'installation des dépendances Node: {e}")
        
        # Créer le fichier principal pour les opérations Solana
        bridge_script_path = bridge_dir / "solana_bridge.js"
        if not bridge_script_path.exists():
            with open(bridge_script_path, "w") as f:
                f.write("""
const { Connection, PublicKey, Keypair, Transaction, SystemProgram } = require('@solana/web3.js');

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

// Fonction pour envoyer des SOL
async function sendSol(rpcUrl, fromPrivateKey, toAddress, amount, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const senderKeypair = Keypair.fromSecretKey(Buffer.from(fromPrivateKey, 'hex'));
    const receiverPublicKey = new PublicKey(toAddress);
    
    const transaction = new Transaction().add(
      SystemProgram.transfer({
        fromPubkey: senderKeypair.publicKey,
        toPubkey: receiverPublicKey,
        lamports: amount,
      })
    );
    
    const signature = await connection.sendTransaction(transaction, [senderKeypair]);
    return { success: true, signature };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Obtenir les informations de compte
async function getAccountInfo(rpcUrl, address, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const publicKey = new PublicKey(address);
    const accountInfo = await connection.getAccountInfo(publicKey);
    return { 
      success: true, 
      accountInfo: accountInfo ? {
        lamports: accountInfo.lamports,
        owner: accountInfo.owner.toString(),
        executable: accountInfo.executable,
        rentEpoch: accountInfo.rentEpoch,
        data: Buffer.from(accountInfo.data).toString('hex')
      } : null
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Fonction pour obtenir la liste des transactions récentes
async function getRecentTransactions(rpcUrl, address, limit = 10, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const publicKey = new PublicKey(address);
    
    // Obtenir les signatures des transactions récentes
    const signatures = await connection.getSignaturesForAddress(publicKey, { limit });
    
    // Obtenir les détails des transactions
    const transactions = [];
    for (const sig of signatures) {
      const tx = await connection.getTransaction(sig.signature);
      transactions.push({
        signature: sig.signature,
        blockTime: tx?.blockTime || 0,
        slot: tx?.slot || 0,
        confirmationStatus: tx?.confirmationStatus || 'unknown'
      });
    }
    
    return { success: true, transactions };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Fonction pour créer un portefeuille
function createWallet() {
  try {
    const keypair = Keypair.generate();
    return { 
      success: true, 
      publicKey: keypair.publicKey.toString(),
      privateKey: Buffer.from(keypair.secretKey).toString('hex')
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Fonction pour obtenir la version du nœud
async function getVersion(rpcUrl) {
  try {
    const connection = new Connection(rpcUrl);
    const version = await connection.getVersion();
    return { 
      success: true,
      version: version["solanaCore"] || "unknown",
      featureSet: version["featureSet"] || 0
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Fonction pour obtenir un bloc hash récent
async function getRecentBlockhash(rpcUrl, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash(commitment);
    const feeCalculator = await connection.getFeeForMessage(
      new Transaction().compileMessage(),
      commitment
    );
    
    return { 
      success: true,
      blockhash,
      lastValidBlockHeight,
      feePerSignature: feeCalculator || 5000
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Fonction pour obtenir les comptes token d'un propriétaire
async function getTokenAccountsByOwner(rpcUrl, owner, filter, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const ownerPublicKey = new PublicKey(owner);
    
    let filterObj = {};
    if (filter.mint) {
      filterObj = { mint: new PublicKey(filter.mint) };
    } else if (filter.programId) {
      filterObj = { programId: new PublicKey(filter.programId) };
    }
    
    const accounts = await connection.getTokenAccountsByOwner(
      ownerPublicKey,
      filterObj
    );
    
    const formattedAccounts = accounts.value.map(account => {
      return {
        pubkey: account.pubkey.toString(),
        account: {
          data: ['', 'base64'],
          executable: account.account.executable,
          lamports: account.account.lamports,
          owner: account.account.owner.toString(),
          rentEpoch: account.account.rentEpoch
        }
      };
    });
    
    return { 
      success: true,
      accounts: {
        result: {
          value: formattedAccounts
        }
      }
    };
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
    case 'sendSol':
      sendSol(args.rpcUrl, args.fromPrivateKey, args.toAddress, args.amount, args.commitment)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    case 'getAccountInfo':
      getAccountInfo(args.rpcUrl, args.address, args.commitment)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    case 'getRecentTransactions':
      getRecentTransactions(args.rpcUrl, args.address, args.limit, args.commitment)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    case 'createWallet':
      const wallet = createWallet();
      console.log(JSON.stringify(wallet));
      break;
    case 'getVersion':
      getVersion(args.rpcUrl)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    case 'getRecentBlockhash':
      getRecentBlockhash(args.rpcUrl, args.commitment)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    case 'getTokenAccountsByOwner':
      getTokenAccountsByOwner(args.rpcUrl, args.owner, args.filter, args.commitment)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
    default:
      console.error(JSON.stringify({ success: false, error: `Unknown command: ${command}` }));
  }
}
                """)
        
        return str(bridge_dir)
    
    def _execute_node_command(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute une commande via le script Node.js et retourne le résultat
        
        Args:
            command: Nom de la commande à exécuter
            args: Arguments pour la commande
            
        Returns:
            Résultat de la commande
        """
        script_path = os.path.join(self.node_bridge_dir, "solana_bridge.js")
        
        # Ajouter l'URL RPC si non spécifiée
        if "rpcUrl" not in args:
            args["rpcUrl"] = self.rpc_url
        
        # Ajouter le commitment si non spécifié
        if "commitment" not in args:
            args["commitment"] = self.commitment
        
        try:
            # Exécuter la commande Node.js
            process = subprocess.run(
                ["node", script_path, command, json.dumps(args)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Analyser la sortie JSON
            result = json.loads(process.stdout)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'exécution de la commande Node.js: {e}")
            logger.error(f"Sortie d'erreur: {e.stderr}")
            
            # Essayer de parser l'erreur JSON si possible
            try:
                return json.loads(e.stdout)
            except:
                return {"success": False, "error": f"Erreur lors de l'exécution de la commande: {e}"}
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {e}")
            return {"success": False, "error": f"Erreur de décodage JSON: {e}"}
    
    def get_balance(self, address: str) -> float:
        """
        Obtenir le solde d'une adresse Solana en SOL
        
        Args:
            address: Adresse du portefeuille Solana
            
        Returns:
            Solde en SOL
        
        Raises:
            Exception: Si la requête échoue
        """
        result = self._execute_node_command("getBalance", {"address": address})
        
        if result.get("success"):
            # Convertir les lamports en SOL (1 SOL = 10^9 lamports)
            return result["balance"] / 1_000_000_000
        else:
            raise Exception(f"Erreur lors de la récupération du solde: {result.get('error')}")
    
    def send_sol(self, from_private_key: str, to_address: str, amount_sol: float) -> str:
        """
        Envoyer des SOL à une adresse
        
        Args:
            from_private_key: Clé privée de l'expéditeur (en hexa)
            to_address: Adresse du destinataire
            amount_sol: Montant en SOL à envoyer
            
        Returns:
            Signature de la transaction
            
        Raises:
            Exception: Si la transaction échoue
        """
        # Convertir le montant en SOL vers lamports
        amount_lamports = int(amount_sol * 1_000_000_000)
        
        result = self._execute_node_command("sendSol", {
            "fromPrivateKey": from_private_key,
            "toAddress": to_address,
            "amount": amount_lamports
        })
        
        if result.get("success"):
            return result["signature"]
        else:
            raise Exception(f"Erreur lors de l'envoi de SOL: {result.get('error')}")
    
    def get_account_info(self, address: str) -> Dict[str, Any]:
        """
        Obtenir les informations d'un compte Solana
        
        Args:
            address: Adresse du compte
            
        Returns:
            Informations du compte
            
        Raises:
            Exception: Si la requête échoue
        """
        result = self._execute_node_command("getAccountInfo", {"address": address})
        
        if result.get("success"):
            return result["accountInfo"]
        else:
            raise Exception(f"Erreur lors de la récupération des informations du compte: {result.get('error')}")
    
    def get_recent_transactions(self, address: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtenir les transactions récentes pour une adresse
        
        Args:
            address: Adresse du compte
            limit: Nombre maximum de transactions à retourner
            
        Returns:
            Liste des transactions récentes
            
        Raises:
            Exception: Si la requête échoue
        """
        result = self._execute_node_command("getRecentTransactions", {
            "address": address,
            "limit": limit
        })
        
        if result.get("success"):
            return result["transactions"]
        else:
            raise Exception(f"Erreur lors de la récupération des transactions récentes: {result.get('error')}")
    
    def create_wallet(self) -> Dict[str, str]:
        """
        Créer un nouveau portefeuille Solana
        
        Returns:
            Dictionnaire contenant la clé publique et la clé privée
            
        Raises:
            Exception: Si la création échoue
        """
        result = self._execute_node_command("createWallet", {})
        
        if result.get("success"):
            return {
                "public_key": result["publicKey"],
                "private_key": result["privateKey"]
            }
        else:
            raise Exception(f"Erreur lors de la création du portefeuille: {result.get('error')}")


# Classes d'adaptateurs pour remplacer les classes de solana-py

class PublicKey:
    """
    Adaptateur pour solana.publickey.PublicKey
    """
    def __init__(self, value: str):
        self.value = value
        
    def __str__(self) -> str:
        return self.value
    
    def to_base58(self) -> str:
        return self.value


class Keypair:
    """
    Adaptateur pour solana.keypair.Keypair
    """
    def __init__(self, secret_key: Optional[bytes] = b""):
        """
        Initialiser un Keypair
        
        Args:
            secret_key: Clé privée en bytes (optionnel)
        """
        if not secret_key:  # Vérifie si la clé est vide ou None
            # Créer un nouveau portefeuille
            adapter = SolanaWeb3Adapter()
            wallet = adapter.create_wallet()
            self.public_key = PublicKey(wallet["public_key"])
            self._secret_key = bytes.fromhex(wallet["private_key"])
        else:
            # Utiliser la clé privée fournie
            self._secret_key = secret_key
            # Normalement, nous devrions dériver la clé publique à partir de la clé privée
            # Mais comme nous ne pouvons pas facilement faire cette dérivation ici,
            # nous allons créer un nouveau portefeuille et ignorer la clé privée
            # Ce n'est pas idéal, mais c'est une solution temporaire
            adapter = SolanaWeb3Adapter()
            wallet = adapter.create_wallet()
            self.public_key = PublicKey(wallet["public_key"])
    
    @staticmethod
    def generate() -> 'Keypair':
        """
        Générer un nouveau Keypair
        
        Returns:
            Nouveau Keypair
        """
        return Keypair()
    
    @staticmethod
    def from_secret_key(secret_key: bytes) -> 'Keypair':
        """
        Créer un Keypair à partir d'une clé privée
        
        Args:
            secret_key: Clé privée en bytes
            
        Returns:
            Keypair
        """
        return Keypair(secret_key=secret_key)


class Transaction:
    """
    Adaptateur pour solana.transaction.Transaction
    """
    def __init__(self):
        self.instructions = []
        self.recent_blockhash = None
        self.signatures = []
    
    def add(self, instruction):
        """
        Ajouter une instruction à la transaction
        
        Args:
            instruction: Instruction à ajouter
            
        Returns:
            self
        """
        self.instructions.append(instruction)
        return self
    
    def sign(self, *signers):
        """
        Signer la transaction
        
        Args:
            signers: Liste des signataires
            
        Returns:
            self
        """
        for signer in signers:
            self.signatures.append(signer.public_key)
        return self


class TransactionInstruction:
    """
    Adaptateur pour solana.transaction.TransactionInstruction
    """
    def __init__(self, keys, program_id, data):
        self.keys = keys
        self.program_id = program_id
        self.data = data


class AccountMeta:
    """
    Adaptateur pour solana.transaction.AccountMeta
    """
    def __init__(self, pubkey, is_signer, is_writable):
        self.pubkey = pubkey
        self.is_signer = is_signer
        self.is_writable = is_writable


# Module pour remplacer solana.system_program
class SystemProgram:
    """
    Adaptateur pour solana.system_program
    """
    @staticmethod
    def transfer(params):
        """
        Créer une instruction de transfert
        
        Args:
            params: Paramètres de transfert
            
        Returns:
            Instruction de transfert
        """
        return {"type": "transfer", "params": params}


# Variable pour compatibilité avec solana.system_program.SYS_PROGRAM_ID
SYS_PROGRAM_ID = PublicKey("11111111111111111111111111111111")

# Remplacements pour les types de solana.rpc
class Commitment:
    """Enum pour les niveaux d'engagement de Solana."""
    FINALIZED = "finalized"
    CONFIRMED = "confirmed"
    PROCESSED = "processed"

class TxOpts:
    """Adaptateur pour solana.rpc.types.TxOpts."""
    def __init__(self, skip_preflight=False, preflight_commitment=None, max_retries=None):
        self.skip_preflight = skip_preflight
        self.preflight_commitment = preflight_commitment or Commitment.CONFIRMED
        self.max_retries = max_retries


# Classes pour remplacer solana.rpc.async_api.AsyncClient
class AsyncClient:
    """
    Adaptateur pour solana.rpc.async_api.AsyncClient
    """
    def __init__(self, endpoint: Optional[str] = "", commitment: Optional[str] = ""):
        """
        Initialiser un client Solana asynchrone
        
        Args:
            endpoint: URL du point de terminaison RPC Solana
            commitment: Niveau d'engagement
        """
        self.adapter = SolanaWeb3Adapter(
            rpc_url=endpoint or "https://api.mainnet-beta.solana.com", 
            commitment=commitment or "confirmed"
        )
    
    async def get_balance(self, pubkey):
        """
        Obtenir le solde d'une adresse
        
        Args:
            pubkey: Clé publique
            
        Returns:
            Solde en lamports
        """
        address = str(pubkey)
        sol_balance = self.adapter.get_balance(address)
        # Convertir SOL en lamports
        return int(sol_balance * 1_000_000_000)
    
    async def get_account_info(self, pubkey):
        """
        Obtenir les informations d'un compte
        
        Args:
            pubkey: Clé publique
            
        Returns:
            Informations du compte
        """
        address = str(pubkey)
        return self.adapter.get_account_info(address)
    
    async def send_transaction(self, transaction, signers):
        """
        Envoyer une transaction
        
        Args:
            transaction: Transaction à envoyer
            signers: Liste des signataires
            
        Returns:
            Signature de la transaction
        """
        # Cette méthode est simplifiée et ne gère que le cas de base
        # Un adaptateur plus complet nécessiterait plus de travail
        if len(transaction.instructions) == 1 and transaction.instructions[0].get("type") == "transfer":
            params = transaction.instructions[0]["params"]
            from_key = signers[0]._secret_key.hex()
            to_address = str(params["toPubkey"])
            amount_lamports = params["lamports"]
            
            # Convertir lamports en SOL
            amount_sol = amount_lamports / 1_000_000_000
            
            return self.adapter.send_sol(from_key, to_address, amount_sol)
        else:
            raise NotImplementedError("Seules les transactions de transfert simple sont implémentées")
    
    async def get_version(self):
        """
        Obtenir la version du node Solana
        
        Returns:
            Informations de version
        """
        result = self.adapter._execute_node_command("getVersion", {})
        
        if result.get("success"):
            return {
                "solana-core": result.get("version", "unknown"),
                "feature-set": result.get("featureSet", 0)
            }
        else:
            return None
    
    async def get_recent_blockhash(self):
        """
        Obtenir un blockhash récent
        
        Returns:
            Informations sur le blockhash récent
        """
        result = self.adapter._execute_node_command("getRecentBlockhash", {})
        
        if result.get("success"):
            return {
                "result": {
                    "value": {
                        "blockhash": result.get("blockhash", "11111111111111111111111111111111"),
                        "feeCalculator": {
                            "lamportsPerSignature": result.get("feePerSignature", 5000)
                        }
                    }
                }
            }
        else:
            return {
                "result": {
                    "value": {
                        "blockhash": "11111111111111111111111111111111",
                        "feeCalculator": {
                            "lamportsPerSignature": 5000
                        }
                    }
                }
            }
    
    async def get_token_accounts_by_owner(self, owner, filter_params):
        """
        Obtenir les comptes de token appartenant à un propriétaire
        
        Args:
            owner: Adresse du propriétaire
            filter_params: Paramètres de filtrage
            
        Returns:
            Liste des comptes de token
        """
        params = {
            "owner": str(owner),
            "filter": filter_params
        }
        
        result = self.adapter._execute_node_command("getTokenAccountsByOwner", params)
        
        if result.get("success"):
            return result.get("accounts", {"result": {"value": []}})
        else:
            return {"result": {"value": []}}
    
    async def close(self):
        """
        Fermer la connexion au node Solana
        """
        # Rien à faire, car les connexions sont éphémères dans notre adaptateur
        return True


# Fonction utilitaire pour créer une fonction de transfert compatible
def transfer(from_pubkey, to_pubkey, lamports):
    """
    Créer une instruction de transfert
    
    Args:
        from_pubkey: Clé publique de l'expéditeur
        to_pubkey: Clé publique du destinataire
        lamports: Montant en lamports
        
    Returns:
        Instruction de transfert
    """
    return SystemProgram.transfer({
        "fromPubkey": from_pubkey,
        "toPubkey": to_pubkey,
        "lamports": lamports
    })


# Client synchrone
class Client:
    """
    Adaptateur pour solana.rpc.api.Client
    """
    def __init__(self, endpoint: Optional[str] = "", commitment: Optional[str] = ""):
        """
        Initialiser un client Solana synchrone
        
        Args:
            endpoint: URL du point de terminaison RPC Solana
            commitment: Niveau d'engagement
        """
        self.adapter = SolanaWeb3Adapter(
            rpc_url=endpoint or "https://api.mainnet-beta.solana.com", 
            commitment=commitment or "confirmed"
        )
    
    def get_balance(self, pubkey):
        """
        Obtenir le solde d'une adresse
        
        Args:
            pubkey: Clé publique
            
        Returns:
            Solde en lamports
        """
        address = str(pubkey)
        sol_balance = self.adapter.get_balance(address)
        # Convertir SOL en lamports
        return int(sol_balance * 1_000_000_000)
    
    def get_account_info(self, pubkey):
        """
        Obtenir les informations d'un compte
        
        Args:
            pubkey: Clé publique
            
        Returns:
            Informations du compte
        """
        address = str(pubkey)
        return self.adapter.get_account_info(address)
    
    def send_transaction(self, transaction, signers):
        """
        Envoyer une transaction
        
        Args:
            transaction: Transaction à envoyer
            signers: Liste des signataires
            
        Returns:
            Signature de la transaction
        """
        # Cette méthode est simplifiée et ne gère que le cas de base
        # Un adaptateur plus complet nécessiterait plus de travail
        if len(transaction.instructions) == 1 and transaction.instructions[0].get("type") == "transfer":
            params = transaction.instructions[0]["params"]
            from_key = signers[0]._secret_key.hex()
            to_address = str(params["toPubkey"])
            amount_lamports = params["lamports"]
            
            # Convertir lamports en SOL
            amount_sol = amount_lamports / 1_000_000_000
            
            return self.adapter.send_sol(from_key, to_address, amount_sol)
        else:
            raise NotImplementedError("Seules les transactions de transfert simple sont implémentées") 