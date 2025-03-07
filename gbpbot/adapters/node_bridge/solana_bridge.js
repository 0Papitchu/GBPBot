const { Connection, PublicKey, Keypair, Transaction, SystemProgram } = require('@solana/web3.js');

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

// Fonction pour obtenir un bloc hash récent
async function getRecentBlockhash(rpcUrl, commitment = 'confirmed') {
  try {
    const connection = new Connection(rpcUrl, commitment);
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash(commitment);
    
    return { 
      success: true,
      blockhash,
      lastValidBlockHeight,
      feePerSignature: 5000 // Valeur par défaut raisonnable
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
    case 'getVersion':
      getVersion(args.rpcUrl)
        .then(result => console.log(JSON.stringify(result)))
        .catch(err => console.error(JSON.stringify({ success: false, error: err.message })));
      break;
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