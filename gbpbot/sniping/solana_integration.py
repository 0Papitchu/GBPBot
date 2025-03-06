"""
Intégration du Solana Memecoin Sniper pour GBPBot
=================================================

Ce module fournit l'interface entre le sniper spécialisé de memecoins Solana
et le système principal de GBPBot.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple

# Importer le sniper Solana
from gbpbot.sniping.solana_memecoin_sniper import SolanaMemecoinSniper

logger = logging.getLogger("gbpbot.sniping.solana_integration")

class SolanaSnipingIntegration:
    """
    Classe d'intégration qui adapte le SolanaMemecoinSniper pour être utilisé
    avec le système GBPBot.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialise l'intégration du sniper Solana
        
        Args:
            config: Configuration pour le sniper
        """
        self.config = config or {}
        self.sniper = None
        self.running = False
        self.performance_data = {
            "tokens_detected": 0,
            "tokens_analyzed": 0,
            "tokens_sniped": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_profit_usd": 0.0,
            "active_positions": 0
        }
        self.active_positions = {}
        self.position_history = []
        
        # Configuration spécifique à Solana
        self.rpc_url = self.config.get("SOLANA_RPC_URL", os.environ.get("SOLANA_RPC_URL"))
        self.private_key = self.config.get("SOLANA_PRIVATE_KEY", os.environ.get("MAIN_PRIVATE_KEY"))
        
        logger.info("Intégration du sniper Solana initialisée")
    
    async def start(self) -> bool:
        """
        Démarre le sniper Solana
        
        Returns:
            bool: True si démarré avec succès, False sinon
        """
        if self.running:
            logger.warning("Le sniper Solana est déjà en cours d'exécution")
            return True
            
        try:
            # Créer et initialiser le sniper
            self.sniper = SolanaMemecoinSniper(
                rpc_url=self.rpc_url,
                private_key=self.private_key,
                config=self.config
            )
            
            # Démarrer le sniper
            success = await self.sniper.start()
            if success:
                self.running = True
                
                # Démarrer la tâche de mise à jour des performances
                asyncio.create_task(self._update_performance_loop())
                
                logger.info("Sniper Solana démarré avec succès")
                return True
            else:
                logger.error("Échec du démarrage du sniper Solana")
                return False
                
        except Exception as e:
            logger.exception(f"Erreur lors du démarrage du sniper Solana: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """
        Arrête le sniper Solana
        
        Returns:
            bool: True si arrêté avec succès, False sinon
        """
        if not self.running or not self.sniper:
            logger.warning("Le sniper Solana n'est pas en cours d'exécution")
            return True
            
        try:
            # Arrêter le sniper
            await self.sniper.stop()
            self.running = False
            
            logger.info("Sniper Solana arrêté avec succès")
            return True
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'arrêt du sniper Solana: {str(e)}")
            return False
    
    async def _update_performance_loop(self) -> None:
        """
        Met à jour périodiquement les données de performance depuis le sniper
        """
        try:
            while self.running and self.sniper:
                # Récupérer les statistiques du sniper
                stats = self.sniper.get_stats()
                
                # Mettre à jour les données de performance
                self.performance_data.update({
                    "tokens_detected": stats["tokens_detected"],
                    "tokens_analyzed": stats["tokens_analyzed"],
                    "tokens_sniped": stats["tokens_sniped"],
                    "successful_trades": stats["successful_snipes"],
                    "failed_trades": stats["failed_snipes"],
                    "total_profit_usd": stats["net_profit_usd"],
                    "active_positions": stats["active_snipes"]
                })
                
                # Attendre avant la prochaine mise à jour
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Boucle de mise à jour des performances arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de mise à jour des performances: {str(e)}")
    
    def get_performance_stats(self) -> Dict:
        """
        Récupère les statistiques de performance du sniper
        
        Returns:
            Dict: Statistiques de performance
        """
        if not self.running or not self.sniper:
            return self.performance_data
            
        try:
            # Récupérer les statistiques les plus récentes
            stats = self.sniper.get_stats()
            
            # Fusionner avec les données de performance
            self.performance_data.update({
                "tokens_detected": stats["tokens_detected"],
                "tokens_analyzed": stats["tokens_analyzed"],
                "tokens_sniped": stats["tokens_sniped"],
                "successful_trades": stats["successful_snipes"],
                "failed_trades": stats["failed_snipes"],
                "total_profit_usd": stats["net_profit_usd"],
                "active_positions": stats["active_snipes"],
                "hourly_profit": stats.get("hourly_profit", 0),
                "running_time": stats.get("running_time", "0:00:00")
            })
            
            return self.performance_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
            return self.performance_data
    
    def get_active_positions(self) -> List[Dict]:
        """
        Récupère la liste des positions actives
        
        Returns:
            List[Dict]: Liste des positions actives
        """
        # Cette fonction serait implémentée pour extraire les positions actives
        # du sniper et les formater selon les besoins de l'interface GBPBot
        return []
    
    def get_historical_positions(self) -> List[Dict]:
        """
        Récupère l'historique des positions
        
        Returns:
            List[Dict]: Historique des positions
        """
        # Cette fonction serait implémentée pour extraire l'historique des positions
        # du sniper et les formater selon les besoins de l'interface GBPBot
        return []
    
    async def update_configuration(self, new_config: Dict) -> bool:
        """
        Met à jour la configuration du sniper
        
        Args:
            new_config: Nouvelle configuration
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        # Redémarrer le sniper avec la nouvelle configuration
        # Dans une implémentation réelle, nous pourrions mettre à jour
        # la configuration sans redémarrer
        
        was_running = self.running
        if was_running:
            await self.stop()
            
        self.config.update(new_config)
        
        if was_running:
            return await self.start()
            
        return True


# Fonction d'aide pour créer facilement une instance d'intégration
def create_solana_sniper(config: Dict = None) -> SolanaSnipingIntegration:
    """
    Crée une instance d'intégration du sniper Solana
    
    Args:
        config: Configuration pour le sniper
        
    Returns:
        SolanaSnipingIntegration: Instance d'intégration
    """
    return SolanaSnipingIntegration(config) 