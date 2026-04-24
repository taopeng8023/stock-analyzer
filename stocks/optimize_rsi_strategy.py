#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSI策略优化器 - 测试多种改进版本，提高胜率

改进方向：
1. 添加趋势过滤（MA趋势确认）
2. 添加成交量过滤（放量确认）
3. 添加MACD辅助确认
4. 优化止盈/止损比例
5. 二次确认（RSI连续超卖）
"""

import json
import warnings
from pathlib import Path
import time
import statistics

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


def calc_ema(closes, period, idx):
    if idx < period - 1:
        return None
    k = 2 / (period + 1)
    ema = closes[0]
    for i in range(1, idx+1):
        ema = closes[i] * k + ema * (1 - k)
    return ema


def calc_macd(closes, idx):
    if idx < 26:
        return None, None
    
    ema12 = calc_ema(closes, 12, idx)
    ema26 = calc_ema(closes, 26, idx)
    
    if ema12 is None or ema26 is None:
        return None, None
    
    dif = ema12 - ema26
    
    # 计算 DEA (MACD线的9日EMA)
    if idx < 35:
        return dif, None
    
    # 简化：直接返回DIF和前一日DIF
    return dif, ema12 - ema26


# ============== 策略版本 ==============

def strategy_rsi_base(data, params):
    """基础RSI策略"""
    closes = data['close']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        
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
        
        # RSI < buy_th 买入
        if rsi < buy_th and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # RSI > sell_th 卖出
        elif rsi > sell_th and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


def strategy_rsi_trend_filter(data, params):
    """RSI + MA趋势过滤"""
    closes = data['close']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    ma_period = params.get('ma_period', 60)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(max(period, ma_period) + 5, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        ma = calc_ma(closes, ma_period, i)
        
        if rsi is None or ma is None:
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
        
        # RSI超卖 + 股价在MA之上（趋势向上）
        if rsi < buy_th and price > ma * 0.98 and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # RSI超买 或 跌破MA
        elif pos > 0:
            if rsi > sell_th or price < ma * 0.95:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
    
    if not trades:
        return None
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


def strategy_rsi_volume_filter(data, params):
    """RSI + 成交量过滤"""
    closes = data['close']
    volumes = data['volume']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    vol_ratio = params.get('vol_ratio', 1.2)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 20, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        vol = volumes[i]
        avg_vol = sum(volumes[i-20:i]) / 20
        
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
        
        # RSI超卖 + 放量（底部放量更可靠）
        if rsi < buy_th and vol > avg_vol * vol_ratio and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # RSI超买卖出
        elif rsi > sell_th and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


def strategy_rsi_double_confirm(data, params):
    """RSI二次确认策略"""
    closes = data['close']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    rsi_history = []
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        
        if rsi is None:
            continue
        
        rsi_history.append(rsi)
        
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
        
        # 二次确认：连续2天RSI超卖，且今日RSI回升
        if len(rsi_history) >= 2:
            prev_rsi = rsi_history[-2]
            
            if pos == 0:
                # 连续超卖 + 今日回升 = 确认反转
                if prev_rsi < buy_th and rsi < buy_th and rsi > prev_rsi:
                    shares = int(capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        amt = shares * price
                        capital -= amt + amt * fee
                        pos = shares
                        cost = price
                        high = price
        
        # RSI超买卖出
        elif rsi > sell_th and pos > 0:
            amt = pos * price
            trades.append(amt - pos * cost - amt * fee)
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


def strategy_rsi_macd_confirm(data, params):
    """RSI + MACD确认"""
    closes = data['close']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    prev_dif = None
    
    for i in range(35, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        dif, _ = calc_macd(closes, i)
        
        if rsi is None or dif is None:
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
                prev_dif = dif
                continue
        
        # RSI超卖 + MACD金叉（DIF从负转正）
        if pos == 0:
            if prev_dif is not None:
                if rsi < buy_th and prev_dif < 0 and dif > 0:
                    shares = int(capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        amt = shares * price
                        capital -= amt + amt * fee
                        pos = shares
                        cost = price
                        high = price
        
        # RSI超买 或 MACD死叉
        elif pos > 0:
            if prev_dif is not None:
                if rsi > sell_th or (prev_dif > 0 and dif < 0):
                    amt = pos * price
                    trades.append(amt - pos * cost - amt * fee)
                    capital += amt - amt * fee
                    pos = 0
        
        prev_dif = dif
    
    if not trades:
        return None
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


def strategy_rsi_comprehensive(data, params):
    """综合策略：RSI + 趋势 + 成交量 + 二次确认"""
    closes = data['close']
    volumes = data['volume']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop = params.get('stop', 0.15)
    ma_period = params.get('ma_period', 60)
    vol_ratio = params.get('vol_ratio', 1.2)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    rsi_history = []
    
    for i in range(max(period, ma_period) + 20, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        ma = calc_ma(closes, ma_period, i)
        vol = volumes[i]
        avg_vol = sum(volumes[i-20:i]) / 20
        
        if rsi is None or ma is None:
            continue
        
        rsi_history.append(rsi)
        
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
        
        # 综合买入条件
        if pos == 0 and len(rsi_history) >= 2:
            prev_rsi = rsi_history[-2]
            
            # 1. RSI超卖
            # 2. RSI回升（二次确认）
            # 3. 股价在MA附近或上方
            # 4. 放量
            conditions = [
                rsi < buy_th,
                rsi > prev_rsi,  # RSI回升
                price > ma * 0.95,  # 趋势未破坏
                vol > avg_vol * vol_ratio,  # 放量
            ]
            
            # 至少满足3个条件
            if sum(conditions) >= 3:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    amt = shares * price
                    capital -= amt + amt * fee
                    pos = shares
                    cost = price
                    high = price
        
        # 综合卖出条件
        elif pos > 0:
            # RSI超买 或 跌破MA
            if rsi > sell_th or price < ma * 0.92:
                amt = pos * price
                trades.append(amt - pos * cost - amt * fee)
                capital += amt - amt * fee
                pos = 0
    
    if not trades:
        return None
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(trades) if trades else 0
    }


def strategy_rsi_stop_loss(data, params):
    """RSI + 止损策略"""
    closes = data['close']
    period = params.get('period', 14)
    buy_th = params.get('buy_th', 25)
    sell_th = params.get('sell_th', 75)
    stop_profit = params.get('stop_profit', 0.15)
    stop_loss = params.get('stop_loss', 0.08)
    
    capital = 100000.0
    pos = 0
    cost = 0.0
    high = 0.0
    trades = []
    fee = 0.0003
    
    for i in range(period + 5, len(closes)):
        price = closes[i]
        rsi = calc_rsi(closes, period, i)
        
        if rsi is None:
            continue
        
        # 止盈止损
        if pos > 0:
            if price > high:
                high = price
            
            profit_dd = (high - price) / high
            loss_dd = (cost - price) / cost
            
            # 止盈
            if profit_dd >= stop_profit:
                amt = pos * price
                trades.append({'profit': amt - pos * cost - amt * fee, 'reason': '止盈'})
                capital += amt - amt * fee
                pos = 0
                continue
            
            # 止损
            if loss_dd >= stop_loss:
                amt = pos * price
                trades.append({'profit': amt - pos * cost - amt * fee, 'reason': '止损'})
                capital += amt - amt * fee
                pos = 0
                continue
        
        # RSI超卖买入
        if rsi < buy_th and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # RSI超买卖出
        elif rsi > sell_th and pos > 0:
            amt = pos * price
            trades.append({'profit': amt - pos * cost - amt * fee, 'reason': 'RSI超买'})
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    
    profits = [t['profit'] for t in trades]
    wins = [t for t in trades if t['profit'] > 0]
    
    return {
        'return': (capital - 100000) / 100000,
        'win_rate': len(wins) / len(trades) * 100,
        'trades': len(trades),
        'avg_profit': statistics.mean(profits),
        'stop_profit_count': len([t for t in trades if t['reason'] == '止盈']),
        'stop_loss_count': len([t for t in trades if t['reason'] == '止损']),
    }


# ============== 策略配置 ==============

STRATEGIES = [
    {'name': '基础RSI(25/75)', 'func': strategy_rsi_base, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15}},
    {'name': 'RSI+趋势MA60', 'func': strategy_rsi_trend_filter, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'ma_period': 60}},
    {'name': 'RSI+趋势MA30', 'func': strategy_rsi_trend_filter, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'ma_period': 30}},
    {'name': 'RSI+放量1.2倍', 'func': strategy_rsi_volume_filter, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'vol_ratio': 1.2}},
    {'name': 'RSI+放量1.5倍', 'func': strategy_rsi_volume_filter, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15, 'vol_ratio': 1.5}},
    {'name': 'RSI+二次确认', 'func': strategy_rsi_double_confirm, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15}},
    {'name': 'RSI+综合', 'func': strategy_rsi_comprehensive, 'params': {'buy_th': 25, 'sell_th': 75, 'stop': 0.15}},
    {'name': 'RSI+止损8%', 'func': strategy_rsi_stop_loss, 'params': {'buy_th': 25, 'sell_th': 75, 'stop_profit': 0.15, 'stop_loss': 0.08}},
    {'name': 'RSI+止损5%', 'func': strategy_rsi_stop_loss, 'params': {'buy_th': 25, 'sell_th': 75, 'stop_profit': 0.15, 'stop_loss': 0.05}},
    {'name': 'RSI宽松(20/80)', 'func': strategy_rsi_base, 'params': {'buy_th': 20, 'sell_th': 80, 'stop': 0.15}},
    {'name': 'RSI严格(30/70)', 'func': strategy_rsi_base, 'params': {'buy_th': 30, 'sell_th': 70, 'stop': 0.15}},
]


def main():
    print('=' * 80)
    print('📊 RSI策略优化器 - 提高胜率版本测试')
    print('=' * 80)
    
    files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    print(f'全量股票：{len(files)} 只')
    print(f'策略数量：{len(STRATEGIES)} 个')
    print()
    
    results = {}
    for s in STRATEGIES:
        results[s['name']] = []
    
    start = time.time()
    
    for i, sym in enumerate(files):
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
        
        if (i+1) % 500 == 0:
            elapsed = time.time() - start
            print(f'进度: {i+1}/{len(files)} ({(i+1)/len(files)*100:.0f}%) 耗时: {elapsed:.0f}s')
    
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
            'avg_profit': statistics.mean([r['avg_profit'] for r in res]),
            'avg_trades': statistics.mean([r['trades'] for r in res]),
        })
    
    # 按胜率排序
    final.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print('=' * 80)
    print('🏆 策略排名 (按胜率)')
    print('=' * 80)
    print(f"{'排名':<4}{'策略':<22}{'胜率':<8}{'盈利占比':<10}{'中位收益':<10}{'平均交易':<10}")
    print('-' * 64)
    
    for i, r in enumerate(final, 1):
        print(f"{i:<4}{r['name']:<22}{r['win_rate']:>6.1f}%{r['profit_pct']:>8.1f}%{r['med_ret']:>8.2f}%{r['avg_trades']:>8.1f}")
    
    # 最优策略
    best = final[0]
    
    print()
    print('=' * 80)
    print(f'🎯 最高胜率策略：{best["name"]}')
    print('=' * 80)
    print(f"测试股票：{best['count']} 只")
    print(f"平均胜率：{best['win_rate']:.1f}%")
    print(f"盈利占比：{best['profit_pct']:.1f}%")
    print(f"中位收益：{best['med_ret']:.2f}%")
    print(f"平均收益：{best['avg_ret']:.2f}%")
    print(f"平均交易：{best['avg_trades']:.1f} 次")
    
    # 按收益排序
    print()
    print('=' * 80)
    print('📈 策略排名 (按中位收益)')
    print('=' * 80)
    
    final_by_return = sorted(final, key=lambda x: x['med_ret'], reverse=True)
    
    print(f"{'排名':<4}{'策略':<22}{'中位收益':<10}{'胜率':<8}{'盈利占比':<10}")
    print('-' * 54)
    
    for i, r in enumerate(final_by_return[:5], 1):
        print(f"{i:<4}{r['name']:<22}{r['med_ret']:>8.2f}%{r['win_rate']:>6.1f}%{r['profit_pct']:>8.1f}%")
    
    # 保存
    import pandas as pd
    import datetime
    df = pd.DataFrame(final)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'rsi_optimized_{ts}.csv'
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'\n💾 结果：{out}')
    
    # 保存最优配置
    import json as j
    best_s = next(s for s in STRATEGIES if s['name'] == best['name'])
    best_s['stats'] = best
    cfg = RESULTS_DIR / 'best_rsi_strategy.json'
    with open(cfg, 'w') as f:
        j.dump(best_s, f, ensure_ascii=False, indent=2)
    print(f'💾 配置：{cfg}')
    
    print(f'\n⏱️ 总耗时：{elapsed:.1f}s')
    
    return final


if __name__ == '__main__':
    main()