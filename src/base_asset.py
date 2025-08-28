# -*- coding: UTF-8 -*-
import logging
from abc import ABC, abstractmethod


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

    def __str__(self):
        """Default string representation with hardcoded thresholds for backward compatibility"""
        return self.format_with_config()

    def format_with_config(self, low_threshold=-300, drawdown_threshold=0.2, daily_change_threshold=0.1):
        """Format asset string with configurable thresholds"""
        k = '{0}({1})'.format(self.name, self.code)
        v = str(self.N)

        # return MAX when it reaches the highest in history
        if self.N == len(self.worth) - 1:
            v = 'MAX' # Historical high point
        elif self.N == -(len(self.worth) - 1):
            v = 'MIN' # Historical low point

        # 创历史新高后下跌则减仓
        # Circled Letter Symbols from https://altcodeunicode.com/alt-codes-circled-number-letter-symbols-enclosed-alphanumerics/
        if len(self.worth) >= 2 and max(self.worth) == self.worth[-2]:
            v += '🅢' # sell

        # Add position when it falls to the valley bottom of the past N trading days (using configurable threshold)
        if self.N <= low_threshold:
            v += '🅑'

        # Maximum drawdown
        now = self.cur > 0 and self.cur == self.mdd
        # Current occurrence of historical maximum or significant drawdown (using configurable threshold)
        if now or self.cur > drawdown_threshold:
            if v[-1].isdigit():
                v += ','
            v += '{:.0f}%'.format(100*self.cur)
        if now:
            v += '🅜'

        # Add daily change percentage if it's above the threshold
        if len(self.worth) >= 2:
            prev_close = self.worth[-2]
            if prev_close:  # avoid division by zero
                daily_change = (self.worth[-1] - prev_close) / prev_close
                if abs(daily_change) >= daily_change_threshold:
                    if v[-1].isdigit():
                        v += ','
                    # Use different symbols for rise and drop
                    symbol = '⬆️' if daily_change >= 0 else '⬇️'
                    v += '{:+.1f}%{}'.format(100*daily_change, symbol)

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