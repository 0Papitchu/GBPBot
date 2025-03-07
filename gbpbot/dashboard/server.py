#!/usr/bin/env python3
"""
Serveur FastAPI pour le dashboard GBPBot.
Combine l'API REST et le serveur WebSocket.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import asyncio
import logging
import os
import sys
from typing import Set, Dict, Any
from datetime import datetime
from decimal import Decimal

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules du dashboard
from gbpbot.dashboard.api import setup_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dashboard.log")
    ]
)
logger = logging.getLogger("dashboard_server")

# Création de l'application FastAPI
app = FastAPI(
    title="GBPBot Dashboard",
    description="Interface de monitoring et de contrôle du GBPBot",
    version="1.0.0"
)

# Montage des fichiers statiques
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialisation des templates
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

# Connexions WebSocket actives
active_connections: Set[WebSocket] = set()

# Encodeur JSON pour gérer les types spéciaux
class CustomJSONEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour gérer les types spéciaux."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def broadcast_metrics(metrics: Dict[str, Any]):
    """Diffuse les métriques à tous les clients connectés via WebSocket."""
    if not active_connections:
        return
        
    encoded_metrics = json.dumps(metrics, cls=CustomJSONEncoder)
    dead_connections = set()
    
    for connection in active_connections:
        try:
            await connection.send_text(encoded_metrics)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des métriques: {str(e)}")
            dead_connections.add(connection)
            
    # Nettoyer les connexions mortes
    active_connections.difference_update(dead_connections)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Page principale du dashboard."""
    try:
        with open(os.path.join(static_dir, "index.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
            <head>
                <title>GBPBot Dashboard</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                    .container { background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    h1 { color: #0066cc; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>GBPBot Dashboard</h1>
                    <p>Le fichier index.html est manquant dans le dossier static. Assurez-vous qu'il est correctement installé.</p>
                </div>
            </body>
        </html>
        """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pour les mises à jour en temps réel."""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        # Envoyer des données initiales
        initial_data = {
            "event": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connexion WebSocket établie"
        }
        await websocket.send_text(json.dumps(initial_data, cls=CustomJSONEncoder))
        
        # Boucle de réception des messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Traiter les messages du client si nécessaire
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
            except json.JSONDecodeError:
                logger.warning(f"Message WebSocket invalide reçu: {data}")
                
    except WebSocketDisconnect:
        logger.info("Client WebSocket déconnecté")
    except Exception as e:
        logger.exception(f"Erreur WebSocket: {str(e)}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

# Classe principale du Dashboard
class Dashboard:
    """Gestionnaire principal du dashboard."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Initialise le dashboard avec les paramètres spécifiés."""
        self.host = host
        self.port = port
        self.running = False
        self.server = None
        
        # Configuration de l'API REST
        setup_router(app)
        
    async def start(self):
        """Démarre le serveur dashboard."""
        if not self.running:
            self.running = True
            
            # Démarrer le serveur en arrière-plan
            config = uvicorn.Config(app=app, host=self.host, port=self.port, log_level="info")
            self.server = uvicorn.Server(config)
            await self.server.serve()
    
    async def stop(self):
        """Arrête le serveur dashboard."""
        if self.running and self.server:
            self.running = False
            await self.server.shutdown()
            logger.info("Serveur dashboard arrêté")
    
    async def update_metrics(self, metrics: Dict[str, Any]):
        """Met à jour les métriques et les diffuse aux clients."""
        if self.running:
            # Transmettre les métriques à l'API pour mise à jour
            try:
                # Mettre à jour les métriques via l'API
                from gbpbot.dashboard.api import update_metrics
                await update_metrics(metrics)
                
                # Diffuser aux clients WebSocket
                await broadcast_metrics(metrics)
            except Exception as e:
                logger.exception(f"Erreur lors de la mise à jour des métriques: {str(e)}")

# Point d'entrée pour exécution directe
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Serveur Dashboard GBPBot")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'hôte pour le serveur")
    parser.add_argument("--port", type=int, default=8000, help="Port pour le serveur")
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port) 