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
    format='%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s')

def download(fund_code):
    """get a list of recent worth including today's"""
    # 1. get the history daily price
    url = 'http://fund.eastmoney.com/pingzhongdata/{0}.js?v={1}'.format(fund_code, time.strftime("%Y%m%d%H%M%S", time.localtime()))
    r = requests.get(url)
    assert r.status_code == 200
    jsContent = execjs.compile(r.text)
    name = jsContent.eval('fS_name')
    logging.info('{0}:{1}'.format(fund_code, name))
    logging.info('url1: {0}'.format(url))
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
    """send notifiation via quip"""
    logging.info(msg)
    # return
    client = quip.QuipClient(access_token="YURJQU1BaGJSQ0g=|1635522342|nvZ5YsJ03DDUrt8b5b7hKbIJ2/0L7dBS41GfEWZZ6rI=")
    # user = client.get_authenticated_user()
    r = client.new_message(thread_id='XPdAAAdjxIV', content=msg)

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
            name, worth = download(fund_code)
            # current price is higher than the past N days
            N = high_or_low(worth)
            k = '{0} ({1})'.format(name, fund_code)
            d[k] = N
        except:
            traceback.print_exc()
    # sort by value
    msgs = ['{0}: {1}'.format(k, v) for k, v in sorted(x.items(), key=lambda item: -item[1])]
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
        '000961', # 天虹沪深300ETF联接A
        '270042', # 广发纳斯达克100
        '164906', # 交银中证海外中国互联网指数
        '008903', # 广发科技先锋混合
        '001410', # 信达澳银新能源产业
        '001595', # 天弘中证银行指数C
        '161725', # 招商中证白酒指数分级
        '320007', # 诺安成长混合
        '502056', # 广发中证医疗指数
    ]
    main(codes)
