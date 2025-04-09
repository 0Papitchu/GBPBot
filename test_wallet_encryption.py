#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour l'importation du module de chiffrement
"""

import os
import sys

# Ajouter le répertoire racine au chemin Python pour résoudre les importations relatives
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    print("Tentative d'importation directe...")
    from gbpbot.security.wallet_encryption import WalletEncryption
    print("Importation réussie via chemin d'importation direct!")
    
    # Tester les fonctionnalités
    encryption = WalletEncryption()
    print(f"Module chargé, cryptography disponible: {encryption.encryption_available}")
    
except ImportError as e:
    print(f"Erreur d'importation directe: {str(e)}")
    print("\nInformation de débogage:")
    print(f"sys.path: {sys.path}")
    
    try:
        print("\nTentative d'importation alternative...")
        # Importation absolue
        import gbpbot.security.wallet_encryption
        print("Importation absolue réussie!")
    except ImportError as e:
        print(f"Erreur d'importation absolue: {str(e)}")
        
        try:
            print("\nTentative d'importation par chemin relatif...")
            # Importation relative explicite
            import importlib.util
            module_path = os.path.join(current_dir, "gbpbot", "security", "wallet_encryption.py")
            
            if os.path.exists(module_path):
                spec = importlib.util.spec_from_file_location("wallet_encryption", module_path)
                if spec is not None and spec.loader is not None:
                    wallet_encryption = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(wallet_encryption)
                    print("Importation relative explicite réussie!")
                    print(f"Classes disponibles: {dir(wallet_encryption)}")
                else:
                    print(f"Erreur: impossible de créer un spec valide pour le module ({module_path})")
            else:
                print(f"Erreur: le fichier n'existe pas ({module_path})")
        except Exception as e:
            print(f"Erreur d'importation relative explicite: {str(e)}")

print("\nVérification de la structure de l'arborescence:")
for root, dirs, files in os.walk("gbpbot"):
    if "__init__.py" in files:
        print(f"Package trouvé: {root}")
        
print("\nFin du test d'importation.") 