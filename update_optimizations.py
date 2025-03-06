#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GBPBot - Mise à jour des optimisations
--------------------------------------
Ce script analyse les logs du moniteur de performances et suggère
des ajustements d'optimisation pour GBPBot en fonction de l'utilisation
des ressources système.
"""

import os
import re
import sys
import json
import logging
import argparse
from datetime import datetime
from collections import defaultdict

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"update_optimizations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GBPBot-Optimizer")

# Seuils d'utilisation des ressources
THRESHOLDS = {
    'cpu_high': 90,      # Pourcentage d'utilisation CPU considéré comme élevé
    'cpu_low': 20,       # Pourcentage d'utilisation CPU considéré comme bas
    'memory_high': 85,   # Pourcentage d'utilisation mémoire considéré comme élevé
    'memory_low': 30,    # Pourcentage d'utilisation mémoire considéré comme bas
    'gpu_high': 85,      # Pourcentage d'utilisation GPU considéré comme élevé
    'gpu_low': 20,       # Pourcentage d'utilisation GPU considéré comme bas
}

# Paramètres d'optimisation et leurs valeurs par défaut
DEFAULT_OPTIMIZATIONS = {
    'MAX_TRANSACTION_HISTORY': 10000,
    'MAX_TOKEN_CACHE_SIZE': 2000,
    'MAX_BLACKLIST_SIZE': 10000,
    'MAX_CACHED_OPPORTUNITIES': 5000,
    'RPC_CONNECTION_LIMIT': 36,
    'RPC_MAX_CONNECTIONS_PER_HOST': 10,
    'RPC_SESSION_REFRESH_INTERVAL': 3600,
    'ML_MAX_MEMORY_USAGE': 4060,
    'ML_MAX_MODEL_SIZE': 1015,
    'ML_BATCH_SIZE': 64,
    'ML_GPU_ACCELERATION': 'auto',
    'ML_MAX_GPU_MEMORY_MB': 9830,
}

def parse_performance_log(log_file):
    """
    Analyse le fichier de log du moniteur de performances pour extraire
    les métriques d'utilisation des ressources.
    
    Args:
        log_file (str): Chemin vers le fichier de log
        
    Returns:
        dict: Statistiques d'utilisation des ressources
    """
    if not os.path.exists(log_file):
        logger.error(f"Le fichier de log {log_file} n'existe pas")
        return None
    
    # Patterns pour extraire les métriques
    cpu_pattern = re.compile(r'CPU: (\d+\.?\d*)%')
    memory_pattern = re.compile(r'Mémoire: (\d+\.?\d*)%')
    gpu_pattern = re.compile(r'GPU: (\d+\.?\d*)%')
    gpu_memory_pattern = re.compile(r'Mémoire GPU: (\d+\.?\d*)%')
    
    # Métriques à collecter
    metrics = {
        'cpu': [],
        'memory': [],
        'gpu': [],
        'gpu_memory': [],
    }
    
    # Lecture du fichier de log
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Extraction CPU
                cpu_match = cpu_pattern.search(line)
                if cpu_match:
                    metrics['cpu'].append(float(cpu_match.group(1)))
                
                # Extraction Mémoire
                memory_match = memory_pattern.search(line)
                if memory_match:
                    metrics['memory'].append(float(memory_match.group(1)))
                
                # Extraction GPU
                gpu_match = gpu_pattern.search(line)
                if gpu_match:
                    metrics['gpu'].append(float(gpu_match.group(1)))
                
                # Extraction Mémoire GPU
                gpu_memory_match = gpu_memory_pattern.search(line)
                if gpu_memory_match:
                    metrics['gpu_memory'].append(float(gpu_memory_match.group(1)))
    
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier de log: {e}")
        return None
    
    # Calcul des statistiques
    stats = {}
    for metric, values in metrics.items():
        if values:
            stats[metric] = {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'count': len(values),
            }
    
    return stats

def read_env_file(env_file):
    """
    Lit le fichier .env et extrait les paramètres d'optimisation actuels.
    
    Args:
        env_file (str): Chemin vers le fichier .env
        
    Returns:
        dict: Paramètres d'optimisation actuels
    """
    if not os.path.exists(env_file):
        logger.error(f"Le fichier .env {env_file} n'existe pas")
        return {}
    
    optimizations = {}
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Vérifier si c'est un paramètre d'optimisation
                    if key in DEFAULT_OPTIMIZATIONS:
                        # Convertir en nombre si possible
                        try:
                            if value.isdigit():
                                value = int(value)
                            elif value.replace('.', '', 1).isdigit():
                                value = float(value)
                        except ValueError:
                            pass
                        
                        optimizations[key] = value
    
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier .env: {e}")
        return {}
    
    return optimizations

def suggest_optimizations(stats, current_optimizations):
    """
    Suggère des ajustements d'optimisation en fonction des statistiques d'utilisation.
    
    Args:
        stats (dict): Statistiques d'utilisation des ressources
        current_optimizations (dict): Paramètres d'optimisation actuels
        
    Returns:
        dict: Suggestions d'optimisation
    """
    suggestions = {}
    explanations = {}
    
    # Si aucune statistique n'est disponible
    if not stats:
        logger.warning("Aucune statistique d'utilisation disponible pour suggérer des optimisations")
        return suggestions, explanations
    
    # Si aucune optimisation actuelle n'est disponible
    if not current_optimizations:
        logger.warning("Aucun paramètre d'optimisation actuel disponible")
        current_optimizations = DEFAULT_OPTIMIZATIONS.copy()
    
    # Compléter les optimisations manquantes avec les valeurs par défaut
    for key, value in DEFAULT_OPTIMIZATIONS.items():
        if key not in current_optimizations:
            current_optimizations[key] = value
    
    # Analyse de l'utilisation CPU
    if 'cpu' in stats:
        cpu_avg = stats['cpu']['avg']
        cpu_max = stats['cpu']['max']
        
        # CPU trop utilisé
        if cpu_avg > THRESHOLDS['cpu_high'] or cpu_max > 95:
            # Réduire les connexions RPC
            if 'RPC_CONNECTION_LIMIT' in current_optimizations:
                new_value = max(10, int(current_optimizations['RPC_CONNECTION_LIMIT'] * 0.7))
                suggestions['RPC_CONNECTION_LIMIT'] = new_value
                explanations['RPC_CONNECTION_LIMIT'] = f"Réduit de {current_optimizations['RPC_CONNECTION_LIMIT']} à {new_value} pour diminuer la charge CPU (utilisation moyenne: {cpu_avg:.1f}%)"
            
            # Réduire la taille des lots ML
            if 'ML_BATCH_SIZE' in current_optimizations:
                new_value = max(16, int(current_optimizations['ML_BATCH_SIZE'] * 0.5))
                suggestions['ML_BATCH_SIZE'] = new_value
                explanations['ML_BATCH_SIZE'] = f"Réduit de {current_optimizations['ML_BATCH_SIZE']} à {new_value} pour diminuer la charge CPU"
        
        # CPU sous-utilisé
        elif cpu_avg < THRESHOLDS['cpu_low'] and cpu_max < 50:
            # Augmenter les connexions RPC
            if 'RPC_CONNECTION_LIMIT' in current_optimizations:
                new_value = min(100, int(current_optimizations['RPC_CONNECTION_LIMIT'] * 1.3))
                suggestions['RPC_CONNECTION_LIMIT'] = new_value
                explanations['RPC_CONNECTION_LIMIT'] = f"Augmenté de {current_optimizations['RPC_CONNECTION_LIMIT']} à {new_value} pour mieux utiliser le CPU (utilisation moyenne: {cpu_avg:.1f}%)"
            
            # Augmenter la taille des lots ML
            if 'ML_BATCH_SIZE' in current_optimizations:
                new_value = min(128, int(current_optimizations['ML_BATCH_SIZE'] * 1.5))
                suggestions['ML_BATCH_SIZE'] = new_value
                explanations['ML_BATCH_SIZE'] = f"Augmenté de {current_optimizations['ML_BATCH_SIZE']} à {new_value} pour mieux utiliser le CPU"
    
    # Analyse de l'utilisation mémoire
    if 'memory' in stats:
        memory_avg = stats['memory']['avg']
        memory_max = stats['memory']['max']
        
        # Mémoire trop utilisée
        if memory_avg > THRESHOLDS['memory_high'] or memory_max > 95:
            # Réduire l'historique des transactions
            if 'MAX_TRANSACTION_HISTORY' in current_optimizations:
                new_value = max(1000, int(current_optimizations['MAX_TRANSACTION_HISTORY'] * 0.6))
                suggestions['MAX_TRANSACTION_HISTORY'] = new_value
                explanations['MAX_TRANSACTION_HISTORY'] = f"Réduit de {current_optimizations['MAX_TRANSACTION_HISTORY']} à {new_value} pour diminuer l'utilisation mémoire (utilisation moyenne: {memory_avg:.1f}%)"
            
            # Réduire la taille du cache de tokens
            if 'MAX_TOKEN_CACHE_SIZE' in current_optimizations:
                new_value = max(500, int(current_optimizations['MAX_TOKEN_CACHE_SIZE'] * 0.6))
                suggestions['MAX_TOKEN_CACHE_SIZE'] = new_value
                explanations['MAX_TOKEN_CACHE_SIZE'] = f"Réduit de {current_optimizations['MAX_TOKEN_CACHE_SIZE']} à {new_value} pour diminuer l'utilisation mémoire"
            
            # Réduire la mémoire ML
            if 'ML_MAX_MEMORY_USAGE' in current_optimizations:
                new_value = max(1000, int(current_optimizations['ML_MAX_MEMORY_USAGE'] * 0.7))
                suggestions['ML_MAX_MEMORY_USAGE'] = new_value
                explanations['ML_MAX_MEMORY_USAGE'] = f"Réduit de {current_optimizations['ML_MAX_MEMORY_USAGE']} à {new_value} pour diminuer l'utilisation mémoire"
        
        # Mémoire sous-utilisée
        elif memory_avg < THRESHOLDS['memory_low'] and memory_max < 60:
            # Augmenter l'historique des transactions
            if 'MAX_TRANSACTION_HISTORY' in current_optimizations:
                new_value = min(50000, int(current_optimizations['MAX_TRANSACTION_HISTORY'] * 1.5))
                suggestions['MAX_TRANSACTION_HISTORY'] = new_value
                explanations['MAX_TRANSACTION_HISTORY'] = f"Augmenté de {current_optimizations['MAX_TRANSACTION_HISTORY']} à {new_value} pour mieux utiliser la mémoire disponible (utilisation moyenne: {memory_avg:.1f}%)"
            
            # Augmenter la taille du cache de tokens
            if 'MAX_TOKEN_CACHE_SIZE' in current_optimizations:
                new_value = min(5000, int(current_optimizations['MAX_TOKEN_CACHE_SIZE'] * 1.5))
                suggestions['MAX_TOKEN_CACHE_SIZE'] = new_value
                explanations['MAX_TOKEN_CACHE_SIZE'] = f"Augmenté de {current_optimizations['MAX_TOKEN_CACHE_SIZE']} à {new_value} pour mieux utiliser la mémoire disponible"
            
            # Augmenter la mémoire ML
            if 'ML_MAX_MEMORY_USAGE' in current_optimizations:
                new_value = min(8000, int(current_optimizations['ML_MAX_MEMORY_USAGE'] * 1.3))
                suggestions['ML_MAX_MEMORY_USAGE'] = new_value
                explanations['ML_MAX_MEMORY_USAGE'] = f"Augmenté de {current_optimizations['ML_MAX_MEMORY_USAGE']} à {new_value} pour mieux utiliser la mémoire disponible"
    
    # Analyse de l'utilisation GPU
    if 'gpu' in stats and 'gpu_memory' in stats:
        gpu_avg = stats['gpu']['avg']
        gpu_memory_avg = stats['gpu_memory']['avg']
        
        # GPU trop utilisé
        if gpu_avg > THRESHOLDS['gpu_high'] or gpu_memory_avg > THRESHOLDS['gpu_high']:
            # Réduire la mémoire GPU pour ML
            if 'ML_MAX_GPU_MEMORY_MB' in current_optimizations:
                new_value = max(2000, int(current_optimizations['ML_MAX_GPU_MEMORY_MB'] * 0.8))
                suggestions['ML_MAX_GPU_MEMORY_MB'] = new_value
                explanations['ML_MAX_GPU_MEMORY_MB'] = f"Réduit de {current_optimizations['ML_MAX_GPU_MEMORY_MB']} à {new_value} pour diminuer l'utilisation GPU (utilisation moyenne: {gpu_avg:.1f}%)"
        
        # GPU sous-utilisé
        elif gpu_avg < THRESHOLDS['gpu_low'] and gpu_memory_avg < THRESHOLDS['gpu_low']:
            # Forcer l'utilisation du GPU
            if 'ML_GPU_ACCELERATION' in current_optimizations:
                if current_optimizations['ML_GPU_ACCELERATION'] != 'force':
                    suggestions['ML_GPU_ACCELERATION'] = 'force'
                    explanations['ML_GPU_ACCELERATION'] = f"Changé de '{current_optimizations['ML_GPU_ACCELERATION']}' à 'force' pour mieux utiliser le GPU (utilisation moyenne: {gpu_avg:.1f}%)"
            
            # Augmenter la mémoire GPU pour ML
            if 'ML_MAX_GPU_MEMORY_MB' in current_optimizations:
                new_value = min(16000, int(current_optimizations['ML_MAX_GPU_MEMORY_MB'] * 1.2))
                suggestions['ML_MAX_GPU_MEMORY_MB'] = new_value
                explanations['ML_MAX_GPU_MEMORY_MB'] = f"Augmenté de {current_optimizations['ML_MAX_GPU_MEMORY_MB']} à {new_value} pour mieux utiliser le GPU"
    
    return suggestions, explanations

def update_env_file(env_file, suggestions, explanations, dry_run=True):
    """
    Met à jour le fichier .env avec les suggestions d'optimisation.
    
    Args:
        env_file (str): Chemin vers le fichier .env
        suggestions (dict): Suggestions d'optimisation
        explanations (dict): Explications des suggestions
        dry_run (bool): Si True, n'effectue pas les modifications
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    if not os.path.exists(env_file):
        logger.error(f"Le fichier .env {env_file} n'existe pas")
        return False
    
    if not suggestions:
        logger.info("Aucune suggestion d'optimisation à appliquer")
        return True
    
    # Lecture du fichier .env
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier .env: {e}")
        return False
    
    # Création d'une sauvegarde
    backup_file = f"{env_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        logger.info(f"Sauvegarde du fichier .env créée: {backup_file}")
    except Exception as e:
        logger.error(f"Erreur lors de la création de la sauvegarde: {e}")
        return False
    
    # Mise à jour des lignes
    updated_lines = []
    updated_params = set()
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip or line_strip.startswith('#'):
            updated_lines.append(line)
            continue
        
        if '=' in line_strip:
            key, value = line_strip.split('=', 1)
            key = key.strip()
            
            if key in suggestions:
                new_line = f"{key}={suggestions[key]}"
                if not line.endswith('\n'):
                    new_line += '\n'
                updated_lines.append(new_line)
                updated_params.add(key)
                logger.info(f"Mise à jour de {key}: {value.strip()} -> {suggestions[key]} ({explanations.get(key, 'Optimisation')})")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Ajouter les paramètres manquants
    missing_params = set(suggestions.keys()) - updated_params
    if missing_params:
        # Chercher la section des optimisations
        optimization_section_found = False
        for i, line in enumerate(updated_lines):
            if "OPTIMISATIONS DE PERFORMANCE" in line or "PERFORMANCE OPTIMIZATIONS" in line:
                optimization_section_found = True
                break
        
        if optimization_section_found:
            # Ajouter les paramètres manquants à la fin de la section
            for key in missing_params:
                new_line = f"{key}={suggestions[key]}\n"
                updated_lines.append(new_line)
                logger.info(f"Ajout de {key}={suggestions[key]} ({explanations.get(key, 'Optimisation')})")
        else:
            # Ajouter une nouvelle section d'optimisations
            updated_lines.append("\n# OPTIMISATIONS DE PERFORMANCE\n")
            for key in missing_params:
                new_line = f"{key}={suggestions[key]}\n"
                updated_lines.append(new_line)
                logger.info(f"Ajout de {key}={suggestions[key]} ({explanations.get(key, 'Optimisation')})")
    
    # Écriture du fichier mis à jour
    if not dry_run:
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            logger.info(f"Fichier .env mis à jour avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du fichier .env: {e}")
            return False
    else:
        logger.info("Mode simulation: aucune modification n'a été effectuée")
        return True

def generate_report(stats, current_optimizations, suggestions, explanations):
    """
    Génère un rapport détaillé des optimisations suggérées.
    
    Args:
        stats (dict): Statistiques d'utilisation des ressources
        current_optimizations (dict): Paramètres d'optimisation actuels
        suggestions (dict): Suggestions d'optimisation
        explanations (dict): Explications des suggestions
        
    Returns:
        str: Rapport au format Markdown
    """
    report = "# Rapport d'Optimisation GBPBot\n\n"
    report += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Statistiques d'utilisation
    report += "## Statistiques d'Utilisation\n\n"
    
    if stats:
        report += "| Ressource | Minimum | Maximum | Moyenne | Nombre de mesures |\n"
        report += "|-----------|---------|---------|---------|-------------------|\n"
        
        for metric, values in stats.items():
            if metric == 'cpu':
                name = "CPU"
            elif metric == 'memory':
                name = "Mémoire RAM"
            elif metric == 'gpu':
                name = "GPU"
            elif metric == 'gpu_memory':
                name = "Mémoire GPU"
            else:
                name = metric
            
            report += f"| {name} | {values['min']:.1f}% | {values['max']:.1f}% | {values['avg']:.1f}% | {values['count']} |\n"
    else:
        report += "*Aucune statistique d'utilisation disponible*\n\n"
    
    # Optimisations actuelles
    report += "\n## Optimisations Actuelles\n\n"
    
    if current_optimizations:
        report += "| Paramètre | Valeur |\n"
        report += "|-----------|--------|\n"
        
        for key, value in sorted(current_optimizations.items()):
            report += f"| {key} | {value} |\n"
    else:
        report += "*Aucune optimisation actuelle disponible*\n\n"
    
    # Suggestions d'optimisation
    report += "\n## Suggestions d'Optimisation\n\n"
    
    if suggestions:
        report += "| Paramètre | Valeur Actuelle | Nouvelle Valeur | Explication |\n"
        report += "|-----------|----------------|----------------|-------------|\n"
        
        for key, new_value in sorted(suggestions.items()):
            current_value = current_optimizations.get(key, "N/A")
            explanation = explanations.get(key, "Optimisation recommandée")
            report += f"| {key} | {current_value} | {new_value} | {explanation} |\n"
    else:
        report += "*Aucune suggestion d'optimisation*\n\n"
    
    # Recommandations générales
    report += "\n## Recommandations Générales\n\n"
    
    if stats:
        if 'cpu' in stats and stats['cpu']['avg'] > THRESHOLDS['cpu_high']:
            report += "- ⚠️ **Utilisation CPU élevée**: Envisagez de réduire le nombre de connexions RPC et la taille des lots ML.\n"
        
        if 'memory' in stats and stats['memory']['avg'] > THRESHOLDS['memory_high']:
            report += "- ⚠️ **Utilisation mémoire élevée**: Envisagez de réduire la taille des caches et l'historique des transactions.\n"
        
        if 'gpu' in stats and 'gpu_memory' in stats:
            if stats['gpu']['avg'] < THRESHOLDS['gpu_low'] and stats['gpu_memory']['avg'] < THRESHOLDS['gpu_low']:
                report += "- 💡 **GPU sous-utilisé**: Envisagez d'activer l'accélération GPU pour les modèles ML.\n"
    
    report += "\n---\n\n"
    report += "*Ce rapport a été généré automatiquement par l'outil d'optimisation GBPBot.*\n"
    
    return report

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='GBPBot - Mise à jour des optimisations')
    parser.add_argument('--log-file', default='gbpbot_performance.log', help='Fichier de log du moniteur de performances')
    parser.add_argument('--env-file', default='.env', help='Fichier .env à mettre à jour')
    parser.add_argument('--apply', action='store_true', help='Appliquer les suggestions (par défaut: mode simulation)')
    parser.add_argument('--report', action='store_true', help='Générer un rapport détaillé')
    parser.add_argument('--report-file', default='optimization_report.md', help='Fichier de rapport')
    args = parser.parse_args()
    
    logger.info("=== GBPBot - Analyse des performances et mise à jour des optimisations ===")
    
    # Analyse du fichier de log
    logger.info(f"Analyse du fichier de log: {args.log_file}")
    stats = parse_performance_log(args.log_file)
    
    if not stats:
        logger.error("Impossible d'analyser les statistiques d'utilisation")
        return 1
    
    # Lecture des optimisations actuelles
    logger.info(f"Lecture des optimisations actuelles: {args.env_file}")
    current_optimizations = read_env_file(args.env_file)
    
    # Suggestion d'optimisations
    logger.info("Génération des suggestions d'optimisation")
    suggestions, explanations = suggest_optimizations(stats, current_optimizations)
    
    if not suggestions:
        logger.info("Aucune suggestion d'optimisation n'est nécessaire")
    else:
        logger.info(f"Nombre de suggestions: {len(suggestions)}")
        
        # Affichage des suggestions
        for key, value in suggestions.items():
            current = current_optimizations.get(key, "N/A")
            logger.info(f"  {key}: {current} -> {value} ({explanations.get(key, 'Optimisation')})")
        
        # Mise à jour du fichier .env
        if args.apply:
            logger.info(f"Application des suggestions au fichier {args.env_file}")
            if update_env_file(args.env_file, suggestions, explanations, dry_run=False):
                logger.info("Optimisations appliquées avec succès")
            else:
                logger.error("Erreur lors de l'application des optimisations")
                return 1
        else:
            logger.info("Mode simulation: aucune modification n'a été effectuée")
            logger.info("Utilisez --apply pour appliquer les suggestions")
    
    # Génération du rapport
    if args.report:
        logger.info(f"Génération du rapport: {args.report_file}")
        report = generate_report(stats, current_optimizations, suggestions, explanations)
        
        try:
            with open(args.report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Rapport généré avec succès: {args.report_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            return 1
    
    logger.info("=== Analyse terminée ===")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 