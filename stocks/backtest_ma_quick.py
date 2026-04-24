#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线优化策略回测 - 简化快速版
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import random
import warnings
warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

def load_data(symbol):
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data or len(data) < 100:
        return None
    df = pd.DataFrame(data)
    df = df.rename(columns={'日期':'date','收盘':'close','最高':'high','最低':'low','成交量':'volume'})
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df.sort_values('date').reset_index(drop=True)

def backtest(df, version='v3'):
    """回测"""
    if len(df) < 100:
        return None
    
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    filtered = 0
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        ma15 = df['ma15'].iloc[idx]
        ma20 = df['ma20'].iloc[idx]
        ma15_prev = df['ma15'].iloc[idx-1]
        ma20_prev = df['ma20'].iloc[idx-1]
        ma60 = df['ma60'].iloc[idx]
        vol_ratio = df['volume'].iloc[idx] / df['vol_ma20'].iloc[idx] if df['vol_ma20'].iloc[idx] > 0 else 0
        cross_strength = (ma15 - ma20) / ma20 * 100 if pd.notna(ma20) and ma20 > 0 else 0
        
        if pd.isna([ma15, ma20, ma15_prev, ma20_prev, ma60]).any():
            continue
        
        # 持仓管理
        if position:
            highest = max(highest, price)
            # 移动止盈 15%
            if highest > position['cost'] * 1.10 and price <= highest * 0.85:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
            # 止损 15%
            elif price <= position['cost'] * 0.85:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
        
        # 金叉
        golden = ma15_prev <= ma20_prev and ma15 > ma20
        
        if golden and not position:
            # 过滤检查
            reject = False
            
            # V1: 成交量
            if version in ['v1','v2','v3'] and vol_ratio < 1.5:
                reject = True
            
            # V2: 趋势
            if version in ['v2','v3'] and price <= ma60:
                reject = True
            
            # V3: 强度
            if version == 'v3' and cross_strength < 0.5:
                reject = True
            
            if reject:
                filtered += 1
            else:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares}
                    highest = price
        
        # 死叉卖出
        death = ma15_prev >= ma20_prev and ma15 < ma20
        if death and position:
            profit = (price - position['cost']) / position['cost'] * 100
            trades.append(profit)
            capital = position['shares'] * price * 0.9997
            position = None
            highest = 0
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
        'filtered': filtered
    }

def main():
    print("=" * 80)
    print("🔬 双均线优化策略回测")
    print("=" * 80)
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    sampled = random.sample(stock_files, min(500, len(stock_files)))
    
    print(f"\n📊 抽样：{len(sampled)}只股票")
    print(f"📋 对比：基础版 vs V1(量) vs V2(量 + 势) vs V3(量 + 势 + 强度)\n")
    
    versions = ['base', 'v1', 'v2', 'v3']
    all_results = {v: [] for v in versions}
    
    for i, filepath in enumerate(sampled):
        symbol = filepath.stem
        df = load_data(symbol)
        if df is None:
            continue
        
        for ver in versions:
            r = backtest(df, ver)
            if r:
                r['symbol'] = symbol
                all_results[ver].append(r)
        
        if (i + 1) % 100 == 0:
            print(f"  进度：{i+1}/{len(sampled)}")
    
    print(f"\n✅ 完成\n")
    
    # 输出
    print("=" * 80)
    print("📊 策略对比")
    print("=" * 80)
    print(f"\n{'版本':<20} {'平均收益':>12} {'胜率':>10} {'盈利股':>10} {'过滤':>10}")
    print("-" * 65)
    
    for ver in versions:
        r = all_results[ver]
        if r:
            avg_ret = np.mean([x['return'] for x in r])
            avg_wr = np.mean([x['win_rate'] for x in r])
            prof = len([x for x in r if x['return'] > 0]) / len(r) * 100
            avg_f = np.mean([x['filtered'] for x in r])
            name = '基础版' if ver=='base' else 'V1(+ 成交量)' if ver=='v1' else 'V2(+ 量 + 势)' if ver=='v2' else 'V3(完全版)'
            print(f"{name:<20} {avg_ret:>10.2f}% {avg_wr:>8.1f}% {prof:>8.1f}% {avg_f:>8.1f}")
    
    # 最佳
    print("\n" + "=" * 80)
    best_ver = max(versions, key=lambda v: np.mean([x['return'] for x in all_results[v]]) if all_results[v] else -999)
    best_name = '基础版' if best_ver=='base' else 'V1(+ 成交量)' if best_ver=='v1' else 'V2(+ 量 + 势)' if best_ver=='v2' else 'V3(完全版)'
    best_avg = np.mean([x['return'] for x in all_results[best_ver]])
    
    print(f"🏆 最佳：{best_name} ({best_avg:.2f}%)")
    
    # TOP5
    results = all_results[best_ver]
    results.sort(key=lambda x: x['return'], reverse=True)
    print(f"\n🏆 {best_name} TOP 5:")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r['symbol']}: {r['return']:+.2f}% (过滤{r['filtered']}个假信号)")
    
    print("\n" + "=" * 80)
    print("=" * 80)

if __name__ == '__main__':
    main()
