#!/usr/bin/env python3
"""
Script pour corriger l'erreur de syntaxe dans arbitrage_engine.py
"""

import os
import re

def fix_indentation():
    """Corrige l'indentation du bloc except dans arbitrage_engine.py"""
    filepath = "gbpbot/modules/arbitrage_engine.py"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier: {e}")
        return False
    
    print(f"Le fichier contient {len(lines)} lignes.")
    
    # Rechercher les lignes avec "except Exception as e:"
    except_lines = []
    for i, line in enumerate(lines):
        if "except Exception as e:" in line:
            except_lines.append(i)
    
    print(f"Trouvé {len(except_lines)} occurrences de 'except Exception as e:':")
    for i in except_lines:
        print(f"  Ligne {i+1}: {lines[i].strip()}")
        
        # Afficher le contexte autour de cette ligne
        print("\nContexte:")
        for j in range(max(0, i-10), min(len(lines), i+5)):
            print(f"  {j+1}: {lines[j].rstrip()}")
    
    # S'il y a une erreur autour de la ligne 335-336
    problematic_line = None
    for line_num in except_lines:
        if 330 <= line_num <= 340:
            problematic_line = line_num
            break
    
    if problematic_line is None:
        print("\nAucune ligne problématique identifiée entre 330 et 340.")
        return False
    
    print(f"\nCorrection de l'erreur à la ligne {problematic_line+1}...")
    
    # Trouver l'indentation correcte en regardant la ligne try correspondante
    try_line = None
    for i in range(problematic_line-1, -1, -1):
        if "try:" in lines[i]:
            try_line = i
            break
    
    if try_line is None:
        print("Impossible de trouver le bloc 'try' correspondant.")
        return False
    
    # Extraire l'indentation du bloc try
    try_match = re.match(r'^(\s*)', lines[try_line])
    if not try_match:
        print("Impossible d'extraire l'indentation du bloc try.")
        return False
        
    try_indentation = try_match.group(1)
    
    # L'indentation du except devrait être la même que celle du try
    except_line = lines[problematic_line]
    except_content = except_line.lstrip()
    corrected_except = try_indentation + except_content
    
    print(f"Indentation originale: '{lines[problematic_line]}'")
    print(f"Indentation corrigée : '{corrected_except}'")
    
    # Appliquer la correction
    lines[problematic_line] = corrected_except
    
    # Écrire les modifications dans le fichier
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.writelines(lines)
        print("\nFichier corrigé avec succès!")
        return True
    except Exception as e:
        print(f"Erreur lors de l'écriture du fichier: {e}")
        return False

if __name__ == "__main__":
    fix_indentation() 