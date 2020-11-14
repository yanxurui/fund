# -*- coding: UTF-8 -*-
import os
import re
import time
import unittest
import traceback
import logging
from datetime import datetime

import execjs
import requests
import quip

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s')


def send_notification(msg):
    """send notifiation via quip"""
    client = quip.QuipClient(
        access_token="YURJQU1BaGJSQ0g=|1635522342|nvZ5YsJ03DDUrt8b5b7hKbIJ2/0L7dBS41GfEWZZ6rI=")
    r = client.new_message(thread_id='XPdAAAdjxIV', content=msg)

class Fund:
    IsTrading = False

    def __init__(self, fund_code):
        self.fund_code = fund_code
        self.name, self.worth = self.download(fund_code)
        # current price is higher than the past N days
        self.N = self.high_or_low(self.worth)

    @classmethod
    def download(cls, fund_code):
        """get historical daily prices including today's if available"""
        # 1. get the history daily price
        url = 'http://fund.eastmoney.com/pingzhongdata/{0}.js?v={1}'.format(
            fund_code, time.strftime("%Y%m%d%H%M%S", time.localtime()))
        r = requests.get(url)
        assert r.status_code == 200
        jsContent = execjs.compile(r.text)
        name = jsContent.eval('fS_name')
        logging.info('{0}:{1}'.format(fund_code, name))
        logging.info('url1: {0}'.format(url))
        ACWorthTrend = jsContent.eval('Data_ACWorthTrend')
        worth = [w for t,w in ACWorthTrend]

        # 2. get today's real-time price
        url = 'http://fundgz.1234567.com.cn/js/{0}.js?rt={1}'.format(
            fund_code, int(time.time()*1000))
        logging.info('url2: {0}'.format(url))
        r = requests.get(url)
        assert r.status_code == 200
        rate = cls.parse_current_rate(r.text)
        if rate is not None:
            cls.IsTrading = True
            worth.append(worth[-1] * (1 + rate/100))
        return name, worth

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
        return None

    @staticmethod
    def high_or_low(worth):
        """returns N which indicates the current price is higher (+) or lower (-) than the past N days (exclusively)"""
        N = 0
        # empty or None
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

def main(codes):
    logging.info('+++++BEGIN+++++')
    d = {}
    for fund_code in codes:
        try:
            fund = Fund(fund_code)
            k = '{0} ({1})'.format(fund.name, fund.fund_code)
            d[k] = fund.N
            if os.getenv('TEST'):
                logging.info('TEST mode')
                break
        except:
            traceback.print_exc()
    # sort by value
    msgs = ['{0}: {1}'.format(k, v) for k, v in sorted(d.items(), key=lambda item: -item[1])]
    output = '\n'.join(msgs)
    logging.info(output)
    if Fund.IsTrading:
        send_notification(output)


class MyTest(unittest.TestCase):
    def test_high_or_low(self):
        high_or_low = Fund.high_or_low
        self.assertEqual(0, high_or_low([]))
        self.assertEqual(0, high_or_low([1]))
        self.assertEqual(1, high_or_low([1, 2]))
        self.assertEqual(0, high_or_low([1, 2, 2]))
        self.assertEqual(2, high_or_low([1, 2, 3]))
        self.assertEqual(2, high_or_low([4, 1, 2, 3]))
        self.assertEqual(-1, high_or_low([2, 1]))
        self.assertEqual(0, high_or_low([2, 1, 1]))
        self.assertEqual(-2, high_or_low([1, 3, 2, 1]))

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


if __name__ == '__main__':
    codes = [
        '000961', # 天虹沪深300ETF联接A
        '270042', # 广发纳斯达克100
        '164906', # 交银中证海外中国互联网指数
        '110022', # 易方达消费行业股票
        '008903', # 广发科技先锋混合
        '001410', # 信达澳银新能源产业
        '001595', # 天弘中证银行指数C
        '161725', # 招商中证白酒指数分级
        '320007', # 诺安成长混合
        '502056', # 广发中证医疗指数
        '161903', # 万家行业优选混合
        '008087', # 华夏中证5G通信主题ETF联接C
    ]
    main(codes)
