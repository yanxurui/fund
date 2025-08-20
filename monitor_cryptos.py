# -*- coding: UTF-8 -*-
from monitor_with_criteria import MonitorWithCriteria
from crypto import Crypto


def main_cryptos(symbols, exchange_name='binance'):
    """Monitor crypto assets"""
    cryptos = [Crypto(symbol, exchange_name) for symbol in symbols]
    MonitorWithCriteria('crypto').process(cryptos)


if __name__ == '__main__':
    # Crypto symbols from original monitor_cryptos.py
    crypto_symbols = [
        # Major cryptocurrencies
        'BTC/USDT',     # Bitcoin
        'ETH/USDT',     # Ethereum
        # 'BNB/USDT',     # Binance Coin
        # 'XRP/USDT',     # Ripple
        # 'ADA/USDT',     # Cardano
        'SOL/USDT',     # Solana
        'DOGE/USDT',    # Dogecoin
        # 'DOT/USDT',     # Polkadot
        # 'MATIC/USDT',   # Polygon
        # 'SHIB/USDT',    # Shiba Inu
        # 'AVAX/USDT',    # Avalanche
        # 'ATOM/USDT',    # Cosmos
        'LINK/USDT',    # Chainlink
        # 'UNI/USDT',     # Uniswap
        # 'LTC/USDT',     # Litecoin
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
    main_cryptos(crypto_symbols, 'binance')