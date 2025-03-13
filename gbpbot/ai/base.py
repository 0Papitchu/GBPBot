"""
Module de base pour les fournisseurs d'IA de GBPBot
Définit les interfaces communes à tous les fournisseurs d'IA
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import logging

class LLMProvider(ABC):
    """
    Classe abstraite de base pour tous les fournisseurs de LLM (Large Language Models)
    Cette classe définit l'interface commune que tous les clients d'IA doivent implémenter
    """
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Génère une réponse textuelle à partir d'un prompt donné
        
        Args:
            prompt: Le prompt à envoyer au modèle
            max_tokens: Nombre maximum de tokens dans la réponse
            temperature: Contrôle de la randomisation (0-1)
            system_message: Message système optionnel
            kwargs: Paramètres supplémentaires spécifiques au fournisseur
            
        Returns:
            Texte généré par le modèle
        """
        pass
    
    @abstractmethod
    async def analyze_code(
        self,
        code: str,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse un morceau de code pour une tâche spécifique
        
        Args:
            code: Code à analyser
            task: Description de la tâche d'analyse
            kwargs: Paramètres supplémentaires
            
        Returns:
            Résultats de l'analyse sous forme de dictionnaire
        """
        pass
    
    @abstractmethod
    async def get_token_score(
        self,
        token_data: Dict[str, Any],
        **kwargs
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Attribue un score à un token crypto basé sur son potentiel et ses risques
        
        Args:
            token_data: Données du token à évaluer
            kwargs: Paramètres supplémentaires
            
        Returns:
            Tuple (score, détails) où score est entre 0 et 100
        """
        pass
    
    @abstractmethod
    async def analyze_market_trend(
        self,
        market_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse les tendances du marché crypto à partir des données fournies
        
        Args:
            market_data: Données du marché à analyser
            kwargs: Paramètres supplémentaires
            
        Returns:
            Analyse des tendances du marché
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nom du fournisseur d'IA"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le client est disponible et utilisable"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        """Liste des capacités supportées par ce fournisseur"""
        pass
    
    async def close(self):
        """Ferme proprement toutes les ressources utilisées par le client"""
        pass 