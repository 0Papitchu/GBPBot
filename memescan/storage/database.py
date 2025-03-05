from typing import Dict, List, Optional, Union, Any
import asyncio
from datetime import datetime
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import pandas as pd
import os
from ..utils.config import Config

class Database:
    """Gestionnaire de base de données pour le stockage des données"""
    
    def __init__(self, config: Config, simulation_mode=False):
        """
        Initialise la connexion à la base de données
        
        Args:
            config: Configuration du système
            simulation_mode: Si True, utilise SQLite au lieu de PostgreSQL
        """
        self.config = config
        self.simulation_mode = simulation_mode
        
        # Vérifier si nous sommes en mode simulation
        if simulation_mode:
            # Utiliser SQLite pour la simulation
            sqlite_path = os.path.join("simulation_results", "simulation.db")
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
            
            self.engine = create_engine(f"sqlite:///{sqlite_path}")
            self.session = sessionmaker(self.engine)
            self.async_session = None
            logger.info(f"Using SQLite database for simulation at {sqlite_path}")
        else:
            # Connexion PostgreSQL pour le mode normal
            try:
                self.engine = create_async_engine(
                    f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}@"
                    f"{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
                )
                
                self.async_session = sessionmaker(
                    self.engine, class_=AsyncSession, expire_on_commit=False
                )
                logger.info("Connected to PostgreSQL database")
            except ImportError:
                logger.warning("asyncpg not installed, falling back to SQLite")
                # Fallback to SQLite if asyncpg is not available
                sqlite_path = os.path.join("simulation_results", "fallback.db")
                os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
                
                self.engine = create_engine(f"sqlite:///{sqlite_path}")
                self.session = sessionmaker(self.engine)
                self.async_session = None
        
    async def init_db(self):
        """Initialise la base de données et crée les tables si elles n'existent pas"""
        try:
            logger.info("Initializing database...")
            
            if self.simulation_mode or self.async_session is None:
                # Mode SQLite synchrone
                with self.engine.begin() as conn:
                    # Créer les tables pour la simulation uniquement
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS simulations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            start_time TIMESTAMP,
                            end_time TIMESTAMP,
                            initial_balance REAL,
                            final_balance REAL,
                            total_profit REAL,
                            total_trades INTEGER,
                            profitable_trades INTEGER,
                            win_rate REAL,
                            max_drawdown REAL
                        )
                    """))
                    
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS simulation_trades (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            simulation_id INTEGER,
                            token_symbol TEXT,
                            token_address TEXT,
                            type TEXT,
                            price REAL,
                            amount REAL,
                            value REAL,
                            timestamp TIMESTAMP,
                            profit_loss REAL,
                            profit_loss_pct REAL,
                            reason TEXT,
                            FOREIGN KEY (simulation_id) REFERENCES simulations(id)
                        )
                    """))
                
                logger.info("SQLite database initialized for simulation")
                return
            
            # Mode PostgreSQL asynchrone
            async with self.engine.begin() as conn:
                # Table des tokens
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tokens (
                        address VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255),
                        symbol VARCHAR(50),
                        chain VARCHAR(50),
                        decimals INTEGER,
                        total_supply NUMERIC,
                        created_at TIMESTAMP,
                        is_meme BOOLEAN DEFAULT FALSE
                    )
                """))
                
                # Table des métriques de tokens
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS token_metrics (
                        id SERIAL PRIMARY KEY,
                        token_address VARCHAR(255),
                        price NUMERIC,
                        volume_24h NUMERIC,
                        volume_1h NUMERIC,
                        tvl NUMERIC,
                        holders INTEGER,
                        transactions_24h INTEGER,
                        timestamp TIMESTAMP,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                # Table des transactions de wallets
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS wallet_transactions (
                        id SERIAL PRIMARY KEY,
                        wallet_address VARCHAR(255),
                        token_address VARCHAR(255),
                        transaction_hash VARCHAR(255),
                        transaction_type VARCHAR(50),
                        amount NUMERIC,
                        price NUMERIC,
                        timestamp TIMESTAMP,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                # Table des prédictions de tokens
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS token_predictions (
                        id SERIAL PRIMARY KEY,
                        token_address VARCHAR(255),
                        prediction_category VARCHAR(50),
                        confidence NUMERIC,
                        prediction_time TIMESTAMP,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                # Table des alertes
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS token_alerts (
                        id SERIAL PRIMARY KEY,
                        token_address VARCHAR(255),
                        alert_type VARCHAR(50),
                        alert_time TIMESTAMP,
                        confidence NUMERIC,
                        price NUMERIC,
                        additional_data JSONB,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ml_models (
                        id SERIAL PRIMARY KEY,
                        model_name VARCHAR(100),
                        model_type VARCHAR(50),
                        version VARCHAR(20),
                        created_at TIMESTAMP,
                        metrics JSONB,
                        file_path VARCHAR(255)
                    )
                """))
                
                # Table des prix sur différents DEX
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS dex_prices (
                        id SERIAL PRIMARY KEY,
                        token_address VARCHAR(255),
                        dex_name VARCHAR(50),
                        price NUMERIC,
                        liquidity NUMERIC,
                        volume_24h NUMERIC,
                        timestamp TIMESTAMP,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                # Table des événements de sniping
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS sniping_events (
                        id SERIAL PRIMARY KEY,
                        token_address VARCHAR(255),
                        token_symbol VARCHAR(50),
                        chain VARCHAR(50),
                        dex VARCHAR(50),
                        price NUMERIC,
                        liquidity NUMERIC,
                        market_cap NUMERIC,
                        is_meme BOOLEAN,
                        detection_time TIMESTAMP,
                        status VARCHAR(50),
                        analysis TEXT,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                # Table des snipes effectués
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS token_snipes (
                        id SERIAL PRIMARY KEY,
                        token_address VARCHAR(255),
                        token_symbol VARCHAR(50),
                        chain VARCHAR(50),
                        dex VARCHAR(50),
                        price NUMERIC,
                        amount NUMERIC,
                        tx_hash VARCHAR(255),
                        timestamp TIMESTAMP,
                        ml_score NUMERIC,
                        final_score NUMERIC,
                        status VARCHAR(50),
                        sell_price NUMERIC,
                        sell_tx_hash VARCHAR(255),
                        sell_timestamp TIMESTAMP,
                        profit_loss NUMERIC,
                        profit_loss_pct NUMERIC,
                        FOREIGN KEY (token_address) REFERENCES tokens(address)
                    )
                """))
                
                # Table des simulations
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS simulations (
                        id SERIAL PRIMARY KEY,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        initial_balance NUMERIC,
                        final_balance NUMERIC,
                        total_profit NUMERIC,
                        total_trades INTEGER,
                        profitable_trades INTEGER,
                        win_rate NUMERIC,
                        max_drawdown NUMERIC,
                        parameters JSONB
                    )
                """))
                
                # Table des trades simulés
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS simulation_trades (
                        id SERIAL PRIMARY KEY,
                        simulation_id INTEGER,
                        token_symbol VARCHAR(50),
                        token_address VARCHAR(255),
                        type VARCHAR(10),
                        price NUMERIC,
                        amount NUMERIC,
                        value NUMERIC,
                        timestamp TIMESTAMP,
                        profit_loss NUMERIC,
                        profit_loss_pct NUMERIC,
                        reason VARCHAR(50),
                        FOREIGN KEY (simulation_id) REFERENCES simulations(id)
                    )
                """))
                
                # Index pour améliorer les performances
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_token_metrics_token_address ON token_metrics(token_address);
                    CREATE INDEX IF NOT EXISTS idx_token_metrics_timestamp ON token_metrics(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_wallet_transactions_wallet ON wallet_transactions(wallet_address);
                    CREATE INDEX IF NOT EXISTS idx_token_predictions_category ON token_predictions(prediction_category);
                    CREATE INDEX IF NOT EXISTS idx_token_predictions_time ON token_predictions(prediction_time);
                    CREATE INDEX IF NOT EXISTS idx_token_alerts_time ON token_alerts(alert_time);
                    
                    -- Index pour les requêtes d'arbitrage
                    CREATE INDEX IF NOT EXISTS idx_dex_prices_token_timestamp ON dex_prices(token_address, timestamp DESC);
                    CREATE INDEX IF NOT EXISTS idx_dex_prices_dex_timestamp ON dex_prices(dex_name, timestamp DESC);
                    
                    -- Index pour les requêtes de sniping
                    CREATE INDEX IF NOT EXISTS idx_tokens_created_at ON tokens(created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_token_metrics_composite ON token_metrics(token_address, timestamp DESC);
                    
                    -- Index pour les événements de sniping
                    CREATE INDEX IF NOT EXISTS idx_sniping_events_status ON sniping_events(status);
                    CREATE INDEX IF NOT EXISTS idx_sniping_events_detection ON sniping_events(detection_time DESC);
                    
                    -- Index pour les snipes
                    CREATE INDEX IF NOT EXISTS idx_token_snipes_status ON token_snipes(status);
                    CREATE INDEX IF NOT EXISTS idx_token_snipes_timestamp ON token_snipes(timestamp DESC);
                """))
                
            logger.info("PostgreSQL database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if not self.simulation_mode and self.async_session is None:
                logger.info("Creating in-memory database for simulation")
                self.engine = create_engine("sqlite:///:memory:")
                self.session = sessionmaker(self.engine)
                with self.engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS simulations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            start_time TIMESTAMP,
                            end_time TIMESTAMP,
                            initial_balance REAL,
                            final_balance REAL,
                            total_profit REAL,
                            total_trades INTEGER,
                            profitable_trades INTEGER,
                            win_rate REAL,
                            max_drawdown REAL
                        )
                    """))
                    
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS simulation_trades (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            simulation_id INTEGER,
                            token_symbol TEXT,
                            token_address TEXT,
                            type TEXT,
                            price REAL,
                            amount REAL,
                            value REAL,
                            timestamp TIMESTAMP,
                            profit_loss REAL,
                            profit_loss_pct REAL,
                            reason TEXT,
                            FOREIGN KEY (simulation_id) REFERENCES simulations(id)
                        )
                    """))
            else:
                raise
            
    async def store_token(self, token_data: Dict):
        """
        Stocke les informations d'un token
        
        Args:
            token_data: Données du token à stocker
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO tokens (
                        address, chain, name, symbol, created_at,
                        total_supply, holders_count, last_updated
                    ) VALUES (
                        :address, :chain, :name, :symbol, :created_at,
                        :total_supply, :holders_count, NOW()
                    ) ON CONFLICT (address) DO UPDATE SET
                        holders_count = :holders_count,
                        last_updated = NOW()
                """)
                
                await session.execute(query, token_data)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing token data: {str(e)}")
            
    async def store_token_metrics(self, metrics: Dict):
        """
        Stocke les métriques d'un token
        
        Args:
            metrics: Métriques à stocker
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO token_metrics (
                        token_address, timestamp, volume_24h, volume_1h,
                        market_cap, tvl, price, holders, transactions_24h
                    ) VALUES (
                        :token_address, :timestamp, :volume_24h, :volume_1h,
                        :market_cap, :tvl, :price, :holders, :transactions_24h
                    )
                """)
                
                await session.execute(query, metrics)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing token metrics: {str(e)}")
            
    async def store_transaction(self, transaction: Dict):
        """
        Stocke une transaction
        
        Args:
            transaction: Données de la transaction
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO wallet_transactions (
                        wallet_address, token_address, type, amount,
                        price, timestamp, tx_hash
                    ) VALUES (
                        :wallet_address, :token_address, :type, :amount,
                        :price, :timestamp, :tx_hash
                    )
                """)
                
                await session.execute(query, transaction)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing transaction: {str(e)}")
            
    async def store_rug_pull(self, rug_pull: Dict):
        """
        Stocke les informations d'un rug pull détecté
        
        Args:
            rug_pull: Informations sur le rug pull
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO rug_pulls (
                        token_address, detected_at, severity,
                        description, lost_value
                    ) VALUES (
                        :token_address, :detected_at, :severity,
                        :description, :lost_value
                    )
                """)
                
                await session.execute(query, rug_pull)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing rug pull: {str(e)}")
            
    async def store_prediction(self, prediction: Dict):
        """
        Stocke une prédiction ML
        
        Args:
            prediction: Données de la prédiction
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO token_predictions (
                        token_address, prediction_category, confidence,
                        prediction_time, additional_data
                    ) VALUES (
                        :token_address, :prediction_category, :confidence,
                        :prediction_time, :additional_data
                    )
                """)
                
                await session.execute(query, prediction)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing prediction: {str(e)}")
            
    async def store_alert(self, alert: Dict):
        """
        Stocke une alerte
        
        Args:
            alert: Données de l'alerte
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO token_alerts (
                        token_address, alert_type, alert_time,
                        confidence, price, additional_data
                    ) VALUES (
                        :token_address, :alert_type, :alert_time,
                        :confidence, :price, :additional_data
                    )
                """)
                
                await session.execute(query, alert)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing alert: {str(e)}")
            
    async def store_ml_model(self, model_info: Dict):
        """
        Stocke les informations d'un modèle ML
        
        Args:
            model_info: Informations sur le modèle
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO ml_models (
                        model_name, model_type, version,
                        created_at, metrics, file_path
                    ) VALUES (
                        :model_name, :model_type, :version,
                        :created_at, :metrics, :file_path
                    )
                """)
                
                await session.execute(query, model_info)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing ML model info: {str(e)}")
            
    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict]:
        """
        Récupère l'historique des transactions d'un wallet
        
        Args:
            wallet_address: Adresse du wallet
            
        Returns:
            Liste des transactions
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT * FROM wallet_transactions
                    WHERE wallet_address = :wallet_address
                    ORDER BY timestamp DESC
                """)
                
                result = await session.execute(query, {"wallet_address": wallet_address})
                return [dict(row) for row in result]
                
        except Exception as e:
            logger.error(f"Error getting wallet transactions: {str(e)}")
            return []
            
    async def get_token_metrics(self, token_address: str,
                              start_time: Optional[datetime] = None) -> List[Dict]:
        """
        Récupère les métriques d'un token
        
        Args:
            token_address: Adresse du token
            start_time: Timestamp de début (optionnel)
            
        Returns:
            Liste des métriques
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT * FROM token_metrics
                    WHERE token_address = :token_address
                    AND (:start_time IS NULL OR timestamp >= :start_time)
                    ORDER BY timestamp DESC
                """)
                
                result = await session.execute(query, {
                    "token_address": token_address,
                    "start_time": start_time
                })
                return [dict(row) for row in result]
                
        except Exception as e:
            logger.error(f"Error getting token metrics: {str(e)}")
            return []
            
    async def get_rug_pulled_tokens(self) -> List[str]:
        """
        Récupère la liste des tokens ayant subi un rug pull
        
        Returns:
            Liste des adresses des tokens
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT DISTINCT token_address FROM rug_pulls
                """)
                
                result = await session.execute(query)
                return [row[0] for row in result]  # type: ignore
                
        except Exception as e:
            logger.error(f"Error getting rug pulled tokens: {str(e)}")
            return []
            
    async def get_wallet_involvement_in_tokens(self, wallet_address: str,
                                             token_addresses: List[str]) -> List[Dict]:
        """
        Vérifie l'implication d'un wallet dans une liste de tokens
        
        Args:
            wallet_address: Adresse du wallet
            token_addresses: Liste des adresses de tokens
            
        Returns:
            Liste des implications
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT 
                        t.token_address,
                        MIN(t.timestamp) as entry_time,
                        MAX(t.timestamp) as exit_time,
                        SUM(CASE WHEN t.type = 'buy' THEN t.amount * t.price ELSE 0 END) as total_bought,
                        SUM(CASE WHEN t.type = 'sell' THEN t.amount * t.price ELSE 0 END) as total_sold,
                        r.detected_at as rug_time
                    FROM wallet_transactions t
                    LEFT JOIN rug_pulls r ON t.token_address = r.token_address
                    WHERE t.wallet_address = :wallet_address
                    AND t.token_address = ANY(:token_addresses)
                    GROUP BY t.token_address, r.detected_at
                """)
                
                result = await session.execute(query, {
                    "wallet_address": wallet_address,
                    "token_addresses": token_addresses
                })
                
                involvement = []
                for row in result:
                    data = dict(row)
                    data["profit"] = data["total_sold"] - data["total_bought"]
                    involvement.append(data)
                    
                return involvement
                
        except Exception as e:
            logger.error(f"Error getting wallet involvement: {str(e)}")
            return []
            
    async def get_token_predictions(self, token_address: str = None, 
                                  category: str = None, 
                                  limit: int = 100) -> List[Dict]:
        """
        Récupère les prédictions pour un token ou une catégorie
        
        Args:
            token_address: Adresse du token (optionnel)
            category: Catégorie de prédiction (optionnel)
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des prédictions
        """
        try:
            async with self.async_session() as session:
                conditions = []
                params = {"limit": limit}
                
                if token_address:
                    conditions.append("token_address = :token_address")
                    params["token_address"] = token_address
                    
                if category:
                    conditions.append("prediction_category = :category")
                    params["category"] = category
                    
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                query = text(f"""
                    SELECT 
                        p.token_address, p.prediction_category, p.confidence,
                        p.prediction_time, p.additional_data,
                        t.name, t.symbol, t.chain
                    FROM token_predictions p
                    JOIN tokens t ON p.token_address = t.address
                    WHERE {where_clause}
                    ORDER BY p.prediction_time DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, params)
                return [dict(row) for row in result]
                
        except Exception as e:
            logger.error(f"Error getting token predictions: {str(e)}")
            return []
            
    async def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """
        Récupère les alertes récentes
        
        Args:
            limit: Nombre maximum d'alertes
            
        Returns:
            Liste des alertes
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT 
                        a.token_address, a.alert_type, a.alert_time,
                        a.confidence, a.price, a.additional_data,
                        t.name, t.symbol, t.chain
                    FROM token_alerts a
                    JOIN tokens t ON a.token_address = t.address
                    ORDER BY a.alert_time DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {"limit": limit})
                return [dict(row) for row in result]
                
        except Exception as e:
            logger.error(f"Error getting recent alerts: {str(e)}")
            return []
            
    async def get_ml_models(self) -> List[Dict]:
        """
        Récupère la liste des modèles ML
        
        Returns:
            Liste des modèles
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT * FROM ml_models
                    ORDER BY created_at DESC
                """)
                
                result = await session.execute(query)
                return [dict(row) for row in result]
                
        except Exception as e:
            logger.error(f"Error getting ML models: {str(e)}")
            return []
            
    async def export_to_csv(self, query_result: List[Dict], filename: str):
        """
        Exporte des résultats en CSV
        
        Args:
            query_result: Résultats à exporter
            filename: Nom du fichier
        """
        try:
            df = pd.DataFrame(query_result)
            df.to_csv(filename, index=False)
            logger.info(f"Data exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            
    async def close(self):
        """Ferme la connexion à la base de données"""
        await self.engine.dispose()

    async def store_dex_price(self, dex_price: Dict):
        """
        Stocke le prix d'un token sur un DEX
        
        Args:
            dex_price: Données du prix à stocker
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO dex_prices (
                        token_address, dex_name, price, liquidity,
                        volume_24h, timestamp
                    ) VALUES (
                        :token_address, :dex_name, :price, :liquidity,
                        :volume_24h, NOW()
                    )
                """)
                
                await session.execute(query, dex_price)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing DEX price: {str(e)}")

    async def store_sniping_event(self, event: Dict) -> Optional[int]:
        """
        Stocke un événement de sniping
        
        Args:
            event: Données de l'événement à stocker
            
        Returns:
            ID de l'événement créé ou None en cas d'erreur
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO sniping_events (
                        token_address, token_symbol, chain, dex,
                        price, liquidity, market_cap, is_meme,
                        detection_time, status, analysis
                    ) VALUES (
                        :token_address, :token_symbol, :chain, :dex,
                        :price, :liquidity, :market_cap, :is_meme,
                        :detection_time, :status, :analysis
                    )
                    RETURNING id
                """)
                
                result = await session.execute(query, event)
                event_id = result.scalar_one()
                await session.commit()
                
                return event_id
                
        except Exception as e:
            logger.error(f"Error storing sniping event: {str(e)}")
            return None

    async def update_sniping_event(self, event_id: int, status: str, analysis: str = None):
        """
        Met à jour le statut d'un événement de sniping
        
        Args:
            event_id: ID de l'événement
            status: Nouveau statut
            analysis: Résultat de l'analyse (optionnel)
        """
        try:
            async with self.async_session() as session:
                if analysis:
                    query = text("""
                        UPDATE sniping_events
                        SET status = :status, analysis = :analysis
                        WHERE id = :event_id
                    """)
                    params = {"event_id": event_id, "status": status, "analysis": analysis}
                else:
                    query = text("""
                        UPDATE sniping_events
                        SET status = :status
                        WHERE id = :event_id
                    """)
                    params = {"event_id": event_id, "status": status}
                    
                await session.execute(query, params)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating sniping event: {str(e)}")

    async def store_token_snipe(self, snipe: Dict) -> Optional[int]:
        """
        Stocke un snipe de token
        
        Args:
            snipe: Données du snipe à stocker
            
        Returns:
            ID du snipe créé ou None en cas d'erreur
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    INSERT INTO token_snipes (
                        token_address, token_symbol, chain, dex,
                        price, amount, tx_hash, timestamp,
                        ml_score, final_score, status
                    ) VALUES (
                        :token_address, :token_symbol, :chain, :dex,
                        :price, :amount, :tx_hash, :timestamp,
                        :ml_score, :final_score, :status
                    )
                    RETURNING id
                """)
                
                result = await session.execute(query, snipe)
                snipe_id = result.scalar_one()
                await session.commit()
                
                return snipe_id
                
        except Exception as e:
            logger.error(f"Error storing token snipe: {str(e)}")
            return None

    async def update_token_snipe_sell(self, snipe_id: int, sell_data: Dict):
        """
        Met à jour un snipe avec les informations de vente
        
        Args:
            snipe_id: ID du snipe
            sell_data: Données de la vente
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    UPDATE token_snipes
                    SET sell_price = :sell_price,
                        sell_tx_hash = :sell_tx_hash,
                        sell_timestamp = :sell_timestamp,
                        profit_loss = :profit_loss,
                        status = :status
                    WHERE id = :snipe_id
                """)
                
                params = {
                    "snipe_id": snipe_id,
                    "sell_price": sell_data["sell_price"],
                    "sell_tx_hash": sell_data["sell_tx_hash"],
                    "sell_timestamp": sell_data["sell_timestamp"],
                    "profit_loss": sell_data["profit_loss"],
                    "status": sell_data["status"]
                }
                    
                await session.execute(query, params)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating token snipe sell: {str(e)}")

    async def get_pending_sniping_events(self, limit: int = 10) -> List[Dict]:
        """
        Récupère les événements de sniping en attente
        
        Args:
            limit: Nombre maximum d'événements à récupérer
            
        Returns:
            Liste des événements en attente
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT 
                        id, token_address, token_symbol, chain, dex,
                        price, liquidity, market_cap, is_meme,
                        detection_time, status
                    FROM sniping_events
                    WHERE status = 'detected'
                    ORDER BY detection_time ASC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {"limit": limit})
                events = [dict(row) for row in result]
                
                return events
                
        except Exception as e:
            logger.error(f"Error getting pending sniping events: {str(e)}")
            return []

    async def get_active_snipes(self) -> List[Dict]:
        """
        Récupère les snipes actifs
        
        Returns:
            Liste des snipes actifs
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT 
                        id, token_address, token_symbol, chain, dex,
                        price, amount, tx_hash, timestamp,
                        ml_score, final_score, status
                    FROM token_snipes
                    WHERE status = 'active'
                    ORDER BY timestamp DESC
                """)
                
                result = await session.execute(query)
                snipes = [dict(row) for row in result]
                
                return snipes
                
        except Exception as e:
            logger.error(f"Error getting active snipes: {str(e)}")
            return []

    async def get_snipe_history(self, limit: int = 50) -> List[Dict]:
        """
        Récupère l'historique des snipes
        
        Args:
            limit: Nombre maximum de snipes à récupérer
            
        Returns:
            Liste des snipes
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT 
                        id, token_address, token_symbol, chain, dex,
                        price, amount, tx_hash, timestamp,
                        sell_price, sell_timestamp, profit_loss, status
                    FROM token_snipes
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {"limit": limit})
                snipes = [dict(row) for row in result]
                
                return snipes
                
        except Exception as e:
            logger.error(f"Error getting snipe history: {str(e)}")
            return []

    async def get_dex_prices(self, token_address: str) -> List[Dict]:
        """
        Récupère les prix d'un token sur différents DEX
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Liste des prix sur différents DEX
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    WITH latest_prices AS (
                        SELECT 
                            dex_name, 
                            MAX(timestamp) as latest_time
                        FROM dex_prices
                        WHERE token_address = :token_address
                        GROUP BY dex_name
                    )
                    SELECT 
                        d.token_address, d.dex_name, d.price, 
                        d.liquidity, d.volume_24h, d.timestamp
                    FROM dex_prices d
                    JOIN latest_prices lp ON 
                        d.dex_name = lp.dex_name AND 
                        d.timestamp = lp.latest_time
                    WHERE d.token_address = :token_address
                    ORDER BY d.dex_name
                """)
                
                result = await session.execute(query, {"token_address": token_address})
                prices = [dict(row) for row in result]
                
                return prices
                
        except Exception as e:
            logger.error(f"Error getting DEX prices: {str(e)}")
            return [] 