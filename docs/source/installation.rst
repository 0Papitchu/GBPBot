
Installation
===========

Prérequis
--------

* Python 3.8+
* Accès à un nœud Ethereum/BSC (Infura, Alchemy, etc.)
* Un wallet avec des fonds suffisants pour les transactions

Installation rapide
-----------------

.. code-block:: bash

   # Cloner le dépôt
   git clone https://github.com/votre-username/gbpbot.git
   cd gbpbot
   
   # Créer un environnement virtuel
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   
   # Installer les dépendances
   pip install -r requirements.txt
   
   # Copier le fichier d'exemple de configuration
   cp .env.example .env
