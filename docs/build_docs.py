#!/usr/bin/env python3
"""
Script pour g�n�rer la documentation HTML.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    """Ex�cute une commande shell et affiche la sortie."""
    print(f"Ex�cution de la commande: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, cwd=cwd, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'ex�cution de la commande: {e}")
        print(f"Sortie d'erreur: {e.stderr}")
        return False

def main():
    """Fonction principale."""
    # G�n�rer la documentation automatique
    print("G�n�ration de la documentation automatique...")
    run_command("python generate_autodoc.py", cwd=Path.cwd())
    
    # G�n�rer la documentation HTML
    print("G�n�ration de la documentation HTML...")
    if sys.platform == "win32":
        run_command("make.bat html", cwd=Path.cwd())
    else:
        run_command("make html", cwd=Path.cwd())
    
    # Afficher le chemin vers la documentation g�n�r�e
    build_dir = Path.cwd() / "build" / "html"
    print(f"\nDocumentation g�n�r�e avec succ�s dans: {build_dir}")
    print(f"Ouvrez {build_dir / 'index.html'} dans votre navigateur pour la consulter.")

if __name__ == "__main__":
    main()
