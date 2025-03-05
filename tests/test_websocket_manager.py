import asyncio
import json
import time
import threading
import unittest
import websockets
import random
from unittest.mock import patch, MagicMock
from gbpbot.utils.websocket_manager import WebSocketManager, websocket_manager
import pytest

# Utiliser pytest-asyncio pour les tests asynchrones
pytestmark = pytest.mark.asyncio

class TestWebSocketManager(unittest.TestCase):
    """Tests pour le gestionnaire WebSocket"""
    
    def setUp(self):
        """Initialise l'environnement de test"""
        # Réinitialiser le singleton pour chaque test
        websocket_manager.reset()
        
        # Choisir un port aléatoire pour éviter les conflits
        self.port = random.randint(8800, 9000)
        self.url = f"ws://localhost:{self.port}"
        
        # Démarrer un serveur WebSocket de test dans un thread séparé
        self.server_thread = threading.Thread(target=self.run_test_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Attendre que le serveur démarre
        time.sleep(0.5)
    
    def run_test_server(self):
        """Exécute un serveur WebSocket de test"""
        # Stocker les clients connectés
        connected_clients = set()
        
        async def handler(websocket, path):
            """Gère les connexions WebSocket entrantes"""
            # Ajouter le client à la liste des clients connectés
            connected_clients.add(websocket)
            
            # Envoyer un message de bienvenue
            await websocket.send(json.dumps({"type": "welcome", "message": "Bienvenue sur le serveur de test"}))
            
            try:
                # Boucle de réception des messages
                async for message in websocket:
                    # Traiter le message
                    try:
                        data = json.loads(message)
                        
                        # Si c'est un message d'écho, le renvoyer
                        if data.get("type") == "echo":
                            await websocket.send(json.dumps({
                                "type": "echo_response",
                                "message": data.get("message", ""),
                                "timestamp": time.time()
                            }))
                        
                        # Si c'est un message de broadcast, l'envoyer à tous les clients
                        elif data.get("type") == "broadcast":
                            for client in connected_clients:
                                await client.send(json.dumps({
                                    "type": "broadcast_message",
                                    "message": data.get("message", ""),
                                    "timestamp": time.time()
                                }))
                    
                    except json.JSONDecodeError:
                        # Message non-JSON, le renvoyer tel quel
                        await websocket.send(message)
            
            except websockets.exceptions.ConnectionClosed:
                pass
            
            finally:
                # Retirer le client de la liste des clients connectés
                if websocket in connected_clients:
                    connected_clients.remove(websocket)
        
        # Créer une boucle d'événements pour le serveur
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Démarrer le serveur WebSocket
        server = websockets.serve(handler, "localhost", self.port)
        loop.run_until_complete(server)
        loop.run_forever()
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Teste la connexion à un WebSocket"""
        # Créer un callback pour les messages
        messages_received = []
        
        async def on_message(conn_id, message):
            messages_received.append(message)
        
        # Créer un callback pour la connexion
        connection_established = asyncio.Event()
        
        async def on_connect(conn_id):
            connection_established.set()
        
        # Se connecter au WebSocket
        conn_id = await websocket_manager.connect(
            url=self.url,
            on_message=on_message,
            on_connect=on_connect
        )
        
        # Attendre que la connexion soit établie
        try:
            await asyncio.wait_for(connection_established.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.fail("La connexion n'a pas été établie dans le délai imparti")
        
        # Vérifier que la connexion est établie
        self.assertTrue(websocket_manager.is_connected(conn_id))
        
        # Attendre de recevoir le message de bienvenue
        await asyncio.sleep(1)
        
        # Vérifier qu'on a reçu le message de bienvenue
        self.assertEqual(len(messages_received), 1)
        self.assertEqual(messages_received[0]["type"], "welcome")
        
        # Fermer la connexion
        await websocket_manager.disconnect(conn_id)
        
        # Vérifier que la connexion est fermée
        self.assertFalse(websocket_manager.is_connected(conn_id))
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Teste l'envoi de messages via WebSocket"""
        # Créer un callback pour les messages
        messages_received = []
        
        async def on_message(conn_id, message):
            messages_received.append(message)
        
        # Se connecter au WebSocket
        conn_id = await websocket_manager.connect(
            url=self.url,
            on_message=on_message
        )
        
        # Attendre que la connexion soit établie
        await asyncio.sleep(1)
        
        # Envoyer un message d'écho
        await websocket_manager.send_message(conn_id, {
            "type": "echo",
            "message": "Test message"
        })
        
        # Attendre la réponse
        await asyncio.sleep(1)
        
        # Vérifier qu'on a reçu la réponse
        self.assertGreaterEqual(len(messages_received), 2)  # Message de bienvenue + réponse d'écho
        
        # Trouver le message d'écho dans les réponses
        echo_response = None
        for message in messages_received:
            if isinstance(message, dict) and message.get("type") == "echo_response":
                echo_response = message
                break
        
        # Vérifier le contenu de la réponse
        self.assertIsNotNone(echo_response)
        self.assertEqual(echo_response["message"], "Test message")
        
        # Fermer la connexion
        await websocket_manager.disconnect(conn_id)
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Teste la gestion de plusieurs connexions WebSocket simultanées"""
        # Nombre de connexions à tester
        num_connections = 3
        
        # Créer des callbacks pour chaque connexion
        messages_by_connection = {f"connection_{i}": [] for i in range(num_connections)}
        
        # Créer des callbacks pour les messages
        def create_message_callback(conn_index):
            async def on_message(conn_id, message):
                messages_by_connection[f"connection_{conn_index}"].append(message)
            return on_message
        
        # Créer des callbacks pour les connexions
        connection_events = {f"connection_{i}": asyncio.Event() for i in range(num_connections)}
        
        def create_connect_callback(conn_index):
            async def on_connect(conn_id):
                connection_events[f"connection_{conn_index}"].set()
            return on_connect
        
        # Se connecter aux WebSockets
        connection_ids = []
        for i in range(num_connections):
            conn_id = await websocket_manager.connect(
                url=self.url,
                on_message=create_message_callback(i),
                on_connect=create_connect_callback(i),
                connection_id=f"connection_{i}"
            )
            connection_ids.append(conn_id)
        
        # Attendre que toutes les connexions soient établies
        for i in range(num_connections):
            try:
                await asyncio.wait_for(connection_events[f"connection_{i}"].wait(), timeout=5)
            except asyncio.TimeoutError:
                self.fail(f"La connexion {i} n'a pas été établie dans le délai imparti")
        
        # Vérifier que toutes les connexions sont établies
        for conn_id in connection_ids:
            self.assertTrue(websocket_manager.is_connected(conn_id))
        
        # Attendre de recevoir les messages de bienvenue
        await asyncio.sleep(1)
        
        # Vérifier qu'on a reçu les messages de bienvenue sur chaque connexion
        for i in range(num_connections):
            self.assertGreaterEqual(len(messages_by_connection[f"connection_{i}"]), 1)
            self.assertEqual(messages_by_connection[f"connection_{i}"][0]["type"], "welcome")
        
        # Envoyer un message de broadcast sur la première connexion
        await websocket_manager.send_message(connection_ids[0], {
            "type": "broadcast",
            "message": "Broadcast test"
        })
        
        # Attendre que le message soit diffusé
        await asyncio.sleep(1)
        
        # Vérifier que toutes les connexions ont reçu le message de broadcast
        for i in range(num_connections):
            # Chercher le message de broadcast
            broadcast_received = False
            for message in messages_by_connection[f"connection_{i}"]:
                if isinstance(message, dict) and message.get("type") == "broadcast_message":
                    broadcast_received = True
                    self.assertEqual(message["message"], "Broadcast test")
                    break
            
            self.assertTrue(broadcast_received, f"La connexion {i} n'a pas reçu le message de broadcast")
        
        # Fermer toutes les connexions
        for conn_id in connection_ids:
            await websocket_manager.disconnect(conn_id)
        
        # Vérifier que toutes les connexions sont fermées
        for conn_id in connection_ids:
            self.assertFalse(websocket_manager.is_connected(conn_id))
    
    @pytest.mark.asyncio
    async def test_reconnection(self):
        """Teste la reconnexion automatique après une déconnexion"""
        # Créer un callback pour les messages
        messages_received = []
        
        async def on_message(conn_id, message):
            messages_received.append(message)
        
        # Créer un callback pour la connexion
        connection_count = 0
        connection_event = asyncio.Event()
        
        async def on_connect(conn_id):
            nonlocal connection_count
            connection_count += 1
            connection_event.set()
        
        # Créer un callback pour la déconnexion
        disconnection_event = asyncio.Event()
        
        async def on_disconnect(conn_id):
            disconnection_event.set()
        
        # Se connecter au WebSocket
        conn_id = await websocket_manager.connect(
            url=self.url,
            on_message=on_message,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            auto_reconnect=True
        )
        
        # Attendre que la connexion soit établie
        try:
            await asyncio.wait_for(connection_event.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.fail("La connexion n'a pas été établie dans le délai imparti")
        
        # Vérifier que la connexion est établie
        self.assertTrue(websocket_manager.is_connected(conn_id))
        
        # Attendre de recevoir le message de bienvenue
        await asyncio.sleep(1)
        
        # Vérifier qu'on a reçu le message de bienvenue
        self.assertEqual(len(messages_received), 1)
        self.assertEqual(messages_received[0]["type"], "welcome")
        
        # Simuler une déconnexion en fermant la connexion WebSocket
        if conn_id in websocket_manager.connections:
            # Utiliser la méthode disconnect pour fermer proprement la connexion
            # mais garder auto_reconnect à True
            websocket_manager.connection_status[conn_id]["auto_reconnect"] = True
            await websocket_manager.connections[conn_id].close()
        
        # Attendre que la déconnexion soit détectée
        try:
            await asyncio.wait_for(disconnection_event.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.fail("La déconnexion n'a pas été détectée dans le délai imparti")
        
        # Réinitialiser les événements pour la reconnexion
        connection_event.clear()
        disconnection_event.clear()
        
        # Attendre que la reconnexion se produise
        try:
            await asyncio.wait_for(connection_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            self.fail("La reconnexion n'a pas eu lieu dans le délai imparti")
        
        # Vérifier que la connexion est rétablie
        self.assertTrue(websocket_manager.is_connected(conn_id))
        
        # Vérifier qu'on a reçu un nouveau message de bienvenue
        self.assertGreaterEqual(len(messages_received), 2)
        
        # Vérifier que le compteur de connexions a été incrémenté
        self.assertEqual(connection_count, 2)
        
        # Fermer la connexion
        await websocket_manager.disconnect(conn_id)
        
        # Vérifier que la connexion est fermée
        self.assertFalse(websocket_manager.is_connected(conn_id))
    
    def tearDown(self):
        """Nettoie l'environnement de test"""
        # Fermer toutes les connexions
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(websocket_manager.disconnect_all())

if __name__ == "__main__":
    unittest.main() 