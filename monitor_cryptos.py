# -*- coding: UTF-8 -*-
import os
import unittest
import logging
import json
from datetime import datetime
import pandas as pd

import ccxt

from monitor import Monitor
from monitor_funds import MyFund


class MyCrypto(MyFund):
    def __init__(self, symbol, exchange_name='binance'):
        # For crypto, we use the symbol as the code (e.g., 'BTC/USDT')
        super().__init__(symbol)
        self.symbol = symbol
        self.exchange_name = exchange_name

    def download(self):
        # Initialize the exchange
        exchange_class = getattr(ccxt, self.exchange_name)
        exchange = exchange_class({
            'apiKey': '',  # Add your API key if needed
            'secret': '',  # Add your secret if needed
            'timeout': 30000,
            'enableRateLimit': True,
        })
        
        try:
            # Fetch all available OHLCV data (1 day timeframe)
            # Some exchanges have limits, so we'll try without limit first
            # If that fails, we'll fetch in chunks
            try:
                ohlcv = exchange.fetch_ohlcv(self.symbol, '1d')
            except Exception as e:
                logging.warning(f"Failed to fetch all data for {self.symbol}, trying with larger limit: {e}")
                # Try with a large limit if unlimited fetch fails
                ohlcv = exchange.fetch_ohlcv(self.symbol, '1d', limit=2000)
            
            if not ohlcv:
                raise Exception(f"No data returned for {self.symbol}")
            
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            logging.info(f"Fetched {len(df)} days of historical data for {self.symbol}")
            
            # Set name and worth (closing prices)
            self.name = self.symbol.replace('/', '_')  # e.g., BTC/USDT -> BTC_USDT
            self.worth = df['close'].tolist()
                
        except Exception as e:
            logging.error(f"Error fetching data for {self.symbol}: {e}")
            raise


class CryptoMonitor(Monitor):
    def __init__(self):
        super().__init__()
        self.subject = '加密货币小作手【{}】'.format(datetime.now().strftime(u"%Y{0}%m{1}%d{2}").format(*'年月日'))

    def filter_sort(self):
        now = datetime.now()
        date_format = '%Y-%m-%d %H:%M:%S'

        # load the snapshot from the json file below
        # the snapshot is a dictionary with symbol as the key
        # the value is a dictionary:
        # {
        #     'dateime': '2021-08-01 12:00:00',
        #     'N': -356,
        #     'cur': 0.1,
        #     'last_notified_time': '2021-08-01 12:00:00',
        # }
        snapshot_file = 'crypto_snapshot.json'
        snapshot = {}
        if os.path.exists(snapshot_file):
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
        
        for s in self.success:
            if s.code not in snapshot:
                # First time checking this crypto
                # use 2000-01-01 00:00:00 as the initial value
                snapshot[s.code] = {
                    'last_notified_time': '2000-01-01 00:00:00',
                }
            
            logging.info('{0},{1},{2},{3},{4:.0f}'.format(
                s.code, s.name, s.worth[-1], s.N, 100*s.cur))
            
            snapshot[s.code]['datetime'] = now.strftime(date_format)
            snapshot[s.code]['N'] = s.N
            snapshot[s.code]['cur'] = s.cur

        def is_interesting(s):
            # notify when any of the following conditions are met:
            # 1. lower than the past 200 days (crypto is more volatile)
            if s.N < -200:
                return True
            # 2. drawdown is greater than 30% (crypto threshold higher)
            if s.cur > 0.3:
                return True
            # 3. higher than the past 500 days
            if s.N > 500:
                return True
            # 4. reached the highest price
            if s.N == len(s.worth) - 1:
                return True
            return False

        results = []
        for s in self.success:
            if is_interesting(s):
                # filter out the cryptos notified within 3 days (shorter than stocks due to 24/7 trading)
                if (now - datetime.strptime(snapshot[s.code]['last_notified_time'], date_format)).days >= 3:
                    results.append(s)
                    snapshot[s.code]['last_notified_time'] = now.strftime(date_format)

        # output the snapshot to a json file
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False)

        results.sort(key=lambda x: x.N, reverse=True)
        return results


class TestCryptoMonitor(unittest.TestCase):
    '''测试：`python -m unittest monitor_cryptos`'''

    def setUp(self):
        # Code to set up the test environment
        self.monitor = CryptoMonitor()
        self.filter_sort = self.monitor.filter_sort
        self.s = self.create_crypto('BTC/USDT')
        self.monitor.success = [self.s]
        self.filter_sort()

    def tearDown(self):
        # Code to clean up after a test: delete crypto_snapshot.json if exists
        if os.path.exists('crypto_snapshot.json'):
            os.remove('crypto_snapshot.json')

    def create_crypto(self, symbol="BTC/USDT", N=0, cur=0, worth=[]):
        crypto = MyCrypto(symbol)
        crypto.N = N
        crypto.cur = cur
        crypto.worth = worth
        return crypto

    def test_filter_sort_empty(self):
        self.monitor.success = []
        self.assertEqual([], self.filter_sort())

    def test_filter_sort_is_interesting_0(self):
        self.s.N = -100
        self.s.cur = 0.1
        self.s.worth = [40000, 45000, 50000, 55000]
        self.assertEqual([], self.filter_sort())

    def test_filter_sort_is_interesting_1(self):
        s = self.s
        s.worth = [45000]  # Set current price
        s.N = -500
        self.assertEqual([s], self.filter_sort())

    def test_filter_sort_is_interesting_2(self):
        s = self.s
        s.worth = [45000]  # Set current price
        s.cur = 0.4
        self.assertEqual([s], self.filter_sort())

    def test_filter_sort_is_interesting_3(self):
        s = self.s
        s.worth = [40000, 50000, 60000]  # Set price history
        s.N = 2
        self.assertEqual([s], self.filter_sort())

    def test_filter_sort_dedup(self):
        s = self.s
        s.worth = [45000]  # Set current price
        s.N = -500
        self.assertEqual([s], self.filter_sort())
        self.assertEqual([], self.filter_sort())


def main(symbols, exchange_name='binance'):
    cryptos = [MyCrypto(symbol, exchange_name) for symbol in symbols]
    CryptoMonitor().process(cryptos)


if __name__ == '__main__':
    # Popular cryptocurrency pairs
    symbols = [
        # Major cryptocurrencies
        'BTC/USDT',     # Bitcoin
        'ETH/USDT',     # Ethereum
        'BNB/USDT',     # Binance Coin
        'XRP/USDT',     # Ripple
        'ADA/USDT',     # Cardano
        'SOL/USDT',     # Solana
        'DOGE/USDT',    # Dogecoin
        'DOT/USDT',     # Polkadot
        'MATIC/USDT',   # Polygon
        'SHIB/USDT',    # Shiba Inu
        'AVAX/USDT',    # Avalanche
        'ATOM/USDT',    # Cosmos
        'LINK/USDT',    # Chainlink
        'UNI/USDT',     # Uniswap
        'LTC/USDT',     # Litecoin
        # DeFi tokens
        'AAVE/USDT',    # Aave
        'COMP/USDT',    # Compound
        'SUSHI/USDT',   # SushiSwap
        'CRV/USDT',     # Curve
        'YFI/USDT',     # Yearn Finance
        # Layer 2 and new projects
        'ARB/USDT',     # Arbitrum
        'OP/USDT',      # Optimism
        'APT/USDT',     # Aptos
        'SUI/USDT',     # Sui
        'SEI/USDT',     # Sei
    ]
    
    main(symbols, 'binance')
