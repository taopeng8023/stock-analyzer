#!/usr/bin/env python3
"""
股票筛选与多因子决策工作流 - 多数据源版
使用腾讯 + 网易 + 东方财富多数据源轮询
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

print("="*70)
print("📊 股票筛选与多因子决策工作流 - 多数据源版")
print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

def get_all_stocks_from_qq():
    """从腾讯获取股票列表"""
    print("  [腾讯] 获取股票列表...")
    stocks = []
    prefixes = ['600', '601', '603', '605', '000', '001', '002', '003']
    
    for prefix in prefixes:
        for batch in range(0, 1000, 100):
            codes = [f"{'sh' if prefix.startswith('6') else 'sz'}{prefix}{i:03d}" for i in range(batch, min(batch+100, 1000))]
            try:
                resp = requests.get(f'http://qt.gtimg.cn/q={",".join(codes)}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                for line in resp.content.decode('gbk').strip().split('\n'):
                    if '=' in line:
                        parts = line.split('~')
                        if len(parts) >= 40 and parts[1] and float(parts[3]) > 0:
                            stocks.append({'code': parts[0].split('_')[-1][2:], 'name': parts[1]})
                time.sleep(0.05)
            except:
                pass
    return stocks

def get_data_from_qq(code):
    """腾讯数据源"""
    try:
        symbol = f'sh{code}' if code.startswith('6') else f'sz{code}'
        resp = requests.get(f'http://qt.gtimg.cn/q={symbol}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        parts = resp.content.decode('gbk').strip().split('~')
        if len(parts) >= 40 and float(parts[3]) > 0:
            return {
                'price': float(parts[3]),
                'change_pct': ((float(parts[3]) - float(parts[4])) / float(parts[4]) * 100) if float(parts[4]) > 0 else 0,
                'volume': int(parts[6]),
                'amount': float(parts[37]) if len(parts) > 37 else 0,
            }
    except:
        pass
    return None

def get_data_from_163(code):
    """网易数据源"""
    try:
        symbol = f'sh{code}' if code.startswith('6') else f'sz{code}'
        resp = requests.get(f'http://quotes.money.163.com/service/stockquote.html?code={symbol}&type=quote', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        # 解析 CSV 格式
        lines = resp.text.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split(',')
            if len(parts) >= 10 and float(parts[3]) > 0:
                return {
                    'price': float(parts[3]),
                    'change_pct': float(parts[15]) if len(parts) > 15 else 0,
                    'volume': int(float(parts[8])) if parts[8] else 0,
                    'amount': float(parts[9]) if parts[9] else 0,
                }
    except:
        pass
    return None

def get_data_from_eastmoney(code):
    """东方财富数据源"""
    try:
        symbol = '1' if code.startswith('6') else '0'
        url = f'http://push2.eastmoney.com/api/qt/stock/get?secid={symbol}.{code}&fields=f43,f44,f45,f46,f47,f48'
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        data = resp.json()
        if data.get('data') and data['data'].get('f46') > 0:
            d = data['data']
            return {
                'price': d.get('f43', 0) / 100,
                'change_pct': d.get('f14', 0),
                'volume': d.get('f47', 0),
                'amount': d.get('f48', 0) / 100000000,
            }
    except:
        pass
    return None

def get_vol_ma5_from_qq(code):
    """从腾讯获取 5 日均量"""
    try:
        symbol = f'sh{code}' if code.startswith('6') else f'sz{code}'
        resp = requests.get(f'http://data.gtimg.cn/flashdata/hushen/minute/{symbol}.js?maxcnt=32&datatype=1', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        volumes = []
        for line in resp.content.decode('gbk').strip().split('\n'):
            if '~' in line:
                parts = line.split('~')
                if len(parts) >= 7:
                    try:
                        volumes.append(int(parts[6]))
                        if len(volumes) >= 5:
                            break
                    except:
                        pass
        if len(volumes) >= 5:
            return sum(volumes) / len(volumes)
    except:
        pass
    return None

def get_stock_data(code):
    """多数据源轮询获取股票数据"""
    # 尝试不同数据源
    for source_name, source_func in [
        ('腾讯', get_data_from_qq),
        ('网易', get_data_from_163),
        ('东方财富', get_data_from_eastmoney),
    ]:
        data = source_func(code)
        if data:
            # 获取 5 日均量
            vol_ma5 = get_vol_ma5_from_qq(code)
            if vol_ma5 and vol_ma5 > 0:
                data['vol_ma5'] = vol_ma5
                data['volume_ratio'] = data['volume'] / (vol_ma5 + 1)
                return data
    
    return None

# ==================== 开始筛选 ====================
print("\n" + "="*70)
print("📋 阶段 1: 从全市场获取股票列表")
print("="*70)

stocks = get_all_stocks_from_qq()
print(f"\n获取到 {len(stocks)} 只真实交易的主板股票")

# 获取股票数据
print("\n获取股票数据（多数据源轮询）...")
quotes = []

for i, stock in enumerate(stocks):
    if (i + 1) % 100 == 0:
        print(f"  已处理 {i+1}/{len(stocks)} 只股票...")
    
    data = get_stock_data(stock['code'])
    if data and data.get('vol_ma5'):
        data['code'] = stock['code']
        data['name'] = stock['name']
        quotes.append(data)
    
    time.sleep(0.03)

print(f"\n✅ 获取到 {len(quotes)} 只股票的完整数据")

# 筛选
print("\n" + "="*70)
print("成交量放大筛选（严格执行>1.5 倍）")
print("="*70)

amplified = [q for q in quotes if q['volume_ratio'] > 1.5]
amplified.sort(key=lambda x: x['volume_ratio'], reverse=True)

print(f"\n成交量放大>1.5 倍：{len(amplified)}只")

if amplified:
    print("\n" + "="*110)
    print(f"{'排名':<6} {'股票':<12} {'代码':<10} {'股价':<10} {'涨幅':<12} {'成交量放大':<12} {'今日成交量':<14} {'5 日均量':<14}")
    print("="*110)
    
    for i, q in enumerate(amplified[:30], 1):
        print(f"{i:<6} {q['name']:<12} {q['code']:<10} ¥{q['price']:<8.2f} {q['change_pct']:>+10.2f}% {q['volume_ratio']:<11.2f}倍 {q['volume']/10000:<13.1f}万手 {q['vol_ma5']/10000:<13.1f}万手")
    
    print("="*110)
    print(f"\n✅ 候选股票池：{len(amplified)}只")
else:
    print("\n⚠️ 没有股票满足成交量放大>1.5 倍的条件")

print("\n✅ 多数据源筛选完成！")
