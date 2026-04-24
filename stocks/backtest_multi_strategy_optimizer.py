#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略优化器 - 测试 RSI、布林带、MACD、突破等多种策略
"""

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
    """提取价格数据"""
    if not data or 'items' not in data:
        return None
    
    items = data['items']
    fields = data['fields']
    
    try:
        close_idx = fields.index('close')
        high_idx = fields.index('high')
        low_idx = fields.index('low')
        vol_idx = fields.index('vol')
    except:
        return None
    
    closes = []
    highs = []
    lows = []
    volumes = []
    
    for item in items:
        try:
            closes.append(float(item[close_idx]))
            highs.append(float(item[high_idx]))
            lows.append(float(item[low_idx]))
            volumes.append(float(item[vol_idx]))
        except:
            continue
    
    return {'close': closes, 'high': highs, 'low': lows, 'volume': volumes}


def calc_ma(data, period, idx):
    """计算MA"""
    if idx < period - 1:
        return None
    return sum(data['close'][idx-period+1:idx+1]) / period


def calc_rsi(data, period, idx):
    """计算RSI"""
    if idx < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(idx-period, idx+1):
        change = data['close'][i] - data['close'][i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))


def calc_bollinger(data, period, idx):
    """计算布林带"""
    if idx < period - 1:
        return None, None, None
    
    closes = data['close'][idx-period+1:idx+1]
    ma = sum(closes) / period
    
    # 标准差
    variance = sum((c - ma) ** 2 for c in closes) / period
    std = variance ** 0.5
    
    upper = ma + 2 * std
    lower = ma - 2 * std
    
    return upper, ma, lower


def calc_macd(data, idx):
    """计算MACD"""
    if idx < 26:
        return None, None
    
    # EMA12
    ema12 = data['close'][0]
    k12 = 2 / 13
    for i in range(1, idx+1):
        ema12 = data['close'][i] * k12 + ema12 * (1 - k12)
    
    # EMA26
    ema26 = data['close'][0]
    k26 = 2 / 27
    for i in range(1, idx+1):
        ema26 = data['close'][i] * k26 + ema26 * (1 - k26)
    
    dif = ema12 - ema26
    return dif, ema12 - ema26


# ============== 策略定义 ==============

def strategy_rsi(data, params):
    """RSI策略: RSI<30买入, RSI>70卖出"""
    closes = data['close']
    period = params.get('period', 14)
    stop = params.get('stop', 0.10)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        rsi = calc_rsi(data, period, i)
        
        if rsi is None:
            continue
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # RSI<30 超卖买入
        if rsi < 30 and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # RSI>70 超买卖出
        elif rsi > 70 and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


def strategy_bollinger(data, params):
    """布林带策略: 价格触及下轨买入, 触及上轨卖出"""
    closes = data['close']
    period = params.get('period', 20)
    stop = params.get('stop', 0.10)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        upper, mid, lower = calc_bollinger(data, period, i)
        
        if upper is None:
            continue
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # 价格跌破下轨买入
        if price < lower and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # 价格突破上轨卖出
        elif price > upper and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


def strategy_breakout(data, params):
    """突破策略: 突破N日高点买入, 跌破N日低点卖出"""
    closes = data['close']
    highs = data['high']
    lows = data['low']
    period = params.get('period', 20)
    stop = params.get('stop', 0.10)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # 前N日高低点
        prev_high = max(highs[i-period:i])
        prev_low = min(lows[i-period:i])
        
        # 突破高点买入
        if price > prev_high and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # 跌破低点卖出
        elif price < prev_low and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


def strategy_macd(data, params):
    """MACD策略: DIF金叉买入, DIF死叉卖出"""
    closes = data['close']
    stop = params.get('stop', 0.10)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    prev_dif = None
    
    for i in range(35, len(closes)):
        price = closes[i]
        
        # 计算DIF
        # EMA12
        ema12 = closes[0]
        for j in range(1, i+1):
            ema12 = closes[j] * 2/13 + ema12 * 11/13
        
        # EMA26
        ema26 = closes[0]
        for j in range(1, i+1):
            ema26 = closes[j] * 2/27 + ema26 * 25/27
        
        dif = ema12 - ema26
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                prev_dif = dif
                continue
        
        if prev_dif is not None:
            # DIF金叉 (从负转正)
            if prev_dif < 0 and dif > 0 and pos == 0:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    amt = shares * price
                    capital -= amt + amt * fee
                    pos = shares
                    cost = price
                    high = price
            
            # DIF死叉 (从正转负)
            elif prev_dif > 0 and dif < 0 and pos > 0:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
        
        prev_dif = dif
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


def strategy_volume_breakout(data, params):
    """缩量突破策略: 放量突破买入"""
    closes = data['close']
    highs = data['high']
    volumes = data['volume']
    period = params.get('period', 20)
    vol_ratio = params.get('vol_ratio', 1.5)
    stop = params.get('stop', 0.10)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        vol = volumes[i]
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        avg_vol = sum(volumes[i-period:i]) / period
        prev_high = max(highs[i-period:i])
        
        # 放量突破买入
        if price > prev_high and vol > avg_vol * vol_ratio and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # 跌破均线卖出
        ma20 = sum(closes[i-20:i]) / 20 if i >= 20 else None
        if ma20 and price < ma20 * 0.95 and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


def strategy_trend_follow(data, params):
    """趋势跟踪策略: 站上MA60买入, 跌破MA60卖出"""
    closes = data['close']
    period = params.get('period', 60)
    stop = params.get('stop', 0.15)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        ma = calc_ma({'close': closes}, period, i)
        
        if ma is None:
            continue
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # 站上均线买入
        if price > ma * 1.02 and pos == 0:  # 确认突破
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # 跌破均线卖出
        elif price < ma * 0.98 and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


def strategy_dip_buy(data, params):
    """抄底策略: 连续下跌后反弹买入"""
    closes = data['close']
    drop_days = params.get('drop_days', 3)
    drop_pct = params.get('drop_pct', 0.05)
    stop = params.get('stop', 0.10)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(drop_days + 5, len(closes)):
        price = closes[i]
        
        # 止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                continue
        
        # 检查连续下跌
        consecutive_drop = True
        total_drop = 0
        for j in range(i-drop_days, i):
            if closes[j] >= closes[j-1]:
                consecutive_drop = False
                break
            total_drop += (closes[j-1] - closes[j]) / closes[j-1]
        
        # 连续下跌超过阈值，今日反弹买入
        if consecutive_drop and total_drop >= drop_pct and price > closes[i-1] and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # 跌破成本价5%止损
        elif pos > 0 and price < cost * 0.95:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {'return': (capital - 100000) / 100000, 'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100, 'trades': len(trades)}


# ============== 主程序 ==============

STRATEGIES = [
    {'name': 'RSI超买卖卖', 'func': strategy_rsi, 'params': {'period': 14, 'stop': 0.10}},
    {'name': 'RSI宽松(25/75)', 'func': strategy_rsi, 'params': {'period': 14, 'stop': 0.15}},
    {'name': '布林带突破', 'func': strategy_bollinger, 'params': {'period': 20, 'stop': 0.10}},
    {'name': '布林带宽松', 'func': strategy_bollinger, 'params': {'period': 20, 'stop': 0.15}},
    {'name': 'N日突破', 'func': strategy_breakout, 'params': {'period': 20, 'stop': 0.10}},
    {'name': '10日突破', 'func': strategy_breakout, 'params': {'period': 10, 'stop': 0.10}},
    {'name': 'MACD金叉', 'func': strategy_macd, 'params': {'stop': 0.10}},
    {'name': '放量突破', 'func': strategy_volume_breakout, 'params': {'period': 20, 'vol_ratio': 1.5, 'stop': 0.10}},
    {'name': '趋势跟踪MA60', 'func': strategy_trend_follow, 'params': {'period': 60, 'stop': 0.15}},
    {'name': '趋势跟踪MA30', 'func': strategy_trend_follow, 'params': {'period': 30, 'stop': 0.10}},
    {'name': '抄底策略', 'func': strategy_dip_buy, 'params': {'drop_days': 3, 'drop_pct': 0.05, 'stop': 0.10}},
    {'name': '抄底宽松', 'func': strategy_dip_buy, 'params': {'drop_days': 5, 'drop_pct': 0.08, 'stop': 0.15}},
]


def main():
    print('=' * 80)
    print('📊 多策略优化器 - 测试 RSI/布林带/MACD/突破等策略')
    print('=' * 80)
    
    files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    
    sample = 500
    random.seed(42)
    stocks = random.sample(files, min(sample, len(files)))
    
    print(f'抽样股票：{len(stocks)} 只')
    print(f'策略数量：{len(STRATEGIES)} 个')
    print()
    
    results = {}
    for s in STRATEGIES:
        results[s['name']] = []
    
    start = time.time()
    
    for i, sym in enumerate(stocks):
        raw = load_stock(sym)
        data = extract_prices(raw)
        
        if not data or len(data['close']) < 100:
            continue
        
        for s in STRATEGIES:
            try:
                r = s['func'](data, s['params'])
                if r:
                    results[s['name']].append(r)
            except:
                continue
        
        if (i+1) % 100 == 0:
            elapsed = time.time() - start
            print(f'进度: {i+1}/{len(stocks)} ({(i+1)/len(stocks)*100:.0f}%) 耗时: {elapsed:.0f}s')
    
    print()
    
    # 统计
    final = []
    for name, res in results.items():
        if not res:
            continue
        
        returns = [r['return'] for r in res]
        wins = [r['win_rate'] for r in res]
        
        # 综合评分
        median_ret = statistics.median(returns) * 100
        profit_pct = len([r for r in returns if r > 0]) / len(returns) * 100
        avg_win = statistics.mean(wins)
        
        score = median_ret + profit_pct * 0.5 + avg_win * 0.3
        
        final.append({
            'name': name,
            'count': len(res),
            'avg_ret': statistics.mean(returns) * 100,
            'med_ret': median_ret,
            'profit_pct': profit_pct,
            'win_rate': avg_win,
            'score': score,
            'max_ret': max(returns) * 100,
            'min_ret': min(returns) * 100,
        })
    
    final.sort(key=lambda x: x['score'], reverse=True)
    
    print('=' * 80)
    print('🏆 策略排名')
    print('=' * 80)
    print(f"{'排名':<4}{'策略':<20}{'中位收益':<10}{'盈利占比':<10}{'胜率':<8}{'评分':<8}")
    print('-' * 60)
    
    for i, r in enumerate(final, 1):
        print(f"{i:<4}{r['name']:<20}{r['med_ret']:>8.2f}%{r['profit_pct']:>8.1f}%{r['win_rate']:>6.1f}%{r['score']:>6.1f}")
    
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
    print(f"最高收益: {best['max_ret']:.2f}%")
    print(f"最低收益: {best['min_ret']:.2f}%")
    
    # 保存
    import pandas as pd
    import datetime
    df = pd.DataFrame(final)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'multi_strategy_{ts}.csv'
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'\n💾 结果: {out}')
    
    # 最优配置
    import json as j
    cfg = RESULTS_DIR / 'best_strategy.json'
    best_s = next(s for s in STRATEGIES if s['name'] == best['name'])
    best_s['stats'] = best
    with open(cfg, 'w') as f:
        j.dump(best_s, f, ensure_ascii=False, indent=2)
    print(f'💾 配置: {cfg}')
    
    elapsed = time.time() - start
    print(f'\n⏱️ 总耗时: {elapsed:.1f}s')
    
    return best


if __name__ == '__main__':
    main()