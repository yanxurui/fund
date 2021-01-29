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

MAX = 100000

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s')

def send_notification(msg):
    """send notifiation via quip"""
    client = quip.QuipClient(
        access_token="YURJQU1BaGJSQ0g=|1635522342|nvZ5YsJ03DDUrt8b5b7hKbIJ2/0L7dBS41GfEWZZ6rI=")
    r = client.new_message(thread_id='XWWAAAszoRa', content=msg)
    logging.info('notification sent')

class Fund:
    IsTrading = False

    def __init__(self, fund_code):
        self.fund_code = fund_code
        retry = 1 # retry only 1 time
        while retry >= 0:
            try:
                self.name, self.worth = self.download(fund_code)
                break
            except:
                logging.exception('failed to download data for fund {0}'.format(fund_code))
                retry -= 1
        # current price is higher than the past N days
        self.N = self.high_or_low(self.worth)

    @classmethod
    def download(cls, fund_code):
        """get historical daily prices including today's if available"""
        # 1. get the history daily price
        url = 'http://fund.eastmoney.com/pingzhongdata/{0}.js'.format(fund_code)
        r = requests.get(url, timeout=10)
        assert r.status_code == 200
        jsContent = execjs.compile(r.text)
        name = jsContent.eval('fS_name')
        logging.info('{0}:{1}'.format(fund_code, name))
        logging.info('url1: {0}'.format(url))
        ACWorthTrend = jsContent.eval('Data_ACWorthTrend')
        worth = [w for t,w in ACWorthTrend]

        # 2. get today's real-time price
        url = 'http://fundgz.1234567.com.cn/js/{0}.js'.format(fund_code)
        logging.info('url2: {0}'.format(url))
        r = requests.get(url, timeout=10)
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
        # there are 2 cases:
        # 1. QDII
        # 2. NOT QDII
        #   a) on a non-trading day, the value of the last trading day has been updated
        #   b) on a trading day but after 15:00, today's value has probably not been updated yet. BUG: This is misleading.
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
        # return MAX when it reaches the highest in history
        if N == len(worth) - 1:
            N = MAX
        return N

def main(codes):
    TEST = os.getenv('TEST')
    start = time.time()
    logging.info('-'*50)
    d = {}
    failed = []
    for fund_code in codes:
        try:
            fund = Fund(fund_code)
            k = '{0} ({1})'.format(fund.name[:10], fund.fund_code)
            d[k] = fund.N
            if TEST:
                logging.info('TEST mode')
                break
        except:
            logging.exception('failed to get fund {0}'.format(fund_code))
            failed.append(fund_code)
    # sort by value
    msgs = ['{0}: {1}'.format(k, 'MAX' if v == MAX else v) \
        for k, v in sorted(d.items(), key=lambda item: -item[1])]
    if failed:
        msgs.append('Failed: ' + ','.join(failed))
    output = '\n'.join(msgs)
    logging.info(output)
    if Fund.IsTrading and not TEST:
        send_notification(output)
    else:
        logging.info('Skip sending notification')
    end = time.time()
    logging.info('Finishied in {0:.2f} seconds'.format(end - start))


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
        '000961', # 天弘沪深300ETF联接A
        '001557', # 天弘中证500指数增强
        '001593', # 天弘创业板ETF
        '001595', # 天弘中证银行指数C
        '008591', # 天弘中证全指证券公司指数C
        '004746', # 易方达上证50指数
        '005827', # 易方达蓝筹精选混合
        '110022', # 易方达消费行业股票
        '110011', # 易方达中小盘混合
        '002963', # 易方达黄金ETF联接C
        '270042', # 广发纳斯达克100
        '008903', # 广发科技先锋混合
        '502056', # 广发中证医疗指数
        '004997', # 广发高端制造股票A
        '004753', # 广发中证传媒ETF联接C
        '161725', # 招商中证白酒指数分级
        '001410', # 信达澳银新能源产业
        '005572', # 中银证券新能源混合C
        '320007', # 诺安成长混合
        '161903', # 万家行业优选混合
        '008087', # 华夏中证5G通信主题ETF
        '002891', # 华夏移动互联混合人民币
        '164906', # 交银中证海外中国互联网
        '260108', # 景顺长城新兴成长混合
        '006751', # 富国互联科技股票
        '003494', # 富国天惠成长混合C
        '001102', # 前海开源国家
        '001668', # 汇添富全球互联混合
        '010789', # 汇添富恒生指数
        '004241', # 中欧时代先锋
    ]
    main(codes)
