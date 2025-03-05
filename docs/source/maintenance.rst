
Maintenance
==========

Mises à jour
----------

Pour mettre à jour le bot:

.. code-block:: bash

   # Arrêter tous les services
   python stop_servers.py
   
   # Sauvegarder les fichiers de configuration
   cp .env .env.backup
   cp -r config config.backup
   
   # Mettre à jour le code
   git pull
   
   # Installer les nouvelles dépendances
   pip install -r requirements.txt
   
   # Redémarrer les services
   python start_servers.py

Logs
----

Les logs sont stockés dans le répertoire `logs/`:

* `bot.log`: Log principal du bot
* `gbpbot_api.log`: Log de l'API
* `gbpbot_dashboard.log`: Log du dashboard
* `monitor.log`: Log du moniteur de production
* `deployment.log`: Log du déploiement
