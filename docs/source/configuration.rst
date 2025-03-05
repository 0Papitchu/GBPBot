Configuration
============

.. note::
   Ce guide de configuration a été vérifié le 04/03/2024 et est à jour avec la version actuelle du bot.
   Toutes les configurations décrites correspondent à l'implémentation actuelle.

Fichier .env
-----------

Le fichier `.env` contient toutes les variables d'environnement nécessaires au fonctionnement du bot.

.. code-block:: bash

   # Fournisseurs Web3
   WEB3_PROVIDER_URI=https://mainnet.infura.io/v3/your-api-key
   WEB3_PROVIDER_URI_TESTNET=https://goerli.infura.io/v3/your-api-key
   
   # Wallet
   WALLET_PRIVATE_KEY=your-private-key
   WALLET_ADDRESS=your-wallet-address
   
   # Mode de fonctionnement
   SIMULATION_MODE=true
   IS_TESTNET=false
   
   # Limites
   MAX_TRADES_PER_DAY=10
   MAX_GAS_PER_TRADE=0.01
   STOP_LOSS_PERCENTAGE=10
   TAKE_PROFIT_PERCENTAGE=20

Configuration des stratégies
--------------------------

Les stratégies sont configurées dans des fichiers JSON dans le répertoire `config/strategies/`.

.. code-block:: json

   {
     "name": "mempool_sniping",
     "enabled": true,
     "parameters": {
       "min_liquidity": 1.0,
       "max_buy_amount": 0.1,
       "gas_boost_percentage": 10,
       "target_dexes": [
         "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
         "0x10ED43C718714eb63d5aA57B78B54704E256024E"
       ],
       "blacklisted_tokens": [
         "0x0000000000000000000000000000000000000000"
       ]
     }
   }
