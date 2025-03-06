#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Prompts pour l'IA
================================

Ce module gère les templates de prompts utilisés pour interagir avec les 
modèles d'IA. Il permet de charger, formater et personnaliser les prompts
en fonction des besoins spécifiques.
"""

import os
import logging
from typing import Dict, Any, Optional

# Configurer le logger
logger = logging.getLogger("gbpbot.ai.prompt_manager")

class PromptManager:
    """
    Gestionnaire de templates de prompts pour l'IA.
    
    Cette classe permet de charger et formater des templates de prompts
    pour différentes tâches d'IA (analyse de marché, analyse de code, etc.).
    """
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de prompts.
        
        Args:
            prompts_dir: Répertoire contenant les templates de prompts (optionnel)
        """
        # Utiliser le répertoire par défaut si non spécifié
        if prompts_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompts_dir = os.path.join(current_dir, "prompts")
        
        self.prompts_dir = prompts_dir
        self.templates = {}
        
        # Charger les templates disponibles
        self._load_templates()
    
    def _load_templates(self) -> None:
        """
        Charge les templates de prompts disponibles dans le répertoire spécifié.
        """
        if not os.path.exists(self.prompts_dir):
            logger.warning(f"Le répertoire de prompts {self.prompts_dir} n'existe pas.")
            return
        
        for filename in os.listdir(self.prompts_dir):
            if filename.endswith("_prompt.txt"):
                template_name = filename.replace("_prompt.txt", "")
                template_path = os.path.join(self.prompts_dir, filename)
                
                try:
                    with open(template_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        
                        # Extraire le template de prompt
                        if "PROMPT_TEMPLATE" in content:
                            # Trouver le template entre les guillemets triples
                            start = content.find("PROMPT_TEMPLATE = '''") + len("PROMPT_TEMPLATE = '''")
                            end = content.rfind("'''")
                            
                            if start > 0 and end > start:
                                template = content[start:end].strip()
                                self.templates[template_name] = template
                                logger.info(f"Template '{template_name}' chargé avec succès.")
                            else:
                                logger.warning(f"Format invalide pour le template '{template_name}'.")
                        else:
                            logger.warning(f"Variable PROMPT_TEMPLATE non trouvée dans '{filename}'.")
                
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du template '{template_name}': {e}")
    
    def get_template(self, template_name: str) -> Optional[str]:
        """
        Récupère un template de prompt par son nom.
        
        Args:
            template_name: Nom du template à récupérer
            
        Returns:
            Le template de prompt ou None si non trouvé
        """
        return self.templates.get(template_name)
    
    def format_prompt(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Formate un template de prompt avec les variables spécifiées.
        
        Args:
            template_name: Nom du template à formater
            **kwargs: Variables à injecter dans le template
            
        Returns:
            Le prompt formaté ou None si le template n'est pas trouvé
        """
        template = self.get_template(template_name)
        
        if template is None:
            logger.warning(f"Template '{template_name}' non trouvé.")
            return None
        
        try:
            # Formater le template avec les variables
            formatted_prompt = template.format(**kwargs)
            return formatted_prompt
        
        except KeyError as e:
            logger.error(f"Variable manquante dans le template '{template_name}': {e}")
            return None
        
        except Exception as e:
            logger.error(f"Erreur lors du formatage du template '{template_name}': {e}")
            return None
    
    def list_templates(self) -> Dict[str, str]:
        """
        Liste tous les templates disponibles.
        
        Returns:
            Dictionnaire des templates disponibles
        """
        return self.templates
    
    def get_template_names(self) -> list:
        """
        Récupère la liste des noms de templates disponibles.
        
        Returns:
            Liste des noms de templates
        """
        return list(self.templates.keys())


# Instance globale du gestionnaire de prompts
_prompt_manager = None

def get_prompt_manager(prompts_dir: Optional[str] = None) -> PromptManager:
    """
    Récupère l'instance globale du gestionnaire de prompts.
    
    Args:
        prompts_dir: Répertoire contenant les templates de prompts (optionnel)
        
    Returns:
        L'instance du gestionnaire de prompts
    """
    global _prompt_manager
    
    if _prompt_manager is None:
        _prompt_manager = PromptManager(prompts_dir)
    
    return _prompt_manager 