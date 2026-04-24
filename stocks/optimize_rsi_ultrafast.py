#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极速RSI策略优化 - 预计算RSI"""

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
    
    return closes, volumes


def precalc_rsi(closes, period=14):
    """预计算RSI数组"""
    rsi_arr = [None] * len(closes)
    
    if len(closes) < period + 1:
        return rsi_arr
    
    # 计算初始平均值
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i-1]
        gains += max(change, 0)
        losses += max(-change, 0)
    
    avg_gain = gains / period
    avg_loss = losses / period
    
    if avg_loss == 0:
        rsi_arr[period] = 100.0
    else:
        rsi_arr[period] = 100.0 - (100.0 / (1 + avg_gain / avg_loss))
    
    # 平滑计算后续RSI
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i-1]
        gain = max(change, 0)
        loss = max(-change, 0)
        
        # EMA平滑
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi_arr[i] = 100.0
        else:
            rsi_arr[i] = 100.0 - (100.0 / (1 + avg_gain / avg_loss))
    
    return rsi_arr


def precalc_ma(closes, period):
    """预计算MA数组"""
    ma_arr = [None] * len(closes)
    
    for i in range(period - 1, len(closes)):
        ma_arr[i] = sum(closes[i-period+1:i+1]) / period
    
    return ma_arr


def backtest(closes, volumes, rsi_arr, ma30_arr, ma60_arr, buy_th, sell_th, stop, 
             use_trend=False, use_volume=False, use_double=False, use_stop_loss=False, stop_loss=0.08):
    """快速回测"""
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    prev_rsi = None
    
    start = 60  # 最小起始点
    
    for i in range(start, len(closes)):
        price = closes[i]
        rsi = rsi_arr[i]
        vol = volumes[i]
        
        if rsi is None:
            continue
        
        # 持仓管理
        if pos > 0:
            if price > high:
                high = price
            
            # 止盈
            if (high - price) / high >= stop:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                prev_rsi = None
                continue
            
            # 止损
            if use_stop_loss and (cost - price) / cost >= stop_loss:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                prev_rsi = None
                continue
        
        # 买入
        if pos == 0:
            buy_ok = False
            
            # 基础：RSI超卖
            if rsi < buy_th:
                buy_ok = True
                
                # 二次确认：RSI回升
                if use_double and prev_rsi is not None:
                    if rsi <= prev_rsi:
                        buy_ok = False
                
                # 趋势过滤：股价在MA之上
                if use_trend and buy_ok:
                    ma60 = ma60_arr[i]
                    if ma60 and price < ma60 * 0.98:
                        buy_ok = False
                
                # 成交量过滤：放量
                if use_volume and buy_ok and i >= 20:
                    avg_vol = sum(volumes[i-20:i]) / 20
                    if vol < avg_vol * 1.2:
                        buy_ok = False
            
            if buy_ok:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    amt = shares * price
                    capital -= amt + amt * fee
                    pos = shares
                    cost = price
                    high = price
        
        # 卖出
        elif pos > 0:
            if rsi > sell_th:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
                prev_rsi = None
            
            # 跌破趋势线
            if use_trend:
                ma30 = ma30_arr[i]
                if ma30 and price < ma30 * 0.95:
                    amt = pos * price
                    trades.append(amt - pos * cost - amt * fee)
                    capital += amt - amt * fee
                    pos = 0
                    prev_rsi = None
        
        prev_rsi = rsi
    
    if not trades:
        return None
    
    wins = len([t for t in trades if t > 0])
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': wins / len(trades) * 100,
        'trades': len(trades)
    }


# 策略配置
STRATEGIES = [
    {'name': '基础RSI(25/75)', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15},
    {'name': 'RSI宽松(20/80)', 'buy_th': 20, 'sell_th': 80, 'stop': 0.15},
    {'name': 'RSI严格(30/70)', 'buy_th': 30, 'sell_th': 70, 'stop': 0.15},
    {'name': 'RSI+趋势MA60', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True},
    {'name': 'RSI+放量', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_volume': True},
    {'name': 'RSI+二次确认', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_double': True},
    {'name': 'RSI+止损8%', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_stop_loss': True, 'stop_loss': 0.08},
    {'name': 'RSI+止损5%', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_stop_loss': True, 'stop_loss': 0.05},
    {'name': '趋势+放量', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'use_volume': True},
    {'name': '趋势+二次', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'use_double': True},
    {'name': '二次+放量', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_double': True, 'use_volume': True},
    {'name': '全面优化', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'use_double': True, 'use_stop_loss': True, 'stop_loss': 0.08},
    {'name': '全面+放量', 'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'use_trend': True, 'use_double': True, 'use_volume': True},
]


def main():
    print('=' * 80)
    print('📊 极速RSI策略优化')
    print('=' * 80)
    
    files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    random.seed(42)
    stocks = random.sample(files, min(2000, len(files)))
    
    print(f'抽样：{len(stocks)} 只')
    print(f'策略：{len(STRATEGIES)} 个')
    print()
    
    results = {s['name']: [] for s in STRATEGIES}
    start_time = time.time()
    
    for i, sym in enumerate(stocks):
        raw = load_stock(sym)
        closes, volumes = extract_prices(raw)
        
        if not closes or len(closes) < 80:
            continue
        
        # 预计算
        rsi_arr = precalc_rsi(closes)
        ma30_arr = precalc_ma(closes, 30)
        ma60_arr = precalc_ma(closes, 60)
        
        for s in STRATEGIES:
            try:
                r = backtest(closes, volumes, rsi_arr, ma30_arr, ma60_arr,
                            s['buy_th'], s['sell_th'], s['stop'],
                            s.get('use_trend', False),
                            s.get('use_volume', False),
                            s.get('use_double', False),
                            s.get('use_stop_loss', False),
                            s.get('stop_loss', 0.08))
                if r:
                    results[s['name']].append(r)
            except:
                continue
        
        if (i+1) % 400 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i+1}/{len(stocks)} ({(i+1)/len(stocks)*100:.0f}%) 耗时: {elapsed:.0f}s')
    
    elapsed = time.time() - start_time
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
    print(f"{'排名':<4}{'策略':<18}{'胜率':<8}{'盈利占比':<10}{'中位收益':<10}{'交易':<6}")
    print('-' * 56)
    
    for i, r in enumerate(final, 1):
        print(f"{i:<4}{r['name']:<18}{r['win_rate']:>6.1f}%{r['profit_pct']:>8.1f}%{r['med_ret']:>8.2f}%{r['avg_trades']:>4.1f}")
    
    # 最优
    best = final[0]
    
    print()
    print('=' * 80)
    print(f'🎯 最高胜率策略：{best["name"]}')
    print('=' * 80)
    print(f"测试股票：{best['count']} 只")
    print(f"平均胜率：{best['win_rate']:.1f}%")
    print(f"盈利占比：{best['profit_pct']:.1f}%")
    print(f"中位收益：{best['med_ret']:.2f}%")
    
    # 按收益
    print()
    by_ret = sorted(final, key=lambda x: x['med_ret'], reverse=True)
    print('📈 按收益排名 TOP5')
    print('-' * 50)
    for i, r in enumerate(by_ret[:5], 1):
        print(f"{i}. {r['name']:<18} 收益:{r['med_ret']:>7.2f}% 胜率:{r['win_rate']:>5.1f}%")
    
    # 保存
    import pandas as pd
    import datetime
    df = pd.DataFrame(final)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'rsi_opt_{ts}.csv'
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'\n💾 结果：{out}')
    
    # 配置
    best_s = next(s for s in STRATEGIES if s['name'] == best['name'])
    best_s['stats'] = best
    cfg = RESULTS_DIR / 'best_rsi_opt.json'
    with open(cfg, 'w') as f:
        json.dump(best_s, f, ensure_ascii=False, indent=2)
    print(f'💾 配置：{cfg}')
    
    print(f'\n⏱️ 耗时：{elapsed:.1f}s')
    
    return final


if __name__ == '__main__':
    main()