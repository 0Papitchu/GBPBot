"""
Commandes CLI pour l'automatisation intelligente du GBPBot
========================================================

Ce module fournit des commandes pour configurer, activer et surveiller
l'automatisation intelligente du GBPBot, qui permet d'adapter automatiquement
les stratégies de trading en fonction des conditions de marché.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# Configuration du logger
logger = logging.getLogger("gbpbot.cli.commands.auto_optimization")

def display_auto_optimization_menu(bot_context: Dict[str, Any]) -> None:
    """
    Affiche le menu d'automatisation intelligente et gère les interactions utilisateur.
    
    Args:
        bot_context: Contexte du bot contenant la configuration et les modules actifs
    """
    while True:
        print("\n" + "="*60)
        print(f"{'Menu d'Automatisation Intelligente':^60}")
        print("="*60)
        
        # Récupérer l'état actuel de l'automatisation
        auto_optimization_enabled = bot_context.get("config", {}).get("auto_optimization", {}).get("enabled", False)
        status_text = "✅ ACTIVÉE" if auto_optimization_enabled else "❌ DÉSACTIVÉE"
        
        print(f"\nAutomatisation intelligente: {status_text}\n")
        
        # Menu principal
        print("Options:")
        print("1. Activer/Désactiver l'automatisation")
        print("2. Configurer les paramètres d'automatisation")
        print("3. Afficher l'état actuel")
        print("4. Consulter les recommandations automatiques")
        print("5. Appliquer les paramètres recommandés")
        print("6. Retour au menu principal")
        
        choice = input("\nChoisissez une option (1-6): ")
        
        if choice == '1':
            toggle_auto_optimization(bot_context)
        elif choice == '2':
            configure_auto_optimization(bot_context)
        elif choice == '3':
            display_auto_optimization_status(bot_context)
        elif choice == '4':
            display_recommendations(bot_context)
        elif choice == '5':
            apply_recommended_parameters(bot_context)
        elif choice == '6':
            break
        else:
            print("Option invalide, veuillez réessayer.")

def toggle_auto_optimization(bot_context: Dict[str, Any]) -> None:
    """
    Active ou désactive l'automatisation intelligente.
    
    Args:
        bot_context: Contexte du bot contenant la configuration et les modules actifs
    """
    # Récupérer l'état actuel
    config = bot_context.get("config", {})
    auto_config = config.get("auto_optimization", {})
    currently_enabled = auto_config.get("enabled", False)
    
    # Inverser l'état
    new_state = not currently_enabled
    
    # Afficher la confirmation
    print(f"\n{'Activation' if new_state else 'Désactivation'} de l'automatisation intelligente...")
    
    if new_state:
        # Vérifier si les dépendances sont satisfaites
        try:
            from gbpbot.core.auto_optimization import initialize_auto_optimization
            
            # Mettre à jour la configuration
            if "auto_optimization" not in config:
                config["auto_optimization"] = {}
            config["auto_optimization"]["enabled"] = True
            
            # Initialiser l'automatisation
            success = initialize_auto_optimization(config)
            
            if success:
                print("✅ Automatisation intelligente activée avec succès!")
                bot_context["config"] = config
                
                # Sauvegarder la configuration
                if "save_config" in bot_context:
                    bot_context["save_config"](config)
            else:
                print("❌ Échec de l'activation. Vérifiez les logs pour plus de détails.")
        except ImportError:
            print("❌ Module d'automatisation intelligente non disponible.")
            print("   Installez les dépendances requises et réessayez.")
    else:
        # Désactiver l'automatisation
        try:
            from gbpbot.core.auto_optimization import shutdown
            
            # Arrêter l'automatisation
            shutdown()
            
            # Mettre à jour la configuration
            if "auto_optimization" not in config:
                config["auto_optimization"] = {}
            config["auto_optimization"]["enabled"] = False
            
            print("✅ Automatisation intelligente désactivée avec succès!")
            bot_context["config"] = config
            
            # Sauvegarder la configuration
            if "save_config" in bot_context:
                bot_context["save_config"](config)
        except ImportError:
            print("❌ Module d'automatisation intelligente non disponible.")

def configure_auto_optimization(bot_context: Dict[str, Any]) -> None:
    """
    Configure les paramètres de l'automatisation intelligente.
    
    Args:
        bot_context: Contexte du bot contenant la configuration et les modules actifs
    """
    config = bot_context.get("config", {})
    auto_config = config.get("auto_optimization", {})
    
    print("\n" + "="*60)
    print(f"{'Configuration de l'Automatisation Intelligente':^60}")
    print("="*60 + "\n")
    
    # Liste des paramètres configurables
    params = [
        {
            "name": "enable_parameter_adjustment",
            "display": "Ajustement auto. des paramètres",
            "type": "bool",
            "default": True,
            "help": "Ajuste automatiquement les paramètres des stratégies"
        },
        {
            "name": "enable_market_detection",
            "display": "Détection des conditions de marché",
            "type": "bool",
            "default": True,
            "help": "Détecte automatiquement les conditions de marché"
        },
        {
            "name": "enable_capital_allocation",
            "display": "Allocation dynamique du capital",
            "type": "bool",
            "default": True,
            "help": "Répartit dynamiquement le capital entre les stratégies"
        },
        {
            "name": "enable_error_recovery",
            "display": "Récupération automatique des erreurs",
            "type": "bool",
            "default": True,
            "help": "Tente de récupérer automatiquement après une erreur"
        },
        {
            "name": "parameter_adjustment_interval",
            "display": "Intervalle d'ajustement des paramètres (s)",
            "type": "int",
            "default": 300,
            "help": "Temps en secondes entre les ajustements de paramètres"
        },
        {
            "name": "market_detection_interval",
            "display": "Intervalle de détection du marché (s)",
            "type": "int",
            "default": 120,
            "help": "Temps en secondes entre les détections de conditions de marché"
        },
        {
            "name": "capital_allocation_interval",
            "display": "Intervalle d'allocation du capital (s)",
            "type": "int",
            "default": 600,
            "help": "Temps en secondes entre les allocations de capital"
        },
        {
            "name": "volatility_threshold",
            "display": "Seuil de volatilité",
            "type": "float",
            "default": 0.05,
            "help": "Seuil de volatilité pour les décisions d'allocation"
        },
        {
            "name": "max_capital_per_strategy",
            "display": "Capital max par stratégie",
            "type": "float",
            "default": 0.5,
            "help": "Proportion maximale du capital par stratégie (0.0-1.0)"
        },
        {
            "name": "min_capital_per_strategy",
            "display": "Capital min par stratégie",
            "type": "float",
            "default": 0.05,
            "help": "Proportion minimale du capital par stratégie (0.0-1.0)"
        }
    ]
    
    # Afficher et modifier les paramètres
    for i, param in enumerate(params):
        current_value = auto_config.get(param["name"], param["default"])
        print(f"{i+1}. {param['display']}: {current_value}")
        print(f"   {param['help']}")
    
    print("\n0. Retour")
    
    while True:
        choice = input("\nChoisissez un paramètre à modifier (0 pour retour): ")
        
        try:
            choice_num = int(choice)
            if choice_num == 0:
                break
            elif 1 <= choice_num <= len(params):
                param = params[choice_num - 1]
                current_value = auto_config.get(param["name"], param["default"])
                
                # Demander la nouvelle valeur
                if param["type"] == "bool":
                    new_value_str = input(f"Nouvelle valeur pour {param['display']} (true/false) [{current_value}]: ")
                    if new_value_str.strip().lower() in ["true", "t", "1", "yes", "y"]:
                        new_value = True
                    elif new_value_str.strip().lower() in ["false", "f", "0", "no", "n"]:
                        new_value = False
                    else:
                        new_value = current_value
                elif param["type"] == "int":
                    new_value_str = input(f"Nouvelle valeur pour {param['display']} [{current_value}]: ")
                    try:
                        new_value = int(new_value_str) if new_value_str.strip() else current_value
                    except ValueError:
                        print("Valeur invalide, conservation de l'ancienne valeur.")
                        new_value = current_value
                elif param["type"] == "float":
                    new_value_str = input(f"Nouvelle valeur pour {param['display']} [{current_value}]: ")
                    try:
                        new_value = float(new_value_str) if new_value_str.strip() else current_value
                    except ValueError:
                        print("Valeur invalide, conservation de l'ancienne valeur.")
                        new_value = current_value
                else:
                    new_value_str = input(f"Nouvelle valeur pour {param['display']} [{current_value}]: ")
                    new_value = new_value_str if new_value_str.strip() else current_value
                
                # Mettre à jour la configuration
                if "auto_optimization" not in config:
                    config["auto_optimization"] = {}
                config["auto_optimization"][param["name"]] = new_value
                
                print(f"✅ Paramètre {param['display']} mis à jour: {new_value}")
                
                # Réafficher le menu
                print("\n" + "="*60)
                print(f"{'Configuration de l'Automatisation Intelligente':^60}")
                print("="*60 + "\n")
                
                for i, param in enumerate(params):
                    current_value = config.get("auto_optimization", {}).get(param["name"], param["default"])
                    print(f"{i+1}. {param['display']}: {current_value}")
                    print(f"   {param['help']}")
                
                print("\n0. Retour")
            else:
                print("Option invalide, veuillez réessayer.")
        except ValueError:
            print("Option invalide, veuillez réessayer.")
    
    # Sauvegarder la configuration
    bot_context["config"] = config
    if "save_config" in bot_context:
        bot_context["save_config"](config)
        print("✅ Configuration sauvegardée avec succès!")
    
    # Redémarrer l'automatisation si elle est active
    if config.get("auto_optimization", {}).get("enabled", False):
        try:
            from gbpbot.core.auto_optimization import shutdown, initialize_auto_optimization
            
            # Redémarrer l'automatisation
            shutdown()
            success = initialize_auto_optimization(config)
            
            if success:
                print("✅ Automatisation intelligente redémarrée avec succès!")
            else:
                print("❌ Échec du redémarrage. Vérifiez les logs pour plus de détails.")
        except ImportError:
            print("⚠️ Module d'automatisation intelligente non disponible.")

def display_auto_optimization_status(bot_context: Dict[str, Any]) -> None:
    """
    Affiche l'état actuel de l'automatisation intelligente.
    
    Args:
        bot_context: Contexte du bot contenant la configuration et les modules actifs
    """
    print("\n" + "="*60)
    print(f"{'État de l'Automatisation Intelligente':^60}")
    print("="*60 + "\n")
    
    # Vérifier si l'automatisation est activée
    auto_optimization_enabled = bot_context.get("config", {}).get("auto_optimization", {}).get("enabled", False)
    
    if not auto_optimization_enabled:
        print("❌ L'automatisation intelligente est actuellement désactivée.")
        print("   Activez-la pour voir son état.")
        input("\nAppuyez sur Entrée pour continuer...")
        return
    
    try:
        # Importer le module d'automatisation
        from gbpbot.core.auto_optimization import get_optimization_status, is_initialized
        
        if not is_initialized():
            print("❌ L'automatisation intelligente n'est pas initialisée.")
            print("   Activez-la pour voir son état.")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        # Récupérer l'état actuel
        status = get_optimization_status()
        
        # Formater les dates pour l'affichage
        last_parameter_adjustment = datetime.fromisoformat(status.get("last_parameter_adjustment", datetime.now().isoformat()))
        last_market_detection = datetime.fromisoformat(status.get("last_market_detection", datetime.now().isoformat()))
        last_capital_allocation = datetime.fromisoformat(status.get("last_capital_allocation", datetime.now().isoformat()))
        
        now = datetime.now()
        
        # Afficher l'état
        print(f"État actuel    : {'✅ En cours' if status.get('running', False) else '❌ Arrêté'}")
        print(f"Dernière optimisation: {(now - last_parameter_adjustment).total_seconds():.0f} secondes")
        
        # Afficher les conditions de marché
        print("\n📊 Conditions de marché détectées:")
        market_conditions = status.get("market_conditions", {})
        for key, value in market_conditions.items():
            print(f"  {key.capitalize():15}: {value}")
        
        # Afficher les paramètres des stratégies
        print("\n⚙️ Paramètres des stratégies:")
        strategy_parameters = status.get("strategy_parameters", {})
        for strategy, params in strategy_parameters.items():
            print(f"  {strategy}:")
            for param_name, param_value in params.items():
                print(f"    {param_name:20}: {param_value}")
        
        # Afficher les statistiques d'optimisation
        print("\n📈 Statistiques d'optimisation:")
        stats = status.get("optimization_stats", {})
        for stat_name, stat_value in stats.items():
            print(f"  {stat_name:20}: {stat_value}")
        
        # Afficher les dernières actions de récupération
        recovery_actions = status.get("recovery_actions", [])
        if recovery_actions:
            print("\n🛠️ Dernières actions de récupération:")
            for action in recovery_actions:
                timestamp = datetime.fromisoformat(action.get("timestamp", now.isoformat()))
                time_ago = (now - timestamp).total_seconds()
                print(f"  {action.get('action'):15} pour {action.get('error_type'):15} il y a {time_ago:.0f}s")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    except ImportError:
        print("❌ Module d'automatisation intelligente non disponible.")
        input("\nAppuyez sur Entrée pour continuer...")

def display_recommendations(bot_context: Dict[str, Any]) -> None:
    """
    Affiche les recommandations générées par l'automatisation intelligente.
    
    Args:
        bot_context: Contexte du bot contenant la configuration et les modules actifs
    """
    print("\n" + "="*60)
    print(f"{'Recommandations Automatiques':^60}")
    print("="*60 + "\n")
    
    # Vérifier si l'automatisation est activée
    auto_optimization_enabled = bot_context.get("config", {}).get("auto_optimization", {}).get("enabled", False)
    
    if not auto_optimization_enabled:
        print("❌ L'automatisation intelligente est actuellement désactivée.")
        print("   Activez-la pour voir les recommandations.")
        input("\nAppuyez sur Entrée pour continuer...")
        return
    
    try:
        # Importer le module d'automatisation
        from gbpbot.core.auto_optimization import get_optimization_status, is_initialized
        
        if not is_initialized():
            print("❌ L'automatisation intelligente n'est pas initialisée.")
            print("   Activez-la pour voir les recommandations.")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        # Récupérer l'état actuel
        status = get_optimization_status()
        
        # Analyser les conditions de marché pour générer des recommandations
        market_conditions = status.get("market_conditions", {})
        volatility = market_conditions.get("volatility", "normal")
        trend = market_conditions.get("trend", "neutral")
        opportunity_level = market_conditions.get("opportunity_level", "medium")
        risk_level = market_conditions.get("risk_level", "medium")
        
        # Générer des recommandations en fonction des conditions
        recommendations = []
        
        if volatility == "high" or volatility == "extreme":
            recommendations.append("Augmentez la part d'arbitrage (conditions de forte volatilité)")
            recommendations.append("Augmentez le seuil de profit minimum pour les transactions")
            recommendations.append("Réduisez la taille des transactions")
            recommendations.append("Augmentez la priorité des transactions (gas price)")
        
        if trend == "bullish" and opportunity_level == "high":
            recommendations.append("Augmentez la part de sniping (marché haussier avec opportunités)")
            recommendations.append("Augmentez la taille maximale d'investissement par token")
            recommendations.append("Augmentez le nombre de tokens suivis simultanément")
        
        if trend == "bearish":
            recommendations.append("Réduisez la part de sniping (marché baissier)")
            recommendations.append("Augmentez les exigences de confiance pour les nouveaux tokens")
            recommendations.append("Réduisez la taille maximale d'investissement par token")
            recommendations.append("Réduisez le nombre de tokens par jour")
        
        if risk_level == "high":
            recommendations.append("Augmentez les seuils de sécurité pour toutes les stratégies")
            recommendations.append("Réduisez l'exposition globale au marché")
            recommendations.append("Augmentez la fréquence de surveillance des positions")
        
        # Afficher les recommandations
        if recommendations:
            print("📋 Recommandations basées sur les conditions actuelles:\n")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("Aucune recommandation spécifique pour les conditions actuelles.")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    except ImportError:
        print("❌ Module d'automatisation intelligente non disponible.")
        input("\nAppuyez sur Entrée pour continuer...")

def apply_recommended_parameters(bot_context: Dict[str, Any]) -> None:
    """
    Applique les paramètres recommandés par l'automatisation intelligente.
    
    Args:
        bot_context: Contexte du bot contenant la configuration et les modules actifs
    """
    print("\n" + "="*60)
    print(f"{'Application des Paramètres Recommandés':^60}")
    print("="*60 + "\n")
    
    # Vérifier si l'automatisation est activée
    auto_optimization_enabled = bot_context.get("config", {}).get("auto_optimization", {}).get("enabled", False)
    
    if not auto_optimization_enabled:
        print("❌ L'automatisation intelligente est actuellement désactivée.")
        print("   Activez-la pour appliquer les recommandations.")
        input("\nAppuyez sur Entrée pour continuer...")
        return
    
    try:
        # Importer le module d'automatisation
        from gbpbot.core.auto_optimization import get_optimization_status, is_initialized
        
        if not is_initialized():
            print("❌ L'automatisation intelligente n'est pas initialisée.")
            print("   Activez-la pour appliquer les recommandations.")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        # Récupérer l'état actuel
        status = get_optimization_status()
        
        # Récupérer les paramètres recommandés
        strategy_parameters = status.get("strategy_parameters", {})
        
        if not strategy_parameters:
            print("❌ Aucun paramètre recommandé disponible.")
            print("   Attendez que l'automatisation génère des recommandations.")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        # Afficher les paramètres recommandés
        print("📋 Paramètres recommandés:\n")
        for strategy, params in strategy_parameters.items():
            print(f"Stratégie: {strategy}")
            for param_name, param_value in params.items():
                print(f"  {param_name:20}: {param_value}")
        
        # Demander confirmation
        choice = input("\nAppliquer ces paramètres aux stratégies actives? (o/n): ")
        
        if choice.lower() in ["o", "oui", "y", "yes"]:
            # Appliquer les paramètres aux stratégies actives
            modules = bot_context.get("modules", {})
            
            for strategy, params in strategy_parameters.items():
                if strategy == "arbitrage" and "arbitrage_strategy" in modules:
                    arbitrage_strategy = modules["arbitrage_strategy"]
                    if hasattr(arbitrage_strategy, "update_parameters"):
                        arbitrage_strategy.update_parameters(params)
                        print(f"✅ Paramètres appliqués à la stratégie d'arbitrage")
                
                if strategy == "sniping" and "sniper_strategy" in modules:
                    sniper_strategy = modules["sniper_strategy"]
                    if hasattr(sniper_strategy, "update_parameters"):
                        sniper_strategy.update_parameters(params)
                        print(f"✅ Paramètres appliqués à la stratégie de sniping")
            
            print("\n✅ Paramètres recommandés appliqués avec succès!")
        else:
            print("\nApplication annulée.")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    except ImportError:
        print("❌ Module d'automatisation intelligente non disponible.")
        input("\nAppuyez sur Entrée pour continuer...") 