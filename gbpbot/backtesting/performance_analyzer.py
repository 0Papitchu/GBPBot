#!/usr/bin/env python3
"""
Module d'analyse de performance pour le backtesting de GBPBot.

Ce module fournit des fonctionnalités pour analyser les performances des stratégies
de trading testées en backtesting, calculer des métriques de performance et générer
des rapports détaillés.
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration du logger
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Classe pour analyser les performances des stratégies de trading.
    
    Cette classe fournit des méthodes pour calculer diverses métriques de performance,
    générer des visualisations et produire des rapports détaillés sur les résultats
    des backtests.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'analyseur de performance.
        
        Args:
            config: Configuration pour l'analyseur de performance
        """
        self.config = config
        
        # Paramètres d'analyse
        self.risk_free_rate = float(config.get("RISK_FREE_RATE", 0.02))  # 2% par défaut
        self.benchmark_symbol = config.get("BENCHMARK_SYMBOL", "BTC/USDT")
        self.report_dir = config.get("REPORT_DIR", "reports")
        self.trading_days_per_year = int(config.get("TRADING_DAYS_PER_YEAR", 365))
        
        # Créer le répertoire de rapports s'il n'existe pas
        os.makedirs(self.report_dir, exist_ok=True)
        
        logger.info("Analyseur de performance initialisé")
    
    def analyze_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyse une liste de trades pour calculer diverses métriques de performance.
        
        Args:
            trades: Liste des trades à analyser
            
        Returns:
            Métriques de performance calculées
        """
        if not trades:
            logger.warning("Aucun trade à analyser")
            return {
                "total_trades": 0,
                "profitable_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "average_profit": 0.0,
                "average_loss": 0.0,
                "largest_profit": 0.0,
                "largest_loss": 0.0,
                "average_holding_time": timedelta(0),
                "total_fees": 0.0
            }
        
        # Calculer les métriques de base
        total_trades = len(trades)
        profitable_trades = sum(1 for trade in trades if trade.get("pnl", 0) > 0)
        losing_trades = sum(1 for trade in trades if trade.get("pnl", 0) < 0)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Calculer les profits et pertes
        total_profit = sum(trade.get("pnl", 0) for trade in trades if trade.get("pnl", 0) > 0)
        total_loss = abs(sum(trade.get("pnl", 0) for trade in trades if trade.get("pnl", 0) < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        total_pnl = sum(trade.get("pnl", 0) for trade in trades)
        
        # Calculer les moyennes
        average_profit = total_profit / profitable_trades if profitable_trades > 0 else 0
        average_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Trouver les extrêmes
        largest_profit = max((trade.get("pnl", 0) for trade in trades), default=0)
        largest_loss = min((trade.get("pnl", 0) for trade in trades), default=0)
        
        # Calculer les durées de détention
        holding_times = []
        for trade in trades:
            if "entry_time" in trade and "exit_time" in trade:
                entry_time = trade["entry_time"]
                exit_time = trade["exit_time"]
                
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                
                if isinstance(exit_time, str):
                    exit_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                
                holding_time = exit_time - entry_time
                holding_times.append(holding_time)
        
        average_holding_time = sum(holding_times, timedelta(0)) / len(holding_times) if holding_times else timedelta(0)
        
        # Calculer les frais totaux
        total_fees = sum(trade.get("fee", 0) for trade in trades)
        
        # Retourner les métriques calculées
        return {
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "average_profit": average_profit,
            "average_loss": average_loss,
            "largest_profit": largest_profit,
            "largest_loss": largest_loss,
            "average_holding_time": average_holding_time,
            "total_fees": total_fees
        }
    
    def calculate_equity_curve(self, trades: List[Dict[str, Any]], initial_capital: float) -> pd.DataFrame:
        """
        Calcule la courbe d'équité à partir d'une liste de trades.
        
        Args:
            trades: Liste des trades
            initial_capital: Capital initial
            
        Returns:
            DataFrame contenant la courbe d'équité
        """
        if not trades:
            logger.warning("Aucun trade pour calculer la courbe d'équité")
            return pd.DataFrame(columns=["timestamp", "equity"])
        
        # Trier les trades par date
        sorted_trades = sorted(trades, key=lambda x: x.get("exit_time", datetime.min))
        
        # Créer la courbe d'équité
        equity_points = []
        current_equity = initial_capital
        
        for trade in sorted_trades:
            pnl = trade.get("pnl", 0)
            current_equity += pnl
            
            exit_time = trade.get("exit_time")
            if isinstance(exit_time, str):
                exit_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            
            equity_points.append({
                "timestamp": exit_time,
                "equity": current_equity
            })
        
        # Convertir en DataFrame
        df = pd.DataFrame(equity_points)
        if not df.empty:
            df.set_index("timestamp", inplace=True)
        
        return df
    
    def calculate_drawdowns(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les drawdowns à partir de la courbe d'équité.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            
        Returns:
            DataFrame contenant les drawdowns
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour le calcul des drawdowns")
            return pd.DataFrame(columns=["timestamp", "equity", "peak", "drawdown", "drawdown_pct"])
        
        # Calculer les pics (maximum cumulatif)
        equity_curve["peak"] = equity_curve["equity"].cummax()
        
        # Calculer les drawdowns
        equity_curve["drawdown"] = equity_curve["peak"] - equity_curve["equity"]
        equity_curve["drawdown_pct"] = equity_curve["drawdown"] / equity_curve["peak"] * 100
        
        return equity_curve
    
    def calculate_max_drawdown(self, equity_curve: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcule le drawdown maximum à partir de la courbe d'équité.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            
        Returns:
            Informations sur le drawdown maximum
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour le calcul du drawdown maximum")
            return {
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "max_drawdown_start": None,
                "max_drawdown_end": None,
                "max_drawdown_duration": timedelta(0)
            }
        
        # Calculer les drawdowns
        drawdowns = self.calculate_drawdowns(equity_curve)
        
        # Trouver le drawdown maximum
        max_dd_idx = drawdowns["drawdown"].idxmax()
        max_dd = drawdowns.loc[max_dd_idx, "drawdown"]
        max_dd_pct = drawdowns.loc[max_dd_idx, "drawdown_pct"]
        
        # Trouver le début du drawdown maximum
        peak_idx = drawdowns[:max_dd_idx]["equity"].idxmax()
        
        # Calculer la durée du drawdown
        dd_duration = max_dd_idx - peak_idx if peak_idx is not None else timedelta(0)
        
        return {
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_start": peak_idx,
            "max_drawdown_end": max_dd_idx,
            "max_drawdown_duration": dd_duration
        }
    
    def calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """
        Calcule le ratio de Sharpe.
        
        Args:
            returns: Série de rendements
            
        Returns:
            Ratio de Sharpe
        """
        if returns.empty:
            logger.warning("Série de rendements vide pour le calcul du ratio de Sharpe")
            return 0.0
        
        # Calculer le rendement moyen et l'écart-type
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Calculer le ratio de Sharpe
        if std_return == 0:
            return 0.0
        
        # Annualiser le ratio de Sharpe
        sharpe_ratio = (mean_return - self.risk_free_rate / self.trading_days_per_year) / std_return
        sharpe_ratio_annualized = sharpe_ratio * np.sqrt(self.trading_days_per_year)
        
        return sharpe_ratio_annualized
    
    def calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """
        Calcule le ratio de Sortino.
        
        Args:
            returns: Série de rendements
            
        Returns:
            Ratio de Sortino
        """
        if returns.empty:
            logger.warning("Série de rendements vide pour le calcul du ratio de Sortino")
            return 0.0
        
        # Calculer le rendement moyen
        mean_return = returns.mean()
        
        # Calculer l'écart-type des rendements négatifs
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() if not negative_returns.empty else 0
        
        # Calculer le ratio de Sortino
        if downside_std == 0:
            return 0.0
        
        # Annualiser le ratio de Sortino
        sortino_ratio = (mean_return - self.risk_free_rate / self.trading_days_per_year) / downside_std
        sortino_ratio_annualized = sortino_ratio * np.sqrt(self.trading_days_per_year)
        
        return sortino_ratio_annualized
    
    def calculate_calmar_ratio(self, returns: pd.Series, max_drawdown_pct: float) -> float:
        """
        Calcule le ratio de Calmar.
        
        Args:
            returns: Série de rendements
            max_drawdown_pct: Drawdown maximum en pourcentage
            
        Returns:
            Ratio de Calmar
        """
        if returns.empty or max_drawdown_pct == 0:
            logger.warning("Données insuffisantes pour le calcul du ratio de Calmar")
            return 0.0
        
        # Calculer le rendement annualisé
        total_return = (1 + returns).prod() - 1
        years = len(returns) / self.trading_days_per_year
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Calculer le ratio de Calmar
        calmar_ratio = annualized_return / (max_drawdown_pct / 100)
        
        return calmar_ratio
    
    def calculate_returns(self, equity_curve: pd.DataFrame) -> pd.Series:
        """
        Calcule les rendements à partir de la courbe d'équité.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            
        Returns:
            Série de rendements
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour le calcul des rendements")
            return pd.Series()
        
        # Calculer les rendements
        returns = equity_curve["equity"].pct_change().dropna()
        
        return returns
    
    def calculate_monthly_returns(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les rendements mensuels à partir de la courbe d'équité.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            
        Returns:
            DataFrame contenant les rendements mensuels
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour le calcul des rendements mensuels")
            return pd.DataFrame()
        
        # Rééchantillonner la courbe d'équité par mois
        monthly_equity = equity_curve["equity"].resample("M").last()
        
        # Calculer les rendements mensuels
        monthly_returns = monthly_equity.pct_change().dropna()
        
        # Convertir en DataFrame
        monthly_returns_df = pd.DataFrame(monthly_returns)
        monthly_returns_df.columns = ["return"]
        
        return monthly_returns_df
    
    def plot_equity_curve(self, equity_curve: pd.DataFrame, title: str = "Equity Curve") -> plt.Figure:
        """
        Génère un graphique de la courbe d'équité.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            title: Titre du graphique
            
        Returns:
            Figure matplotlib
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour la génération du graphique")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title(title)
            ax.set_xlabel("Date")
            ax.set_ylabel("Equity")
            return fig
        
        # Créer la figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Tracer la courbe d'équité
        ax.plot(equity_curve.index, equity_curve["equity"], label="Equity")
        
        # Ajouter les drawdowns
        if "drawdown" in equity_curve.columns:
            # Trouver les périodes de drawdown
            is_drawdown = equity_curve["drawdown"] > 0
            
            # Colorier les périodes de drawdown
            for i in range(len(is_drawdown)):
                if is_drawdown.iloc[i]:
                    ax.axvspan(is_drawdown.index[i], is_drawdown.index[i], alpha=0.2, color="red")
        
        # Ajouter les labels et la légende
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity")
        ax.legend()
        
        # Formater l'axe des dates
        fig.autofmt_xdate()
        
        return fig
    
    def plot_drawdowns(self, equity_curve: pd.DataFrame, title: str = "Drawdowns") -> plt.Figure:
        """
        Génère un graphique des drawdowns.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            title: Titre du graphique
            
        Returns:
            Figure matplotlib
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour la génération du graphique des drawdowns")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title(title)
            ax.set_xlabel("Date")
            ax.set_ylabel("Drawdown (%)")
            return fig
        
        # Calculer les drawdowns
        drawdowns = self.calculate_drawdowns(equity_curve)
        
        # Créer la figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Tracer les drawdowns
        ax.fill_between(drawdowns.index, 0, -drawdowns["drawdown_pct"], color="red", alpha=0.3)
        ax.plot(drawdowns.index, -drawdowns["drawdown_pct"], color="red", label="Drawdown")
        
        # Ajouter les labels et la légende
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown (%)")
        ax.legend()
        
        # Formater l'axe des dates
        fig.autofmt_xdate()
        
        return fig
    
    def plot_monthly_returns(self, equity_curve: pd.DataFrame, title: str = "Monthly Returns") -> plt.Figure:
        """
        Génère un graphique des rendements mensuels.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            title: Titre du graphique
            
        Returns:
            Figure matplotlib
        """
        if equity_curve.empty:
            logger.warning("Courbe d'équité vide pour la génération du graphique des rendements mensuels")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title(title)
            ax.set_xlabel("Date")
            ax.set_ylabel("Return (%)")
            return fig
        
        # Calculer les rendements mensuels
        monthly_returns = self.calculate_monthly_returns(equity_curve)
        
        # Créer la figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Tracer les rendements mensuels
        colors = ["green" if r >= 0 else "red" for r in monthly_returns["return"]]
        ax.bar(monthly_returns.index, monthly_returns["return"] * 100, color=colors)
        
        # Ajouter les labels
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Return (%)")
        
        # Formater l'axe des dates
        fig.autofmt_xdate()
        
        return fig
    
    def generate_performance_report(self, trades: List[Dict[str, Any]], initial_capital: float, 
                                  benchmark_data: Optional[pd.DataFrame] = None,
                                  report_name: str = "performance_report") -> str:
        """
        Génère un rapport de performance complet.
        
        Args:
            trades: Liste des trades
            initial_capital: Capital initial
            benchmark_data: Données de benchmark (optionnel)
            report_name: Nom du rapport
            
        Returns:
            Chemin du rapport généré
        """
        # Calculer les métriques de performance
        metrics = self.analyze_trades(trades)
        
        # Calculer la courbe d'équité
        equity_curve = self.calculate_equity_curve(trades, initial_capital)
        
        # Calculer les drawdowns
        drawdowns = self.calculate_drawdowns(equity_curve)
        
        # Calculer le drawdown maximum
        max_drawdown = self.calculate_max_drawdown(equity_curve)
        
        # Calculer les rendements
        returns = self.calculate_returns(equity_curve)
        
        # Calculer les ratios
        sharpe_ratio = self.calculate_sharpe_ratio(returns)
        sortino_ratio = self.calculate_sortino_ratio(returns)
        calmar_ratio = self.calculate_calmar_ratio(returns, max_drawdown["max_drawdown_pct"])
        
        # Calculer les rendements mensuels
        monthly_returns = self.calculate_monthly_returns(equity_curve)
        
        # Générer les graphiques
        equity_fig = self.plot_equity_curve(equity_curve)
        drawdown_fig = self.plot_drawdowns(equity_curve)
        monthly_returns_fig = self.plot_monthly_returns(equity_curve)
        
        # Créer le rapport
        report = {
            "metrics": metrics,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "initial_capital": initial_capital,
            "final_capital": equity_curve["equity"].iloc[-1] if not equity_curve.empty else initial_capital,
            "total_return": (equity_curve["equity"].iloc[-1] / initial_capital - 1) * 100 if not equity_curve.empty else 0,
            "annualized_return": self._calculate_annualized_return(equity_curve, initial_capital),
            "trading_period": {
                "start": equity_curve.index[0] if not equity_curve.empty else None,
                "end": equity_curve.index[-1] if not equity_curve.empty else None,
                "days": (equity_curve.index[-1] - equity_curve.index[0]).days if not equity_curve.empty else 0
            }
        }
        
        # Sauvegarder le rapport
        report_path = os.path.join(self.report_dir, f"{report_name}.json")
        with open(report_path, "w") as f:
            # Convertir les objets non sérialisables
            report_json = self._prepare_report_for_json(report)
            json.dump(report_json, f, indent=4)
        
        # Sauvegarder les graphiques
        equity_fig.savefig(os.path.join(self.report_dir, f"{report_name}_equity.png"))
        drawdown_fig.savefig(os.path.join(self.report_dir, f"{report_name}_drawdowns.png"))
        monthly_returns_fig.savefig(os.path.join(self.report_dir, f"{report_name}_monthly_returns.png"))
        
        logger.info(f"Rapport de performance généré: {report_path}")
        
        return report_path
    
    def _calculate_annualized_return(self, equity_curve: pd.DataFrame, initial_capital: float) -> float:
        """
        Calcule le rendement annualisé.
        
        Args:
            equity_curve: DataFrame contenant la courbe d'équité
            initial_capital: Capital initial
            
        Returns:
            Rendement annualisé
        """
        if equity_curve.empty:
            return 0.0
        
        # Calculer le rendement total
        final_capital = equity_curve["equity"].iloc[-1]
        total_return = final_capital / initial_capital - 1
        
        # Calculer la durée en années
        start_date = equity_curve.index[0]
        end_date = equity_curve.index[-1]
        years = (end_date - start_date).days / 365
        
        # Calculer le rendement annualisé
        if years <= 0:
            return 0.0
        
        annualized_return = (1 + total_return) ** (1 / years) - 1
        
        return annualized_return * 100  # En pourcentage
    
    def _prepare_report_for_json(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prépare le rapport pour la sérialisation JSON.
        
        Args:
            report: Rapport à préparer
            
        Returns:
            Rapport préparé pour JSON
        """
        # Créer une copie du rapport
        report_copy = report.copy()
        
        # Convertir les objets datetime
        if "trading_period" in report_copy:
            if report_copy["trading_period"]["start"] is not None:
                report_copy["trading_period"]["start"] = report_copy["trading_period"]["start"].isoformat()
            if report_copy["trading_period"]["end"] is not None:
                report_copy["trading_period"]["end"] = report_copy["trading_period"]["end"].isoformat()
        
        # Convertir les objets timedelta
        if "metrics" in report_copy and "average_holding_time" in report_copy["metrics"]:
            report_copy["metrics"]["average_holding_time"] = report_copy["metrics"]["average_holding_time"].total_seconds()
        
        if "max_drawdown" in report_copy and "max_drawdown_duration" in report_copy["max_drawdown"]:
            if isinstance(report_copy["max_drawdown"]["max_drawdown_duration"], timedelta):
                report_copy["max_drawdown"]["max_drawdown_duration"] = report_copy["max_drawdown"]["max_drawdown_duration"].total_seconds()
        
        # Convertir les objets datetime dans max_drawdown
        if "max_drawdown" in report_copy:
            if report_copy["max_drawdown"]["max_drawdown_start"] is not None:
                report_copy["max_drawdown"]["max_drawdown_start"] = report_copy["max_drawdown"]["max_drawdown_start"].isoformat()
            if report_copy["max_drawdown"]["max_drawdown_end"] is not None:
                report_copy["max_drawdown"]["max_drawdown_end"] = report_copy["max_drawdown"]["max_drawdown_end"].isoformat()
        
        return report_copy 