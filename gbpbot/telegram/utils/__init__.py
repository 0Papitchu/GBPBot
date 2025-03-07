#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module d'utilitaires pour le bot Telegram de GBPBot.

Ce package contient divers utilitaires pour faciliter l'interaction avec Telegram:
- Gestion de l'authentification et des permissions
- Formatage et envoi de messages
- Création de claviers interactifs
- Gestion des callbacks des boutons
- Notifications automatiques
"""

# Version et auteur
__version__ = "1.0.0"
__author__ = "GBPBot Team"

# Importation des modules pour faciliter l'accès
try:
    # Utilitaires d'authentification
    from .auth import (
        AuthManager, check_user_auth, admin_required, rate_limit
    )
    
    # Utilitaires de messages
    from .messages import (
        send_message, edit_message, delete_message,
        send_error, send_success, send_warning, send_info,
        format_coin_info, format_trade, format_profit_report,
        escape_markdown
    )
    
    # Utilitaires de claviers
    from .keyboards import (
        create_menu_keyboard, create_confirmation_keyboard,
        create_navigation_keyboard, create_grid_keyboard,
        create_settings_keyboard, create_trading_actions_keyboard,
        create_yes_no_keyboard, create_amount_selection_keyboard,
        create_remove_keyboard, create_reply_keyboard
    )
    
    # Utilitaires de callbacks
    from .callbacks import (
        create_callback_data, parse_callback_data, get_callback_data,
        create_json_callback_data, parse_json_callback_data,
        CallbackDataBuilder, execute_callback_handlers,
        register_callback_handlers, create_paginated_data,
        parse_paginated_data
    )
    
    # Notifications automatiques
    from .auto_notifications import (
        notify_market_conditions_change, notify_parameter_adjustment,
        notify_capital_allocation, notify_error_recovery,
        format_market_conditions
    )

except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Erreur lors de l'importation des modules d'utilitaires Telegram: {e}")

# Mettre à disposition les noms des sous-modules
__all__ = [
    'auth',
    'messages',
    'keyboards',
    'callbacks',
    'auto_notifications'
] 