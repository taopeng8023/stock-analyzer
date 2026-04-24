#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略参数优化器 - 快速版本 (多进程并行)
"""

import pandas as pd
import numpy as np
import json
import warnings
from pathlib import Path
import time
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
RESULTS_DIR.mkdir(exist_ok=True)

# 策略参数组合
STRATEGY_COMBINATIONS = [
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA5/MA10 + 5%止盈'},
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA5/MA10 + 10%止盈'},
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA5/MA10 + 15%止盈'},
    {'short_ma': 5, 'long_ma': 20, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA5/MA20 + 5%止盈'},
    {'short_ma': 5, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA5/MA20 + 10%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA10/MA20 + 5%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA10/MA20 + 10%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA10/MA20 + 15%止盈'},
    {'short_ma': 15, 'long_ma': 20, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA15/MA20 + 5%止盈'},
    {'short_ma': 15, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA15/MA20 + 10%止盈'},
    {'short_ma': 20, 'long_ma': 30, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA20/MA30 + 10%止盈'},
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.10, 'use_filters': True, 'name': 'MA5/MA10 + 过滤'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': True, 'name': 'MA10/MA20 + 过滤'},
]


def load_all_stock_data():
    """批量加载所有股票数据到内存"""
    stocks = {}
    for filepath in CACHE_DIR.glob('*.json'):
        if filepath.name == 'stock_list.json':
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'items' in data and len(data['items']) > 50:
                stocks[filepath.stem] = data
        except:
            continue
    return stocks


def backtest_stock_data(data: dict, config: dict) -> dict:
    """回测单只股票"""
    items = data['items']
    fields = data['fields']
    
    # 构建价格数组
    close_idx = fields.index('close')
    volume_idx = fields.index('vol') if 'vol' in fields else -1
    
    closes = [float(item[close_idx]) for item in items]
    volumes = [float(item[volume_idx]) if volume_idx >= 0 else 0 for item in items]
    
    if len(closes) < config['long_ma'] + 10:
        return None
    
    short_ma = config['short_ma']
    long_ma = config['long_ma']
    profit_stop = config['profit_stop']
    use_filters = config['use_filters']
    
    # 计算MA数组
    ma_short = []
    ma_long = []
    for i in range(len(closes)):
        if i < short_ma - 1:
            ma_short.append(None)
        else:
            ma_short.append(sum(closes[i-short_ma+1:i+1]) / short_ma)
        
        if i < long_ma - 1:
            ma_long.append(None)
        else:
            ma_long.append(sum(closes[i-long_ma+1:i+1]) / long_ma)
    
    capital = 100000
    position = 0
    cost_price = 0
    highest_price = 0
    trades = []
    fee_rate = 0.0003
    
    for i in range(len(closes)):
        price = closes[i]
        
        if i < long_ma + 5:
            continue
        
        # 移动止盈检查
        if position > 0:
            if price > highest_price:
                highest_price = price
            dd = (highest_price - price) / highest_price
            if dd >= profit_stop:
                amount = position * price
                fee = amount * fee_rate
                profit = amount - (position * cost_price) - fee
                trades.append(profit)
                capital += amount - fee
                position = 0
                continue
        
        # 信号判断
        ms = ma_short[i]
        ml = ma_long[i]
        ms_prev = ma_short[i-1]
        ml_prev = ma_long[i-1]
        
        if None in [ms, ml, ms_prev, ml_prev]:
            continue
        
        # 金叉买入
        if ms_prev <= ml_prev and ms > ml:
            if not position:
                if use_filters:
                    # 简化过滤：只检查成交量
                    if i >= 20 and volume_idx >= 0:
                        avg_vol = sum(volumes[i-20:i]) / 20
                        if volumes[i] <= avg_vol * 1.5:
                            continue
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    amount = shares * price
                    fee = amount * fee_rate
                    capital -= amount + fee
                    position = shares
                    cost_price = price
                    highest_price = price
        
        # 死叉卖出
        elif ms_prev >= ml_prev and ms < ml:
            if position > 0:
                amount = position * price
                fee = amount * fee_rate
                profit = amount - (position * cost_price) - fee
                trades.append(profit)
                capital += amount - fee
                position = 0
    
    if not trades:
        return None
    
    return {
        'return_rate': (capital - 100000) / 100000,
        'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
        'trade_count': len(trades)
    }


def test_strategy(config: dict, stocks: dict) -> dict:
    """测试单个策略"""
    results = []
    
    for symbol, data in stocks.items():
        try:
            r = backtest_stock_data(data, config)
            if r:
                results.append(r)
        except:
            continue
    
    if not results:
        return None
    
    returns = [r['return_rate'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    
    return {
        'name': config['name'],
        'short_ma': config['short_ma'],
        'long_ma': config['long_ma'],
        'profit_stop': config['profit_stop'],
        'use_filters': config['use_filters'],
        'stock_count': len(results),
        'avg_return': statistics.mean(returns) * 100,
        'median_return': statistics.median(returns) * 100,
        'win_rate_avg': statistics.mean(win_rates),
        'profitable_pct': len([r for r in returns if r > 0]) / len(results) * 100,
        'max_return': max(returns) * 100,
        'min_return': min(returns) * 100,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=500, help='抽样数量')
    args = parser.parse_args()
    
    print('=' * 80)
    print('📊 策略参数优化器 - 快速版本')
    print('=' * 80)
    
    # 加载所有数据
    print('正在加载股票数据...')
    stocks = load_all_stock_data()
    print(f'加载完成：{len(stocks)} 只股票')
    
    # 抽样
    if args.sample and len(stocks) > args.sample:
        import random
        random.seed(42)
        sample_keys = random.sample(list(stocks.keys()), args.sample)
        stocks = {k: stocks[k] for k in sample_keys}
        print(f'抽样测试：{args.sample} 只')
    
    print(f'策略组合：{len(STRATEGY_COMBINATIONS)} 个')
    print()
    
    all_results = []
    start_time = time.time()
    
    # 并行测试策略
    for i, config in enumerate(STRATEGY_COMBINATIONS):
        print(f"[{i+1}/{len(STRATEGY_COMBINATIONS)}] {config['name']}")
        
        result = test_strategy(config, stocks)
        
        if result:
            all_results.append(result)
            print(f"   ✓ 中位收益: {result['median_return']:.2f}%")
            print(f"   ✓ 盈利占比: {result['profitable_pct']:.1f}%")
            print(f"   ✓ 平均胜率: {result['win_rate_avg']:.1f}%")
            print()
    
    elapsed = time.time() - start_time
    
    if all_results:
        # 计算综合评分
        for r in all_results:
            # 评分 = 中位收益 + 盈利占比权重 + 胜率权重
            r['score'] = r['median_return'] + r['profitable_pct'] * 0.3 + r['win_rate_avg'] * 0.2
        
        sorted_results = sorted(all_results, key=lambda x: x['score'], reverse=True)
        
        print('=' * 80)
        print('🏆 策略排名 (综合评分)')
        print('=' * 80)
        
        print(f"\n{'排名':<4}{'策略':<30}{'中位收益':<10}{'盈利占比':<10}{'胜率':<8}{'评分':<8}")
        print('-' * 70)
        
        for rank, r in enumerate(sorted_results, 1):
            print(f"{rank:<4}{r['name']:<30}"
                  f"{r['median_return']:>8.2f}%"
                  f"{r['profitable_pct']:>8.1f}%"
                  f"{r['win_rate_avg']:>6.1f}%"
                  f"{r['score']:>6.1f}")
        
        # 最优策略
        best = sorted_results[0]
        
        print()
        print('=' * 80)
        print('🎯 最优策略')
        print('=' * 80)
        print(f"""
策略名称：    {best['name']}
均线组合：    MA{best['short_ma']}/MA{best['long_ma']}
止盈阈值：    {best['profit_stop']*100:.0f}%
五重过滤：    {'启用' if best['use_filters'] else '禁用'}

回测股票：    {best['stock_count']} 只
平均收益：    {best['avg_return']:.2f}%
中位收益：    {best['median_return']:.2f}%
盈利占比：    {best['profitable_pct']:.1f}%
平均胜率：    {best['win_rate_avg']:.1f}%
最高收益：    {best['max_return']:.2f}%
最低收益：    {best['min_return']:.2f}%

耗时：{elapsed:.1f}秒
""")
        
        # 保存结果
        df = pd.DataFrame(all_results)
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = RESULTS_DIR / f'strategy_optimizer_{timestamp}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f'💾 结果已保存：{output_file}')
        
        return best
    
    return None


if __name__ == '__main__':
    best_strategy = main()
    
    # 如果找到最优策略，保存配置供后续使用
    if best_strategy:
        config_file = RESULTS_DIR / 'best_strategy.json'
        import json as json_mod
        with open(config_file, 'w', encoding='utf-8') as f:
            json_mod.dump(best_strategy, f, ensure_ascii=False, indent=2)
        print(f'💾 最优策略配置已保存：{config_file}')