"""
Mock module for tensorflow to avoid dependency issues during testing.
"""

class MockTensor:
    """Mock TensorFlow tensor class."""
    
    def __init__(self, shape=None, dtype=None, name=None, value=None):
        self.shape = shape
        self.dtype = dtype
        self.name = name
        self.value = value if value is not None else 0
    
    def numpy(self):
        """Return value as numpy array."""
        return self.value
    
    def __add__(self, other):
        return MockTensor(value=self.value + getattr(other, 'value', other))
    
    def __mul__(self, other):
        return MockTensor(value=self.value * getattr(other, 'value', other))

def constant(value, dtype=None, shape=None, name=None):
    """Mock tf.constant."""
    return MockTensor(shape=shape, dtype=dtype, name=name, value=value)

def Variable(initial_value, dtype=None, name=None, trainable=True):
    """Mock tf.Variable."""
    return MockTensor(dtype=dtype, name=name, value=initial_value)

class python:
    """Mock tf.python module."""
    
    class pywrap_tensorflow:
        """Mock tf.python.pywrap_tensorflow module."""
        
        @staticmethod
        def TF_Version():
            """Return mock version string."""
            return "2.8.0-mock"
        
        @staticmethod
        def get_op_list(name):
            """Return empty op list."""
            return []

def set_random_seed(seed):
    """Mock set_random_seed function."""
    pass

def executing_eagerly():
    """Mock executing_eagerly function."""
    return True

def function(func=None, input_signature=None, autograph=True):
    """Mock function decorator."""
    def decorator(f):
        return f
    if func is not None:
        return decorator(func)
    return decorator

class Model:
    """Mock tf.keras.Model class."""
    
    def __init__(self, inputs=None, outputs=None):
        self.inputs = inputs
        self.outputs = outputs
        self.layers = []
    
    def add(self, layer):
        """Add a layer to the model."""
        self.layers.append(layer)
    
    def compile(self, optimizer=None, loss=None, metrics=None):
        """Mock compile method."""
        self.optimizer = optimizer
        self.loss = loss
        self.metrics = metrics
    
    def fit(self, x=None, y=None, epochs=1, batch_size=None, validation_data=None, callbacks=None):
        """Mock fit method."""
        import numpy as np
        
        class History:
            def __init__(self):
                self.history = {
                    'loss': [0.1] * epochs,
                    'val_loss': [0.2] * epochs
                }
        
        return History()
    
    def predict(self, x):
        """Mock predict method."""
        import numpy as np
        if hasattr(x, 'shape'):
            return np.zeros((len(x), 1))
        else:
            return np.zeros((1, 1))
    
    def save(self, filepath, overwrite=True, save_format=None):
        """Mock save method."""
        pass
    
    def load_weights(self, filepath):
        """Mock load_weights method."""
        return self

class layer_classes:
    """Mock layer classes."""
    
    class Dense:
        def __init__(self, units, activation=None, input_shape=None):
            self.units = units
            self.activation = activation
            self.input_shape = input_shape
        
        def __call__(self, inputs):
            return MockTensor()
    
    class Input:
        @staticmethod
        def __call__(shape=None, dtype=None, name=None):
            return MockTensor(shape=shape, dtype=dtype, name=name)
    
    class LSTM:
        def __init__(self, units, return_sequences=False, input_shape=None):
            self.units = units
            self.return_sequences = return_sequences
            self.input_shape = input_shape
        
        def __call__(self, inputs):
            return MockTensor()
    
    class Dropout:
        def __init__(self, rate):
            self.rate = rate
        
        def __call__(self, inputs):
            return MockTensor()
    
    class BatchNormalization:
        def __init__(self):
            pass
        
        def __call__(self, inputs):
            return MockTensor()

class optimizer_classes:
    """Mock optimizer classes."""
    
    class Adam:
        def __init__(self, learning_rate=0.001):
            self.learning_rate = learning_rate
    
    class RMSprop:
        def __init__(self, learning_rate=0.001):
            self.learning_rate = learning_rate

class loss_classes:
    """Mock loss classes."""
    
    @staticmethod
    def binary_crossentropy(y_true, y_pred):
        return 0.0
    
    @staticmethod
    def categorical_crossentropy(y_true, y_pred):
        return 0.0
    
    @staticmethod
    def mean_squared_error(y_true, y_pred):
        return 0.0

class callback_classes:
    """Mock callback classes."""
    
    class EarlyStopping:
        def __init__(self, monitor='val_loss', patience=0, verbose=0, mode='auto'):
            self.monitor = monitor
            self.patience = patience
            self.verbose = verbose
            self.mode = mode
    
    class ModelCheckpoint:
        def __init__(self, filepath, monitor='val_loss', save_best_only=False, verbose=0):
            self.filepath = filepath
            self.monitor = monitor
            self.save_best_only = save_best_only
            self.verbose = verbose

class activation_functions:
    """Mock activation functions."""
    
    @staticmethod
    def relu(x):
        return MockTensor()
    
    @staticmethod
    def sigmoid(x):
        return MockTensor()
    
    @staticmethod
    def tanh(x):
        return MockTensor()
    
    @staticmethod
    def softmax(x):
        return MockTensor()

def Sequential(layers=None):
    """Mock keras.Sequential function."""
    model = Model()
    if layers is not None:
        for layer in layers:
            model.add(layer)
    return model

class keras:
    """Mock tf.keras module."""
    
    Model = Model
    Sequential = Sequential
    layers = layer_classes()
    optimizers = optimizer_classes()
    losses = loss_classes()
    callbacks = callback_classes()
    activations = activation_functions()

# Exports to make keras available as a top-level attribute
