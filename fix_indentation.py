#!/usr/bin/env python
"""
Script pour corriger les problèmes d'indentation dans price_feed.py
"""

def fix_indentation():
    file_path = "gbpbot/core/price_feed.py"
    
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Corriger l'indentation des lignes problématiques
    if len(lines) >= 1001:  # Vérifier que le fichier a suffisamment de lignes
        # Corriger l'indentation de la ligne "opportunity = {"
        if "opportunity = {" in lines[1000]:
            lines[1000] = "                opportunity = {\n"
        
        # Vérifier et corriger l'indentation de "opportunities.append(opportunity)"
        if len(lines) >= 1012 and "opportunities.append(opportunity)" in lines[1011]:
            lines[1011] = "                opportunities.append(opportunity)\n"
    
    # Écrire le contenu corrigé dans le fichier
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)
    
    print(f"Correction de l'indentation terminée pour {file_path}")

if __name__ == "__main__":
    fix_indentation() 