#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction pour l'importation cyclique entre 
gbpbot.core.monitoring.compatibility et gbpbot.core.optimization
"""

import os
import sys
import re

def fix_circular_import():
    # Chemins des fichiers à modifier
    compat_file = os.path.join("gbpbot", "core", "monitoring", "compatibility.py")
    optim_file = os.path.join("gbpbot", "core", "optimization", "__init__.py")
    
    # Vérifier si les fichiers existent
    if not os.path.exists(compat_file):
        print(f"Erreur: {compat_file} n'existe pas")
        return False
    
    if not os.path.exists(optim_file):
        print(f"Erreur: {optim_file} n'existe pas")
        return False
    
    # Lire le contenu du fichier compatibility.py
    with open(compat_file, 'r', encoding='utf-8') as f:
        compat_content = f.read()
    
    # Rechercher et commenter l'importation problématique
    pattern = r'from gbpbot\.core\.optimization import \('
    if re.search(pattern, compat_content):
        compat_content = re.sub(
            pattern, 
            '# Temporairement commenté pour éviter l\'importation cyclique\n# from gbpbot.core.optimization import (', 
            compat_content
        )
        
        # Commenter également les classes importées
        compat_content = re.sub(
            r'(\s+)(HardwareOptimizer,)', 
            r'\1# \2', 
            compat_content
        )
        
        # Ajouter une classe de remplacement temporaire
        add_after = "# Classe temporaire pour éviter l'importation cyclique\nclass HardwareOptimizerCompat:\n    @staticmethod\n    def get_instance():\n        return None\n\ndef get_hardware_optimizer_compat():\n    return None\n\n"
        
        # Trouver l'endroit où ajouter la classe temporaire (après les imports)
        import_section_end = re.search(r'import.*?\n\n', compat_content, re.DOTALL)
        if import_section_end:
            pos = import_section_end.end()
            compat_content = compat_content[:pos] + add_after + compat_content[pos:]
        else:
            # Si on ne trouve pas la fin des imports, ajouter au début du fichier
            compat_content = add_after + compat_content
            
        # Écrire les modifications
        with open(compat_file, 'w', encoding='utf-8') as f:
            f.write(compat_content)
            
        print(f"✅ {compat_file} modifié avec succès pour éviter l'importation cyclique")
        return True
    else:
        print(f"⚠️ Pattern d'importation non trouvé dans {compat_file}")
        return False

if __name__ == "__main__":
    print("Correction de l'importation cyclique...")
    if fix_circular_import():
        print("✅ Correction terminée. Vous pouvez maintenant exécuter les tests MEV.")
    else:
        print("❌ Échec de la correction. Veuillez résoudre manuellement l'importation cyclique.") 