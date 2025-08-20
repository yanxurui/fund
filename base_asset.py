# -*- coding: UTF-8 -*-
import logging
from abc import ABC, abstractmethod


class BaseAsset(ABC):
    """Base class for all asset types"""
    def __init__(self, code):
        self.code = code
        self.name = ''
        self.worth = []
        self.trading = False
        self.N = 0
        self.mdd = None
        self.cur = None
        
    def __str__(self):
        k = '{0}({1})'.format(self.name, self.code)
        v = str(self.N)
        if self.worth and len(self.worth) > 1:
            if self.N == len(self.worth) - 1:
                v = 'MAX'
            elif self.N == -(len(self.worth) - 1):
                v = 'MIN'
            if len(self.worth) >= 2 and max(self.worth) == self.worth[-2]:
                v += '🅢'
        if self.N <= -300:
            v += '🅑'
        if self.cur is not None and self.mdd is not None:
            now = self.cur > 0 and self.cur == self.mdd
            if now or self.cur > 0.2:
                if v[-1].isdigit():
                    v += ','
                v += '{:.0f}%'.format(100*self.cur)
            if now:
                v += '🅜'
        return '{0}:{1}'.format(k, v)

    def buy_or_sell(self, worth):
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
        logging.debug('最大回撤：{:.1f}%'.format(100*max_drawdown))
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