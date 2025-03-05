#!/usr/bin/env python
"""
Script pour corriger les références au middleware geth_poa_middleware
dans le code source du bot.

Ce script recherche toutes les occurrences de 'geth_poa_middleware'
et les remplace par notre propre middleware personnalisé.
"""

import os
import re
import glob

def find_files_with_pattern(directory, pattern, exclude_dirs=None):
    """Trouve tous les fichiers Python contenant le pattern spécifié"""
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
                        if pattern in content:
                            matches.append(filepath)
                except Exception as e:
                    print(f"Erreur lors de la lecture de {filepath}: {e}")
    return matches

def fix_middleware_imports(filepath):
    """Corrige les imports et utilisations du middleware dans un fichier"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si le fichier contient déjà notre fonction create_poa_middleware
        if 'def create_poa_middleware' not in content:
            # Ajouter notre fonction create_poa_middleware
            poa_middleware_function = """
# Fonction pour créer un middleware personnalisé pour les chaînes PoA
def create_poa_middleware():
    \"\"\"Crée un middleware personnalisé pour les chaînes PoA\"\"\"
    from web3.types import RPCEndpoint
    
    def ignore_poa_middleware(make_request, web3):
        def middleware(method, params):
            try:
                return make_request(method, params)
            except ExtraDataLengthError:
                # Ignorer l'erreur ExtraDataLengthError pour les chaînes PoA
                if method == RPCEndpoint('eth_getBlockByNumber') or method == RPCEndpoint('eth_getBlockByHash'):
                    return make_request(method, params)
                else:
                    raise
        return middleware
    
    return ignore_poa_middleware
"""
            # Trouver un bon endroit pour insérer la fonction
            import_section_end = re.search(r'(^import.*?\n)+', content, re.MULTILINE)
            if import_section_end:
                pos = import_section_end.end()
                content = content[:pos] + "\n" + poa_middleware_function + "\n" + content[pos:]
            else:
                # Si on ne trouve pas la section d'import, ajouter au début
                content = poa_middleware_function + "\n" + content
        
        # Remplacer l'import de geth_poa_middleware
        content = re.sub(
            r'from web3\.middleware import geth_poa_middleware',
            '# Import remplacé par notre propre middleware',
            content
        )
        
        # Remplacer l'utilisation de geth_poa_middleware
        content = re.sub(
            r'(\w+)\.middleware_onion\.inject\(geth_poa_middleware, layer=0\)',
            r'\1.middleware_onion.inject(create_poa_middleware(), layer=0)',
            content
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fichier corrigé: {filepath}")
    except Exception as e:
        print(f"Erreur lors de la correction de {filepath}: {e}")

def main():
    """Fonction principale"""
    print("Recherche des fichiers contenant 'geth_poa_middleware'...")
    
    # Répertoires à analyser
    project_dirs = ['.']
    
    all_files = []
    for directory in project_dirs:
        if os.path.exists(directory):
            files = find_files_with_pattern(directory, 'geth_poa_middleware')
            all_files.extend(files)
    
    # Exclure ce script lui-même
    all_files = [f for f in all_files if not f.endswith('fix_middleware.py')]
    
    if not all_files:
        print("Aucun fichier trouvé contenant 'geth_poa_middleware'.")
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