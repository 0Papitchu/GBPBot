
Installation
===========

Pr�requis
--------

* Python 3.8+
* Acc�s � un n�ud Ethereum/BSC (Infura, Alchemy, etc.)
* Un wallet avec des fonds suffisants pour les transactions

Installation rapide
-----------------

.. code-block:: bash

   # Cloner le d�p�t
   git clone https://github.com/votre-username/gbpbot.git
   cd gbpbot
   
   # Cr�er un environnement virtuel
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   
   # Installer les d�pendances
   pip install -r requirements.txt
   
   # Copier le fichier d'exemple de configuration
   cp .env.example .env
