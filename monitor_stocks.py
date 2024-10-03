# -*- coding: UTF-8 -*-
import os
import logging
from datetime import datetime

from monitor import Monitor
# monkey patch needs to be done before this
import efinance as ef
from monitor_funds import MyFund

today_str = datetime.now().strftime('%Y-%m-%d')

class MyStock(MyFund):
    def download(self):
        hist = ef.stock.get_quote_history(self.code, fqt=0)
        self.name = hist.iloc[-1]['股票名称']
        self.worth = hist['收盘'].tolist()
        logging.info('{0}:{1}'.format(self.code, self.name))

        # Todo: how can we check if it's trading time accurately?
        if today_str == hist.iloc[-1]['日期']:
            self.trading = True

class StockMonitor(Monitor):
    # override the filter_sort method
    def filter_sort(self):
        '''sort by the N value'''
        results = [s for s in self.success if s.trading and (abs(s.N) > 300 or s.mdd > 0.2)]
        results.sort(key=lambda x: x.N, reverse=True)

        # load the stocks notified last time from the file
        notified = set()
        if os.path.exists('stocks_notified.txt'):
            with open('stocks_notified.txt') as f:
                date = f.readline().strip()
                if date == today_str:
                    notified = set(f.read().split())

        # filter out the stocks notified last time
        results = [s for s in results if s.code not in notified]

        # output the code of the stocks to notify to a text file
        # write the date at the beginning of the file
        with open('stocks_notified.txt', 'w') as f:
            f.write(today_str)
            f.write('\n'.join([s.code for s in results]))

        return results


def main(codes):
    StockMonitor().process([MyStock(c) for c in codes])


if __name__ == '__main__':
    codes = [
        '00700', # 腾讯
        'MSFT', # 微软
    ]
    main(codes)
