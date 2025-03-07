#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation de l'IA pour analyser un token Solana

Ce script démontre comment utiliser le module d'intelligence artificielle
de GBPBot pour analyser un token spécifique sur Solana et obtenir des
recommandations de trading basées sur l'analyse.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, cast

# Ajout du répertoire parent au path pour permettre l'import des modules GBPBot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from gbpbot.ai import create_ai_client
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    # Import conditionnel pour éviter les erreurs si le module n'existe pas
    try:
        from gbpbot.config.config_manager import ConfigManager
        HAS_CONFIG_MANAGER = True
    except ImportError:
        HAS_CONFIG_MANAGER = False
except ImportError:
    print("❌ Erreur d'importation des modules GBPBot. Assurez-vous que GBPBot est correctement installé.")
    print("   Exécutez 'pip install -e .' depuis le répertoire racine du projet.")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AI_DEMO")

# Exemple de données de token (normalement récupérées depuis une API comme Solscan ou DexScreener)
SAMPLE_TOKEN_DATA = {
    "symbol": "BONK",
    "name": "Bonk",
    "address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "price_usd": 0.000012,
    "price_change_24h": 15.3,  # En pourcentage
    "market_cap": 734000000,
    "fully_diluted_valuation": 950000000,
    "volume_24h": 120000000,
    "volume_change_24h": 45.7,  # En pourcentage
    "liquidity_usd": 56000000,
    "holders": 235000,
    "transactions_24h": 37500,
    "twitter_followers": 450000,
    "launch_date": "2022-12-25",
    "security_score": 85,  # Score sur 100
    "contract_verified": True,
    "liquidity_locked": True,
    "tax_buy": 0,
    "tax_sell": 0
}

def load_config() -> Dict[str, Any]:
    """Charge la configuration depuis le fichier de configuration GBPBot ou utilise des valeurs par défaut."""
    config = {
        "AI_PROVIDER": "openai",
        "AI_MODEL": "gpt-3.5-turbo",
        "AI_TEMPERATURE": 0.7,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "AI_LOCAL_MODEL_PATH": ""
    }
    
    # Si le ConfigManager est disponible, essayons de l'utiliser
    if HAS_CONFIG_MANAGER:
        try:
            # Utilisation sécurisée de ConfigManager via les fonctions dict
            config_manager = ConfigManager()
            config_dict = config_manager.get_all_config() if hasattr(config_manager, 'get_all_config') else {}
            
            # Mettre à jour les valeurs si elles existent dans la configuration
            if "AI_PROVIDER" in config_dict:
                config["AI_PROVIDER"] = config_dict["AI_PROVIDER"]
            if "AI_MODEL" in config_dict:
                config["AI_MODEL"] = config_dict["AI_MODEL"]
            if "AI_TEMPERATURE" in config_dict:
                config["AI_TEMPERATURE"] = float(config_dict["AI_TEMPERATURE"])
            if "OPENAI_API_KEY" in config_dict:
                config["OPENAI_API_KEY"] = config_dict["OPENAI_API_KEY"]
            if "AI_LOCAL_MODEL_PATH" in config_dict:
                config["AI_LOCAL_MODEL_PATH"] = config_dict["AI_LOCAL_MODEL_PATH"]
                
            logger.info("Configuration chargée avec succès depuis ConfigManager")
        except Exception as e:
            logger.warning(f"Impossible de charger la configuration: {e}. Utilisation des valeurs par défaut.")
    
    return config

def get_token_data(symbol: str) -> Dict[str, Any]:
    """
    Récupère les données d'un token spécifique.
    
    Dans un cas réel, cette fonction ferait des appels API à Solscan, DexScreener, etc.
    Pour cette démo, nous utilisons des données prédéfinies.
    """
    logger.info(f"Récupération des données pour le token {symbol}...")
    # Simulons un délai réseau
    import time
    time.sleep(1)
    
    if symbol.upper() == "BONK":
        return SAMPLE_TOKEN_DATA
    else:
        # Générons des données aléatoires pour tout autre token
        import random
        return {
            "symbol": symbol.upper(),
            "name": f"{symbol.capitalize()} Token",
            "address": "Sx" + "".join(random.choices("0123456789abcdef", k=40)),
            "price_usd": random.uniform(0.00000001, 5),
            "price_change_24h": random.uniform(-30, 30),
            "market_cap": random.randint(10000, 1000000000),
            "fully_diluted_valuation": random.randint(10000, 2000000000),
            "volume_24h": random.randint(5000, 200000000),
            "volume_change_24h": random.uniform(-50, 100),
            "liquidity_usd": random.randint(1000, 100000000),
            "holders": random.randint(100, 500000),
            "transactions_24h": random.randint(100, 50000),
            "twitter_followers": random.randint(0, 1000000),
            "launch_date": f"2023-{random.randint(1, 12)}-{random.randint(1, 28)}",
            "security_score": random.randint(30, 100),
            "contract_verified": random.choice([True, True, True, False]),  # Plus probable d'être vérifié
            "liquidity_locked": random.choice([True, True, False]),  # Plus probable d'être verrouillé
            "tax_buy": random.choice([0, 0, 0, 3, 5, 10]),  # Taxes possibles
            "tax_sell": random.choice([0, 0, 0, 3, 5, 10])  # Taxes possibles
        }

def format_analysis_results(analysis_result: Dict[str, Any]) -> None:
    """Affiche les résultats d'analyse de manière formatée et colorée."""
    # ANSI colors for terminal
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}🤖 ANALYSE IA DU TOKEN: {analysis_result.get('symbol', 'N/A')}{RESET}")
    print(f"{BOLD}{'='*80}{RESET}")
    
    # Tendance
    trend = analysis_result.get('trend', 'neutre').lower()
    trend_color = GREEN if trend == 'haussière' else RED if trend == 'baissière' else YELLOW
    print(f"{BOLD}Tendance actuelle:{RESET} {trend_color}{trend}{RESET}")
    
    # Niveau de confiance
    confidence = analysis_result.get('confidence_level', 0)
    confidence_color = GREEN if confidence >= 70 else YELLOW if confidence >= 40 else RED
    print(f"{BOLD}Niveau de confiance:{RESET} {confidence_color}{confidence}%{RESET}")
    
    # Forces et faiblesses
    print(f"\n{BOLD}Forces:{RESET}")
    for strength in analysis_result.get('strengths', []):
        print(f"  {GREEN}✓{RESET} {strength}")
    
    print(f"\n{BOLD}Faiblesses:{RESET}")
    for weakness in analysis_result.get('weaknesses', []):
        print(f"  {RED}✗{RESET} {weakness}")
    
    # Opportunités
    print(f"\n{BOLD}Opportunités:{RESET}")
    for opportunity in analysis_result.get('opportunities', []):
        print(f"  {BLUE}→{RESET} {opportunity}")
    
    # Risques
    print(f"\n{BOLD}Risques:{RESET}")
    risk_level = analysis_result.get('risk_level', 'modéré').lower()
    risk_color = GREEN if risk_level == 'faible' else RED if risk_level == 'élevé' else YELLOW
    print(f"  {BOLD}Niveau de risque global:{RESET} {risk_color}{risk_level}{RESET}")
    
    for risk in analysis_result.get('risks', []):
        print(f"  {RED}!{RESET} {risk}")
    
    # Recommandations
    print(f"\n{BOLD}Recommandations:{RESET}")
    for recommendation in analysis_result.get('recommendations', []):
        print(f"  {BLUE}•{RESET} {recommendation}")
    
    # Prédiction de prix
    prediction = analysis_result.get('price_prediction', {})
    if prediction:
        direction = prediction.get('direction', 'stable')
        direction_color = GREEN if direction == 'hausse' else RED if direction == 'baisse' else YELLOW
        
        print(f"\n{BOLD}Prédiction de prix (24h):{RESET}")
        print(f"  {BOLD}Direction:{RESET} {direction_color}{direction}{RESET}")
        print(f"  {BOLD}Amplitude potentielle:{RESET} {prediction.get('amplitude', 'N/A')}%")
        print(f"  {BOLD}Facteurs clés:{RESET} {prediction.get('key_factors', 'N/A')}")
    
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}Note:{RESET} Cette analyse est générée par l'IA et ne constitue pas un conseil financier.")
    print(f"{BOLD}{'='*80}{RESET}\n")

async def analyze_token() -> None:
    """Fonction principale qui exécute l'analyse de token."""
    # Chargement de la configuration
    config = load_config()
    
    # Vérification de la clé API si OpenAI est utilisé
    if config["AI_PROVIDER"] == "openai" and not config["OPENAI_API_KEY"]:
        logger.error("Aucune clé API OpenAI trouvée. Définissez la variable d'environnement OPENAI_API_KEY ou configurez-la dans GBPBot.")
        print("\nPour exécuter cette démo avec OpenAI, vous devez définir une clé API:")
        print("1. Exportez la variable d'environnement: export OPENAI_API_KEY='votre-clé-api'")
        print("2. Ou configurez-la dans GBPBot via le menu de configuration")
        sys.exit(1)
    
    # Demander à l'utilisateur quel token analyser
    token_symbol = input("Entrez le symbole du token à analyser (ex: BONK, WIF, BOME): ").strip().upper()
    if not token_symbol:
        logger.error("Aucun symbole de token fourni.")
        return
    
    try:
        # Récupération des données du token
        token_data = get_token_data(token_symbol)
        
        logger.info(f"Création du client IA avec le fournisseur {config['AI_PROVIDER']}...")
        # Création du client IA avec les paramètres adaptés aux signatures de méthodes attendues
        ai_client = create_ai_client(
            provider=config["AI_PROVIDER"],
            openai_api_key=config["OPENAI_API_KEY"],
            model_name=config["AI_MODEL"],
            temperature=config["AI_TEMPERATURE"],
            local_model_path=config["AI_LOCAL_MODEL_PATH"]
        )
        
        if not ai_client:
            logger.error("Impossible de créer le client IA. Vérifiez votre configuration et vos dépendances.")
            return
        
        # Création de l'analyseur de marché
        logger.info("Initialisation de l'analyseur de marché...")
        market_analyzer = MarketAnalyzer(ai_client=ai_client, config=config)
        
        # Analyse du token
        logger.info(f"Analyse du token {token_symbol} en cours...")
        analysis_result_coroutine = market_analyzer.analyze_token(token_data)
        
        # Pour exécuter la coroutine, nous avons besoin d'un event loop
        import asyncio
        analysis_result = await analysis_result_coroutine
        
        # Affichage des résultats
        format_analysis_results(analysis_result)
        
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors de l'analyse: {e}")
        import traceback
        logger.debug(traceback.format_exc())

async def main() -> None:
    """Point d'entrée principal du script, gère l'exécution asynchrone."""
    print(f"{'='*80}")
    print(f"🤖 DÉMO D'ANALYSE DE TOKEN AVEC L'IA DE GBPBOT")
    print(f"{'='*80}")
    print("Cette démo montre comment utiliser l'IA intégrée dans GBPBot pour analyser")
    print("un token spécifique sur Solana et obtenir des recommandations de trading.")
    print(f"{'='*80}\n")
    
    await analyze_token()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 