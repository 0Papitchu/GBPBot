from typing import Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Configuration du système"""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialise la configuration à partir du fichier .env
        
        Args:
            env_file: Chemin vers le fichier .env
        """
        # Charger les variables d'environnement
        load_dotenv(env_file)
        
        # Configuration des RPC
        self.rpc_urls = {
            "avalanche": os.getenv("AVAX_RPC_URL", "https://api.avax.network/ext/bc/C/rpc"),
            "solana": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
            "sonic": os.getenv("SONIC_RPC_URL", "")
        }
        
        # Clés API
        self.api_keys = {
            "etherscan": os.getenv("ETHERSCAN_API_KEY", ""),
            "snowtrace": os.getenv("SNOWTRACE_API_KEY", ""),
            "solscan": os.getenv("SOLSCAN_API_KEY", ""),
            "coinmarketcap": os.getenv("CMC_API_KEY", ""),
            "coingecko": os.getenv("COINGECKO_API_KEY", "")
        }
        
        # Configuration de la base de données
        self.DB_HOST = os.getenv("DB_HOST", "localhost")
        self.DB_PORT = os.getenv("DB_PORT", "5432")
        self.DB_NAME = os.getenv("DB_NAME", "memescan")
        self.DB_USER = os.getenv("DB_USER", "postgres")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
        
        # Paramètres de scraping
        self.SCRAPING_INTERVAL = int(os.getenv("SCRAPING_INTERVAL", "300"))  # 5 minutes
        self.ANALYSIS_INTERVAL = int(os.getenv("ANALYSIS_INTERVAL", "600"))  # 10 minutes
        self.ML_PREDICTION_INTERVAL = int(os.getenv("ML_PREDICTION_INTERVAL", "300"))  # 5 minutes
        self.MAX_TOKENS_PER_CHAIN = int(os.getenv("MAX_TOKENS_PER_CHAIN", "1000"))
        self.TOKEN_AGE_DAYS = int(os.getenv("TOKEN_AGE_DAYS", "90"))  # 3 mois
        
        # Paramètres de logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_DIR = os.getenv("LOG_DIR", "logs")
        
        # Paramètres d'alerte
        self.DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        self.ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.8"))  # Seuil de confiance pour les alertes
        
        # Chemins des fichiers
        self.DATA_DIR = os.getenv("DATA_DIR", "data")
        self.EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")
        self.ML_MODELS_DIR = os.getenv("ML_MODELS_DIR", "models")
        
        # Paramètres ML
        self.ML_MODEL_URL = os.getenv("ML_MODEL_URL", "")
        self.ML_MODEL_TYPE = os.getenv("ML_MODEL_TYPE", "xgboost")
        
        # Paramètres de wallet
        self.WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
        self.PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
        
        # Paramètres de sniping
        self.SNIPING_ENABLED = os.getenv("SNIPING_ENABLED", "false").lower() == "true"
        self.MAX_TOKENS_PER_DAY = int(os.getenv("MAX_TOKENS_PER_DAY", "5"))
        self.MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "1000"))
        self.MAX_MARKET_CAP = float(os.getenv("MAX_MARKET_CAP", "10000"))
        self.MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.7"))
        self.DEFAULT_BUY_AMOUNT = float(os.getenv("DEFAULT_BUY_AMOUNT", "0.05"))
        self.GAS_BOOST = float(os.getenv("GAS_BOOST", "1.2"))
        self.SLIPPAGE = float(os.getenv("SLIPPAGE", "10"))
        
        # Paramètres de sécurité pour le sniping
        self.HONEYPOT_DETECTION = os.getenv("HONEYPOT_DETECTION", "true").lower() == "true"
        self.CONTRACT_VERIFICATION = os.getenv("CONTRACT_VERIFICATION", "true").lower() == "true"
        self.LIQUIDITY_LOCK_CHECK = os.getenv("LIQUIDITY_LOCK_CHECK", "true").lower() == "true"
        self.OWNERSHIP_RENOUNCED_CHECK = os.getenv("OWNERSHIP_RENOUNCED_CHECK", "true").lower() == "true"
        self.MAX_BUY_TAX = float(os.getenv("MAX_BUY_TAX", "10"))
        self.MAX_SELL_TAX = float(os.getenv("MAX_SELL_TAX", "15"))
        
        # Créer les répertoires nécessaires
        self._create_directories()
    
    def _create_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        Path(self.DATA_DIR).mkdir(exist_ok=True)
        Path(self.EXPORT_DIR).mkdir(exist_ok=True)
        Path(self.ML_MODELS_DIR).mkdir(exist_ok=True)
        Path(self.LOG_DIR).mkdir(exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la configuration en dictionnaire
        
        Returns:
            Dictionnaire de configuration
        """
        return {
            "rpc_urls": self.rpc_urls,
            "api_keys": {k: "***" for k in self.api_keys},  # Masquer les clés API
            "db": {
                "host": self.DB_HOST,
                "port": self.DB_PORT,
                "name": self.DB_NAME,
                "user": self.DB_USER,
                "password": "***"  # Masquer le mot de passe
            },
            "scraping": {
                "interval": self.SCRAPING_INTERVAL,
                "analysis_interval": self.ANALYSIS_INTERVAL,
                "ml_prediction_interval": self.ML_PREDICTION_INTERVAL,
                "max_tokens_per_chain": self.MAX_TOKENS_PER_CHAIN,
                "token_age_days": self.TOKEN_AGE_DAYS
            },
            "logging": {
                "level": self.LOG_LEVEL,
                "dir": self.LOG_DIR
            },
            "alerts": {
                "discord_webhook": bool(self.DISCORD_WEBHOOK),
                "telegram_enabled": bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID),
                "threshold": self.ALERT_THRESHOLD
            },
            "paths": {
                "data_dir": self.DATA_DIR,
                "export_dir": self.EXPORT_DIR,
                "ml_models_dir": self.ML_MODELS_DIR
            },
            "ml": {
                "model_url": bool(self.ML_MODEL_URL),
                "model_type": self.ML_MODEL_TYPE
            },
            "wallet": {
                "address": self.WALLET_ADDRESS,
                "private_key": bool(self.PRIVATE_KEY)
            },
            "sniping": {
                "enabled": self.SNIPING_ENABLED,
                "max_tokens_per_day": self.MAX_TOKENS_PER_DAY,
                "min_liquidity_usd": self.MIN_LIQUIDITY_USD,
                "max_market_cap": self.MAX_MARKET_CAP,
                "min_confidence_score": self.MIN_CONFIDENCE_SCORE,
                "default_buy_amount": self.DEFAULT_BUY_AMOUNT,
                "gas_boost": self.GAS_BOOST,
                "slippage": self.SLIPPAGE
            },
            "security": {
                "honeypot_detection": self.HONEYPOT_DETECTION,
                "contract_verification": self.CONTRACT_VERIFICATION,
                "liquidity_lock_check": self.LIQUIDITY_LOCK_CHECK,
                "ownership_renounced_check": self.OWNERSHIP_RENOUNCED_CHECK,
                "max_buy_tax": self.MAX_BUY_TAX,
                "max_sell_tax": self.MAX_SELL_TAX
            }
        } 