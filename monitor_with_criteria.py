# -*- coding: UTF-8 -*-
import os
import unittest
import logging
import json
from datetime import datetime

from monitor import Monitor


class MonitorConfig:
    """Configuration for monitoring different asset types"""
    def __init__(
            self,
            asset_type,
            subject_prefix,
            snapshot_file="snapshot.json",
            notification_days=7,
            low_threshold=-500,
            high_threshold=1000,
            drawdown_threshold=0.2,
            daily_change_threshold=0.15
    ):
        self.asset_type = asset_type  # e.g. 'stock' or 'crypto'
        self.snapshot_file = snapshot_file
        self.subject_prefix = subject_prefix
        self.notification_days = notification_days
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.drawdown_threshold = drawdown_threshold
        self.daily_change_threshold = daily_change_threshold  # abs pct change vs previous close to trigger


class MonitorWithCriteria(Monitor):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.asset_type = config.asset_type
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

            # 0. large single-day move (>= configured threshold vs previous close)
            if len(s.worth) >= 2:
                prev_close = s.worth[-2]
                if prev_close:  # avoid division by zero
                    day_change = (s.worth[-1] - prev_close) / prev_close
                    if abs(day_change) >= self.config.daily_change_threshold:
                        logging.info(f"{s.code} triggered daily move {day_change:.2%} (threshold {self.config.daily_change_threshold:.0%})")
                        return True

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


class MonitorWithCriteriaTestCase(unittest.TestCase):
    '''Base test class for monitor with criteria functionality'''

    def setUp(self):
        # Skip if this base class is being run directly
        if self.__class__.__name__ == 'MonitorWithCriteriaTestCase':
            self.skipTest("Abstract base class - should not be run directly")

        # To be set by subclasses
        self.asset_type = None
        self.config = None
        self.monitor = None

    def tearDown(self):
        # To be implemented by subclasses for cleanup
        pass

    def create_stock(self, code="007", N=0, cur=0, worth=[], last_price={'收盘': 1}):
        from stock import Stock
        stock = Stock(code)
        stock.N = N
        stock.cur = cur
        stock.worth = worth or [1]
        stock.last_price = last_price
        return stock

    def create_crypto(self, symbol="BTC/USDT", N=0, cur=0, worth=[]):
        from crypto import Crypto
        crypto = Crypto(symbol)
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


class TestStockMonitor(MonitorWithCriteriaTestCase):
    '''Tests for stock monitoring functionality'''

    def setUp(self):
        super().setUp()
        
        asset_type = 'stock'
        self.asset_type = asset_type
        self.config = MonitorConfig(
            asset_type='stock',
            subject_prefix='股票小作手'
        )
        self.monitor = MonitorWithCriteria(self.config)
        self.create_asset = self.create_stock
        
        # Clean up stock snapshot file
        if os.path.exists(self.config.snapshot_file):
            os.remove(self.config.snapshot_file)

    def tearDown(self):
        # Clean up stock snapshot file after test
        if os.path.exists(self.config.snapshot_file):
            os.remove(self.config.snapshot_file)

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


class TestCryptoMonitor(MonitorWithCriteriaTestCase):
    '''Tests for crypto monitoring functionality'''

    def setUp(self):
        super().setUp()
        
        asset_type = 'crypto'
        self.asset_type = asset_type
        self.config = MonitorConfig(
            asset_type='crypto',
            subject_prefix='加密货币小作手',
            snapshot_file='crypto_snapshot.json',
            notification_days=3,
            drawdown_threshold=0.3
        )
        self.monitor = MonitorWithCriteria(self.config)
        self.create_asset = self.create_crypto
        
        # Clean up crypto snapshot file
        if os.path.exists(self.config.snapshot_file):
            os.remove(self.config.snapshot_file)

    def tearDown(self):
        # Clean up crypto snapshot file after test
        if os.path.exists(self.config.snapshot_file):
            os.remove(self.config.snapshot_file)

    def test_always_trading(self):
        """Crypto-specific test: should always be trading (24/7 markets)"""
        asset = self.create_crypto('BTC/USDT')
        self.monitor.success = [asset]

        # Crypto should always be trading
        self.monitor.filter_sort()
        self.assertEqual(True, asset.trading)