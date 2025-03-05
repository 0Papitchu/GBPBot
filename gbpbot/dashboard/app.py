#!/usr/bin/env python3
"""
Dashboard de monitoring en temps réel pour GBPBot.
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Set
import logging

app = FastAPI(title="GBPBot Dashboard")
app.mount("/static", StaticFiles(directory="gbpbot/dashboard/static"), name="static")

# Connexions WebSocket actives
active_connections: Set[WebSocket] = set()

class DecimalEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour gérer les Decimal."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def broadcast_metrics(metrics: Dict):
    """Diffuse les métriques à tous les clients connectés."""
    if not active_connections:
        return
        
    encoded_metrics = json.dumps(metrics, cls=DecimalEncoder)
    dead_connections = set()
    
    for connection in active_connections:
        try:
            await connection.send_text(encoded_metrics)
        except:
            dead_connections.add(connection)
            
    # Nettoyer les connexions mortes
    active_connections.difference_update(dead_connections)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Page principale du dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GBPBot Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/chart.js@3.7.0/dist/chart.min.css" rel="stylesheet">
        <link href="/static/styles.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container-fluid">
                <span class="navbar-brand mb-0 h1">GBPBot Dashboard</span>
                <span id="connection-status" class="badge bg-success">Connected</span>
            </div>
        </nav>
        
        <div class="container-fluid mt-3">
            <div class="row">
                <!-- Performance Metrics -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Performance Metrics</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-6">
                                    <div class="metric-box">
                                        <h6>Total Profit</h6>
                                        <span id="total-profit">0.00 ETH</span>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="metric-box">
                                        <h6>Success Rate</h6>
                                        <span id="success-rate">0%</span>
                                    </div>
                                </div>
                            </div>
                            <canvas id="profit-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <!-- Market Data -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Market Data</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-4">
                                    <div class="metric-box">
                                        <h6>DEX Price</h6>
                                        <span id="dex-price">0.00</span>
                                    </div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-box">
                                        <h6>CEX Price</h6>
                                        <span id="cex-price">0.00</span>
                                    </div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-box">
                                        <h6>Spread</h6>
                                        <span id="spread">0.00%</span>
                                    </div>
                                </div>
                            </div>
                            <canvas id="price-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-3">
                <!-- System Status -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>System Status</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-6">
                                    <div class="metric-box">
                                        <h6>Gas Price</h6>
                                        <span id="gas-price">0 Gwei</span>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="metric-box">
                                        <h6>Wallet Balance</h6>
                                        <span id="wallet-balance">0.00 ETH</span>
                                    </div>
                                </div>
                            </div>
                            <div class="alert-container mt-3">
                                <h6>Recent Alerts</h6>
                                <div id="alerts-list" class="list-group">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Recent Trades -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Recent Trades</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Time</th>
                                            <th>Type</th>
                                            <th>Amount</th>
                                            <th>Price</th>
                                            <th>Profit</th>
                                        </tr>
                                    </thead>
                                    <tbody id="trades-table">
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.0/dist/chart.min.js"></script>
        <script src="/static/dashboard.js"></script>
    </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Point d'entrée WebSocket pour les mises à jour en temps réel."""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        while True:
            # Garder la connexion active
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)

class Dashboard:
    """Gestionnaire du dashboard."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.is_running = False
        self._update_task = None
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Démarre le dashboard."""
        if self.is_running:
            return
            
        self.is_running = True
        self.logger.info("Starting dashboard server on %s:%d", self.host, self.port)
        
        import uvicorn
        config = uvicorn.Config(app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Arrête le dashboard."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self._update_task:
            self._update_task.cancel()
            
        self.logger.info("Dashboard server stopped")
    
    async def update_metrics(self, metrics: Dict):
        """Met à jour les métriques affichées."""
        if not self.is_running:
            return
            
        await broadcast_metrics(metrics) 