#!/usr/bin/env python
"""
Script pour exécuter tous les tests de vérification et préparer le bot pour une exécution en production
"""

import os
import sys
import time
import logging
import asyncio
import subprocess
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"pre_launch_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

# Scripts de vérification à exécuter
VERIFICATION_SCRIPTS = [
    {
        "name": "Vérification de l'intégrité du bot",
        "script": "verify_bot_integrity.py",
        "required": True,
        "description": "Vérifie que tous les composants du bot sont présents et fonctionnels"
    },
    {
        "name": "Test des endpoints RPC",
        "script": "test_rpc_endpoints.py",
        "required": True,
        "description": "Teste la connectivité et la fiabilité des endpoints RPC"
    },
    {
        "name": "Vérification des paires de trading",
        "script": "verify_trading_pairs.py",
        "required": True,
        "description": "Vérifie l'existence et la liquidité des paires de trading configurées"
    },
    {
        "name": "Optimisation des paramètres",
        "script": "optimize_bot_params.py",
        "required": False,
        "description": "Optimise les paramètres du bot en fonction des conditions du marché"
    },
    {
        "name": "Tests unitaires",
        "script": "python -m pytest tests/test_arbitrage.py tests/test_mev.py tests/test_sniping.py -v",
        "required": True,
        "description": "Exécute les tests unitaires pour vérifier le bon fonctionnement des stratégies",
        "is_shell_command": True
    }
]

# Étapes de préparation pour le lancement
PREPARATION_STEPS = [
    {
        "name": "Création d'une sauvegarde",
        "command": "python -c \"from gbpbot.core.version_manager import VersionManager; import asyncio; asyncio.run(VersionManager().create_backup('pre_launch'))\"",
        "required": True,
        "description": "Crée une sauvegarde complète du bot avant le lancement"
    },
    {
        "name": "Nettoyage des logs",
        "command": "python -c \"import os, glob; [os.remove(f) for f in glob.glob('logs/*.log') if os.path.getsize(f) > 10*1024*1024]\"",
        "required": False,
        "description": "Supprime les fichiers de log trop volumineux pour libérer de l'espace"
    }
]

async def run_verification_script(script_info: Dict) -> Tuple[bool, str]:
    """
    Exécute un script de vérification
    
    Args:
        script_info: Informations sur le script à exécuter
        
    Returns:
        Tuple[bool, str]: Succès (True/False) et message de sortie
    """
    try:
        logging.info(f"Exécution de {script_info['name']}...")
        
        if script_info.get("is_shell_command", False):
            # Exécuter une commande shell
            process = subprocess.Popen(
                script_info["script"],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            output = stdout + stderr
            success = process.returncode == 0
        else:
            # Exécuter un script Python
            process = subprocess.Popen(
                [sys.executable, script_info["script"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            output = stdout + stderr
            success = process.returncode == 0
        
        status = "✅ Réussi" if success else "❌ Échoué"
        logging.info(f"{status} - {script_info['name']}")
        
        # Enregistrer la sortie dans un fichier
        script_name = script_info["script"].split(" ")[0].replace(".py", "")
        output_file = f"output_{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(output_file, "w") as f:
            f.write(output)
        
        return success, output
    
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution de {script_info['name']}: {str(e)}")
        return False, str(e)

async def run_preparation_step(step_info: Dict) -> Tuple[bool, str]:
    """
    Exécute une étape de préparation
    
    Args:
        step_info: Informations sur l'étape à exécuter
        
    Returns:
        Tuple[bool, str]: Succès (True/False) et message de sortie
    """
    try:
        logging.info(f"Exécution de {step_info['name']}...")
        
        process = subprocess.Popen(
            step_info["command"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        output = stdout + stderr
        success = process.returncode == 0
        
        status = "✅ Réussi" if success else "❌ Échoué"
        logging.info(f"{status} - {step_info['name']}")
        
        return success, output
    
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution de {step_info['name']}: {str(e)}")
        return False, str(e)

async def run_all_checks():
    """
    Exécute tous les tests de vérification et prépare le bot pour une exécution en production
    """
    logging.info("=== DÉMARRAGE DES VÉRIFICATIONS PRÉ-LANCEMENT ===")
    logging.info(f"Date et heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Résultats des vérifications
    verification_results = []
    all_required_passed = True
    
    # Exécuter les scripts de vérification
    logging.info("\n=== SCRIPTS DE VÉRIFICATION ===")
    for script_info in VERIFICATION_SCRIPTS:
        success, output = await run_verification_script(script_info)
        verification_results.append({
            "name": script_info["name"],
            "success": success,
            "required": script_info["required"],
            "output": output[:500] + "..." if len(output) > 500 else output  # Tronquer la sortie pour le résumé
        })
        
        if script_info["required"] and not success:
            all_required_passed = False
    
    # Vérifier si toutes les vérifications requises ont réussi
    if not all_required_passed:
        logging.error("\n❌ Certaines vérifications requises ont échoué. Arrêt du processus de lancement.")
        return False
    
    # Exécuter les étapes de préparation
    logging.info("\n=== ÉTAPES DE PRÉPARATION ===")
    preparation_results = []
    all_required_prep_passed = True
    
    for step_info in PREPARATION_STEPS:
        success, output = await run_preparation_step(step_info)
        preparation_results.append({
            "name": step_info["name"],
            "success": success,
            "required": step_info["required"],
            "output": output[:500] + "..." if len(output) > 500 else output  # Tronquer la sortie pour le résumé
        })
        
        if step_info["required"] and not success:
            all_required_prep_passed = False
    
    # Vérifier si toutes les étapes de préparation requises ont réussi
    if not all_required_prep_passed:
        logging.error("\n❌ Certaines étapes de préparation requises ont échoué. Arrêt du processus de lancement.")
        return False
    
    # Afficher le résumé
    logging.info("\n=== RÉSUMÉ DES VÉRIFICATIONS ===")
    for result in verification_results:
        status = "✅" if result["success"] else "❌"
        required = "[REQUIS]" if result["required"] else "[OPTIONNEL]"
        logging.info(f"{status} {required} {result['name']}")
    
    logging.info("\n=== RÉSUMÉ DES ÉTAPES DE PRÉPARATION ===")
    for result in preparation_results:
        status = "✅" if result["success"] else "❌"
        required = "[REQUIS]" if result["required"] else "[OPTIONNEL]"
        logging.info(f"{status} {required} {result['name']}")
    
    # Conclusion
    if all_required_passed and all_required_prep_passed:
        logging.info("\n✅ TOUTES LES VÉRIFICATIONS ET PRÉPARATIONS REQUISES ONT RÉUSSI")
        logging.info("Le bot est prêt à être lancé en production.")
        
        # Demander confirmation pour le lancement
        print("\nVoulez-vous lancer le bot maintenant? (o/n): ", end="")
        response = input().lower()
        
        if response == "o" or response == "oui":
            logging.info("Lancement du bot...")
            
            # Lancer le bot en mode production
            launch_command = "python -m gbpbot.cli"
            logging.info(f"Exécution de la commande: {launch_command}")
            
            # Utiliser subprocess.Popen pour lancer le bot en arrière-plan
            process = subprocess.Popen(
                launch_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Attendre un peu pour voir si le processus démarre correctement
            time.sleep(2)
            
            if process.poll() is None:
                logging.info("✅ Le bot a été lancé avec succès (PID: {})".format(process.pid))
                return True
            else:
                stdout, stderr = process.communicate()
                logging.error(f"❌ Échec du lancement du bot: {stderr}")
                return False
        else:
            logging.info("Lancement annulé par l'utilisateur.")
            return True
    else:
        logging.error("\n❌ CERTAINES VÉRIFICATIONS OU PRÉPARATIONS REQUISES ONT ÉCHOUÉ")
        logging.error("Veuillez corriger les problèmes avant de lancer le bot en production.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_checks())
    sys.exit(0 if success else 1) 