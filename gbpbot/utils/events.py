from typing import Dict, List, Callable, Any
from collections import defaultdict

class EventEmitter:
    """
    Système simple d'émission et de souscription à des événements.
    Permet la communication entre différents modules de l'application.
    """
    
    def __init__(self):
        """Initialise l'émetteur d'événements"""
        self.events = defaultdict(list)
        
    def on(self, event_name: str, callback: Callable):
        """
        Souscrit à un événement
        
        Args:
            event_name: Nom de l'événement
            callback: Fonction à appeler lors de l'émission de l'événement
        """
        self.events[event_name].append(callback)
        return self  # Pour le chaînage
        
    def off(self, event_name: str, callback: Callable = None):
        """
        Annule une souscription à un événement
        
        Args:
            event_name: Nom de l'événement
            callback: Fonction à retirer. Si None, retire tous les callbacks pour cet événement
        """
        if callback is None:
            self.events[event_name] = []
        else:
            self.events[event_name] = [
                cb for cb in self.events[event_name] if cb != callback
            ]
        return self  # Pour le chaînage
        
    def once(self, event_name: str, callback: Callable):
        """
        Souscrit à un événement pour une seule exécution
        
        Args:
            event_name: Nom de l'événement
            callback: Fonction à appeler lors de l'émission de l'événement
        """
        def wrapper(*args, **kwargs):
            self.off(event_name, wrapper)
            return callback(*args, **kwargs)
            
        self.on(event_name, wrapper)
        return self  # Pour le chaînage
        
    def emit(self, event_name: str, *args, **kwargs):
        """
        Émet un événement
        
        Args:
            event_name: Nom de l'événement
            *args, **kwargs: Arguments à passer aux callbacks
        """
        callbacks = self.events.get(event_name, [])
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                # Ajouter une gestion d'erreurs ici si nécessaire
                print(f"Erreur lors de l'exécution du callback pour l'événement {event_name}: {e}")
        return self  # Pour le chaînage
        
    def list_events(self) -> Dict[str, int]:
        """
        Liste tous les événements avec leur nombre de souscripteurs
        
        Returns:
            Dict[str, int]: Dictionnaire des événements avec le nombre de souscripteurs
        """
        return {event: len(callbacks) for event, callbacks in self.events.items()}
        
    def has_event(self, event_name: str) -> bool:
        """
        Vérifie si un événement a des souscripteurs
        
        Args:
            event_name: Nom de l'événement
            
        Returns:
            bool: True si l'événement a des souscripteurs, False sinon
        """
        return event_name in self.events and len(self.events[event_name]) > 0


class GlobalEventEmitter:
    """
    Singleton pour gérer les événements au niveau global de l'application.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Obtient l'instance unique du gestionnaire d'événements global
        
        Returns:
            EventEmitter: Instance unique du gestionnaire d'événements
        """
        if cls._instance is None:
            cls._instance = EventEmitter()
        return cls._instance 