#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略对比回测 - 快速抽样版
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

def load_data(symbol: str):
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data or len(data) < 100:
        return None
    df = pd.DataFrame(data)
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume'
    })
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df.sort_values('date').reset_index(drop=True)

def backtest_momentum(df):
    """动量策略：20 日强势股"""
    if len(df) < 80:
        return None
    
    df['mom_20d'] = df['close'].pct_change(20)
    
    capital = 100000
    trades = []
    position = None
    
    for idx in range(60, len(df)):
        mom = df['mom_20d'].iloc[idx]
        if pd.isna(mom):
            continue
        
        if not position and mom > 0.15:  # 20 日涨>15%
            price = df['close'].iloc[idx]
            if pd.notna(price) and price > 0:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares}
        
        if position:
            price = df['close'].iloc[idx]
            # 持有 5 天或止损
            if price <= position['cost'] * 0.88:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            elif df.index[idx] - df.index[df.index.get_loc(idx)] >= 5:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades)
    }

def backtest_breakout(df):
    """突破策略：20 日高点突破"""
    if len(df) < 80:
        return None
    
    df['high_20d'] = df['high'].rolling(20).max()
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    
    capital = 100000
    trades = []
    position = None
    highest = 0
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        
        if position:
            highest = max(highest, price)
            # 移动止盈 10%
            if highest > position['cost']*1.08 and price <= highest*0.9:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 止损 10%
            elif price <= position['cost']*0.9:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 突破 + 放量
        if not position:
            vol_ratio = df['volume'].iloc[idx] / df['vol_ma20'].iloc[idx] if df['vol_ma20'].iloc[idx] > 0 else 0
            if price > df['high_20d'].iloc[idx-1] and vol_ratio > 1.5:
                if pd.notna(price) and price > 0:
                    shares = int(capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        position = {'cost': price, 'shares': shares}
                        highest = price
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades)
    }

def backtest_rsi(df):
    """RSI 超卖反弹"""
    if len(df) < 80:
        return None
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    capital = 100000
    trades = []
    position = None
    
    for idx in range(50, len(df)):
        rsi = df['rsi'].iloc[idx]
        if pd.isna(rsi):
            continue
        
        price = df['close'].iloc[idx]
        
        if position:
            # RSI>50 卖出
            if rsi > 50:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 止损 8%
            elif price <= position['cost']*0.92:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # RSI<30 超卖
        if not position and rsi < 30:
            if pd.notna(price) and price > 0:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares}
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades)
    }

def main():
    print("=" * 80)
    print("🔬 多策略对比回测 (快速抽样版)")
    print("=" * 80)
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    sampled = random.sample(stock_files, min(500, len(stock_files)))
    
    print(f"\n📊 抽样：{len(sampled)}只股票")
    print(f"📋 策略：动量 | 突破 | RSI 超卖\n")
    
    results = {'momentum': [], 'breakout': [], 'rsi': []}
    
    for i, filepath in enumerate(sampled):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is None:
            continue
        
        r = backtest_momentum(df)
        if r:
            r['symbol'] = symbol
            results['momentum'].append(r)
        
        r = backtest_breakout(df)
        if r:
            r['symbol'] = symbol
            results['breakout'].append(r)
        
        r = backtest_rsi(df)
        if r:
            r['symbol'] = symbol
            results['rsi'].append(r)
        
        if (i + 1) % 100 == 0:
            print(f"  进度：{i+1}/{len(sampled)}")
    
    print(f"\n✅ 完成\n")
    
    # 输出
    print("=" * 80)
    print("📊 策略对比")
    print("=" * 80)
    print(f"\n{'策略':<15} {'平均收益':>12} {'胜率':>10} {'盈利股':>10} {'交易':>8}")
    print("-" * 60)
    
    for name, key in [('动量策略', 'momentum'), ('突破策略', 'breakout'), ('RSI 超卖', 'rsi')]:
        r = results[key]
        if r:
            avg_ret = np.mean([x['return'] for x in r])
            avg_wr = np.mean([x['win_rate'] for x in r])
            prof = len([x for x in r if x['return'] > 0]) / len(r) * 100
            avg_t = np.mean([x['trades'] for x in r])
            print(f"{name:<15} {avg_ret:>10.2f}% {avg_wr:>8.1f}% {prof:>8.1f}% {avg_t:>8.1f}")
    
    print("-" * 60)
    print(f"{'双均线 (参考)':<15} {20.00:>10.2f}% {58.0:>8.1f}% {65.0:>8.1f} {2.0:>8.1f}")
    
    # 最佳
    print("\n" + "=" * 80)
    best_key = max(results.keys(), key=lambda k: np.mean([x['return'] for x in results[k]]) if results[k] else -999)
    best_name = '动量策略' if best_key == 'momentum' else '突破策略' if best_key == 'breakout' else 'RSI 超卖'
    best_avg = np.mean([x['return'] for x in results[best_key]])
    
    print(f"🏆 最佳：{best_name} ({best_avg:.2f}%)")
    
    if best_avg > 20:
        print("✅ 优于双均线！")
    elif best_avg > 15:
        print("👍 与双均线相当")
    else:
        print("⚠️ 不如双均线")
    
    print("=" * 80)

if __name__ == '__main__':
    main()
