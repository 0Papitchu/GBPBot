"""
Blockchain utilities for common operations across different blockchains.

This module provides utility functions for common blockchain operations such as
unit conversion, address validation, and other helper functions that can be used
across different blockchain implementations.
"""

import re
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any

# Configure logging
logger = logging.getLogger(__name__)

# Common constants
WEI_TO_ETH = Decimal('1000000000000000000')  # 10^18
LAMPORTS_TO_SOL = Decimal('1000000000')  # 10^9
GWEI_TO_WEI = Decimal('1000000000')  # 10^9

# Common token decimals
DEFAULT_TOKEN_DECIMALS = {
    'ethereum': {
        'ETH': 18,
        'USDT': 6,
        'USDC': 6,
        'DAI': 18,
        'WETH': 18,
    },
    'solana': {
        'SOL': 9,
        'USDT': 6,
        'USDC': 6,
    },
    'polygon': {
        'MATIC': 18,
        'USDT': 6,
        'USDC': 6,
        'WETH': 18,
    },
    'avalanche': {
        'AVAX': 18,
        'USDT': 6,
        'USDC': 6,
    },
    'arbitrum': {
        'ETH': 18,
        'USDT': 6,
        'USDC': 6,
    }
}

def wei_to_eth(wei_amount: Union[int, str, Decimal]) -> Decimal:
    """
    Convert wei to ETH.
    
    Args:
        wei_amount: Amount in wei
        
    Returns:
        Amount in ETH as a Decimal
    """
    wei = Decimal(str(wei_amount))
    return wei / WEI_TO_ETH

def eth_to_wei(eth_amount: Union[float, str, Decimal]) -> int:
    """
    Convert ETH to wei.
    
    Args:
        eth_amount: Amount in ETH
        
    Returns:
        Amount in wei as an integer
    """
    eth = Decimal(str(eth_amount))
    wei = eth * WEI_TO_ETH
    return int(wei)

def lamports_to_sol(lamports_amount: Union[int, str, Decimal]) -> Decimal:
    """
    Convert lamports to SOL.
    
    Args:
        lamports_amount: Amount in lamports
        
    Returns:
        Amount in SOL as a Decimal
    """
    lamports = Decimal(str(lamports_amount))
    return lamports / LAMPORTS_TO_SOL

def sol_to_lamports(sol_amount: Union[float, str, Decimal]) -> int:
    """
    Convert SOL to lamports.
    
    Args:
        sol_amount: Amount in SOL
        
    Returns:
        Amount in lamports as an integer
    """
    sol = Decimal(str(sol_amount))
    lamports = sol * LAMPORTS_TO_SOL
    return int(lamports)

def gwei_to_wei(gwei_amount: Union[float, str, Decimal]) -> int:
    """
    Convert Gwei to wei.
    
    Args:
        gwei_amount: Amount in Gwei
        
    Returns:
        Amount in wei as an integer
    """
    gwei = Decimal(str(gwei_amount))
    wei = gwei * GWEI_TO_WEI
    return int(wei)

def format_token_amount(amount: Union[int, float, str, Decimal], 
                        decimals: int) -> Decimal:
    """
    Format a token amount from its smallest unit to its standard unit.
    
    Args:
        amount: Amount in the smallest unit
        decimals: Number of decimal places
        
    Returns:
        Formatted amount as a Decimal
    """
    amount_decimal = Decimal(str(amount))
    divisor = Decimal(10) ** Decimal(decimals)
    return amount_decimal / divisor

def parse_token_amount(amount: Union[float, str, Decimal], 
                       decimals: int) -> int:
    """
    Parse a token amount from its standard unit to its smallest unit.
    
    Args:
        amount: Amount in the standard unit
        decimals: Number of decimal places
        
    Returns:
        Parsed amount as an integer
    """
    amount_decimal = Decimal(str(amount))
    multiplier = Decimal(10) ** Decimal(decimals)
    return int(amount_decimal * multiplier)

def is_valid_ethereum_address(address: str) -> bool:
    """
    Check if an Ethereum address is valid.
    
    Args:
        address: Ethereum address to check
        
    Returns:
        True if the address is valid, False otherwise
    """
    if not address:
        return False
    
    # Check if the address starts with '0x' and has the correct length
    if not address.startswith('0x') or len(address) != 42:
        return False
    
    # Check if the address contains only hexadecimal characters after '0x'
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False

def is_valid_solana_address(address: str) -> bool:
    """
    Check if a Solana address is valid.
    
    Args:
        address: Solana address to check
        
    Returns:
        True if the address is valid, False otherwise
    """
    if not address:
        return False
    
    # Solana addresses are base58 encoded and typically 32-44 characters long
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
    return bool(re.match(base58_pattern, address))

def get_token_decimals(token_symbol: str, blockchain: str) -> int:
    """
    Get the number of decimals for a token.
    
    Args:
        token_symbol: Symbol of the token
        blockchain: Blockchain the token is on
        
    Returns:
        Number of decimals for the token
    """
    blockchain = blockchain.lower()
    token_symbol = token_symbol.upper()
    
    if blockchain in DEFAULT_TOKEN_DECIMALS and token_symbol in DEFAULT_TOKEN_DECIMALS[blockchain]:
        return DEFAULT_TOKEN_DECIMALS[blockchain][token_symbol]
    
    # Default values if not found
    if blockchain == 'solana':
        return 9  # Default for Solana tokens
    else:
        return 18  # Default for EVM-based tokens

def get_gas_price_level(blockchain: str, priority: str = "normal") -> Dict[str, Any]:
    """
    Get gas price levels for a blockchain.
    
    Args:
        blockchain: Blockchain to get gas price for
        priority: Gas priority level (slow, normal, fast)
        
    Returns:
        Gas price configuration for the specified priority
    """
    priority = priority.lower()
    blockchain = blockchain.lower()
    
    # Default gas price configurations
    gas_configs = {
        'ethereum': {
            'slow': {'max_fee_per_gas': 30, 'max_priority_fee_per_gas': 1},
            'normal': {'max_fee_per_gas': 50, 'max_priority_fee_per_gas': 1.5},
            'fast': {'max_fee_per_gas': 100, 'max_priority_fee_per_gas': 2},
        },
        'polygon': {
            'slow': {'max_fee_per_gas': 100, 'max_priority_fee_per_gas': 30},
            'normal': {'max_fee_per_gas': 200, 'max_priority_fee_per_gas': 50},
            'fast': {'max_fee_per_gas': 300, 'max_priority_fee_per_gas': 80},
        },
        'avalanche': {
            'slow': {'max_fee_per_gas': 25, 'max_priority_fee_per_gas': 1},
            'normal': {'max_fee_per_gas': 35, 'max_priority_fee_per_gas': 2},
            'fast': {'max_fee_per_gas': 50, 'max_priority_fee_per_gas': 3},
        },
        'arbitrum': {
            'slow': {'max_fee_per_gas': 0.1, 'max_priority_fee_per_gas': 0.01},
            'normal': {'max_fee_per_gas': 0.3, 'max_priority_fee_per_gas': 0.1},
            'fast': {'max_fee_per_gas': 0.5, 'max_priority_fee_per_gas': 0.2},
        },
    }
    
    # For Solana, gas is different (compute units)
    if blockchain == 'solana':
        solana_configs = {
            'slow': {'compute_unit_price': 1000},
            'normal': {'compute_unit_price': 5000},
            'fast': {'compute_unit_price': 10000},
        }
        return solana_configs.get(priority, solana_configs['normal'])
    
    # For EVM chains
    if blockchain in gas_configs:
        return gas_configs[blockchain].get(priority, gas_configs[blockchain]['normal'])
    
    # Default to Ethereum if blockchain not found
    logger.warning(f"Gas configuration not found for blockchain {blockchain}, using Ethereum defaults")
    return gas_configs['ethereum'].get(priority, gas_configs['ethereum']['normal'])

def truncate_address(address: str, chars: int = 4) -> str:
    """
    Truncate an address for display purposes.
    
    Args:
        address: Address to truncate
        chars: Number of characters to keep at each end
        
    Returns:
        Truncated address (e.g., 0x1234...5678)
    """
    if not address:
        return ""
    
    if len(address) <= chars * 2 + 5:  # +5 for "0x" and "..."
        return address
    
    if address.startswith("0x"):
        return f"{address[:chars+2]}...{address[-chars:]}"
    else:
        return f"{address[:chars]}...{address[-chars:]}"

def normalize_blockchain_name(blockchain: str) -> str:
    """
    Normalize blockchain name to a standard format.
    
    Args:
        blockchain: Blockchain name to normalize
        
    Returns:
        Normalized blockchain name
    """
    blockchain = blockchain.lower()
    
    # Map of common variations to standard names
    blockchain_map = {
        'eth': 'ethereum',
        'ether': 'ethereum',
        'sol': 'solana',
        'matic': 'polygon',
        'poly': 'polygon',
        'avax': 'avalanche',
        'arb': 'arbitrum',
    }
    
    return blockchain_map.get(blockchain, blockchain) 