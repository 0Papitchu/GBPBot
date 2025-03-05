#!/usr/bin/env python3
"""
Script d'analyse des logs pour GBPBot.
Permet d'analyser les logs pour identifier les causes d'incidents et analyser les performances.
"""

import argparse
import logging
import sys
import os
import re
import json
import csv
import datetime
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/analyze_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("analyze_logs")

# Patterns de regex pour l'analyse des logs
LOG_PATTERNS = {
    "timestamp": r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})",
    "level": r"(DEBUG|INFO|WARNING|ERROR|CRITICAL)",
    "module": r"- ([a-zA-Z0-9_.]+) -",
    "message": r"- [A-Z]+ - (.+)$",
    "error": r"Error|Exception|Failed|Failure|Timeout|Invalid",
    "opportunity": r"Opportunity detected|Arbitrage opportunity|Profit: ([0-9.]+)",
    "transaction": r"Transaction ([a-f0-9]{64})|txHash: ([a-f0-9]{64})",
    "gas": r"Gas price: ([0-9.]+) Gwei|Gas used: ([0-9]+)",
    "price": r"Price: ([0-9.]+)|Rate: ([0-9.]+)",
    "wallet": r"Balance: ([0-9.]+) ETH|Wallet ([0-9a-fA-F]{40})"
}

def parse_timestamp(timestamp_str):
    """Parse un timestamp au format des logs."""
    try:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
    except ValueError:
        return None

def filter_logs_by_timerange(logs, start_time=None, end_time=None):
    """Filtre les logs par plage horaire."""
    filtered_logs = []
    
    for log in logs:
        timestamp_match = re.search(LOG_PATTERNS["timestamp"], log)
        if not timestamp_match:
            continue
            
        log_time = parse_timestamp(timestamp_match.group(1))
        if not log_time:
            continue
            
        if start_time and log_time < start_time:
            continue
            
        if end_time and log_time > end_time:
            continue
            
        filtered_logs.append(log)
        
    return filtered_logs

def extract_log_info(log_line):
    """Extrait les informations d'une ligne de log."""
    info = {}
    
    # Extraire les informations de base
    for key, pattern in LOG_PATTERNS.items():
        match = re.search(pattern, log_line)
        if match:
            # Certains patterns ont des groupes de capture multiples
            if key in ["opportunity", "transaction", "gas", "price", "wallet"]:
                # Prendre le premier groupe non None
                for group in match.groups():
                    if group is not None:
                        info[key] = group
                        break
            else:
                info[key] = match.group(1)
                
    return info

def analyze_errors(logs):
    """Analyse les erreurs dans les logs."""
    error_logs = [log for log in logs if "ERROR" in log or "CRITICAL" in log]
    error_count = len(error_logs)
    
    if error_count == 0:
        return {"count": 0, "errors": []}
        
    # Extraire les types d'erreurs
    error_types = Counter()
    error_details = []
    
    for log in error_logs:
        info = extract_log_info(log)
        if "message" in info:
            # Simplifier le message d'erreur pour le regroupement
            error_message = info["message"]
            # Extraire le type d'erreur (première partie du message)
            error_type = error_message.split(":")[0] if ":" in error_message else error_message
            error_types[error_type] += 1
            
            error_details.append({
                "timestamp": info.get("timestamp"),
                "module": info.get("module"),
                "message": error_message,
                "level": info.get("level")
            })
            
    return {
        "count": error_count,
        "types": dict(error_types.most_common(10)),
        "errors": error_details
    }

def analyze_opportunities(logs):
    """Analyse les opportunités d'arbitrage dans les logs."""
    opportunity_logs = [log for log in logs if "Opportunity" in log or "opportunity" in log]
    opportunity_count = len(opportunity_logs)
    
    if opportunity_count == 0:
        return {"count": 0, "opportunities": []}
        
    # Extraire les détails des opportunités
    opportunities = []
    profits = []
    
    for log in opportunity_logs:
        info = extract_log_info(log)
        if "opportunity" in info and info["opportunity"].replace(".", "", 1).isdigit():
            profit = float(info["opportunity"])
            profits.append(profit)
            
        if "timestamp" in info and "message" in info:
            opportunities.append({
                "timestamp": info["timestamp"],
                "message": info["message"],
                "profit": info.get("opportunity")
            })
            
    # Calculer les statistiques
    avg_profit = sum(profits) / len(profits) if profits else 0
    max_profit = max(profits) if profits else 0
    min_profit = min(profits) if profits else 0
    
    return {
        "count": opportunity_count,
        "avg_profit": avg_profit,
        "max_profit": max_profit,
        "min_profit": min_profit,
        "opportunities": opportunities
    }

def analyze_transactions(logs):
    """Analyse les transactions dans les logs."""
    transaction_logs = [log for log in logs if "Transaction" in log or "txHash" in log]
    transaction_count = len(transaction_logs)
    
    if transaction_count == 0:
        return {"count": 0, "transactions": []}
        
    # Extraire les détails des transactions
    transactions = []
    gas_prices = []
    gas_used = []
    
    for log in transaction_logs:
        info = extract_log_info(log)
        if "gas" in info and info["gas"].replace(".", "", 1).isdigit():
            if "Gas price" in log:
                gas_prices.append(float(info["gas"]))
            elif "Gas used" in log:
                gas_used.append(int(info["gas"]))
                
        if "timestamp" in info and "message" in info:
            transactions.append({
                "timestamp": info["timestamp"],
                "message": info["message"],
                "transaction": info.get("transaction"),
                "gas": info.get("gas")
            })
            
    # Calculer les statistiques
    avg_gas_price = sum(gas_prices) / len(gas_prices) if gas_prices else 0
    avg_gas_used = sum(gas_used) / len(gas_used) if gas_used else 0
    
    return {
        "count": transaction_count,
        "avg_gas_price": avg_gas_price,
        "avg_gas_used": avg_gas_used,
        "transactions": transactions
    }

def analyze_performance(logs):
    """Analyse les performances du bot."""
    # Extraire les timestamps pour analyser l'activité
    timestamps = []
    
    for log in logs:
        info = extract_log_info(log)
        if "timestamp" in info:
            timestamp = parse_timestamp(info["timestamp"])
            if timestamp:
                timestamps.append(timestamp)
                
    if not timestamps:
        return {"active_time": 0, "activity": {}}
        
    # Calculer la durée d'activité
    start_time = min(timestamps)
    end_time = max(timestamps)
    active_time = (end_time - start_time).total_seconds() / 3600  # en heures
    
    # Analyser l'activité par heure
    activity_by_hour = Counter()
    for timestamp in timestamps:
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        activity_by_hour[hour] += 1
        
    # Convertir en dictionnaire pour le retour
    activity = {str(hour): count for hour, count in activity_by_hour.items()}
    
    return {
        "active_time": active_time,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "activity": activity
    }

def analyze_modules(logs):
    """Analyse l'activité par module."""
    module_activity = Counter()
    module_errors = Counter()
    
    for log in logs:
        info = extract_log_info(log)
        if "module" in info:
            module = info["module"]
            module_activity[module] += 1
            
            if "level" in info and info["level"] in ["ERROR", "CRITICAL"]:
                module_errors[module] += 1
                
    return {
        "activity": dict(module_activity.most_common()),
        "errors": dict(module_errors.most_common())
    }

def generate_report(analysis, args):
    """Génère un rapport d'analyse."""
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_base = f"log_analysis_{timestamp}"
    
    # Générer un rapport texte
    with open(f"{report_dir}/{report_base}.txt", "w") as f:
        f.write("=" * 80 + "\n")
        f.write("RAPPORT D'ANALYSE DES LOGS GBPBOT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Période analysée: {analysis['performance']['start_time']} à {analysis['performance']['end_time']}\n")
        f.write(f"Durée d'activité: {analysis['performance']['active_time']:.2f} heures\n\n")
        
        f.write("-" * 80 + "\n")
        f.write("RÉSUMÉ\n")
        f.write("-" * 80 + "\n\n")
        
        f.write(f"Erreurs: {analysis['errors']['count']}\n")
        f.write(f"Opportunités: {analysis['opportunities']['count']}\n")
        f.write(f"Transactions: {analysis['transactions']['count']}\n\n")
        
        if analysis['errors']['count'] > 0:
            f.write("-" * 80 + "\n")
            f.write("ERREURS PRINCIPALES\n")
            f.write("-" * 80 + "\n\n")
            
            for error_type, count in analysis['errors']['types'].items():
                f.write(f"{error_type}: {count}\n")
            
            f.write("\nDétails des 10 dernières erreurs:\n\n")
            for error in analysis['errors']['errors'][-10:]:
                f.write(f"{error.get('timestamp', 'N/A')} - {error.get('module', 'N/A')} - {error.get('message', 'N/A')}\n")
            
            f.write("\n")
            
        if analysis['opportunities']['count'] > 0:
            f.write("-" * 80 + "\n")
            f.write("OPPORTUNITÉS\n")
            f.write("-" * 80 + "\n\n")
            
            f.write(f"Profit moyen: {analysis['opportunities']['avg_profit']:.6f}\n")
            f.write(f"Profit maximum: {analysis['opportunities']['max_profit']:.6f}\n")
            f.write(f"Profit minimum: {analysis['opportunities']['min_profit']:.6f}\n\n")
            
            f.write("Dernières opportunités détectées:\n\n")
            for opp in analysis['opportunities']['opportunities'][-5:]:
                f.write(f"{opp.get('timestamp', 'N/A')} - {opp.get('message', 'N/A')}\n")
                
            f.write("\n")
            
        if analysis['transactions']['count'] > 0:
            f.write("-" * 80 + "\n")
            f.write("TRANSACTIONS\n")
            f.write("-" * 80 + "\n\n")
            
            f.write(f"Prix du gas moyen: {analysis['transactions']['avg_gas_price']:.2f} Gwei\n")
            f.write(f"Gas utilisé moyen: {analysis['transactions']['avg_gas_used']:.0f}\n\n")
            
            f.write("Dernières transactions:\n\n")
            for tx in analysis['transactions']['transactions'][-5:]:
                f.write(f"{tx.get('timestamp', 'N/A')} - {tx.get('message', 'N/A')}\n")
                
            f.write("\n")
            
        f.write("-" * 80 + "\n")
        f.write("ACTIVITÉ PAR MODULE\n")
        f.write("-" * 80 + "\n\n")
        
        for module, count in list(analysis['modules']['activity'].items())[:10]:
            errors = analysis['modules']['errors'].get(module, 0)
            error_rate = (errors / count) * 100 if count > 0 else 0
            f.write(f"{module}: {count} logs, {errors} erreurs ({error_rate:.2f}%)\n")
            
    logger.info(f"Rapport texte généré: {report_dir}/{report_base}.txt")
    
    # Générer un rapport CSV pour les erreurs
    if analysis['errors']['count'] > 0:
        with open(f"{report_dir}/{report_base}_errors.csv", "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "module", "level", "message"])
            writer.writeheader()
            for error in analysis['errors']['errors']:
                writer.writerow(error)
                
        logger.info(f"Rapport CSV des erreurs généré: {report_dir}/{report_base}_errors.csv")
        
    # Générer des graphiques si matplotlib est disponible
    try:
        # Graphique des erreurs par module
        if analysis['errors']['count'] > 0:
            plt.figure(figsize=(12, 6))
            modules = list(analysis['modules']['errors'].keys())
            errors = list(analysis['modules']['errors'].values())
            
            if modules:
                plt.bar(modules, errors)
                plt.title('Erreurs par module')
                plt.xlabel('Module')
                plt.ylabel('Nombre d\'erreurs')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig(f"{report_dir}/{report_base}_errors_by_module.png")
                logger.info(f"Graphique des erreurs généré: {report_dir}/{report_base}_errors_by_module.png")
                
        # Graphique d'activité par heure
        activity_hours = []
        activity_counts = []
        
        for hour_str, count in sorted(analysis['performance']['activity'].items()):
            activity_hours.append(hour_str)
            activity_counts.append(count)
            
        if activity_hours:
            plt.figure(figsize=(12, 6))
            plt.plot(activity_hours, activity_counts)
            plt.title('Activité par heure')
            plt.xlabel('Heure')
            plt.ylabel('Nombre de logs')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(f"{report_dir}/{report_base}_activity.png")
            logger.info(f"Graphique d'activité généré: {report_dir}/{report_base}_activity.png")
            
    except Exception as e:
        logger.warning(f"Impossible de générer les graphiques: {str(e)}")
        
    # Afficher un résumé à l'écran
    print("\n" + "=" * 80)
    print("RÉSUMÉ DE L'ANALYSE DES LOGS")
    print("=" * 80)
    
    print(f"\nPériode: {analysis['performance']['start_time']} à {analysis['performance']['end_time']} ({analysis['performance']['active_time']:.2f} heures)")
    
    print("\nStatistiques principales:")
    stats_table = [
        ["Erreurs", analysis['errors']['count']],
        ["Opportunités", analysis['opportunities']['count']],
        ["Transactions", analysis['transactions']['count']]
    ]
    
    if analysis['opportunities']['count'] > 0:
        stats_table.extend([
            ["Profit moyen", f"{analysis['opportunities']['avg_profit']:.6f}"],
            ["Profit maximum", f"{analysis['opportunities']['max_profit']:.6f}"]
        ])
        
    if analysis['transactions']['count'] > 0:
        stats_table.extend([
            ["Gas moyen", f"{analysis['transactions']['avg_gas_price']:.2f} Gwei"]
        ])
        
    print(tabulate(stats_table, headers=["Métrique", "Valeur"]))
    
    if analysis['errors']['count'] > 0:
        print("\nPrincipaux types d'erreurs:")
        error_table = [[error_type, count] for error_type, count in analysis['errors']['types'].items()]
        print(tabulate(error_table, headers=["Type d'erreur", "Nombre"]))
        
    print("\nRapports générés dans le répertoire:", report_dir)
    print("=" * 80 + "\n")
    
    return f"{report_dir}/{report_base}.txt"

def analyze_logs(args):
    """
    Analyse les logs du bot.
    
    Args:
        args: Arguments de la ligne de commande
    """
    try:
        # Déterminer les fichiers de log à analyser
        log_files = []
        
        if args.log_file:
            if os.path.exists(args.log_file):
                log_files.append(args.log_file)
            else:
                logger.error(f"Le fichier de log spécifié n'existe pas: {args.log_file}")
                return 1
        else:
            # Chercher les fichiers de log dans le répertoire logs
            log_dir = "logs"
            if not os.path.exists(log_dir):
                logger.error(f"Le répertoire de logs n'existe pas: {log_dir}")
                return 1
                
            # Trouver les fichiers de log correspondant au pattern
            for file in os.listdir(log_dir):
                if file.startswith("gbpbot_") and file.endswith(".log"):
                    log_files.append(os.path.join(log_dir, file))
                    
            # Trier par date de modification (du plus récent au plus ancien)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Limiter le nombre de fichiers à analyser
            log_files = log_files[:args.max_files]
            
        if not log_files:
            logger.error("Aucun fichier de log trouvé à analyser")
            return 1
            
        logger.info(f"Analyse des fichiers de log: {', '.join(log_files)}")
        
        # Lire les logs
        all_logs = []
        for log_file in log_files:
            with open(log_file, "r") as f:
                logs = f.readlines()
                all_logs.extend(logs)
                
        logger.info(f"Nombre total de lignes de log: {len(all_logs)}")
        
        # Convertir les timestamps si spécifiés
        start_time = None
        end_time = None
        
        if args.from_time:
            try:
                start_time = datetime.datetime.strptime(args.from_time, "%Y-%m-%dT%H:%M:%S")
                logger.info(f"Filtrage à partir de: {start_time}")
            except ValueError:
                logger.error(f"Format de timestamp invalide pour --from: {args.from_time}")
                return 1
                
        if args.to_time:
            try:
                end_time = datetime.datetime.strptime(args.to_time, "%Y-%m-%dT%H:%M:%S")
                logger.info(f"Filtrage jusqu'à: {end_time}")
            except ValueError:
                logger.error(f"Format de timestamp invalide pour --to: {args.to_time}")
                return 1
                
        # Filtrer les logs par plage horaire si nécessaire
        if start_time or end_time:
            all_logs = filter_logs_by_timerange(all_logs, start_time, end_time)
            logger.info(f"Nombre de lignes après filtrage temporel: {len(all_logs)}")
            
        # Filtrer par niveau de log si spécifié
        if args.level:
            level_pattern = f" - {args.level.upper()} - "
            all_logs = [log for log in all_logs if level_pattern in log]
            logger.info(f"Nombre de lignes après filtrage par niveau {args.level}: {len(all_logs)}")
            
        # Filtrer par module si spécifié
        if args.module:
            module_pattern = f" - {args.module} - "
            all_logs = [log for log in all_logs if module_pattern in log]
            logger.info(f"Nombre de lignes après filtrage par module {args.module}: {len(all_logs)}")
            
        # Filtrer par mot-clé si spécifié
        if args.keyword:
            all_logs = [log for log in all_logs if args.keyword in log]
            logger.info(f"Nombre de lignes après filtrage par mot-clé '{args.keyword}': {len(all_logs)}")
            
        if not all_logs:
            logger.warning("Aucun log ne correspond aux critères de filtrage")
            return 0
            
        # Analyser les logs
        analysis = {
            "errors": analyze_errors(all_logs),
            "opportunities": analyze_opportunities(all_logs),
            "transactions": analyze_transactions(all_logs),
            "performance": analyze_performance(all_logs),
            "modules": analyze_modules(all_logs)
        }
        
        # Générer le rapport
        report_path = generate_report(analysis, args)
        
        # Afficher les détails spécifiques si demandé
        if args.show_errors and analysis["errors"]["count"] > 0:
            print("\nDétails des erreurs:")
            for error in analysis["errors"]["errors"]:
                print(f"{error.get('timestamp', 'N/A')} - {error.get('module', 'N/A')} - {error.get('message', 'N/A')}")
                
        if args.show_opportunities and analysis["opportunities"]["count"] > 0:
            print("\nDétails des opportunités:")
            for opp in analysis["opportunities"]["opportunities"]:
                print(f"{opp.get('timestamp', 'N/A')} - Profit: {opp.get('profit', 'N/A')} - {opp.get('message', 'N/A')}")
                
        if args.show_transactions and analysis["transactions"]["count"] > 0:
            print("\nDétails des transactions:")
            for tx in analysis["transactions"]["transactions"]:
                print(f"{tx.get('timestamp', 'N/A')} - {tx.get('transaction', 'N/A')} - {tx.get('message', 'N/A')}")
                
        logger.info("Analyse des logs terminée avec succès")
        return 0
        
    except Exception as e:
        logger.critical(f"Erreur lors de l'analyse des logs: {str(e)}", exc_info=True)
        return 1

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script d'analyse des logs pour GBPBot")
    
    parser.add_argument("--log-file", help="Chemin vers le fichier de log à analyser")
    parser.add_argument("--max-files", type=int, default=5, help="Nombre maximum de fichiers de log à analyser")
    parser.add_argument("--from", dest="from_time", help="Timestamp de début (format: YYYY-MM-DDThh:mm:ss)")
    parser.add_argument("--to", dest="to_time", help="Timestamp de fin (format: YYYY-MM-DDThh:mm:ss)")
    parser.add_argument("--level", choices=["debug", "info", "warning", "error", "critical"], help="Niveau de log à filtrer")
    parser.add_argument("--module", help="Module à filtrer")
    parser.add_argument("--keyword", help="Mot-clé à rechercher dans les logs")
    parser.add_argument("--show-errors", action="store_true", help="Afficher les détails des erreurs")
    parser.add_argument("--show-opportunities", action="store_true", help="Afficher les détails des opportunités")
    parser.add_argument("--show-transactions", action="store_true", help="Afficher les détails des transactions")
    parser.add_argument("--output", help="Chemin de sortie pour le rapport")
    
    args = parser.parse_args()
    
    # Exécuter l'analyse des logs
    exit_code = analyze_logs(args)
    sys.exit(exit_code)
    
if __name__ == "__main__":
    main() 