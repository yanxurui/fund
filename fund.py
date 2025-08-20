# -*- coding: UTF-8 -*-
import re
import logging
import unittest
from datetime import datetime
import execjs
import requests

from base_asset import BaseAsset


class Fund(BaseAsset):
    '''
    该策略并未直接输出买入或卖出的金额，而是输出一个强弱信号，由我自己决定
    self.N: 正数代表比过去N个交易日价格高，负数代表比过去N个交易日价格低
    '''
    def __init__(self, code):
        super().__init__(code)

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
    '''测试：`python -m unittest fund`'''
    def test_parse_current_rate(self):
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

    def test_buy_or_sell(self):
        fake_fund = Fund(0)
        buy_or_sell = fake_fund.buy_or_sell
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
        fake_fund = Fund(0)
        # empty
        fake_fund.worth = []
        self.assertEqual((0, 0), fake_fund.cal_mdd())
        # 1 point
        fake_fund.worth = [1]
        self.assertEqual((0, 0), fake_fund.cal_mdd())
        # 2 points
        fake_fund.worth = [0.8, 1]
        self.assertEqual((0, 0), fake_fund.cal_mdd())
        fake_fund.worth = [1, 0.8]
        self.assertEqual((0.2, 0.2), fake_fund.cal_mdd())
        # 3 points
        fake_fund.worth = [1, 0.8, 0.6]
        self.assertEqual((0.4, 0.4), fake_fund.cal_mdd())
        fake_fund.worth = [1, 0.8, 1.2]
        self.assertEqual((0.2, 0), fake_fund.cal_mdd())
        fake_fund.worth = [0.8, 1, 1.2]
        self.assertEqual((0, 0), fake_fund.cal_mdd())
        fake_fund.worth = [0.8, 1, 0.6]
        self.assertEqual((0.4, 0.4), fake_fund.cal_mdd())
        # 4 points
        fake_fund.worth = [1, 0.6, 1, 0.8]
        self.assertEqual((0.4, 0.2), fake_fund.cal_mdd())
        fake_fund.worth = [1, 0.8, 1, 0.6]
        self.assertEqual((0.4, 0.4), fake_fund.cal_mdd())
        # 最大回撤的开始和结束没有涉及到最高点或最低点
        fake_fund.worth = [0.8, 0.7, 1, 0.8, 1.2]
        self.assertEqual((0.2, 0), fake_fund.cal_mdd())

    def test_str(self):
        fake_fund = Fund(0)
        fake_fund.name = '123456789012'

        # scenario #1
        fake_fund.N = -1
        fake_fund.worth = [1.2, 0.5, 1, 0.9]
        fake_fund.mdd, fake_fund.cur = fake_fund.cal_mdd()
        f = str(fake_fund)
        print(f)
        self.assertFalse('🅢' in f)
        self.assertFalse('🅑' in f)
        self.assertFalse('🅜' in f)
        self.assertFalse(',' in f)

        # scenario #2
        fake_fund.N = -1
        fake_fund.worth = [1.5, 0.5, 1, 0.7]
        fake_fund.mdd, fake_fund.cur = fake_fund.cal_mdd()
        f = str(fake_fund)
        print(f)
        self.assertFalse('🅢' in f)
        self.assertFalse('🅑' in f)
        self.assertFalse('🅜' in f)
        self.assertTrue(',' in f)
        self.assertTrue('30%' in f)

        # scenario #3
        fake_fund.worth = [1.2, 0.8, 1, 0.6]
        fake_fund.mdd, fake_fund.cur = fake_fund.cal_mdd()
        f = str(fake_fund)
        print(f)
        self.assertFalse('🅢' in f)
        self.assertFalse('🅑' in f)
        self.assertTrue('🅜' in f)
        self.assertTrue(',' in f)

        # scenario #4
        fake_fund.N = -500
        f = str(fake_fund)
        print(f)
        self.assertFalse('🅢' in f)
        self.assertTrue('🅑' in f)
        self.assertTrue('🅜' in f)
        self.assertFalse(',' in f)

        # scenario #5
        fake_fund.N = -2
        fake_fund.worth = [0.8, 1, 0.6]
        fake_fund.mdd, fake_fund.cur = fake_fund.cal_mdd()
        f = str(fake_fund)
        print(f)
        self.assertTrue('🅢' in f)
        self.assertFalse('🅑' in f)
        self.assertTrue('🅜' in f)
        self.assertFalse(',' in f)