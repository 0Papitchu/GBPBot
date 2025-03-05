#!/usr/bin/env python
"""
Script pour corriger l'erreur d'indentation dans price_feed.py
"""

def fix_indentation():
    file_path = 'gbpbot/core/price_feed.py'
    
    # Lire le fichier
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Corriger l'indentation à la ligne 470 (index 469)
    if len(lines) > 469:
        lines[469] = '                    # Ajouter un log sur la fiabilité du prix\n'
        print(f"Ligne 470 corrigée: {lines[469].strip()}")
    else:
        print(f"Le fichier ne contient pas assez de lignes (seulement {len(lines)} lignes)")
    
    # Écrire les modifications dans le fichier
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print(f"Fichier {file_path} mis à jour avec succès")

if __name__ == "__main__":
    fix_indentation() 