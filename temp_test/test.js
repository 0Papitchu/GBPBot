const { Connection, PublicKey } = require('@solana/web3.js');

async function main() {
  try {
    console.log("Test de connexion à Solana...");
    
    // Utiliser un point de terminaison RPC public pour Solana
    const rpcUrl = "https://api.mainnet-beta.solana.com";
    const connection = new Connection(rpcUrl, 'confirmed');
    
    // Tester avec une adresse Solana connue
    const testAddress = "Ey9dqpS9PBRuMDGVj3Ec2W5d3mfnHNcHMYLMmJ17GVD1";
    const publicKey = new PublicKey(testAddress);
    
    // Récupérer la version
    console.log("Récupération de la version...");
    const version = await connection.getVersion();
    console.log("Version Solana:", version);
    
    // Récupérer le solde
    console.log("Récupération du solde...");
    const balance = await connection.getBalance(publicKey);
    const balanceSol = balance / 1_000_000_000; // Convertir lamports en SOL
    console.log(`Solde de ${testAddress}: ${balanceSol} SOL`);
    
    console.log("Test terminé avec succès!");
  } catch (error) {
    console.error("Erreur:", error);
    process.exit(1);
  }
}

main(); 