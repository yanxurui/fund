# -*- coding: UTF-8 -*-
import logging
from abc import ABC, abstractmethod
import unittest


class BaseAsset(ABC):
    """Base class for all asset types"""
    def __init__(self, code):
        self.code = code
        self.name = ''
        self.worth = [] # Daily closing prices
        self.trading = False # Whether currently trading
        self.N = 0 # Records the output of the buy_or_sell strategy method, positive means buy amount, negative means sell
        self.mdd = None # Maximum drawdown
        self.cur = None # Current drawdown

    @property
    def current_price(self):
        """Get the current price (last value in worth)"""
        return self.worth[-1] if self.worth else None

    @property
    def daily_change_pct(self):
        """Get the daily change percentage vs previous close"""
        if len(self.worth) < 2:
            return 0.0
        prev_close = self.worth[-2]
        if not prev_close:  # avoid division by zero
            return 0.0
        return (self.worth[-1] - prev_close) / prev_close

    @property
    def is_at_historical_high(self):
        """Check if current price is at historical high (N == len(worth) - 1)"""
        if not self.worth:
            return False
        return self.N == len(self.worth) - 1

    @property
    def is_at_historical_low(self):
        """Check if current price is at historical low (N == -(len(worth) - 1))"""
        if len(self.worth) <= 1:
            return False  # Need at least 2 data points to have a meaningful low
        return self.N == -(len(self.worth) - 1)

    @property
    def was_at_high_yesterday(self):
        """Check if yesterday's price was the historical maximum"""
        if len(self.worth) < 2:
            return False
        return max(self.worth) == self.worth[-2]

    def __str__(self):
        """Default string representation with hardcoded thresholds for backward compatibility"""
        return self.format_with_config()

    def format_with_config(self, low_threshold=-300, drawdown_threshold=0.2, daily_change_threshold=0.1):
        """Format asset string with configurable thresholds"""
        k = '{0}({1})'.format(self.name, self.code)
        v = str(self.N)

        # return MAX when it reaches the highest in history
        if self.is_at_historical_high:
            v = 'MAX' # Historical high point
        elif self.is_at_historical_low:
            v = 'MIN' # Historical low point

        # 创历史新高后下跌则减仓
        # Circled Letter Symbols from https://altcodeunicode.com/alt-codes-circled-number-letter-symbols-enclosed-alphanumerics/
        if self.was_at_high_yesterday:
            v += '🅢' # sell

        # Add position when it falls to the valley bottom of the past N trading days (using configurable threshold)
        if self.N <= low_threshold:
            v += '🅑'

        # Add daily change percentage if it's above the threshold
        daily_change = self.daily_change_pct
        if abs(daily_change) >= daily_change_threshold:
            if v[-1].isdigit():
                v += ','
            # Use different symbols for rise and drop
            symbol = '⬆️' if daily_change >= 0 else '⬇️'
            v += '{:+.1f}%{}'.format(100*daily_change, symbol)

        # Maximum drawdown
        now = self.cur > 0 and self.cur == self.mdd
        # Current occurrence of historical maximum or significant drawdown (using configurable threshold)
        if now or self.cur > drawdown_threshold:
            if v[-1].isdigit():
                v += ','
            v += '{:.0f}%'.format(100*self.cur)
            if now:
                v += '🅜'
            else:
                v += '🅓'

        return '{0}:{1}'.format(k, v)

    def buy_or_sell(self, worth):
        '''This strategy does not directly output the amount to buy or sell, but outputs a strength signal for me to decide
    self.N: positive number represents price higher than past N trading days, negative number represents price lower than past N trading days'''
        N = 0
        if not worth:
            return 0
        worth = worth[::-1]
        current = worth[0]
        for i in range(1, len(worth)):
            if current > worth[i]:
                N = i
            else:
                break
        for i in range(1, len(worth)):
            if current < worth[i]:
                N = -i
            else:
                break
        return N

    def cal_mdd(self):
        if not self.worth:
            return 0, 0
        current_drawdown = 0
        max_drawdown = 0
        start = 0
        end = 0
        start_tmp = 0
        worth = self.worth[::-1]
        for i in range(1, len(worth)):
            if worth[i] < worth[start_tmp] or i == len(worth)-1:
                tmp_drawdown = 1 - worth[start_tmp] / max(worth[start_tmp:i+1])
                if start_tmp == 0:
                    current_drawdown = tmp_drawdown
                if tmp_drawdown > max_drawdown:
                    max_drawdown = tmp_drawdown
                    start = start_tmp
                    end = i - 1
                start_tmp = i
        logging.debug('Maximum drawdown: {:.1f}%'.format(100*max_drawdown))
        return round(max_drawdown, 4), round(current_drawdown, 4)

    def trade(self):
        retry = 1
        while retry >= 0:
            try:
                self.download()
                break
            except:
                logging.exception('failed to download data for asset {0}'.format(self.code))
                retry -= 1
                if retry < 0:
                    raise

        self.N = self.buy_or_sell(self.worth)
        self.mdd, self.cur = self.cal_mdd()
        return self.N

    @abstractmethod
    def download(self):
        """Download asset data - must be implemented by subclasses"""
        pass

class TestAsset(BaseAsset):
    """Concrete implementation of BaseAsset for testing"""
    def __init__(self, code):
        super().__init__(code)
        self.name = 'Test Asset'

    def download(self):
        """Dummy implementation for testing"""
        pass

class TestBaseAsset(unittest.TestCase):
    """Tests for BaseAsset formatting functionality"""

    def setUp(self):
        self.asset = TestAsset('TEST')

    def test_daily_change_pct_property(self):
        """Test the daily_change_pct property"""
        # Test with no data
        self.asset.worth = []
        self.assertEqual(0.0, self.asset.daily_change_pct)

        # Test with single value
        self.asset.worth = [100.0]
        self.assertEqual(0.0, self.asset.daily_change_pct)

        # Test with zero previous close (division by zero protection)
        self.asset.worth = [0.0, 100.0]
        self.assertEqual(0.0, self.asset.daily_change_pct)

        # Test positive change
        self.asset.worth = [100.0, 115.0]  # 15% increase
        self.assertAlmostEqual(0.15, self.asset.daily_change_pct, places=6)

        # Test negative change
        self.asset.worth = [100.0, 85.0]  # 15% decrease
        self.assertAlmostEqual(-0.15, self.asset.daily_change_pct, places=6)

        # Test no change
        self.asset.worth = [100.0, 100.0]  # 0% change
        self.assertEqual(0.0, self.asset.daily_change_pct)

    def test_historical_high_low_properties(self):
        """Test the is_at_historical_high and is_at_historical_low properties"""
        # Test with no data
        self.asset.worth = []
        self.asset.N = 0
        self.assertFalse(self.asset.is_at_historical_high)
        self.assertFalse(self.asset.is_at_historical_low)

        # Test with single data point
        self.asset.worth = [100.0]
        self.asset.N = 0  # N == len(worth) - 1 = 0
        self.assertTrue(self.asset.is_at_historical_high)
        self.assertFalse(self.asset.is_at_historical_low)  # Need at least 2 points for low

        # Test with multiple data points
        self.asset.worth = [100.0, 110.0, 120.0]  # 3 data points

        # Test historical high
        self.asset.N = 2  # N == len(worth) - 1 = 2
        self.assertTrue(self.asset.is_at_historical_high)
        self.assertFalse(self.asset.is_at_historical_low)

        # Test historical low
        self.asset.N = -2  # N == -(len(worth) - 1) = -2
        self.assertFalse(self.asset.is_at_historical_high)
        self.assertTrue(self.asset.is_at_historical_low)

        # Test neither high nor low
        self.asset.N = 1
        self.assertFalse(self.asset.is_at_historical_high)
        self.assertFalse(self.asset.is_at_historical_low)

    def test_was_at_high_yesterday_property(self):
        """Test the was_at_high_yesterday property"""
        # Test with no data
        self.asset.worth = []
        self.assertFalse(self.asset.was_at_high_yesterday)

        # Test with single data point
        self.asset.worth = [100.0]
        self.assertFalse(self.asset.was_at_high_yesterday)

        # Test when yesterday was NOT the historical high
        self.asset.worth = [100.0, 110.0, 120.0]  # Today (120) is highest
        self.assertFalse(self.asset.was_at_high_yesterday)

        # Test when yesterday WAS the historical high
        self.asset.worth = [100.0, 120.0, 115.0]  # Yesterday (120) was highest
        self.assertTrue(self.asset.was_at_high_yesterday)

        # Test with more complex scenario
        self.asset.worth = [90.0, 100.0, 120.0, 110.0]  # Yesterday (120) was highest
        self.assertTrue(self.asset.was_at_high_yesterday)

    def test_format_with_config_daily_change(self):
        """Test that daily change percentage is displayed when above threshold"""
        # Set up asset with significant daily change
        self.asset.worth = [100.0, 115.0]  # 15% increase
        self.asset.N = 5
        self.asset.cur = 0.05

        # Test formatting with daily change threshold of 10% - should show change
        formatted_with_change = self.asset.format_with_config(
            low_threshold=-300,
            drawdown_threshold=0.2,
            daily_change_threshold=0.10  # 10% threshold
        )
        self.assertIn('+15.0%⬆️', formatted_with_change)

        # Test formatting with daily change threshold of 20% - should NOT show change
        formatted_without_change = self.asset.format_with_config(
            low_threshold=-300,
            drawdown_threshold=0.2,
            daily_change_threshold=0.20  # 20% threshold
        )
        self.assertNotIn('⬆️', formatted_without_change)
        self.assertNotIn('⬇️', formatted_without_change)

        # Test negative daily change
        self.asset.worth = [100.0, 85.0]  # -15% decrease
        self.asset.N = -50

        formatted_negative = self.asset.format_with_config(
            low_threshold=-300,
            drawdown_threshold=0.2,
            daily_change_threshold=0.10  # 10% threshold
        )
        self.assertIn('-15.0%⬇️', formatted_negative)

    def test_format_with_config_thresholds(self):
        """Test different threshold configurations"""
        self.asset.worth = [100.0, 110.0]  # 10% increase
        self.asset.N = -400  # Below low threshold
        self.asset.cur = 0.25  # Above drawdown threshold

        # Test low threshold trigger
        result = self.asset.format_with_config(
            low_threshold=-300,  # Asset N=-400 is below this
            drawdown_threshold=0.3,
            daily_change_threshold=0.05
        )
        self.assertIn('🅑', result)  # Buy signal
        self.assertIn('+10.0%⬆️', result)  # Daily change
        self.assertNotIn('🅓', result)  # No drawdown signal (below threshold)

        # Test drawdown threshold trigger
        result = self.asset.format_with_config(
            low_threshold=-500,  # Asset N=-400 is above this
            drawdown_threshold=0.2,  # Asset cur=0.25 is above this
            daily_change_threshold=0.05
        )
        self.assertNotIn('🅑', result)  # No buy signal
        self.assertIn('🅓', result)  # Drawdown signal
        self.assertIn('+10.0%⬆️', result)  # Daily change

    def test_format_with_config_max_min(self):
        """Test MAX/MIN formatting"""
        # Test MAX case
        self.asset.worth = [100.0, 110.0, 120.0]
        self.asset.N = 2  # len(worth) - 1
        self.asset.cur = 0.0

        result = self.asset.format_with_config()
        self.assertIn('MAX', result)

        # Test MIN case
        self.asset.N = -2  # -(len(worth) - 1)

        result = self.asset.format_with_config()
        self.assertIn('MIN', result)

    def test_format_with_config_sell_signal(self):
        """Test sell signal when reaching new high then declining"""
        # Previous day was the historical max, today declined
        self.asset.worth = [100.0, 120.0, 115.0]  # max at index 1 (yesterday)
        self.asset.N = 0
        self.asset.cur = 0.0

        result = self.asset.format_with_config()
        self.assertIn('🅢', result)  # Sell signal

    def test_format_with_config_max_drawdown(self):
        """Test maximum drawdown vs regular drawdown symbols"""
        self.asset.worth = [100.0, 90.0]
        self.asset.N = 0
        self.asset.cur = 0.3  # 30% drawdown
        self.asset.mdd = 0.3  # This is also the max drawdown

        result = self.asset.format_with_config(drawdown_threshold=0.2)
        self.assertIn('🅜', result)  # Max drawdown symbol
        self.assertNotIn('🅓', result)  # Not regular drawdown symbol

        # Test regular drawdown (not max)
        self.asset.mdd = 0.4  # Max is higher than current

        result = self.asset.format_with_config(drawdown_threshold=0.2)
        self.assertIn('🅓', result)  # Regular drawdown symbol
        self.assertNotIn('🅜', result)  # Not max drawdown symbol

    def test_format_with_config_combined_signals(self):
        """Test multiple signals appearing together"""
        self.asset.worth = [100.0, 120.0, 85.0]  # New high then big drop
        self.asset.N = -400  # Low threshold trigger
        self.asset.cur = 0.3  # High drawdown
        self.asset.mdd = 0.3  # Max drawdown

        result = self.asset.format_with_config(
            low_threshold=-300,
            drawdown_threshold=0.2,
            daily_change_threshold=0.1
        )

        # Should show multiple signals
        self.assertIn('🅢', result)  # Sell (new high yesterday)
        self.assertIn('🅑', result)  # Buy (low threshold)
        self.assertIn('🅜', result)  # Max drawdown
        self.assertIn('-29.2%⬇️', result)  # Daily change down

        # Verify the complete expected format
        expected = 'Test Asset(TEST):-400🅢🅑-29.2%⬇️30%🅜'
        self.assertEqual(expected, result)

    def test_buy_or_sell(self):
        """Test the buy_or_sell strategy method"""
        buy_or_sell = self.asset.buy_or_sell
        self.assertEqual(0, buy_or_sell([]))
        self.assertEqual(0, buy_or_sell([1]))
        self.assertEqual(1, buy_or_sell([1, 2]))
        self.assertEqual(0, buy_or_sell([1, 2, 2]))
        self.assertEqual(2, buy_or_sell([1, 2, 3]))
        self.assertEqual(2, buy_or_sell([4, 1, 2, 3]))
        self.assertEqual(-1, buy_or_sell([2, 1]))
        self.assertEqual(0, buy_or_sell([2, 1, 1]))
        self.assertEqual(-2, buy_or_sell([1, 3, 2, 1]))

    def test_mdd(self):
        """Test maximum drawdown calculation"""
        # empty
        self.asset.worth = []
        self.assertEqual((0, 0), self.asset.cal_mdd())
        # 1 point
        self.asset.worth = [1]
        self.assertEqual((0, 0), self.asset.cal_mdd())
        # 2 points
        self.asset.worth = [0.8, 1]
        self.assertEqual((0, 0), self.asset.cal_mdd())
        self.asset.worth = [1, 0.8]
        self.assertEqual((0.2, 0.2), self.asset.cal_mdd())
        # 3 points
        self.asset.worth = [1, 0.8, 0.6]
        self.assertEqual((0.4, 0.4), self.asset.cal_mdd())
        self.asset.worth = [1, 0.8, 1.2]
        self.assertEqual((0.2, 0), self.asset.cal_mdd())
        self.asset.worth = [0.8, 1, 1.2]
        self.assertEqual((0, 0), self.asset.cal_mdd())
        self.asset.worth = [0.8, 1, 0.6]
        self.assertEqual((0.4, 0.4), self.asset.cal_mdd())
        # 4 points
        self.asset.worth = [1, 0.6, 1, 0.8]
        self.assertEqual((0.4, 0.2), self.asset.cal_mdd())
        self.asset.worth = [1, 0.8, 1, 0.6]
        self.assertEqual((0.4, 0.4), self.asset.cal_mdd())
        # The start and end of the maximum drawdown do not involve the highest or lowest points
        self.asset.worth = [0.8, 0.7, 1, 0.8, 1.2]
        self.assertEqual((0.2, 0), self.asset.cal_mdd())

    def test_str_scenarios(self):
        """Test string formatting scenarios"""
        self.asset.name = 'Test Asset Long Name'
        self.asset.code = 'TEST123'

        # scenario #1 - normal case with no special signals
        self.asset.N = -1
        self.asset.worth = [1.2, 0.5, 1, 0.9]
        self.asset.mdd, self.asset.cur = self.asset.cal_mdd()
        f = str(self.asset)
        self.assertNotIn('🅢', f)
        self.assertNotIn('🅑', f)
        self.assertNotIn('🅜', f)
        self.assertNotIn(',', f)

        # scenario #2 - with drawdown above threshold
        self.asset.N = -1
        self.asset.worth = [1.5, 0.5, 1, 0.7]
        self.asset.mdd, self.asset.cur = self.asset.cal_mdd()
        f = str(self.asset)
        self.assertNotIn('🅢', f)
        self.assertNotIn('🅑', f)
        self.assertNotIn('🅜', f)
        self.assertIn(',', f)
        self.assertIn('30%', f)

        # scenario #3 - with maximum drawdown
        self.asset.worth = [1.2, 0.8, 1, 0.6]
        self.asset.mdd, self.asset.cur = self.asset.cal_mdd()
        f = str(self.asset)
        self.assertNotIn('🅢', f)
        self.assertNotIn('🅑', f)
        self.assertIn('🅜', f)
        self.assertIn(',', f)

        # scenario #4 - with buy signal and max drawdown
        self.asset.N = -500
        f = str(self.asset)
        self.assertNotIn('🅢', f)
        self.assertIn('🅑', f)
        self.assertIn('🅜', f)
        self.assertNotIn(',', f)

        # scenario #5 - with sell signal and max drawdown
        self.asset.N = -2
        self.asset.worth = [0.8, 1, 0.6]
        self.asset.mdd, self.asset.cur = self.asset.cal_mdd()
        f = str(self.asset)
        self.assertIn('🅢', f)
        self.assertNotIn('🅑', f)
        self.assertIn('🅜', f)
        self.assertNotIn(',', f)


if __name__ == '__main__':
    unittest.main()