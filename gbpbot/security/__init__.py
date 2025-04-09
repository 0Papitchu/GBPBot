#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de sécurité GBPBot
=========================

Ce package contient les fonctionnalités de sécurité pour le bot GBPBot.
"""

# Exposer les classes et fonctions principales
from gbpbot.security.wallet_encryption import (
    WalletEncryption,
    encrypt_wallet_file,
    decrypt_wallet_file
)

__all__ = [
    'WalletEncryption',
    'encrypt_wallet_file',
    'decrypt_wallet_file',
] 