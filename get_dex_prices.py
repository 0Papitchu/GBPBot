from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# 🔹 Liste de RPC pour Avalanche
RPC_LIST = [
    os.getenv("RPC_URL", "https://api.avax.network/ext/bc/C/rpc"),
    "https://avax-mainnet.public.blastapi.io/ext/bc/C/rpc",
    "https://api.avax-test.network/ext/bc/C/rpc"
]

# 🔹 Connexion Web3 avec gestion des erreurs
web3 = None
for rpc in RPC_LIST:
    temp_web3 = Web3(Web3.HTTPProvider(rpc))
    if temp_web3.is_connected():
        web3 = temp_web3
        print(f"✅ Connecté à Avalanche via {rpc}")
        break
else:
    raise Exception("❌ Impossible de se connecter à Avalanche via les RPC testés.")

# 🔹 Adresses des ROUTERS et QUOTERS des DEX
TRADER_JOE_LBROUTER_V2_2 = "0x18556DA13313f3532c54711497A8FedAC273220E"  # LBRouter V2.2
TRADER_JOE_LBQUOTER_V2_2 = "0x9A550a522BBaDFB69019b0432800Ed17855A51C3"  # LBQuoter V2.2
PANGOLIN_ROUTER = "0x2D99ABD9008Dc933ff5c0CD271B88309593aB921"  # Pangolin Testnet

# 🔹 ABI des routers pour Trader Joe et Pangolin
JOE_LBROUTER_ABI = json.loads("""
[
    {
        "inputs": [
            {"internalType": "contract IERC20", "name": "tokenX", "type": "address"},
            {"internalType": "contract IERC20", "name": "tokenY", "type": "address"},
            {"internalType": "uint128", "name": "amountX", "type": "uint128"}
        ],
        "name": "getSwapOut",
        "outputs": [
            {"internalType": "uint128", "name": "amountY", "type": "uint128"},
            {"internalType": "uint128", "name": "fees", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
""")

PANGOLIN_ROUTER_ABI = json.loads("""
[
    {
        "constant": true,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "", "type": "uint256[]"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    }
]
""")

# 🔹 Charger les smart contracts avec gestion d'erreur
try:
    joe_router = web3.eth.contract(address=Web3.to_checksum_address(TRADER_JOE_LBROUTER_V2_2), abi=JOE_LBROUTER_ABI)
    pangolin_router = web3.eth.contract(address=Web3.to_checksum_address(PANGOLIN_ROUTER), abi=PANGOLIN_ROUTER_ABI)
except Exception as e:
    raise Exception(f"❌ Erreur lors du chargement des contrats DEX : {e}")

# 🔹 Adresses des tokens (AVAX / USDT)
AVAX_ADDRESS = "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"  # AVAX sur Avalanche
USDT_ADDRESS = "0xc7198437980c041c805A1EDcbA50c1Ce5db95118"  # USDT sur Avalanche

def get_trader_joe_v2_2_price(amount_in_wei, token_in, token_out):
    """ Récupère le prix sur Trader Joe V2.2 avec la fonction getSwapOut """
    try:
        result = joe_router.functions.getSwapOut(token_in, token_out, amount_in_wei).call()
        amount_out_wei, fees_wei = result
        amount_out = web3.from_wei(amount_out_wei, "ether")
        return amount_out
    except Exception as e:
        print(f"⚠️ Erreur sur Trader Joe V2.2 : {e}")
        return None

def get_pangolin_price(amount_in_wei, token_in, token_out):
    """ Récupère le prix sur Pangolin avec getAmountsOut() """
    try:
        amounts = pangolin_router.functions.getAmountsOut(amount_in_wei, [token_in, token_out]).call()
        return web3.from_wei(amounts[1], "ether")  # Convertir de wei en AVAX/USDT
    except Exception as e:
        print(f"⚠️ Erreur sur Pangolin : {e}")
        return None

def main():
    amount_in_wei = web3.to_wei(1, "ether")  # Simuler un swap de 1 AVAX

    joe_price = get_trader_joe_v2_2_price(amount_in_wei, AVAX_ADDRESS, USDT_ADDRESS)
    pangolin_price = get_pangolin_price(amount_in_wei, AVAX_ADDRESS, USDT_ADDRESS)

    print("\n📊 **Prix récupérés sur les DEX** :")
    print(f"🔹 Trader Joe V2.2 : {joe_price:.4f} USDT" if joe_price else "❌ Erreur sur Trader Joe V2.2")
    print(f"🔹 Pangolin        : {pangolin_price:.4f} USDT" if pangolin_price else "❌ Erreur sur Pangolin")

if __name__ == "__main__":
    main()
