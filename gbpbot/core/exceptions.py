"""
Exceptions personnalisées pour GBPBot
"""

class GBPBotBaseException(Exception):
    """Exception de base pour toutes les erreurs GBPBot"""
    pass

# Exceptions liées aux blockchains
class BlockchainError(GBPBotBaseException):
    """Exception de base pour les erreurs liées aux blockchains"""
    pass

class RPCConnectionError(BlockchainError):
    """Erreur de connexion RPC"""
    pass

class RPCTimeoutError(BlockchainError):
    """Timeout lors d'une requête RPC"""
    pass

class RPCResponseError(BlockchainError):
    """Erreur dans la réponse RPC"""
    pass

class ContractCallError(BlockchainError):
    """Erreur lors de l'appel d'un contrat"""
    pass

# Exceptions liées aux transactions
class TransactionError(GBPBotBaseException):
    """Exception de base pour les erreurs de transaction"""
    pass

class TransactionFailedError(TransactionError):
    """Transaction échouée"""
    pass

class TransactionTimeoutError(TransactionError):
    """Timeout lors de l'attente d'une transaction"""
    pass

class InsufficientFundsError(TransactionError):
    """Fonds insuffisants pour exécuter une transaction"""
    pass

class GasEstimationError(TransactionError):
    """Erreur lors de l'estimation du gas"""
    pass

# Exceptions liées aux swaps
class SwapError(GBPBotBaseException):
    """Exception de base pour les erreurs de swap"""
    pass

class SwapExecutionError(SwapError):
    """Erreur lors de l'exécution d'un swap"""
    pass

class SlippageExceededError(SwapError):
    """Slippage dépassé lors d'un swap"""
    pass

class PriceImpactTooHighError(SwapError):
    """Impact sur le prix trop élevé"""
    pass

# Exceptions liées à l'arbitrage
class ArbitrageError(GBPBotBaseException):
    """Exception de base pour les erreurs d'arbitrage"""
    pass

class NoArbitrageOpportunityError(ArbitrageError):
    """Aucune opportunité d'arbitrage trouvée"""
    pass

class ArbitrageExecutionError(ArbitrageError):
    """Erreur lors de l'exécution d'un arbitrage"""
    pass

# Exceptions liées à la configuration
class ConfigError(GBPBotBaseException):
    """Exception de base pour les erreurs de configuration"""
    pass

class InvalidConfigError(ConfigError):
    """Configuration invalide"""
    pass

class MissingConfigError(ConfigError):
    """Configuration manquante"""
    pass

# Exceptions liées à la sécurité
class SecurityError(GBPBotBaseException):
    """Exception de base pour les erreurs de sécurité"""
    pass

class PrivateKeyError(SecurityError):
    """Erreur liée à la clé privée"""
    pass

class AuthenticationError(SecurityError):
    """Erreur d'authentification"""
    pass 