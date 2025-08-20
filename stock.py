# -*- coding: UTF-8 -*-
import efinance as ef

from base_asset import BaseAsset


class Stock(BaseAsset):
    def __init__(self, code):
        super().__init__(code)
        self.last_price = None

    def download(self):
        # fqt
            # 0: 不复权
            # 1: 前复权 (default)
            # 2: 后复权
            # 使用后复权因为东方财富返回的前复权历史数据可能包含负数，比如NVDA，会影响计算最大回撤
        hist = ef.stock.get_quote_history(self.code, fqt=2)
        self.name = hist.iloc[-1]['股票名称']
        self.worth = hist['收盘'].tolist() # The last row contains the current real-time price
        self.last_price = hist.iloc[-1].to_dict()