#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de prompts pour les modèles d'IA
============================================

Ce module fournit des fonctionnalités pour charger, formater et gérer
les prompts utilisés par les modèles d'IA dans le GBPBot.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Configuration du logger
logger = logging.getLogger(__name__)

class PromptManager:
    """
    Gestionnaire de prompts pour les modèles d'IA
    
    Cette classe permet de charger des prompts depuis des fichiers,
    de les formater avec des variables et de les gérer pour différents
    cas d'utilisation.
    """
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de prompts
        
        Args:
            prompts_dir: Répertoire contenant les fichiers de prompts
        """
        # Déterminer le répertoire des prompts
        if prompts_dir is None:
            # Utiliser le répertoire par défaut
            module_dir = os.path.dirname(os.path.abspath(__file__))
            self.prompts_dir = os.path.join(module_dir, "prompts")
        else:
            self.prompts_dir = prompts_dir
        
        # S'assurer que le répertoire existe
        os.makedirs(self.prompts_dir, exist_ok=True)
        
        # Charger les prompts
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """
        Charge tous les prompts depuis le répertoire des prompts
        """
        try:
            # Parcourir tous les fichiers JSON dans le répertoire
            for file_path in Path(self.prompts_dir).glob("*.json"):
                try:
                    # Charger le fichier JSON
                    with open(file_path, "r", encoding="utf-8") as f:
                        prompt_data = json.load(f)
                    
                    # Ajouter le prompt au dictionnaire
                    prompt_name = file_path.stem
                    self.prompts[prompt_name] = prompt_data
                    logger.debug(f"Prompt '{prompt_name}' chargé depuis {file_path}")
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du prompt {file_path}: {e}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des prompts: {e}")
    
    def get_prompt(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un prompt par son nom
        
        Args:
            prompt_name: Nom du prompt à récupérer
            
        Returns:
            Dict[str, Any]: Données du prompt ou None si non trouvé
        """
        return self.prompts.get(prompt_name)
    
    def format_prompt(self, prompt_name: str, **kwargs) -> Optional[str]:
        """
        Formate un prompt avec les variables fournies
        
        Args:
            prompt_name: Nom du prompt à formater
            **kwargs: Variables à insérer dans le prompt
            
        Returns:
            str: Prompt formaté ou None si non trouvé
        """
        prompt_data = self.get_prompt(prompt_name)
        if not prompt_data or "template" not in prompt_data:
            logger.error(f"Prompt '{prompt_name}' non trouvé ou invalide")
            return None
        
        try:
            # Formater le template avec les variables
            template = prompt_data["template"]
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Variable manquante dans le prompt '{prompt_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du formatage du prompt '{prompt_name}': {e}")
            return None
    
    def get_system_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Récupère le message système associé à un prompt
        
        Args:
            prompt_name: Nom du prompt
            
        Returns:
            str: Message système ou None si non trouvé
        """
        prompt_data = self.get_prompt(prompt_name)
        if not prompt_data:
            return None
        
        return prompt_data.get("system_message")
    
    def create_prompt(self, prompt_name: str, template: str, system_message: Optional[str] = None, 
                     description: Optional[str] = None, save: bool = True) -> bool:
        """
        Crée un nouveau prompt
        
        Args:
            prompt_name: Nom du prompt
            template: Template du prompt
            system_message: Message système optionnel
            description: Description du prompt
            save: Sauvegarder le prompt dans un fichier
            
        Returns:
            bool: True si le prompt a été créé avec succès
        """
        # Créer les données du prompt
        prompt_data = {
            "template": template,
            "description": description or f"Prompt {prompt_name}",
            "created_at": import_time_module_and_get_iso_time()
        }
        
        if system_message:
            prompt_data["system_message"] = system_message
        
        # Ajouter le prompt au dictionnaire
        self.prompts[prompt_name] = prompt_data
        
        # Sauvegarder le prompt si demandé
        if save:
            return self.save_prompt(prompt_name)
        
        return True
    
    def save_prompt(self, prompt_name: str) -> bool:
        """
        Sauvegarde un prompt dans un fichier
        
        Args:
            prompt_name: Nom du prompt à sauvegarder
            
        Returns:
            bool: True si le prompt a été sauvegardé avec succès
        """
        prompt_data = self.get_prompt(prompt_name)
        if not prompt_data:
            logger.error(f"Prompt '{prompt_name}' non trouvé")
            return False
        
        try:
            # Créer le chemin du fichier
            file_path = os.path.join(self.prompts_dir, f"{prompt_name}.json")
            
            # Sauvegarder le prompt dans un fichier JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(prompt_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Prompt '{prompt_name}' sauvegardé dans {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du prompt '{prompt_name}': {e}")
            return False
    
    def list_prompts(self) -> List[str]:
        """
        Liste tous les prompts disponibles
        
        Returns:
            List[str]: Liste des noms de prompts
        """
        return list(self.prompts.keys())
    
    def create_default_prompts(self) -> None:
        """
        Crée les prompts par défaut s'ils n'existent pas
        """
        # Prompt pour l'analyse de contrat
        if "contract_analysis" not in self.prompts:
            self.create_prompt(
                "contract_analysis",
                template="""
                Analyse le contrat suivant et identifie les risques potentiels:
                
                ```solidity
                {contract_code}
                ```
                
                Réponds au format JSON avec les champs suivants:
                - risk_score: note de 0 à 100 (100 = très risqué)
                - rug_pull_risk: note de 0 à 100
                - honeypot_risk: note de 0 à 100
                - backdoor_risk: note de 0 à 100
                - issues: liste des problèmes identifiés
                - explanation: explication détaillée
                """,
                system_message="Tu es un expert en sécurité des contrats intelligents. Ton rôle est d'analyser les contrats pour détecter les risques et vulnérabilités.",
                description="Analyse de contrat intelligent pour détecter les risques"
            )
        
        # Prompt pour l'analyse de token
        if "token_analysis" not in self.prompts:
            self.create_prompt(
                "token_analysis",
                template="""
                Analyse les données suivantes d'un token et évalue son potentiel:
                
                {token_info}
                
                Réponds au format JSON avec les champs suivants:
                - potential_score: note de 0 à 100 (100 = très prometteur)
                - pump_probability: probabilité de 0 à 100
                - risk_level: "low", "medium", "high" ou "extreme"
                - recommendation: "buy", "hold", "sell" ou "avoid"
                - reasoning: explication détaillée
                """,
                system_message="Tu es un expert en analyse de tokens et cryptomonnaies. Ton rôle est d'évaluer le potentiel et les risques des tokens.",
                description="Analyse de token pour évaluer son potentiel"
            )
        
        # Prompt pour l'analyse de marché
        if "market_sentiment" not in self.prompts:
            self.create_prompt(
                "market_sentiment",
                template="""
                Analyse les données suivantes du marché et détermine le sentiment général:
                
                {market_info}
                
                Réponds au format JSON avec les champs suivants:
                - sentiment: "bullish", "neutral" ou "bearish"
                - confidence: niveau de confiance de 0 à 100
                - market_phase: "accumulation", "markup", "distribution" ou "markdown"
                - recommendation: recommandation générale
                - reasoning: explication détaillée
                """,
                system_message="Tu es un expert en analyse de marché crypto. Ton rôle est d'évaluer le sentiment du marché et de fournir des recommandations.",
                description="Analyse du sentiment du marché"
            )


def import_time_module_and_get_iso_time() -> str:
    """
    Importe le module time et retourne la date/heure actuelle au format ISO
    
    Returns:
        str: Date/heure au format ISO
    """
    import datetime
    return datetime.datetime.now().isoformat()


# Instance globale du gestionnaire de prompts
_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager(prompts_dir: Optional[str] = None) -> PromptManager:
    """
    Récupère l'instance globale du gestionnaire de prompts
    
    Args:
        prompts_dir: Répertoire contenant les fichiers de prompts
        
    Returns:
        PromptManager: Instance du gestionnaire de prompts
    """
    global _prompt_manager
    
    if _prompt_manager is None:
        _prompt_manager = PromptManager(prompts_dir)
        # Créer les prompts par défaut
        _prompt_manager.create_default_prompts()
    
    return _prompt_manager 