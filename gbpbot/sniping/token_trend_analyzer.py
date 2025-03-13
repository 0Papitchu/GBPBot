"""
Analyseur de tendances des tokens pour GBPBot
==============================================

Ce module permet d'analyser les tendances des tokens similaires pour
identifier des patterns de croissance et optimiser les stratégies de sniping.
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass

from gbpbot.utils.logging_utils import setup_custom_logger
from gbpbot.config.trading_config import TradingConfig

logger = logging.getLogger("token_trend_analyzer")

@dataclass
class TokenMetrics:
    """Métriques d'un token pour l'analyse des tendances."""
    address: str
    name: str
    symbol: str
    category: str  # e.g., "meme", "defi", "utility"
    launch_date: Optional[datetime] = None
    
    # Métriques de croissance
    initial_price_usd: float = 0.0
    max_price_usd: float = 0.0
    current_price_usd: float = 0.0
    
    # Métriques de volume
    avg_daily_volume_usd: float = 0.0
    max_daily_volume_usd: float = 0.0
    
    # Métriques communautaires
    twitter_followers: int = 0
    telegram_members: int = 0
    
    # Métriques de performance
    peak_roi: float = 0.0  # Return on Investment au pic
    time_to_peak_hours: float = 0.0  # Temps pour atteindre le pic
    
    # Métriques de liquidité
    initial_liquidity_usd: float = 0.0
    max_liquidity_usd: float = 0.0
    current_liquidity_usd: float = 0.0

class TokenTrendAnalyzer:
    """
    Analyse les tendances de tokens similaires pour optimiser les stratégies de sniping.
    Utilise des données historiques pour identifier les patterns de succès.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'analyseur de tendances de tokens.
        
        Args:
            config: Configuration pour l'analyseur
        """
        self.config = config or {}
        self.trend_data_path = self.config.get("trend_data_path", "data/token_trends.json")
        
        # Base de données de tokens de référence
        self.reference_tokens: Dict[str, TokenMetrics] = {}
        
        # Seuils de similarité
        self.similarity_thresholds = {
            "high": 0.85,  # Haute similarité (85%+)
            "medium": 0.70,  # Similarité moyenne (70-85%)
            "low": 0.50  # Faible similarité (50-70%)
        }
        
        # Catégories de tokens
        self.token_categories = ["meme", "defi", "game", "ai", "utility"]
        
        # Facteurs de poids pour le calcul de similarité
        self.similarity_weights = {
            "category": 0.25,  # Catégorie du token
            "liquidity": 0.20,  # Liquidité initiale
            "community": 0.15,  # Force de la communauté
            "volume": 0.20,  # Volume de trading
            "blockchain": 0.10,  # Blockchain spécifique
            "launch_timing": 0.10  # Timing de lancement
        }
        
        # Initialiser le logger
        self.logger = setup_custom_logger("TokenTrendAnalyzer", logging.INFO)
        
        # Charger les données des tokens de référence
        self._load_reference_data()
        
    def _load_reference_data(self):
        """Charge les données des tokens de référence depuis le fichier JSON."""
        try:
            with open(self.trend_data_path, "r") as f:
                data = json.load(f)
                
            # Convertir les données JSON en objets TokenMetrics
            for token_data in data.get("tokens", []):
                # Convertir la date de lancement en objet datetime
                launch_date = None
                if token_data.get("launch_date"):
                    launch_date = datetime.fromisoformat(token_data["launch_date"])
                
                token = TokenMetrics(
                    address=token_data["address"],
                    name=token_data["name"],
                    symbol=token_data["symbol"],
                    category=token_data["category"],
                    launch_date=launch_date,
                    initial_price_usd=token_data.get("initial_price_usd", 0.0),
                    max_price_usd=token_data.get("max_price_usd", 0.0),
                    current_price_usd=token_data.get("current_price_usd", 0.0),
                    avg_daily_volume_usd=token_data.get("avg_daily_volume_usd", 0.0),
                    max_daily_volume_usd=token_data.get("max_daily_volume_usd", 0.0),
                    twitter_followers=token_data.get("twitter_followers", 0),
                    telegram_members=token_data.get("telegram_members", 0),
                    peak_roi=token_data.get("peak_roi", 0.0),
                    time_to_peak_hours=token_data.get("time_to_peak_hours", 0.0),
                    initial_liquidity_usd=token_data.get("initial_liquidity_usd", 0.0),
                    max_liquidity_usd=token_data.get("max_liquidity_usd", 0.0),
                    current_liquidity_usd=token_data.get("current_liquidity_usd", 0.0)
                )
                
                self.reference_tokens[token.address] = token
                
            self.logger.info(f"Loaded {len(self.reference_tokens)} reference tokens from {self.trend_data_path}")
        except FileNotFoundError:
            self.logger.warning(f"Reference data file not found: {self.trend_data_path}")
            self.reference_tokens = {}
        except Exception as e:
            self.logger.error(f"Error loading reference data: {str(e)}")
            self.reference_tokens = {}
    
    async def analyze_token(self, token_data: Dict[str, Any], blockchain_client) -> Dict[str, Any]:
        """
        Analyse un token en le comparant avec des tokens de référence similaires
        pour prédire son potentiel de croissance.
        
        Args:
            token_data: Données du token à analyser
            blockchain_client: Client blockchain pour les requêtes supplémentaires
            
        Returns:
            Résultats de l'analyse comparative
        """
        self.logger.info(f"Analyzing token trends for {token_data.get('address')} ({token_data.get('symbol')})")
        
        results = {
            "token_address": token_data.get("address"),
            "symbol": token_data.get("symbol"),
            "similar_tokens": [],
            "predicted_performance": {
                "expected_roi": 0.0,
                "expected_time_to_peak_hours": 0.0,
                "confidence_score": 0.0
            },
            "recommended_exit_strategies": [],
            "growth_pattern": "",
            "token_strength_score": 0,  # 0-100
            "potential_signals": [],
            "risk_signals": []
        }
        
        # 1. Extraire la catégorie du token
        token_category = await self._determine_token_category(token_data, blockchain_client)
        
        # 2. Trouver des tokens similaires
        similar_tokens = self._find_similar_tokens(token_data, token_category)
        results["similar_tokens"] = [
            {
                "address": t.address,
                "symbol": t.symbol,
                "similarity_score": s,
                "peak_roi": t.peak_roi,
                "time_to_peak_hours": t.time_to_peak_hours
            } for t, s in similar_tokens
        ]
        
        # 3. Prédire la performance en fonction des tokens similaires
        if similar_tokens:
            # Calculer la moyenne pondérée des ROI des tokens similaires
            total_weight = sum(score for _, score in similar_tokens)
            if total_weight > 0:
                expected_roi = sum(token.peak_roi * score for token, score in similar_tokens) / total_weight
                expected_time = sum(token.time_to_peak_hours * score for token, score in similar_tokens) / total_weight
                
                results["predicted_performance"]["expected_roi"] = expected_roi
                results["predicted_performance"]["expected_time_to_peak_hours"] = expected_time
                
                # Niveau de confiance basé sur la qualité des comparaisons
                top_similarity = similar_tokens[0][1] if similar_tokens else 0
                confidence = min(top_similarity * 100, 100)  # 0-100
                results["predicted_performance"]["confidence_score"] = confidence
        
        # 4. Déterminer le modèle de croissance probable
        growth_pattern = self._determine_growth_pattern(similar_tokens)
        results["growth_pattern"] = growth_pattern
        
        # 5. Recommander des stratégies de sortie
        exit_strategies = self._recommend_exit_strategies(similar_tokens, growth_pattern)
        results["recommended_exit_strategies"] = exit_strategies
        
        # 6. Calculer un score de force du token
        token_strength = self._calculate_token_strength(token_data, similar_tokens)
        results["token_strength_score"] = token_strength
        
        # 7. Identifier les signaux positifs et négatifs
        potential_signals, risk_signals = self._identify_signals(token_data, similar_tokens)
        results["potential_signals"] = potential_signals
        results["risk_signals"] = risk_signals
        
        return results
    
    async def _determine_token_category(self, token_data: Dict[str, Any], blockchain_client) -> str:
        """
        Détermine la catégorie d'un token en analysant ses métadonnées et son contrat.
        
        Args:
            token_data: Données du token
            blockchain_client: Client blockchain pour les requêtes
            
        Returns:
            Catégorie du token
        """
        # Par défaut, considérer comme un meme coin
        category = "meme"
        
        # Vérifier si le nom/symbole contient des mots-clés
        name = token_data.get("name", "").lower()
        symbol = token_data.get("symbol", "").lower()
        
        # Mots-clés par catégorie
        category_keywords = {
            "meme": ["doge", "shib", "pepe", "cat", "dog", "moon", "elon", "inu", "floki", "meme", "wojak", "chad"],
            "defi": ["swap", "yield", "lend", "borrow", "dao", "stake", "farm", "defi", "finance", "compound"],
            "game": ["play", "game", "nft", "meta", "verse", "land", "player", "axie", "arena"],
            "ai": ["ai", "gpt", "neural", "brain", "intelligence", "predict", "learn", "data"],
            "utility": ["pay", "chain", "exchange", "token", "wallet", "transfer", "utility"]
        }
        
        # Vérifier les mots-clés dans le nom et le symbole
        for cat, keywords in category_keywords.items():
            if any(keyword in name for keyword in keywords) or any(keyword in symbol for keyword in keywords):
                category = cat
                break
        
        # Essayer d'analyser le contrat pour des indices supplémentaires
        try:
            contract_info = await blockchain_client.get_token_metadata(token_data["address"])
            description = contract_info.get("description", "").lower()
            
            # Vérifier la description pour des indices supplémentaires
            for cat, keywords in category_keywords.items():
                if any(keyword in description for keyword in keywords):
                    # Donner plus de poids à la description qu'au nom/symbole
                    category = cat
                    break
        except Exception as e:
            self.logger.warning(f"Could not analyze contract for category determination: {str(e)}")
        
        self.logger.info(f"Determined category for token {token_data.get('symbol')}: {category}")
        return category
    
    def _find_similar_tokens(self, token_data: Dict[str, Any], token_category: str) -> List[Tuple[TokenMetrics, float]]:
        """
        Trouve des tokens similaires dans la base de données de référence.
        
        Args:
            token_data: Données du token à analyser
            token_category: Catégorie déterminée du token
            
        Returns:
            Liste de tokens similaires avec leurs scores de similarité
        """
        similar_tokens = []
        
        # Extraire les caractéristiques principales du token
        liquidity = token_data.get("initial_liquidity_usd", 0)
        community_size = token_data.get("social_media_followers", 0) + token_data.get("telegram_members", 0)
        volume = token_data.get("daily_volume_usd", 0)
        blockchain = token_data.get("blockchain", "unknown")
        
        # Normaliser les valeurs pour la comparaison
        # Ces coefficients servent à normaliser les valeurs pour la comparaison
        liquidity_norm = min(1.0, liquidity / 100000) if liquidity > 0 else 0  # Normaliser jusqu'à $100k
        community_norm = min(1.0, community_size / 10000) if community_size > 0 else 0  # Normaliser jusqu'à 10k membres
        volume_norm = min(1.0, volume / 100000) if volume > 0 else 0  # Normaliser jusqu'à $100k volume
        
        # Calculer la similarité pour chaque token de référence
        for ref_token in self.reference_tokens.values():
            # Similarité de catégorie (binaire - même catégorie ou non)
            category_similarity = 1.0 if ref_token.category == token_category else 0.0
            
            # Similarité de liquidité
            ref_liquidity_norm = min(1.0, ref_token.initial_liquidity_usd / 100000) if ref_token.initial_liquidity_usd > 0 else 0
            liquidity_similarity = 1.0 - abs(liquidity_norm - ref_liquidity_norm)
            
            # Similarité de communauté
            ref_community_norm = min(1.0, (ref_token.twitter_followers + ref_token.telegram_members) / 10000)
            community_similarity = 1.0 - abs(community_norm - ref_community_norm)
            
            # Similarité de volume
            ref_volume_norm = min(1.0, ref_token.avg_daily_volume_usd / 100000) if ref_token.avg_daily_volume_usd > 0 else 0
            volume_similarity = 1.0 - abs(volume_norm - ref_volume_norm)
            
            # Similarité de blockchain (binaire - même blockchain ou non)
            blockchain_similarity = 1.0 if token_data.get("blockchain") == blockchain else 0.0
            
            # Similarité de timing de lancement
            launch_similarity = 1.0  # Par défaut
            if token_data.get("launch_date") and ref_token.launch_date:
                token_launch = datetime.fromisoformat(token_data["launch_date"])
                time_diff_days = abs((token_launch - ref_token.launch_date).days)
                # Considérer comme similaire si lancé dans la même saison (90 jours)
                launch_similarity = max(0.0, 1.0 - (time_diff_days / 90))
            
            # Calculer le score de similarité global en utilisant les poids
            similarity_score = (
                category_similarity * self.similarity_weights["category"] +
                liquidity_similarity * self.similarity_weights["liquidity"] +
                community_similarity * self.similarity_weights["community"] +
                volume_similarity * self.similarity_weights["volume"] +
                blockchain_similarity * self.similarity_weights["blockchain"] +
                launch_similarity * self.similarity_weights["launch_timing"]
            )
            
            # Ajouter aux tokens similaires si le score dépasse le seuil minimum
            if similarity_score >= self.similarity_thresholds["low"]:
                similar_tokens.append((ref_token, similarity_score))
        
        # Trier par score de similarité décroissant
        similar_tokens.sort(key=lambda x: x[1], reverse=True)
        
        # Retourner les 5 tokens les plus similaires
        return similar_tokens[:5]
    
    def _determine_growth_pattern(self, similar_tokens: List[Tuple[TokenMetrics, float]]) -> str:
        """
        Détermine le modèle de croissance probable du token en fonction des tokens similaires.
        
        Args:
            similar_tokens: Liste de tokens similaires avec leurs scores de similarité
            
        Returns:
            Modèle de croissance prédit
        """
        if not similar_tokens:
            return "unknown"
        
        # Calculer le temps moyen pour atteindre le pic (en heures)
        times_to_peak = [token.time_to_peak_hours for token, _ in similar_tokens if token.time_to_peak_hours > 0]
        
        if not times_to_peak:
            return "unknown"
            
        avg_time_to_peak = sum(times_to_peak) / len(times_to_peak)
        
        # Modèles de croissance basés sur le temps moyen pour atteindre le pic
        if avg_time_to_peak < 6:
            return "rapid_spike"  # Pic rapide en moins de 6h
        elif avg_time_to_peak < 24:
            return "fast_growth"  # Croissance rapide (6-24h)
        elif avg_time_to_peak < 72:
            return "steady_climb"  # Croissance régulière (1-3 jours)
        else:
            return "slow_builder"  # Croissance lente (plus de 3 jours)
    
    def _recommend_exit_strategies(self, similar_tokens: List[Tuple[TokenMetrics, float]], growth_pattern: str) -> List[Dict[str, Any]]:
        """
        Recommande des stratégies de sortie en fonction des tokens similaires et du modèle de croissance.
        
        Args:
            similar_tokens: Liste de tokens similaires avec leurs scores de similarité
            growth_pattern: Modèle de croissance déterminé
            
        Returns:
            Liste de stratégies de sortie recommandées
        """
        if not similar_tokens:
            return []
        
        strategies = []
        
        # Calculer le ROI moyen des tokens similaires
        avg_roi = sum(token.peak_roi for token, _ in similar_tokens if token.peak_roi > 0) / len(similar_tokens)
        
        # Recommandations en fonction du modèle de croissance
        if growth_pattern == "rapid_spike":
            # Pour les pics rapides, il faut sortir rapidement
            strategies.append({
                "name": "Vente rapide progressive",
                "description": "Vendre 50% à 2x, 30% à 3x, et garder 20% pour un potentiel 5x+",
                "targets": [
                    {"percentage": 50, "roi_target": 2.0, "time_target_hours": 2},
                    {"percentage": 30, "roi_target": 3.0, "time_target_hours": 4},
                    {"percentage": 20, "roi_target": 5.0, "time_target_hours": 6}
                ],
                "stop_loss": {"percentage": 100, "threshold": 0.7}  # Si baisse de 30% du pic
            })
            
        elif growth_pattern == "fast_growth":
            # Pour une croissance rapide, sortie en plusieurs étapes
            strategies.append({
                "name": "Sortie étagée sur 24h",
                "description": "Vendre 30% à 2x, 40% à 4x, et 30% à 6x ou après 20h",
                "targets": [
                    {"percentage": 30, "roi_target": 2.0, "time_target_hours": 6},
                    {"percentage": 40, "roi_target": 4.0, "time_target_hours": 12},
                    {"percentage": 30, "roi_target": 6.0, "time_target_hours": 20}
                ],
                "stop_loss": {"percentage": 100, "threshold": 0.6}  # Si baisse de 40% du pic
            })
            
        elif growth_pattern == "steady_climb":
            # Pour une croissance régulière, approche plus patiente
            strategies.append({
                "name": "Stratégie de patience",
                "description": "Vendre 20% à 3x, 30% à 5x, 30% à 7x, et garder 20% pour le long terme",
                "targets": [
                    {"percentage": 20, "roi_target": 3.0, "time_target_hours": 24},
                    {"percentage": 30, "roi_target": 5.0, "time_target_hours": 48},
                    {"percentage": 30, "roi_target": 7.0, "time_target_hours": 72},
                    {"percentage": 20, "roi_target": 10.0, "time_target_hours": 120}
                ],
                "stop_loss": {"percentage": 100, "threshold": 0.5}  # Si baisse de 50% du pic
            })
            
        elif growth_pattern == "slow_builder":
            # Pour une croissance lente, stratégie à long terme
            strategies.append({
                "name": "Stratégie long terme",
                "description": "Vendre 25% à 3x, 25% à 6x, et réévaluer pour les 50% restants",
                "targets": [
                    {"percentage": 25, "roi_target": 3.0, "time_target_hours": 72},
                    {"percentage": 25, "roi_target": 6.0, "time_target_hours": 168},
                    {"percentage": 50, "roi_target": 10.0, "time_target_hours": 336}
                ],
                "stop_loss": {"percentage": 100, "threshold": 0.4}  # Si baisse de 60% du pic
            })
        
        else:
            # Stratégie générique si le modèle est inconnu
            strategies.append({
                "name": "Stratégie équilibrée",
                "description": "Vendre 30% à 2x, 40% à 3.5x, et 30% à 5x",
                "targets": [
                    {"percentage": 30, "roi_target": 2.0, "time_target_hours": 24},
                    {"percentage": 40, "roi_target": 3.5, "time_target_hours": 48},
                    {"percentage": 30, "roi_target": 5.0, "time_target_hours": 72}
                ],
                "stop_loss": {"percentage": 100, "threshold": 0.5}  # Si baisse de 50% du pic
            })
        
        # Ajouter une stratégie adaptative basée sur le ROI moyen des tokens similaires
        adaptive_strategy = {
            "name": "Stratégie adaptative",
            "description": f"Basée sur le ROI moyen de {avg_roi:.1f}x pour des tokens similaires",
            "targets": [
                {"percentage": 30, "roi_target": max(1.5, avg_roi * 0.5), "time_target_hours": 12},
                {"percentage": 40, "roi_target": max(2.0, avg_roi * 0.8), "time_target_hours": 24},
                {"percentage": 30, "roi_target": max(3.0, avg_roi * 1.2), "time_target_hours": 48}
            ],
            "stop_loss": {"percentage": 100, "threshold": 0.6}  # Si baisse de 40% du pic
        }
        strategies.append(adaptive_strategy)
        
        return strategies
    
    def _calculate_token_strength(self, token_data: Dict[str, Any], similar_tokens: List[Tuple[TokenMetrics, float]]) -> int:
        """
        Calcule un score de force pour le token en fonction de ses caractéristiques
        et des tokens similaires.
        
        Args:
            token_data: Données du token à analyser
            similar_tokens: Liste de tokens similaires avec leurs scores de similarité
            
        Returns:
            Score de force du token (0-100)
        """
        score = 50  # Score de base
        
        # Facteurs positifs
        # Liquidité
        liquidity = token_data.get("initial_liquidity_usd", 0)
        if liquidity > 100000:
            score += 10
        elif liquidity > 50000:
            score += 5
        elif liquidity > 10000:
            score += 2
        
        # Taille de la communauté
        twitter_followers = token_data.get("twitter_followers", 0)
        telegram_members = token_data.get("telegram_members", 0)
        community_size = twitter_followers + telegram_members
        
        if community_size > 10000:
            score += 10
        elif community_size > 5000:
            score += 5
        elif community_size > 1000:
            score += 2
        
        # Croissance de la communauté
        community_growth = token_data.get("community_growth_rate", 0)  # en % par jour
        if community_growth > 50:
            score += 10
        elif community_growth > 20:
            score += 5
        elif community_growth > 10:
            score += 2
        
        # Volume de trading
        volume = token_data.get("daily_volume_usd", 0)
        if volume > 500000:
            score += 10
        elif volume > 100000:
            score += 5
        elif volume > 25000:
            score += 2
        
        # Facteurs négatifs
        # Age du token (tokens trop récents sont plus risqués)
        age_days = token_data.get("age_days", 0)
        if age_days < 1:
            score -= 5
        
        # Tokens similaires avec fort ROI
        high_roi_tokens = sum(1 for token, _ in similar_tokens if token.peak_roi > 5)
        if high_roi_tokens >= 3:
            score += 10
        elif high_roi_tokens >= 1:
            score += 5
        
        # Limiter le score entre 0 et 100
        return max(0, min(100, score))
    
    def _identify_signals(self, token_data: Dict[str, Any], similar_tokens: List[Tuple[TokenMetrics, float]]) -> Tuple[List[str], List[str]]:
        """
        Identifie les signaux positifs et négatifs pour le token.
        
        Args:
            token_data: Données du token à analyser
            similar_tokens: Liste de tokens similaires avec leurs scores de similarité
            
        Returns:
            Tuple contenant les listes de signaux positifs et négatifs
        """
        potential_signals = []
        risk_signals = []
        
        # Signaux positifs basés sur les caractéristiques du token
        
        # Liquidité
        liquidity = token_data.get("initial_liquidity_usd", 0)
        if liquidity > 100000:
            potential_signals.append("Liquidité initiale très élevée (>$100k)")
        elif liquidity > 50000:
            potential_signals.append("Bonne liquidité initiale (>$50k)")
        elif liquidity < 10000:
            risk_signals.append("Faible liquidité initiale (<$10k)")
        
        # Communauté
        twitter_followers = token_data.get("twitter_followers", 0)
        telegram_members = token_data.get("telegram_members", 0)
        
        if twitter_followers > 5000:
            potential_signals.append(f"Forte présence Twitter ({twitter_followers} followers)")
        
        if telegram_members > 5000:
            potential_signals.append(f"Communauté Telegram active ({telegram_members} membres)")
        
        if twitter_followers < 500 and telegram_members < 500:
            risk_signals.append("Faible présence sur les réseaux sociaux")
        
        # Vérrouillage de liquidité
        liquidity_locked = token_data.get("liquidity_locked", False)
        lock_duration = token_data.get("liquidity_lock_days", 0)
        
        if liquidity_locked and lock_duration > 180:
            potential_signals.append(f"Liquidité verrouillée pour {lock_duration} jours")
        elif liquidity_locked and lock_duration > 30:
            potential_signals.append(f"Liquidité verrouillée pour {lock_duration} jours")
        elif not liquidity_locked:
            risk_signals.append("Liquidité non verrouillée")
        
        # Signaux basés sur les tokens similaires
        if similar_tokens:
            avg_roi = sum(token.peak_roi for token, _ in similar_tokens) / len(similar_tokens)
            
            if avg_roi > 10:
                potential_signals.append(f"Tokens similaires ont eu un ROI moyen de {avg_roi:.1f}x")
            elif avg_roi > 5:
                potential_signals.append(f"Tokens similaires ont eu un ROI moyen de {avg_roi:.1f}x")
            elif avg_roi < 2:
                risk_signals.append(f"Tokens similaires ont eu un faible ROI moyen de {avg_roi:.1f}x")
            
            # Temps pour atteindre le pic
            times_to_peak = [token.time_to_peak_hours for token, _ in similar_tokens]
            if times_to_peak:
                avg_time = sum(times_to_peak) / len(times_to_peak)
                if avg_time < 12:
                    potential_signals.append(f"Tokens similaires ont atteint leur pic en {avg_time:.1f}h en moyenne")
        
        # Signaux spécifiques au marché
        market_condition = token_data.get("market_condition", "neutral")
        if market_condition == "bullish":
            potential_signals.append("Conditions de marché globales favorables (bullish)")
        elif market_condition == "bearish":
            risk_signals.append("Conditions de marché globales défavorables (bearish)")
        
        return potential_signals, risk_signals
    
    async def update_reference_token(self, token_address: str, blockchain_client) -> bool:
        """
        Met à jour les données d'un token de référence ou ajoute un nouveau token.
        
        Args:
            token_address: Adresse du token à mettre à jour
            blockchain_client: Client blockchain pour les requêtes
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        try:
            # Récupérer les données du token
            token_info = await blockchain_client.get_token_info(token_address)
            
            if not token_info:
                self.logger.error(f"Could not get token info for {token_address}")
                return False
                
            # Récupérer les données de performance
            performance_data = await blockchain_client.get_token_historical_performance(token_address)
            
            # Créer ou mettre à jour le token de référence
            token = TokenMetrics(
                address=token_address,
                name=token_info.get("name", ""),
                symbol=token_info.get("symbol", ""),
                category=token_info.get("category", "meme"),
                launch_date=datetime.fromisoformat(token_info.get("launch_date", datetime.now().isoformat())),
                initial_price_usd=performance_data.get("initial_price_usd", 0.0),
                max_price_usd=performance_data.get("max_price_usd", 0.0),
                current_price_usd=performance_data.get("current_price_usd", 0.0),
                avg_daily_volume_usd=performance_data.get("avg_daily_volume_usd", 0.0),
                max_daily_volume_usd=performance_data.get("max_daily_volume_usd", 0.0),
                twitter_followers=token_info.get("twitter_followers", 0),
                telegram_members=token_info.get("telegram_members", 0),
                peak_roi=performance_data.get("peak_roi", 0.0),
                time_to_peak_hours=performance_data.get("time_to_peak_hours", 0.0),
                initial_liquidity_usd=performance_data.get("initial_liquidity_usd", 0.0),
                max_liquidity_usd=performance_data.get("max_liquidity_usd", 0.0),
                current_liquidity_usd=performance_data.get("current_liquidity_usd", 0.0)
            )
            
            # Ajouter/mettre à jour dans la collection
            self.reference_tokens[token_address] = token
            
            # Sauvegarder les données mises à jour
            self._save_reference_data()
            
            self.logger.info(f"Successfully updated reference data for {token.symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating reference token {token_address}: {str(e)}")
            return False
    
    def _save_reference_data(self):
        """Sauvegarde les données des tokens de référence dans le fichier JSON."""
        try:
            # Convertir les TokenMetrics en dictionnaires
            tokens_data = []
            for token in self.reference_tokens.values():
                token_dict = {
                    "address": token.address,
                    "name": token.name,
                    "symbol": token.symbol,
                    "category": token.category,
                    "launch_date": token.launch_date.isoformat() if token.launch_date else None,
                    "initial_price_usd": token.initial_price_usd,
                    "max_price_usd": token.max_price_usd,
                    "current_price_usd": token.current_price_usd,
                    "avg_daily_volume_usd": token.avg_daily_volume_usd,
                    "max_daily_volume_usd": token.max_daily_volume_usd,
                    "twitter_followers": token.twitter_followers,
                    "telegram_members": token.telegram_members,
                    "peak_roi": token.peak_roi,
                    "time_to_peak_hours": token.time_to_peak_hours,
                    "initial_liquidity_usd": token.initial_liquidity_usd,
                    "max_liquidity_usd": token.max_liquidity_usd,
                    "current_liquidity_usd": token.current_liquidity_usd
                }
                tokens_data.append(token_dict)
            
            # Créer le dictionnaire complet
            data = {
                "last_updated": datetime.now().isoformat(),
                "tokens": tokens_data
            }
            
            # S'assurer que le répertoire existe
            os.makedirs(os.path.dirname(self.trend_data_path), exist_ok=True)
            
            # Sauvegarder les données
            with open(self.trend_data_path, "w") as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved {len(tokens_data)} reference tokens to {self.trend_data_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving reference data: {str(e)}") 