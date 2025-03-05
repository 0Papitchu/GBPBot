from typing import Dict
from datetime import timedelta
import os

class TradingConfig:
    """Configuration optimisée pour le trading"""
    
    @staticmethod
    def get_simulation_config() -> Dict:
        """Configuration du mode simulation"""
        return {
            "simulation_duration": 43200,  # 12 heures
            "progressive_start": {
                "initial_amount": 1.0,    # 1 AVAX
                "max_amount": 5.0,        # 5 AVAX maximum
                "increment_step": 0.5,     # +0.5 AVAX
                "min_success_rate": 70,    # 70% de succès requis
                "success_threshold": 5      # 5 trades réussis avant augmentation
            },
            "wallet_monitoring": {
                "initial_capital": 5.0,    # 5 AVAX
                "min_balance_alert": 1.0,   # Alerte à 1 AVAX
                "max_balance_drop": 10.0    # 10% de perte max
            },
            "profit_transfer": {
                "threshold": 10.0,         # Transférer à partir de 10 USDT de profit
                "percentage": 30.0,        # Transférer 30% des profits
                "secure_wallet": os.getenv("SECURE_WALLET_ADDRESS", "0x0000000000000000000000000000000000000000")  # Adresse du wallet sécurisé
            }
        }
        
    @staticmethod
    def get_performance_config() -> Dict:
        """Configuration des métriques de performance"""
        return {
            "window_size": 100,          # Taille de la fenêtre d'analyse
            "min_success_rate": 60.0,    # 60% de succès minimum
            "max_loss_percent": -2.0,    # -2% de perte maximale
            "profit_target": 1.2,        # 1.2% de profit cible
            "gas_multipliers": {
                "low": 1.1,              # +10% pour priorité basse
                "normal": 1.3,           # +30% pour priorité normale
                "high": 1.5              # +50% pour priorité haute
            },
            "time_windows": {
                "1h": timedelta(hours=1),
                "4h": timedelta(hours=4),
                "24h": timedelta(hours=24)
            }
        }
        
    @staticmethod
    def get_opportunity_config() -> Dict:
        """Configuration de l'analyse des opportunités"""
        return {
            "min_profit_threshold": 0.5,  # 0.5% de profit minimum
            "max_slippage": 0.3,         # 0.3% de slippage maximum
            "min_liquidity": 2000,       # 2000 AVAX de liquidité minimum
            "short_window": 15,          # 15 secondes pour analyse rapide
            "long_window": 50,           # 50 secondes pour analyse approfondie
            "confidence_weights": {
                "price_impact": 0.4,     # 40% pour l'impact sur le prix
                "liquidity": 0.3,        # 30% pour la liquidité
                "volatility": 0.2,       # 20% pour la volatilité
                "volume": 0.1            # 10% pour le volume
            },
            "risk_levels": {
                "low": {
                    "min_profit": 1.0,    # 1.0% minimum pour risque faible
                    "max_slippage": 0.2,  # 0.2% slippage maximum
                    "min_liquidity": 3000  # 3000 AVAX minimum
                },
                "medium": {
                    "min_profit": 0.7,    # 0.7% minimum pour risque moyen
                    "max_slippage": 0.3,  # 0.3% slippage maximum
                    "min_liquidity": 2000  # 2000 AVAX minimum
                },
                "high": {
                    "min_profit": 0.5,    # 0.5% minimum pour risque élevé
                    "max_slippage": 0.4,  # 0.4% slippage maximum
                    "min_liquidity": 1000  # 1000 AVAX minimum
                }
            },
            "slippage": {
                "base": 0.1,             # 0.1% de base
                "max": 0.5               # 0.5% maximum
            }
        }
        
    @staticmethod
    def get_arbitrage_config() -> Dict:
        """Configuration de la stratégie d'arbitrage"""
        return {
            "monitoring_interval": 1,     # 1 seconde entre les vérifications
            "min_profit_percent": 0.5,    # 0.5% de profit minimum
            "max_slippage": 0.3,         # 0.3% de slippage maximum
            "gas_threshold": 500000,      # Seuil de gas maximum
            "min_amount_in": 0.5,        # 0.5 AVAX minimum par trade
            "max_amount_in": 5.0,        # 5 AVAX maximum par trade
            "capital_protection": {
                "max_daily_trades": 100,  # 100 trades maximum par jour
                "max_daily_loss": -5.0,   # -5% de perte maximale par jour
                "cooldown_period": 300    # 5 minutes de pause après une perte
            },
            "trade_validation": {
                "pre_trade_checks": True,
                "max_failure_streak": 3,   # 3 échecs consécutifs maximum
                "min_success_rate": 60.0   # 60% de succès minimum requis
            },
            "dex_settings": {
                "trader_joe": {
                    "router": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
                    "factory": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10",
                    "fee": 0.003  # 0.3% de frais
                },
                "pangolin": {
                    "router": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106",
                    "factory": "0xefa94DE7a4656D787667C749f7E1223D71E9FD88",
                    "fee": 0.003  # 0.3% de frais
                }
            },
            "cex_settings": {
                "binance": {
                    "fee": 0.001,  # 0.1% de frais
                    "min_order": 0.1  # 0.1 AVAX minimum
                },
                "kucoin": {
                    "fee": 0.001,  # 0.1% de frais
                    "min_order": 0.1  # 0.1 AVAX minimum
                },
                "gate": {
                    "fee": 0.002,  # 0.2% de frais
                    "min_order": 0.1  # 0.1 AVAX minimum
                }
            },
            "market_metrics": {
                "price_impact_threshold": 0.5,  # 0.5% d'impact maximum
                "liquidity_threshold": 2000,    # 2000 AVAX minimum
                "volume_threshold": 1000,       # 1000 AVAX de volume minimum
                "volatility_threshold": 2.0     # 2% de volatilité maximum
            },
            "transaction_optimization": {
                "max_pending_tx": 5,      # 5 transactions en attente maximum
                "tx_timeout": 180,        # 3 minutes de timeout
                "replacement_multiplier": 1.2,  # +20% de gas pour remplacer
                "priority_levels": {
                    "low": {
                        "base_fee_multiplier": 1.1,
                        "priority_fee": 2.0  # 2 Gwei
                    },
                    "normal": {
                        "base_fee_multiplier": 1.3,
                        "priority_fee": 3.0  # 3 Gwei
                    },
                    "high": {
                        "base_fee_multiplier": 1.5,
                        "priority_fee": 5.0  # 5 Gwei
                    }
                }
            }
        }
        
    @staticmethod
    def get_sniping_config() -> Dict:
        """Configuration de la stratégie de sniping de tokens"""
        return {
            "detection": {
                "min_liquidity": 5.0,  # Liquidité minimale en AVAX
                "max_buy_tax": 10,     # Taxe d'achat maximale en %
                "max_sell_tax": 10,    # Taxe de vente maximale en %
                "min_locked_liquidity_percent": 80,  # % minimum de liquidité bloquée
                "min_locked_time": 30 * 24 * 60 * 60,  # 30 jours minimum de lock
                "blacklist_tokens": [],  # Liste des tokens à ignorer
                "factory_addresses": {
                    "trader_joe": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10",
                    "pangolin": "0xefa94DE7a4656D787667C749f7E1223D71E9FD88"
                },
                "polling_interval": 1,  # Intervalle en secondes
                "honeypot_checker_api": "https://api.honeypot.is/v2/IsHoneypot"
            },
            "execution": {
                "initial_buy_amount": 0.1,  # Montant initial en AVAX
                "max_buy_amount": 0.5,      # Montant maximum en AVAX
                "gas_priority": "high",     # Priorité de gas pour les transactions
                "max_active_snipes": 5      # Nombre maximum de snipes actifs
            },
            "risk_management": {
                "take_profit": 30,          # Prendre profit à +30%
                "stop_loss": -15,           # Stop loss à -15%
                "trailing_stop": True,      # Activer le stop suiveur
                "trailing_percent": 5,      # % de trailing stop
                "profit_tiers": [
                    {"multiplier": 2.0, "percentage": 30},  # Vendre 30% à x2
                    {"multiplier": 5.0, "percentage": 50},  # Vendre 50% à x5
                    {"multiplier": 10.0, "percentage": 20}  # Vendre 20% à x10
                ],
                "emergency_exit_threshold": -30  # Sortie d'urgence à -30%
            },
            "security": {
                "contract_verification": {
                    "check_source_code": True,  # Vérifier si le code source est disponible
                    "check_copy_cats": True,    # Vérifier les copycats de contrats connus
                    "check_malicious_functions": True  # Vérifier les fonctions malveillantes
                },
                "whale_protection": {
                    "enabled": True,
                    "min_whale_amount": 1.0,  # Montant minimum en AVAX pour whale
                    "max_price_impact": 20    # Impact maximum sur le prix en %
                }
            },
            "notifications": {
                "new_token_alerts": True,    # Alertes pour les nouveaux tokens
                "trade_alerts": True,        # Alertes pour les trades
                "profit_loss_alerts": True   # Alertes pour les profits/pertes
            }
        }