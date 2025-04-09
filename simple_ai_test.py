#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple pour le module d'IA du GBPBot.
"""

import os
import sys
import unittest
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Ajouter le répertoire de mocks au début du PYTHONPATH
mock_dir = ROOT_DIR / "gbpbot" / "tests" / "mocks"
if mock_dir.exists():
    sys.path.insert(0, str(mock_dir))

class SimpleAITest(unittest.TestCase):
    """Tests simples pour le module d'IA."""
    
    def test_import_tensorflow_mock(self):
        """Vérifie que le mock TensorFlow peut être importé."""
        try:
            import tensorflow as tf
            self.assertIsNotNone(tf)
            # Vérifier que c'est bien notre mock
            self.assertTrue(hasattr(tf, 'python'))
            self.assertTrue(hasattr(tf.python, 'pywrap_tensorflow'))
        except ImportError as e:
            self.fail(f"Erreur lors de l'importation de TensorFlow mock: {e}")
    
    def test_keras_model(self):
        """Vérifie que le modèle Keras peut être utilisé."""
        try:
            import tensorflow as tf
            # Créer un modèle séquentiel
            model = tf.keras.Sequential()
            
            # Ajouter des couches
            model.add(tf.keras.layers.Dense(10, activation='relu', input_shape=(5,)))
            model.add(tf.keras.layers.Dense(1, activation='sigmoid'))
            
            # Compiler le modèle
            model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                loss='binary_crossentropy'
            )
            
            self.assertIsNotNone(model)
        except Exception as e:
            self.fail(f"Erreur lors de l'utilisation du modèle Keras: {e}")
    
    def test_model_predict(self):
        """Vérifie que la prédiction du modèle fonctionne."""
        try:
            import tensorflow as tf
            import numpy as np
            
            # Créer un modèle séquentiel
            model = tf.keras.Sequential()
            model.add(tf.keras.layers.Dense(1))
            
            # Données fictives
            x_test = np.array([[1, 2, 3], [4, 5, 6]])
            
            # Prédire
            predictions = model.predict(x_test)
            
            self.assertIsNotNone(predictions)
            self.assertEqual(len(predictions), len(x_test))
        except Exception as e:
            self.fail(f"Erreur lors de la prédiction du modèle: {e}")

if __name__ == "__main__":
    unittest.main() 