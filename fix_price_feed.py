#!/usr/bin/env python
"""
Script pour corriger les problèmes d'indentation dans price_feed.py
"""
import re

def fix_price_feed():
    file_path = 'gbpbot/core/price_feed.py'
    
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Rechercher et remplacer la section problématique
    pattern = r"""            # Normaliser les prix DEX en tenant compte de la fiabilité
            for dex, price_data in dex_prices\.items\(\):
                if price_data and price_data\.get\("amount_out", 0\) > 0:
                    # Vérifier la liquidité et la fiabilité
                    liquidity = price_data\.get\("liquidity", 0\)
                    is_reliable = price_data\.get\("is_reliable", False\)
                    
                        # Calculer le prix normalisé
                        amount_in_eth = float\(Web3\.from_wei\(amount_in, "ether"\)\)
                        amount_out_eth = float\(Web3\.from_wei\(price_data\["amount_out"\], "ether"\)\)
                        
                        # Prix brut \(non normalisé\)
                        raw_price = amount_out_eth / amount_in_eth
                        
                        # Appliquer le facteur de normalisation pour les DEX
                        normalized_price = raw_price \* self\.default_dex_normalization
                        
                # Ajouter le prix au dictionnaire avec une note sur sa fiabilité
                    normalized_prices\[dex\] = normalized_price
                
                # Ajouter un log sur la fiabilité du prix
                    if is_reliable:"""
    
    replacement = """            # Normaliser les prix DEX en tenant compte de la fiabilité
            for dex, price_data in dex_prices.items():
                if price_data and price_data.get("amount_out", 0) > 0:
                    # Vérifier la liquidité et la fiabilité
                    liquidity = price_data.get("liquidity", 0)
                    is_reliable = price_data.get("is_reliable", False)
                    
                    # Calculer le prix normalisé
                    amount_in_eth = float(Web3.from_wei(amount_in, "ether"))
                    amount_out_eth = float(Web3.from_wei(price_data["amount_out"], "ether"))
                    
                    # Prix brut (non normalisé)
                    raw_price = amount_out_eth / amount_in_eth
                    
                    # Appliquer le facteur de normalisation pour les DEX
                    normalized_price = raw_price * self.default_dex_normalization
                    
                    # Ajouter le prix au dictionnaire avec une note sur sa fiabilité
                    normalized_prices[dex] = normalized_price
                    
                    # Ajouter un log sur la fiabilité du prix
                    if is_reliable:"""
    
    # Utiliser une recherche moins stricte si le pattern exact n'est pas trouvé
    if not re.search(pattern, content, re.DOTALL):
        print("Pattern exact non trouvé, utilisation d'une recherche moins stricte...")
        pattern = r"""            # Normaliser les prix DEX en tenant compte de la fiabilité
            for dex, price_data in dex_prices\.items\(\):
                if price_data and price_data\.get\("amount_out", 0\) > 0:
                    # Vérifier la liquidité et la fiabilité
                    liquidity = price_data\.get\("liquidity", 0\)
                    is_reliable = price_data\.get\("is_reliable", False\)"""
        
        # Trouver la position de début du pattern
        match = re.search(pattern, content, re.DOTALL)
        if match:
            start_pos = match.start()
            # Chercher la ligne "if is_reliable:" après cette position
            end_pattern = r"if is_reliable:"
            end_match = re.search(end_pattern, content[start_pos:])
            if end_match:
                end_pos = start_pos + end_match.end()
                # Remplacer toute la section
                section_to_replace = content[start_pos:end_pos]
                content = content.replace(section_to_replace, replacement)
                print("Section remplacée avec succès!")
            else:
                print("Fin de section non trouvée")
        else:
            print("Début de section non trouvé")
    else:
        # Remplacer le pattern exact
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        print("Pattern exact remplacé avec succès!")
    
    # Écrire le contenu modifié dans le fichier
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fichier {file_path} mis à jour")

if __name__ == "__main__":
    fix_price_feed() 