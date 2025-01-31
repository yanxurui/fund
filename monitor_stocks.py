# -*- coding: UTF-8 -*-
import os
import unittest
import logging
import json
from datetime import datetime

import efinance as ef

from monitor import Monitor
from monitor_funds import MyFund


class MyStock(MyFund):
    def __init__(self, code):
        super().__init__(code)
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

class StockMonitor(Monitor):
    def __init__(self):
        super().__init__()
        self.subject = '股票小作手【{}】'.format(datetime.now().strftime(u"%Y{0}%m{1}%d{2}").format(*'年月日'))

    def filter_sort(self):
        now = datetime.now()
        date_format = '%Y-%m-%d %H:%M:%S'

        # load the snapshot from the json file below
        # the snapshot is a dictionary with code as the key
        # the value is a dictionary:
        # {
        #     'dateime': '2021-08-01 12:00:00',
        #     'N': -356,
        #     'trading': True,
        #     'last_price': 100,
        #      'mdd': 0.2,
        #      'cur': 0.1,
        #     'last_notified_time': '2021-08-01 12:00:00',
        # }
        snapshot = {}
        if os.path.exists('snapshot.json'):
            with open('snapshot.json', 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
        for s in self.success:
            s.trading = False
            if s.code in snapshot:
                if s.last_price != snapshot[s.code]['last_price']:
                    # it's either because it's not trading time or the price has changed since last check
                    s.trading = True
            else:
                # trading will be False this is the first time to check
                # use 2000-01-01 00:00:00 as the initial value
                snapshot[s.code] = {
                    'last_notified_time': '2000-01-01 00:00:00',
                }
            logging.info('{0},{1},{2},{3},{4},{5:.0f}'.format(s.code, s.name, s.last_price['收盘'], s.trading, s.N, 100*s.cur))
            snapshot[s.code]['datetime'] = now.strftime(date_format)
            snapshot[s.code]['N'] = s.N
            snapshot[s.code]['trading'] = s.trading
            snapshot[s.code]['cur'] = s.cur
            snapshot[s.code]['last_price'] = s.last_price

        def is_interesting(s):
            # notify when any of the following conditions are met:
            if not s.trading:
                return False
            # 1. lower than the past 500 days
            if s.N < -500:
                return True
            # 2. drawdown is greater than 20%
            if s.cur > 0.2:
                return True
            # 3. reached the highest price
            if s.N == len(s.worth) - 1:
                return True
            return False

        results = []
        for s in self.success:
            if is_interesting(s):
                # filter out the stocks notified within a day
                if (now - datetime.strptime(snapshot[s.code]['last_notified_time'], date_format)).days >= 1:
                    results.append(s)
                    snapshot[s.code]['last_notified_time'] = now.strftime(date_format)

        # output the snapshot to a json file
        with open('snapshot.json', 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False)

        results.sort(key=lambda x: x.N, reverse=True)
        return results

class TestStockMonitor(unittest.TestCase):
    '''测试：`python -m unittest monitor_stocks`'''

    def setUp(self):
        # Code to set up the test environment
        self.monitor = StockMonitor()
        self.filter_sort = self.monitor.filter_sort
        self.s = self.create_stock('007')
        self.monitor.success = [self.s]
        self.filter_sort()

    def tearDown(self):
        # Code to clean up after a test: delte snapshot.json if exists
        if os.path.exists('snapshot.json'):
            os.remove('snapshot.json')

    def create_stock(self, code="007", N=0, cur=0, worth=[], last_price={'收盘': 1}):
        stock = MyStock(code)
        stock.N = N
        stock.cur = cur
        stock.worth = worth
        stock.last_price = last_price
        return stock

    def test_filter_sort_empty(self):
        self.monitor.success = []
        self.assertEqual([], self.filter_sort())

    def test_filter_sort_trading(self):
        self.filter_sort()
        self.assertEqual(False, self.s.trading)
        self.s.last_price = {'收盘': 2}
        self.filter_sort()
        self.assertEqual(True, self.s.trading)

    def test_filter_sort_is_interesting_0(self):
        self.s.N = -100
        self.s.cur = 0.1
        self.s.worth = [1, 2, 3, 4]
        self.assertEqual([], self.filter_sort())

    def test_filter_sort_is_interesting_1(self):
        s = self.s
        s.last_price = {'收盘': 2}
        s.N = -1000
        self.assertEqual([s], self.filter_sort())

    def test_filter_sort_is_interesting_2(self):
        s = self.s
        s.last_price = {'收盘': 2}
        s.cur = 0.5
        self.assertEqual([s], self.filter_sort())

    def test_filter_sort_is_interesting_3(self):
        s = self.s
        s.last_price = {'收盘': 3}
        s.N = 2
        s.worth = [1, 2, 3]
        self.assertEqual([s], self.filter_sort())

    def test_filter_sort_dedup(self):
        s = self.s
        s.last_price = {'收盘': 2}
        s.N = -1000
        self.assertEqual([s], self.filter_sort())
        self.assertEqual([], self.filter_sort())


def main(codes):
    StockMonitor().process([MyStock(c) for c in codes])

    # Need to close the session manually to avoid the error below:
    # sys:1: ResourceWarning: unclosed <socket object, fd=3, family=2, type=1, proto=6>
    ef.shared.session.close()

if __name__ == '__main__':
    codes = [
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
        'PDD',      # 拼多多
        '京东',     # 京东
        'BABA',     # 阿里巴巴
        # 港股
        '00700',    # 腾讯
        '01810',    # 小米
        '03690',    # 美团
        # A股
        '002594',   # 比亚迪
        # 其他
        '黄金ETF-SPDR',# 黄金
        'USDCNY',   # 美元人民币
        'IBIT',     # 比特币
    ]
    main(codes)
