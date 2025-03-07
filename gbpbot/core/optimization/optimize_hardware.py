#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'optimisation matérielle pour GBPBot
============================================

Ce script permet de détecter, d'optimiser et d'appliquer les réglages
optimaux pour le GBPBot en fonction du matériel spécifique de l'utilisateur.
Il ajuste les paramètres de performance pour le CPU, GPU, RAM et stockage.

Utilisation:
    python optimize_hardware.py [--apply] [--component COMPONENT] [--profile PROFILE]

Options:
    --apply             Applique les optimisations détectées (sinon analyse uniquement)
    --component         Composant à optimiser (cpu, gpu, memory, disk, network, all)
    --profile           Nom du profil à sauvegarder/charger
    --load              Charge un profil existant au lieu de détecter
    --save              Sauvegarde le profil après détection/application
"""

import os
import sys
import time
import json
import logging
import argparse
from typing import Dict, Any, List, Optional
from pathlib import Path

# Ajouter le répertoire parent au path pour les importations relatives
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Configurer le logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(parent_dir, 'logs', 'hardware_optimization.log'))
    ]
)
logger = logging.getLogger("gbpbot.optimize_hardware")

try:
    from gbpbot.core.optimization.hardware_optimizer import HardwareOptimizer, get_hardware_optimizer
    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    logger.error(f"Erreur lors de l'importation du module d'optimisation: {str(e)}")
    OPTIMIZER_AVAILABLE = False

def print_banner():
    """Affiche la bannière du script d'optimisation"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗      ║
║  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝      ║
║  ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║         ║
║  ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║         ║
║  ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║         ║
║   ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝         ║
║                                                            ║
║               Optimisation Matérielle                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_hardware_info(hardware_info: Dict[str, Any]):
    """
    Affiche les informations matérielles détectées de manière formatée.
    
    Args:
        hardware_info: Dictionnaire contenant les informations matérielles
    """
    print("\n" + "="*60)
    print(f"{'Détection du Matériel':^60}")
    print("="*60)
    
    # Informations système
    print(f"\n🖥️  {'Système':20}: {hardware_info.get('platform', 'Non détecté')}")
    
    # Informations CPU
    cpu_info = hardware_info.get('cpu', {})
    print(f"\n📊 {'CPU':^20}")
    print(f"  {'Modèle':18}: {cpu_info.get('model', 'Non détecté')}")
    print(f"  {'Cœurs physiques':18}: {cpu_info.get('cores_physical', 0)}")
    print(f"  {'Threads logiques':18}: {cpu_info.get('cores_logical', 0)}")
    print(f"  {'Fréquence':18}: {cpu_info.get('frequency', 0)/1000:.2f} GHz")
    print(f"  {'i5-12400F détecté':18}: {'✅ Oui' if cpu_info.get('is_i5_12400f', False) else '❌ Non'}")
    
    # Informations mémoire
    mem_info = hardware_info.get('memory', {})
    total_gb = mem_info.get('total', 0) / (1024**3)
    available_gb = mem_info.get('available', 0) / (1024**3)
    
    print(f"\n🧠 {'Mémoire':^20}")
    print(f"  {'Total':18}: {total_gb:.2f} Go")
    print(f"  {'Disponible':18}: {available_gb:.2f} Go")
    print(f"  {'Utilisation':18}: {mem_info.get('percent_used', 0):.1f}%")
    
    # Informations GPU
    gpu_info = hardware_info.get('gpu', {})
    print(f"\n🎮 {'GPU':^20}")
    if gpu_info.get('available', False):
        print(f"  {'Modèle':18}: {gpu_info.get('model', 'Non détecté')}")
        print(f"  {'Mémoire':18}: {gpu_info.get('memory', 0) / (1024**3):.2f} Go")
        print(f"  {'CUDA disponible':18}: {'✅ Oui' if gpu_info.get('cuda_available', False) else '❌ Non'}")
        print(f"  {'RTX 3060 détecté':18}: {'✅ Oui' if gpu_info.get('is_rtx_3060', False) else '❌ Non'}")
    else:
        print(f"  {'Status':18}: ❌ Aucun GPU compatible détecté")
    
    # Informations disque
    disk_info = hardware_info.get('disk', {})
    print(f"\n💾 {'Disque':^20}")
    print(f"  {'Total':18}: {disk_info.get('total', 0) / (1024**3):.2f} Go")
    print(f"  {'Libre':18}: {disk_info.get('free', 0) / (1024**3):.2f} Go")
    print(f"  {'NVMe détecté':18}: {'✅ Oui' if disk_info.get('is_nvme', False) else '❌ Non'}")
    
    if disk_info.get('io_speed') is not None:
        print(f"  {'Vitesse I/O':18}: {disk_info.get('io_speed', 0) / (1024**3):.2f} Go/s")
    
    # Informations réseau
    net_info = hardware_info.get('network', {})
    print(f"\n🌐 {'Réseau':^20}")
    print(f"  {'Interfaces':18}: {net_info.get('interfaces', 0)}")
    
    print("\n" + "="*60)

def print_optimization_params(params: Dict[str, Any]):
    """
    Affiche les paramètres d'optimisation de manière formatée.
    
    Args:
        params: Dictionnaire contenant les paramètres d'optimisation
    """
    print("\n" + "="*60)
    print(f"{'Paramètres d'Optimisation':^60}")
    print("="*60)
    
    # Paramètres CPU
    cpu_params = params.get('cpu', {})
    print(f"\n📊 {'CPU':^20}")
    print(f"  {'Threads optimaux':18}: {cpu_params.get('optimal_threads', 0)}")
    print(f"  {'Priorité processus':18}: {cpu_params.get('process_priority', 'normal')}")
    
    thread_alloc = cpu_params.get('thread_allocation', {})
    print(f"  {'Allocation threads':18}:")
    for purpose, count in thread_alloc.items():
        print(f"    - {purpose.capitalize():15}: {count}")
    
    # Paramètres mémoire
    mem_params = params.get('memory', {})
    print(f"\n🧠 {'Mémoire':^20}")
    print(f"  {'Utilisation max':18}: {mem_params.get('max_usage_percent', 0)}%")
    print(f"  {'Allocation trading':18}: {mem_params.get('trading_allocation_mb', 0)} Mo")
    print(f"  {'Allocation cache':18}: {mem_params.get('cache_allocation_mb', 0)} Mo")
    print(f"  {'Allocation IA':18}: {mem_params.get('ai_allocation_mb', 0)} Mo")
    print(f"  {'Stratégie cache':18}: {mem_params.get('cache_strategy', 'standard')}")
    
    # Paramètres GPU
    gpu_params = params.get('gpu', {})
    print(f"\n🎮 {'GPU':^20}")
    if gpu_params.get('enabled', False):
        print(f"  {'État':18}: ✅ Activé")
        print(f"  {'Taille de batch':18}: {gpu_params.get('optimal_batch_size', 0)}")
        print(f"  {'Précision':18}: {gpu_params.get('precision', 'float32')}")
        
        models = gpu_params.get('models_to_gpu', [])
        if models:
            print(f"  {'Modèles sur GPU':18}:")
            for model in models:
                print(f"    - {model}")
    else:
        print(f"  {'État':18}: ❌ Désactivé")
    
    # Paramètres disque
    disk_params = params.get('disk', {})
    print(f"\n💾 {'Disque':^20}")
    print(f"  {'Optimisation I/O':18}: {disk_params.get('io_optimization', 'standard')}")
    print(f"  {'Buffer lecture':18}: {disk_params.get('read_buffer_size', 0)} octets")
    print(f"  {'Buffer écriture':18}: {disk_params.get('write_buffer_size', 0)} octets")
    print(f"  {'Taille cache max':18}: {disk_params.get('max_cache_size_mb', 0)} Mo")
    
    # Paramètres réseau
    net_params = params.get('network', {})
    print(f"\n🌐 {'Réseau':^20}")
    print(f"  {'Connexions simult.':18}: {net_params.get('concurrent_connections', 0)}")
    print(f"  {'Timeout':18}: {net_params.get('timeout_ms', 0)} ms")
    print(f"  {'Tentatives':18}: {net_params.get('retry_attempts', 0)}")
    
    print("\n" + "="*60)

def print_recommendations(recommendations: List[str]):
    """
    Affiche les recommandations d'optimisation.
    
    Args:
        recommendations: Liste des recommandations
    """
    if not recommendations:
        return
    
    print("\n" + "="*60)
    print(f"{'Recommandations':^60}")
    print("="*60 + "\n")
    
    for i, recommendation in enumerate(recommendations, 1):
        print(f"  {i}. {recommendation}")
    
    print("\n" + "="*60)

def main():
    """Fonction principale du script d'optimisation matérielle"""
    parser = argparse.ArgumentParser(description="Outil d'optimisation matérielle pour GBPBot")
    parser.add_argument("--apply", action="store_true", help="Appliquer les optimisations")
    parser.add_argument("--component", choices=["cpu", "gpu", "memory", "disk", "network", "all"], 
                      default="all", help="Composant à optimiser")
    parser.add_argument("--profile", default="default", help="Nom du profil à utiliser")
    parser.add_argument("--load", action="store_true", help="Charger un profil existant")
    parser.add_argument("--save", action="store_true", help="Sauvegarder le profil après détection/application")
    
    args = parser.parse_args()
    
    print_banner()
    
    if not OPTIMIZER_AVAILABLE:
        print("❌ Module d'optimisation matérielle non disponible. Veuillez installer les dépendances requises.")
        return 1
    
    # Créer le dossier de logs s'il n'existe pas
    log_dir = os.path.join(parent_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    try:
        # Initialiser l'optimiseur matériel
        optimizer = get_hardware_optimizer()
        
        # Chargement d'un profil existant si demandé
        if args.load:
            print(f"\n📂 Chargement du profil '{args.profile}'...")
            if optimizer.load_optimization_profile(args.profile):
                print(f"✅ Profil '{args.profile}' chargé avec succès.")
            else:
                print(f"❌ Échec du chargement du profil '{args.profile}'.")
                return 1
        
        # Afficher les informations matérielles détectées
        print_hardware_info(optimizer.hardware_info)
        
        # Afficher les paramètres d'optimisation générés
        print_optimization_params(optimizer.optimization_params)
        
        # Afficher les recommandations
        recommendations = optimizer.get_recommendations()
        print_recommendations(recommendations)
        
        # Appliquer les optimisations si demandé
        if args.apply:
            print(f"\n⚙️ Application des optimisations pour: {args.component}")
            success = optimizer.apply_optimizations(args.component)
            
            if success:
                print(f"✅ Optimisations appliquées avec succès pour: {args.component}")
                
                # Afficher les métriques actuelles
                time.sleep(2)  # Attendre un instant pour collecter quelques métriques
                status = optimizer.get_optimization_status()
                
                print("\n" + "="*60)
                print(f"{'Métriques Système Actuelles':^60}")
                print("="*60 + "\n")
                
                metrics = status["current_metrics"]
                print(f"  {'CPU':18}: {metrics.get('cpu', 0):.1f}%")
                print(f"  {'RAM':18}: {metrics.get('memory', 0):.1f}%")
                
                if metrics.get('gpu', 0) > 0:
                    print(f"  {'GPU':18}: {metrics.get('gpu', 0):.1f}%")
                
                print(f"  {'Disque libre':18}: {metrics.get('disk_free_percent', 0):.1f}%")
                
                print("\n" + "="*60)
            else:
                print(f"❌ Échec de l'application des optimisations pour: {args.component}")
                return 1
        
        # Sauvegarder le profil si demandé
        if args.save:
            print(f"\n💾 Sauvegarde du profil '{args.profile}'...")
            if optimizer.save_optimization_profile(args.profile):
                print(f"✅ Profil '{args.profile}' sauvegardé avec succès.")
            else:
                print(f"❌ Échec de la sauvegarde du profil '{args.profile}'.")
                return 1
        
        # Succès
        return 0
        
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation matérielle: {str(e)}")
        print(f"❌ Une erreur s'est produite: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 