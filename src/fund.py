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
    This strategy does not directly output the amount to buy or sell, but outputs a strength signal for me to decide
    self.N: positive number represents price higher than past N trading days, negative number represents price lower than past N trading days
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
    '''Test: `python -m unittest fund`'''
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