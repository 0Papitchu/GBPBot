#!/usr/bin/env python3
"""
Module d'exemple pour illustrer les docstrings correctement formatées pour Sphinx.

Ce module montre comment documenter les classes, méthodes et fonctions
pour que Sphinx puisse générer automatiquement une documentation de qualité.
"""

import time
from typing import Dict, List, Optional, Union, Tuple


class ExampleClass:
    """
    Classe d'exemple pour illustrer la documentation.
    
    Cette classe contient des méthodes d'exemple avec des docstrings
    bien formatées pour la génération automatique de documentation.
    
    Attributes:
        name (str): Nom de l'instance.
        config (Dict): Configuration de l'instance.
        is_active (bool): Indique si l'instance est active.
    """
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        Initialise une nouvelle instance de ExampleClass.
        
        Args:
            name: Nom de l'instance.
            config: Configuration optionnelle de l'instance.
                   Si None, une configuration par défaut sera utilisée.
        """
        self.name = name
        self.config = config or {"default": True}
        self.is_active = False
    
    def start(self) -> bool:
        """
        Démarre l'instance.
        
        Cette méthode active l'instance et effectue les initialisations nécessaires.
        
        Returns:
            bool: True si le démarrage a réussi, False sinon.
        
        Raises:
            RuntimeError: Si l'instance est déjà active.
        """
        if self.is_active:
            raise RuntimeError("L'instance est déjà active")
        
        # Logique de démarrage
        self.is_active = True
        return True
    
    def stop(self) -> bool:
        """
        Arrête l'instance.
        
        Cette méthode désactive l'instance et effectue les nettoyages nécessaires.
        
        Returns:
            bool: True si l'arrêt a réussi, False sinon.
        
        Raises:
            RuntimeError: Si l'instance n'est pas active.
        """
        if not self.is_active:
            raise RuntimeError("L'instance n'est pas active")
        
        # Logique d'arrêt
        self.is_active = False
        return True
    
    def get_status(self) -> Dict[str, Union[str, bool, int]]:
        """
        Obtient le statut actuel de l'instance.
        
        Returns:
            Dict[str, Union[str, bool, int]]: Dictionnaire contenant les informations de statut:
                - name (str): Nom de l'instance
                - is_active (bool): Indique si l'instance est active
                - uptime (int): Temps d'activité en secondes (0 si inactive)
        """
        return {
            "name": self.name,
            "is_active": self.is_active,
            "uptime": 0  # Dans un cas réel, calculer le temps d'activité
        }
    
    def process_data(self, data: List[Dict]) -> Tuple[int, List[Dict]]:
        """
        Traite les données fournies.
        
        Cette méthode analyse et transforme les données d'entrée.
        
        Args:
            data: Liste de dictionnaires contenant les données à traiter.
                 Chaque dictionnaire doit contenir au moins une clé 'id'.
        
        Returns:
            Tuple contenant:
                - Le nombre d'éléments traités
                - La liste des éléments traités
        
        Raises:
            ValueError: Si les données d'entrée sont invalides.
        """
        if not data:
            raise ValueError("Les données d'entrée ne peuvent pas être vides")
        
        processed_data = []
        for item in data:
            if 'id' not in item:
                raise ValueError("Chaque élément doit contenir une clé 'id'")
            
            # Logique de traitement
            processed_item = item.copy()
            processed_item['processed'] = True
            processed_item['timestamp'] = time.time()
            
            processed_data.append(processed_item)
        
        return len(processed_data), processed_data


def validate_config(config: Dict) -> bool:
    """
    Valide une configuration.
    
    Cette fonction vérifie si la configuration fournie est valide
    selon les règles définies.
    
    Args:
        config: Dictionnaire de configuration à valider.
    
    Returns:
        bool: True si la configuration est valide, False sinon.
    
    Examples:
        >>> validate_config({"api_key": "abc123", "max_retries": 3})
        True
        >>> validate_config({})
        False
    """
    required_keys = ['api_key', 'max_retries']
    
    # Vérifier que toutes les clés requises sont présentes
    for key in required_keys:
        if key not in config:
            return False
    
    # Vérifier les types et valeurs
    if not isinstance(config['api_key'], str) or not config['api_key']:
        return False
    
    if not isinstance(config['max_retries'], int) or config['max_retries'] <= 0:
        return False
    
    return True


def create_instance(name: str, config: Optional[Dict] = None) -> ExampleClass:
    """
    Crée et configure une nouvelle instance de ExampleClass.
    
    Cette fonction est un helper pour créer et initialiser une instance
    avec les paramètres fournis.
    
    Args:
        name: Nom de l'instance à créer.
        config: Configuration optionnelle pour l'instance.
    
    Returns:
        ExampleClass: Une nouvelle instance configurée.
    
    Raises:
        ValueError: Si le nom est vide ou si la configuration est invalide.
    """
    if not name:
        raise ValueError("Le nom ne peut pas être vide")
    
    if config and not validate_config(config):
        raise ValueError("Configuration invalide")
    
    instance = ExampleClass(name, config)
    return instance


if __name__ == "__main__":
    # Exemple d'utilisation
    try:
        # Créer une instance
        instance = create_instance("example", {"api_key": "abc123", "max_retries": 3})
        
        # Démarrer l'instance
        instance.start()
        
        # Obtenir le statut
        status = instance.get_status()
        print(f"Statut: {status}")
        
        # Traiter des données
        data = [{"id": 1, "value": "test"}, {"id": 2, "value": "example"}]
        count, processed = instance.process_data(data)
        print(f"Éléments traités: {count}")
        print(f"Données traitées: {processed}")
        
        # Arrêter l'instance
        instance.stop()
        
    except Exception as e:
        print(f"Erreur: {e}") 