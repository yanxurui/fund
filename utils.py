#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import unittest
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from smtplib import SMTP_SSL

import CONFIG

def html_table(lol, head=True):
    def yield_lines():
        assert len(lol) > 0, 'Invalid input: empty list'
        yield '<table style="border-collapse:collapse; border: 1px solid; ">'
        for i, sublist in enumerate(lol):
            yield '  <tr>'
            for j, e in enumerate(sublist):
                if head and i == 0:
                    yield '    <th>{}</th>'.format(e)
                else:

                    yield '    <td>{}</td>'.format(e)
            yield '  </tr>'
        yield '</table>'
    return '\n'.join(yield_lines())

def send_email(receiver, mail_content, mimetype='plain', doNotSend=False):
    logging.info('send email...')

    host_server = 'smtp.qq.com'
    sender_qq_mail = CONFIG.EMAIL_ADDRESS
    pwd = CONFIG.EMAIL_PASSCODE
    smtp = SMTP_SSL(host_server)
    smtp.login(sender_qq_mail, pwd)

    subject = '基金小作手【{}】'.format(datetime.now().strftime("%Y年%m月%d日"))
    msg = MIMEMultipart()
    msg.attach(MIMEText(mail_content, mimetype, 'utf-8'))
    msg["Subject"] = Header(subject, 'utf-8')
    msg["From"] = sender_qq_mail

    if not doNotSend:
        smtp.sendmail(sender_qq_mail, receiver, msg.as_string())
    smtp.quit()
    logging.info('email sent successfully')

class TestUtils(unittest.TestCase):
    def test_html_table(self):
        lols = [
            ['col1', 'col2', 'col3'],
            ['a', 'b', 'c'],
            [1, 2, 3],
        ]
        print(html_table(lols, head=False))
        print(html_table(lols))

    @unittest.skipIf(int(os.getenv('TEST_SEND_EMAIL', 0)) < 1, 'skip by default')
    def test_send_email(self):
        html_msg = """<table>
  <tr>
    <td>万家行业优选混合(L(161903)</td>
    <td>19</td>
  </tr>
  <tr>
    <td>易方达科创板50ET(011609)</td>
    <td>12</td>
  </tr>
  <tr>
    <td>华夏移动互联混合人民(002891)</td>
    <td>9</td>
  </tr>
  <tr>
    <td>天弘中证全指证券公司(008591)</td>
    <td>2</td>
  </tr>
  <tr>
    <td>易方达黄金ETF联接(002963)</td>
    <td>1</td>
  </tr>
  <tr>
    <td>易方达消费行业股票(110022)</td>
    <td>-111</td>
  </tr>
  <tr>
    <td>招商中证白酒指数(L(161725)</td>
    <td>-118</td>
  </tr>
  <tr>
    <td>景顺长城新兴成长混合(260108)</td>
    <td>-128</td>
  </tr>
  <tr>
    <td>交银中证海外中国互联(164906)</td>
    <td>-144,31%</td>
  </tr>
  <tr>
    <td>天弘恒生科技指数(Q(012349)</td>
    <td>MIN🅑54%🅜</td>
  </tr>
  <tr>
    <td>汇添富恒生指数C(010789)</td>
    <td>MIN🅑38%🅜</td>
  </tr>
  <tr>
    <td>天弘中证银行ETF联(001595)</td>
    <td>-560🅑22%</td>
  </tr>
  <tr>
    <td>易方达蓝筹精选混合(005827)</td>
    <td>-569🅑48%🅜</td>
  </tr>
  <tr>
    <td>易方达上证50增强C(004746)</td>
    <td>-602🅑40%🅜</td>
  </tr>
</table>
<table>
  <tr>
    <th>符号</th>
    <th>说明</th>
  </tr>
  <tr>
    <td>MAX</td>
    <td>历史最高点</td>
  </tr>
  <tr>
    <td>MIN</td>
    <td>历史最低点</td>
  </tr>
  <tr>
    <td>🅢</td>
    <td>sell 卖出指令</td>
  </tr>
  <tr>
    <td>🅑</td>
    <td>buy 买入指令</td>
  </tr>
  <tr>
    <td>🅜</td>
    <td>历史最大回撤</td>
  </tr>
  <tr>
    <td>M%</td>
    <td>回撤M%</td>
  </tr>
</table>
"""
        send_email(
            ['yanxurui1993@qq.com', 'yxr1993@gmail.com'],
            html_msg, 'html')

if __name__ == '__main__':
    # send_notification('test')
    pass
