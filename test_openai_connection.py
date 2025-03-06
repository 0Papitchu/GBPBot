#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de connexion à l'API OpenAI
===============================

Script simple pour tester la connexion à l'API OpenAI avec la clé configurée.
"""

import os
import json
import time
import sys

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("La bibliothèque OpenAI n'est pas installée.")
    print("Installez-la avec: pip install openai")
    sys.exit(1)

def get_api_key():
    """Récupère la clé API depuis le fichier de configuration."""
    config_path = os.path.join(os.path.expanduser("~"), ".gbpbot", "ai_config.json")
    
    if not os.path.exists(config_path):
        print(f"Erreur: Fichier de configuration non trouvé à {config_path}")
        return None
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        if "openai" in config and "api_key" in config["openai"]:
            return config["openai"]["api_key"]
        else:
            print("Erreur: Clé API non trouvée dans la configuration")
            return None
    
    except Exception as e:
        print(f"Erreur lors de la lecture de la configuration: {e}")
        return None

def get_model():
    """Récupère le modèle depuis le fichier de configuration."""
    config_path = os.path.join(os.path.expanduser("~"), ".gbpbot", "ai_config.json")
    
    if not os.path.exists(config_path):
        return "gpt-3.5-turbo"  # Modèle par défaut
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        if "openai" in config and "model" in config["openai"]:
            return config["openai"]["model"]
        else:
            return "gpt-3.5-turbo"  # Modèle par défaut
    
    except Exception:
        return "gpt-3.5-turbo"  # Modèle par défaut

def test_openai_connection():
    """Teste la connexion à l'API OpenAI."""
    print("=== Test de connexion à l'API OpenAI ===")
    
    # Récupérer la clé API
    api_key = get_api_key()
    if not api_key:
        return
    
    # Récupérer le modèle
    model = get_model()
    print(f"Modèle configuré: {model}")
    
    try:
        # Initialiser le client OpenAI
        print("Initialisation du client OpenAI...")
        client = OpenAI(api_key=api_key)
        
        # Tester la connexion en listant les modèles disponibles
        print("Test de connexion en listant les modèles disponibles...")
        models = client.models.list()
        print(f"Connexion réussie! {len(models.data)} modèles disponibles.")
        
        # Tester une génération simple
        prompt = "Génère un haiku sur le trading de crypto-monnaies."
        print(f"\nTest de génération avec le prompt: '{prompt}'")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Tu es un assistant spécialisé dans le trading crypto."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        # Afficher la réponse
        print("\nRéponse de l'API OpenAI:")
        print("-" * 50)
        print(response.choices[0].message.content)
        print("-" * 50)
        
        print("\nTest réussi! La connexion à l'API OpenAI fonctionne correctement.")
    
    except Exception as e:
        print(f"\nErreur lors du test de l'API OpenAI: {e}")
        print("\nVérifiez que votre clé API est correcte et que vous avez accès à l'API OpenAI.")

if __name__ == "__main__":
    test_openai_connection()
    print("\nTest terminé. Appuyez sur Entrée pour quitter...")
    input() 