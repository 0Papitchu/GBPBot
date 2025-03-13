#!/usr/bin/env python3
"""
Interface en ligne de commande pour le système d'apprentissage continu - GBPBot

Ce module fournit une interface conviviale en ligne de commande pour
interagir avec le système d'apprentissage continu du GBPBot.
"""

import os
import sys
import time
import asyncio
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import colorama pour des couleurs dans le terminal
try:
    from colorama import init, Fore, Style
    init()  # Initialiser colorama
    HAS_COLORS = True
except ImportError:
    # Fallback si colorama n'est pas disponible
    class DummyFore:
        GREEN = ""
        RED = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        RESET = ""
    
    class DummyStyle:
        BRIGHT = ""
        RESET_ALL = ""
    
    Fore = DummyFore()
    Style = DummyStyle()
    HAS_COLORS = False

# Import locaux
from gbpbot.utils.logger import setup_logger
from gbpbot.ai.continuous_learning import get_continuous_learning, TradeRecord
from gbpbot.ai.learning_analyzer import get_learning_analyzer
from gbpbot.ai.learning_integration import get_learning_integration

# Configuration du logger
import logging
logger = setup_logger("learning_cli", logging.INFO)

def print_header(text):
    """Affiche un en-tête stylisé."""
    width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    print("\n" + "=" * width)
    print(f"{Fore.CYAN}{Style.BRIGHT}{text.center(width)}{Style.RESET_ALL}")
    print("=" * width + "\n")

def print_section(text):
    """Affiche un titre de section."""
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}>> {text}{Style.RESET_ALL}")

def print_success(text):
    """Affiche un message de succès."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_error(text):
    """Affiche un message d'erreur."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_info(text):
    """Affiche un message d'information."""
    print(f"{Fore.BLUE}ℹ {text}{Style.RESET_ALL}")

def print_warning(text):
    """Affiche un avertissement."""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

def print_metric(label, value, positive_is_good=True):
    """Affiche une métrique avec sa valeur, colorée selon sa positivité."""
    if isinstance(value, float):
        formatted_value = f"{value:.2f}"
    else:
        formatted_value = str(value)
    
    if isinstance(value, (int, float)) and value != 0:
        if positive_is_good:
            color = Fore.GREEN if value > 0 else Fore.RED
        else:
            color = Fore.RED if value > 0 else Fore.GREEN
    else:
        color = Fore.BLUE
    
    print(f"  {label}: {color}{formatted_value}{Style.RESET_ALL}")

def format_timestamp(timestamp):
    """Convertit un timestamp en date/heure lisible."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def clear_screen():
    """Efface l'écran du terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

class LearningCLI:
    """Interface en ligne de commande pour le système d'apprentissage continu."""
    
    def __init__(self):
        """Initialise l'interface CLI avec les modules d'apprentissage."""
        self.cl = get_continuous_learning()
        self.analyzer = get_learning_analyzer()
        self.integration = get_learning_integration()
    
    def show_main_menu(self):
        """Affiche le menu principal et gère les choix utilisateur."""
        while True:
            clear_screen()
            print_header("Système d'Apprentissage Continu - GBPBot")
            
            print("1. Afficher le résumé des performances")
            print("2. Consulter l'historique des trades")
            print("3. Analyser les performances par token")
            print("4. Voir les recommandations actuelles")
            print("5. Appliquer les recommandations aux modules")
            print("6. Paramètres du système d'apprentissage")
            print("7. Retour au menu principal")
            
            choice = input("\nEntrez votre choix (1-7): ")
            
            if choice == '1':
                self.show_performance_summary()
            elif choice == '2':
                self.show_trade_history()
            elif choice == '3':
                self.show_token_analysis()
            elif choice == '4':
                self.show_recommendations()
            elif choice == '5':
                self.apply_recommendations()
            elif choice == '6':
                self.configure_learning_system()
            elif choice == '7':
                print_info("Retour au menu principal...")
                break
            else:
                print_error("Choix invalide. Veuillez réessayer.")
            
            input("\nAppuyez sur Entrée pour continuer...")
    
    def show_performance_summary(self):
        """Affiche un résumé des performances globales."""
        clear_screen()
        print_header("Résumé des Performances")
        
        summary = self.integration.get_performance_summary()
        overall = summary['overall']
        
        print_section("Statistiques Globales")
        print_metric("Total des trades", overall['total_trades'])
        print_metric("Profit total", overall['total_profit'])
        print_metric("Profit moyen par trade", overall['avg_profit'])
        print_metric("Taux de réussite", f"{overall['success_rate'] * 100:.1f}%")
        
        if summary['best_performers']:
            print_section("Meilleures Paires")
            for pair in summary['best_performers']:
                print(f"  {Fore.GREEN}{pair['symbol']}{Style.RESET_ALL}:")
                print(f"    Win Rate: {pair['win_rate'] * 100:.1f}%")
                print(f"    Profit Moyen: {pair['avg_profit']:.2f}")
                print(f"    Profit Total: {pair['total_profit']:.2f}")
        
        if summary['worst_performers']:
            print_section("Paires les Moins Performantes")
            for pair in summary['worst_performers']:
                print(f"  {Fore.RED}{pair['symbol']}{Style.RESET_ALL}:")
                print(f"    Win Rate: {pair['win_rate'] * 100:.1f}%")
                print(f"    Profit Moyen: {pair['avg_profit']:.2f}")
                print(f"    Profit Total: {pair['total_profit']:.2f}")
    
    def show_trade_history(self):
        """Affiche l'historique des trades."""
        clear_screen()
        print_header("Historique des Trades")
        
        trades = self.cl.get_trade_history()
        
        if not trades:
            print_warning("Aucun trade enregistré.")
            return
        
        # Calculer les statistiques globales
        total_profit = sum(trade.profit for trade in trades)
        winners = sum(1 for trade in trades if trade.profit > 0)
        losers = sum(1 for trade in trades if trade.profit <= 0)
        
        print_section("Statistiques")
        print_metric("Nombre total de trades", len(trades))
        print_metric("Trades gagnants", winners)
        print_metric("Trades perdants", losers)
        print_metric("Profit/perte total(e)", total_profit)
        
        # Demander à l'utilisateur le nombre de trades à afficher
        try:
            count = int(input("\nNombre de trades à afficher (0 pour tous): "))
            if count < 0:
                count = 10  # Valeur par défaut
        except ValueError:
            count = 10
        
        trades_to_show = trades if count == 0 else trades[-count:]
        
        print_section(f"{'Tous les trades' if count == 0 else f'Derniers {len(trades_to_show)} trades'}")
        
        # En-tête du tableau
        print(f"{'ID':<6} {'Token':<10} {'Type':<6} {'Quantité':<10} {'Prix':<12} {'Profit':<10} {'Date/Heure':<20}")
        print("-" * 80)
        
        # Contenu du tableau
        for trade in trades_to_show:
            profit_color = Fore.GREEN if trade.profit > 0 else Fore.RED if trade.profit < 0 else Fore.BLUE
            
            print(f"{trade.trade_id:<6} {trade.symbol:<10} {trade.trade_type:<6} "
                  f"{trade.quantity:<10.2f} {trade.price:<12.6f} "
                  f"{profit_color}{trade.profit:<10.2f}{Style.RESET_ALL} "
                  f"{format_timestamp(trade.timestamp):<20}")
    
    def show_token_analysis(self):
        """Affiche l'analyse détaillée des performances par token."""
        clear_screen()
        print_header("Analyse des Performances par Token")
        
        token_stats = self.analyzer.analyze_token_performance()
        
        if not token_stats:
            print_warning("Pas assez de données pour analyser les performances par token.")
            return
        
        print_section("Performance des Tokens (triés par score global)")
        
        # En-tête du tableau
        print(f"{'Token':<10} {'Trades':<8} {'Win Rate':<10} {'Profit Moy':<12} {'Total':<10} {'Volatilité':<10} {'Score':<10}")
        print("-" * 80)
        
        # Contenu du tableau
        for token, stats in token_stats.items():
            profit_color = Fore.GREEN if stats['avg_profit'] > 0 else Fore.RED
            win_color = Fore.GREEN if stats['win_rate'] > 0.5 else Fore.YELLOW if stats['win_rate'] >= 0.3 else Fore.RED
            
            print(f"{token:<10} {stats['total_trades']:<8} "
                  f"{win_color}{stats['win_rate']*100:<8.1f}%{Style.RESET_ALL} "
                  f"{profit_color}{stats['avg_profit']:<10.2f}{Style.RESET_ALL} "
                  f"{stats['total_profit']:<10.2f} {stats['volatility']:<10.2f} "
                  f"{stats['score']:<10.2f}")
        
        print_section("Analyse des Patterns Temporels")
        time_patterns = self.analyzer.analyze_time_patterns()
        
        if time_patterns and 'hourly' in time_patterns and time_patterns['hourly']:
            # Trouver les meilleures et pires heures
            best_hour = max(time_patterns['hourly'].items(), key=lambda x: x[1]['avg_profit'])
            worst_hour = min(time_patterns['hourly'].items(), key=lambda x: x[1]['avg_profit'])
            
            print(f"Meilleure heure de trading: {Fore.GREEN}{best_hour[0]}h{Style.RESET_ALL} "
                  f"(Profit moyen: {best_hour[1]['avg_profit']:.2f}, "
                  f"Win rate: {best_hour[1]['win_rate']*100:.1f}%)")
            
            print(f"Pire heure de trading: {Fore.RED}{worst_hour[0]}h{Style.RESET_ALL} "
                  f"(Profit moyen: {worst_hour[1]['avg_profit']:.2f}, "
                  f"Win rate: {worst_hour[1]['win_rate']*100:.1f}%)")
        
        if time_patterns and 'daily' in time_patterns and time_patterns['daily']:
            # Trouver les meilleurs et pires jours
            best_day = max(time_patterns['daily'].items(), key=lambda x: x[1]['avg_profit'])
            worst_day = min(time_patterns['daily'].items(), key=lambda x: x[1]['avg_profit'])
            
            print(f"Meilleur jour de trading: {Fore.GREEN}{best_day[0]}{Style.RESET_ALL} "
                  f"(Profit moyen: {best_day[1]['avg_profit']:.2f}, "
                  f"Win rate: {best_day[1]['win_rate']*100:.1f}%)")
            
            print(f"Pire jour de trading: {Fore.RED}{worst_day[0]}{Style.RESET_ALL} "
                  f"(Profit moyen: {worst_day[1]['avg_profit']:.2f}, "
                  f"Win rate: {worst_day[1]['win_rate']*100:.1f}%)")
    
    def show_recommendations(self):
        """Affiche les recommandations actuelles basées sur l'analyse."""
        clear_screen()
        print_header("Recommandations Actuelles")
        
        recommendations = self.analyzer.generate_recommendations()
        
        if not recommendations:
            print_warning("Pas assez de données pour générer des recommandations.")
            return
        
        # Recommandations pour les tokens
        print_section("Tokens")
        
        if 'tokens' in recommendations and 'focus_on' in recommendations['tokens']:
            print(f"Tokens à privilégier: {Fore.GREEN}{', '.join(recommendations['tokens']['focus_on'])}{Style.RESET_ALL}")
        
        if 'tokens' in recommendations and 'avoid' in recommendations['tokens']:
            print(f"Tokens à éviter: {Fore.RED}{', '.join(recommendations['tokens']['avoid'])}{Style.RESET_ALL}")
        
        if 'tokens' in recommendations and 'risk_levels' in recommendations['tokens']:
            print("\nNiveaux de risque par token:")
            for token, risk in recommendations['tokens']['risk_levels'].items():
                risk_color = Fore.GREEN if risk == "low" else Fore.YELLOW if risk == "medium" else Fore.RED
                print(f"  {token}: {risk_color}{risk}{Style.RESET_ALL}")
        
        # Recommandations pour le timing
        print_section("Timing")
        
        if 'timing' in recommendations and 'best_hours' in recommendations['timing']:
            print(f"Meilleures heures: {Fore.GREEN}{', '.join(map(str, recommendations['timing']['best_hours']))}h{Style.RESET_ALL}")
        
        if 'timing' in recommendations and 'best_days' in recommendations['timing']:
            print(f"Meilleurs jours: {Fore.GREEN}{', '.join(recommendations['timing']['best_days'])}{Style.RESET_ALL}")
        
        if 'timing' in recommendations and 'avoid_hours' in recommendations['timing']:
            print(f"Heures à éviter: {Fore.RED}{', '.join(map(str, recommendations['timing']['avoid_hours']))}h{Style.RESET_ALL}")
        
        # Recommandations pour les ajustements de stratégie
        print_section("Ajustements de Stratégie")
        
        if 'strategy_adjustments' in recommendations:
            strat_adj = recommendations['strategy_adjustments']
            
            risk_level = strat_adj.get('risk_level', 'moderate')
            risk_color = Fore.GREEN if risk_level == "conservative" else Fore.YELLOW if risk_level == "moderate" else Fore.RED
            print(f"Niveau de risque recommandé: {risk_color}{risk_level}{Style.RESET_ALL}")
            
            position_size = strat_adj.get('position_size', 'maintain')
            position_color = Fore.RED if position_size == "reduce" else Fore.GREEN if position_size == "increase" else Fore.BLUE
            print(f"Taille de position: {position_color}{position_size}{Style.RESET_ALL}")
            
            stop_loss = strat_adj.get('stop_loss', 'standard')
            stop_color = Fore.GREEN if stop_loss == "tighter" else Fore.RED if stop_loss == "wider" else Fore.BLUE
            print(f"Stop-loss: {stop_color}{stop_loss}{Style.RESET_ALL}")
            
            if 'trend_bias' in strat_adj:
                trend_bias = strat_adj['trend_bias']
                trend_color = Fore.GREEN if trend_bias == "bullish" else Fore.RED
                print(f"Biais de tendance: {trend_color}{trend_bias}{Style.RESET_ALL}")
            
            if 'hold_time' in strat_adj:
                hold_time = strat_adj['hold_time']
                hold_color = Fore.GREEN if hold_time == "longer" else Fore.RED
                print(f"Durée de détention: {hold_color}{hold_time}{Style.RESET_ALL}")
        
        # Paramètres de stratégie optimisés
        print_section("Paramètres de Stratégie Optimisés")
        
        params = self.analyzer.generate_strategy_parameters()
        
        print("Arbitrage:")
        for param, value in params.get('arbitrage', {}).items():
            print(f"  {param}: {value}")
        
        print("\nSniping:")
        for param, value in params.get('sniping', {}).items():
            print(f"  {param}: {value}")
        
        if 'time_based' in params:
            print("\nParamètres basés sur le timing:")
            for param, value in params['time_based'].items():
                print(f"  {param}: {value}")
    
    def apply_recommendations(self):
        """Applique les recommandations aux modules enregistrés."""
        clear_screen()
        print_header("Application des Recommandations")
        
        # Vérifier si des modules sont intégrés
        if not self.integration.integrated_modules:
            print_warning("Aucun module n'est actuellement enregistré pour l'apprentissage continu.")
            print_info("Les modules doivent s'enregistrer auprès du système d'apprentissage continu.")
            return
        
        # Afficher les modules intégrés
        print_section("Modules Enregistrés")
        for module_name in self.integration.integrated_modules:
            print(f"  • {module_name}")
        
        # Demander confirmation
        confirm = input("\nVoulez-vous appliquer les recommandations à ces modules? (o/n): ")
        
        if confirm.lower() in ('o', 'oui', 'y', 'yes'):
            # Forcer une mise à jour
            try:
                self.integration.force_update()
                print_success("Recommandations appliquées avec succès!")
            except Exception as e:
                print_error(f"Erreur lors de l'application des recommandations: {e}")
        else:
            print_info("Application des recommandations annulée.")
    
    def configure_learning_system(self):
        """Configure les paramètres du système d'apprentissage continu."""
        clear_screen()
        print_header("Configuration du Système d'Apprentissage")
        
        print_section("Paramètres Actuels")
        print(f"Intervalle de mise à jour: {self.integration.update_interval} secondes")
        print(f"Nombre minimum de trades pour mise à jour: {self.integration.min_trades_for_update}")
        
        print_section("Modifier les Paramètres")
        
        try:
            new_interval = input("Nouvel intervalle de mise à jour (en secondes, minimum 300, Entrée pour conserver): ")
            if new_interval:
                new_interval = int(new_interval)
                self.integration.set_update_interval(new_interval)
                print_success(f"Intervalle de mise à jour défini à {self.integration.update_interval} secondes")
            
            new_min_trades = input("Nouveau nombre minimum de trades (minimum 5, Entrée pour conserver): ")
            if new_min_trades:
                new_min_trades = int(new_min_trades)
                self.integration.set_min_trades(new_min_trades)
                print_success(f"Nombre minimum de trades défini à {self.integration.min_trades_for_update}")
        
        except ValueError:
            print_error("Valeur invalide. Les paramètres n'ont pas été modifiés.")
        
        # Options avancées
        print_section("Options Avancées")
        
        print("1. Effacer toutes les données d'apprentissage")
        print("2. Exporter l'historique des trades (non implémenté)")
        print("3. Importer des données de trades (non implémenté)")
        print("4. Retour")
        
        choice = input("\nEntrez votre choix (1-4): ")
        
        if choice == '1':
            confirm = input("ATTENTION: Cette action effacera toutes les données d'apprentissage. Confirmer? (o/n): ")
            if confirm.lower() in ('o', 'oui', 'y', 'yes'):
                # Pour l'instant, nous ne supportons pas la suppression des données
                print_warning("Fonctionnalité non implémentée: effacement des données.")
        elif choice == '2' or choice == '3':
            print_warning("Fonctionnalité non implémentée: import/export de données.")
        
        return

def main():
    """Fonction principale pour exécuter l'interface CLI indépendamment."""
    parser = argparse.ArgumentParser(description="Interface CLI pour le système d'apprentissage continu de GBPBot")
    parser.add_argument('--summary', action='store_true', help="Afficher le résumé des performances et sortir")
    parser.add_argument('--history', action='store_true', help="Afficher l'historique des trades et sortir")
    parser.add_argument('--apply', action='store_true', help="Appliquer les recommandations et sortir")
    
    args = parser.parse_args()
    
    cli = LearningCLI()
    
    if args.summary:
        cli.show_performance_summary()
    elif args.history:
        cli.show_trade_history()
    elif args.apply:
        cli.apply_recommendations()
    else:
        cli.show_main_menu()

if __name__ == "__main__":
    main() 