#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de compatibilité pour le chiffrement
===========================================

Ce module fournit des stubs et gère les importations optionnelles
pour le module de chiffrement des wallets.
"""

from typing import Any, Callable, TypeVar

# Définir un type personnalisé au lieu d'utiliser FixtureFunction
FixtureFunction = TypeVar('FixtureFunction', bound=Callable[..., Any])

# Statut de disponibilité des modules
has_cryptography = False
has_secrets = False
has_prometheus = False
has_pandas = False

# Pour le chiffrement
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    has_cryptography = True
except ImportError:
    # Créer des stubs si nécessaire
    class Fernet:
        def __init__(self, key):
            self.key = key
            
        def encrypt(self, data):
            raise NotImplementedError("Module cryptography non disponible")
            
        def decrypt(self, data):
            raise NotImplementedError("Module cryptography non disponible")
    
    class hashes:
        class SHA256:
            pass
    
    class PBKDF2HMAC:
        def __init__(self, algorithm, length, salt, iterations):
            self.algorithm = algorithm
            self.length = length
            self.salt = salt
            self.iterations = iterations
            
        def derive(self, data):
            raise NotImplementedError("Module cryptography non disponible")

# Pour les fonctions de chiffrement simplifiées
try:
    import secrets
    has_secrets = True
except ImportError:
    # Module secrets (disponible depuis Python 3.6)
    import os
    
    class SecretsStub:
        def token_bytes(self, nbytes=32):
            return os.urandom(nbytes)
            
        def token_hex(self, nbytes=32):
            return os.urandom(nbytes).hex()
            
        def token_urlsafe(self, nbytes=32):
            import base64
            return base64.urlsafe_b64encode(os.urandom(nbytes)).rstrip(b'=').decode('ascii')
    
    secrets = SecretsStub()

# Pour les métriques (optionnel)
try:
    import prometheus_client
    has_prometheus = True
except ImportError:
    # Créer un stub pour éviter les erreurs d'importation
    class PrometheusClientStub:
        class Counter:
            def __init__(self, *args, **kwargs):
                pass
                
            def inc(self, *args, **kwargs):
                pass
                
        class Gauge:
            def __init__(self, *args, **kwargs):
                pass
                
            def set(self, *args, **kwargs):
                pass
                
            def inc(self, *args, **kwargs):
                pass
                
            def dec(self, *args, **kwargs):
                pass
    
    # Assigner le stub au nom de module manquant
    prometheus_client = PrometheusClientStub()

# Pour l'analyse de données (optionnel)
try:
    import pandas as pd
    has_pandas = True
except ImportError:
    # Créer un stub minimal pour pandas si nécessaire
    class PandasStub:
        def DataFrame(self, *args, **kwargs):
            return []
            
        def Series(self, *args, **kwargs):
            return []
    
    # Assigner le stub au nom de module manquant
    pd = PandasStub() 