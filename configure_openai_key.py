#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration de la clé API OpenAI
=================================

Script simple pour configurer la clé API OpenAI pour GBPBot.
Ce script crée directement le fichier de configuration sans dépendre
des autres modules du projet.
"""

import os
import json
import time
from pathlib import Path

def main():
    print("=== Configuration de la clé API OpenAI pour GBPBot ===")
    time.sleep(1)
    
    # Clé API à configurer
    api_key = "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"
    model = "gpt-3.5-turbo"  # Modèle plus accessible
    
    print(f"Modèle sélectionné: {model}")
    time.sleep(1)
    
    # Chemin du fichier de configuration
    config_dir = os.path.join(os.path.expanduser("~"), ".gbpbot")
    config_path = os.path.join(config_dir, "ai_config.json")
    
    print(f"Répertoire de configuration: {config_dir}")
    time.sleep(1)
    
    # Créer le répertoire si nécessaire
    Path(config_dir).mkdir(parents=True, exist_ok=True)
    print(f"Répertoire créé ou existant: {os.path.exists(config_dir)}")
    time.sleep(1)
    
    # Créer ou charger la configuration
    if os.path.exists(config_path):
        print(f"Fichier de configuration existant trouvé: {config_path}")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            print("Configuration existante chargée avec succès.")
        except Exception as e:
            print(f"Erreur lors de la lecture de la configuration existante: {e}")
            config = {}
    else:
        print("Aucun fichier de configuration existant. Création d'une nouvelle configuration.")
        config = {}
    
    time.sleep(1)
    
    # Mettre à jour la configuration
    if "openai" not in config:
        config["openai"] = {}
    
    config["openai"]["api_key"] = api_key
    config["openai"]["model"] = model
    
    print("Configuration mise à jour avec la clé API et le modèle.")
    time.sleep(1)
    
    # Sauvegarder la configuration
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        
        # Restreindre les permissions du fichier (lecture/écriture uniquement pour l'utilisateur)
        try:
            os.chmod(config_path, 0o600)
            print("Permissions du fichier restreintes pour plus de sécurité.")
        except Exception as e:
            print(f"Avertissement: Impossible de restreindre les permissions du fichier: {e}")
        
        print(f"Clé API OpenAI configurée avec succès pour le modèle {model}")
        print(f"La configuration est stockée dans: {config_path}")
    
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la configuration: {e}")
    
    # Vérifier que le fichier a bien été créé
    if os.path.exists(config_path):
        print(f"Vérification: Le fichier de configuration existe à {config_path}")
        print(f"Taille du fichier: {os.path.getsize(config_path)} octets")
    else:
        print("Erreur: Le fichier de configuration n'a pas été créé.")
    
    print("\nConfiguration terminée. Appuyez sur Entrée pour quitter...")
    input()

if __name__ == "__main__":
    main() 