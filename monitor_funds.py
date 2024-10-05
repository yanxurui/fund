# -*- coding: UTF-8 -*-
import os
import logging
import unittest

from fund import Fund, TestFund
from monitor import Monitor

class MyFund(Fund):
    '''
    该策略并未直接输出买入或卖出的金额，而是输出一个强弱信号，由我自己决定
    self.N: 正数代表比过去N个交易日价格高，负数代表比过去N个交易日价格低
    '''
    def __init__(self, code):
        super().__init__(code)
        self.mdd = None # 最大回撤
        self.cur = None # 当前的回撤

    def __str__(self):
        '''convert self to str'''
        k = '{0}({1})'.format(self.name, self.code)
        v = str(self.N)
        # return MAX when it reaches the highest in history
        if self.N == len(self.worth) - 1:
            v = 'MAX' # 历史最高点
        elif self.N == -(len(self.worth) - 1):
            v = 'MIN' # 历史最低点
        # 创历史新高后下跌则减仓
        # Circled Letter Symbols from https://altcodeunicode.com/alt-codes-circled-number-letter-symbols-enclosed-alphanumerics/
        if max(self.worth) == self.worth[-2]:
            v += '🅢' # sell
        # 下跌到过去100个交易日的谷底时加仓
        # ***这里用了一个hardcoded的经验值***
        if self.N <= -300:
            v += '🅑' # buy
        # 最大回撤
        now = self.cur > 0 and self.cur == self.mdd
        # 当前出现历史最大或较大(>20%)的回撤
        if now or self.cur > 0.2:
            if v[-1].isdigit():
                # avoid output like -9622%
                v += ','
            v += '{:.0f}%'.format(100*self.cur)
        if now:
            v += '🅜'
        return '{0}:{1}'.format(k, v)

    def trade(self):
        '''download and run the strategy'''
        super().trade()
        self.mdd, self.cur = self.cal_mdd()

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

    def cal_mdd(self):
        '''return maximum drawdown, current drawdown'''
        if not self.worth:
            return 0, 0
        current_drawdown = 0
        max_drawdown = 0
        start = 0
        end = 0
        start_tmp = 0
        worth = self.worth[::-1]
        for i in range(1, len(worth)):
            # find a lower point or reach to the start point
            if worth[i] < worth[start_tmp] or i == len(worth)-1:
                tmp_drawdown = 1 - worth[start_tmp] / max(worth[start_tmp:i+1])
                if start_tmp == 0:
                    current_drawdown = tmp_drawdown
                if tmp_drawdown > max_drawdown:
                    max_drawdown = tmp_drawdown
                    start = start_tmp
                    end = i - 1
                start_tmp = i
        logging.debug('最大回撤：{:.1f}%'.format(100*max_drawdown))
        return round(max_drawdown, 4), round(current_drawdown, 4)

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

    def test_mdd(self):
        fake_fund = MyFund(0)
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
        fake_fund = MyFund(0)
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


def main(codes):
    '''
    codes是所关注的基金代码的列表。
    测试：`TEST=1 python monitor.py`
    '''
    Monitor().process([MyFund(c) for c in codes])


if __name__ == '__main__':
    codes = [
        '000961', # 天弘沪深300ETF联接A
        '001557', # 天弘中证500指数增强
        '001593', # 天弘创业板ETF
        '001595', # 天弘中证银行指数C
        '008591', # 天弘中证全指证券公司指数C
        '012349', # 天弘恒生科技指数
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
        '161725', # 招商中证白酒指数分级
        '005572', # 中银证券新能源混合C
        '004813', # 中欧先进制造股票C
        '320007', # 诺安成长混合
        '161903', # 万家行业优选混合
        '164906', # 交银中证海外中国互联网
        '260108', # 景顺长城新兴成长混合
        '006751', # 富国互联科技股票
        '003494', # 富国天惠成长混合C
        '001102', # 前海开源国家
        '001668', # 汇添富全球互联混合
        '010789', # 汇添富恒生指数
        '004241', # 中欧时代先锋
        '378006', # 上投摩根全球新兴市场
        '167301', # 方正富邦中证保险主题指数
    ]

    main(codes)
