#!/usr/bin/env python
"""
Script pour corriger les références au middleware geth_poa_middleware
et les fonctions create_poa_middleware dans le code source du bot pour web3.py v7.8.0.

Ce script recherche toutes les occurrences de 'geth_poa_middleware' et 'create_poa_middleware'
et les supprime, car web3.py v7.8.0 gère déjà correctement les chaînes PoA.
"""

import os
import re
import glob

def find_files_with_patterns(directory, patterns, exclude_dirs=None):
    """Trouve tous les fichiers Python contenant les patterns spécifiés"""
    if exclude_dirs is None:
        exclude_dirs = ['venv', 'venv_new', '__pycache__', '.git']
    
    matches = []
    for root, dirs, files in os.walk(directory):
        # Exclure les répertoires spécifiés
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for filename in files:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if any(pattern in content for pattern in patterns):
                            matches.append(filepath)
                except Exception as e:
                    print(f"Erreur lors de la lecture de {filepath}: {e}")
    return matches

def fix_middleware_imports(filepath):
    """Corrige les imports et utilisations du middleware dans un fichier"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Supprimer l'import de geth_poa_middleware
        content = re.sub(
            r'from web3\.middleware import geth_poa_middleware\s*',
            '',
            content
        )
        
        # Supprimer l'utilisation du middleware
        content = re.sub(
            r'(\w+)\.middleware_onion\.inject\(geth_poa_middleware, layer=0\)',
            r'# Middleware PoA non nécessaire avec web3.py v7.8.0',
            content
        )
        
        # Supprimer les fonctions create_poa_middleware
        content = re.sub(
            r'def create_poa_middleware\(\):.*?return ignore_poa_middleware',
            '# Fonction supprimée car non nécessaire avec web3.py v7.8.0',
            content,
            flags=re.DOTALL
        )
        
        # Supprimer l'utilisation de create_poa_middleware
        content = re.sub(
            r'(\w+)\.middleware_onion\.inject\(create_poa_middleware\(\), layer=0\)',
            r'# Middleware PoA non nécessaire avec web3.py v7.8.0',
            content
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fichier corrigé: {filepath}")
    except Exception as e:
        print(f"Erreur lors de la correction de {filepath}: {e}")

def main():
    """Fonction principale"""
    print("Recherche des fichiers contenant 'geth_poa_middleware' ou 'create_poa_middleware'...")
    
    # Répertoires à analyser
    project_dirs = ['.']
    
    all_files = []
    for directory in project_dirs:
        if os.path.exists(directory):
            files = find_files_with_patterns(directory, ['geth_poa_middleware', 'create_poa_middleware'])
            all_files.extend(files)
    
    # Exclure ce script lui-même et les autres scripts de correction
    all_files = [f for f in all_files if not (f.endswith('fix_middleware.py') or 
                                             f.endswith('fix_middleware_v2.py') or
                                             f.endswith('fix_middleware_v3.py'))]
    
    if not all_files:
        print("Aucun fichier trouvé contenant 'geth_poa_middleware' ou 'create_poa_middleware'.")
        return
    
    print(f"Trouvé {len(all_files)} fichier(s) à corriger:")
    for file in all_files:
        print(f"- {file}")
    
    print("\nCorrection des fichiers...")
    for file in all_files:
        fix_middleware_imports(file)
    
    print("\nCorrection terminée. Vous pouvez maintenant lancer le bot.")

if __name__ == "__main__":
    main() 