#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration et Test de l'API OpenAI pour GBPBot
================================================

Ce script permet de configurer rapidement la clé API OpenAI pour GBPBot
et de tester la connexion pour vérifier que tout fonctionne correctement.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Configurer le logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gbpbot.setup_openai")

def main() -> None:
    """
    Point d'entrée principal du script.
    """
    parser = argparse.ArgumentParser(
        description="Configuration et test de l'API OpenAI pour GBPBot"
    )
    
    parser.add_argument(
        "--key", 
        type=str, 
        help="Clé API OpenAI (si non fournie, elle sera demandée)"
    )
    
    parser.add_argument(
        "--model", 
        type=str, 
        default="gpt-3.5-turbo",
        help="Modèle OpenAI à utiliser (défaut: gpt-3.5-turbo)"
    )
    
    parser.add_argument(
        "--test-only", 
        action="store_true",
        help="Uniquement tester la connexion sans configurer la clé"
    )
    
    args = parser.parse_args()
    
    # Ajouter le répertoire du projet au path pour les imports
    project_root = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, project_root)
    
    try:
        # Importer les modules nécessaires
        from gbpbot.ai.config import get_ai_config
        
        # Configurer la clé API si demandé
        if not args.test_only:
            api_key = args.key
            
            # Si la clé n'est pas fournie en argument, la demander
            if not api_key:
                print("\n=== Configuration de la clé API OpenAI pour GBPBot ===")
                print("La clé API sera stockée de manière sécurisée dans ~/.gbpbot/ai_config.json")
                api_key = input("Entrez votre clé API OpenAI: ").strip()
            
            if not api_key:
                logger.error("Aucune clé API fournie. Configuration annulée.")
                return
            
            # Stocker la clé
            config = get_ai_config()
            config.set_openai_api_key(api_key)
            config.set("openai", "model", args.model)
            
            logger.info(f"Clé API OpenAI configurée avec succès. Modèle par défaut: {args.model}")
        
        # Tester la connexion
        print("\n=== Test de la connexion à l'API OpenAI ===")
        
        # Importer le module de test
        from gbpbot.ai.test_openai import test_openai_connection
        
        # Lancer le test
        test_openai_connection(args.model)
    
    except ImportError as e:
        logger.error(f"Erreur d'importation: {e}")
        print("\nAssurez-vous que le projet GBPBot est correctement installé.")
        print("Vous pouvez l'installer avec: pip install -e .")
    
    except Exception as e:
        logger.error(f"Erreur lors de la configuration/test: {e}")
        print(f"\nUne erreur est survenue: {e}")

if __name__ == "__main__":
    main() 