#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略参数优化器 - 流式版本 (逐个加载股票)
"""

import pandas as pd
import json
import warnings
from pathlib import Path
import time
import statistics
import random

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
RESULTS_DIR.mkdir(exist_ok=True)

# 简化的策略组合
STRATEGIES = [
    {'short': 5, 'long': 10, 'stop': 0.05, 'name': 'MA5/MA10+5%止盈'},
    {'short': 5, 'long': 10, 'stop': 0.10, 'name': 'MA5/MA10+10%止盈'},
    {'short': 5, 'long': 20, 'stop': 0.10, 'name': 'MA5/MA20+10%止盈'},
    {'short': 10, 'long': 20, 'stop': 0.05, 'name': 'MA10/MA20+5%止盈'},
    {'short': 10, 'long': 20, 'stop': 0.10, 'name': 'MA10/MA20+10%止盈'},
    {'short': 10, 'long': 20, 'stop': 0.15, 'name': 'MA10/MA20+15%止盈'},
    {'short': 15, 'long': 20, 'stop': 0.05, 'name': 'MA15/MA20+5%止盈'},
    {'short': 15, 'long': 20, 'stop': 0.10, 'name': 'MA15/MA20+10%止盈'},
    {'short': 20, 'long': 30, 'stop': 0.10, 'name': 'MA20/MA30+10%止盈'},
]


def load_stock(symbol):
    """加载单只股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except:
        return None


def backtest(data, short, long, stop):
    """快速回测"""
    if not data or 'items' not in data or len(data['items']) < long + 20:
        return None
    
    items = data['items']
    fields = data['fields']
    close_idx = fields.index('close')
    
    # 提取收盘价
    closes = []
    for item in items:
        try:
            closes.append(float(item[close_idx]))
        except:
            continue
    
    if len(closes) < long + 20:
        return None
    
    # 计算均线
    ma_s = []
    ma_l = []
    for i in range(len(closes)):
        if i >= short - 1:
            ma_s.append(sum(closes[i-short+1:i+1]) / short)
        else:
            ma_s.append(None)
        if i >= long - 1:
            ma_l.append(sum(closes[i-long+1:i+1]) / long)
        else:
            ma_l.append(None)
    
    # 回测
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(long + 5, len(closes)):
        price = closes[i]
        ms = ma_s[i]
        ml = ma_l[i]
        ms_p = ma_s[i-1]
        ml_p = ma_l[i-1]
        
        if None in [ms, ml, ms_p, ml_p]:
            continue
        
        # 止盈检查
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # 金叉
        if ms_p <= ml_p and ms > ml and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # 死叉
        elif ms_p >= ml_p and ms < ml and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    
    ret = (capital - 100000) / 100000
    wins = len([t for t in trades if t > 0])
    win_rate = wins / len(trades) * 100
    
    return {'return': ret, 'win_rate': win_rate, 'trades': len(trades)}


def main():
    print('=' * 80)
    print('📊 策略参数优化器')
    print('=' * 80)
    
    # 获取股票列表
    files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    
    # 抽样
    sample = 300
    random.seed(42)
    stocks = random.sample(files, min(sample, len(files)))
    
    print(f'抽样股票：{len(stocks)} 只')
    print(f'策略数量：{len(STRATEGIES)} 个')
    print()
    
    results = {}
    for s in STRATEGIES:
        results[s['name']] = []
    
    start = time.time()
    
    # 逐股票测试
    for i, sym in enumerate(stocks):
        data = load_stock(sym)
        if not data:
            continue
        
        for s in STRATEGIES:
            r = backtest(data, s['short'], s['long'], s['stop'])
            if r:
                results[s['name']].append(r)
        
        if (i+1) % 50 == 0:
            elapsed = time.time() - start
            print(f'进度: {i+1}/{len(stocks)} ({(i+1)/len(stocks)*100:.0f}%) 耗时: {elapsed:.0f}s')
    
    print()
    
    # 统计结果
    final = []
    for name, res in results.items():
        if not res:
            continue
        
        returns = [r['return'] for r in res]
        wins = [r['win_rate'] for r in res]
        
        final.append({
            'name': name,
            'count': len(res),
            'avg_ret': statistics.mean(returns) * 100,
            'med_ret': statistics.median(returns) * 100,
            'profit_pct': len([r for r in returns if r > 0]) / len(returns) * 100,
            'win_rate': statistics.mean(wins),
            'score': statistics.median(returns) * 100 + len([r for r in returns if r > 0]) / len(returns) * 20
        })
    
    # 排序
    final.sort(key=lambda x: x['score'], reverse=True)
    
    print('=' * 80)
    print('🏆 策略排名')
    print('=' * 80)
    print(f"{'排名':<4}{'策略':<25}{'中位收益':<10}{'盈利占比':<10}{'胜率':<8}{'评分':<8}")
    print('-' * 70)
    
    for i, r in enumerate(final, 1):
        print(f"{i:<4}{r['name']:<25}{r['med_ret']:>8.2f}%{r['profit_pct']:>8.1f}%{r['win_rate']:>6.1f}%{r['score']:>6.1f}")
    
    # 最优策略
    best = final[0]
    
    print()
    print('=' * 80)
    print('🎯 最优策略')
    print('=' * 80)
    print(f"策略: {best['name']}")
    print(f"测试股票: {best['count']} 只")
    print(f"中位收益: {best['med_ret']:.2f}%")
    print(f"平均收益: {best['avg_ret']:.2f}%")
    print(f"盈利占比: {best['profit_pct']:.1f}%")
    print(f"平均胜率: {best['win_rate']:.1f}%")
    
    # 保存
    df = pd.DataFrame(final)
    import datetime
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'optimizer_{ts}.csv'
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'\n💾 结果已保存: {out}')
    
    # 保存最优策略配置
    import json as j
    cfg = RESULTS_DIR / 'best_strategy.json'
    best_cfg = next(s for s in STRATEGIES if s['name'] == best['name'])
    best_cfg['stats'] = best
    with open(cfg, 'w') as f:
        j.dump(best_cfg, f, ensure_ascii=False, indent=2)
    print(f'💾 最优配置: {cfg}')
    
    elapsed = time.time() - start
    print(f'\n⏱️ 总耗时: {elapsed:.1f}s')
    
    return best


if __name__ == '__main__':
    main()