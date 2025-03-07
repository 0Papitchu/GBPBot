#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Début du test d'import")

try:
    print("Tentative d'import de create_market_analyzer...")
    from gbpbot.ai import create_market_analyzer
    print('Import successful')
    print(f"Type de create_market_analyzer: {type(create_market_analyzer)}")
except Exception as e:
    print(f'Import failed: {e}')

print("Fin du test d'import") 