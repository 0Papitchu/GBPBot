#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
from security_config import SecurityConfig
import time
import json
import requests
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from loguru import logger
import sys

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
log_level = os.getenv("GBPBOT_LOG_LEVEL", "INFO")
logger.remove()
logger.add(sys.stderr, level=log_level)
logger.add("gbpbot_dashboard.log", rotation="10 MB", level=log_level)

# Créer l'application Flask
app = Flask(__name__, template_folder="templates")
CORS(app)

# Charger la configuration de sécurité
security_config = SecurityConfig()

# Configuration de l'API
API_URL = os.getenv("GBPBOT_API_URL", "http://127.0.0.1:5000")
API_KEY = os.getenv("GBPBOT_API_KEY", security_config.api_key)
API_TIMEOUT = int(os.getenv("GBPBOT_API_TIMEOUT", "5"))  # Timeout en secondes

# Routes du dashboard
@app.route("/")
def index():
    """Page principale du dashboard."""
    return render_template("dashboard.html", api_url=API_URL, api_key=API_KEY)

# Proxy pour les requêtes API (pour éviter les problèmes CORS)
@app.route("/api/status")
def api_status():
    """Proxy pour l'endpoint /status de l'API."""
    try:
        response = requests.get(
            f"{API_URL}/status",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json())
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (status): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/trades")
def api_trades():
    """Proxy pour l'endpoint /trades de l'API."""
    try:
        limit = request.args.get("limit", default=20, type=int)
        response = requests.get(
            f"{API_URL}/trades?limit={limit}",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json())
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (trades): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/performance")
def api_performance():
    """Proxy pour l'endpoint /performance de l'API."""
    try:
        response = requests.get(
            f"{API_URL}/performance",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json())
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (performance): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/change_mode", methods=["POST"])
def api_change_mode():
    """Proxy pour l'endpoint /change_mode de l'API."""
    try:
        data = request.json
        response = requests.post(
            f"{API_URL}/change_mode",
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
            json=data,
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (change_mode): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/start_sniping", methods=["POST"])
def api_start_sniping():
    """Proxy pour l'endpoint /start_sniping de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/start_sniping",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (start_sniping): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop_sniping", methods=["POST"])
def api_stop_sniping():
    """Proxy pour l'endpoint /stop_sniping de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/stop_sniping",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (stop_sniping): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/start_arbitrage", methods=["POST"])
def api_start_arbitrage():
    """Proxy pour l'endpoint /start_arbitrage de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/start_arbitrage",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (start_arbitrage): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop_arbitrage", methods=["POST"])
def api_stop_arbitrage():
    """Proxy pour l'endpoint /stop_arbitrage de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/stop_arbitrage",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (stop_arbitrage): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/start_mev", methods=["POST"])
def api_start_mev():
    """Proxy pour l'endpoint /start_mev de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/start_mev",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (start_mev): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop_mev", methods=["POST"])
def api_stop_mev():
    """Proxy pour l'endpoint /stop_mev de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/stop_mev",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (stop_mev): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop_bot", methods=["POST"])
def api_stop_bot():
    """Proxy pour l'endpoint /stop_bot de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/stop_bot",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (stop_bot): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/start_bot", methods=["POST"])
def api_start_bot():
    """Proxy pour l'endpoint /start_bot de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/start_bot",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (start_bot): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/reset_bot", methods=["POST"])
def api_reset_bot():
    """Proxy pour l'endpoint /reset_bot de l'API."""
    try:
        response = requests.post(
            f"{API_URL}/reset_bot",
            headers={"x-api-key": API_KEY},
            timeout=API_TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête à l'API (reset_bot): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Vérifier l'état de santé du dashboard."""
    # Vérifier également la connexion à l'API
    api_health = {"status": "unknown"}
    try:
        response = requests.get(
            f"{API_URL}/health",
            timeout=API_TIMEOUT
        )
        api_health = response.json()
    except requests.RequestException as e:
        api_health = {"status": "error", "error": str(e)}
    
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time(),
        "api_health": api_health
    })

if __name__ == "__main__":
    # Configurer le serveur avec SSL si spécifié
    ssl_context = security_config.get_ssl_context()
    
    host = "127.0.0.1"
    port = int(os.getenv("GBPBOT_DASHBOARD_PORT", 5001))
    
    logger.info(f"Démarrage du dashboard web sur {host}:{port}")
    app.run(host=host, port=port, ssl_context=ssl_context, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true") 