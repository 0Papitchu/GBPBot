from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np
from ..storage.database import Database
from ..utils.config import Config

class WalletAnalyzer:
    """Analyseur de comportement des wallets"""
    
    def __init__(self, config: Config, db: Database):
        """
        Initialise l'analyseur de wallets
        
        Args:
            config: Configuration du système
            db: Instance de la base de données
        """
        self.config = config
        self.db = db
        
        # Paramètres d'analyse
        self.params = {
            "min_transactions": 5,  # Nombre minimum de transactions pour l'analyse
            "whale_threshold": 0.05,  # 5% du supply pour être considéré comme whale
            "suspicious_buy_threshold": 0.02,  # 2% du supply en une transaction
            "suspicious_sell_threshold": 0.03,  # 3% du supply en une transaction
            "rug_pull_threshold": 0.5,  # 50% du supply vendu rapidement
            "rapid_movement_hours": 24,  # Période pour les mouvements rapides
            "profit_analysis_days": 30  # Période d'analyse de rentabilité
        }
        
    async def analyze_wallet(self, wallet_address: str) -> Dict:
        """
        Analyse complète d'un wallet
        
        Args:
            wallet_address: Adresse du wallet à analyser
            
        Returns:
            Dict contenant les résultats de l'analyse
        """
        try:
            # Récupérer l'historique des transactions
            transactions = await self.db.get_wallet_transactions(wallet_address)
            if not transactions:
                return {"error": "No transactions found"}
                
            # Convertir en DataFrame pour l'analyse
            df = pd.DataFrame(transactions)
            
            # Analyses
            token_involvement = self._analyze_token_involvement(df)
            trading_patterns = self._analyze_trading_patterns(df)
            rug_pull_history = await self._analyze_rug_pull_history(wallet_address)
            profitability = self._calculate_profitability(df)
            
            risk_score = self._calculate_risk_score(
                token_involvement,
                trading_patterns,
                rug_pull_history,
                profitability
            )
            
            return {
                "address": wallet_address,
                "risk_score": risk_score,
                "token_involvement": token_involvement,
                "trading_patterns": trading_patterns,
                "rug_pull_history": rug_pull_history,
                "profitability": profitability,
                "analysis_timestamp": datetime.now().timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing wallet {wallet_address}: {str(e)}")
            return {"error": str(e)}
            
    def _analyze_token_involvement(self, df: pd.DataFrame) -> Dict:
        """Analyse l'implication du wallet dans différents tokens"""
        try:
            # Grouper par token
            token_stats = df.groupby("token_address").agg({
                "amount": ["count", "sum"],
                "timestamp": ["min", "max"]
            })
            
            # Calculer les métriques
            involvement = {
                "total_tokens": len(token_stats),
                "active_tokens": len(df[df["timestamp"] > 
                    (datetime.now() - timedelta(days=7)).timestamp()]["token_address"].unique()),
                "most_traded_tokens": token_stats.sort_values(
                    ("amount", "count"), ascending=False).head(5).index.tolist(),
                "avg_holding_time": (token_stats["timestamp"]["max"] - 
                    token_stats["timestamp"]["min"]).mean() / 3600  # en heures
            }
            
            return involvement
            
        except Exception as e:
            logger.error(f"Error analyzing token involvement: {str(e)}")
            return {}
            
    def _analyze_trading_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyse les patterns de trading du wallet"""
        try:
            patterns = {
                "total_transactions": len(df),
                "buy_sell_ratio": len(df[df["type"] == "buy"]) / max(len(df[df["type"] == "sell"]), 1),
                "avg_transaction_size": df["amount"].mean(),
                "max_transaction_size": df["amount"].max(),
                "suspicious_movements": []
            }
            
            # Détecter les mouvements suspects
            for token in df["token_address"].unique():
                token_df = df[df["token_address"] == token]
                
                # Achats massifs
                large_buys = token_df[
                    (token_df["type"] == "buy") & 
                    (token_df["amount"] > self.params["suspicious_buy_threshold"])
                ]
                
                # Ventes massives
                large_sells = token_df[
                    (token_df["type"] == "sell") & 
                    (token_df["amount"] > self.params["suspicious_sell_threshold"])
                ]
                
                if not large_buys.empty or not large_sells.empty:
                    patterns["suspicious_movements"].append({
                        "token": token,
                        "large_buys": len(large_buys),
                        "large_sells": len(large_sells)
                    })
                    
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing trading patterns: {str(e)}")
            return {}
            
    async def _analyze_rug_pull_history(self, wallet_address: str) -> Dict:
        """Analyse l'historique de participation à des rug pulls"""
        try:
            # Récupérer les tokens rugpullés
            rug_pulled_tokens = await self.db.get_rug_pulled_tokens()
            
            # Vérifier l'implication du wallet
            involvement = await self.db.get_wallet_involvement_in_tokens(
                wallet_address,
                rug_pulled_tokens
            )
            
            history = {
                "total_rug_pulls": len(involvement),
                "profit_from_rugs": sum(inv["profit"] for inv in involvement),
                "avg_exit_time": np.mean([inv["exit_time"] for inv in involvement]),
                "suspected_involvement": any(
                    inv["exit_time"] < inv["rug_time"] for inv in involvement
                )
            }
            
            return history
            
        except Exception as e:
            logger.error(f"Error analyzing rug pull history: {str(e)}")
            return {}
            
    def _calculate_profitability(self, df: pd.DataFrame) -> Dict:
        """Calcule la rentabilité du wallet"""
        try:
            # Filtrer sur la période d'analyse
            start_time = (datetime.now() - 
                timedelta(days=self.params["profit_analysis_days"])).timestamp()
            recent_df = df[df["timestamp"] >= start_time]
            
            # Calculer les profits/pertes
            profits = []
            for token in recent_df["token_address"].unique():
                token_df = recent_df[recent_df["token_address"] == token]
                buys = token_df[token_df["type"] == "buy"]
                sells = token_df[token_df["type"] == "sell"]
                
                # Calculer le profit
                total_bought = (buys["amount"] * buys["price"]).sum()
                total_sold = (sells["amount"] * sells["price"]).sum()
                profit = total_sold - total_bought
                
                if profit != 0:
                    profits.append({
                        "token": token,
                        "profit": profit,
                        "roi": (profit / total_bought) if total_bought > 0 else 0
                    })
                    
            return {
                "total_profit": sum(p["profit"] for p in profits),
                "avg_roi": np.mean([p["roi"] for p in profits]),
                "profitable_trades": len([p for p in profits if p["profit"] > 0]),
                "losing_trades": len([p for p in profits if p["profit"] < 0]),
                "best_trades": sorted(profits, key=lambda x: x["roi"], reverse=True)[:3]
            }
            
        except Exception as e:
            logger.error(f"Error calculating profitability: {str(e)}")
            return {}
            
    def _calculate_risk_score(self, token_involvement: Dict, trading_patterns: Dict,
                            rug_pull_history: Dict, profitability: Dict) -> float:
        """Calcule le score de risque global du wallet"""
        try:
            score = 0.0
            
            # Facteurs de risque liés aux tokens
            if token_involvement.get("total_tokens", 0) < 3:
                score += 0.2  # Peu d'historique
            if token_involvement.get("avg_holding_time", 0) < 24:
                score += 0.3  # Trading très court terme
                
            # Facteurs liés au trading
            if trading_patterns.get("suspicious_movements"):
                score += len(trading_patterns["suspicious_movements"]) * 0.1
            if trading_patterns.get("buy_sell_ratio", 1) > 3:
                score += 0.2  # Déséquilibre achat/vente
                
            # Facteurs liés aux rug pulls
            if rug_pull_history.get("suspected_involvement", False):
                score += 0.5
            score += min(rug_pull_history.get("total_rug_pulls", 0) * 0.1, 0.5)
            
            # Facteurs liés à la rentabilité
            if profitability.get("avg_roi", 0) > 1.0:
                score += 0.2  # ROI anormalement élevé
                
            return min(score, 1.0)  # Score entre 0 et 1
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 1.0  # Score maximum en cas d'erreur 