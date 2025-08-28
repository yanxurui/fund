# -*- coding: UTF-8 -*-
import efinance as ef

from monitor_with_criteria import MonitorWithCriteria, MonitorConfig
from stock import Stock


def main_stocks(codes):
    """Monitor stock assets"""
    # Create stock-specific configuration
    stock_config = MonitorConfig(
        asset_type='stock',
        subject_prefix='股票小作手',
        snapshot_file="stock_snapshot.json"
    )

    MonitorWithCriteria(stock_config).process([Stock(c) for c in codes])

    # Need to close the session manually to avoid the error below:
    # sys:1: ResourceWarning: unclosed <socket object, fd=3, family=2, type=1, proto=6>
    ef.shared.session.close()


if __name__ == '__main__':
    # Stock codes from original monitor_stocks.py
    stock_codes = [
        # 美股
        'NDX',      # 纳指ETF
        'SPY',      # 标普500
        'DJI',      # 道琼斯
        'MSFT',     # 微软
        'NVDA',     # 英伟达
        'TSLA',     # 特斯拉
        'AAPL',     # 苹果
        'GOOG',     # 谷歌
        'AMZN',     # 亚马逊
        'META',     # Meta
        'NFLX',     # Netflix
        'TSM',      # 台积电
        'QCOM',     # 高通
        'COST',     # 好市多
        'TM',       # 丰田
        # 中概
        'PDD',      # 拼多多
        '京东',     # 京东
        'BABA',     # 阿里巴巴
        # 港股
        'HSI',      # 恒生指数
        '00700',    # 腾讯
        '01810',    # 小米
        '03690',    # 美团
        # A股
        'SZZS',     # 上证指数
        '000300',   # 沪深300
        '002594',   # 比亚迪
        '300750',   # 宁德时代
        '002352',   # 顺丰
        '600036',   # 招商银行
        # 债券
        'US10Y',   # 美债10年
        'CN10Y',   # 国债10年
        # 其他
        '黄金ETF-SPDR', # 黄金
        'USDCNY',   # 美元人民币
        'IBIT',     # 比特币
    ]

    print("Monitoring stocks...")
    main_stocks(stock_codes)