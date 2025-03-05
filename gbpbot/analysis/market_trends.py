from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

class MarketTrends:
    def __init__(self, db_connection):
        """
        Initialize market trends analyzer
        
        Args:
            db_connection: Database connection for storing/retrieving historical data
        """
        self.db = db_connection
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        
    async def analyze_historical_trends(self, days: int = 90) -> Dict:
        """
        Analyze MEME coin trends from the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary containing trend analysis results
        """
        try:
            # Get historical data from database
            start_date = datetime.now() - timedelta(days=days)
            historical_data = await self._get_historical_data(start_date)
            
            if not historical_data:
                logger.warning("No historical data available for analysis")
                return {}
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(historical_data)
            
            # Calculate key metrics
            trends = {
                "avg_pump_duration": self._calculate_avg_pump_duration(df),
                "typical_profit_levels": self._identify_profit_levels(df),
                "optimal_exit_times": self._analyze_exit_timing(df),
                "liquidity_patterns": self._analyze_liquidity_patterns(df),
                "whale_behavior": self._analyze_whale_behavior(df),
                "volume_patterns": self._analyze_volume_patterns(df)
            }
            
            # Detect market regime changes
            trends["market_regime"] = self._detect_market_regime(df)
            
            # Save analysis results
            await self._save_trend_analysis(trends)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing market trends: {str(e)}")
            return {}
    
    def _calculate_avg_pump_duration(self, df: pd.DataFrame) -> Dict:
        """Calculate average duration of price pumps"""
        pump_durations = []
        current_pump = {"start": None, "peak": 0}
        
        for idx, row in df.iterrows():
            price_change = row["price_change_pct"]
            
            if price_change > 20 and current_pump["start"] is None:  # Start of pump
                current_pump["start"] = row["timestamp"]
                current_pump["peak"] = price_change
            elif current_pump["start"] is not None:
                if price_change > current_pump["peak"]:
                    current_pump["peak"] = price_change
                elif price_change < 0:  # End of pump
                    duration = row["timestamp"] - current_pump["start"]
                    pump_durations.append({
                        "duration": duration.total_seconds() / 60,  # Convert to minutes
                        "peak": current_pump["peak"]
                    })
                    current_pump = {"start": None, "peak": 0}
        
        if not pump_durations:
            return {"avg_duration": 0, "avg_peak": 0}
            
        avg_duration = np.mean([p["duration"] for p in pump_durations])
        avg_peak = np.mean([p["peak"] for p in pump_durations])
        
        return {
            "avg_duration": avg_duration,
            "avg_peak": avg_peak,
            "distribution": self._calculate_duration_distribution(pump_durations)
        }
    
    def _identify_profit_levels(self, df: pd.DataFrame) -> Dict:
        """Identify common profit levels where dumps occur"""
        profit_dumps = []
        
        for idx, row in df.iterrows():
            if row["price_change_pct"] > 0 and row["volume_change_pct"] < -30:
                profit_dumps.append(row["price_change_pct"])
        
        if not profit_dumps:
            return {"levels": [], "frequency": {}}
            
        # Use KDE to find density peaks
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(profit_dumps)
        x_range = np.linspace(min(profit_dumps), max(profit_dumps), 100)
        density = kde(x_range)
        
        # Find local maxima in density
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(density)
        profit_levels = x_range[peaks]
        
        return {
            "levels": profit_levels.tolist(),
            "frequency": {
                f"x{int(level)}": len([x for x in profit_dumps if abs(x - level) < 5]) 
                for level in profit_levels
            }
        }
    
    def _analyze_exit_timing(self, df: pd.DataFrame) -> Dict:
        """Analyze optimal exit timing based on historical data"""
        successful_exits = []
        failed_exits = []
        
        for token_group in df.groupby("token_address"):
            token_data = token_group[1].sort_values("timestamp")
            
            max_profit = token_data["price_change_pct"].max()
            actual_exit = token_data["price_change_pct"].iloc[-1]
            
            exit_quality = actual_exit / max_profit if max_profit > 0 else 0
            
            exit_data = {
                "max_profit": max_profit,
                "actual_exit": actual_exit,
                "exit_quality": exit_quality,
                "volume_pattern": token_data["volume_change_pct"].tolist()[-5:],
                "whale_activity": token_data["whale_transactions"].tolist()[-5:]
            }
            
            if exit_quality > 0.8:
                successful_exits.append(exit_data)
            else:
                failed_exits.append(exit_data)
        
        return {
            "successful_patterns": self._extract_exit_patterns(successful_exits),
            "failed_patterns": self._extract_exit_patterns(failed_exits),
            "optimal_indicators": self._identify_optimal_indicators(successful_exits)
        }
    
    def _analyze_liquidity_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze liquidity patterns and their impact on price movement"""
        liquidity_impacts = []
        
        for token_group in df.groupby("token_address"):
            token_data = token_group[1].sort_values("timestamp")
            
            # Calculate correlation between liquidity and price changes
            correlation = token_data["liquidity_change_pct"].corr(token_data["price_change_pct"])
            
            # Analyze liquidity removal events
            liquidity_removals = token_data[token_data["liquidity_change_pct"] < -10]
            avg_price_impact = liquidity_removals["price_change_pct"].mean() if not liquidity_removals.empty else 0
            
            liquidity_impacts.append({
                "correlation": correlation,
                "avg_price_impact": avg_price_impact,
                "initial_liquidity": token_data["liquidity"].iloc[0],
                "max_price_reached": token_data["price_change_pct"].max()
            })
        
        return {
            "avg_correlation": np.mean([x["correlation"] for x in liquidity_impacts]),
            "price_impact_by_liquidity": self._group_by_liquidity_level(liquidity_impacts),
            "risk_levels": self._calculate_liquidity_risk_levels(liquidity_impacts)
        }
    
    def _analyze_whale_behavior(self, df: pd.DataFrame) -> Dict:
        """Analyze whale behavior patterns and their impact"""
        whale_patterns = []
        
        for token_group in df.groupby("token_address"):
            token_data = token_group[1].sort_values("timestamp")
            
            # Analyze whale accumulation phases
            whale_buys = token_data[token_data["whale_buy_volume"] > 0]
            whale_sells = token_data[token_data["whale_sell_volume"] > 0]
            
            pattern = {
                "avg_hold_time": self._calculate_whale_hold_time(whale_buys, whale_sells),
                "buy_pressure": whale_buys["whale_buy_volume"].sum() / token_data["total_volume"].sum(),
                "sell_pressure": whale_sells["whale_sell_volume"].sum() / token_data["total_volume"].sum(),
                "price_correlation": token_data["whale_net_volume"].corr(token_data["price_change_pct"])
            }
            
            whale_patterns.append(pattern)
        
        return {
            "avg_hold_time": np.mean([p["avg_hold_time"] for p in whale_patterns]),
            "typical_patterns": self._cluster_whale_patterns(whale_patterns),
            "price_impact": self._analyze_whale_price_impact(whale_patterns)
        }
    
    def _analyze_volume_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze volume patterns and their relationship with price movement"""
        volume_patterns = []
        
        for token_group in df.groupby("token_address"):
            token_data = token_group[1].sort_values("timestamp")
            
            # Calculate volume momentum
            token_data["volume_momentum"] = token_data["volume"].pct_change(3)
            
            pattern = {
                "volume_price_correlation": token_data["volume_momentum"].corr(token_data["price_change_pct"]),
                "avg_volume_spike": token_data[token_data["volume_change_pct"] > 100]["price_change_pct"].mean(),
                "volume_decay_pattern": self._calculate_volume_decay(token_data)
            }
            
            volume_patterns.append(pattern)
        
        return {
            "avg_correlation": np.mean([p["volume_price_correlation"] for p in volume_patterns]),
            "typical_decay_patterns": self._cluster_volume_patterns(volume_patterns),
            "momentum_indicators": self._extract_volume_momentum_indicators(volume_patterns)
        }
    
    def _detect_market_regime(self, df: pd.DataFrame) -> Dict:
        """Detect current market regime and its characteristics"""
        recent_data = df[df["timestamp"] > datetime.now() - timedelta(days=7)]
        
        regime = {
            "avg_pump_magnitude": recent_data["price_change_pct"].max(),
            "avg_dump_magnitude": recent_data["price_change_pct"].min(),
            "success_rate": len(recent_data[recent_data["price_change_pct"] > 0]) / len(recent_data),
            "avg_volume": recent_data["volume"].mean(),
            "whale_activity": recent_data["whale_transactions"].mean()
        }
        
        # Classify market regime
        if regime["avg_pump_magnitude"] > 500 and regime["success_rate"] > 0.7:
            regime["type"] = "bull_market"
        elif regime["avg_dump_magnitude"] < -50 and regime["success_rate"] < 0.3:
            regime["type"] = "bear_market"
        else:
            regime["type"] = "neutral_market"
        
        return regime
    
    async def _get_historical_data(self, start_date: datetime) -> List[Dict]:
        """Get historical trading data from database"""
        # TODO: Implement database query
        return []
    
    async def _save_trend_analysis(self, trends: Dict):
        """Save trend analysis results to database"""
        # TODO: Implement database save
        pass
    
    def _calculate_duration_distribution(self, pump_durations: List[Dict]) -> Dict:
        """Calculate distribution of pump durations"""
        durations = [p["duration"] for p in pump_durations]
        return {
            "min": np.min(durations),
            "max": np.max(durations),
            "median": np.median(durations),
            "std": np.std(durations),
            "percentiles": {
                "25": np.percentile(durations, 25),
                "75": np.percentile(durations, 75),
                "90": np.percentile(durations, 90)
            }
        }
    
    def _extract_exit_patterns(self, exits: List[Dict]) -> Dict:
        """Extract common patterns from exit data"""
        patterns = {
            "volume_patterns": [],
            "whale_patterns": []
        }
        
        for exit in exits:
            patterns["volume_patterns"].append(exit["volume_pattern"])
            patterns["whale_patterns"].append(exit["whale_activity"])
        
        return {
            "typical_volume_pattern": np.mean(patterns["volume_patterns"], axis=0).tolist(),
            "typical_whale_pattern": np.mean(patterns["whale_patterns"], axis=0).tolist()
        }
    
    def _identify_optimal_indicators(self, successful_exits: List[Dict]) -> Dict:
        """Identify indicators that predict successful exits"""
        indicators = {
            "min_profit": np.min([x["actual_exit"] for x in successful_exits]),
            "avg_volume_change": np.mean([np.mean(x["volume_pattern"]) for x in successful_exits]),
            "whale_activity_threshold": np.mean([np.sum(x["whale_activity"]) for x in successful_exits])
        }
        
        return indicators
    
    def _group_by_liquidity_level(self, liquidity_impacts: List[Dict]) -> Dict:
        """Group price impacts by liquidity level"""
        liquidity_levels = pd.qcut([x["initial_liquidity"] for x in liquidity_impacts], q=5)
        
        grouped_impacts = {}
        for level in range(5):
            level_impacts = [x["avg_price_impact"] for i, x in enumerate(liquidity_impacts) 
                           if liquidity_levels[i].left <= level <= liquidity_levels[i].right]
            grouped_impacts[f"level_{level+1}"] = np.mean(level_impacts)
        
        return grouped_impacts
    
    def _calculate_liquidity_risk_levels(self, liquidity_impacts: List[Dict]) -> Dict:
        """Calculate risk levels based on liquidity patterns"""
        correlations = [x["correlation"] for x in liquidity_impacts]
        price_impacts = [x["avg_price_impact"] for x in liquidity_impacts]
        
        risk_levels = {
            "high_risk": np.percentile(correlations, 75),
            "medium_risk": np.percentile(correlations, 50),
            "low_risk": np.percentile(correlations, 25),
            "price_impact_threshold": np.mean(price_impacts) + np.std(price_impacts)
        }
        
        return risk_levels
    
    def _calculate_whale_hold_time(self, whale_buys: pd.DataFrame, whale_sells: pd.DataFrame) -> float:
        """Calculate average hold time for whale positions"""
        if whale_buys.empty or whale_sells.empty:
            return 0
            
        buy_times = whale_buys["timestamp"].values
        sell_times = whale_sells["timestamp"].values
        
        hold_times = []
        for buy_time in buy_times:
            next_sell = sell_times[sell_times > buy_time]
            if len(next_sell) > 0:
                hold_time = (next_sell[0] - buy_time).total_seconds() / 60  # Convert to minutes
                hold_times.append(hold_time)
        
        return np.mean(hold_times) if hold_times else 0
    
    def _cluster_whale_patterns(self, whale_patterns: List[Dict]) -> Dict:
        """Cluster whale trading patterns"""
        from sklearn.cluster import KMeans
        
        features = np.array([[p["buy_pressure"], p["sell_pressure"], p["price_correlation"]] 
                           for p in whale_patterns])
        
        if len(features) < 3:
            return {"clusters": []}
            
        kmeans = KMeans(n_clusters=min(3, len(features)), random_state=42)
        clusters = kmeans.fit_predict(features)
        
        return {
            "clusters": [
                {
                    "buy_pressure": centroid[0],
                    "sell_pressure": centroid[1],
                    "price_correlation": centroid[2]
                }
                for centroid in kmeans.cluster_centers_
            ]
        }
    
    def _analyze_whale_price_impact(self, whale_patterns: List[Dict]) -> Dict:
        """Analyze price impact of whale activities"""
        correlations = [p["price_correlation"] for p in whale_patterns]
        
        return {
            "avg_correlation": np.mean(correlations),
            "std_correlation": np.std(correlations),
            "impact_threshold": np.mean(correlations) + np.std(correlations)
        }
    
    def _calculate_volume_decay(self, token_data: pd.DataFrame) -> List[float]:
        """Calculate volume decay pattern after peak"""
        peak_idx = token_data["volume"].idxmax()
        post_peak = token_data.loc[peak_idx:]["volume"].values
        
        if len(post_peak) < 5:
            return [1.0] * 5
            
        decay_pattern = post_peak[:5] / post_peak[0]
        return decay_pattern.tolist()
    
    def _cluster_volume_patterns(self, volume_patterns: List[Dict]) -> Dict:
        """Cluster volume decay patterns"""
        decay_patterns = np.array([p["volume_decay_pattern"] for p in volume_patterns])
        
        if len(decay_patterns) < 3:
            return {"clusters": []}
            
        kmeans = KMeans(n_clusters=min(3, len(decay_patterns)), random_state=42)
        clusters = kmeans.fit_predict(decay_patterns)
        
        return {
            "clusters": [
                {
                    "pattern": centroid.tolist(),
                    "description": self._describe_volume_pattern(centroid)
                }
                for centroid in kmeans.cluster_centers_
            ]
        }
    
    def _describe_volume_pattern(self, pattern: np.ndarray) -> str:
        """Generate description for volume pattern"""
        decay_rate = (pattern[0] - pattern[-1]) / len(pattern)
        
        if decay_rate > 0.5:
            return "rapid_decay"
        elif decay_rate > 0.2:
            return "moderate_decay"
        else:
            return "sustained_volume"
    
    def _extract_volume_momentum_indicators(self, volume_patterns: List[Dict]) -> Dict:
        """Extract volume momentum indicators"""
        correlations = [p["volume_price_correlation"] for p in volume_patterns]
        spike_impacts = [p["avg_volume_spike"] for p in volume_patterns if not np.isnan(p["avg_volume_spike"])]
        
        return {
            "momentum_threshold": np.mean(correlations) + np.std(correlations),
            "spike_impact_threshold": np.mean(spike_impacts) if spike_impacts else 0,
            "reliability_score": np.mean([abs(c) for c in correlations])
        } 