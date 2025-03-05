
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

D�marrer le sniping
^^^^^^^^^^^^^^^^

.. code-block:: bash

   POST /start_sniping

Authentification
--------------

Toutes les requ�tes (sauf `/health`) n�cessitent une authentification par cl� API.

.. code-block:: bash

   x-api-key: votre-cl�-api
