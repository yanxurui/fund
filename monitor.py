#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import logging
import unittest
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import utils
from fund import Fund, TestFund


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s')

HTML_TEMPLATE = '''
<table width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
        <td align="center">
            {}
            <p>source in <a target="_blank" href="https://github.com/yanxurui/fund">Github</a></p>
        </td>
    </tr>
</table>'''

class Monitor:
    def __init__(self):
        self.success = []
        self.failed = []
        self.subject = '基金小作手【{}】'.format(datetime.now().strftime(u"%Y{0}%m{1}%d{2}").format(*'年月日'))
        self.TEST = os.getenv('TEST')

    def process(self, funds):
        
        if self.TEST:
            logging.info('TEST mode')
            funds = funds[:2]
        start = time.time()
        logging.info('-'*50)

        # crawling in a parallel manner using gevent
        def process_async(fund):
            start = time.time()
            try:
                fund.trade()
                self.success.append(fund)
            except:
                logging.exception('failed to get fund {0}'.format(fund.code))
                self.failed.append(fund.code)
            return time.time() - start

        start = time.time()
        total_time = 0
        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            total_time = sum(executor.map(process_async, funds))
        actual_time = time.time() - start
        logging.info('total time needed is %.2f, actual time spent is %.2f', total_time, actual_time)

        # sort self.success by the order in funds
        # Create a mapping of the index of each object in list1
        index_map = {obj: index for index, obj in enumerate(funds)}
        # Sort list2 based on the index in list1
        self.success.sort(key=lambda obj: index_map[obj])

        self.output()
        end = time.time()
        logging.info('Finishied in {0:.2f} seconds'.format(end - start))

    def output(self):
        html_msg = self.format()
        if not html_msg:
            logging.info('Skip sending notification')
        else:
            # send notification
            # avoid notifying on weekends or in test mode
            if not self.TEST:
                utils.send_email(
                    ['yanxurui1993@qq.com'],
                    self.subject,
                    html_msg,
                    mimetype='html')
            else:
                logging.info('Skip sending notification in test mode')

    def format(self):
        results = self.filter_sort()
        if not results:
            return None

        # construct the message to send to subscribers
        lines = list(map(str, results))
        html_msg = utils.html_table(list(map(lambda x: x.split(':'), lines)), head=False)
        error_msg = ''
        if self.failed:
            error_msg = 'Failed: ' + ','.join(self.failed)
            lines.append(error_msg)
            html_msg += '\n<p style="color:red">{}</p>'.format(error_msg)
        text_msg = '\n'.join(lines)
        html_msg = HTML_TEMPLATE.format(html_msg)
        logging.info(text_msg)
        logging.debug(html_msg)
        return html_msg

    def filter_sort(self):
        if any([fund.trading for fund in self.success]):
            # sort by N in place
            self.success.sort(key=lambda x: x.N, reverse=True)
            return self.success
        else:
            logging.info('No trading today')
            return []


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
        '163402', # 兴全趋势投资混合
        '378006', # 上投摩根全球新兴市场
        '167301', # 方正富邦中证保险主题指数
    ]
    main(codes)
