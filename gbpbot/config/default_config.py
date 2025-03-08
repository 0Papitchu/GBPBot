"""
Configuration par défaut pour le GBPBot
"""

# Configuration par défaut
DEFAULT_CONFIG = {
    # Configuration générale
    "general": {
        "log_level": "INFO",
        "log_file": "gbpbot.log",
        "simulation_mode": False,
        "testnet": False,
        "debug": False
    },
    
    # Configuration RPC
    "rpc": {
        "providers": {
            "avalanche": {
                "mainnet": [
                    {"url": "https://api.avax.network/ext/bc/C/rpc", "weight": 10},
                    {"url": "https://avalanche-c-chain.publicnode.com", "weight": 8},
                    {"url": "https://rpc.ankr.com/avalanche", "weight": 7}
                ]
            }
        },
        "timeout": 10,
        "max_retries": 3,
        "retry_delay": 1,
        "max_retry_delay": 30,
        "jitter": True,
        "batch_size": 10,
        "batch_interval": 0.5
    },
    
    # Configuration du cache
    "cache": {
        "rpc_ttl": 30,  # Durée de vie des résultats RPC en secondes
        "price_ttl": 10,  # Durée de vie des prix en secondes
        "max_rpc_items": 1000,  # Nombre maximum d'éléments dans le cache RPC
        "max_price_items": 100,  # Nombre maximum d'éléments dans le cache de prix
        "enabled": True  # Activer/désactiver le cache
    },
    
    # Configuration du cache distribué
    "distributed_cache": {
        "mode": "local",  # Mode de fonctionnement: "local" ou "redis"
        "local_cache_dir": None,  # Répertoire pour le cache local (None = utiliser tempdir)
        "redis_host": "localhost",  # Hôte Redis (pour mode "redis")
        "redis_port": 6379,  # Port Redis (pour mode "redis")
        "redis_password": None,  # Mot de passe Redis (pour mode "redis")
        "redis_db": 0,  # Base de données Redis (pour mode "redis")
        "prefix": "gbpbot:",  # Préfixe pour les clés de cache
        "default_ttl": 600,  # Durée de vie par défaut en secondes (10 minutes)
        "enable_compression": True,  # Activer la compression des données (pour économiser de l'espace)
        "max_memory": "100MB",  # Limite de mémoire pour le cache
        "eviction_policy": "lru",  # Politique d'éviction: "lru", "lfu", "fifo"
        "sync_interval": 60,  # Intervalle de synchronisation en secondes
        "persistent": True,  # Sauvegarder le cache sur disque pour récupération après redémarrage
        "replica_sync": False,  # Synchroniser avec les réplicas Redis si disponibles
        "fallback_to_local": True,  # Basculer en mode local si Redis est indisponible
    },
    
    # Configuration du moniteur de performance
    "performance_monitor": {
        "enabled": True,  # Activer/désactiver le monitoring des performances
        "monitoring_interval": 5.0,  # Intervalle de collecte des métriques en secondes
        "log_interval": 60.0,  # Intervalle d'enregistrement des métriques dans le log en secondes
        "cpu_alert_threshold": 90.0,  # Seuil d'alerte pour l'utilisation CPU en pourcentage
        "memory_alert_threshold": 85.0,  # Seuil d'alerte pour l'utilisation de la mémoire en pourcentage
        "disk_alert_threshold": 95.0,  # Seuil d'alerte pour l'utilisation du disque en pourcentage
        "tx_latency_alert_threshold": 10.0,  # Seuil d'alerte pour la latence des transactions en secondes
        "rpc_time_alert_threshold": 5.0,  # Seuil d'alerte pour le temps de réponse RPC en secondes
        "metrics_storage_dir": "metrics",  # Répertoire pour stocker les métriques exportées
        "metrics_retention_days": 30,  # Nombre de jours de rétention des métriques
        "alert_notifications": {
            "enabled": True,  # Activer/désactiver les notifications d'alerte
            "email": False,  # Envoyer des alertes par email
            "telegram": False,  # Envoyer des alertes par Telegram
            "discord": False,  # Envoyer des alertes par Discord
            "cooldown_period": 300  # Période de cooldown entre les alertes en secondes
        },
        "custom_metrics": {
            # Métriques personnalisées
            "arbitrage_profit": {
                "max_history": 1000,
                "alert_threshold": None
            },
            "sniper_success_rate": {
                "max_history": 1000,
                "alert_threshold": 50.0  # Alerte si le taux de succès descend en dessous de 50%
            }
        },
        "export_settings": {
            "auto_export": False,  # Exporter automatiquement les métriques
            "export_interval": 3600,  # Intervalle d'exportation en secondes (1 heure)
            "format": "csv"  # Format d'exportation: "csv" ou "json"
        },
        "hardware_optimization": {
            "auto_adapt": True,  # Adapter automatiquement les paramètres en fonction des ressources disponibles
            "low_resource_mode": False,  # Mode économie de ressources (à activer manuellement ou automatiquement)
            "cpu_target_usage": 70.0,  # Utilisation CPU cible en pourcentage
            "memory_target_usage": 60.0  # Utilisation mémoire cible en pourcentage
        }
    },
    
    # Configuration WebSocket
    "websocket": {
        "reconnect_interval": 5,  # Intervalle de reconnexion en secondes
        "max_reconnect_attempts": 5,  # Nombre maximum de tentatives de reconnexion
        "heartbeat_interval": 30,  # Intervalle de heartbeat en secondes
        "connection_timeout": 10,  # Timeout de connexion en secondes
        "max_backoff": 60,  # Backoff maximum en secondes
        "pairs": [
            "avaxusdt",
            "avaxusdc"
        ]
    },
    
    # Configuration des échanges
    "exchanges": {
        "binance": {
            "api_key": "",
            "api_secret": "",
            "enabled": True
        },
        "kucoin": {
            "api_key": "",
            "api_secret": "",
            "passphrase": "",
            "enabled": False
        }
    },
    
    # Configuration des contrats
    "contracts": {
        "mainnet": {
            "router": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",  # TraderJoe V2 Router
            "factory": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10",  # TraderJoe V2 Factory
            "tokens": {
                "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
                "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
                "JOE": "0x6e84a6216eA6dACC71eE8E6b0a5B7322EEbC0fDd"
            }
        },
        "testnet": {
            "router": "0x7E2f4A0e85A8A248E5Bc5B3Ee5f3dD214C5bC935",  # TraderJoe V2 Router (Fuji)
            "factory": "0x6E557F3dd43210E8bD7C54de1E3c6AE5a4fe6431",  # TraderJoe V2 Factory (Fuji)
            "tokens": {
                "WAVAX": "0xd00ae08403B9bbb9124bB305C09058E32C39A48c",
                "USDC": "0x5425890298aed601595a70AB815c96711a31Bc65",
                "USDT": "0x02823f9B469960Bb3b1de0B3746D4b95B7E35543",
                "JOE": "0x477Fd10Db0D80eAFb773cF623B258313C3739413"
            }
        }
    },
    
    # Configuration des flux de prix
    "price_feed": {
        "cache_timeout": 5,           # Durée de vie du cache en secondes
        "update_interval": 5,          # Intervalle de mise à jour en secondes
        "dex_update_interval": 5,      # Intervalle de mise à jour DEX en secondes
        "cex_update_interval": 5,      # Intervalle de mise à jour CEX en secondes
        "opportunity_update_interval": 10,  # Intervalle de mise à jour des opportunités en secondes
        "use_oracle": False,           # Utiliser les oracles de prix
        "outlier_threshold": 2.0,      # Seuil pour la détection des outliers (écarts-types)
        "min_sources": 2,              # Nombre minimum de sources pour la normalisation
        "max_deviation": 0.05,         # Écart maximum autorisé entre sources (5%)
        "history_size": 50,            # Taille de l'historique des prix pour la volatilité
        "volatility_threshold": 0.03,  # Seuil de volatilité (3%)
        "min_spread": 0.01,            # Spread minimum pour les opportunités d'arbitrage (1%)
        "min_arbitrage_profit": 5.0,   # Profit minimum en USD pour les opportunités d'arbitrage
        "gas_cost_estimate": 2.0,      # Coût estimé du gaz en USD
        
        # Configuration des paires surveillées
        "pairs": [
            "WAVAX/USDC",
            "WAVAX/USDT",
            "USDC/USDT"
        ],
        
        # Configuration des paires WebSocket
        "websocket_pairs": [
            "WAVAX/USDC",
            "WAVAX/USDT"
        ],
        
        # Configuration des seuils de stop-loss/take-profit
        "stop_loss": {
            "default_percent": 0.05,   # 5% sous le prix d'entrée
            "enabled": True
        },
        "take_profit": {
            "default_percent": 0.1,    # 10% au-dessus du prix d'entrée
            "enabled": True
        }
    },
    
    # Configuration des stratégies
    "strategies": {
        "arbitrage": {
            "enabled": True,
            "min_profit_threshold": 0.5,  # Seuil de profit minimum en pourcentage
            "gas_price_multiplier": 1.1,  # Multiplicateur du prix du gaz
            "max_slippage": 0.5,  # Slippage maximum en pourcentage
            "max_gas": 1000000,  # Gaz maximum pour une transaction
            "pairs": [
                ["WAVAX", "USDC"],
                ["WAVAX", "USDT"],
                ["USDC", "USDT"]
            ]
        }
    },
    
    # Configuration de la détection d'anomalies
    "anomaly_detection": {
        "enabled": True,
        "window_size": 20,  # Taille de la fenêtre pour la détection d'anomalies
        "z_score_threshold": 3.0,  # Seuil de score Z pour la détection d'anomalies
        "min_data_points": 10,  # Nombre minimum de points de données requis
        "check_interval": 5  # Intervalle de vérification en secondes
    },
    
    # Configuration de la rééquilibrage du portefeuille
    "portfolio": {
        "target_wavax_ratio": 0.5,     # 50% du portefeuille en WAVAX
        "ratio_threshold": 0.2,        # Tolérance de 20% sur le ratio
        "min_wavax_balance": 1.0,      # Seuil minimum absolu de WAVAX
        "max_rebalance_frequency": 3600,  # Fréquence maximale de rééquilibrage (secondes)
        "stablecoin_preference": ["USDC", "USDT"]  # Préférence de stablecoin
    },
    
    # Configuration des tokens
    "tokens": {
        "WAVAX": {
            "address": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
            "decimals": 18,
            "symbol": "WAVAX",
            "name": "Wrapped AVAX",
            "is_stablecoin": False,
            "is_native": True,
            "initial_balance": 5.0  # Pour le mode simulation
        },
        "USDC": {
            "address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
            "decimals": 6,
            "symbol": "USDC",
            "name": "USD Coin",
            "is_stablecoin": True,
            "is_native": False,
            "initial_balance": 1000.0  # Pour le mode simulation
        },
        "USDT": {
            "address": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
            "decimals": 6,
            "symbol": "USDT",
            "name": "Tether USD",
            "is_stablecoin": True,
            "is_native": False,
            "initial_balance": 1000.0  # Pour le mode simulation
        },
        "WETH": {
            "address": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
            "decimals": 18,
            "symbol": "WETH.e",
            "name": "Wrapped Ether",
            "is_stablecoin": False,
            "is_native": False,
            "initial_balance": 0.5  # Pour le mode simulation
        }
    }
} 