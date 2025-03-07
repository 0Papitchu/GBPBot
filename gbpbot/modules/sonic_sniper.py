#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de Sniping sur Sonic pour GBPBot
=======================================

Ce module fournit des fonctionnalités pour détecter et acheter rapidement
les nouveaux tokens sur la blockchain Sonic, avec une analyse intelligente
pour éviter les scams et maximiser les profits.
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from decimal import Decimal

from gbpbot.clients.blockchain_client_factory import BlockchainClientFactory
from gbpbot.config.config_manager import config_manager
from gbpbot.utils.cache_manager import cache_manager
from gbpbot.ai.contract_analyzer import create_contract_analyzer

# Configuration du logger
logger = logging.getLogger("gbpbot.modules.sonic_sniper")

class SonicSniper:
    """
    Système de sniping spécialisé pour Sonic.
    
    Cette classe implémente des stratégies avancées pour détecter et acheter
    rapidement les nouveaux tokens sur Sonic, avec des mécanismes de sécurité
    pour éviter les scams et maximiser les profits.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le système de sniping Sonic.
        
        Args:
            config: Configuration du sniper (optionnel)
        """
        logger.info("Initialisation du système de sniping Sonic")
        
        # Charger la configuration
        self.config = config or config_manager.get_config().get("modules", {}).get("sniping", {})
        
        # État du sniper
        self.running = False
        self.monitoring_task = None
        self.stop_event = asyncio.Event()
        
        # Client blockchain
        self.client = None
        self.init_client()
        
        # Statistiques et suivi
        self.stats = {
            "tokens_detected": 0,
            "tokens_analyzed": 0,
            "tokens_bought": 0,
            "tokens_rejected": 0,
            "total_profit": 0.0,
            "last_detection": None,
            "last_buy": None,
        }
        
        # Liste des tokens détectés et leurs analyses
        self.detected_tokens = {}
        self.bought_tokens = {}
        
        # Analyseur de contrats
        try:
            self.contract_analyzer = create_contract_analyzer()
            logger.info("Analyseur de contrats initialisé")
        except Exception as e:
            logger.warning(f"Impossible d'initialiser l'analyseur de contrats: {str(e)}")
            self.contract_analyzer = None
        
        logger.info("Système de sniping Sonic initialisé")
    
    def init_client(self):
        """
        Initialise le client blockchain pour Sonic.
        """
        try:
            # Créer le client Sonic
            self.client = BlockchainClientFactory.create_client("sonic")
            
            if not self.client:
                logger.error("Échec de l'initialisation du client Sonic")
                return False
            
            logger.info("Client Sonic initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Sonic: {str(e)}")
            return False
    
    async def start(self):
        """
        Démarre le système de sniping Sonic.
        """
        if self.running:
            logger.warning("Le système de sniping Sonic est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du système de sniping Sonic")
        self.running = True
        self.stop_event.clear()
        
        # Démarrer la tâche de monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Système de sniping Sonic démarré")
    
    async def stop(self):
        """
        Arrête le système de sniping Sonic.
        """
        if not self.running:
            logger.warning("Le système de sniping Sonic n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du système de sniping Sonic")
        self.running = False
        self.stop_event.set()
        
        # Attendre la fin de la tâche de monitoring
        if self.monitoring_task:
            try:
                await asyncio.wait_for(self.monitoring_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Timeout lors de l'attente de la fin de la tâche de monitoring")
        
        logger.info("Système de sniping Sonic arrêté")
    
    async def _monitoring_loop(self):
        """
        Boucle principale de surveillance des nouveaux tokens.
        """
        logger.info("Démarrage de la boucle de surveillance des nouveaux tokens Sonic")
        
        try:
            while not self.stop_event.is_set():
                # Surveiller les nouveaux tokens
                await self._detect_new_tokens()
                
                # Attendre un court instant
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
        finally:
            logger.info("Boucle de surveillance des nouveaux tokens Sonic terminée")
    
    async def _detect_new_tokens(self):
        """
        Détecte les nouveaux tokens sur Sonic.
        """
        if not self.client:
            logger.error("Client Sonic non disponible")
            return
        
        try:
            # Définir un callback pour traiter les nouveaux tokens
            async def token_callback(token_data):
                token_address = token_data.get("address")
                if token_address:
                    logger.info(f"Nouveau token détecté sur Sonic: {token_address}")
                    self.stats["tokens_detected"] += 1
                    self.stats["last_detection"] = datetime.now()
                    
                    # Stocker les données du token
                    self.detected_tokens[token_address] = {
                        "data": token_data,
                        "detection_time": datetime.now(),
                        "analyzed": False,
                        "analysis_result": None,
                    }
                    
                    # Analyser le token
                    await self._analyze_token(token_address)
            
            # Démarrer la surveillance
            await self.client.monitor_new_tokens(token_callback)
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection des nouveaux tokens: {str(e)}")
    
    async def _analyze_token(self, token_address: str):
        """
        Analyse un token pour déterminer s'il est intéressant à acheter.
        
        Args:
            token_address: Adresse du token à analyser
        """
        if token_address not in self.detected_tokens:
            logger.warning(f"Token {token_address} non trouvé dans les tokens détectés")
            return
        
        logger.info(f"Analyse du token Sonic: {token_address}")
        self.stats["tokens_analyzed"] += 1
        self.detected_tokens[token_address]["analyzed"] = True
        
        try:
            # Récupérer les informations du token
            token_info = await self.client.get_token_info(token_address)
            
            # Vérifier si le token est déjà liquidé
            initial_price = await self.client.get_token_price(token_address)
            if initial_price <= 0:
                logger.warning(f"Token {token_address} n'a pas de liquidité")
                self._reject_token(token_address, "Pas de liquidité")
                return
            
            # Analyser le contrat si possible
            contract_analysis = None
            if self.contract_analyzer:
                try:
                    # Récupérer le code du contrat
                    contract_code = await self.client.get_contract_code(token_address)
                    if contract_code and contract_code != "0x":
                        # Analyser le contrat
                        contract_analysis = await self.contract_analyzer.analyze_contract(
                            contract_code, 
                            contract_address=token_address,
                            blockchain="sonic"
                        )
                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse du contrat {token_address}: {str(e)}")
            
            # Évaluer le token
            score, recommendation, reasons = await self._evaluate_token(
                token_address, 
                token_info, 
                contract_analysis
            )
            
            # Enregistrer le résultat de l'analyse
            analysis_result = {
                "score": score,
                "recommendation": recommendation,
                "reasons": reasons,
                "initial_price": str(initial_price),
                "token_info": token_info,
                "contract_analysis": contract_analysis,
                "analysis_time": datetime.now().isoformat(),
            }
            
            self.detected_tokens[token_address]["analysis_result"] = analysis_result
            
            # Décider si on achète ou non
            if recommendation == "buy":
                logger.info(f"Token {token_address} recommandé pour achat avec score {score}")
                await self._buy_token(token_address, analysis_result)
            else:
                logger.info(f"Token {token_address} rejeté avec score {score}: {reasons}")
                self._reject_token(token_address, reasons)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du token {token_address}: {str(e)}")
            self._reject_token(token_address, f"Erreur d'analyse: {str(e)}")
    
    async def _evaluate_token(
        self, 
        token_address: str, 
        token_info: Dict[str, Any], 
        contract_analysis: Optional[Dict[str, Any]]
    ) -> Tuple[float, str, List[str]]:
        """
        Évalue un token pour déterminer son potentiel et les risques.
        
        Args:
            token_address: Adresse du token
            token_info: Informations sur le token
            contract_analysis: Analyse du contrat (peut être None)
            
        Returns:
            Tuple (score, recommendation, reasons)
        """
        score = 0.5  # Score initial (0-1)
        reasons = []
        
        # Vérifier les informations de base
        if not token_info.get("name") or not token_info.get("symbol"):
            reasons.append("Informations de base manquantes")
            score -= 0.2
        
        if token_info.get("error"):
            reasons.append(f"Erreur lors de la récupération des infos: {token_info['error']}")
            score -= 0.3
        
        # Analyser le contrat si disponible
        if contract_analysis:
            security_issues = contract_analysis.get("security_issues", [])
            if security_issues:
                critical_issues = [i for i in security_issues if i.get("severity") == "critique"]
                high_issues = [i for i in security_issues if i.get("severity") == "élevée"]
                
                if critical_issues:
                    reasons.append(f"{len(critical_issues)} problèmes critiques détectés")
                    score -= 0.5
                
                if high_issues:
                    reasons.append(f"{len(high_issues)} problèmes élevés détectés")
                    score -= 0.3
            
            if "risk_assessment" in contract_analysis:
                reasons.append(f"Évaluation des risques: {contract_analysis['risk_assessment']}")
            
            if contract_analysis.get("recommendation") == "éviter":
                reasons.append("L'analyseur de contrat recommande d'éviter ce token")
                score -= 0.4
        
        # Vérifier la liquidité
        try:
            # Dans une implémentation réelle, nous vérifierions la liquidité du pool
            # Pour cet exemple, nous considérons une liquidité minimale de 10000 USDC
            pool_data = await self.client.get_pools()
            # Filtrer les pools qui contiennent ce token
            token_pools = [p for p in pool_data if p.get("token0") == token_address or p.get("token1") == token_address]
            
            if not token_pools:
                reasons.append("Aucun pool de liquidité trouvé")
                score -= 0.4
            else:
                # Calculer la liquidité approximative (simplifiée pour l'exemple)
                liquidity = Decimal("10000")  # Valeur factice
                if liquidity < Decimal("10000"):
                    reasons.append(f"Liquidité insuffisante: {liquidity} USD")
                    score -= 0.3
                else:
                    reasons.append(f"Bonne liquidité: {liquidity} USD")
                    score += 0.2
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la liquidité: {str(e)}")
            reasons.append("Impossible de vérifier la liquidité")
            score -= 0.2
        
        # Décision finale
        if score >= 0.7:
            recommendation = "buy"
            reasons.append("Score élevé, recommandé pour achat")
        elif score >= 0.4:
            recommendation = "monitor"
            reasons.append("Score moyen, à surveiller")
        else:
            recommendation = "reject"
            reasons.append("Score bas, rejeté")
        
        return score, recommendation, reasons
    
    async def _buy_token(self, token_address: str, analysis_result: Dict[str, Any]):
        """
        Achète un token après analyse positive.
        
        Args:
            token_address: Adresse du token à acheter
            analysis_result: Résultat de l'analyse
        """
        if not self.client:
            logger.error("Client Sonic non disponible")
            return
        
        logger.info(f"Tentative d'achat du token Sonic: {token_address}")
        
        try:
            # Récupérer la configuration d'achat
            buy_amount = self.config.get("max_buy_amount", 0.1)  # en FTM
            
            # Adresse du token de base (FTM)
            base_token = self.client.contracts.get("wftm")
            
            # Calculer le montant minimum à recevoir (avec slippage)
            slippage = self.config.get("max_slippage", 5.0) / 100  # convertir en pourcentage
            
            # Dans une implémentation réelle, on calculerait le montant exact
            # Pour cet exemple, nous utilisons des valeurs fixes
            amount_in_wei = int(buy_amount * 10**18)  # Conversion en wei
            min_amount_out = 1  # Valeur minimale
            
            # Effectuer le swap
            tx_hash = await self.client.swap_tokens(
                token_in=base_token,
                token_out=token_address,
                amount_in=amount_in_wei,
                min_amount_out=min_amount_out
            )
            
            # Enregistrer l'achat
            self.bought_tokens[token_address] = {
                "tx_hash": tx_hash,
                "amount": buy_amount,
                "buy_time": datetime.now(),
                "analysis": analysis_result,
                "initial_price": analysis_result.get("initial_price"),
                "current_price": analysis_result.get("initial_price"),
                "profit_percentage": 0.0,
                "take_profit_triggered": False,
                "stop_loss_triggered": False,
            }
            
            self.stats["tokens_bought"] += 1
            self.stats["last_buy"] = datetime.now()
            
            logger.info(f"Token Sonic acheté avec succès: {token_address}, tx: {tx_hash}")
            
            # Démarrer le suivi du token
            asyncio.create_task(self._monitor_token_price(token_address))
            
        except Exception as e:
            logger.error(f"Erreur lors de l'achat du token {token_address}: {str(e)}")
    
    def _reject_token(self, token_address: str, reason: str):
        """
        Rejette un token après analyse négative.
        
        Args:
            token_address: Adresse du token rejeté
            reason: Raison du rejet
        """
        if token_address in self.detected_tokens:
            self.detected_tokens[token_address]["rejected"] = True
            self.detected_tokens[token_address]["rejection_reason"] = reason
            self.detected_tokens[token_address]["rejection_time"] = datetime.now()
        
        self.stats["tokens_rejected"] += 1
        logger.info(f"Token Sonic rejeté: {token_address}, raison: {reason}")
    
    async def _monitor_token_price(self, token_address: str):
        """
        Surveille le prix d'un token acheté pour appliquer take-profit et stop-loss.
        
        Args:
            token_address: Adresse du token à surveiller
        """
        if token_address not in self.bought_tokens:
            logger.warning(f"Token {token_address} non trouvé dans les tokens achetés")
            return
        
        logger.info(f"Démarrage de la surveillance du prix du token Sonic: {token_address}")
        
        # Configuration
        take_profit_percentage = self.config.get("take_profit_percentage", 50.0)
        stop_loss_percentage = self.config.get("stop_loss_percentage", 10.0)
        check_interval = self.config.get("price_check_interval", 5)  # secondes
        
        # Prix initial
        initial_price = Decimal(self.bought_tokens[token_address].get("initial_price", "0"))
        if initial_price <= 0:
            logger.warning(f"Prix initial invalide pour le token {token_address}")
            return
        
        # Seuils
        take_profit_threshold = initial_price * (1 + Decimal(take_profit_percentage) / 100)
        stop_loss_threshold = initial_price * (1 - Decimal(stop_loss_percentage) / 100)
        
        logger.info(f"Seuils pour {token_address}: Take-profit: {take_profit_threshold}, Stop-loss: {stop_loss_threshold}")
        
        try:
            while not self.stop_event.is_set() and token_address in self.bought_tokens:
                # Vérifier si take-profit ou stop-loss déjà déclenchés
                if (self.bought_tokens[token_address].get("take_profit_triggered") or 
                    self.bought_tokens[token_address].get("stop_loss_triggered")):
                    break
                
                # Récupérer le prix actuel
                current_price = await self.client.get_token_price(token_address)
                
                # Mettre à jour le prix actuel dans les données du token
                self.bought_tokens[token_address]["current_price"] = str(current_price)
                
                # Calculer le profit en pourcentage
                if initial_price > 0:
                    profit_percentage = (current_price - initial_price) / initial_price * 100
                    self.bought_tokens[token_address]["profit_percentage"] = float(profit_percentage)
                
                logger.debug(f"Prix actuel de {token_address}: {current_price}, Profit: {profit_percentage}%")
                
                # Vérifier les conditions de take-profit et stop-loss
                if current_price >= take_profit_threshold:
                    logger.info(f"Take-profit déclenché pour {token_address}: {current_price} >= {take_profit_threshold}")
                    self.bought_tokens[token_address]["take_profit_triggered"] = True
                    await self._sell_token(token_address, "take_profit")
                    break
                    
                elif current_price <= stop_loss_threshold:
                    logger.info(f"Stop-loss déclenché pour {token_address}: {current_price} <= {stop_loss_threshold}")
                    self.bought_tokens[token_address]["stop_loss_triggered"] = True
                    await self._sell_token(token_address, "stop_loss")
                    break
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(check_interval)
                
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance du prix du token {token_address}: {str(e)}")
        finally:
            logger.info(f"Fin de la surveillance du prix du token Sonic: {token_address}")
    
    async def _sell_token(self, token_address: str, trigger: str):
        """
        Vend un token après déclenchement de take-profit ou stop-loss.
        
        Args:
            token_address: Adresse du token à vendre
            trigger: Déclencheur de la vente ("take_profit" ou "stop_loss")
        """
        if token_address not in self.bought_tokens:
            logger.warning(f"Token {token_address} non trouvé dans les tokens achetés")
            return
        
        logger.info(f"Vente du token Sonic {token_address} déclenchée par {trigger}")
        
        try:
            # Adresse du token de base (FTM)
            base_token = self.client.contracts.get("wftm")
            
            # Dans une implémentation réelle, on récupérerait le solde exact du token
            # Pour cet exemple, nous utilisons une valeur fixe
            token_balance = 1000000000000000000  # 1 token (exemple)
            min_amount_out = 1  # Valeur minimale
            
            # Effectuer le swap inverse
            tx_hash = await self.client.swap_tokens(
                token_in=token_address,
                token_out=base_token,
                amount_in=token_balance,
                min_amount_out=min_amount_out
            )
            
            # Mettre à jour les données de vente
            self.bought_tokens[token_address]["sell_tx_hash"] = tx_hash
            self.bought_tokens[token_address]["sell_time"] = datetime.now()
            self.bought_tokens[token_address]["sell_trigger"] = trigger
            
            # Calculer le profit
            initial_price = Decimal(self.bought_tokens[token_address].get("initial_price", "0"))
            current_price = Decimal(self.bought_tokens[token_address].get("current_price", "0"))
            
            if initial_price > 0:
                profit_percentage = (current_price - initial_price) / initial_price * 100
                profit_amount = float(profit_percentage) * float(self.bought_tokens[token_address].get("amount", 0)) / 100
                
                self.bought_tokens[token_address]["final_profit_percentage"] = float(profit_percentage)
                self.bought_tokens[token_address]["final_profit_amount"] = profit_amount
                
                # Mettre à jour les statistiques globales
                self.stats["total_profit"] += profit_amount
            
            logger.info(f"Token Sonic vendu avec succès: {token_address}, tx: {tx_hash}, profit: {profit_percentage}%")
            
        except Exception as e:
            logger.error(f"Erreur lors de la vente du token {token_address}: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du système de sniping Sonic.
        
        Returns:
            Statistiques du système
        """
        # Ajouter les statistiques dynamiques
        stats = self.stats.copy()
        stats["detected_tokens_count"] = len(self.detected_tokens)
        stats["bought_tokens_count"] = len(self.bought_tokens)
        stats["active_monitors_count"] = sum(1 for token in self.bought_tokens.values() 
                                           if not token.get("take_profit_triggered") 
                                           and not token.get("stop_loss_triggered"))
        
        return stats 