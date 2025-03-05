#!/usr/bin/env python3
"""
Script de génération de tests d'intégration pour GBPBot.
Crée des tests d'intégration pour valider les interactions entre les différents modules.
"""

import argparse
import logging
import sys
import os
import re
import yaml
import json
import inspect
from pathlib import Path
import importlib
import importlib.util
import ast
from jinja2 import Template

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/create_integration_tests.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("create_integration_tests")

# Templates pour les tests d'intégration
INTEGRATION_TEST_TEMPLATE = """#!/usr/bin/env python3
\"\"\"
Tests d'intégration pour {{ module1 }} et {{ module2 }}.
Valide les interactions entre ces modules.
\"\"\"

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent.parent))

{% for import_stmt in imports %}
{{ import_stmt }}
{% endfor %}

@pytest.fixture
def config():
    \"\"\"Fixture pour la configuration de test.\"\"\"
    return {
        {% for key, value in config_values.items() %}
        "{{ key }}": {{ value }},
        {% endfor %}
    }

{% for fixture in fixtures %}
{{ fixture }}
{% endfor %}

{% for test in tests %}
{{ test }}
{% endfor %}
"""

FIXTURE_TEMPLATE = """@pytest.fixture
def {{ fixture_name }}():
    \"\"\"Fixture pour {{ fixture_description }}.\"\"\"
    {{ fixture_code }}
    return {{ fixture_return }}
"""

TEST_TEMPLATE = """@pytest.mark.asyncio
async def {{ test_name }}({{ test_params }}):
    \"\"\"{{ test_description }}\"\"\"
    # Arrange
    {{ arrange_code }}
    
    # Act
    {{ act_code }}
    
    # Assert
    {{ assert_code }}
"""

def scan_modules(module_path):
    """
    Scanne les modules dans le chemin spécifié.
    
    Args:
        module_path: Chemin vers le module à scanner
        
    Returns:
        dict: Informations sur les modules trouvés
    """
    modules_info = {}
    
    try:
        # Vérifier que le chemin existe
        if not os.path.exists(module_path):
            logger.error(f"Le chemin spécifié n'existe pas: {module_path}")
            return {}
            
        # Parcourir les fichiers Python dans le chemin
        for root, _, files in os.walk(module_path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(root, file)
                    module_name = os.path.splitext(file)[0]
                    
                    # Analyser le fichier pour extraire les classes et méthodes
                    module_info = analyze_module(file_path, module_name)
                    if module_info:
                        modules_info[module_name] = module_info
                        
        return modules_info
        
    except Exception as e:
        logger.error(f"Erreur lors du scan des modules: {str(e)}", exc_info=True)
        return {}

def analyze_module(file_path, module_name):
    """
    Analyse un module pour extraire les classes et méthodes.
    
    Args:
        file_path: Chemin vers le fichier du module
        module_name: Nom du module
        
    Returns:
        dict: Informations sur le module
    """
    try:
        with open(file_path, "r") as f:
            content = f.read()
            
        # Analyser le code source avec ast
        tree = ast.parse(content)
        
        classes = []
        imports = []
        
        # Extraire les imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(f"import {name.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    imports.append(f"from {module} import {name.name}")
                    
        # Extraire les classes
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "methods": [],
                    "async_methods": [],
                    "properties": []
                }
                
                # Extraire les méthodes
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            "name": item.name,
                            "args": [arg.arg for arg in item.args.args if arg.arg != "self"],
                            "is_async": False
                        }
                        class_info["methods"].append(method_info)
                    elif isinstance(item, ast.AsyncFunctionDef):
                        method_info = {
                            "name": item.name,
                            "args": [arg.arg for arg in item.args.args if arg.arg != "self"],
                            "is_async": True
                        }
                        class_info["async_methods"].append(method_info)
                        
                classes.append(class_info)
                
        return {
            "path": file_path,
            "name": module_name,
            "imports": imports,
            "classes": classes
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du module {module_name}: {str(e)}", exc_info=True)
        return None

def identify_dependencies(modules_info):
    """
    Identifie les dépendances entre les modules.
    
    Args:
        modules_info: Informations sur les modules
        
    Returns:
        list: Paires de modules avec des dépendances
    """
    dependencies = []
    
    # Identifier les modules qui importent d'autres modules
    for module_name, module_info in modules_info.items():
        for import_stmt in module_info["imports"]:
            for other_module_name in modules_info.keys():
                if other_module_name != module_name and other_module_name in import_stmt:
                    dependencies.append((module_name, other_module_name))
                    
    return dependencies

def generate_test_config():
    """
    Génère une configuration de test.
    
    Returns:
        dict: Configuration de test
    """
    return {
        "network": "testnet",
        "rpc": {
            "endpoints": [
                {"url": "https://goerli.infura.io/v3/test", "weight": 10}
            ],
            "max_retries": 3,
            "timeout": 5,
            "cache_ttl": 15
        },
        "gas": {
            "max_base_fee_gwei": "50",
            "max_priority_fee_gwei": "5",
            "min_priority_fee_gwei": "1",
            "base_fee_multiplier": "1.1",
            "priority_fee_multiplier": "1.05",
            "max_total_fee_gwei": "100",
            "update_interval": 15,
            "history_size": 20
        },
        "trading": {
            "max_slippage": 0.02,
            "min_profit": 0.01,
            "max_gas_price_gwei": "50",
            "confirmation_timeout": 60,
            "max_pending_transactions": 3,
            "emergency_shutdown_threshold": 0.1
        },
        "security": {
            "max_price_change": 0.05,
            "min_liquidity": 100,
            "max_gas_price_gwei": 100,
            "min_confirmations": 1,
            "max_confirmation_attempts": 5
        },
        "monitoring": {
            "update_interval": 5,
            "alert_thresholds": {
                "low_balance": 0.1,
                "high_gas": 50,
                "low_profit": 0.005,
                "price_deviation": 0.1,
                "error_rate": 0.3
            }
        },
        "test_mode": {
            "enabled": True,
            "simulation_only": True
        }
    }

def generate_fixtures(module1_info, module2_info):
    """
    Génère des fixtures pour les tests d'intégration.
    
    Args:
        module1_info: Informations sur le premier module
        module2_info: Informations sur le deuxième module
        
    Returns:
        list: Fixtures générées
    """
    fixtures = []
    
    # Générer des fixtures pour les classes du premier module
    for class_info in module1_info["classes"]:
        fixture_name = f"mock_{class_info['name'].lower()}"
        fixture_description = f"une instance mockée de {class_info['name']}"
        
        # Créer le code de la fixture
        fixture_code = f"mock = AsyncMock() if len({class_info['async_methods']}) > 0 else MagicMock()"
        
        # Ajouter des méthodes mockées
        for method in class_info["methods"]:
            fixture_code += f"\nmock.{method['name']}.return_value = MagicMock()"
            
        for method in class_info["async_methods"]:
            fixture_code += f"\nmock.{method['name']}.return_value = asyncio.Future()"
            fixture_code += f"\nmock.{method['name']}.return_value.set_result(MagicMock())"
            
        fixture = FIXTURE_TEMPLATE.format(
            fixture_name=fixture_name,
            fixture_description=fixture_description,
            fixture_code=fixture_code,
            fixture_return="mock"
        )
        fixtures.append(fixture)
        
    # Générer des fixtures pour les classes du deuxième module
    for class_info in module2_info["classes"]:
        fixture_name = f"mock_{class_info['name'].lower()}"
        fixture_description = f"une instance mockée de {class_info['name']}"
        
        # Créer le code de la fixture
        fixture_code = f"mock = AsyncMock() if len({class_info['async_methods']}) > 0 else MagicMock()"
        
        # Ajouter des méthodes mockées
        for method in class_info["methods"]:
            fixture_code += f"\nmock.{method['name']}.return_value = MagicMock()"
            
        for method in class_info["async_methods"]:
            fixture_code += f"\nmock.{method['name']}.return_value = asyncio.Future()"
            fixture_code += f"\nmock.{method['name']}.return_value.set_result(MagicMock())"
            
        fixture = FIXTURE_TEMPLATE.format(
            fixture_name=fixture_name,
            fixture_description=fixture_description,
            fixture_code=fixture_code,
            fixture_return="mock"
        )
        fixtures.append(fixture)
        
    return fixtures

def generate_integration_tests(module1_info, module2_info):
    """
    Génère des tests d'intégration pour deux modules.
    
    Args:
        module1_info: Informations sur le premier module
        module2_info: Informations sur le deuxième module
        
    Returns:
        list: Tests d'intégration générés
    """
    tests = []
    
    # Générer des tests pour les interactions entre les classes des deux modules
    for class1 in module1_info["classes"]:
        for class2 in module2_info["classes"]:
            # Test d'initialisation
            test_name = f"test_{class1['name'].lower()}_with_{class2['name'].lower()}_integration"
            test_params = f"config, mock_{class1['name'].lower()}, mock_{class2['name'].lower()}"
            test_description = f"Teste l'intégration entre {class1['name']} et {class2['name']}."
            
            arrange_code = f"{class1['name'].lower()} = {class1['name']}(config, mock_{class2['name'].lower()})"
            act_code = "# Simuler une interaction entre les deux classes"
            
            # Ajouter des appels de méthodes si disponibles
            if class1["methods"] or class1["async_methods"]:
                if class1["async_methods"]:
                    method = class1["async_methods"][0]
                    act_code = f"result = await {class1['name'].lower()}.{method['name']}()"
                else:
                    method = class1["methods"][0]
                    act_code = f"result = {class1['name'].lower()}.{method['name']}()"
                    
            assert_code = f"assert mock_{class2['name'].lower()}.mock_calls, \"Le mock devrait être appelé\""
            
            test = TEST_TEMPLATE.format(
                test_name=test_name,
                test_params=test_params,
                test_description=test_description,
                arrange_code=arrange_code,
                act_code=act_code,
                assert_code=assert_code
            )
            tests.append(test)
            
            # Test de comportement en cas d'erreur
            test_name = f"test_{class1['name'].lower()}_handles_{class2['name'].lower()}_error"
            test_params = f"config, mock_{class1['name'].lower()}, mock_{class2['name'].lower()}"
            test_description = f"Teste la gestion des erreurs entre {class1['name']} et {class2['name']}."
            
            arrange_code = f"{class1['name'].lower()} = {class1['name']}(config, mock_{class2['name'].lower()})"
            
            # Configurer le mock pour lever une exception
            if class2["methods"]:
                method = class2["methods"][0]
                arrange_code += f"\nmock_{class2['name'].lower()}.{method['name']}.side_effect = Exception(\"Test error\")"
            elif class2["async_methods"]:
                method = class2["async_methods"][0]
                arrange_code += f"\nmock_{class2['name'].lower()}.{method['name']}.side_effect = Exception(\"Test error\")"
                
            # Appeler une méthode qui devrait gérer l'erreur
            if class1["async_methods"]:
                method = class1["async_methods"][0]
                act_code = f"with pytest.raises(Exception):\n    await {class1['name'].lower()}.{method['name']}()"
            else:
                method = class1["methods"][0]
                act_code = f"with pytest.raises(Exception):\n    {class1['name'].lower()}.{method['name']}()"
                
            assert_code = "# L'exception devrait être levée"
            
            test = TEST_TEMPLATE.format(
                test_name=test_name,
                test_params=test_params,
                test_description=test_description,
                arrange_code=arrange_code,
                act_code=act_code,
                assert_code=assert_code
            )
            tests.append(test)
            
    return tests

def create_integration_test_file(module1_info, module2_info, output_dir):
    """
    Crée un fichier de test d'intégration pour deux modules.
    
    Args:
        module1_info: Informations sur le premier module
        module2_info: Informations sur le deuxième module
        output_dir: Répertoire de sortie
        
    Returns:
        str: Chemin vers le fichier de test créé
    """
    try:
        # Créer le répertoire de sortie si nécessaire
        os.makedirs(output_dir, exist_ok=True)
        
        # Générer le nom du fichier de test
        test_file_name = f"test_{module1_info['name']}_{module2_info['name']}_integration.py"
        test_file_path = os.path.join(output_dir, test_file_name)
        
        # Générer les imports
        imports = []
        imports.extend(module1_info["imports"])
        imports.extend(module2_info["imports"])
        
        # Ajouter les imports des classes testées
        for class_info in module1_info["classes"]:
            imports.append(f"from gbpbot.core.{module1_info['name']} import {class_info['name']}")
            
        for class_info in module2_info["classes"]:
            imports.append(f"from gbpbot.core.{module2_info['name']} import {class_info['name']}")
            
        # Supprimer les doublons
        imports = list(set(imports))
        
        # Générer la configuration de test
        config_values = generate_test_config()
        
        # Générer les fixtures
        fixtures = generate_fixtures(module1_info, module2_info)
        
        # Générer les tests
        tests = generate_integration_tests(module1_info, module2_info)
        
        # Créer le template
        template = Template(INTEGRATION_TEST_TEMPLATE)
        
        # Rendre le template
        test_content = template.render(
            module1=module1_info["name"],
            module2=module2_info["name"],
            imports=imports,
            config_values=config_values,
            fixtures=fixtures,
            tests=tests
        )
        
        # Écrire le fichier de test
        with open(test_file_path, "w") as f:
            f.write(test_content)
            
        logger.info(f"Fichier de test d'intégration créé: {test_file_path}")
        return test_file_path
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du fichier de test d'intégration: {str(e)}", exc_info=True)
        return None

def create_integration_tests(args):
    """
    Crée des tests d'intégration pour les modules spécifiés.
    
    Args:
        args: Arguments de la ligne de commande
        
    Returns:
        int: Code de sortie
    """
    try:
        # Déterminer le chemin des modules
        module_path = args.module_path or "gbpbot/core"
        
        # Déterminer le répertoire de sortie
        output_dir = args.output_dir or "tests/integration"
        
        logger.info(f"Scan des modules dans: {module_path}")
        
        # Scanner les modules
        modules_info = scan_modules(module_path)
        
        if not modules_info:
            logger.error("Aucun module trouvé")
            return 1
            
        logger.info(f"Modules trouvés: {', '.join(modules_info.keys())}")
        
        # Si des modules spécifiques sont demandés
        if args.modules:
            module_pairs = []
            modules = args.modules.split(",")
            
            if len(modules) % 2 != 0:
                logger.error("Le nombre de modules doit être pair")
                return 1
                
            for i in range(0, len(modules), 2):
                module_pairs.append((modules[i], modules[i+1]))
        else:
            # Identifier les dépendances entre les modules
            dependencies = identify_dependencies(modules_info)
            
            if not dependencies:
                logger.warning("Aucune dépendance trouvée entre les modules")
                
                # Utiliser des paires prédéfinies pour les tests d'intégration
                module_pairs = [
                    ("price_feed", "price_aggregator"),
                    ("trade_executor", "emergency_system"),
                    ("gas_manager", "trade_executor"),
                    ("price_aggregator", "trade_executor"),
                    ("trade_protection", "trade_executor"),
                    ("monitor", "emergency_system")
                ]
            else:
                module_pairs = dependencies
                
        # Créer les tests d'intégration
        created_files = []
        
        for module1_name, module2_name in module_pairs:
            if module1_name not in modules_info or module2_name not in modules_info:
                logger.warning(f"Module non trouvé: {module1_name} ou {module2_name}")
                continue
                
            logger.info(f"Création de tests d'intégration pour: {module1_name} et {module2_name}")
            
            test_file = create_integration_test_file(
                modules_info[module1_name],
                modules_info[module2_name],
                output_dir
            )
            
            if test_file:
                created_files.append(test_file)
                
        if not created_files:
            logger.warning("Aucun fichier de test d'intégration créé")
            return 1
            
        logger.info(f"Tests d'intégration créés: {len(created_files)}")
        
        # Afficher un résumé
        print("\n" + "=" * 80)
        print("RÉSUMÉ DE LA CRÉATION DES TESTS D'INTÉGRATION")
        print("=" * 80)
        
        print(f"\nModules analysés: {len(modules_info)}")
        print(f"Paires de modules testées: {len(module_pairs)}")
        print(f"Fichiers de test créés: {len(created_files)}")
        
        print("\nFichiers de test créés:")
        for file in created_files:
            print(f"  - {file}")
            
        print("\nPour exécuter les tests:")
        print(f"  pytest {output_dir} -v")
        
        print("=" * 80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.critical(f"Erreur lors de la création des tests d'intégration: {str(e)}", exc_info=True)
        return 1

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script de génération de tests d'intégration pour GBPBot")
    
    parser.add_argument("--module-path", help="Chemin vers les modules à tester")
    parser.add_argument("--output-dir", help="Répertoire de sortie pour les tests d'intégration")
    parser.add_argument("--modules", help="Paires de modules à tester (séparées par des virgules)")
    
    args = parser.parse_args()
    
    # Créer les tests d'intégration
    exit_code = create_integration_tests(args)
    sys.exit(exit_code)
    
if __name__ == "__main__":
    main() 