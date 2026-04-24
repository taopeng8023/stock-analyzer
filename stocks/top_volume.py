#!/usr/bin/env python3
"""
获取 A 股成交量前 N 的股票并推送

用法:
    python3 top_volume.py --top 100 --push
"""

import requests
import re
import argparse
import time
from datetime import datetime
from sina_stock import get_stock_quote
from wechat_push import push_to_corp_webhook, format_stock_message


def get_a_share_list():
    """
    获取 A 股股票列表（沪市 + 深市）
    使用腾讯财经接口获取股票列表
    """
    stocks = []
    
    # 沪市 A 股 (600000-609999)
    print("正在获取沪市 A 股列表...")
    for i in range(0, 100):
        page_url = f"http://qt.gtimg.cn/q=sh60{i:02d}00,sh60{i:02d}01,sh60{i:02d}02,sh60{i:02d}03,sh60{i:02d}04,sh60{i:02d}05,sh60{i:02d}06,sh60{i:02d}07,sh60{i:02d}08,sh60{i:02d}09"
        try:
            resp = requests.get(page_url, timeout=5)
            resp.encoding = 'gbk'
            matches = re.findall(r'v_(sh\d{6})="', resp.text)
            stocks.extend(matches)
        except:
            pass
        time.sleep(0.1)
    
    # 深市 A 股 (000001-002999, 300000-301999)
    print("正在获取深市 A 股列表...")
    for i in range(0, 30):
        page_url = f"http://qt.gtimg.cn/q=sz00{i:02d}00,sz00{i:02d}01,sz00{i:02d}02,sz00{i:02d}03,sz00{i:02d}04,sz00{i:02d}05,sz00{i:02d}06,sz00{i:02d}07,sz00{i:02d}08,sz00{i:02d}09"
        try:
            resp = requests.get(page_url, timeout=5)
            resp.encoding = 'gbk'
            matches = re.findall(r'v_(sz\d{6})="', resp.text)
            stocks.extend(matches)
        except:
            pass
        time.sleep(0.1)
    
    # 创业板 (300xxx)
    for i in range(0, 20):
        page_url = f"http://qt.gtimg.cn/q=sz30{i:02d}00,sz30{i:02d}01,sz30{i:02d}02,sz30{i:02d}03,sz30{i:02d}04,sz30{i:02d}05,sz30{i:02d}06,sz30{i:02d}07,sz30{i:02d}08,sz30{i:02d}09"
        try:
            resp = requests.get(page_url, timeout=5)
            resp.encoding = 'gbk'
            matches = re.findall(r'v_(sz\d{6})="', resp.text)
            stocks.extend(matches)
        except:
            pass
        time.sleep(0.1)
    
    # 去重
    stocks = list(set(stocks))
    print(f"共获取到 {len(stocks)} 只股票")
    return stocks


def get_stock_list_from_sina():
    """
    从新浪财经获取股票列表（更快）
    """
    stocks = []
    
    # 沪深 A 股列表
    urls = [
        "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=80&sort=symbol&asc=1&node=hs_a&symbol=&_s_r_a=page",
    ]
    
    # 这个方法需要解析 JSON，简化处理：使用预定义的股票范围
    # 实际使用时建议从本地文件或数据库加载股票列表
    
    return stocks


def get_batch_quotes(symbols, batch_size=50):
    """
    批量获取股票行情（分批请求避免超时）
    """
    all_quotes = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        print(f"正在获取第 {i//batch_size + 1} 批 ({len(batch)}只)...")
        
        # 腾讯接口批量查询
        symbol_list = ','.join(batch)
        url = f"https://qt.gtimg.cn/q={symbol_list}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://stockapp.finance.qq.com/'
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'gbk'
            
            for line in resp.text.split('\n'):
                if not line.strip():
                    continue
                
                match = re.search(r'v_(\w+)="([^"]+)"', line)
                if match:
                    symbol = match.group(1)
                    fields = match.group(2).split('~')
                    
                    if len(fields) >= 50 and fields[6]:  # 有成交量数据
                        try:
                            volume = int(fields[6]) if fields[6] else 0
                            data = {
                                'symbol': symbol,
                                'name': fields[1],
                                'current': float(fields[3]) if fields[3] else 0,
                                'close': float(fields[4]) if fields[4] else 0,
                                'open': float(fields[5]) if fields[5] else 0,
                                'high': float(fields[33]) if fields[33] else 0,
                                'low': float(fields[34]) if fields[34] else 0,
                                'volume': volume,
                                'amount_wan': float(fields[7]) if fields[7] else 0,
                                'change': float(fields[38]) if fields[38] else 0,
                                'change_percent': float(fields[39]) if fields[39] else 0,
                                'time': fields[30] if len(fields) > 30 else '',
                            }
                            all_quotes.append(data)
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            print(f"批次 {i//batch_size + 1} 获取失败：{e}")
        
        time.sleep(0.2)  # 避免请求过快
    
    return all_quotes


def get_top_volume(top_n=100, webhook=None):
    """
    获取成交量前 N 的股票并推送
    
    Args:
        top_n: 前 N 只股票
        webhook: 企业微信 Webhook 地址（可选）
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取 A 股成交量排行榜 Top{top_n}...")
    
    # 获取股票列表（简化：使用常见股票范围）
    # 实际 A 股约 5000+ 只，这里使用更高效的获取方式
    
    # 方法：从腾讯获取沪深 A 股完整列表
    all_stocks = []
    
    # 沪市 60xxxx
    for prefix in range(600, 606):
        for suffix in range(100):
            all_stocks.append(f"sh{prefix}{suffix:03d}")
    
    # 深市 00xxxx
    for prefix in range(0, 30):
        for suffix in range(100):
            all_stocks.append(f"sz00{prefix}{suffix:02d}")
    
    # 深市 002xxx (中小板)
    for suffix in range(1000, 5000):
        all_stocks.append(f"sz00{suffix}")
    
    # 创业板 30xxxx
    for prefix in range(0, 40):
        for suffix in range(100):
            all_stocks.append(f"sz30{prefix}{suffix:02d}")
    
    print(f"待查询股票数量：{len(all_stocks)}")
    
    # 批量获取行情
    quotes = get_batch_quotes(all_stocks, batch_size=80)
    print(f"成功获取 {len(quotes)} 只股票数据")
    
    if not quotes:
        print("❌ 未获取到任何股票数据")
        return False
    
    # 按成交量排序
    quotes_sorted = sorted(quotes, key=lambda x: x.get('volume', 0), reverse=True)
    
    # 取前 N
    top_stocks = quotes_sorted[:top_n]
    
    print(f"\n{'='*60}")
    print(f"📊 A 股成交量排行榜 Top{top_n}")
    print(f"{'='*60}")
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'成交量 (手)':<12} {'成交额':<10} {'现价':<8} {'涨跌%':<8}")
    print(f"{'-'*60}")
    
    for i, s in enumerate(top_stocks, 1):
        amount_str = f"{s.get('amount_wan', 0):.0f}万"
        if s.get('amount_wan', 0) >= 10000:
            amount_str = f"{s.get('amount_wan', 0)/10000:.2f}亿"
        
        change_sign = '+' if s.get('change', 0) >= 0 else ''
        print(f"{i:<4} {s['symbol']:<8} {s['name']:<10} {s.get('volume', 0):>10,} {amount_str:>10} ¥{s['current']:>6.2f} {change_sign}{s.get('change_percent', 0):>6.2f}%")
    
    print(f"{'='*60}")
    
    # 推送
    if webhook:
        print("\n📤 正在推送到企业微信...")
        
        # 格式化推送内容
        lines = [f"📊 **A 股成交量排行榜 Top{top_n}**", f"_更新时间：{datetime.now().strftime('%m-%d %H:%M')}_", ""]
        
        for i, s in enumerate(top_stocks[:20], 1):  # 推送前 20 只（消息长度限制）
            amount_str = f"{s.get('amount_wan', 0):.0f}万"
            if s.get('amount_wan', 0) >= 10000:
                amount_str = f"{s.get('amount_wan', 0)/10000:.2f}亿"
            change_sign = '📈' if s.get('change', 0) >= 0 else '📉'
            
            lines.append(f"{i}. {change_sign} **{s['name']}** ({s['symbol']})")
            lines.append(f"   成交：{s.get('volume', 0):,}手 | 金额：{amount_str} | 现价：¥{s['current']:.2f}")
        
        if top_n > 20:
            lines.append(f"\n_... 共{top_n}只，详见终端输出_")
        
        content = "\n".join(lines)
        
        success = push_to_corp_webhook(webhook, f"📊 A 股成交量 Top{top_n}", content)
        return success
    
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='获取 A 股成交量排行榜')
    parser.add_argument('--top', type=int, default=100, help='前 N 只股票')
    parser.add_argument('--push', action='store_true', help='推送到企业微信')
    parser.add_argument('--webhook', type=str, help='企业微信 Webhook 地址')
    
    args = parser.parse_args()
    
    # 默认 Webhook
    webhook = args.webhook or "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
    
    get_top_volume(top_n=args.top, webhook=webhook if args.push else None)
