
API Reference
============

Endpoints principaux
------------------

Statut du bot
^^^^^^^^^^^

.. code-block:: bash

   GET /status

Historique des trades
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   GET /trades

Démarrer le sniping
^^^^^^^^^^^^^^^^

.. code-block:: bash

   POST /start_sniping

Authentification
--------------

Toutes les requêtes (sauf `/health`) nécessitent une authentification par clé API.

.. code-block:: bash

   x-api-key: votre-clé-api
