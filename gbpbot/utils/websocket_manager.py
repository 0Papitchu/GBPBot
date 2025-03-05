"""
Module de gestion des WebSockets pour GBPBot
Ce module fournit des fonctionnalités robustes pour la gestion des connexions WebSocket
"""

import asyncio
import websockets
import json
import time
import threading
import random
import hashlib
from typing import Dict, Any, Optional, Callable, List, Tuple, Union
from loguru import logger
from gbpbot.config.config_manager import config_manager
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

# Configuration par défaut pour le WebSocket Manager
DEFAULT_WEBSOCKET_CONFIG = {
    "heartbeat_interval": 30,
    "reconnect_interval": 5,
    "max_reconnect_attempts": 10,
    "max_backoff": 60,
    "ping_interval": 30,
    "ping_timeout": 10,
    "close_timeout": 5,
    "reconnect_delay": 1,
    "max_reconnect_delay": 60,
    "jitter": True,
    "max_message_size": 10485760
}

class WebSocketManager:
    """
    Gestionnaire de connexions WebSocket avec reconnexion automatique et gestion d'état
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le gestionnaire de WebSockets
        """
        if not hasattr(self, 'initialized'):
            # Charger la configuration
            try:
                self.config = config_manager.get_config("websocket")
            except (KeyError, AttributeError):
                logger.warning("Configuration WebSocket non trouvée, utilisation des valeurs par défaut")
                self.config = DEFAULT_WEBSOCKET_CONFIG
            
            # Initialiser les connexions
            self.connections = {}
            self.connection_tasks = {}
            self.connection_status = {}
            self.message_callbacks = {}
            self.connection_callbacks = {}
            self.disconnection_callbacks = {}
            self.reconnection_tasks = {}
            self.message_queues = {}
            self.connection_locks = {}
            
            # Statistiques
            self.stats = {
                "total_connections": 0,
                "active_connections": 0,
                "reconnections": 0,
                "messages_sent": 0,
                "messages_received": 0,
                "connection_errors": 0,
                "message_errors": 0
            }
            
            # Initialiser le gestionnaire d'événements
            self.event_loop = None
            try:
                self.event_loop = asyncio.get_event_loop()
            except RuntimeError:
                # Pas d'event loop dans ce thread, on n'en crée pas un nouveau ici
                # Il sera créé au besoin lors de l'utilisation
                pass
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Gestionnaire WebSocket initialisé")
    
    def reset(self):
        """
        Réinitialise le gestionnaire WebSocket (utile pour les tests)
        """
        # Fermer toutes les connexions existantes
        if hasattr(self, 'connections'):
            for connection_id in list(self.connections.keys()):
                if self.event_loop and self.event_loop.is_running():
                    asyncio.create_task(self.disconnect(connection_id))
                else:
                    # Créer une nouvelle boucle pour la déconnexion
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.disconnect(connection_id))
                    loop.close()
        
        # Réinitialiser les structures de données
        self.connections = {}
        self.connection_tasks = {}
        self.connection_status = {}
        self.message_callbacks = {}
        self.connection_callbacks = {}
        self.disconnection_callbacks = {}
        self.reconnection_tasks = {}
        self.message_queues = {}
        self.connection_locks = {}
        
        # Réinitialiser les statistiques
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "reconnections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "connection_errors": 0,
            "message_errors": 0
        }
        
        logger.info("Gestionnaire WebSocket réinitialisé")
    
    def _generate_connection_id(self, url: str, params: Dict = None) -> str:
        """
        Génère un identifiant unique pour une connexion WebSocket
        
        Args:
            url: URL du WebSocket
            params: Paramètres supplémentaires
            
        Returns:
            str: Identifiant unique
        """
        # Créer une représentation de la connexion
        connection_repr = {
            "url": url,
            "params": params or {}
        }
        
        # Convertir en JSON et hacher
        connection_json = json.dumps(connection_repr, sort_keys=True)
        return hashlib.md5(connection_json.encode()).hexdigest()[:12]
    
    async def connect(self, url: str, params: Dict = None, 
                      on_message: Callable = None, 
                      on_connect: Callable = None,
                      on_disconnect: Callable = None,
                      auto_reconnect: bool = True,
                      connection_id: str = None) -> str:
        """
        Établit une connexion WebSocket
        
        Args:
            url: URL du WebSocket
            params: Paramètres supplémentaires
            on_message: Callback appelé à la réception d'un message
            on_connect: Callback appelé à la connexion
            on_disconnect: Callback appelé à la déconnexion
            auto_reconnect: Si la reconnexion automatique est activée
            connection_id: Identifiant de connexion personnalisé
            
        Returns:
            str: Identifiant de la connexion
        """
        # Générer un identifiant de connexion si non fourni
        if connection_id is None:
            connection_id = self._generate_connection_id(url, params)
        
        # Vérifier si la connexion existe déjà
        if connection_id in self.connections:
            logger.warning(f"Connexion WebSocket {connection_id} déjà établie")
            return connection_id
        
        # Initialiser les structures pour cette connexion
        self.connection_status[connection_id] = {
            "url": url,
            "params": params or {},
            "connected": False,
            "connecting": True,
            "last_connected": 0,
            "last_disconnected": 0,
            "reconnect_attempts": 0,
            "auto_reconnect": auto_reconnect,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }
        
        # Initialiser les callbacks
        if on_message:
            self.message_callbacks[connection_id] = on_message
        if on_connect:
            self.connection_callbacks[connection_id] = on_connect
        if on_disconnect:
            self.disconnection_callbacks[connection_id] = on_disconnect
        
        # Initialiser la file de messages
        self.message_queues[connection_id] = asyncio.Queue()
        
        # Initialiser le verrou de connexion
        self.connection_locks[connection_id] = asyncio.Lock()
        
        # Créer la tâche de connexion
        try:
            # Essayer d'obtenir la boucle d'événements actuelle
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Créer une nouvelle boucle si nécessaire
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        connection_task = asyncio.create_task(
            self._connection_handler(connection_id, url, params or {})
        )
        self.connection_tasks[connection_id] = connection_task
        
        # Mettre à jour les statistiques
        self.stats["total_connections"] += 1
        
        logger.info(f"Connexion WebSocket {connection_id} initiée vers {url}")
        
        return connection_id
    
    async def _connection_handler(self, connection_id: str, url: str, params: Dict) -> None:
        """
        Gère une connexion WebSocket
        
        Args:
            connection_id: Identifiant de la connexion
            url: URL du WebSocket
            params: Paramètres supplémentaires
        """
        # Extraire les paramètres de connexion
        headers = params.get("headers", {})
        ping_interval = params.get("ping_interval", self.config.get("ping_interval", 30))
        ping_timeout = params.get("ping_timeout", self.config.get("ping_timeout", 10))
        close_timeout = params.get("close_timeout", self.config.get("close_timeout", 5))
        max_size = params.get("max_size", self.config.get("max_message_size", 10485760))
        
        # Boucle de reconnexion
        while True:
            try:
                # Mettre à jour le statut
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["connecting"] = True
                else:
                    # La connexion a été supprimée pendant la reconnexion
                    logger.info(f"Connexion {connection_id} supprimée, arrêt du handler")
                    break
                
                # Établir la connexion
                # Utiliser la version correcte de websockets.connect selon la version de la bibliothèque
                try:
                    # Pour websockets >= 10.0
                    websocket = await websockets.connect(
                        url,
                        extra_headers=headers,
                        ping_interval=ping_interval,
                        ping_timeout=ping_timeout,
                        close_timeout=close_timeout,
                        max_size=max_size
                    )
                except TypeError:
                    # Pour websockets < 10.0
                    websocket = await websockets.connect(
                        url,
                        extra_headers=headers,
                        ping_interval=ping_interval,
                        ping_timeout=ping_timeout,
                        close_timeout=close_timeout,
                        max_size=max_size,
                        subprotocols=None
                    )
                
                # Stocker la connexion
                self.connections[connection_id] = websocket
                
                # Mettre à jour le statut
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["connected"] = True
                    self.connection_status[connection_id]["connecting"] = False
                    self.connection_status[connection_id]["last_connected"] = time.time()
                    self.connection_status[connection_id]["reconnect_attempts"] = 0
                else:
                    # La connexion a été supprimée pendant la connexion
                    await websocket.close()
                    logger.info(f"Connexion {connection_id} supprimée, fermeture du websocket")
                    break
                
                # Mettre à jour les statistiques
                self.stats["active_connections"] += 1
                
                logger.info(f"Connexion WebSocket {connection_id} établie")
                
                # Appeler le callback de connexion
                if connection_id in self.connection_callbacks:
                    try:
                        callback = self.connection_callbacks[connection_id]
                        if asyncio.iscoroutinefunction(callback):
                            await callback(connection_id)
                        else:
                            callback(connection_id)
                    except Exception as e:
                        logger.error(f"Erreur dans le callback de connexion pour {connection_id}: {str(e)}")
                
                # Créer les tâches de réception et d'envoi
                receive_task = asyncio.create_task(self._receive_handler(connection_id, websocket))
                send_task = asyncio.create_task(self._send_handler(connection_id, websocket))
                
                # Attendre que l'une des tâches se termine
                done, pending = await asyncio.wait(
                    [receive_task, send_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Annuler les tâches en attente
                for task in pending:
                    task.cancel()
                
                # Attendre que les tâches soient annulées
                try:
                    await asyncio.gather(*pending, return_exceptions=True)
                except asyncio.CancelledError:
                    pass
                
                # Fermer la connexion WebSocket
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Erreur lors de la fermeture du WebSocket {connection_id}: {str(e)}")
                
                # Si on arrive ici, la connexion a été fermée proprement
                logger.info(f"Connexion WebSocket {connection_id} fermée proprement")
            
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                logger.warning(f"Connexion WebSocket {connection_id} fermée: {str(e)}")
                self.stats["connection_errors"] += 1
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["errors"] += 1
            
            except Exception as e:
                logger.error(f"Erreur de connexion WebSocket {connection_id}: {str(e)}")
                self.stats["connection_errors"] += 1
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["errors"] += 1
            
            finally:
                # Mettre à jour le statut
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["connected"] = False
                    self.connection_status[connection_id]["connecting"] = False
                    self.connection_status[connection_id]["last_disconnected"] = time.time()
                
                # Mettre à jour les statistiques
                if self.stats["active_connections"] > 0:
                    self.stats["active_connections"] -= 1
                
                # Supprimer la connexion
                if connection_id in self.connections:
                    del self.connections[connection_id]
                
                # Appeler le callback de déconnexion
                if connection_id in self.disconnection_callbacks:
                    try:
                        callback = self.disconnection_callbacks[connection_id]
                        if asyncio.iscoroutinefunction(callback):
                            await callback(connection_id)
                        else:
                            callback(connection_id)
                    except Exception as e:
                        logger.error(f"Erreur dans le callback de déconnexion pour {connection_id}: {str(e)}")
            
            # Vérifier si la reconnexion est activée
            if not self.connection_status.get(connection_id, {}).get("auto_reconnect", False):
                logger.info(f"Reconnexion automatique désactivée pour {connection_id}")
                break
            
            # Vérifier si la connexion a été explicitement fermée
            if connection_id not in self.connection_status:
                logger.info(f"Connexion {connection_id} supprimée, arrêt du handler")
                break
            
            # Calculer le délai de reconnexion avec backoff exponentiel
            self.connection_status[connection_id]["reconnect_attempts"] += 1
            reconnect_attempts = self.connection_status[connection_id]["reconnect_attempts"]
            
            base_delay = self.config.get("reconnect_delay", 1)
            max_delay = self.config.get("max_reconnect_delay", 60)
            
            # Backoff exponentiel avec jitter
            delay = min(base_delay * (2 ** (reconnect_attempts - 1)), max_delay)
            if self.config.get("jitter", True):
                delay += random.uniform(0, delay * 0.2)
            
            logger.info(f"Tentative de reconnexion WebSocket {connection_id} dans {delay:.2f}s (tentative {reconnect_attempts})")
            
            # Mettre à jour les statistiques
            self.stats["reconnections"] += 1
            
            # Attendre avant de reconnecter
            await asyncio.sleep(delay)
    
    async def _receive_handler(self, connection_id: str, websocket) -> None:
        """
        Gère la réception des messages WebSocket
        
        Args:
            connection_id: Identifiant de la connexion
            websocket: Connexion WebSocket
        """
        try:
            async for message in websocket:
                # Mettre à jour les statistiques
                self.stats["messages_received"] += 1
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["messages_received"] += 1
                
                # Traiter le message
                try:
                    # Convertir le message en JSON si possible
                    if isinstance(message, str):
                        try:
                            message_data = json.loads(message)
                        except json.JSONDecodeError:
                            message_data = message
                    else:
                        message_data = message
                    
                    # Appeler le callback de message
                    if connection_id in self.message_callbacks:
                        callback = self.message_callbacks[connection_id]
                        if asyncio.iscoroutinefunction(callback):
                            await callback(connection_id, message_data)
                        else:
                            callback(connection_id, message_data)
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du message WebSocket {connection_id}: {str(e)}")
                    self.stats["message_errors"] += 1
        
        except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK):
            # Connexion fermée, sera gérée par le handler de connexion
            pass
        
        except Exception as e:
            logger.error(f"Erreur dans le handler de réception WebSocket {connection_id}: {str(e)}")
            self.stats["message_errors"] += 1
    
    async def _send_handler(self, connection_id: str, websocket) -> None:
        """
        Gère l'envoi des messages WebSocket
        
        Args:
            connection_id: Identifiant de la connexion
            websocket: Connexion WebSocket
        """
        try:
            while True:
                # Vérifier si la file de messages existe encore
                if connection_id not in self.message_queues:
                    logger.warning(f"File de messages pour {connection_id} supprimée, arrêt du handler d'envoi")
                    break
                
                # Attendre un message dans la file
                message = await self.message_queues[connection_id].get()
                
                # Vérifier si c'est un message de fin
                if message is None:
                    break
                
                # Convertir le message en JSON si nécessaire
                if not isinstance(message, (str, bytes)):
                    message = json.dumps(message)
                
                # Envoyer le message
                await websocket.send(message)
                
                # Mettre à jour les statistiques
                self.stats["messages_sent"] += 1
                if connection_id in self.connection_status:
                    self.connection_status[connection_id]["messages_sent"] += 1
                
                # Marquer la tâche comme terminée
                self.message_queues[connection_id].task_done()
        
        except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK):
            # Connexion fermée, sera gérée par le handler de connexion
            pass
        
        except Exception as e:
            logger.error(f"Erreur dans le handler d'envoi WebSocket {connection_id}: {str(e)}")
            self.stats["message_errors"] += 1
    
    async def send_message(self, connection_id: str, message: Any) -> bool:
        """
        Envoie un message sur une connexion WebSocket
        
        Args:
            connection_id: Identifiant de la connexion
            message: Message à envoyer
            
        Returns:
            bool: True si le message a été mis en file d'attente, False sinon
        """
        # Vérifier si la connexion existe
        if connection_id not in self.connection_status:
            logger.warning(f"Tentative d'envoi de message sur une connexion inexistante: {connection_id}")
            return False
        
        # Vérifier si la connexion est établie
        if not self.connection_status[connection_id]["connected"]:
            logger.warning(f"Tentative d'envoi de message sur une connexion non établie: {connection_id}")
            return False
        
        # Vérifier si la file de messages existe
        if connection_id not in self.message_queues:
            logger.warning(f"File de messages pour {connection_id} inexistante")
            return False
        
        # Mettre le message en file d'attente
        await self.message_queues[connection_id].put(message)
        
        return True
    
    async def disconnect(self, connection_id: str) -> bool:
        """
        Ferme une connexion WebSocket
        
        Args:
            connection_id: Identifiant de la connexion
            
        Returns:
            bool: True si la connexion a été fermée, False sinon
        """
        # Vérifier si la connexion existe
        if connection_id not in self.connection_status:
            logger.warning(f"Tentative de fermeture d'une connexion inexistante: {connection_id}")
            return False
        
        # Acquérir le verrou de connexion
        if connection_id in self.connection_locks:
            async with self.connection_locks[connection_id]:
                # Désactiver la reconnexion automatique
                self.connection_status[connection_id]["auto_reconnect"] = False
                
                # Fermer la connexion si elle est établie
                if connection_id in self.connections:
                    try:
                        # Envoyer un message de fin pour arrêter le handler d'envoi
                        if connection_id in self.message_queues:
                            await self.message_queues[connection_id].put(None)
                        
                        # Fermer la connexion WebSocket
                        await self.connections[connection_id].close()
                        
                        logger.info(f"Connexion WebSocket {connection_id} fermée")
                    except Exception as e:
                        logger.error(f"Erreur lors de la fermeture de la connexion WebSocket {connection_id}: {str(e)}")
                
                # Annuler la tâche de connexion
                if connection_id in self.connection_tasks:
                    try:
                        self.connection_tasks[connection_id].cancel()
                        await asyncio.gather(self.connection_tasks[connection_id], return_exceptions=True)
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation de la tâche de connexion {connection_id}: {str(e)}")
                
                # Annuler la tâche de reconnexion
                if connection_id in self.reconnection_tasks:
                    try:
                        self.reconnection_tasks[connection_id].cancel()
                        await asyncio.gather(self.reconnection_tasks[connection_id], return_exceptions=True)
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation de la tâche de reconnexion {connection_id}: {str(e)}")
                
                # Supprimer les structures de données
                for data_dict in [
                    self.connections, self.connection_tasks, self.connection_status,
                    self.message_callbacks, self.connection_callbacks, self.disconnection_callbacks,
                    self.reconnection_tasks, self.message_queues, self.connection_locks
                ]:
                    if connection_id in data_dict:
                        del data_dict[connection_id]
        else:
            logger.warning(f"Verrou de connexion pour {connection_id} inexistant")
            return False
        
        return True
    
    async def disconnect_all(self) -> None:
        """
        Ferme toutes les connexions WebSocket
        """
        # Copier les identifiants de connexion pour éviter les modifications pendant l'itération
        connection_ids = list(self.connection_status.keys())
        
        # Fermer chaque connexion
        for connection_id in connection_ids:
            await self.disconnect(connection_id)
        
        logger.info(f"Toutes les connexions WebSocket fermées ({len(connection_ids)} connexions)")
    
    def get_connection_status(self, connection_id: str = None) -> Union[Dict, List[Dict]]:
        """
        Récupère le statut d'une ou de toutes les connexions
        
        Args:
            connection_id: Identifiant de la connexion (optionnel)
            
        Returns:
            Dict ou List[Dict]: Statut de la connexion ou liste des statuts
        """
        if connection_id is not None:
            # Vérifier si la connexion existe
            if connection_id not in self.connection_status:
                return None
            
            return self.connection_status[connection_id]
        else:
            # Retourner le statut de toutes les connexions
            return [
                {
                    "connection_id": conn_id,
                    **status
                }
                for conn_id, status in self.connection_status.items()
            ]
    
    def is_connected(self, connection_id: str) -> bool:
        """
        Vérifie si une connexion est établie
        
        Args:
            connection_id: Identifiant de la connexion
            
        Returns:
            bool: True si la connexion est établie, False sinon
        """
        if connection_id not in self.connection_status:
            return False
        
        return self.connection_status[connection_id]["connected"]
    
    def get_stats(self) -> Dict:
        """
        Récupère les statistiques du gestionnaire WebSocket
        
        Returns:
            Dict: Statistiques
        """
        return self.stats
    
    def register_message_callback(self, connection_id: str, callback: Callable) -> bool:
        """
        Enregistre un callback pour les messages d'une connexion
        
        Args:
            connection_id: Identifiant de la connexion
            callback: Fonction de callback
            
        Returns:
            bool: True si le callback a été enregistré, False sinon
        """
        if connection_id not in self.connection_status:
            logger.warning(f"Tentative d'enregistrement d'un callback pour une connexion inexistante: {connection_id}")
            return False
        
        self.message_callbacks[connection_id] = callback
        return True
    
    def register_connection_callback(self, connection_id: str, callback: Callable) -> bool:
        """
        Enregistre un callback pour la connexion
        
        Args:
            connection_id: Identifiant de la connexion
            callback: Fonction de callback
            
        Returns:
            bool: True si le callback a été enregistré, False sinon
        """
        if connection_id not in self.connection_status:
            logger.warning(f"Tentative d'enregistrement d'un callback pour une connexion inexistante: {connection_id}")
            return False
        
        self.connection_callbacks[connection_id] = callback
        return True
    
    def register_disconnection_callback(self, connection_id: str, callback: Callable) -> bool:
        """
        Enregistre un callback pour la déconnexion
        
        Args:
            connection_id: Identifiant de la connexion
            callback: Fonction de callback
            
        Returns:
            bool: True si le callback a été enregistré, False sinon
        """
        if connection_id not in self.connection_status:
            logger.warning(f"Tentative d'enregistrement d'un callback pour une connexion inexistante: {connection_id}")
            return False
        
        self.disconnection_callbacks[connection_id] = callback
        return True

# Créer une instance singleton du gestionnaire WebSocket
websocket_manager = WebSocketManager() 