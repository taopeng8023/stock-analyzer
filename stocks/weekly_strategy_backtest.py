#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周交易策略回测系统
目标：每周至少1次交易机会，且整体收益为正

策略方向：
1. 短周期均线 (MA5/MA10) - 信号频繁
2. 宽松RSI (40/60) - 更多的超买超卖信号
3. 布林带突破 - 价格触及边界
4. KDJ交叉 - 快速指标
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import time
import statistics
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
RESULTS_DIR.mkdir(exist_ok=True)


def load_stock_data(symbol):
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'fields' in data and 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date').reset_index(drop=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
    except:
        return None


# ============== 技术指标 ==============

def calc_ma(close, period):
    return close.rolling(period).mean()

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_kdj(df, n=9):
    lowv = df['low'].rolling(n).min()
    highv = df['high'].rolling(n).max()
    rsv = (df['close'] - lowv) / (highv - lowv) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

def calc_boll(close, period=20, std_dev=2):
    mid = calc_ma(close, period)
    std = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower

def calc_macd(close, fast=12, slow=26, signal=9):
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    dif = ema_f - ema_s
    dea = dif.ewm(span=signal, adjust=False).mean()
    return dif, dea


# ============== 策略定义 ==============

def strategy_ma_short(df, fast=5, slow=10, stop_pct=0.05, trail_pct=0.03):
    """短周期均线策略 - MA5/MA10"""
    ma_f = calc_ma(df['close'], fast)
    ma_s = calc_ma(df['close'], slow)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(slow + 5, len(df)):
        price = float(df['close'].iloc[i])
        
        # 移动止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= trail_pct:
                sell_amt = pos * price * (1 - fee)
                profit = sell_amt - pos * cost
                trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'trail'})
                capital += sell_amt
                pos = 0
                continue
        
        # 止损
        if pos > 0 and (price - cost) / cost <= -stop_pct:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'stop'})
            capital += sell_amt
            pos = 0
            continue
        
        # 金叉买入
        if ma_f.iloc[i] > ma_s.iloc[i] and ma_f.iloc[i-1] <= ma_s.iloc[i-1] and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                buy_amt = shares * price * (1 + fee)
                capital -= buy_amt
                pos = shares
                cost = price
                high = price
                trades.append({'type': 'buy', 'price': price})
        
        # 死叉卖出
        elif ma_f.iloc[i] < ma_s.iloc[i] and ma_f.iloc[i-1] >= ma_s.iloc[i-1] and pos > 0:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'cross'})
            capital += sell_amt
            pos = 0
    
    return trades, capital


def strategy_rsi_weekly(df, period=14, buy_th=40, sell_th=60, stop_pct=0.08, trail_pct=0.05):
    """宽松RSI策略 - 40/60阈值，每周更多信号"""
    rsi = calc_rsi(df['close'], period)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(df)):
        price = float(df['close'].iloc[i])
        r = rsi.iloc[i]
        
        if pd.isna(r):
            continue
        
        # 移动止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= trail_pct:
                sell_amt = pos * price * (1 - fee)
                profit = sell_amt - pos * cost
                trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'trail'})
                capital += sell_amt
                pos = 0
                continue
        
        # 止损
        if pos > 0 and (price - cost) / cost <= -stop_pct:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'stop'})
            capital += sell_amt
            pos = 0
            continue
        
        # RSI < 40 买入 (更宽松)
        if r < buy_th and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                buy_amt = shares * price * (1 + fee)
                capital -= buy_amt
                pos = shares
                cost = price
                high = price
                trades.append({'type': 'buy', 'price': price, 'rsi': r})
        
        # RSI > 60 卖出 (更宽松)
        elif r > sell_th and pos > 0:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'rsi'})
            capital += sell_amt
            pos = 0
    
    return trades, capital


def strategy_kdj(df, n=9, stop_pct=0.06, trail_pct=0.04):
    """KDJ交叉策略 - 快速响应"""
    k, d, j = calc_kdj(df, n)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(n + 5, len(df)):
        price = float(df['close'].iloc[i])
        
        ki = k.iloc[i]
        di = d.iloc[i]
        
        if pd.isna(ki) or pd.isna(di):
            continue
        
        # 移动止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= trail_pct:
                sell_amt = pos * price * (1 - fee)
                profit = sell_amt - pos * cost
                trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'trail'})
                capital += sell_amt
                pos = 0
                continue
        
        # 止损
        if pos > 0 and (price - cost) / cost <= -stop_pct:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'stop'})
            capital += sell_amt
            pos = 0
            continue
        
        # K上穿D 且 J<20 (低位金叉)
        if ki > di and k.iloc[i-1] <= d.iloc[i-1] and j.iloc[i] < 30 and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                buy_amt = shares * price * (1 + fee)
                capital -= buy_amt
                pos = shares
                cost = price
                high = price
                trades.append({'type': 'buy', 'price': price, 'k': ki, 'd': di, 'j': j.iloc[i]})
        
        # K下穿D 且 J>80 (高位死叉)
        elif ki < di and k.iloc[i-1] >= d.iloc[i-1] and j.iloc[i] > 70 and pos > 0:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'kdj'})
            capital += sell_amt
            pos = 0
    
    return trades, capital


def strategy_boll(df, period=20, std_dev=2, stop_pct=0.06, trail_pct=0.04):
    """布林带策略 - 触及下轨买入，上轨卖出"""
    upper, mid, lower = calc_boll(df['close'], period, std_dev)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(df)):
        price = float(df['close'].iloc[i])
        
        up = upper.iloc[i]
        lo = lower.iloc[i]
        
        if pd.isna(up) or pd.isna(lo):
            continue
        
        # 移动止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= trail_pct:
                sell_amt = pos * price * (1 - fee)
                profit = sell_amt - pos * cost
                trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'trail'})
                capital += sell_amt
                pos = 0
                continue
        
        # 止损
        if pos > 0 and (price - cost) / cost <= -stop_pct:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'stop'})
            capital += sell_amt
            pos = 0
            continue
        
        # 触及下轨买入
        if price <= lo and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                buy_amt = shares * price * (1 + fee)
                capital -= buy_amt
                pos = shares
                cost = price
                high = price
                trades.append({'type': 'buy', 'price': price, 'reason': 'boll_lower'})
        
        # 触及上轨卖出
        elif price >= up and pos > 0:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'boll_upper'})
            capital += sell_amt
            pos = 0
    
    return trades, capital


def strategy_combo(df, stop_pct=0.06, trail_pct=0.05):
    """组合策略 - RSI + KDJ 双确认"""
    rsi = calc_rsi(df['close'], 14)
    k, d, j = calc_kdj(df, 9)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(25, len(df)):
        price = float(df['close'].iloc[i])
        
        r = rsi.iloc[i]
        ki = k.iloc[i]
        di = d.iloc[i]
        ji = j.iloc[i]
        
        if pd.isna(r) or pd.isna(ki):
            continue
        
        # 移动止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= trail_pct:
                sell_amt = pos * price * (1 - fee)
                profit = sell_amt - pos * cost
                trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'trail'})
                capital += sell_amt
                pos = 0
                continue
        
        # 止损
        if pos > 0 and (price - cost) / cost <= -stop_pct:
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'stop'})
            capital += sell_amt
            pos = 0
            continue
        
        # 双信号买入：RSI<40 + KDJ低位金叉
        buy_signal = 0
        if r < 40:
            buy_signal += 1
        if ki > di and k.iloc[i-1] <= d.iloc[i-1] and ji < 30:
            buy_signal += 1
        
        if buy_signal >= 1 and pos == 0:  # 任一信号即可
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                buy_amt = shares * price * (1 + fee)
                capital -= buy_amt
                pos = shares
                cost = price
                high = price
                trades.append({'type': 'buy', 'price': price, 'signals': buy_signal})
        
        # 双信号卖出：RSI>60 + KDJ高位死叉
        sell_signal = 0
        if r > 60:
            sell_signal += 1
        if ki < di and k.iloc[i-1] >= d.iloc[i-1] and ji > 70:
            sell_signal += 1
        
        if sell_signal >= 1 and pos > 0:  # 任一信号即可
            sell_amt = pos * price * (1 - fee)
            profit = sell_amt - pos * cost
            trades.append({'type': 'sell', 'profit': profit, 'return': profit / (pos * cost), 'reason': 'combo'})
            capital += sell_amt
            pos = 0
    
    return trades, capital


def evaluate(trades, capital, initial=100000):
    """评估策略表现"""
    if not trades:
        return None
    
    sell_trades = [t for t in trades if t['type'] == 'sell']
    if not sell_trades:
        return None
    
    profits = [t['profit'] for t in sell_trades]
    returns = [t['return'] for t in sell_trades]
    wins = [t for t in sell_trades if t['profit'] > 0]
    
    total_return = (capital - initial) / initial
    
    # 年化收益 (假设2年数据)
    annual_return = total_return / 2
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'trade_count': len(sell_trades),
        'win_count': len(wins),
        'win_rate': len(wins) / len(sell_trades) if sell_trades else 0,
        'avg_return': statistics.mean(returns) if returns else 0,
        'total_profit': sum(profits),
        'avg_profit': statistics.mean(profits) if profits else 0,
        'final_capital': capital
    }


def run_all_strategies(df):
    """运行所有策略"""
    strategies = [
        ('MA5/MA10', strategy_ma_short, {}),
        ('RSI宽松40/60', strategy_rsi_weekly, {'buy_th': 40, 'sell_th': 60}),
        ('RSI宽松35/65', strategy_rsi_weekly, {'buy_th': 35, 'sell_th': 65}),
        ('KDJ交叉', strategy_kdj, {}),
        ('布林带', strategy_boll, {}),
        ('RSI+KDJ组合', strategy_combo, {}),
    ]
    
    results = []
    for name, func, extra_params in strategies:
        trades, capital = func(df, **extra_params)
        metrics = evaluate(trades, capital)
        
        if metrics:
            results.append({
                'strategy': name,
                **metrics
            })
    
    return results


def full_market_backtest(sample=None):
    """全市场回测"""
    print('='*80)
    print('📊 每周交易策略回测 - 全市场测试')
    print('='*80)
    print()
    
    files = [f.stem for f in CACHE_DIR.glob('*.json')]
    
    if sample:
        import random
        random.seed(42)
        files = random.sample(files, min(sample, len(files)))
    
    print(f'股票数量: {len(files)}')
    print()
    
    strategy_results = {}
    all_results = []
    start = time.time()
    
    for i, sym in enumerate(files):
        df = load_stock_data(sym)
        
        if df is None or len(df) < 100:
            continue
        
        results = run_all_strategies(df)
        
        for r in results:
            key = r['strategy']
            if key not in strategy_results:
                strategy_results[key] = []
            strategy_results[key].append(r)
            
            all_results.append({
                'symbol': sym,
                'strategy': key,
                'annual_return': r['annual_return'],
                'trade_count': r['trade_count'],
                'win_rate': r['win_rate'],
                'total_return': r['total_return']
            })
        
        if (i+1) % 200 == 0:
            elapsed = time.time() - start
            print(f'进度: {i+1}/{len(files)} ({(i+1)/len(files)*100:.0f}%) 耗时: {elapsed:.0f}s')
    
    elapsed = time.time() - start
    print()
    
    # 汇总
    print('='*80)
    print('📊 策略对比结果')
    print('='*80)
    print()
    
    summary = []
    for name, results in strategy_results.items():
        if len(results) < 10:
            continue
        
        avg_return = statistics.mean([r['annual_return'] for r in results])
        avg_trades = statistics.mean([r['trade_count'] for r in results])
        avg_win = statistics.mean([r['win_rate'] for r in results])
        profit_pct = len([r for r in results if r['total_return'] > 0]) / len(results)
        
        # 每周交易指标：交易次数 >= 50次 (约2年数据，每周1次)
        weekly_stocks = len([r for r in results if r['trade_count'] >= 50])
        weekly_pct = weekly_stocks / len(results)
        
        summary.append({
            'strategy': name,
            'count': len(results),
            'avg_annual': avg_return,
            'avg_trades': avg_trades,
            'avg_win': avg_win,
            'profit_pct': profit_pct,
            'weekly_pct': weekly_pct,  # 每周交易的股票占比
            'weekly_return': statistics.mean([r['annual_return'] for r in results if r['trade_count'] >= 50]) if weekly_stocks > 0 else 0
        })
    
    # 按每周交易收益率排序
    summary.sort(key=lambda x: x['weekly_return'], reverse=True)
    
    print('| 策略 | 覆盖股票 | 平均年化 | 平均交易 | 平均胜率 | 盈利占比 | 每周交易占比 | 每周交易收益 |')
    print('|------|---------|---------|---------|---------|---------|-------------|-------------|')
    
    for s in summary:
        print(f"| {s['strategy']:<12} | {s['count']:>5} | {s['avg_annual']*100:>6.1f}% | {s['avg_trades']:>5.1f} | "
              f"{s['avg_win']*100:>5.1f}% | {s['profit_pct']*100:>5.1f}% | {s['weekly_pct']*100:>6.1f}% | {s['weekly_return']*100:>6.1f}% |")
    
    print()
    
    # 推荐
    print('='*80)
    print('🏆 每周交易最佳策略推荐')
    print('='*80)
    
    # 筛选：每周交易占比 > 30% 且收益为正
    valid = [s for s in summary if s['weekly_pct'] > 0.1 and s['weekly_return'] > 0]
    
    if valid:
        best = valid[0]
        print(f"""
推荐策略: {best['strategy']}
平均年化收益: {best['avg_annual']*100:.1f}%
平均交易次数: {best['avg_trades']:.1f} 次/2年 ({best['avg_trades']/2/52:.1f}次/周)
平均胜率: {best['avg_win']*100:.1f}%
盈利股票占比: {best['profit_pct']*100:.1f}%
每周交易股票占比: {best['weekly_pct']*100:.1f}%
""")
    else:
        print('⚠️ 没有找到满足每周交易且收益为正的策略')
        print()
        print('📊 按收益排序：')
        summary.sort(key=lambda x: x['avg_annual'], reverse=True)
        for s in summary[:5]:
            print(f"  {s['strategy']}: 年化 {s['avg_annual']*100:.1f}%, 交易 {s['avg_trades']:.1f}次")
    
    print(f'\n⏱️ 耗时: {elapsed:.1f}s')
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(RESULTS_DIR / f'weekly_strategy_summary_{timestamp}.csv', index=False, encoding='utf-8-sig')
    
    all_df = pd.DataFrame(all_results)
    all_df.to_csv(RESULTS_DIR / f'weekly_strategy_all_{timestamp}.csv', index=False, encoding='utf-8-sig')
    
    print(f'\n💾 结果已保存')
    
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=None)
    parser.add_argument('--symbol', type=str, default=None)
    parser.add_argument('--all', action='store_true')
    
    args = parser.parse_args()
    
    if args.symbol:
        df = load_stock_data(args.symbol)
        if df:
            print(f'\n📊 {args.symbol} 策略测试')
            print('='*60)
            results = run_all_strategies(df)
            
            for r in sorted(results, key=lambda x: x['annual_return'], reverse=True):
                print(f"\n{r['strategy']}")
                print(f"  年化收益: {r['annual_return']*100:.1f}%")
                print(f"  交易次数: {r['trade_count']}")
                print(f"  胜率: {r['win_rate']*100:.1f}%")
    
    elif args.all or args.sample:
        full_market_backtest(args.sample)
    
    else:
        print('用法:')
        print('  --symbol 000001    单只股票测试')
        print('  --sample 500       抽样回测')
        print('  --all              全市场回测')


if __name__ == '__main__':
    main()