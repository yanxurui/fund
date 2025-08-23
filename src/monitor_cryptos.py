# -*- coding: UTF-8 -*-
from monitor_with_criteria import MonitorWithCriteria, MonitorConfig
from crypto import Crypto


def main_cryptos(symbols):
    """Monitor crypto assets"""
    config = MonitorConfig(
        asset_type='crypto',
        subject_prefix='加密货币小作手',
        snapshot_file='crypto_snapshot.json',
        notification_days=3,
        drawdown_threshold=0.3
    )
    
    # Handle case where symbols is a list of tuples (symbol, exchange)
    # or a simple list of symbols with default exchange
    cryptos = []
    for item in symbols:
        if isinstance(item, tuple):
            symbol, exchange = item
            cryptos.append(Crypto(symbol, exchange))
        else:
            symbol = item
            cryptos.append(Crypto(symbol))
    
    MonitorWithCriteria(config).process(cryptos)


if __name__ == '__main__':
    # Crypto symbols - can be simple strings or (symbol, exchange) tuples
    crypto_symbols = [
        # Major cryptocurrencies
        'BTC/USDT',     # Bitcoin
        'ETH/USDT',     # Ethereum
        ('BNB/USDT', 'binance'),     # Binance Coin (using OKX due to geo-restrictions)
        'XRP/USDT',     # Ripple
        'ADA/USDT',     # Cardano
        'SOL/USDT',     # Solana
        'DOGE/USDT',    # Dogecoin
        
        # OKB from OKX exchange (native token)
        ('OKB/USDT', 'okx'),     # OKB on OKX exchange

        # Other symbols
        # 'DOT/USDT',     # Polkadot
        # 'MATIC/USDT',   # Polygon
        # 'SHIB/USDT',    # Shiba Inu
        # 'AVAX/USDT',    # Avalanche
        # 'ATOM/USDT',    # Cosmos
        'LINK/USDT',    # Chainlink
        # 'UNI/USDT',     # Uniswap
        'LTC/USDT',     # Litecoin
        # # DeFi tokens
        # 'AAVE/USDT',    # Aave
        # 'COMP/USDT',    # Compound
        # 'SUSHI/USDT',   # SushiSwap
        # 'CRV/USDT',     # Curve
        # 'YFI/USDT',     # Yearn Finance
        # # Layer 2 and new projects
        # 'ARB/USDT',     # Arbitrum
        # 'OP/USDT',      # Optimism
        # 'APT/USDT',     # Aptos
        # 'SUI/USDT',     # Sui
        # 'SEI/USDT',     # Sei
    ]

    print("Monitoring cryptos...")
    main_cryptos(crypto_symbols)  # Default exchange for simple symbols