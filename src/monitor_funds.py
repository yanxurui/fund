# -*- coding: UTF-8 -*-
from monitor import Monitor
from monitor_config import MonitorConfig
from fund import Fund


def main(codes):
    '''
    codes是所关注的基金代码的列表。
    测试：`TEST=1 python monitor_funds.py`
    '''
    # Create a config for fund monitoring
    config = MonitorConfig(
        asset_type='fund',  # Used for identification
        subject_prefix='基金小作手',  # Used in email subject
        snapshot_file='fund_snapshot.json',  # Not used - funds don't use snapshot-based trading detection
        notification_days=1,  # Not used - funds don't use notification deduplication
        low_threshold=-300,  # Used in formatting - traditional fund threshold
        high_threshold=300,  # Not used - funds use basic filter_sort() 
        drawdown_threshold=0.2,  # Used in formatting - 20% drawdown threshold
        daily_change_threshold=0.1  # Used in formatting - 5% daily change display threshold
    )

    Monitor(config).process([Fund(c) for c in codes])


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