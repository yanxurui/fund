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
    """Base monitoring class for processing assets and sending notifications"""
    
    def __init__(self):
        self.success = []
        self.failed = []
        self.subject = '基金小作手【{}】'.format(datetime.now().strftime(u"%Y{0}%m{1}%d{2}").format(*'年月日'))
        self.TEST = os.getenv('TEST')

    def process(self, assets):
        """Main processing pipeline: download data, analyze, and notify"""
        if self.TEST:
            logging.info('TEST mode')
            assets[:] = assets[:2]  # Modify the original list in place
        
        logging.info('-' * 50)
        logging.info(f'Starting to process {len(assets)} assets')
        start_time = time.time()

        self._download_asset_data(assets)
        self._sort_results_by_original_order(assets)
        self._generate_and_send_notification()

        total_time = time.time() - start_time
        logging.info(f'Processing completed in {total_time:.2f} seconds')

    def _download_asset_data(self, assets):
        """Download and process asset data concurrently"""
        def process_single_asset(asset):
            """Process a single asset and track timing"""
            start = time.time()
            try:
                asset.trade()
                self.success.append(asset)
                logging.debug(f'Successfully processed {asset.code}')
            except Exception as e:
                logging.exception(f'Failed to process asset {asset.code}: {e}')
                self.failed.append(asset.code)
            return time.time() - start

        # Execute downloads concurrently
        concurrent_start = time.time()
        total_processing_time = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            total_processing_time = sum(executor.map(process_single_asset, assets))
        
        actual_time = time.time() - concurrent_start
        logging.info(f'Processing time: {total_processing_time:.2f}s total, {actual_time:.2f}s actual')
        logging.info(f'Success: {len(self.success)}, Failed: {len(self.failed)}')

    def _sort_results_by_original_order(self, assets):
        """Sort successful results to match original asset order"""
        index_map = {asset: index for index, asset in enumerate(assets)}
        self.success.sort(key=lambda asset: index_map[asset])

    def _generate_and_send_notification(self):
        """Generate formatted notification and send if needed"""
        html_message = self._create_notification_content()
        
        if not html_message:
            logging.info('No notification needed - no interesting assets found')
            return
            
        self._send_notification(html_message)

    def _create_notification_content(self):
        """Create HTML notification content from processed results"""
        interesting_assets = self.filter_sort()
        
        if not interesting_assets:
            return None

        # Format asset information
        asset_lines = [str(asset) for asset in interesting_assets]
        html_table = utils.html_table([line.split(':') for line in asset_lines], head=False)
        
        # Add error information if any
        if self.failed:
            error_msg = 'Failed: ' + ','.join(self.failed)
            asset_lines.append(error_msg)
            html_table += f'\n<p style="color:red">{error_msg}</p>'
        
        # Log text version and return HTML
        text_message = '\n'.join(asset_lines)
        html_message = HTML_TEMPLATE.format(html_table)
        
        logging.info(f'Notification content:\n{text_message}')
        logging.debug(f'HTML content:\n{html_message}')
        
        return html_message

    def _send_notification(self, html_message):
        """Send email notification unless in test mode"""
        if self.TEST:
            logging.info('Skipping email notification in test mode')
            return
            
        utils.send_email(
            ['yanxurui1993@qq.com'],
            self.subject,
            html_message,
            mimetype='html'
        )
        logging.info('Email notification sent successfully')

    def filter_sort(self):
        """Filter and sort assets based on trading status - override in subclasses"""
        if any(asset.trading for asset in self.success):
            # Sort by trading signal strength (N value)
            sorted_assets = sorted(self.success, key=lambda x: x.N, reverse=True)
            logging.info(f'Found {len(sorted_assets)} trading assets')
            return sorted_assets
        else:
            logging.info('No assets are currently trading')
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
