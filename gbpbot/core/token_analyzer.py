from typing import Dict, List, Optional, Tuple, Any
from loguru import logger
import asyncio
import time
import numpy as np
from datetime import datetime, timedelta
import re
import string

# Indicateurs
class BaseIndicator:
    """Classe de base pour tous les indicateurs d'analyse de tokens"""
    
    def __init__(self, config: Dict, weight: float = 1.0):
        """
        Initialise l'indicateur
        
        Args:
            config: Configuration de l'indicateur
            weight: Poids de l'indicateur dans le score global
        """
        self.config = config
        self.weight = weight
        self.score_range = (0.0, 10.0)  # Score entre 0 et 10
        
    async def calculate_score(self, token_data: Dict) -> float:
        """
        Calcule le score de l'indicateur pour un token
        
        Args:
            token_data: Données du token
            
        Returns:
            float: Score de l'indicateur
        """
        raise NotImplementedError("Les classes dérivées doivent implémenter cette méthode")
        
    def normalize_score(self, score: float) -> float:
        """
        Normalise le score dans la plage de l'indicateur
        
        Args:
            score: Score brut
            
        Returns:
            float: Score normalisé
        """
        min_score, max_score = self.score_range
        if score <= min_score:
            return 0.0
        if score >= max_score:
            return 10.0
        return ((score - min_score) / (max_score - min_score)) * 10.0


class LiquidityIndicator(BaseIndicator):
    """Indicateur basé sur la liquidité du token"""
    
    def __init__(self, config: Dict, weight: float = 2.0):
        super().__init__(config, weight)
        
        # Paramètres spécifiques
        analysis_config = config.get("analysis", {})
        liquidity_config = analysis_config.get("liquidity", {})
        
        self.min_liquidity = liquidity_config.get("min_liquidity", 1000)  # Liquidité minimale en dollars
        self.target_liquidity = liquidity_config.get("target_liquidity", 10000)  # Bonne liquidité
        self.excellent_liquidity = liquidity_config.get("excellent_liquidity", 100000)  # Excellente liquidité
        
    async def calculate_score(self, token_data: Dict) -> float:
        """Calcule le score de liquidité"""
        try:
            # Récupérer la liquidité du token
            liquidity = token_data.get("liquidity", 0)
            
            # Si pas de liquidité, score minimum
            if liquidity <= 0:
                return 0.0
                
            # Si liquidité inférieure au minimum, score faible
            if liquidity < self.min_liquidity:
                return self.normalize_score(liquidity / self.min_liquidity * 2)
                
            # Si liquidité entre min et target, score moyen
            if liquidity < self.target_liquidity:
                return self.normalize_score(2 + (liquidity - self.min_liquidity) / 
                                      (self.target_liquidity - self.min_liquidity) * 3)
                
            # Si liquidité entre target et excellent, bon score
            if liquidity < self.excellent_liquidity:
                return self.normalize_score(5 + (liquidity - self.target_liquidity) / 
                                      (self.excellent_liquidity - self.target_liquidity) * 3)
                
            # Si liquidité supérieure à excellent, score excellent
            return self.normalize_score(8 + min(2, (liquidity / self.excellent_liquidity) - 1))
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du calcul du score de liquidité: {str(e)}")
            return 5.0  # Score moyen en cas d'erreur


class VolumeIndicator(BaseIndicator):
    """Indicateur basé sur le volume de transactions"""
    
    def __init__(self, config: Dict, weight: float = 1.5):
        super().__init__(config, weight)
        
        # Paramètres spécifiques
        analysis_config = config.get("analysis", {})
        volume_config = analysis_config.get("volume", {})
        
        self.min_volume = volume_config.get("min_volume", 500)  # Volume minimum en dollars
        self.target_volume = volume_config.get("target_volume", 5000)  # Bon volume
        self.excellent_volume = volume_config.get("excellent_volume", 50000)  # Excellent volume
        
    async def calculate_score(self, token_data: Dict) -> float:
        """Calcule le score de volume"""
        try:
            # Récupérer le volume du token (24h)
            volume = token_data.get("volume_24h", 0)
            
            # Si pas de volume, score minimum
            if volume <= 0:
                return 0.0
                
            # Si volume inférieur au minimum, score faible
            if volume < self.min_volume:
                return self.normalize_score(volume / self.min_volume * 2)
                
            # Si volume entre min et target, score moyen
            if volume < self.target_volume:
                return self.normalize_score(2 + (volume - self.min_volume) / 
                                     (self.target_volume - self.min_volume) * 3)
                
            # Si volume entre target et excellent, bon score
            if volume < self.excellent_volume:
                return self.normalize_score(5 + (volume - self.target_volume) / 
                                     (self.excellent_volume - self.target_volume) * 3)
                
            # Si volume supérieur à excellent, score excellent
            return self.normalize_score(8 + min(2, (volume / self.excellent_volume) - 1))
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du calcul du score de volume: {str(e)}")
            return 5.0  # Score moyen en cas d'erreur


class SocialIndicator(BaseIndicator):
    """Indicateur basé sur la présence et l'activité sociale"""
    
    def __init__(self, config: Dict, weight: float = 1.0):
        super().__init__(config, weight)
        
    async def calculate_score(self, token_data: Dict) -> float:
        """Calcule le score social"""
        try:
            # Points pour différents facteurs sociaux
            score = 0.0
            
            # Vérifie si le token a un site web
            if token_data.get("website"):
                score += 2.0
                
            # Vérifie si le token a un compte Twitter
            if token_data.get("twitter"):
                score += 2.0
                
            # Vérifie si le token a un groupe Telegram
            if token_data.get("telegram"):
                score += 2.0
                
            # Vérifie si le token a une description
            if token_data.get("description") and len(token_data.get("description", "")) > 50:
                score += 2.0
                
            # Vérifie si le token est vérifié
            if token_data.get("verified", False):
                score += 2.0
                
            # Normaliser le score
            return self.normalize_score(score)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du calcul du score social: {str(e)}")
            return 5.0  # Score moyen en cas d'erreur


class PriceActionIndicator(BaseIndicator):
    """Indicateur basé sur l'action du prix récente"""
    
    def __init__(self, config: Dict, weight: float = 1.8):
        super().__init__(config, weight)
        
    async def calculate_score(self, token_data: Dict) -> float:
        """Calcule le score d'action de prix"""
        try:
            # Récupérer les données de prix si disponibles
            chart_data = token_data.get("chart_data", [])
            
            # Si pas de données de chart, score moyen
            if not chart_data or len(chart_data) < 2:
                return 5.0
                
            # Calculer le ROI sur différentes périodes
            current_price = token_data.get("price", 0)
            if current_price <= 0:
                return 5.0
                
            # Convertir les timestamps en datetime
            for point in chart_data:
                if "timestamp" in point and isinstance(point["timestamp"], (int, float)):
                    point["datetime"] = datetime.fromtimestamp(point["timestamp"] / 1000 
                                                           if point["timestamp"] > 10**10 
                                                           else point["timestamp"])
                    
            # Trier par date
            chart_data.sort(key=lambda x: x.get("datetime", datetime.min))
            
            # Calculer différents indicateurs
            now = datetime.now()
            
            # Données pour différentes périodes
            data_1h = [p for p in chart_data if "datetime" in p and now - p["datetime"] <= timedelta(hours=1)]
            data_24h = [p for p in chart_data if "datetime" in p and now - p["datetime"] <= timedelta(hours=24)]
            
            # ROI sur 1h
            roi_1h = 0
            if data_1h and len(data_1h) > 1:
                start_price = data_1h[0].get("price", 0)
                if start_price > 0:
                    roi_1h = (current_price - start_price) / start_price * 100
                    
            # ROI sur 24h
            roi_24h = 0
            if data_24h and len(data_24h) > 1:
                start_price = data_24h[0].get("price", 0)
                if start_price > 0:
                    roi_24h = (current_price - start_price) / start_price * 100
                    
            # Volatilité sur 24h
            volatility = 0
            if data_24h and len(data_24h) > 2:
                prices = [p.get("price", 0) for p in data_24h if p.get("price", 0) > 0]
                if prices:
                    # Calculer l'écart-type en pourcentage du prix moyen
                    mean_price = sum(prices) / len(prices)
                    if mean_price > 0:
                        volatility = (np.std(prices) / mean_price) * 100
                        
            # Établir le score basé sur les métriques
            score = 5.0  # Score de base moyen
            
            # Ajuster en fonction du ROI à court terme (1h)
            if roi_1h > 20:  # Excellente performance à court terme
                score += 2.5
            elif roi_1h > 10:
                score += 1.5
            elif roi_1h > 5:
                score += 1.0
            elif roi_1h < -20:  # Mauvaise performance à court terme
                score -= 2.5
            elif roi_1h < -10:
                score -= 1.5
            elif roi_1h < -5:
                score -= 1.0
                
            # Ajuster en fonction du ROI à moyen terme (24h)
            if roi_24h > 100:  # Excellente performance à moyen terme
                score += 2.0
            elif roi_24h > 50:
                score += 1.5
            elif roi_24h > 20:
                score += 1.0
            elif roi_24h < -50:  # Mauvaise performance à moyen terme
                score -= 2.0
            elif roi_24h < -30:
                score -= 1.5
            elif roi_24h < -20:
                score -= 1.0
                
            # Ajuster en fonction de la volatilité
            if volatility > 50:  # Très volatile (peut être bon ou mauvais)
                # Si le prix est en hausse, c'est généralement bon
                if roi_24h > 0:
                    score += 1.0
                else:
                    score -= 1.0
                    
            # Normaliser le score
            return self.normalize_score(score)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du calcul du score d'action de prix: {str(e)}")
            return 5.0  # Score moyen en cas d'erreur


class NameQualityIndicator(BaseIndicator):
    """Indicateur basé sur la qualité du nom et du symbole du token"""
    
    def __init__(self, config: Dict, weight: float = 0.5):
        super().__init__(config, weight)
        
        # Liste de mots clés viraux ou populaires
        self.viral_keywords = [
            "pepe", "doge", "shib", "moon", "elon", "musk", "rocket", "safe", "chad", 
            "based", "wojak", "inu", "cat", "meme", "ai", "gpt", "turbo", "frog",
            "pump", "lambo", "diamond", "hands", "hodl", "tendies", "gainz", "moon",
            "ape", "gorilla", "monkey", "banana", "trump", "biden", "president",
            "crypto", "coin", "token", "farm", "yield", "defi", "nft", "metaverse",
            "gaming", "play", "earn", "dao", "governance", "stake", "swap", "exchange"
        ]
        
        # Expressions régulières pour détecter les caractéristiques du nom
        self.all_caps_regex = re.compile(r'^[A-Z]+$')
        self.mix_case_regex = re.compile(r'[a-z][A-Z]|[A-Z][a-z]')
        
    async def calculate_score(self, token_data: Dict) -> float:
        """Calcule le score de qualité du nom"""
        try:
            name = token_data.get("name", "").lower()
            symbol = token_data.get("symbol", "").lower()
            
            if not name or not symbol:
                return 5.0  # Score moyen si pas de données
                
            score = 5.0  # Score de base moyen
            
            # Vérifier la longueur du nom
            if len(name) < 3:
                score -= 2.0  # Trop court
            elif len(name) > 20:
                score -= 1.0  # Trop long
                
            # Vérifier la longueur du symbole
            if len(symbol) < 2:
                score -= 1.0  # Trop court
            elif len(symbol) > 6:
                score -= 1.0  # Trop long
                
            # Vérifier la présence de mots clés viraux
            for keyword in self.viral_keywords:
                if keyword in name or keyword in symbol:
                    score += 1.0
                    break  # Ne compte qu'une seule fois
                    
            # Vérifier si le nom contient des caractères non alphanumériques
            if any(c for c in name if c not in string.ascii_letters + string.digits + ' -_'):
                score -= 1.0
                
            # Vérifier si le symbole contient des caractères non alphanumériques
            if any(c for c in symbol if c not in string.ascii_letters + string.digits):
                score -= 1.5
                
            # Vérifier le case du symbole
            if self.all_caps_regex.match(symbol):
                score += 1.0  # Symbole en majuscules (standard)
                
            # Vérifier la créativité du nom
            if self.mix_case_regex.search(name):
                score += 0.5  # Mix case peut être créatif (comme BitTorrent)
                
            # Normaliser le score
            return self.normalize_score(score)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du calcul du score de qualité du nom: {str(e)}")
            return 5.0  # Score moyen en cas d'erreur


class TokenAnalyzer:
    """Analyseur avancé de tokens pour évaluer leur potentiel"""
    
    def __init__(self, config: Dict):
        """
        Initialise l'analyseur de tokens
        
        Args:
            config: Configuration de l'analyseur
        """
        self.config = config
        self.indicators = []
        
        # Charger les indicateurs configurés
        self._load_indicators()
        
        # Statistiques des analyses
        self.analyzed_tokens = 0
        self.tokens_by_score = {
            "excellent": 0,  # Score > 8
            "good": 0,       # Score 6-8
            "average": 0,    # Score 4-6
            "poor": 0,       # Score 2-4
            "bad": 0         # Score < 2
        }
        
        logger.info(f"✅ Analyseur de tokens initialisé avec {len(self.indicators)} indicateurs")
        
    def _load_indicators(self):
        """Charge les indicateurs configurés"""
        analysis_config = self.config.get("analysis", {})
        
        # Indicateur de liquidité
        if analysis_config.get("liquidity", {}).get("enabled", True):
            weight = analysis_config.get("liquidity", {}).get("weight", 2.0)
            self.indicators.append(LiquidityIndicator(self.config, weight))
            
        # Indicateur de volume
        if analysis_config.get("volume", {}).get("enabled", True):
            weight = analysis_config.get("volume", {}).get("weight", 1.5)
            self.indicators.append(VolumeIndicator(self.config, weight))
            
        # Indicateur social
        if analysis_config.get("social", {}).get("enabled", True):
            weight = analysis_config.get("social", {}).get("weight", 1.0)
            self.indicators.append(SocialIndicator(self.config, weight))
            
        # Indicateur d'action de prix
        if analysis_config.get("price_action", {}).get("enabled", True):
            weight = analysis_config.get("price_action", {}).get("weight", 1.8)
            self.indicators.append(PriceActionIndicator(self.config, weight))
            
        # Indicateur de qualité du nom
        if analysis_config.get("name_quality", {}).get("enabled", True):
            weight = analysis_config.get("name_quality", {}).get("weight", 0.5)
            self.indicators.append(NameQualityIndicator(self.config, weight))
            
    async def analyze_token(self, token_data: Dict) -> Dict:
        """
        Analyse un token selon plusieurs critères et retourne un score
        
        Args:
            token_data: Données du token à analyser
            
        Returns:
            Dict: Résultat de l'analyse avec scores et recommandation
        """
        try:
            start_time = time.time()
            
            # Vérifier si les données minimales sont présentes
            if not token_data or "address" not in token_data:
                return {
                    "success": False,
                    "error": "Données de token insuffisantes pour l'analyse"
                }
                
            token_address = token_data["address"]
            logger.debug(f"🔍 Analyse du token {token_address}")
            
            # Calculer les scores pour chaque indicateur
            indicator_scores = {}
            total_weight = 0.0
            
            # Exécuter tous les indicateurs de manière asynchrone
            tasks = [indicator.calculate_score(token_data) for indicator in self.indicators]
            scores = await asyncio.gather(*tasks)
            
            # Associer les scores aux indicateurs
            for i, score in enumerate(scores):
                indicator = self.indicators[i]
                indicator_name = indicator.__class__.__name__
                indicator_scores[indicator_name] = {
                    "score": score,
                    "weight": indicator.weight
                }
                total_weight += indicator.weight
                
            # Calculer le score global pondéré
            weighted_sum = sum(info["score"] * info["weight"] for info in indicator_scores.values())
            global_score = weighted_sum / total_weight if total_weight > 0 else 5.0
            
            # Déterminer la catégorie de score
            score_category = self._get_score_category(global_score)
            
            # Déterminer la recommandation
            buy_threshold = self.config.get("analysis", {}).get("buy_threshold", 7.0)
            recommendation = "BUY" if global_score >= buy_threshold else "PASS"
            
            # Mettre à jour les statistiques
            self.analyzed_tokens += 1
            self.tokens_by_score[score_category] += 1
            
            # Préparer le résultat
            result = {
                "success": True,
                "token_address": token_address,
                "token_name": token_data.get("name", "Unknown"),
                "token_symbol": token_data.get("symbol", "UNKNOWN"),
                "global_score": global_score,
                "score_category": score_category,
                "indicator_scores": indicator_scores,
                "recommendation": recommendation,
                "analysis_time": time.time() - start_time
            }
            
            logger.info(f"✅ Analyse du token {token_address} terminée: Score {global_score:.2f}, {recommendation}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse du token {token_data.get('address', 'unknown')}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "token_address": token_data.get("address", "unknown")
            }
            
    def _get_score_category(self, score: float) -> str:
        """
        Détermine la catégorie de score
        
        Args:
            score: Score global
            
        Returns:
            str: Catégorie de score
        """
        if score >= 8.0:
            return "excellent"
        elif score >= 6.0:
            return "good"
        elif score >= 4.0:
            return "average"
        elif score >= 2.0:
            return "poor"
        else:
            return "bad"
            
    def get_statistics(self) -> Dict:
        """
        Récupère les statistiques d'analyse
        
        Returns:
            Dict: Statistiques d'analyse
        """
        return {
            "analyzed_tokens": self.analyzed_tokens,
            "tokens_by_score": self.tokens_by_score
        }
        
    def reset_statistics(self):
        """Réinitialise les statistiques d'analyse"""
        self.analyzed_tokens = 0
        self.tokens_by_score = {
            "excellent": 0,
            "good": 0,
            "average": 0,
            "poor": 0,
            "bad": 0
        } 