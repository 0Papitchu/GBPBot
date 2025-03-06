#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de l'API OpenAI
===================

Script pour tester la connexion à l'API OpenAI et vérifier que la clé API
est correctement configurée.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Ajouter le répertoire parent au path pour les imports relatifs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gbpbot.ai.config import get_ai_config
from gbpbot.ai.openai_client import OpenAIClient

# Configurer le logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gbpbot.ai.test_openai")

def test_openai_connection(model: Optional[str] = None) -> None:
    """
    Teste la connexion à l'API OpenAI.
    
    Args:
        model: Le modèle à utiliser pour le test (optionnel)
    """
    config = get_ai_config()
    api_key = config.get_openai_api_key()
    
    if not api_key:
        logger.error("Aucune clé API OpenAI configurée.")
        print("\nVeuillez configurer votre clé API avec la commande:")
        print("python -m gbpbot.ai.setup_api_keys --openai")
        return
    
    # Utiliser le modèle spécifié ou celui de la configuration
    model_to_use = model or config.get("openai", "model", "gpt-3.5-turbo")
    
    try:
        print(f"\nTest de connexion à l'API OpenAI avec le modèle {model_to_use}...")
        client = OpenAIClient(api_key=api_key, model=model_to_use)
        
        # Vérifier que le client est disponible
        if not client.is_available:
            logger.error("Le client OpenAI n'est pas disponible.")
            return
        
        # Tester une génération simple
        prompt = "Génère un haiku sur le trading de crypto-monnaies."
        print(f"\nPrompt de test: '{prompt}'")
        
        response = client.generate_text(
            prompt=prompt,
            max_tokens=100,
            temperature=0.7
        )
        
        print("\nRéponse de l'API OpenAI:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        print("\nTest réussi! La connexion à l'API OpenAI fonctionne correctement.")
        
    except Exception as e:
        logger.error(f"Erreur lors du test de l'API OpenAI: {e}")
        print(f"\nLe test a échoué avec l'erreur: {e}")
        print("\nVérifiez que votre clé API est correcte et que vous avez accès à l'API OpenAI.")

def main() -> None:
    """
    Point d'entrée principal du script.
    """
    parser = argparse.ArgumentParser(description="Test de l'API OpenAI pour GBPBot")
    
    parser.add_argument("--model", type=str, help="Modèle OpenAI à utiliser pour le test")
    
    args = parser.parse_args()
    
    test_openai_connection(args.model)

if __name__ == "__main__":
    main() 