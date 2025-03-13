#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction pour le problème d'initialisation asynchrone 
dans le RPCManager, qui corrige l'erreur:
"RuntimeWarning: coroutine 'RPCManager._init_session' was never awaited"
"""

import os
import sys
import re

def fix_rpc_manager():
    # Chemin du fichier à modifier
    rpc_file = os.path.join("gbpbot", "core", "rpc", "rpc_manager.py")
    
    # Vérifier si le fichier existe
    if not os.path.exists(rpc_file):
        print(f"Erreur: {rpc_file} n'existe pas")
        return False
    
    # Lire le contenu du fichier rpc_manager.py
    with open(rpc_file, 'r', encoding='utf-8') as f:
        rpc_content = f.read()
    
    # 1. Convertir _init_session en méthode synchrone
    # Rechercher la définition de la méthode _init_session
    init_session_pattern = r'async def _init_session\(self\):'
    if re.search(init_session_pattern, rpc_content):
        rpc_content = re.sub(
            init_session_pattern,
            'def _init_session(self):',
            rpc_content
        )
        
        # Remplacer les opérations asynchrones dans _init_session
        # Trouver le corps de la méthode
        method_body_pattern = r'def _init_session\(self\):.*?(?=\n    \w|\n\n)'
        method_body_match = re.search(method_body_pattern, rpc_content, re.DOTALL)
        
        if method_body_match:
            method_body = method_body_match.group(0)
            
            # Remplacer "await" par des appels synchrones
            modified_body = method_body.replace('await self.session.close()', 'if self.session: self.session.close()')
            
            # Remplacer la méthode originale par la version modifiée
            rpc_content = rpc_content.replace(method_body, modified_body)
        
        # 2. Modifier la méthode start() pour initialiser la session de manière asynchrone
        start_method_pattern = r'async def start\(self\):.*?(?=\n    \w|\n\n)'
        start_method_match = re.search(start_method_pattern, rpc_content, re.DOTALL)
        
        if start_method_match:
            start_method = start_method_match.group(0)
            # Ajouter l'initialisation asynchrone correcte
            if "await self._ensure_session()" not in start_method:
                modified_start = start_method.replace(
                    'async def start(self):',
                    'async def start(self):\n        """Démarre le gestionnaire RPC et initialise les sessions"""\n        # Initialiser la session de manière asynchrone\n        await self._ensure_session()'
                )
                rpc_content = rpc_content.replace(start_method, modified_start)
        
        # Écrire les modifications
        with open(rpc_file, 'w', encoding='utf-8') as f:
            f.write(rpc_content)
            
        print(f"✅ {rpc_file} modifié avec succès pour corriger l'initialisation asynchrone")
        return True
    else:
        print(f"⚠️ Méthode _init_session non trouvée dans {rpc_file}")
        return False

if __name__ == "__main__":
    print("Correction de l'initialisation asynchrone du RPCManager...")
    if fix_rpc_manager():
        print("✅ Correction terminée. Le problème de coroutine non attendue devrait être résolu.")
    else:
        print("❌ Échec de la correction. Veuillez résoudre manuellement le problème d'initialisation asynchrone.") 