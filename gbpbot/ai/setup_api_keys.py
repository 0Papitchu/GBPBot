#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration des Clés API pour l'IA
====================================

Script utilitaire pour configurer les clés API et autres paramètres
nécessaires pour les intégrations d'IA dans GBPBot.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Ajouter le répertoire parent au path pour les imports relatifs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gbpbot.ai.config import get_ai_config

# Configurer le logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gbpbot.ai.setup")

def setup_openai_api_key(api_key: Optional[str] = None) -> None:
    """
    Configure la clé API OpenAI.
    
    Args:
        api_key: La clé API OpenAI (demandée si non fournie)
    """
    config = get_ai_config()
    
    # Si la clé n'est pas fournie, la demander
    if not api_key:
        print("\n=== Configuration de la clé API OpenAI ===")
        print("La clé API sera stockée de manière sécurisée dans ~/.gbpbot/ai_config.json")
        print("Vous pouvez aussi définir la variable d'environnement OPENAI_API_KEY")
        api_key = input("Entrez votre clé API OpenAI: ").strip()
    
    if not api_key:
        logger.error("Aucune clé API fournie. Configuration annulée.")
        return
    
    # Stocker la clé
    config.set_openai_api_key(api_key)
    logger.info("Clé API OpenAI configurée avec succès.")
    
    # Configurer le modèle par défaut
    model = input("Modèle par défaut (laissez vide pour 'gpt-3.5-turbo'): ").strip()
    if model:
        config.set("openai", "model", model)
        logger.info(f"Modèle par défaut configuré: {model}")
    else:
        config.set("openai", "model", "gpt-3.5-turbo")
        logger.info("Modèle par défaut configuré: gpt-3.5-turbo")

def setup_llama_model(model_path: Optional[str] = None) -> None:
    """
    Configure le chemin vers le modèle LLaMA.
    
    Args:
        model_path: Le chemin vers le modèle LLaMA (demandé si non fourni)
    """
    config = get_ai_config()
    
    # Si le chemin n'est pas fourni, le demander
    if not model_path:
        print("\n=== Configuration du modèle LLaMA ===")
        print("Le chemin sera stocké de manière sécurisée dans ~/.gbpbot/ai_config.json")
        model_path = input("Entrez le chemin vers le modèle LLaMA: ").strip()
    
    if not model_path:
        logger.error("Aucun chemin fourni. Configuration annulée.")
        return
    
    # Vérifier que le chemin existe
    if not os.path.exists(model_path):
        logger.warning(f"Le chemin {model_path} n'existe pas. Assurez-vous qu'il est correct.")
    
    # Stocker le chemin
    config.set_llama_model_path(model_path)
    logger.info("Chemin du modèle LLaMA configuré avec succès.")
    
    # Configurer la quantification
    quantization = input("Quantification (4bit, 8bit, none, laissez vide pour '4bit'): ").strip()
    if quantization:
        config.set("llama", "quantization", quantization)
        logger.info(f"Quantification configurée: {quantization}")
    else:
        config.set("llama", "quantization", "4bit")
        logger.info("Quantification configurée: 4bit")

def show_current_config() -> None:
    """
    Affiche la configuration actuelle.
    """
    config = get_ai_config()
    
    print("\n=== Configuration Actuelle ===")
    
    # OpenAI
    openai_key = config.get_openai_api_key()
    if openai_key:
        # Masquer la clé pour la sécurité
        masked_key = openai_key[:4] + "..." + openai_key[-4:] if len(openai_key) > 8 else "***"
        print(f"OpenAI API Key: {masked_key}")
    else:
        print("OpenAI API Key: Non configurée")
    
    openai_model = config.get("openai", "model")
    print(f"OpenAI Model: {openai_model}")
    
    # LLaMA
    llama_path = config.get_llama_model_path()
    if llama_path:
        print(f"LLaMA Model Path: {llama_path}")
    else:
        print("LLaMA Model Path: Non configuré")
    
    llama_quant = config.get("llama", "quantization")
    print(f"LLaMA Quantization: {llama_quant}")
    
    print("\nPour modifier ces paramètres, utilisez les options --openai ou --llama")

def main() -> None:
    """
    Point d'entrée principal du script.
    """
    parser = argparse.ArgumentParser(description="Configuration des clés API pour GBPBot")
    
    parser.add_argument("--openai", action="store_true", help="Configurer la clé API OpenAI")
    parser.add_argument("--openai-key", type=str, help="Clé API OpenAI (optionnel)")
    
    parser.add_argument("--llama", action="store_true", help="Configurer le modèle LLaMA")
    parser.add_argument("--llama-path", type=str, help="Chemin vers le modèle LLaMA (optionnel)")
    
    parser.add_argument("--show", action="store_true", help="Afficher la configuration actuelle")
    
    args = parser.parse_args()
    
    # Si aucune option n'est spécifiée, afficher l'aide
    if not (args.openai or args.llama or args.show):
        parser.print_help()
        return
    
    # Afficher la configuration actuelle
    if args.show:
        show_current_config()
    
    # Configurer OpenAI
    if args.openai:
        setup_openai_api_key(args.openai_key)
    
    # Configurer LLaMA
    if args.llama:
        setup_llama_model(args.llama_path)
    
    # Si une configuration a été effectuée, afficher la nouvelle configuration
    if args.openai or args.llama:
        print("\nNouvelle configuration:")
        show_current_config()

if __name__ == "__main__":
    main() 