#!/usr/bin/env python3
"""
Script pour tester l'importation du module arbitrage_engine uniquement
"""

import asyncio
import sys
from pathlib import Path
import importlib.util

async def test_arbitrage_engine():
    """Teste l'importation directe du module arbitrage_engine"""
    try:
        # Chemin absolu vers le module
        module_path = Path(__file__).parent / "gbpbot" / "modules" / "arbitrage_engine.py"
        print(f"Chemin du module: {module_path}")
        print(f"Le fichier existe: {module_path.exists()}")
        
        if not module_path.exists():
            print("❌ Le fichier arbitrage_engine.py n'existe pas au chemin spécifié!")
            return
            
        # Importation directe du module à partir de son chemin
        print("\nImportation directe du module arbitrage_engine.py...")
        spec = importlib.util.spec_from_file_location("arbitrage_engine", module_path)
        
        if spec is None:
            print("❌ Impossible de créer le spec du module!")
            return
            
        arbitrage_engine = importlib.util.module_from_spec(spec)
        
        # Vérifier que le loader existe
        if spec.loader is None:
            print("❌ Le loader du module est None!")
            return
            
        spec.loader.exec_module(arbitrage_engine)
        
        print("✅ Module arbitrage_engine.py importé avec succès via importlib!")
        
        # Afficher les attributs du module
        print("\nAttributs et méthodes du module:")
        for name in dir(arbitrage_engine):
            if not name.startswith('_'):  # Exclure les méthodes privées
                try:
                    attr = getattr(arbitrage_engine, name)
                    attr_type = type(attr).__name__
                    print(f"  - {name} ({attr_type})")
                except Exception as e:
                    print(f"  - {name} (Erreur: {e})")
        
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe dans le module: {e}")
        print(f"   Ligne {e.lineno}, position {e.offset}: {e.text}")
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue: {type(e).__name__}: {e}")

if __name__ == "__main__":
    # Exécuter la fonction asynchrone dans une boucle d'événements
    asyncio.run(test_arbitrage_engine()) 