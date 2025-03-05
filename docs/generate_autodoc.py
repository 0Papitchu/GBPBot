#!/usr/bin/env python3
"""
Script pour g�n�rer automatiquement la documentation � partir des docstrings.
"""

import os
import sys
import inspect
import importlib
from pathlib import Path

def generate_module_doc(module_name, output_dir):
    """G�n�re la documentation pour un module."""
    try:
        # Importer le module
        module = importlib.import_module(module_name)
        
        # Cr�er le fichier RST
        output_path = Path(output_dir) / f"{module_name}.rst"
        
        with open(output_path, "w") as f:
            # �crire l'en-t�te
            f.write(f"{module_name}\n")
            f.write("=" * len(module_name) + "\n\n")
            
            # �crire la directive automodule
            f.write(f".. automodule:: {module_name}\n")
            f.write("   :members:\n")
            f.write("   :undoc-members:\n")
            f.write("   :show-inheritance:\n\n")
            
            # Documenter les classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module_name:
                    f.write(f"{name}\n")
                    f.write("-" * len(name) + "\n\n")
                    f.write(f".. autoclass:: {module_name}.{name}\n")
                    f.write("   :members:\n")
                    f.write("   :undoc-members:\n")
                    f.write("   :show-inheritance:\n\n")
            
            # Documenter les fonctions
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if obj.__module__ == module_name:
                    f.write(f"{name}\n")
                    f.write("-" * len(name) + "\n\n")
                    f.write(f".. autofunction:: {module_name}.{name}\n\n")
        
        print(f"Documentation g�n�r�e pour {module_name} dans {output_path}")
        return True
    
    except ImportError as e:
        print(f"Erreur lors de l'importation du module {module_name}: {e}")
        return False
    except Exception as e:
        print(f"Erreur lors de la g�n�ration de la documentation pour {module_name}: {e}")
        return False

def main():
    """Fonction principale."""
    # Liste des modules � documenter
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
    
    # R�pertoire de sortie
    output_dir = Path("docs") / "source" / "modules"
    os.makedirs(output_dir, exist_ok=True)
    
    # G�n�rer la documentation pour chaque module
    for module in modules:
        generate_module_doc(module, output_dir)
    
    # Mettre � jour le fichier index.rst des modules
    with open(output_dir / "index.rst", "w") as f:
        f.write("Modules\n")
        f.write("=======\n\n")
        f.write(".. toctree::\n")
        f.write("   :maxdepth: 2\n\n")
        
        for module in modules:
            f.write(f"   {module}\n")

if __name__ == "__main__":
    main()
