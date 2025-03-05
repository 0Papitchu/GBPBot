#!/usr/bin/env python3
"""
Script pour vérifier les chemins de fichiers dans le projet GBPBot.
"""

import os

# Définir les fichiers à vérifier
FILES_TO_CHECK = [
    "gbpbot/strategies/mev.py",
    "gbpbot/strategies/scalping.py",
    "gbpbot/strategies/sniping.py",
    "gbpbot/strategies/token_detection.py",
    "gbpbot/core/mev_executor.py",
    "tests/test_arbitrage.py"
]

def main():
    """Fonction principale."""
    print("Vérification des chemins de fichiers...")
    
    # Obtenir le répertoire de travail actuel
    current_dir = os.getcwd()
    print(f"Répertoire de travail actuel: {current_dir}")
    
    # Vérifier les fichiers
    for file_path in FILES_TO_CHECK:
        absolute_path = os.path.join(current_dir, file_path)
        if os.path.exists(absolute_path):
            print(f"[OK] Le fichier existe: {file_path}")
            # Afficher les 15 premières lignes du fichier
            try:
                with open(absolute_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    first_lines = ''.join(lines[:15])
                print(f"Premières lignes (15):\n{first_lines}")
                
                # Rechercher les corrections spécifiques
                corrections = {
                    "gbpbot/strategies/mev.py": "from gbpbot.core.mev_executor import FlashbotsProvider",
                    "gbpbot/strategies/scalping.py": "from typing import FixtureFunction",
                    "gbpbot/strategies/sniping.py": "from typing import FixtureFunction",
                    "gbpbot/strategies/token_detection.py": "from typing import FixtureFunction",
                    "gbpbot/core/mev_executor.py": "baseFeePerGas = None",
                    "tests/test_arbitrage.py": "WAVAX = 'WAVAX'"
                }
                
                if file_path in corrections:
                    correction = corrections[file_path]
                    content = ''.join(lines)
                    if correction in content:
                        print(f"[OK] Correction trouvée: {correction}")
                    else:
                        print(f"[ERREUR] Correction non trouvée: {correction}")
                
            except Exception as e:
                print(f"[ERREUR] Erreur lors de la lecture du fichier: {str(e)}")
        else:
            print(f"[ERREUR] Le fichier n'existe pas: {file_path}")
            # Vérifier si le répertoire existe
            dir_path = os.path.dirname(absolute_path)
            if os.path.exists(dir_path):
                print(f"[OK] Le répertoire existe: {os.path.dirname(file_path)}")
                # Lister les fichiers dans le répertoire
                files = os.listdir(dir_path)
                print(f"Fichiers dans le répertoire: {files}")
            else:
                print(f"[ERREUR] Le répertoire n'existe pas: {os.path.dirname(file_path)}")
    
    print("Vérification terminée!")

if __name__ == "__main__":
    main() 