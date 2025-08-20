# -*- coding: UTF-8 -*-
import logging
from datetime import datetime

from fund import Fund


class FundBaseline(Fund):
    def __init__(self, code):
        """
        declear all instance members here even though it's not required by syntax
        """
        super().__init__(code)

    def __str__(self):
        """convert self to str"""
        k = '{0}({1})'.format(self.name[:10], self.code)
        v = str(self.N)
        return '{0}:{1}'.format(k, v)

    def buy_or_sell(self, worth):
        """strategy of trading
        worth是历史上每天的累计净值，worth[-1]是当前的估值。
        输出N表示买入或卖出（用负数表示）的金额。
        默认行为类似于定投，永不止盈。
        用你自己的策略覆盖这个方法。
        """
        return 1

    def trade(self):
        # download
        retry = 1 # retry only once
        while retry >= 0:
            try:
                self.download()
                break
            except:
                logging.exception('failed to download data for fund {0}'.format(self.code))
                retry -= 1
                if retry < 0:
                    raise

        # run the strategy
        self.N = self.buy_or_sell(self.worth)
        return self.N
