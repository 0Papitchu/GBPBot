#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour le chiffrement des wallets (importation directe)
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

# Ajouter le répertoire racine au chemin Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print("=== Test d'importation directe du module de chiffrement ===\n")

# Définir le répertoire de configuration de test
test_config_dir = os.path.join(current_dir, "config_test")
os.makedirs(test_config_dir, exist_ok=True)

# Créer des wallets de test
test_wallets = [
    {
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "private_key": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "chain": "avax"
    },
    {
        "address": "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5YPVFT",
        "private_key": "4q1tL7ybcDFMcMahfYEZf3X7Ko6XJP5vzCzNPEJELR1wQYhQmNa8aj5eVPTPk5vNz3N4s5uW6aQVk9BErN5dKJ1k",
        "chain": "sol"
    }
]

# Sauvegarde des wallets de test
test_wallets_path = os.path.join(test_config_dir, "wallets_test.json")
with open(test_wallets_path, 'w') as f:
    json.dump(test_wallets, f, indent=4)

print(f"Wallets de test créés dans: {test_wallets_path}")

try:
    print("\nImportation directe du module de chiffrement...")
    # Utiliser importlib.util pour éviter les importations indirectes
    module_path = os.path.join(current_dir, "gbpbot", "security", "wallet_encryption.py")
    
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Module introuvable: {module_path}")
    
    spec = importlib.util.spec_from_file_location("wallet_encryption", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de créer un spec valide pour {module_path}")
    
    wallet_encryption = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wallet_encryption)
    
    # Récupérer les classes nécessaires
    WalletEncryption = wallet_encryption.WalletEncryption
    encrypt_wallet_file = wallet_encryption.encrypt_wallet_file
    decrypt_wallet_file = wallet_encryption.decrypt_wallet_file
    
    print("\nCréation de l'instance WalletEncryption...")
    encryption = WalletEncryption(test_config_dir)
    print(f"Cryptography disponible: {encryption.encryption_available}")
    
    # Tester l'encryption des wallets
    print("\n1) Test de chiffrement des wallets")
    encrypted_wallets_path = os.path.join(test_config_dir, "wallets.encrypted.json")
    
    # Utiliser un mot de passe pour le test
    test_password = "testpassword123"
    print(f"Mot de passe de test: {test_password}")
    
    # Chiffrer les wallets
    success = encrypt_wallet_file(test_wallets_path, test_password, test_config_dir)
    
    if success:
        print(f"Chiffrement réussi! Fichier créé: {encrypted_wallets_path}")
        
        # Vérifier que le fichier existe
        if os.path.exists(encrypted_wallets_path):
            print("Fichier de wallets chiffrés trouvé.")
            
            # Afficher la structure du fichier chiffré
            with open(encrypted_wallets_path, 'r') as f:
                encrypted_data = json.load(f)
                print(f"\nStructure du fichier chiffré: {list(encrypted_data.keys())}")
                print(f"Nombre de wallets: {len(encrypted_data.get('wallets', []))}")
                print(f"Méthode de chiffrement: {encrypted_data.get('encryption_method')}")
            
            # Déchiffrer les wallets
            print("\n2) Test de déchiffrement des wallets")
            decrypted_wallets_path = os.path.join(test_config_dir, "wallets_decrypted.json")
            
            success = decrypt_wallet_file(encrypted_wallets_path, decrypted_wallets_path, test_password, test_config_dir)
            
            if success:
                print(f"Déchiffrement réussi! Fichier créé: {decrypted_wallets_path}")
                
                # Comparer les wallets déchiffrés avec les originaux
                with open(decrypted_wallets_path, 'r') as f:
                    decrypted_wallets = json.load(f)
                    
                if len(decrypted_wallets) == len(test_wallets):
                    print("\nLes wallets déchiffrés correspondent aux originaux en nombre.")
                    
                    # Vérifier quelques valeurs pour confirmer
                    match = True
                    for i, wallet in enumerate(decrypted_wallets):
                        if wallet.get("address") != test_wallets[i].get("address"):
                            match = False
                            print(f"Erreur: L'adresse du wallet {i+1} ne correspond pas.")
                        if wallet.get("private_key") != test_wallets[i].get("private_key"):
                            match = False
                            print(f"Erreur: La clé privée du wallet {i+1} ne correspond pas.")
                    
                    if match:
                        print("\n✅ TEST RÉUSSI: Les wallets déchiffrés correspondent parfaitement aux originaux!")
                    else:
                        print("\n❌ ÉCHEC: Les wallets déchiffrés ne correspondent pas aux originaux.")
                else:
                    print(f"\n❌ ÉCHEC: Nombre de wallets différent après déchiffrement ({len(decrypted_wallets)} vs {len(test_wallets)}).")
            else:
                print("\n❌ ÉCHEC: Déchiffrement des wallets échoué.")
        else:
            print(f"\n❌ ÉCHEC: Le fichier de wallets chiffrés n'a pas été créé: {encrypted_wallets_path}")
    else:
        print("\n❌ ÉCHEC: Chiffrement des wallets échoué.")
        
except Exception as e:
    print(f"\n❌ ERREUR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n=== Fin du test ===") 