# -*- coding: UTF-8 -*-
import re
import unittest
import traceback
import logging
from datetime import datetime

import execjs
import requests

class Fund:
    def __init__(self, code):
        """
        declear all instance members here even though it's not required by syntax
        """
        self.code = code # 基金代码
        self.name = '' # 基金名字
        self.worth = [] # 历史累计净值
        self.trading = False # 当前是否正在交易
        self.N = 0 # 记录策略方法buy_or_sell的输出，正数表示买入的金额，负数表示卖出

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

    def download(self):
        """get historical daily prices including today's if available"""
        code = self.code
        # 1. get the history daily price
        url = 'http://fund.eastmoney.com/pingzhongdata/{0}.js'.format(code)
        r = requests.get(url, timeout=10)
        assert r.status_code == 200
        jsContent = execjs.compile(r.text)
        name = jsContent.eval('fS_name')
        logging.info('{0}:{1}'.format(code, name))
        logging.info('url1: {0}'.format(url))
        # 基金的累计净值，代表基金从成立以来的整体收益情况，比较直观和全面地反映基金在运作期间的历史表现
        ACWorthTrend = jsContent.eval('Data_ACWorthTrend')
        worth = [w for t,w in ACWorthTrend]

        # 2. get today's real-time price
        url = 'http://fundgz.1234567.com.cn/js/{0}.js'.format(code)
        logging.info('url2: {0}'.format(url))
        r = requests.get(url, timeout=10)
        assert r.status_code == 200
        rate = Fund.parse_current_rate(r.text)
        if rate is not None:
            self.trading = True
            worth.append(worth[-1] * (1 + rate/100))
        self.name = name
        self.worth = worth

    @staticmethod
    def parse_current_rate(text):
        rate_match = re.search(r'"gszzl":"(-?\d+(\.\d+)?)"', text)
        datetime_match = re.search(r'"gztime":"(\d+-\d+-\d+ \d+:\d+)"', text)
        if rate_match is None or datetime_match is None:
            logging.error('invalid response: {0}'.format(text))
        else:
            dt_str = datetime_match.group(1)
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            if dt.date() == datetime.today().date() and dt.time().hour != 15:
                return float(rate_match.group(1))
            else:
                logging.warning('real-time price is not available: {0}'.format(dt_str))
        # there are 2 cases:
        # 1. QDII
        # 2. NOT QDII
        #   a) on a non-trading day, the value of the last trading day has been updated
        #   b) on a trading day but after 15:00, today's value has probably not been updated yet. BUG: This is misleading.
        return None

class TestFund(unittest.TestCase):
    def test_parse_current(self):
        parse_current_rate = Fund.parse_current_rate
        # a normal case
        date = datetime.now().strftime("%Y-%m-%d")
        sample = 'jsonpgz({"fundcode":"161725","name":"招商中证白酒指数分级","jzrq":"2020-11-10","dwjz":"1.1808","gsz":"1.1826","gszzl":"0.15","gztime":"%s 14:40"});' % date
        self.assertEqual(0.15, parse_current_rate(sample))
        # empty
        sample = 'jsonpgz();'
        self.assertEqual(None, parse_current_rate(sample))
        # not in trading time
        sample = 'jsonpgz({"gszzl":"0.15","gztime":"2020-11-11 15:00"});'
        self.assertEqual(None, parse_current_rate(sample))
        # test regex
        sample = 'jsonpgz({"gszzl":"1","gztime":"%s 14:40"});' % date
        self.assertEqual(1, parse_current_rate(sample))
        # test regex
        sample = 'jsonpgz({"gszzl":"10","gztime":"%s 14:40"});' % date
        self.assertEqual(10, parse_current_rate(sample))
        # test regex
        sample = 'jsonpgz({"gszzl":"1.23","gztime":"%s 14:40"});' % date
        self.assertEqual(1.23, parse_current_rate(sample))
        # test regex
        sample = 'jsonpgz({"gszzl":"-0.1","gztime":"%s 14:40"});' % date
        self.assertEqual(-0.1, parse_current_rate(sample))

