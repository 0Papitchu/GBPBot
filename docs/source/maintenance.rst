
Maintenance
==========

Mises � jour
----------

Pour mettre � jour le bot:

.. code-block:: bash

   # Arr�ter tous les services
   python stop_servers.py
   
   # Sauvegarder les fichiers de configuration
   cp .env .env.backup
   cp -r config config.backup
   
   # Mettre � jour le code
   git pull
   
   # Installer les nouvelles d�pendances
   pip install -r requirements.txt
   
   # Red�marrer les services
   python start_servers.py

Logs
----

Les logs sont stock�s dans le r�pertoire `logs/`:

* `bot.log`: Log principal du bot
* `gbpbot_api.log`: Log de l'API
* `gbpbot_dashboard.log`: Log du dashboard
* `monitor.log`: Log du moniteur de production
* `deployment.log`: Log du d�ploiement
