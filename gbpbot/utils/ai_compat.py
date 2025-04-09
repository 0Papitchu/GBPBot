"""
Module de compatibilité pour les dépendances d'IA.
Fournit des mocks pour les bibliothèques d'IA lorsqu'elles ne sont pas disponibles.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("gbpbot.utils.ai_compat")

# Statut des bibliothèques d'IA
HAS_TENSORFLOW = False
HAS_TORCH = False
HAS_ONNX = False
HAS_LLAMA = False

# Mock pour tensorflow.python
class MockTensorflow:
    """Mock pour le module tensorflow."""
    
    class python:
        """Mock pour le sous-module tensorflow.python."""
        
        class util:
            """Mock pour tensorflow.python.util."""
            
            def deprecation(*args, **kwargs):
                """Mock pour tensorflow.python.util.deprecation."""
                return lambda x: x
                
            def tf_decorator(*args, **kwargs):
                """Mock pour tensorflow.python.util.tf_decorator."""
                return lambda x: x

# Tenter d'importer tensorflow
try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
    logger.debug("TensorFlow importé avec succès")
except ImportError:
    logger.warning("TensorFlow non disponible, utilisation du mock")
    # Créer un mock pour tensorflow si non disponible
    sys.modules['tensorflow'] = MockTensorflow()
    # Créer un mock pour tensorflow.python s'il n'existe pas
    if 'tensorflow.python' not in sys.modules:
        sys.modules['tensorflow.python'] = MockTensorflow.python
    # Créer un mock pour tensorflow.python.util s'il n'existe pas
    if 'tensorflow.python.util' not in sys.modules:
        sys.modules['tensorflow.python.util'] = MockTensorflow.python.util

# Tenter d'importer torch
try:
    import torch
    HAS_TORCH = True
    logger.debug("PyTorch importé avec succès")
except ImportError:
    logger.warning("PyTorch n'est pas disponible")
    # Créer un mock simple pour torch
    class MockTorch:
        """Mock pour le module torch."""
        @staticmethod
        def tensor(*args, **kwargs):
            """Mock pour torch.tensor."""
            return args[0] if args else None
    
    # Ajouter le mock au sys.modules
    sys.modules['torch'] = MockTorch()

# Tenter d'importer onnx
try:
    import onnxruntime
    HAS_ONNX = True
    logger.debug("ONNX Runtime importé avec succès")
except ImportError:
    logger.warning("ONNX Runtime n'est pas disponible")
    # Créer un mock simple pour onnxruntime
    class MockOnnx:
        """Mock pour le module onnxruntime."""
        class InferenceSession:
            """Mock pour onnxruntime.InferenceSession."""
            def __init__(self, *args, **kwargs):
                pass
            def run(self, *args, **kwargs):
                return [None]
    
    # Ajouter le mock au sys.modules
    sys.modules['onnxruntime'] = MockOnnx()

# Tenter d'importer llama
try:
    import llama_cpp
    HAS_LLAMA = True
    logger.debug("LLaMA importé avec succès")
except ImportError:
    logger.warning("LLaMA n'est pas disponible")
    # Créer un mock simple pour llama_cpp
    class MockLlama:
        """Mock pour le module llama_cpp."""
        class Llama:
            """Mock pour llama_cpp.Llama."""
            def __init__(self, *args, **kwargs):
                pass
            def eval(self, *args, **kwargs):
                return {"text": "LLaMA non disponible"}
    
    # Ajouter le mock au sys.modules
    sys.modules['llama_cpp'] = MockLlama()

def import_tensorflow():
    """
    Importe TensorFlow s'il est disponible, sinon retourne le mock.
    
    Returns:
        module: Le module TensorFlow ou son mock
    """
    if HAS_TENSORFLOW:
        import tensorflow as tf
        return tf
    else:
        return sys.modules['tensorflow']

def import_torch():
    """
    Importe PyTorch s'il est disponible, sinon retourne le mock.
    
    Returns:
        module: Le module PyTorch ou son mock
    """
    if HAS_TORCH:
        import torch
        return torch
    else:
        return sys.modules['torch']

def import_onnx():
    """
    Importe ONNX Runtime s'il est disponible, sinon retourne le mock.
    
    Returns:
        module: Le module ONNX Runtime ou son mock
    """
    if HAS_ONNX:
        import onnxruntime
        return onnxruntime
    else:
        return sys.modules['onnxruntime']

def import_llama():
    """
    Importe LLaMA s'il est disponible, sinon retourne le mock.
    
    Returns:
        module: Le module LLaMA ou son mock
    """
    if HAS_LLAMA:
        import llama_cpp
        return llama_cpp
    else:
        return sys.modules['llama_cpp'] 