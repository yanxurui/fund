# -*- coding: UTF-8 -*-
import os
import time
import logging
import unittest

import CONFIG
import quip
# also import TestFund so that when `python -m unittest monitor`
# will also run TestFund
from fund import Fund, TestFund


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s')

class MyFund(Fund):
    '''
    该策略并未直接输出买入或卖出的金额，而是输出一个强弱信号，由我自己决定
    self.N: 正数代表比过去N个交易日价格高，负数代表比过去N个交易日价格低
    '''
    def __str__(self):
        '''convert self to str'''
        k = '{0}({1})'.format(self.name[:10], self.fund_code)
        v = str(self.N)
        # return MAX when it reaches the highest in history
        if self.N == len(self.worth) - 1:
            v = 'MAX'
        # 创历史新高后下跌则减仓
        if max(self.worth) == self.worth[-2]:
            v += '🅢'
        return '{0}:{1}'.format(k, v)

    def buy_or_sell(self, worth):
        '''returns N which indicates the current price is higher (+) or lower (-) than the past N days (exclusively)'''
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

class TestMyFund(unittest.TestCase):
    '''测试：`python -m unittest monitor`'''
    def test_buy_or_sell(self):
        fake_fund = MyFund(0)
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


def send_notification(msg):
    '''send notifiation via quip'''
    client = quip.QuipClient(access_token=CONFIG.QUIP_TOKEN)
    r = client.new_message(thread_id='XWWAAAszoRa', content=msg)
    logging.info('notification sent')

def main(codes):
    '''
    codes是所关注的基金代码的列表。
    测试：`TEST=1 python monitor.py`
    '''
    TEST = os.getenv('TEST')
    start = time.time()
    logging.info('-'*50)
    success = []
    failed = []
    for fund_code in codes:
        try:
            fund = Fund(fund_code)
            fund.trade()
            success.append(fund)
            if TEST:
                logging.info('TEST mode')
                break
        except:
            logging.exception('failed to get fund {0}'.format(fund_code))
            failed.append(fund_code)
    # sort by N in place
    success.sort(key=lambda x: x.N, reverse=True)
    lines = list(map(str, success))
    if failed:
        lines.append('Failed: ' + ','.join(failed))
    msg = '\n'.join(lines)
    logging.info(msg)
    # avoid notifying on weekends or in test mode
    if Fund.IsTrading and not TEST:
        send_notification(msg)
    else:
        logging.info('Skip sending notification')
    end = time.time()
    logging.info('Finishied in {0:.2f} seconds'.format(end - start))


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
        # '006328', # 易方达中证海外中国互联网50ETF
        '011609', # 易方达科创板50ETF
        '270042', # 广发纳斯达克100
        '008903', # 广发科技先锋混合
        '502056', # 广发中证医疗指数
        '004997', # 广发高端制造股票A
        '004753', # 广发中证传媒ETF联接C
        '161725', # 招商中证白酒指数分级
        '005572', # 中银证券新能源混合C
        '320007', # 诺安成长混合
        '161903', # 万家行业优选混合
        '002891', # 华夏移动互联混合人民币
        '164906', # 交银中证海外中国互联网
        '260108', # 景顺长城新兴成长混合
        '006751', # 富国互联科技股票
        '003494', # 富国天惠成长混合C
        '001102', # 前海开源国家
        '001668', # 汇添富全球互联混合
        '010789', # 汇添富恒生指数
        '004241', # 中欧时代先锋
        '163402', # 兴全趋势投资混合
        '378006', # 上投摩根全球新兴市场
    ]
    main(codes)
