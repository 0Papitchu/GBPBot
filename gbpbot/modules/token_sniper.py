#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de Sniping de Token pour GBPBot
======================================

Ce module fournit des fonctionnalités pour détecter et acheter rapidement
les nouveaux tokens prometteurs, avec une analyse intelligente pour éviter
les scams et maximiser les profits.

Implémente un système de détection et d'achat automatique des tokens prometeurs.
Intègre l'analyse IA avec Claude 3.7 pour minimiser les risques et maximiser les profits.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

from gbpbot.utils.logger import setup_logger
from gbpbot.ai import create_ai_client, create_market_intelligence

# Configurer le logger
logger = setup_logger("TokenSniper", logging.INFO)

class TokenSniper:
    """
    Système de sniping de tokens avancé avec analyse IA intégrée
    Détecte et achète automatiquement les tokens prometeurs
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le système de sniping de tokens
        
        Args:
            config: Configuration du module
        """
        self.config = config
        self.blockchain = None
        self.running = False
        self.ai_client = None
        self.market_intelligence = None
        self.min_token_score = int(os.environ.get("MIN_TOKEN_SCORE", "70"))
        self.use_ai_analysis = os.environ.get("USE_AI_ANALYSIS", "true").lower() == "true"
        self.analyze_before_snipe = os.environ.get("AI_ANALYZE_BEFORE_SNIPE", "true").lower() == "true"
        
        # Statistiques d'activité
        self.stats = {
            "tokens_detected": 0,
            "tokens_analyzed": 0,
            "tokens_sniped": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "profitable_trades": 0,
            "last_activity": datetime.now().isoformat()
        }
        
        # Suivi des tokens analysés
        self.analyzed_tokens = {}
        
        logger.info("Système de sniping de tokens initialisé")
    
    async def initialize(self):
        """Initialise les composants nécessaires au fonctionnement du module"""
        # Initialiser le client blockchain (solana, avax, etc.)
        self.blockchain = await self._initialize_blockchain()
        
        # Initialiser le client IA si l'analyse IA est activée
        if self.use_ai_analysis:
            try:
                logger.info("Initialisation du client IA...")
                self.ai_client = await create_ai_client(
                    provider=os.environ.get("AI_PROVIDER", "claude"),
                    config=self._get_ai_config()
                )
                
                # Initialiser le système d'intelligence de marché
                self.market_intelligence = await create_market_intelligence({
                    "ai_config": self._get_ai_config(),
                    "web_search_config": {
                        "serper_api_key": os.environ.get("SERPER_API_KEY")
                    }
                })
                
                logger.info("Client IA initialisé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du client IA: {str(e)}")
                self.use_ai_analysis = False
        
        logger.info("Initialisation du système de sniping terminée")
    
    async def start(self):
        """Démarre le système de sniping de tokens"""
        if self.running:
            logger.warning("Le système de sniping est déjà en cours d'exécution")
            return
        
        # Initialiser si ce n'est pas déjà fait
        if not self.blockchain:
            await self.initialize()
        
        self.running = True
        logger.info("Démarrage du système de sniping de tokens")
        
        # Lancer la boucle principale
        asyncio.create_task(self._main_loop())
    
    async def stop(self):
        """Arrête le système de sniping de tokens"""
        if not self.running:
            logger.warning("Le système de sniping n'est pas en cours d'exécution")
            return
        
        self.running = False
        logger.info("Arrêt du système de sniping de tokens")
        
        # Fermer proprement les connexions
        if self.ai_client:
            await self.ai_client.close()
        
        if self.market_intelligence:
            await self.market_intelligence.close()
    
    async def _main_loop(self):
        """Boucle principale du système de sniping"""
        logger.info("Boucle principale de surveillance des tokens démarrée")
        
        while self.running:
            try:
                # Détecter les nouveaux tokens
                new_tokens = await self._detect_new_tokens()
                
                if new_tokens:
                    logger.info(f"Détection de {len(new_tokens)} nouveaux tokens")
                    self.stats["tokens_detected"] += len(new_tokens)
                    
                    # Analyser et évaluer chaque token
                    for token in new_tokens:
                        token_symbol = token.get("symbol", "Unknown")
                        token_address = token.get("address", "")
                        
                        # Ne traiter que des tokens uniques
                        if token_address in self.analyzed_tokens:
                            continue
                        
                        # Marquer comme analysé
                        self.analyzed_tokens[token_address] = {
                            "first_seen": datetime.now().isoformat(),
                            "symbol": token_symbol
                        }
                        
                        # Analyser avec l'IA si activé
                        if self.use_ai_analysis and self.analyze_before_snipe:
                            score, analysis = await self._analyze_token(token)
                            
                            # Décider si on snipe le token
                            if score >= self.min_token_score:
                                logger.info(f"Token {token_symbol} a un score de {score}, sniping...")
                                await self._snipe_token(token, analysis)
                            else:
                                logger.info(f"Token {token_symbol} a un score de {score}, en dessous du seuil minimum ({self.min_token_score})")
                        else:
                            # Sniping sans analyse IA
                            await self._snipe_token(token)
                
                # Pause avant la prochaine itération
                await asyncio.sleep(0.5)  # Fréquence de surveillance agressive
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {str(e)}")
                await asyncio.sleep(5)  # Pause plus longue en cas d'erreur
    
    async def _detect_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Détecte les nouveaux tokens sur la blockchain
        
        Returns:
            Liste des nouveaux tokens détectés
        """
        # Exemple simplifié, à implémenter avec la logique spécifique à chaque blockchain
        # Dans une implémentation réelle, cette méthode détecterait les nouveaux tokens
        # via l'écoute du mempool, la surveillance des événements de création de paires, etc.
        return []
    
    async def _analyze_token(self, token: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Analyse un token avec l'IA pour déterminer son potentiel et ses risques
        
        Args:
            token: Données du token à analyser
            
        Returns:
            Tuple (score, détails) où score est entre 0 et 100
        """
        try:
            token_symbol = token.get("symbol", "Unknown")
            token_address = token.get("address", "")
            chain = token.get("chain", "solana")
            
            logger.info(f"Analyse du token {token_symbol} ({token_address}) avec IA")
            self.stats["tokens_analyzed"] += 1
            
            # Enrichir les données du token avec des informations supplémentaires
            token_data = await self._get_token_details(token)
            
            # Utiliser l'intelligence de marché pour une analyse complète
            if self.market_intelligence:
                analysis = await self.market_intelligence.analyze_token(
                    token_symbol=token_symbol,
                    chain=chain,
                    with_web_search=True
                )
                
                # Extraire le score
                score = float(analysis.get("score", 0))
                
                # Compléter l'analyse avec les données de token
                analysis["token_data"] = token_data
                
                # Sauvegarder l'analyse
                self.analyzed_tokens[token_address]["analysis"] = analysis
                self.analyzed_tokens[token_address]["score"] = score
                self.analyzed_tokens[token_address]["analyzed_at"] = datetime.now().isoformat()
                
                return score, analysis
            
            # Fallback à l'utilisation directe du client IA
            elif self.ai_client:
                score, analysis = await self.ai_client.get_token_score(token_data)
                
                # Sauvegarder l'analyse
                self.analyzed_tokens[token_address]["analysis"] = analysis
                self.analyzed_tokens[token_address]["score"] = score
                self.analyzed_tokens[token_address]["analyzed_at"] = datetime.now().isoformat()
                
                return score, analysis
            
            # Aucun client IA disponible
            else:
                logger.warning(f"Impossible d'analyser le token {token_symbol} : aucun client IA disponible")
                return 0, {"error": "IA non disponible"}
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse IA du token: {str(e)}")
            return 0, {"error": str(e)}
    
    async def _snipe_token(self, token: Dict[str, Any], analysis: Optional[Dict[str, Any]] = None) -> bool:
        """
        Exécute l'achat d'un token détecté
        
        Args:
            token: Données du token à sniper
            analysis: Analyse IA optionnelle
            
        Returns:
            True si le sniping a réussi, False sinon
        """
        token_symbol = token.get("symbol", "Unknown")
        token_address = token.get("address", "")
        
        try:
            logger.info(f"Sniping du token {token_symbol} ({token_address})")
            self.stats["tokens_sniped"] += 1
            
            # Calculer le montant à acheter - potentiellement basé sur l'analyse IA
            amount = self._calculate_buy_amount(token, analysis)
            
            # Calculer le slippage - potentiellement optimisé par l'analyse IA
            slippage = self._calculate_slippage(token, analysis)
            
            # Exécuter l'achat
            transaction = await self._execute_buy(token, amount, slippage)
            
            if transaction and transaction.get("success", False):
                logger.info(f"Sniping réussi pour {token_symbol}")
                self.stats["successful_trades"] += 1
                
                # Configurer les ordres de take profit et stop loss en fonction de l'analyse
                if analysis:
                    await self._setup_exit_strategy(token, transaction, analysis)
                
                return True
            else:
                logger.warning(f"Échec du sniping pour {token_symbol}")
                self.stats["failed_trades"] += 1
                return False
        
        except Exception as e:
            logger.error(f"Erreur lors du sniping du token {token_symbol}: {str(e)}")
            self.stats["failed_trades"] += 1
            return False
    
    async def _get_token_details(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Récupère des détails supplémentaires sur un token
        
        Args:
            token: Données de base du token
            
        Returns:
            Données enrichies du token
        """
        # À implémenter avec la logique spécifique à chaque blockchain
        # Cette méthode devrait récupérer des informations comme:
        # - Liquidité et volume
        # - Code du contrat
        # - Nombre de détenteurs
        # - Historique de prix
        return token
    
    async def _setup_exit_strategy(self, token: Dict[str, Any], transaction: Dict[str, Any], analysis: Dict[str, Any]):
        """
        Configure une stratégie de sortie basée sur l'analyse IA
        
        Args:
            token: Données du token
            transaction: Détails de la transaction d'achat
            analysis: Analyse IA du token
        """
        token_symbol = token.get("symbol", "Unknown")
        
        # Extraire les recommandations de l'analyse
        recommendation = analysis.get("recommendation", {})
        take_profit = recommendation.get("take_profit", 50.0)
        stop_loss = recommendation.get("stop_loss", -15.0)
        
        # Utiliser une stratégie par étapes si recommandé
        staged_exit = recommendation.get("staged_exit", False)
        
        if staged_exit:
            stages = recommendation.get("stages", [
                {"percentage": 25, "profit": 25},
                {"percentage": 25, "profit": 50},
                {"percentage": 50, "profit": 100}
            ])
            
            logger.info(f"Configuration d'une sortie par étapes pour {token_symbol}: {stages}")
            # Implémenter la logique de sortie par étapes
        else:
            logger.info(f"Configuration du take profit à {take_profit}% et du stop loss à {stop_loss}% pour {token_symbol}")
            # Implémenter la logique de sortie simple
    
    def _calculate_buy_amount(self, token: Dict[str, Any], analysis: Optional[Dict[str, Any]] = None) -> float:
        """
        Calcule le montant à acheter en fonction du token et de son analyse
        
        Args:
            token: Données du token
            analysis: Analyse IA optionnelle
            
        Returns:
            Montant à acheter en USD
        """
        base_amount = float(os.environ.get("SOLANA_MAX_SNIPE_AMOUNT_USD", "100"))
        
        # Si l'analyse IA est disponible, ajuster le montant en fonction du score et de la confiance
        if analysis:
            score = analysis.get("score", 0)
            confidence = analysis.get("confidence", 50)
            
            # Formule d'ajustement basée sur le score et la confiance
            # Plus le score est élevé, plus on investit (jusqu'à 150% du montant de base)
            # Mais si la confiance est basse, on réduit le montant
            score_factor = min(1.5, max(0.5, score / 100 * 1.5))
            confidence_factor = min(1.0, max(0.5, confidence / 100))
            
            adjusted_amount = base_amount * score_factor * confidence_factor
            
            logger.info(f"Montant ajusté par l'IA: {adjusted_amount:.2f} USD (base: {base_amount} USD, score: {score}, confiance: {confidence})")
            
            return adjusted_amount
        
        return base_amount
    
    def _calculate_slippage(self, token: Dict[str, Any], analysis: Optional[Dict[str, Any]] = None) -> float:
        """
        Calcule le slippage optimal en fonction du token et de son analyse
        
        Args:
            token: Données du token
            analysis: Analyse IA optionnelle
            
        Returns:
            Slippage en pourcentage
        """
        base_slippage = float(os.environ.get("MAX_SLIPPAGE", "2.0"))
        
        # Si l'analyse IA est disponible, ajuster le slippage en fonction de la volatilité attendue
        if analysis:
            volatility = analysis.get("volatility", "medium")
            liquidity = analysis.get("liquidity", "medium")
            
            # Ajuster le slippage en fonction de la volatilité et de la liquidité
            if volatility == "high":
                slippage_factor = 1.5  # Augmenter pour les tokens très volatils
            elif volatility == "low":
                slippage_factor = 0.8  # Réduire pour les tokens stables
            else:
                slippage_factor = 1.0  # Normal
                
            # Ajuster en fonction de la liquidité
            if liquidity == "low":
                slippage_factor *= 1.5  # Augmenter pour les tokens à faible liquidité
            elif liquidity == "high":
                slippage_factor *= 0.8  # Réduire pour les tokens à forte liquidité
            
            adjusted_slippage = base_slippage * slippage_factor
            
            logger.info(f"Slippage ajusté par l'IA: {adjusted_slippage:.2f}% (base: {base_slippage}%, volatilité: {volatility}, liquidité: {liquidity})")
            
            return adjusted_slippage
        
        return base_slippage
    
    async def _initialize_blockchain(self):
        """
        Initialise le client blockchain en fonction de la configuration
        
        Returns:
            Client blockchain initialisé
        """
        # À implémenter en fonction des blockchains supportées
        return None
    
    async def _execute_buy(self, token: Dict[str, Any], amount: float, slippage: float) -> Dict[str, Any]:
        """
        Exécute l'achat d'un token
        
        Args:
            token: Données du token
            amount: Montant à acheter en USD
            slippage: Slippage maximum en pourcentage
            
        Returns:
            Détails de la transaction
        """
        # À implémenter avec la logique spécifique à chaque blockchain
        return {"success": False, "message": "Non implémenté"}
    
    def _get_ai_config(self) -> Dict[str, Any]:
        """
        Prépare la configuration pour le client IA
        
        Returns:
            Configuration du client IA
        """
        ai_provider = os.environ.get("AI_PROVIDER", "claude")
        
        if ai_provider == "claude":
            return {
                "api_key": os.environ.get("CLAUDE_API_KEY"),
                "model": os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20240229")
            }
        elif ai_provider == "openai":
            return {
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "model": os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
            }
        else:
            return {}

    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du système de sniping.
        
        Returns:
            Statistiques du système
        """
        return self.stats 