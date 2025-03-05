#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from dotenv import load_dotenv
from security_config import SecurityConfig, require_auth
from simulation_data import simulation
import threading
import time
import json
import traceback
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from loguru import logger
import argparse

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
log_level = os.getenv("GBPBOT_LOG_LEVEL", "INFO")
logger.remove()
logger.add(sys.stderr, level=log_level)
logger.add("gbpbot_api.log", rotation="10 MB", level=log_level)

# Charger la configuration de sécurité
security_config = SecurityConfig()

# Créer l'application Flask
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configurer le limiteur de requêtes
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[security_config.rate_limit_default],
    storage_uri="memory://"
)

# Thread pour simuler les données en arrière-plan
def simulation_thread():
    """Thread pour simuler les données en arrière-plan."""
    logger.info("Démarrage du thread de simulation...")
    try:
        while True:
            simulation.simulate_tick()
            time.sleep(1)  # Simuler toutes les secondes
    except Exception as e:
        logger.error(f"Erreur dans le thread de simulation: {str(e)}")
        logger.error(traceback.format_exc())

# Démarrer le thread de simulation
simulation_thread_instance = threading.Thread(target=simulation_thread, daemon=True)
simulation_thread_instance.start()

# Middleware pour vérifier l'authentification
@app.before_request
def check_auth():
    """Middleware pour vérifier l'authentification."""
    # Ignorer les requêtes OPTIONS (CORS pre-flight)
    if request.method == 'OPTIONS':
        return None
        
    # Ignorer la vérification pour les endpoints publics
    if request.path == '/health':
        return None
        
    # Vérifier l'IP
    client_ip = request.remote_addr
    if security_config.enable_ip_check and not security_config.is_ip_allowed(client_ip):
        logger.warning(f"Tentative d'accès depuis une IP non autorisée: {client_ip}")
        return jsonify({"error": "Accès non autorisé"}), 403
    
    # Vérifier si l'IP est verrouillée en raison de trop nombreuses tentatives échouées
    if not security_config.check_failed_attempts(client_ip):
        logger.warning(f"IP verrouillée en raison de trop nombreuses tentatives échouées: {client_ip}")
        return jsonify({"error": "Trop de tentatives échouées. Réessayez plus tard."}), 429
    
    # Vérifier la clé API
    api_key = request.headers.get('x-api-key')
    if not api_key or api_key != security_config.api_key:
        security_config.record_failed_attempt(client_ip)
        logger.warning(f"Tentative d'accès avec une clé API invalide depuis: {client_ip}")
        return jsonify({"error": "Authentification requise"}), 401
    
    # Réinitialiser le compteur de tentatives échouées en cas de succès
    security_config.reset_failed_attempts(client_ip)

# Middleware pour journaliser les requêtes
@app.after_request
def log_request(response):
    """Middleware pour journaliser les requêtes."""
    if security_config.log_requests:
        logger.info(f"{request.method} {request.path} - IP: {request.remote_addr} - Status: {response.status_code}")
    return response

# Gestionnaire d'erreurs global
@app.errorhandler(Exception)
def handle_exception(e):
    """Gestionnaire d'erreurs global."""
    logger.error(f"Erreur non gérée: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({"error": "Une erreur interne s'est produite"}), 500

# Routes API
@app.route("/status", methods=["GET"])
@limiter.limit("30 per minute")
def get_status():
    """Obtenir le statut du bot."""
    return jsonify(simulation.get_status())

@app.route("/trades", methods=["GET"])
def get_trades():
    """Obtenir la liste des trades."""
    return jsonify(simulation.get_trades())

@app.route("/performance", methods=["GET"])
def get_performance():
    """Obtenir les performances du bot."""
    return jsonify(simulation.get_performance())

@app.route("/change_mode", methods=["POST"])
def change_mode():
    """Changer le mode du bot (simulation/live)."""
    try:
        data = request.json
        if not data or "mode" not in data:
            return jsonify({"error": "Le mode doit être spécifié"}), 400
            
        mode = data["mode"]
        if mode not in ["simulation", "live"]:
            return jsonify({"error": "Mode invalide. Utilisez 'simulation' ou 'live'"}), 400
            
        # Changer le mode
        simulation.set_mode(mode)
        
        return jsonify({"success": True, "message": f"Mode changé en {mode}"})
    except Exception as e:
        logger.error(f"Erreur lors du changement de mode: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/start_sniping", methods=["POST"])
def start_sniping():
    """Démarrer le sniping."""
    try:
        data = request.json or {}
        simulation_mode = data.get("simulation_mode", True)
        
        # Démarrer le sniping
        simulation.start_sniping(simulation_mode)
        
        return jsonify({"success": True, "message": "Sniping démarré"})
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du sniping: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/stop_sniping", methods=["POST"])
def stop_sniping():
    """Arrêter le sniping."""
    try:
        # Arrêter le sniping
        simulation.stop_sniping()
        
        return jsonify({"success": True, "message": "Sniping arrêté"})
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du sniping: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/start_arbitrage", methods=["POST"])
def start_arbitrage():
    """Démarrer l'arbitrage."""
    try:
        data = request.json or {}
        simulation_mode = data.get("simulation_mode", True)
        
        # Démarrer l'arbitrage
        simulation.start_arbitrage(simulation_mode)
        
        return jsonify({"success": True, "message": "Arbitrage démarré"})
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'arbitrage: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/stop_arbitrage", methods=["POST"])
def stop_arbitrage():
    """Arrêter l'arbitrage."""
    try:
        # Arrêter l'arbitrage
        simulation.stop_arbitrage()
        
        return jsonify({"success": True, "message": "Arbitrage arrêté"})
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt de l'arbitrage: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/start_mev", methods=["POST"])
def start_mev():
    """Démarrer le MEV."""
    try:
        data = request.json or {}
        simulation_mode = data.get("simulation_mode", True)
        
        # Démarrer le MEV
        simulation.start_mev(simulation_mode)
        
        return jsonify({"success": True, "message": "MEV démarré"})
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du MEV: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/stop_mev", methods=["POST"])
def stop_mev():
    """Arrêter le MEV."""
    try:
        # Arrêter le MEV
        simulation.stop_mev()
        
        return jsonify({"success": True, "message": "MEV arrêté"})
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du MEV: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/stop_bot", methods=["POST"])
def stop_bot():
    """Arrêter le bot."""
    try:
        # Arrêter le bot
        simulation.stop_bot()
        
        return jsonify({"success": True, "message": "Bot arrêté"})
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du bot: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/start_bot", methods=["POST"])
def start_bot():
    """Démarrer le bot."""
    try:
        data = request.json or {}
        simulation_mode = data.get("simulation_mode", True)
        
        # Démarrer le bot
        simulation.start_bot(simulation_mode)
        
        return jsonify({"success": True, "message": "Bot démarré"})
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du bot: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/reset_bot", methods=["POST"])
def reset_bot():
    """Réinitialiser le bot."""
    try:
        # Réinitialiser le bot
        simulation.reset_bot()
        
        return jsonify({"success": True, "message": "Bot réinitialisé"})
    except Exception as e:
        logger.error(f"Erreur lors de la réinitialisation du bot: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Vérifier l'état de santé de l'API."""
    return jsonify({
        "status": "ok",
        "timestamp": time.time(),
        "version": "1.0.0"
    })

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Serveur API GBPBot")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute")
    parser.add_argument("--port", type=int, default=5000, help="Port d'écoute")
    parser.add_argument("--debug", action="store_true", help="Mode debug")
    args = parser.parse_args()
    
    # Afficher les informations de démarrage
    logger.info(f"Démarrage du serveur API GBPBot sur {args.host}:{args.port}")
    logger.info(f"Mode debug: {'Activé' if args.debug else 'Désactivé'}")
    logger.info(f"HTTPS: {'Activé' if security_config.use_https else 'Désactivé'}")
    
    # Démarrer le serveur
    if security_config.use_https:
        ssl_context = security_config.get_ssl_context()
        app.run(host=args.host, port=args.port, debug=args.debug, ssl_context=ssl_context)
    else:
        app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 