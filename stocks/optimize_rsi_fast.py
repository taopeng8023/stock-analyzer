#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速RSI策略优化"""

import json
import warnings
from pathlib import Path
import time
import statistics
import random

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')


def load_stock(symbol):
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def extract_prices(data):
    if not data or 'items' not in data:
        return None
    
    items = data['items']
    fields = data['fields']
    
    try:
        close_idx = fields.index('close')
        vol_idx = fields.index('vol')
    except:
        return None
    
    closes = []
    volumes = []
    for item in items:
        try:
            closes.append(float(item[close_idx]))
            volumes.append(float(item[vol_idx]))
        except:
            continue
    
    return {'close': closes, 'volume': volumes}


def calc_rsi(closes, period, idx):
    if idx < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(idx-period, idx+1):
        change = closes[i] - closes[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))


def calc_ma(closes, period, idx):
    if idx < period - 1:
        return None
    return sum(closes[idx-period+1:idx+1]) / period


def backtest_rsi(closes, volumes, params):
    """通用RSI回测"""
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    
    # 过滤条件
    use_trend = params.get('use_trend', False)
    trend_ma = params.get('trend_ma', 60)
    use_volume = params.get('use_volume', False)
    vol_ratio = params.get('vol_ratio', 1.2)
    use_double = params.get('use_double', False)
    use_stop_loss = params.get('use_stop_loss', False)
    stop_loss = params.get('stop_loss', 0.08)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    rsi_hist = []
    
    start_idx = max(period + 5, trend_ma if use_trend else 0, 20 if use_volume else 0)
    
    for i in range(start_idx, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        
        if rsi is None:
            continue
        
        rsi_hist.append(rsi)
        
        # 止盈止损检查
        if pos > 0:
            if price > high:
                high = price
            
            # 止盈
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
            
            # 止损（如果启用）
            if use_stop_loss and (cost - price) / cost >= stop_loss:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # 买入条件
        if pos == 0:
            buy_signal = False
            
            # 基础条件：RSI超卖
            if rsi < buy_th:
                buy_signal = True
            
            # 二次确认
            if use_double and len(rsi_hist) >= 2:
                prev_rsi = rsi_hist[-2]
                if not (rsi < buy_th and rsi > prev_rsi):
                    buy_signal = False
            
            # 趋势过滤
            if use_trend and buy_signal:
                ma = calc_ma(closes, trend_ma, i)
                if ma and price < ma * 0.98:
                    buy_signal = False
            
            # 成交量过滤
            if use_volume and buy_signal:
                avg_vol = sum(volumes[i-20:i]) / 20
                if volumes[i] < avg_vol * vol_ratio:
                    buy_signal = False
            
            if buy_signal:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    amt = shares * price
                    capital -= amt + amt * fee
                    pos = shares
                    cost = price
                    high = price
        
        # 卖出条件
        elif pos > 0:
            if rsi > sell_th:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
            
            # 跌破趋势线卖出
            if use_trend:
                ma = calc_ma(closes, trend_ma, i)
                if ma and price < ma * 0.95:
                    amt = pos * price
                    trades.append(amt - pos * cost - amt * fee)
                    capital += amt - amt * fee
                    pos = 0
    
    if not trades:
        return None
    
    returns = [t / 100000 for t in trades]
    wins = len([t for t in trades if t > 0])
    
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': wins / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


# 策略配置
STRATEGIES = [
    {'name': '基础RSI(25/75)', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15}},
    {'name': 'RSI宽松(20/80)', 'params': {'buy_th': 20, 'sell_th': 80, 'stop': 0.15}},
    {'name': 'RSI严格(30/70)', 'params': {'buy_th': 30, 'sell_th': 70, 'stop': 0.15}},
    {'name': 'RSI+趋势MA60', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'trend_ma': 60}},
    {'name': 'RSI+趋势MA30', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'trend_ma': 30}},
    {'name': 'RSI+放量1.2倍', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_volume': True, 'vol_ratio': 1.2}},
    {'name': 'RSI+放量1.5倍', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_volume': True, 'vol_ratio': 1.5}},
    {'name': 'RSI+二次确认', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_double': True}},
    {'name': 'RSI+止损8%', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_stop_loss': True, 'stop_loss': 0.08}},
    {'name': 'RSI+止损5%', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_stop_loss': True, 'stop_loss': 0.05}},
    {'name': '综合(趋势+放量)', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'trend_ma': 60, 'use_volume': True, 'vol_ratio': 1.2}},
    {'name': '综合(趋势+二次)', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'trend_ma': 30, 'use_double': True}},
    {'name': '综合+止损', 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'trend_ma': 60, 'use_stop_loss': True, 'stop_loss': 0.08}},
]


def main():
    print('=' * 80)
    print('📊 快速RSI策略优化')
    print('=' * 80)
    
    files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    
    # 抽样1500只
    random.seed(42)
    stocks = random.sample(files, min(1500, len(files)))
    
    print(f'抽样股票：{len(stocks)} 只')
    print(f'策略数量：{len(STRATEGIES)} 个')
    print()
    
    results = {s['name']: [] for s in STRATEGIES}
    start = time.time()
    
    for i, sym in enumerate(stocks):
        raw = load_stock(sym)
        data = extract_prices(raw)
        
        if not data or len(data['close']) < 80:
            continue
        
        for s in STRATEGIES:
            try:
                r = backtest_rsi(data['close'], data['volume'], s['params'])
                if r:
                    results[s['name']].append(r)
            except:
                continue
        
        if (i+1) % 300 == 0:
            elapsed = time.time() - start
            print(f'进度: {i+1}/{len(stocks)} ({(i+1)/len(stocks)*100:.0f}%) 耗时: {elapsed:.0f}s')
    
    elapsed = time.time() - start
    print()
    
    # 统计
    final = []
    for name, res in results.items():
        if not res:
            continue
        
        returns = [r['return'] for r in res]
        win_rates = [r['win_rate'] for r in res]
        
        final.append({
            'name': name,
            'count': len(res),
            'avg_ret': statistics.mean(returns) * 100,
            'med_ret': statistics.median(returns) * 100,
            'profit_pct': len([r for r in returns if r > 0]) / len(returns) * 100,
            'win_rate': statistics.mean(win_rates),
            'avg_trades': statistics.mean([r['trades'] for r in res]),
        })
    
    # 按胜率排序
    final.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print('=' * 80)
    print('🏆 策略排名 (按胜率)')
    print('=' * 80)
    print(f"{'排名':<4}{'策略':<22}{'胜率':<8}{'盈利占比':<10}{'中位收益':<10}{'交易次数':<8}")
    print('-' * 62)
    
    for i, r in enumerate(final, 1):
        print(f"{i:<4}{r['name']:<22}{r['win_rate']:>6.1f}%{r['profit_pct']:>8.1f}%{r['med_ret']:>8.2f}%{r['avg_trades']:>6.1f}")
    
    best = final[0]
    
    print()
    print('=' * 80)
    print(f'🎯 最高胜率策略：{best["name"]}')
    print('=' * 80)
    print(f"测试股票：{best['count']} 只")
    print(f"平均胜率：{best['win_rate']:.1f}%")
    print(f"盈利占比：{best['profit_pct']:.1f}%")
    print(f"中位收益：{best['med_ret']:.2f}%")
    print(f"平均交易：{best['avg_trades']:.1f} 次")
    
    # 按收益排序
    print()
    print('=' * 80)
    print('📈 策略排名 (按中位收益)')
    print('=' * 80)
    
    by_return = sorted(final, key=lambda x: x['med_ret'], reverse=True)
    print(f"{'排名':<4}{'策略':<22}{'中位收益':<10}{'胜率':<8}{'盈利占比':<10}")
    print('-' * 54)
    
    for i, r in enumerate(by_return[:5], 1):
        print(f"{i:<4}{r['name']:<22}{r['med_ret']:>8.2f}%{r['win_rate']:>6.1f}%{r['profit_pct']:>8.1f}%")
    
    # 保存
    import pandas as pd
    import datetime
    df = pd.DataFrame(final)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'rsi_optimized_fast_{ts}.csv'
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'\n💾 结果：{out}')
    
    # 最优配置
    best_s = next(s for s in STRATEGIES if s['name'] == best['name'])
    best_s['stats'] = best
    cfg = RESULTS_DIR / 'best_rsi_strategy_optimized.json'
    with open(cfg, 'w') as f:
        json.dump(best_s, f, ensure_ascii=False, indent=2)
    print(f'💾 配置：{cfg}')
    
    print(f'\n⏱️ 总耗时：{elapsed:.1f}s')
    
    return final


if __name__ == '__main__':
    main()