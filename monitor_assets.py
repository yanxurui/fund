# -*- coding: UTF-8 -*-
import os
import unittest
import logging
import json
from datetime import datetime
from abc import ABC, abstractmethod
import pandas as pd

import efinance as ef
import ccxt

from monitor import Monitor
from monitor_funds import MyFund


class AssetConfig:
    """Configuration for different asset types"""
    def __init__(self, name, snapshot_file, subject_prefix, notification_days, 
                 low_threshold, high_threshold, drawdown_threshold):
        self.name = name
        self.snapshot_file = snapshot_file
        self.subject_prefix = subject_prefix
        self.notification_days = notification_days
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.drawdown_threshold = drawdown_threshold


# Asset type configurations
ASSET_CONFIGS = {
    'stock': AssetConfig(
        name='股票',
        snapshot_file='snapshot.json',
        subject_prefix='股票小作手',
        notification_days=7,
        low_threshold=-500,
        high_threshold=1000,
        drawdown_threshold=0.2
    ),
    'crypto': AssetConfig(
        name='加密货币',
        snapshot_file='crypto_snapshot.json',
        subject_prefix='加密货币小作手',
        notification_days=3,
        low_threshold=-500,
        high_threshold=1000,
        drawdown_threshold=0.3
    )
}


class BaseAsset(MyFund, ABC):
    """Base class for all asset types"""
    def __init__(self, code, asset_type):
        super().__init__(code)
        self.asset_type = asset_type
        self.config = ASSET_CONFIGS[asset_type]
        
    @abstractmethod
    def download(self):
        """Download asset data - must be implemented by subclasses"""
        pass


class MyStock(BaseAsset):
    def __init__(self, code):
        super().__init__(code, 'stock')
        self.last_price = None

    def download(self):
        # fqt
            # 0: 不复权
            # 1: 前复权 (default)
            # 2: 后复权
            # 使用后复权因为东方财富返回的前复权历史数据可能包含负数，比如NVDA，会影响计算最大回撤
        hist = ef.stock.get_quote_history(self.code, fqt=2)
        self.name = hist.iloc[-1]['股票名称']
        self.worth = hist['收盘'].tolist() # The last row contains the current real-time price
        self.last_price = hist.iloc[-1].to_dict()


class MyCrypto(BaseAsset):
    def __init__(self, symbol, exchange_name='binance'):
        # For crypto, we use the symbol as the code (e.g., 'BTC/USDT')
        super().__init__(symbol, 'crypto')
        self.symbol = symbol
        self.exchange_name = exchange_name
        self.name = self.symbol.replace('/', '_')  # e.g., BTC/USDT -> BTC_USDT

    def download(self):
        # Initialize the exchange
        exchange_class = getattr(ccxt, self.exchange_name)
        exchange = exchange_class({
            # 'apiKey': '',  # Add your API key if needed
            # 'secret': '',  # Add your secret if needed
            'timeout': 30000,
            # 'enableRateLimit': True,
        })
        
        try:
            # Fetch all available OHLCV data (1 day timeframe)
            # We need to paginate to get all historical data since exchanges have limits
            all_ohlcv = []
            limit = 1000  # Maximum candles per request for most exchanges
            since = None  # Start from the earliest available data
            i = 0
            
            while True:
                i += 1
                try:
                    # Fetch a batch of data - a list of [timestamp, open, high, low, close, volume]
                    if since is None:
                        # First request - get the most recent data
                        ohlcv_batch = exchange.fetch_ohlcv(self.symbol, '1d', limit=limit)
                    else:
                        # Subsequent requests - get data from a specific timestamp
                        ohlcv_batch = exchange.fetch_ohlcv(self.symbol, '1d', since=since, limit=limit)
                    
                    if not ohlcv_batch:
                        logging.warning(f"No data returned for {self.symbol} on batch {i}. Stopping pagination.")
                        break

                    # Prepend older data to the beginning of our list
                    all_ohlcv = ohlcv_batch + all_ohlcv

                    # Check if we've reached the beginning
                    # In this case, this batch may overlap with the previous batch
                    if since != None and ohlcv_batch[0][0] > since:
                        logging.warning(f"We've reached the beginning of available data for {self.symbol}. Stopping pagination.")
                        break

                    # If we got less than the limit, we've reached the end
                    if len(ohlcv_batch) < limit:
                        logging.info(f"Reached the end of available data for {self.symbol} on batch {i}. Stopping pagination.")
                        break

                    # Set since to get older data
                    since = ohlcv_batch[0][0] - (24 * 60 * 60 * 1000 * limit)

                    # Convert since timestamp to human readable format for logging
                    since_date = datetime.fromtimestamp(since / 1000).strftime('%Y-%m-%d %H:%M:%S') if since else 'N/A'
                    first_candle_date = datetime.fromtimestamp(ohlcv_batch[0][0] / 1000).strftime('%Y-%m-%d')
                    last_candle_date = datetime.fromtimestamp(ohlcv_batch[-1][0] / 1000).strftime('%Y-%m-%d')
                    logging.info(f"Fetched {len(ohlcv_batch)} candles for {self.symbol} (batch {i}) from {first_candle_date} to {last_candle_date}, next since: {since_date}")
                        
                except Exception as e:
                    logging.exception(f"Error during pagination for {self.symbol}: {e}")
                    break
            
            if not all_ohlcv:
                raise Exception(f"No data returned for {self.symbol}")
            
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Remove duplicates and sort by timestamp
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            
            logging.info(f"Fetched {len(df)} days of historical data for {self.symbol} (from {df['datetime'].iloc[0].strftime('%Y-%m-%d')} to {df['datetime'].iloc[-1].strftime('%Y-%m-%d')})")
            
            # Set worth (closing prices)
            self.worth = df['close'].tolist()
                
        except Exception as e:
            logging.error(f"Error fetching data for {self.symbol}: {e}")
            raise


class UnifiedMonitor(Monitor):
    def __init__(self, asset_type):
        super().__init__()
        self.asset_type = asset_type
        self.config = ASSET_CONFIGS[asset_type]
        self.subject = f'{self.config.subject_prefix}【{datetime.now().strftime(u"%Y{0}%m{1}%d{2}").format(*"年月日")}】'

    def filter_sort(self):
        now = datetime.now()
        date_format = '%Y-%m-%d %H:%M:%S'

        # Load the snapshot from the appropriate json file
        snapshot = {}
        if os.path.exists(self.config.snapshot_file):
            with open(self.config.snapshot_file, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
        
        for s in self.success:
            # Handle different asset types for trading detection
            if self.asset_type == 'stock':
                s.trading = False
                if s.code in snapshot:
                    if s.last_price != snapshot[s.code].get('last_price'):
                        s.trading = True
                    else:
                        # it's either because it's not trading time or the price has changed since last check
                        pass
                else:
                    # trading will be False this is the first time to check
                    # use 2000-01-01 00:00:00 as the initial value
                    snapshot[s.code] = {
                        'last_notified_time': '2000-01-01 00:00:00',
                    }
            else:  # crypto - always trading 24/7
                s.trading = True
                if s.code not in snapshot:
                    # First time checking this crypto
                    # use 2000-01-01 00:00:00 as the initial value
                    snapshot[s.code] = {
                        'last_notified_time': '2000-01-01 00:00:00',
                    }
            
            # Log current state
            current_price = s.worth[-1]
            logging.info(f'{s.code},{s.name},{current_price},{s.trading},{s.N},{100*s.cur:.0f}')
            
            # Update snapshot
            snapshot[s.code]['datetime'] = now.strftime(date_format)
            snapshot[s.code]['N'] = s.N
            snapshot[s.code]['cur'] = s.cur
            if self.asset_type == 'stock':
                snapshot[s.code]['trading'] = s.trading
                snapshot[s.code]['last_price'] = s.last_price

        def is_interesting(s):
            # Check if asset is trading
            if not s.trading:
                return False
            
            # Use config thresholds for different conditions
            # 1. lower than the past N days
            if s.N < self.config.low_threshold:
                return True
            # 2. drawdown is greater than threshold
            if s.cur > self.config.drawdown_threshold:
                return True
            # 3. higher than the past N days
            if s.N > self.config.high_threshold:
                return True
            # 4. reached the highest price
            if s.N == len(s.worth) - 1:
                return True
            return False

        results = []
        for s in self.success:
            if is_interesting(s):
                # Filter out assets notified within the configured number of days
                days_since_last = (now - datetime.strptime(snapshot[s.code]['last_notified_time'], date_format)).days
                if days_since_last >= self.config.notification_days:
                    results.append(s)
                    snapshot[s.code]['last_notified_time'] = now.strftime(date_format)

        # Save the snapshot to the appropriate json file
        with open(self.config.snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False)

        results.sort(key=lambda x: x.N, reverse=True)
        return results


class UnifiedMonitorTestCase(unittest.TestCase):
    '''Base test class for unified monitor functionality'''

    def setUp(self):
        # Skip if this base class is being run directly
        if self.__class__.__name__ == 'UnifiedMonitorTestCase':
            self.skipTest("Abstract base class - should not be run directly")
            
        # Clean up any existing snapshot files
        for config in ASSET_CONFIGS.values():
            if os.path.exists(config.snapshot_file):
                os.remove(config.snapshot_file)
        
        # To be set by subclasses
        self.asset_type = None
        self.config = None
        self.monitor = None

    def tearDown(self):
        # Clean up snapshot files after tests
        for config in ASSET_CONFIGS.values():
            if os.path.exists(config.snapshot_file):
                os.remove(config.snapshot_file)

    def create_stock(self, code="007", N=0, cur=0, worth=[], last_price={'收盘': 1}):
        stock = MyStock(code)
        stock.N = N
        stock.cur = cur
        stock.worth = worth or [1]
        stock.last_price = last_price
        return stock

    def create_crypto(self, symbol="BTC/USDT", N=0, cur=0, worth=[]):
        crypto = MyCrypto(symbol)
        crypto.N = N
        crypto.cur = cur
        crypto.worth = worth or [45000]
        return crypto

    def _ensure_trading(self, asset):
        """Helper method to ensure asset is in trading state"""
        if self.asset_type == 'stock':
            # For stocks, we need to establish a price change to trigger trading
            self.monitor.success = [asset]
            self.monitor.filter_sort()  # First run establishes snapshot
            asset.last_price = {'收盘': asset.last_price['收盘'] + 1}  # Change price
        else:
            # Cryptos are always trading
            pass
    
    # Common test methods that work for both asset types
    def test_empty_results(self):
        """Empty success list should return empty results"""
        self.monitor.success = []
        results = self.monitor.filter_sort()
        self.assertEqual([], results)

    def test_not_interesting(self):
        """Asset with normal values should not be interesting"""
        asset = self.create_asset()
        asset.N = -100  # Within normal range for both assets
        asset.cur = 0.1  # Below drawdown threshold for both assets
        self._ensure_trading(asset)
            
        self.monitor.success = [asset]
        results = self.monitor.filter_sort()
        self.assertEqual([], results)

    def test_low_threshold(self):
        """Asset below low threshold should be interesting"""
        asset = self.create_asset()
        asset.N = self.config.low_threshold - 100  # Below threshold
        self._ensure_trading(asset)
            
        self.monitor.success = [asset]
        results = self.monitor.filter_sort()
        self.assertEqual([asset], results)

    def test_high_drawdown(self):
        """Asset with high drawdown should be interesting"""
        asset = self.create_asset()
        asset.cur = self.config.drawdown_threshold + 0.1  # Above drawdown threshold
        self._ensure_trading(asset)
            
        self.monitor.success = [asset]
        results = self.monitor.filter_sort()
        self.assertEqual([asset], results)

    def test_high_threshold(self):
        """Asset above high threshold should be interesting"""
        asset = self.create_asset()
        asset.N = self.config.high_threshold + 100  # Above threshold
        self._ensure_trading(asset)
            
        self.monitor.success = [asset]
        results = self.monitor.filter_sort()
        self.assertEqual([asset], results)

    def test_max_price(self):
        """Asset at historical max should be interesting"""
        asset = self.create_asset()
        asset.worth = [40, 50, 60]  # 3 data points
        asset.N = 2  # Index of last element (historical max)
        self._ensure_trading(asset)
            
        self.monitor.success = [asset]
        results = self.monitor.filter_sort()
        self.assertEqual([asset], results)

    def test_notification_deduplication(self):
        """Should not notify twice within notification period"""
        asset = self.create_asset()
        asset.N = self.config.low_threshold - 100  # Below threshold to make it interesting
        self._ensure_trading(asset)
            
        self.monitor.success = [asset]
        
        # First notification should succeed
        results = self.monitor.filter_sort()
        self.assertEqual([asset], results)
        
        # Second notification should be filtered out (within notification period)
        results = self.monitor.filter_sort()
        self.assertEqual([], results)


class TestStockMonitor(UnifiedMonitorTestCase):
    '''Tests for stock monitoring functionality'''

    def setUp(self):
        super().setUp()
        asset_type = 'stock'
        self.asset_type = asset_type
        self.config = ASSET_CONFIGS[asset_type]
        self.monitor = UnifiedMonitor(asset_type)
        self.create_asset = self.create_stock

    def test_trading_detection(self):
        """Stock-specific test: trading detection based on price changes"""
        asset = self.create_stock('007')
        self.monitor.success = [asset]
        
        # First run - should not be trading (same price)
        self.monitor.filter_sort()
        self.assertEqual(False, asset.trading)
        
        # Second run with different price - should be trading
        asset.last_price = {'收盘': 2}
        self.monitor.filter_sort()
        self.assertEqual(True, asset.trading)


class TestCryptoMonitor(UnifiedMonitorTestCase):
    '''Tests for crypto monitoring functionality'''

    def setUp(self):
        super().setUp()
        asset_type = 'crypto'
        self.asset_type = asset_type
        self.config = ASSET_CONFIGS[asset_type]
        self.monitor = UnifiedMonitor(asset_type)
        self.create_asset = self.create_crypto

    def test_always_trading(self):
        """Crypto-specific test: should always be trading (24/7 markets)"""
        asset = self.create_crypto('BTC/USDT')
        self.monitor.success = [asset]
        
        # Crypto should always be trading
        self.monitor.filter_sort()
        self.assertEqual(True, asset.trading)


def main_stocks(codes):
    """Monitor stock assets"""
    UnifiedMonitor('stock').process([MyStock(c) for c in codes])
    
    # Need to close the session manually to avoid the error below:
    # sys:1: ResourceWarning: unclosed <socket object, fd=3, family=2, type=1, proto=6>
    ef.shared.session.close()


def main_cryptos(symbols, exchange_name='binance'):
    """Monitor crypto assets"""
    cryptos = [MyCrypto(symbol, exchange_name) for symbol in symbols]
    UnifiedMonitor('crypto').process(cryptos)


if __name__ == '__main__':
    # Stock codes from original monitor_stocks.py
    stock_codes = [
        # 美股
        'NDX',      # 纳指ETF
        'SPY',      # 标普500
        'DJI',      # 道琼斯
        'MSFT',     # 微软
        'NVDA',     # 英伟达
        'TSLA',     # 特斯拉
        'AAPL',     # 苹果
        'GOOG',     # 谷歌
        'AMZN',     # 亚马逊
        'META',     # Meta
        'NFLX',     # Netflix
        'TSM',      # 台积电
        'QCOM',     # 高通
        'COST',     # 好市多
        'TM',       # 丰田
        # 中概
        'PDD',      # 拼多多
        '京东',     # 京东
        'BABA',     # 阿里巴巴
        # 港股
        'HSI',      # 恒生指数
        '00700',    # 腾讯
        '01810',    # 小米
        '03690',    # 美团
        # A股
        'SZZS',     # 上证指数
        '000300',   # 沪深300
        '002594',   # 比亚迪
        '002352',   # 顺丰
        # 债券
        'US10Y',   # 美债10年
        'CN10Y',   # 国债10年
        # 其他
        '黄金ETF-SPDR', # 黄金
        'USDCNY',   # 美元人民币
        'IBIT',     # 比特币
    ]
    
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
    
    print("Monitoring stocks...")
    main_stocks(stock_codes)
    print("\nMonitoring cryptos...")
    main_cryptos(crypto_symbols, 'binance')