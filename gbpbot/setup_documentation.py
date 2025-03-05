#!/usr/bin/env python3
"""
Script pour initialiser et configurer la documentation Sphinx pour GBPBot.
Ce script crée la structure de base de la documentation et configure le thème ReadTheDocs.
"""

import os
import subprocess
import sys
from pathlib import Path

def create_directory_if_not_exists(directory):
    """Crée un répertoire s'il n'existe pas déjà."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Répertoire créé: {directory}")
    else:
        print(f"Le répertoire existe déjà: {directory}")

def run_command(command, cwd=None):
    """Exécute une commande shell et affiche la sortie."""
    print(f"Exécution de la commande: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, cwd=cwd, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande: {e}")
        print(f"Sortie d'erreur: {e.stderr}")
        return False

def setup_sphinx():
    """Configure Sphinx pour la documentation."""
    # Créer le répertoire docs s'il n'existe pas
    docs_dir = Path("docs")
    create_directory_if_not_exists(docs_dir)
    
    # Vérifier si Sphinx est installé, sinon l'installer
    try:
        import sphinx
        print("Sphinx est déjà installé.")
    except ImportError:
        print("Installation de Sphinx et du thème ReadTheDocs...")
        run_command("pip install sphinx sphinx-rtd-theme")
    
    # Initialiser Sphinx si ce n'est pas déjà fait
    if not (docs_dir / "source").exists() or not (docs_dir / "Makefile").exists():
        print("Initialisation de Sphinx...")
        run_command("sphinx-quickstart --sep --project=GBPBot --author='GBPBot Team' --language=fr", cwd=docs_dir)
    else:
        print("Sphinx est déjà initialisé.")
    
    # Configurer le thème ReadTheDocs
    conf_py_path = docs_dir / "source" / "conf.py"
    if conf_py_path.exists():
        with open(conf_py_path, "r") as f:
            conf_content = f.read()
        
        # Vérifier si le thème est déjà configuré
        if "sphinx_rtd_theme" not in conf_content:
            print("Configuration du thème ReadTheDocs...")
            with open(conf_py_path, "a") as f:
                f.write("\n# Configuration du thème ReadTheDocs\n")
                f.write("import sphinx_rtd_theme\n")
                f.write("html_theme = 'sphinx_rtd_theme'\n")
                f.write("html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]\n")
                f.write("\n# Configuration pour l'autodoc\n")
                f.write("extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.napoleon']\n")
                f.write("autodoc_member_order = 'bysource'\n")
                f.write("autodoc_typehints = 'description'\n")
        else:
            print("Le thème ReadTheDocs est déjà configuré.")
    else:
        print(f"Erreur: Le fichier {conf_py_path} n'existe pas.")
        return False
    
    return True

def create_index_rst():
    """Crée ou met à jour le fichier index.rst."""
    index_path = Path("docs") / "source" / "index.rst"
    
    index_content = """
Documentation de GBPBot
======================

.. toctree::
   :maxdepth: 2
   :caption: Sommaire

   introduction
   installation
   configuration
   utilisation
   api_reference
   modules/index
   maintenance
   faq
   contributeurs

Indices et tables
================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""
    
    with open(index_path, "w") as f:
        f.write(index_content)
    
    print(f"Fichier {index_path} créé/mis à jour.")

def create_rst_files():
    """Crée les fichiers RST de base pour la documentation."""
    source_dir = Path("docs") / "source"
    
    # Créer le répertoire modules s'il n'existe pas
    modules_dir = source_dir / "modules"
    create_directory_if_not_exists(modules_dir)
    
    # Fichiers RST à créer
    rst_files = {
        "introduction.rst": """
Introduction
===========

GBPBot est un système de trading automatisé pour les crypto-monnaies, spécialisé dans le sniping de nouveaux tokens et l'arbitrage.

Fonctionnalités principales
--------------------------

* **Sniping de mempool**: Détecte et exécute des transactions sur les nouvelles paires de trading.
* **Optimisation du gas**: Calcule les prix de gas optimaux pour les transactions.
* **Détection de bundles**: Analyse les transactions groupées pour détecter les manipulations.
* **Interface web**: Contrôle et surveillance du bot via une interface web intuitive.
* **API REST**: Intégration avec d'autres systèmes via une API REST sécurisée.
* **Modes multiples**: Simulation, testnet et production pour tester vos stratégies avant de les déployer.
""",
        
        "installation.rst": """
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
   source venv/bin/activate  # Sur Windows: venv\\Scripts\\activate
   
   # Installer les dépendances
   pip install -r requirements.txt
   
   # Copier le fichier d'exemple de configuration
   cp .env.example .env
""",
        
        "configuration.rst": """
Configuration
============

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
""",
        
        "utilisation.rst": """
Utilisation
==========

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
""",
        
        "api_reference.rst": """
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
""",
        
        "maintenance.rst": """
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
""",
        
        "faq.rst": """
FAQ
===

Questions générales
----------------

Q: Le bot est-il sûr à utiliser?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Oui, le bot est conçu avec la sécurité comme priorité. Cependant, le trading de crypto-monnaies comporte toujours des risques. Commencez avec de petites sommes et en mode simulation.

Q: Puis-je utiliser le bot sur plusieurs chaînes?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Oui, le bot prend en charge plusieurs chaînes, dont Ethereum, BSC, Polygon, etc. Configurez les fournisseurs Web3 appropriés dans le fichier `.env`.

Questions techniques
-----------------

Q: Comment puis-je ajouter une nouvelle stratégie?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Créez un nouveau fichier dans `strategies/` et ajoutez-le à `config/strategies/`. Consultez la documentation technique pour plus de détails.
""",
        
        "contributeurs.rst": """
Contributeurs
============

Comment contribuer
----------------

1. Forker le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Commiter vos changements (`git commit -m 'Add some amazing feature'`)
4. Pousser vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

Mise à jour de la documentation
----------------------------

Pour mettre à jour la documentation:

.. code-block:: bash

   # Générer la documentation
   cd docs
   make html
""",
        
        "modules/index.rst": """
Modules
=======

.. toctree::
   :maxdepth: 2
   
   mempool_sniping
   gas_optimizer
   bundle_checker
   core
   api_server
   web_dashboard
""",
        
        "modules/mempool_sniping.rst": """
Mempool Sniping
==============

.. automodule:: mempool_sniping
   :members:
   :undoc-members:
   :show-inheritance:
""",
        
        "modules/gas_optimizer.rst": """
Gas Optimizer
============

.. automodule:: gas_optimizer
   :members:
   :undoc-members:
   :show-inheritance:
""",
        
        "modules/bundle_checker.rst": """
Bundle Checker
=============

.. automodule:: bundle_checker
   :members:
   :undoc-members:
   :show-inheritance:
""",
        
        "modules/core.rst": """
Core
====

.. automodule:: main
   :members:
   :undoc-members:
   :show-inheritance:
""",
        
        "modules/api_server.rst": """
API Server
=========

.. automodule:: api_server
   :members:
   :undoc-members:
   :show-inheritance:
""",
        
        "modules/web_dashboard.rst": """
Web Dashboard
============

.. automodule:: web_dashboard
   :members:
   :undoc-members:
   :show-inheritance:
"""
    }
    
    # Créer les fichiers RST
    for filename, content in rst_files.items():
        file_path = source_dir / filename
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Fichier {file_path} créé.")

def create_autodoc_script():
    """Crée un script pour générer automatiquement la documentation à partir des docstrings."""
    script_path = Path("docs") / "generate_autodoc.py"
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Script pour générer automatiquement la documentation à partir des docstrings.
\"\"\"

import os
import sys
import inspect
import importlib
from pathlib import Path

def generate_module_doc(module_name, output_dir):
    \"\"\"Génère la documentation pour un module.\"\"\"
    try:
        # Importer le module
        module = importlib.import_module(module_name)
        
        # Créer le fichier RST
        output_path = Path(output_dir) / f"{module_name}.rst"
        
        with open(output_path, "w") as f:
            # Écrire l'en-tête
            f.write(f"{module_name}\\n")
            f.write("=" * len(module_name) + "\\n\\n")
            
            # Écrire la directive automodule
            f.write(f".. automodule:: {module_name}\\n")
            f.write("   :members:\\n")
            f.write("   :undoc-members:\\n")
            f.write("   :show-inheritance:\\n\\n")
            
            # Documenter les classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module_name:
                    f.write(f"{name}\\n")
                    f.write("-" * len(name) + "\\n\\n")
                    f.write(f".. autoclass:: {module_name}.{name}\\n")
                    f.write("   :members:\\n")
                    f.write("   :undoc-members:\\n")
                    f.write("   :show-inheritance:\\n\\n")
            
            # Documenter les fonctions
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if obj.__module__ == module_name:
                    f.write(f"{name}\\n")
                    f.write("-" * len(name) + "\\n\\n")
                    f.write(f".. autofunction:: {module_name}.{name}\\n\\n")
        
        print(f"Documentation générée pour {module_name} dans {output_path}")
        return True
    
    except ImportError as e:
        print(f"Erreur lors de l'importation du module {module_name}: {e}")
        return False
    except Exception as e:
        print(f"Erreur lors de la génération de la documentation pour {module_name}: {e}")
        return False

def main():
    \"\"\"Fonction principale.\"\"\"
    # Liste des modules à documenter
    modules = [
        "mempool_sniping",
        "gas_optimizer",
        "bundle_checker",
        "main",
        "api_server",
        "web_dashboard",
        "security_config",
        "monitor_production",
        "deploy_production"
    ]
    
    # Répertoire de sortie
    output_dir = Path("docs") / "source" / "modules"
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer la documentation pour chaque module
    for module in modules:
        generate_module_doc(module, output_dir)
    
    # Mettre à jour le fichier index.rst des modules
    with open(output_dir / "index.rst", "w") as f:
        f.write("Modules\\n")
        f.write("=======\\n\\n")
        f.write(".. toctree::\\n")
        f.write("   :maxdepth: 2\\n\\n")
        
        for module in modules:
            f.write(f"   {module}\\n")

if __name__ == "__main__":
    main()
"""
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Rendre le script exécutable
    os.chmod(script_path, 0o755)
    
    print(f"Script {script_path} créé.")

def create_pre_commit_hook():
    """Crée un hook pre-commit pour vérifier si la documentation est à jour."""
    hooks_dir = Path(".git") / "hooks"
    
    # Vérifier si le répertoire .git/hooks existe
    if not hooks_dir.exists():
        print(f"Erreur: Le répertoire {hooks_dir} n'existe pas.")
        print("Assurez-vous que vous êtes dans un dépôt Git.")
        return False
    
    pre_commit_path = hooks_dir / "pre-commit"
    
    pre_commit_content = """#!/bin/bash
# Hook pre-commit pour vérifier si la documentation est à jour

echo "Vérification de la documentation..."

# Générer la documentation
cd docs
python generate_autodoc.py
cd ..

# Vérifier s'il y a des modifications dans la documentation
if git diff --quiet docs/source/modules/; then
    echo "La documentation est à jour."
    exit 0
else
    echo "La documentation n'est pas à jour!"
    echo "Veuillez mettre à jour la documentation avant de committer."
    echo "Exécutez: cd docs && python generate_autodoc.py && cd .."
    exit 1
fi
"""
    
    with open(pre_commit_path, "w") as f:
        f.write(pre_commit_content)
    
    # Rendre le hook exécutable
    os.chmod(pre_commit_path, 0o755)
    
    print(f"Hook pre-commit {pre_commit_path} créé.")
    return True

def create_build_script():
    """Crée un script pour générer la documentation HTML."""
    script_path = Path("docs") / "build_docs.py"
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Script pour générer la documentation HTML.
\"\"\"

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    \"\"\"Exécute une commande shell et affiche la sortie.\"\"\"
    print(f"Exécution de la commande: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, cwd=cwd, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande: {e}")
        print(f"Sortie d'erreur: {e.stderr}")
        return False

def main():
    \"\"\"Fonction principale.\"\"\"
    # Générer la documentation automatique
    print("Génération de la documentation automatique...")
    run_command("python generate_autodoc.py", cwd=Path.cwd())
    
    # Générer la documentation HTML
    print("Génération de la documentation HTML...")
    if sys.platform == "win32":
        run_command("make.bat html", cwd=Path.cwd())
    else:
        run_command("make html", cwd=Path.cwd())
    
    # Afficher le chemin vers la documentation générée
    build_dir = Path.cwd() / "build" / "html"
    print(f"\\nDocumentation générée avec succès dans: {build_dir}")
    print(f"Ouvrez {build_dir / 'index.html'} dans votre navigateur pour la consulter.")

if __name__ == "__main__":
    main()
"""
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Rendre le script exécutable
    os.chmod(script_path, 0o755)
    
    print(f"Script {script_path} créé.")

def main():
    """Fonction principale."""
    print("Configuration de la documentation Sphinx pour GBPBot...")
    
    # Configurer Sphinx
    if not setup_sphinx():
        print("Erreur lors de la configuration de Sphinx.")
        return
    
    # Créer les fichiers RST
    create_index_rst()
    create_rst_files()
    
    # Créer le script pour générer la documentation automatique
    create_autodoc_script()
    
    # Créer le hook pre-commit
    create_pre_commit_hook()
    
    # Créer le script pour générer la documentation HTML
    create_build_script()
    
    print("\nConfiguration de la documentation terminée avec succès!")
    print("Pour générer la documentation HTML, exécutez:")
    print("cd docs && python build_docs.py")

if __name__ == "__main__":
    main() 