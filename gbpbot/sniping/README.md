# Memecoin Sniping Module

This module provides high-performance sniping capabilities for memecoins on various blockchains, with specialized focus on Solana for ultra-fast execution.

## Overview

The sniping module is designed to detect, analyze, and automatically trade new memecoin opportunities with sophisticated entry and exit strategies. It integrates closely with other GBPBot components such as blockchain clients, token detection systems, and wallet tracking to provide a comprehensive sniping solution.

## Features

- **Real-time Token Detection**: Monitors multiple sources including DEXs, mempool, and APIs for new token launches and liquidity events
- **Smart Money Tracking**: Identifies and follows wallets with a history of profitable trades
- **Advanced Opportunity Scoring**: Multi-factor analysis to identify the most promising opportunities
- **Risk Management**: Position sizing based on token risk profile and opportunity score
- **Automated Entry/Exit**: Multi-stage take profit and stop loss mechanisms
- **MEV Protection**: Uses priority fees and bundle transactions for protection against frontrunning
- **Performance Analytics**: Detailed tracking of sniping performance and profitability metrics

## Components

### SolanaMemecoinSniper

Specialized implementation for the Solana blockchain with the following capabilities:

- Jito MEV protection bundles
- Priority fee optimization
- Sub-second transaction execution
- Advanced liquidity analysis
- Smart stop-loss mechanisms

## Usage

### Basic Usage

```python
from gbpbot.sniping.memecoin_sniper import SolanaMemecoinSniper
import asyncio

async def main():
    # Initialize the sniper with configuration
    sniper = SolanaMemecoinSniper("config/solana_config.json")
    
    # Start the sniper
    await sniper.start()
    
    # Run for a specific duration or until manually stopped
    try:
        # Run for 60 minutes
        await asyncio.sleep(60 * 60)
    finally:
        # Ensure proper shutdown
        await sniper.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Example Script

For a more comprehensive example, see `example_solana_sniper.py` which demonstrates:

- Configuration loading and overriding
- Command-line argument handling
- Test mode execution
- Signal handling for graceful shutdown
- Performance monitoring and reporting

Run the example with:

```bash
python -m gbpbot.sniping.example_solana_sniper --test
```

### Testing

The module includes a test suite that verifies core functionality:

```bash
python -m gbpbot.sniping.test_memecoin_sniper
```

## Configuration

The sniping module relies on the Solana configuration file (`config/solana_config.json`). Key configuration sections include:

### Sniping Settings

```json
"sniping": {
    "trade_settings": {
        "default_slippage": 0.5,
        "emergency_slippage": 5.0,
        "min_liquidity_usd": 50000,
        "min_volume_usd": 100000,
        "auto_approve": true
    },
    "execution": {
        "use_bundled_transactions": true,
        "use_priority_fees": true,
        "retries_on_failure": 3,
        "use_jito_bundle": true
    },
    "profitability": {
        "take_profit_levels": [
            {"multiplier": 2.0, "percentage": 25},
            {"multiplier": 5.0, "percentage": 50},
            {"multiplier": 10.0, "percentage": 100}
        ],
        "stop_loss": {
            "enabled": true,
            "percentage": 30
        }
    }
}
```

### Security Settings

```json
"security": {
    "max_allocation_per_token_usd": 1000,
    "suspicious_patterns": [
        "rug", "scam", "honeypot", "fake", "test"
    ],
    "auto_blacklist": true,
    "private_transactions": true
}
```

## Integration with Other Modules

The sniping module integrates with:

- **Blockchain Clients**: For transaction execution and token analysis
- **Memecoin Detector**: For identifying new token opportunities
- **Wallet Tracker**: For monitoring smart money wallets and transaction history
- **API Adapters**: For gathering market data from external sources

## Best Practices

1. **Start with Test Mode**: Always use the `--test` flag when first running the sniper
2. **Manage Risk**: Adjust `max_allocation_per_token_usd` based on your risk tolerance
3. **Optimize for Speed**: For Solana, use multiple RPC providers with Jito priority
4. **Regular Monitoring**: Check performance metrics and adjust strategies accordingly
5. **Wallet Security**: Use burner wallets for sniping operations rather than your main wallet

## Troubleshooting

- **Connection Issues**: Verify RPC configurations and try multiple providers
- **Transaction Failures**: Adjust gas/priority fee settings, especially during high network congestion
- **Missing Opportunities**: Lower minimum score thresholds or adjust detection parameters
- **Excessive Gas Costs**: Tune priority fee multipliers in configuration

## MEV Protection

The sniper now incorporates advanced MEV (Maximal Extractable Value) protection via Jito bundles, providing several key benefits:

- **Prevention of frontrunning**: Transactions are bundled and submitted directly to block builders, bypassing the public mempool
- **Reliable execution**: Higher probability of successful transaction execution in competitive token launches
- **Transaction privacy**: Reduced visibility of transaction intent before execution
- **Optimized priority fees**: Automatically calculates optimal priority fees based on network conditions

### How Jito Bundle Protection Works

1. **Transaction Bundling**: Multiple transactions are bundled together and submitted as a single unit
2. **Direct Block Builder Submission**: Bundles are sent directly to Jito block builders, bypassing the public mempool
3. **Fallback Mechanism**: If Jito submission fails, the system automatically falls back to regular transaction submission
4. **Dynamic Fee Optimization**: Priority fees are dynamically adjusted based on network congestion

### Configuring MEV Protection

MEV protection can be configured in `config/solana_sniper_config.yaml`:

```yaml
# Enable/disable Jito bundles
jito_enabled: true

# Jito authentication token (set via environment variable)
jito_auth_token: "${JITO_AUTH_TOKEN}"

# Use Jito for entry transactions (recommended)
use_jito_for_entry: true

# Use Jito for exit transactions (optional)
use_jito_for_exit: false

# Value threshold to use Jito for exits (in USDC)
jito_exit_threshold: 100
```

For optimal protection:
1. Enable `jito_enabled`
2. Set your Jito auth token via environment variable
3. Enable `use_jito_for_entry` for entry transactions
4. Consider enabling `use_jito_for_exit` for high-value positions

## Advanced Transaction Execution

The sniper implements several transaction execution strategies:

1. **Standard Transactions**: Regular transaction submission with optimized priority fees
2. **Jito Bundle Transactions**: MEV-protected transactions bundled and submitted via Jito
3. **Fallback Execution**: Automatic fallback to standard transactions if MEV protection fails

Example of executing a transaction with MEV protection:

```python
from gbpbot.sniping.memecoin_sniper import SolanaMemecoinSniper

# Initialize sniper
sniper = SolanaMemecoinSniper("config/solana_sniper_config.yaml")
await sniper.connect()

# Execute entry with MEV protection
result = await sniper.execute_entry_transaction(
    token_address="TokenAddressHere", 
    amount_usdc=100,
    slippage=1.5
)

# Check if transaction was executed with MEV protection
if result["success"] and result["position"]["mev_protected"]:
    print(f"Successfully entered position with MEV protection: {result['signature']}")
else:
    print(f"Transaction failed or executed without MEV protection")
```

## Performance Considerations

When using Jito bundles for MEV protection:

- **API Rate Limits**: Be aware of Jito API rate limits when executing multiple transactions
- **Cost Considerations**: Jito bundles may incur additional costs through priority fees
- **Authentication**: A valid Jito authentication token is required 