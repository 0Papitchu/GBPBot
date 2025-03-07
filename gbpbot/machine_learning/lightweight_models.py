#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de modèles d'IA légers pour GBPBot
=========================================

Ce module implémente des modèles d'apprentissage automatique légers et optimisés 
pour une exécution rapide en temps réel, permettant d'analyser les contrats et 
les opportunités de marché avec une latence minimale. Il prend en charge les 
modèles quantifiés et optimisés pour CPU/GPU.
"""

import os
import time
import json
import logging
import pickle
import threading
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lightweight_models")

# Essai d'importation des modules d'IA légers
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
    logger.info("ONNX Runtime disponible pour modèles légers")
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime non disponible. Installation via: pip install onnxruntime onnxruntime-gpu")

try:
    import tensorflow as tf
    TF_AVAILABLE = True
    logger.info("TensorFlow disponible pour modèles légers")
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow non disponible. Installation via: pip install tensorflow")

try:
    import torch
    TORCH_AVAILABLE = True
    logger.info("PyTorch disponible pour modèles légers")
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch non disponible. Installation via: pip install torch")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
    logger.info("XGBoost disponible pour modèles légers")
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost non disponible. Installation via: pip install xgboost")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
    logger.info("LightGBM disponible pour modèles légers")
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM non disponible. Installation via: pip install lightgbm")

class ModelType(Enum):
    """Type de modèle d'IA léger."""
    ONNX = "onnx"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CUSTOM = "custom"

class ModelTask(Enum):
    """Tâche pour laquelle le modèle est optimisé."""
    CONTRACT_SECURITY = "contract_security"       # Analyse de sécurité des contrats
    TOKEN_POTENTIAL = "token_potential"           # Évaluation du potentiel d'un token
    PRICE_PREDICTION = "price_prediction"         # Prédiction des mouvements de prix
    PATTERN_DETECTION = "pattern_detection"       # Détection de patterns dans les données
    VOLATILITY_PREDICTION = "volatility_prediction"  # Prédiction de la volatilité
    RISK_ASSESSMENT = "risk_assessment"           # Évaluation des risques
    CUSTOM = "custom"                             # Tâche personnalisée

@dataclass
class ModelPerformanceStats:
    """Statistiques de performance d'un modèle léger."""
    total_predictions: int = 0
    total_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    max_execution_time_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_batch_avg_time_ms: float = 0.0
    last_error: Optional[str] = None
    
    @property
    def avg_execution_time_ms(self) -> float:
        """Temps d'exécution moyen en millisecondes."""
        if self.total_predictions > 0:
            return self.total_execution_time_ms / self.total_predictions
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Taux de succès des prédictions."""
        if self.total_predictions > 0:
            return (self.success_count / self.total_predictions) * 100.0
        return 0.0
    
    def update(self, execution_time_ms: float, success: bool, error_msg: Optional[str] = None) -> None:
        """Met à jour les statistiques avec une nouvelle prédiction."""
        self.total_predictions += 1
        self.total_execution_time_ms += execution_time_ms
        
        self.min_execution_time_ms = min(self.min_execution_time_ms, execution_time_ms)
        self.max_execution_time_ms = max(self.max_execution_time_ms, execution_time_ms)
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            self.last_error = error_msg
            
        # Calculer la moyenne mobile sur les 100 dernières prédictions
        last_n = min(100, self.total_predictions)
        if last_n > 0:
            self.last_batch_avg_time_ms = ((self.last_batch_avg_time_ms * (last_n - 1)) + execution_time_ms) / last_n

@dataclass
class LightweightModel:
    """
    Représentation d'un modèle d'IA léger et optimisé.
    
    Cette classe encapsule un modèle d'IA léger avec ses métadonnées,
    sa configuration et les fonctions de pré/post-traitement.
    """
    name: str
    type: ModelType
    task: ModelTask
    model_path: str
    version: str
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Fonctions de pré/post-traitement
    preprocessor: Optional[Callable] = None
    postprocessor: Optional[Callable] = None
    
    # Modèle chargé en mémoire
    model: Any = None
    
    # Statistiques de performance
    stats: ModelPerformanceStats = field(default_factory=ModelPerformanceStats)
    
    # Métadonnées additionnelles
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Cache pour les résultats récents
    _prediction_cache: Dict[str, Tuple[Any, float]] = field(default_factory=dict)
    _cache_ttl_seconds: int = 30
    _max_cache_items: int = 1000
    
    def __post_init__(self):
        """Initialisation après la création de l'instance."""
        self._lock = threading.RLock()
        
        # Vérifier si le chemin du modèle existe
        if not os.path.exists(self.model_path):
            logger.warning(f"Chemin du modèle non trouvé: {self.model_path}")
            
        # Valider les types d'énumération
        if isinstance(self.type, str):
            self.type = ModelType(self.type)
        if isinstance(self.task, str):
            self.task = ModelTask(self.task)
    
    def load(self) -> bool:
        """
        Charge le modèle en mémoire.
        
        Returns:
            bool: Succès du chargement
        """
        if self.model is not None:
            logger.info(f"Modèle {self.name} déjà chargé")
            return True
            
        try:
            start_time = time.time()
            logger.info(f"Chargement du modèle {self.name} ({self.type.value})...")
            
            with self._lock:
                if self.type == ModelType.ONNX:
                    if not ONNX_AVAILABLE:
                        raise ImportError("ONNX Runtime n'est pas disponible")
                    
                    # Configuration des options ONNX
                    sess_options = ort.SessionOptions()
                    
                    # Utiliser CUDA si disponible et configuré
                    use_cuda = self.config.get('use_cuda', False)
                    if use_cuda and 'CUDAExecutionProvider' in ort.get_available_providers():
                        self.model = ort.InferenceSession(
                            self.model_path, 
                            sess_options=sess_options,
                            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
                        )
                        logger.info(f"Modèle {self.name} chargé avec CUDA")
                    else:
                        self.model = ort.InferenceSession(
                            self.model_path, 
                            sess_options=sess_options,
                            providers=['CPUExecutionProvider']
                        )
                        logger.info(f"Modèle {self.name} chargé avec CPU")
                
                elif self.type == ModelType.TENSORFLOW:
                    if not TF_AVAILABLE:
                        raise ImportError("TensorFlow n'est pas disponible")
                    
                    # Configurer la mémoire GPU si nécessaire
                    if self.config.get('limit_gpu_memory', False):
                        gpus = tf.config.experimental.list_physical_devices('GPU')
                        if gpus:
                            memory_limit = self.config.get('gpu_memory_limit_mb', 512)
                            for gpu in gpus:
                                tf.config.experimental.set_virtual_device_configuration(
                                    gpu,
                                    [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=memory_limit)]
                                )
                    
                    # Charger le modèle TensorFlow
                    self.model = tf.saved_model.load(self.model_path)
                
                elif self.type == ModelType.PYTORCH:
                    if not TORCH_AVAILABLE:
                        raise ImportError("PyTorch n'est pas disponible")
                    
                    # Configurer le périphérique (CPU/CUDA)
                    device_str = self.config.get('device', 'cpu')
                    device = torch.device(device_str if torch.cuda.is_available() and 'cuda' in device_str else 'cpu')
                    
                    # Charger le modèle PyTorch
                    self.model = torch.load(self.model_path, map_location=device)
                    
                    # Mettre en mode évaluation
                    if hasattr(self.model, 'eval'):
                        self.model.eval()
                
                elif self.type == ModelType.XGBOOST:
                    if not XGBOOST_AVAILABLE:
                        raise ImportError("XGBoost n'est pas disponible")
                    
                    # Charger le modèle XGBoost
                    self.model = xgb.Booster()
                    self.model.load_model(self.model_path)
                
                elif self.type == ModelType.LIGHTGBM:
                    if not LIGHTGBM_AVAILABLE:
                        raise ImportError("LightGBM n'est pas disponible")
                    
                    # Charger le modèle LightGBM
                    self.model = lgb.Booster(model_file=self.model_path)
                
                elif self.type == ModelType.CUSTOM:
                    # Pour les modèles personnalisés, charger avec pickle
                    with open(self.model_path, 'rb') as f:
                        self.model = pickle.load(f)
                        
                else:
                    raise ValueError(f"Type de modèle non supporté: {self.type}")
                
            elapsed_time = (time.time() - start_time) * 1000
            logger.info(f"Modèle {self.name} chargé en {elapsed_time:.2f}ms")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle {self.name}: {e}")
            return False
    
    def unload(self) -> bool:
        """
        Décharge le modèle de la mémoire pour libérer des ressources.
        
        Returns:
            bool: Succès du déchargement
        """
        with self._lock:
            if self.model is None:
                return True
                
            try:
                # Libérer explicitement la mémoire si possible
                if self.type == ModelType.PYTORCH and TORCH_AVAILABLE:
                    del self.model
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                else:
                    del self.model
                
                self.model = None
                self._prediction_cache.clear()
                logger.info(f"Modèle {self.name} déchargé de la mémoire")
                return True
                
            except Exception as e:
                logger.error(f"Erreur lors du déchargement du modèle {self.name}: {e}")
                return False
    
    def predict(self, data: Any, cache_key: Optional[str] = None) -> Tuple[Any, float]:
        """
        Effectue une prédiction avec le modèle léger.
        
        Args:
            data: Données d'entrée pour la prédiction
            cache_key: Clé de cache optionnelle pour éviter de recalculer des résultats récents
            
        Returns:
            Tuple[Any, float]: (Résultat de la prédiction, temps d'exécution en ms)
        """
        # Vérifier si le résultat est dans le cache
        if cache_key is not None and cache_key in self._prediction_cache:
            cached_result, cache_time = self._prediction_cache[cache_key]
            if time.time() - cache_time < self._cache_ttl_seconds:
                return cached_result, 0.0  # Temps d'exécution de 0ms pour les résultats en cache
        
        # Charger le modèle s'il n'est pas déjà chargé
        if self.model is None:
            if not self.load():
                raise RuntimeError(f"Impossible de charger le modèle {self.name}")
        
        start_time = time.time()
        success = False
        error_msg = None
        result = None
        
        try:
            # Prétraitement des données
            processed_data = data
            if self.preprocessor is not None:
                processed_data = self.preprocessor(data)
            
            # Effectuer la prédiction en fonction du type de modèle
            with self._lock:
                if self.type == ModelType.ONNX:
                    # Obtenir les noms des entrées du modèle
                    input_names = [input.name for input in self.model.get_inputs()]
                    
                    # Préparer les entrées au format attendu par ONNX
                    if isinstance(processed_data, dict):
                        onnx_inputs = {name: processed_data[name] for name in input_names if name in processed_data}
                    elif len(input_names) == 1:
                        onnx_inputs = {input_names[0]: processed_data}
                    else:
                        raise ValueError(f"Format d'entrée incompatible avec le modèle ONNX qui attend: {input_names}")
                    
                    # Effectuer la prédiction ONNX
                    output = self.model.run(None, onnx_inputs)
                    result = output[0] if len(output) == 1 else output
                
                elif self.type == ModelType.TENSORFLOW:
                    # Effectuer la prédiction TensorFlow
                    if hasattr(self.model, 'signatures') and 'serving_default' in self.model.signatures:
                        result = self.model.signatures['serving_default'](tf.constant(processed_data))
                    else:
                        result = self.model(processed_data)
                    
                    # Convertir le résultat TensorFlow en NumPy si nécessaire
                    if hasattr(result, 'numpy'):
                        result = result.numpy()
                
                elif self.type == ModelType.PYTORCH:
                    # Convertir en tensor PyTorch si nécessaire
                    if not isinstance(processed_data, torch.Tensor):
                        if isinstance(processed_data, np.ndarray):
                            processed_data = torch.from_numpy(processed_data)
                        else:
                            processed_data = torch.tensor(processed_data)
                    
                    # Obtenir le périphérique du modèle
                    device = next(self.model.parameters()).device if hasattr(self.model, 'parameters') else torch.device('cpu')
                    processed_data = processed_data.to(device)
                    
                    # Désactiver le calcul du gradient pour l'inférence
                    with torch.no_grad():
                        result = self.model(processed_data)
                    
                    # Convertir le résultat en NumPy pour uniformité
                    if isinstance(result, torch.Tensor):
                        result = result.cpu().numpy()
                
                elif self.type == ModelType.XGBOOST:
                    # Convertir les données au format DMatrix
                    if not isinstance(processed_data, xgb.DMatrix):
                        if isinstance(processed_data, np.ndarray):
                            processed_data = xgb.DMatrix(processed_data)
                        else:
                            processed_data = xgb.DMatrix(np.array(processed_data))
                    
                    # Effectuer la prédiction XGBoost
                    result = self.model.predict(processed_data)
                
                elif self.type == ModelType.LIGHTGBM:
                    # Effectuer la prédiction LightGBM
                    result = self.model.predict(processed_data)
                
                elif self.type == ModelType.CUSTOM:
                    # Pour les modèles personnalisés, utiliser la méthode 'predict'
                    if hasattr(self.model, 'predict'):
                        result = self.model.predict(processed_data)
                    else:
                        raise AttributeError(f"Le modèle personnalisé ne possède pas de méthode 'predict'")
                
                else:
                    raise ValueError(f"Type de modèle non supporté: {self.type}")
            
            # Post-traitement des résultats
            if self.postprocessor is not None:
                result = self.postprocessor(result)
                
            success = True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erreur lors de la prédiction avec le modèle {self.name}: {e}")
            raise
            
        finally:
            # Calculer le temps d'exécution
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Mettre à jour les statistiques
            self.stats.update(execution_time_ms, success, error_msg)
            
            # Mettre en cache le résultat si nécessaire
            if cache_key is not None and success:
                self._add_to_cache(cache_key, result)
        
        return result, execution_time_ms
    
    def _add_to_cache(self, key: str, value: Any) -> None:
        """Ajoute un résultat au cache avec gestion de la taille maximale."""
        with self._lock:
            # Si le cache est plein, supprimer l'élément le plus ancien
            if len(self._prediction_cache) >= self._max_cache_items:
                oldest_key = next(iter(self._prediction_cache))
                self._prediction_cache.pop(oldest_key)
            
            # Ajouter le nouvel élément
            self._prediction_cache[key] = (value, time.time())
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Récupère les métadonnées complètes du modèle.
        
        Returns:
            Dict[str, Any]: Métadonnées du modèle
        """
        return {
            "name": self.name,
            "type": self.type.value,
            "task": self.task.value,
            "model_path": self.model_path,
            "version": self.version,
            "description": self.description,
            "loaded": self.model is not None,
            "stats": {
                "total_predictions": self.stats.total_predictions,
                "avg_execution_time_ms": self.stats.avg_execution_time_ms,
                "min_execution_time_ms": self.stats.min_execution_time_ms,
                "max_execution_time_ms": self.stats.max_execution_time_ms,
                "success_rate": self.stats.success_rate,
                "last_batch_avg_time_ms": self.stats.last_batch_avg_time_ms
            },
            "metadata": self.metadata
        }

class LightweightModelManager:
    """
    Gestionnaire de modèles d'IA légers.
    
    Cette classe gère le cycle de vie des modèles légers, leur chargement,
    leur utilisation et leur déchargement pour optimiser l'utilisation des ressources.
    """
    
    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de modèles légers.
        
        Args:
            models_dir: Répertoire contenant les modèles légers
        """
        self.models_dir = models_dir or os.path.join(os.path.dirname(__file__), "models")
        self.models: Dict[str, LightweightModel] = {}
        self._lock = threading.RLock()
        
        # Créer le répertoire des modèles s'il n'existe pas
        os.makedirs(self.models_dir, exist_ok=True)
        
        logger.info(f"Gestionnaire de modèles légers initialisé avec répertoire: {self.models_dir}")
    
    def register_model(self, model: LightweightModel, load_immediately: bool = False) -> bool:
        """
        Enregistre un modèle auprès du gestionnaire.
        
        Args:
            model: Modèle à enregistrer
            load_immediately: Si True, charge le modèle immédiatement
            
        Returns:
            bool: Succès de l'enregistrement
        """
        with self._lock:
            if model.name in self.models:
                logger.warning(f"Un modèle avec le nom '{model.name}' est déjà enregistré")
                return False
            
            self.models[model.name] = model
            logger.info(f"Modèle '{model.name}' enregistré avec succès")
            
            if load_immediately:
                return model.load()
            
            return True
    
    def load_model_from_config(self, config_path: str, load_immediately: bool = False) -> Optional[LightweightModel]:
        """
        Charge un modèle à partir d'un fichier de configuration.
        
        Args:
            config_path: Chemin vers le fichier de configuration JSON
            load_immediately: Si True, charge le modèle immédiatement
            
        Returns:
            Optional[LightweightModel]: Modèle chargé ou None en cas d'erreur
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Vérifier les champs requis
            required_fields = ['name', 'type', 'task', 'model_path', 'version']
            for field in required_fields:
                if field not in config:
                    logger.error(f"Champ requis manquant dans la configuration: {field}")
                    return None
            
            # Résoudre le chemin du modèle s'il est relatif
            model_path = config['model_path']
            if not os.path.isabs(model_path):
                # Essayer relatif au répertoire de configuration
                config_dir = os.path.dirname(os.path.abspath(config_path))
                model_path = os.path.join(config_dir, model_path)
                
                # Si toujours pas trouvé, essayer relatif au répertoire des modèles
                if not os.path.exists(model_path):
                    model_path = os.path.join(self.models_dir, config['model_path'])
            
            config['model_path'] = model_path
            
            # Créer l'instance du modèle
            model = LightweightModel(
                name=config['name'],
                type=ModelType(config['type']),
                task=ModelTask(config['task']),
                model_path=model_path,
                version=config['version'],
                description=config.get('description', ''),
                config=config.get('config', {}),
                metadata=config.get('metadata', {})
            )
            
            # Enregistrer le modèle
            if self.register_model(model, load_immediately):
                return model
                
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle depuis la configuration: {e}")
            return None
    
    def discover_models(self, pattern: str = "*_config.json") -> List[str]:
        """
        Découvre les modèles disponibles dans le répertoire des modèles.
        
        Args:
            pattern: Pattern glob pour les fichiers de configuration
            
        Returns:
            List[str]: Liste des chemins vers les fichiers de configuration trouvés
        """
        config_files = []
        
        try:
            # Rechercher récursivement les fichiers de configuration
            for root, _, files in os.walk(self.models_dir):
                for file in files:
                    if Path(file).match(pattern):
                        config_files.append(os.path.join(root, file))
        
        except Exception as e:
            logger.error(f"Erreur lors de la découverte des modèles: {e}")
        
        return config_files
    
    def load_discovered_models(self, pattern: str = "*_config.json", tasks: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Charge tous les modèles découverts dans le répertoire des modèles.
        
        Args:
            pattern: Pattern glob pour les fichiers de configuration
            tasks: Liste des tâches à charger (si None, charge tous les modèles)
            
        Returns:
            Dict[str, bool]: Dictionnaire {nom_modèle: succès_chargement}
        """
        results = {}
        config_files = self.discover_models(pattern)
        
        for config_file in config_files:
            try:
                # Charger la configuration pour vérifier la tâche
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Filtrer par tâche si spécifié
                if tasks and config.get('task') not in tasks:
                    continue
                
                # Charger et enregistrer le modèle
                model = self.load_model_from_config(config_file)
                if model:
                    results[model.name] = True
                else:
                    model_name = config.get('name', os.path.basename(config_file))
                    results[model_name] = False
                    
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle depuis {config_file}: {e}")
                results[os.path.basename(config_file)] = False
        
        return results
    
    def get_model(self, model_name: str, load_if_needed: bool = True) -> Optional[LightweightModel]:
        """
        Récupère un modèle par son nom.
        
        Args:
            model_name: Nom du modèle à récupérer
            load_if_needed: Si True, charge le modèle s'il n'est pas déjà chargé
            
        Returns:
            Optional[LightweightModel]: Modèle ou None s'il n'existe pas
        """
        model = self.models.get(model_name)
        
        if model and load_if_needed and model.model is None:
            if not model.load():
                logger.warning(f"Échec du chargement du modèle {model_name}")
        
        return model
    
    def get_models_by_task(self, task: Union[ModelTask, str], load_if_needed: bool = False) -> List[LightweightModel]:
        """
        Récupère tous les modèles pour une tâche spécifique.
        
        Args:
            task: Tâche pour laquelle récupérer les modèles
            load_if_needed: Si True, charge les modèles s'ils ne sont pas déjà chargés
            
        Returns:
            List[LightweightModel]: Liste des modèles pour la tâche spécifiée
        """
        if isinstance(task, str):
            task = ModelTask(task)
        
        task_models = [model for model in self.models.values() if model.task == task]
        
        if load_if_needed:
            for model in task_models:
                if model.model is None:
                    model.load()
        
        return task_models
    
    def unload_model(self, model_name: str) -> bool:
        """
        Décharge un modèle de la mémoire.
        
        Args:
            model_name: Nom du modèle à décharger
            
        Returns:
            bool: Succès du déchargement
        """
        model = self.models.get(model_name)
        if not model:
            logger.warning(f"Modèle {model_name} non trouvé pour déchargement")
            return False
        
        return model.unload()
    
    def unload_all_models(self) -> Dict[str, bool]:
        """
        Décharge tous les modèles de la mémoire.
        
        Returns:
            Dict[str, bool]: Dictionnaire {nom_modèle: succès_déchargement}
        """
        results = {}
        
        for name, model in self.models.items():
            results[name] = model.unload()
        
        return results
    
    def get_loaded_models(self) -> List[str]:
        """
        Récupère la liste des modèles actuellement chargés en mémoire.
        
        Returns:
            List[str]: Liste des noms des modèles chargés
        """
        return [name for name, model in self.models.items() if model.model is not None]
    
    def get_all_models_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les métadonnées de tous les modèles enregistrés.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des métadonnées par modèle
        """
        return {name: model.get_metadata() for name, model in self.models.items()}

# Fonction utilitaire pour créer un gestionnaire avec configuration par défaut
def create_model_manager(models_dir: Optional[str] = None) -> LightweightModelManager:
    """
    Crée un gestionnaire de modèles légers avec configuration par défaut.
    
    Args:
        models_dir: Répertoire des modèles (si None, utilise le répertoire par défaut)
        
    Returns:
        LightweightModelManager: Gestionnaire de modèles légers
    """
    manager = LightweightModelManager(models_dir)
    
    # Découvrir automatiquement les modèles disponibles
    manager.discover_models()
    
    return manager 