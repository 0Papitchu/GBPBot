Utilisation
==========

.. note::
   Ce guide d'utilisation a été vérifié le 04/03/2024 et est à jour avec la version actuelle du bot.
   Toutes les commandes et fonctionnalités décrites correspondent à l'implémentation actuelle.

Démarrage et arrêt
----------------

.. code-block:: bash

   # Démarrage du bot
   python main.py
   
   # Démarrage du serveur API
   python api_server.py
   
   # Démarrage du dashboard web
   python web_dashboard.py
   
   # Démarrage de tous les services
   python start_servers.py

Modes de fonctionnement
---------------------

* **Mode Simulation**: Exécute les stratégies sans effectuer de transactions réelles.
* **Mode Testnet**: Exécute les stratégies sur un réseau de test (Fuji, Goerli, etc.).
* **Mode Production**: Exécute les stratégies sur le réseau principal (Mainnet).
