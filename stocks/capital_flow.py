#!/usr/bin/env python3
"""
获取 A 股主力资金净流入和 5 日涨幅排行
数据源：东方财富（优先）+ 腾讯财经（备用）

说明：
- 东方财富提供真实的主力净流入数据（f62=当日，f162=3 日，f164=5 日，f174=10 日）
- 如果东方财富不可用，使用腾讯财经的成交额估算

用法:
    python3 capital_flow.py --top 10 --push
"""

import requests
import argparse
import time
from datetime import datetime
from wechat_push import push_to_corp_webhook


def get_main_force_rank_eastmoney(page=1, page_size=50):
    """
    从东方财富获取主力净流入排行（真实数据）
    
    字段说明:
        f62:  当日主力净流入（元）
        f162: 3 日主力净流入
        f164: 5 日主力净流入
        f174: 10 日主力净流入
        f184: 5 日涨跌幅%
    """
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        'pn': page,
        'pz': page_size,
        'po': 1,
        'np': 1,
        'fltt': 2,
        'invt': 2,
        'fid': 'f62',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2',
        'fields': 'f12,f14,f62,f162,f164,f174,f184'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://quote.eastmoney.com/',
    }
    
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            data = resp.json()
            
            if data.get('rc') == 0 and data.get('data'):
                return data['data'].get('diff', [])
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
    
    return []


def get_main_force_rank_tencent(page_size=100):
    """
    从腾讯财经获取股票数据（备用，估算主力）
    
    使用成交额和成交量作为主力活跃度的代理指标
    """
    print("  → 使用腾讯财经备用接口（估算数据）...")
    
    stocks = []
    
    # 获取一批股票
    symbol_batches = []
    
    # 沪市 60xxxx
    batch = []
    for i in range(100, 600):
        batch.append(f"sh600{i%1000:03d}")
        if len(batch) >= 80:
            symbol_batches.append(batch)
            batch = []
    if batch:
        symbol_batches.append(batch)
    
    # 深市 00xxxx, 002xxx, 300xxx
    for prefix in ['000', '002', '300']:
        batch = []
        for i in range(1000, 5000 if prefix != '300' else 4000):
            if prefix == '300' and i >= 4000:
                break
            symbol = f"sz{prefix}{i%1000:03d}"
            batch.append(symbol)
            if len(batch) >= 80:
                symbol_batches.append(batch)
                batch = []
        if batch:
            symbol_batches.append(batch)
    
    # 分批获取
    for i, batch in enumerate(symbol_batches[:6]):  # 限制 6 批，约 480 只
        symbol_list = ','.join(batch)
        url = f"https://qt.gtimg.cn/q={symbol_list}"
        
        try:
            resp = requests.get(url, timeout=15)
            resp.encoding = 'gbk'
            
            for line in resp.text.split('\n'):
                if not line.strip():
                    continue
                    
                import re
                match = re.search(r'v_(\w+)="([^"]+)"', line)
                if match:
                    fields = match.group(2).split('~')
                    if len(fields) >= 50 and fields[6]:
                        symbol = match.group(1)
                        volume = int(fields[6]) if fields[6] else 0
                        amount_wan = float(fields[7]) if fields[7] else 0  # 成交额（万）
                        change_pct = float(fields[39]) if fields[39] else 0
                        
                        # 估算主力净流入：成交额的 10-20% 作为主力
                        # 高成交量股票主力参与度更高
                        factor = 0.15 if volume > 1000000 else 0.10
                        net_main = amount_wan * 10000 * factor
                        
                        stocks.append({
                            'f12': symbol,
                            'f14': fields[1],
                            'f62': net_main,       # 估算的当日主力
                            'f162': net_main * 3,  # 估算 3 日
                            'f164': net_main * 5,  # 估算 5 日
                            'f174': net_main * 10, # 估算 10 日
                            'f184': change_pct,
                        })
        except Exception as e:
            pass
        
        time.sleep(0.3)
    
    # 按主力净流入排序
    stocks.sort(key=lambda x: x.get('f62', 0), reverse=True)
    return stocks


def get_composite_rank(top_n=10, webhook=None):
    """
    获取综合排名（3 日主力净流入 + 5 日涨幅）
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取主力资金 +5 日涨幅综合排行 Top{top_n}...")
    
    # 1. 获取主力净流入排行
    print("[1/2] 获取主力净流入数据...")
    all_stocks = get_main_force_rank_eastmoney(page=1, page_size=50)
    
    data_source = "东方财富（真实数据）"
    if not all_stocks:
        all_stocks = get_main_force_rank_tencent(page_size=100)
        data_source = "腾讯财经（估算数据）"
    
    if not all_stocks:
        print("❌ 未获取到数据")
        return False
    
    print(f"  数据源：{data_source}")
    print(f"  共获取到 {len(all_stocks)} 只股票数据")
    
    # 2. 计算综合评分
    print("[2/2] 计算综合排名...")
    ranked_stocks = []
    
    for i, stock in enumerate(all_stocks[:100]):
        symbol = stock.get('f12', '')
        if not symbol.startswith('sh') and not symbol.startswith('sz'):
            if symbol.startswith('6'):
                symbol = 'sh' + symbol
            else:
                symbol = 'sz' + symbol
        
        name = stock.get('f14', '未知')
        
        # 主力净流入（元）
        net_main = stock.get('f62') or 0
        net_3d = stock.get('f162') or net_main * 3
        net_5d = stock.get('f164') or net_main * 5
        net_10d = stock.get('f174') or net_main * 10
        
        # 5 日涨跌幅%
        change_5d = stock.get('f184') or 0
        
        # 综合评分 = 主力净流入排名 (60%) + 5 日涨幅 (40%)
        score = (100 - i) * 0.6 + (max(-50, min(100, change_5d)) + 50) / 150 * 100 * 0.4
        
        ranked_stocks.append({
            'symbol': symbol,
            'name': name,
            'net_main': net_main,
            'net_3d': net_3d,
            'net_5d': net_5d,
            'net_10d': net_10d,
            'change_5d': change_5d,
            'score': score
        })
    
    # 排序
    ranked_stocks.sort(key=lambda x: x['score'], reverse=True)
    top_stocks = ranked_stocks[:top_n]
    
    # 输出
    print(f"\n{'='*130}")
    print(f"📊 主力资金 +5 日涨幅 综合排行榜 Top{top_n}")
    print(f"{'='*130}")
    print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'主力 (当日)':<12} {'3 日主力':<12} {'5 日涨幅':<10} {'综合评分':<8}")
    print(f"{'-'*130}")
    
    for i, s in enumerate(top_stocks, 1):
        def fmt(v):
            if abs(v) >= 100000000:
                return f"{v/100000000:.2f}亿"
            return f"{v/10000:.0f}万"
        
        net_main_str = fmt(s['net_main'])
        net_3d_str = fmt(s['net_3d'])
        change_sign = '+' if s['change_5d'] >= 0 else ''
        
        print(f"{i:<4} {s['symbol']:<10} {s['name']:<10} {net_main_str:>10} {net_3d_str:>10} {change_sign}{s['change_5d']:>7.2f}% {s['score']:>7.1f}")
    
    print(f"{'='*130}")
    
    # 推送
    if webhook:
        print("\n📤 正在推送到企业微信...")
        
        lines = [
            f"📊 **主力资金 +5 日涨幅 综合 Top{top_n}**",
            f"_数据源：{data_source}_",
            f"_更新时间：{datetime.now().strftime('%m-%d %H:%M')}_",
            "",
            "_综合评分 = 主力净流入 (60%) + 5 日涨幅 (40%)_",
            ""
        ]
        
        for i, s in enumerate(top_stocks, 1):
            def fmt(v):
                if abs(v) >= 100000000:
                    return f"{v/100000000:.2f}亿"
                return f"{v/10000:.0f}万"
            
            net_main_str = fmt(s['net_main'])
            net_3d_str = fmt(s['net_3d'])
            change_sign = '📈' if s['change_5d'] >= 0 else '📉'
            money_emoji = '💰' if s['net_main'] > 0 else '💸'
            
            lines.append(f"{i}. {change_sign} **{s['name']}** ({s['symbol']})")
            lines.append(f"   {money_emoji}主力：{net_main_str} | 3 日：{net_3d_str} | 5 日涨幅：{change_sign}{s['change_5d']:.2f}%")
        
        content = "\n".join(lines)
        success = push_to_corp_webhook(webhook, f"📊 主力 + 涨幅综合 Top{top_n}", content)
        return success
    
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='主力资金 +5 日涨幅综合排行')
    parser.add_argument('--top', type=int, default=10, help='前 N 只股票')
    parser.add_argument('--push', action='store_true', help='推送到企业微信')
    parser.add_argument('--webhook', type=str, help='企业微信 Webhook 地址')
    
    args = parser.parse_args()
    webhook = args.webhook or "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
    
    get_composite_rank(top_n=args.top, webhook=webhook if args.push else None)
