# -*- coding: UTF-8 -*-

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
    format='%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d {%(message)s}')

def download(fund_code):
    """get a list of recent worth including today's"""
    # 1. get the history daily price
    url = 'http://fund.eastmoney.com/pingzhongdata/{0}.js?v={1}'.format(fund_code, time.strftime("%Y%m%d%H%M%S", time.localtime()))
    logging.info('url1: {0}'.format(url))
    r = requests.get(url)
    assert r.status_code == 200
    jsContent = execjs.compile(r.text)
    name = jsContent.eval('fS_name')
    logging.info('fund name: {0}'.format(name))
    ACWorthTrend = jsContent.eval('Data_ACWorthTrend')
    worth = [w for t,w in ACWorthTrend]

    # 2. get today's real-time price
    url = 'http://fundgz.1234567.com.cn/js/{0}.js?rt={1}'.format(fund_code, int(time.time()*1000))
    logging.info('url2: {0}'.format(url))
    r = requests.get(url)
    assert r.status_code == 200
    worth_match = re.search(r'"gsz":"(\d+(\.\d+)?)"', r.text)
    datetime_match = re.search(r'"gztime":"(\d+-\d+-\d+ \d+:\d+)"', r.text)
    if worth_match is None or datetime_match is None:
        logging.error('invalid response: {0}'.format(r.text))
    else:
        current = float(worth_match.group(1))
        dt = datetime.strptime(datetime_match.group(1), '%Y-%m-%d %H:%M')
        if dt.date() == datetime.today().date() and dt.time().hour != 15:
            worth.append(current)
        else:
            logging.warning('current value is not available today: {0}'.format(r.text))
    return name, worth

def send_notification(msg):
    logging.info(msg)
    return
    """send notifiation via quip"""
    client = quip.QuipClient(access_token="YURJQU1BaGJSQ0g=|1635522342|nvZ5YsJ03DDUrt8b5b7hKbIJ2/0L7dBS41GfEWZZ6rI=")
    # user = client.get_authenticated_user()
    r = client.new_message(thread_id='XPdAAAdjxIV', content="Hello world from python in 2020!")

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
    msgs = []
    for fund_code in codes:
        logging.info('fund code: {0}'.format(fund_code))
        try:
            name, worth = download(fund_code)
            msgs.append('{0}:{1}'.format(name, high_or_low(worth)))
        except:
            traceback.print_exc() 
    send_notification('\n'.join(msgs))


class MyTest(unittest.TestCase):
    def test_high_or_low(self):
        self.assertEqual(0, high_or_low([]))
        self.assertEqual(0, high_or_low([1]))
        self.assertEqual(1, high_or_low([1, 2]))
        self.assertEqual(0, high_or_low([1, 2, 2]))
        self.assertEqual(2, high_or_low([1, 2, 3]))
        self.assertEqual(2, high_or_low([4, 1, 2, 3]))
        self.assertEqual(-1, high_or_low([2, 1]))
        self.assertEqual(0, high_or_low([2, 1, 1]))
        self.assertEqual(-2, high_or_low([1, 3, 2, 1]))


if __name__ == '__main__':
    codes = [
        '270042', # 广发纳斯达克100
        '008903', # 广发科技先锋混合
        '000961', # 天虹沪深300ETF联接A
    ]
    main(codes)
