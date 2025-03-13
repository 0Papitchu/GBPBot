#!/usr/bin/env python3
"""
Script pour tester l'importation des modules GBPBot avec asyncio correctement initialisé
"""

import asyncio
import sys
import os
from pathlib import Path

async def test_imports():
    """Teste l'importation des modules GBPBot dans un contexte asyncio"""
    try:
        # Ajouter le répertoire parent au path pour permettre l'importation
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Importations de base
        print("Importation des modules de base...")
        from gbpbot.utils import logger
        print("✅ utils.logger importé")
        
        # Tenter d'importer le module arbitrage_engine
        print("\nTentative d'importation de arbitrage_engine...")
        from gbpbot.modules import arbitrage_engine
        print("✅ modules.arbitrage_engine importé avec succès!")
        
        # Tenter d'importer le module de continuous learning
        print("\nTentative d'importation du module de continuous learning...")
        try:
            from gbpbot.ai import continuous_learning
            print("✅ ai.continuous_learning importé avec succès!")
        except ImportError as e:
            print(f"❌ Erreur lors de l'importation du module continuous_learning: {e}")
            print("   Vérifiez le chemin d'importation et les dépendances.")
            
        # Afficher les méthodes disponibles dans arbitrage_engine
        print("\nMéthodes disponibles dans arbitrage_engine:")
        for name in dir(arbitrage_engine):
            if not name.startswith('_'):  # Exclure les méthodes privées
                print(f"  - {name}")
        
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe: {e}")
        print(f"   Ligne {e.lineno}, position {e.offset}: {e.text}")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")

if __name__ == "__main__":
    # Exécuter la fonction asynchrone dans une boucle d'événements
    asyncio.run(test_imports()) 