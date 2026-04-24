#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证最优策略：RSI宽松(25/75) - 全量回测
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
    except:
        return None
    
    closes = []
    for item in items:
        try:
            closes.append(float(item[close_idx]))
        except:
            continue
    
    return closes


def calc_rsi(closes, period, idx):
    """计算RSI"""
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


def backtest_rsi(closes, period=14, buy_threshold=25, sell_threshold=75, stop=0.15):
    """
    RSI宽松策略回测
    - RSI < 25: 超卖买入
    - RSI > 75: 超买卖出
    - 移动止盈: 15%
    """
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
        
        # 移动止盈
        if pos > 0:
            if price > high:
                high = price
            if (high - price) / high >= stop:
                amt = pos * price
                profit = amt - pos * cost - amt * fee
                trades.append({'profit': profit, 'reason': '止盈', 'return': profit / (pos * cost)})
                capital += amt - amt * fee
                pos = 0
                continue
        
        # RSI < 25 超卖买入
        if rsi < buy_threshold and pos == 0:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amt = shares * price
                capital -= amt + amt * fee
                pos = shares
                cost = price
                high = price
        
        # RSI > 75 超买卖出
        elif rsi > sell_threshold and pos > 0:
            amt = pos * price
            profit = amt - pos * cost - amt * fee
            trades.append({'profit': profit, 'reason': 'RSI超买', 'return': profit / (pos * cost)})
            capital += amt - amt * fee
            pos = 0
    
    if not trades:
        return None
    
    returns = [t['return'] for t in trades]
    wins = [t for t in trades if t['profit'] > 0]
    
    return {
        'final_capital': capital,
        'total_return': (capital - 100000) / 100000,
        'trade_count': len(trades),
        'win_count': len(wins),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': statistics.mean(returns),
        'total_profit': sum([t['profit'] for t in trades]),
    }


def main():
    print('=' * 80)
    print('📊 验证最优策略：RSI宽松(25/75) - 全量回测')
    print('=' * 80)
    print()
    
    files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    print(f'全量股票：{len(files)} 只')
    print()
    
    results = []
    start = time.time()
    
    for i, sym in enumerate(files):
        raw = load_stock(sym)
        closes = extract_prices(raw)
        
        if not closes or len(closes) < 50:
            continue
        
        r = backtest_rsi(closes)
        if r:
            results.append({'symbol': sym, **r})
        
        if (i+1) % 500 == 0:
            elapsed = time.time() - start
            print(f'进度: {i+1}/{len(files)} ({(i+1)/len(files)*100:.0f}%) 完成: {len(results)} 只 耗时: {elapsed:.0f}s')
    
    elapsed = time.time() - start
    print()
    
    if results:
        returns = [r['total_return'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        trade_counts = [r['trade_count'] for r in results]
        
        print('=' * 80)
        print('📊 RSI宽松(25/75) 全量回测结果')
        print('=' * 80)
        
        print(f"""
📈 总体统计
   回测股票：    {len(results)} 只
   盈利股票：    {len([r for r in returns if r > 0])} 只 ({len([r for r in returns if r > 0])/len(results)*100:.1f}%)
   
📊 收益统计
   平均收益：    {statistics.mean(returns)*100:.2f}%
   中位收益：    {statistics.median(returns)*100:.2f}%
   最高收益：    {max(returns)*100:.2f}%
   最低收益：    {min(returns)*100:.2f}%
   
   P10:          {sorted(returns)[int(len(returns)*0.1)]*100:.2f}%
   P25:          {sorted(returns)[int(len(returns)*0.25)]*100:.2f}%
   P50:          {sorted(returns)[int(len(returns)*0.5)]*100:.2f}%
   P75:          {sorted(returns)[int(len(returns)*0.75)]*100:.2f}%
   P90:          {sorted(returns)[int(len(returns)*0.9)]*100:.2f}%
   
🎯 交易统计
   平均胜率：    {statistics.mean(win_rates):.2f}%
   平均交易：    {statistics.mean(trade_counts):.1f} 次
   
⏱️  耗时：{elapsed:.1f}秒
""")
        
        # TOP 20
        sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print('🏆 TOP 20 收益股票')
        print('-' * 60)
        print(f"{'股票':<10}{'总收益':<12}{'胜率':<10}{'交易次数':<10}")
        print('-' * 60)
        
        for r in sorted_results[:20]:
            print(f"{r['symbol']:<10}{r['total_return']*100:>10.2f}%{r['win_rate']:>8.1f}%{r['trade_count']:>8}")
        
        print()
        
        # 收益分布
        print('📊 收益分布')
        print('-' * 60)
        
        bins = [(-100, -50), (-50, -20), (-20, 0), (0, 20), (20, 50), (50, 100), (100, 500), (500, 1000)]
        labels = ['<-50%', '-50~-20%', '-20~0%', '0~20%', '20~50%', '50~100%', '100~500%', '>500%']
        
        for (low, high), label in zip(bins, labels):
            count = len([r for r in returns if low <= r*100 < high])
            pct = count / len(results) * 100
            bar = '█' * int(pct / 2)
            print(f'{label:<12} {count:>5} 只 ({pct:>5.1f}%) {bar}')
        
        # 保存结果
        import pandas as pd
        import datetime
        df = pd.DataFrame(results)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        out = RESULTS_DIR / f'rsi_strategy_verified_{ts}.csv'
        df.to_csv(out, index=False, encoding='utf-8-sig')
        print(f'\n💾 结果已保存：{out}')
        
        # 策略配置
        strategy_config = {
            'name': 'RSI宽松策略',
            'buy_condition': 'RSI < 25 (超卖)',
            'sell_condition': 'RSI > 75 (超买)',
            'stop_loss': '移动止盈 15%',
            'period': 14,
            'verified': True,
            'stats': {
                'stock_count': len(results),
                'avg_return': statistics.mean(returns) * 100,
                'median_return': statistics.median(returns) * 100,
                'profit_pct': len([r for r in returns if r > 0]) / len(results) * 100,
                'win_rate': statistics.mean(win_rates),
            }
        }
        
        cfg_file = RESULTS_DIR / 'best_strategy_verified.json'
        with open(cfg_file, 'w', encoding='utf-8') as f:
            json.dump(strategy_config, f, ensure_ascii=False, indent=2)
        print(f'💾 策略配置：{cfg_file}')
        
        return strategy_config
    
    return None


if __name__ == '__main__':
    main()