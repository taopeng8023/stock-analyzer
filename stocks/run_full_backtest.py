#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极策略优化回测 - 使用完整 2022-2026 数据

数据源: data_history_2022_2026 目录（约5,500只股票，4年+数据）
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import statistics
import time
import random

# 使用完整数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
RESULTS_DIR.mkdir(exist_ok=True)

def load_data(symbol):
    f = DATA_DIR / f'{symbol}.json'
    if not f.exists(): return None
    try:
        data = json.load(open(f))
        if 'items' not in data: return None
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except: return None

def calc_ma(s, p): return s.rolling(p).mean()

def backtest(df, fast=10, slow=20, stop_loss=0.05, take_profit=0.08, trailing=0.05):
    """双均线策略 + 止盈止损"""
    if len(df) < 50: return None
    
    mf = calc_ma(df['close'], fast)
    ms = calc_ma(df['close'], slow)
    
    capital = 100000
    position = 0
    cost = 0
    high = 0
    trades = []
    
    for i in range(slow + 5, len(df)):
        c = float(df['close'].iloc[i])
        
        if position > 0:
            high = max(high, c)
            # 止损
            if (c - cost) / cost <= -stop_loss:
                trades.append({'profit': (c - cost) * position, 'reason': 'stop'})
                capital = position * c * 0.997
                position = 0; continue
            # 止盈
            if (c - cost) / cost >= take_profit:
                trades.append({'profit': (c - cost) * position, 'reason': 'profit'})
                capital = position * c * 0.997
                position = 0; continue
            # 移动止盈
            if (high - c) / high >= trailing:
                trades.append({'profit': (c - cost) * position, 'reason': 'trail'})
                capital = position * c * 0.997
                position = 0; continue
        
        # 金叉买入
        if mf.iloc[i] > ms.iloc[i] and mf.iloc[i-1] <= ms.iloc[i-1] and position == 0:
            sh = int(capital * 0.95 / c / 100) * 100
            if sh >= 100:
                position = sh; cost = c; high = c
                capital -= sh * c * 1.001
        
        # 死叉卖出
        if mf.iloc[i] < ms.iloc[i] and mf.iloc[i-1] >= ms.iloc[i-1] and position > 0:
            trades.append({'profit': (c - cost) * position, 'reason': 'cross'})
            capital = position * c * 0.997
            position = 0
    
    # 强制平仓
    if position > 0:
        last = float(df['close'].iloc[-1])
        trades.append({'profit': (last - cost) * position, 'reason': 'force'})
    
    if not trades: return None
    
    wins = [t for t in trades if t['profit'] > 0]
    total = len(trades)
    win_rate = len(wins) / total if total else 0
    total_profit = sum([t['profit'] for t in trades])
    total_return = total_profit / 100000  # 相对初始资金
    
    return {
        'trades': total,
        'win_rate': win_rate,
        'total_return': total_return,
        'avg_profit': total_profit / total if total else 0
    }

print("="*70)
print("终极策略优化 - 使用完整 2022-2026 数据")
print("="*70)

# 获取股票列表
stocks = [f.stem for f in DATA_DIR.glob('*.json')]
print(f"股票总数: {len(stocks)}")

# 参数组合测试
configs = [
    ('MA5/20 SL5%TP8%Trail5%', 5, 20, 0.05, 0.08, 0.05),
    ('MA10/20 SL5%TP8%Trail5%', 10, 20, 0.05, 0.08, 0.05),
    ('MA10/30 SL5%TP8%Trail5%', 10, 30, 0.05, 0.08, 0.05),
    ('MA15/20 SL5%TP10%Trail5%', 15, 20, 0.05, 0.10, 0.05),
    ('MA5/20 SL8%TP15%Trail10%', 5, 20, 0.08, 0.15, 0.10),
    ('MA10/20 SL3%TP6%Trail3%', 10, 20, 0.03, 0.06, 0.03),
    ('MA7/21 SL5%TP10%Trail7%', 7, 21, 0.05, 0.10, 0.07),
    ('MA5/30 SL5%TP12%Trail8%', 5, 30, 0.05, 0.12, 0.08),
]

results = {name: {'returns': [], 'wins': [], 'trades': []} for name, *_ in configs}

start = time.time()

# 抽样测试
sample_size = 500
random.seed(42)
test_stocks = random.sample(stocks, min(sample_size, len(stocks)))
print(f"抽样测试: {sample_size} 只股票")

for i, sym in enumerate(test_stocks):
    df = load_data(sym)
    if df is None or len(df) < 100: continue
    
    for name, f, s, sl, tp, tr in configs:
        r = backtest(df, f, s, sl, tp, tr)
        if r and r['trades'] >= 2:
            results[name]['returns'].append(r['total_return'])
            results[name]['wins'].append(r['win_rate'])
            results[name]['trades'].append(r['trades'])
    
    if (i+1) % 100 == 0:
        print(f"进度: {i+1}/{len(test_stocks)}")

elapsed = time.time() - start

# 统计
print("\n" + "="*70)
print("策略排名结果")
print("="*70)

summary = []
for name, d in results.items():
    if len(d['returns']) < 10: continue
    avg_ret = statistics.mean(d['returns'])
    avg_win = statistics.mean(d['wins'])
    avg_tr = statistics.mean(d['trades'])
    
    # 综合评分: 胜率40% + 收益40% + 交易频率惩罚10%
    score = avg_win * 0.4 + min(max(avg_ret, -0.5), 0.5) * 0.4 + (avg_tr > 15) * -0.1
    summary.append({
        'name': name, 
        'count': len(d['returns']),
        'avg_win': avg_win,
        'avg_return': avg_ret,
        'avg_trades': avg_tr,
        'score': score
    })

summary.sort(key=lambda x: x['score'], reverse=True)

print("\n| 排名 | 策略参数 | 覆盖 | 平均胜率 | 平均收益 | 平均交易 | 综合评分 |")
print("|------|----------|------|---------|---------|---------|---------|")
for i, s in enumerate(summary, 1):
    print(f"| {i} | {s['name']:28s} | {s['count']:4d} | {s['avg_win']*100:5.1f}% | {s['avg_return']*100:+5.2f}% | {s['avg_trades']:4.1f} | {s['score']:+.3f} |")

# 推荐
if summary:
    best = summary[0]
    print(f"\n🏆 最佳策略: {best['name']}")
    print(f"   平均胜率: {best['avg_win']*100:.1f}%")
    print(f"   平均收益: {best['avg_return']*100:+.2f}%")
    print(f"   覆盖股票: {best['count']} 只")
    print(f"\n⏱️ 耗时: {elapsed:.1f}秒")

print("\n数据范围验证:")
sample_df = load_data('000001')
if sample_df:
    print(f"   第一条: {sample_df['date'].min().strftime('%Y-%m-%d')}")
    print(f"   最后条: {sample_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"   数据条数: {len(sample_df)}")