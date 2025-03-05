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