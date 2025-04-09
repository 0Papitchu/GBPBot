"""
Module de compatibilité pour TensorFlow.

Ce module permet au GBPBot de fonctionner même si TensorFlow n'est pas installé.
Il fournit des fonctionnalités de base pour assurer la compatibilité et éviter
les erreurs d'importation.
"""

import logging
import sys

logger = logging.getLogger(__name__)

# Initialisation des variables
HAS_TENSORFLOW = False
tf = None

try:
    # Tenter d'importer TensorFlow
    import tensorflow as _tf
    tf = _tf
    HAS_TENSORFLOW = True
    logger.info(f"TensorFlow importé avec succès (version: {tf.__version__})")
except ImportError:
    logger.warning("TensorFlow n'est pas disponible. Mode dégradé activé.")
    
    # Créer un module factice pour TensorFlow
    class TensorFlowMock:
        """Classe factice pour simuler TensorFlow."""
        
        def __init__(self):
            self.__version__ = "0.0.0-mock"
            self.keras = TensorFlowKerasMock()
            self.python = TensorFlowPythonMock()
            
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut non-implémenté de TensorFlow: {name}")
            return MockAttribute()
    
    class TensorFlowKerasMock:
        """Classe factice pour simuler tf.keras."""
        
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut non-implémenté de tf.keras: {name}")
            return MockAttribute()
    
    class TensorFlowPythonMock:
        """Classe factice pour simuler tf.python."""
        
        def __init__(self):
            # simuler le module pywrap_tensorflow qui cause l'erreur
            self.pywrap_tensorflow = MockAttribute()
            
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut non-implémenté de tf.python: {name}")
            return MockAttribute()
    
    class MockAttribute:
        """Classe générique pour simuler des attributs."""
        
        def __init__(self, return_value=None):
            self.return_value = return_value
        
        def __call__(self, *args, **kwargs):
            logger.debug(f"Appel d'une fonction TensorFlow mocquée avec args={args}, kwargs={kwargs}")
            return self.return_value if self.return_value is not None else self
        
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut {name} sur un objet TensorFlow mocqué")
            return self
    
    # Créer l'instance factice de TensorFlow
    tf = TensorFlowMock()

def get_status():
    """
    Retourne le statut d'installation de TensorFlow.
    
    Returns:
        dict: Informations sur le statut de TensorFlow.
    """
    status = {
        "available": HAS_TENSORFLOW,
        "version": tf.__version__ if HAS_TENSORFLOW else "Non installé"
    }
    
    if HAS_TENSORFLOW:
        # Ajouter des détails sur la configuration de TensorFlow
        status["gpu_available"] = False
        try:
            # Vérifier si le GPU est disponible
            if hasattr(tf, "config") and hasattr(tf.config, "list_physical_devices"):
                gpus = tf.config.list_physical_devices('GPU')
                status["gpu_available"] = len(gpus) > 0
                status["gpu_count"] = len(gpus)
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification du GPU: {e}")
    
    return status 