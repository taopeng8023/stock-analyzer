#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略参数优化器 - 找出最优盈利策略

测试维度：
1. 均线组合：MA5/10, MA10/20, MA15/20, MA20/30, MA5/20
2. 止盈阈值：5%, 10%, 15%, 20%
3. 是否启用五重过滤

输出：最优策略配置
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
from pathlib import Path
import time
import statistics
from typing import Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
RESULTS_DIR.mkdir(exist_ok=True)

# 策略参数组合
STRATEGY_COMBINATIONS = [
    # 短均线/长均线, 止盈阈值, 是否过滤
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA5/MA10 + 5%止盈'},
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA5/MA10 + 10%止盈'},
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA5/MA10 + 15%止盈'},
    {'short_ma': 5, 'long_ma': 20, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA5/MA20 + 5%止盈'},
    {'short_ma': 5, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA5/MA20 + 10%止盈'},
    {'short_ma': 5, 'long_ma': 20, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA5/MA20 + 15%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA10/MA20 + 5%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA10/MA20 + 10%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA10/MA20 + 15%止盈'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.20, 'use_filters': False, 'name': 'MA10/MA20 + 20%止盈'},
    {'short_ma': 15, 'long_ma': 20, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA15/MA20 + 5%止盈'},
    {'short_ma': 15, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA15/MA20 + 10%止盈'},
    {'short_ma': 15, 'long_ma': 20, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA15/MA20 + 15%止盈'},
    {'short_ma': 20, 'long_ma': 30, 'profit_stop': 0.05, 'use_filters': False, 'name': 'MA20/MA30 + 5%止盈'},
    {'short_ma': 20, 'long_ma': 30, 'profit_stop': 0.10, 'use_filters': False, 'name': 'MA20/MA30 + 10%止盈'},
    {'short_ma': 20, 'long_ma': 30, 'profit_stop': 0.15, 'use_filters': False, 'name': 'MA20/MA30 + 15%止盈'},
    # 带过滤的策略
    {'short_ma': 5, 'long_ma': 10, 'profit_stop': 0.10, 'use_filters': True, 'name': 'MA5/MA10 + 10%止盈 + 过滤'},
    {'short_ma': 10, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': True, 'name': 'MA10/MA20 + 10%止盈 + 过滤'},
    {'short_ma': 15, 'long_ma': 20, 'profit_stop': 0.10, 'use_filters': True, 'name': 'MA15/MA20 + 10%止盈 + 过滤'},
]


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'items' not in data:
            return None
        
        fields = data['fields']
        items = data['items']
        df = pd.DataFrame(items, columns=fields)
        
        df = df.rename(columns={
            'trade_date': 'date',
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'vol': 'volume'
        })
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.sort_values('date').reset_index(drop=True)
        return df
        
    except:
        return None


class Strategy:
    """策略类"""
    
    def __init__(self, short_ma, long_ma, profit_stop, use_filters=False):
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.profit_stop = profit_stop
        self.use_filters = use_filters
    
    def calc_ma(self, data, period, idx):
        if idx < period - 1:
            return None
        return float(data['close'].iloc[idx-period+1:idx+1].mean())
    
    def calc_rsi(self, data, period, idx):
        if idx < period + 1:
            return None
        
        gains, losses = [], []
        for i in range(idx-period, idx+1):
            change = float(data['close'].iloc[i]) - float(data['close'].iloc[i-1])
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        return 100 - (100 / (1 + avg_gain / avg_loss))
    
    def calc_ema(self, data, period, idx):
        if idx < period - 1:
            return None
        multiplier = 2 / (period + 1)
        ema = float(data['close'].iloc[idx-period+1])
        for i in range(idx-period+2, idx+1):
            ema = (float(data['close'].iloc[i]) - ema) * multiplier + ema
        return ema
    
    def check_filters(self, data, idx):
        """过滤条件"""
        score = 0
        
        # 成交量放大
        if idx >= 20:
            vol = float(data['volume'].iloc[idx])
            avg_vol = float(data['volume'].iloc[idx-20:idx].mean())
            if vol > avg_vol * 1.5:
                score += 1
        
        # 趋势向上 (股价 > MA60)
        ma60 = self.calc_ma(data, 60, idx)
        price = float(data['close'].iloc[idx])
        if ma60 and price > ma60:
            score += 1
        
        # RSI 不超买
        rsi = self.calc_rsi(data, 14, idx)
        if rsi and 40 < rsi < 70:
            score += 1
        
        # MACD 金叉
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        if ema12 and ema26 and ema12 > ema26:
            score += 1
        
        return score
    
    def signal(self, data, idx):
        if idx < self.long_ma + 5:
            return 'hold'
        
        ma_s = self.calc_ma(data, self.short_ma, idx)
        ma_l = self.calc_ma(data, self.long_ma, idx)
        ma_s_prev = self.calc_ma(data, self.short_ma, idx-1)
        ma_l_prev = self.calc_ma(data, self.long_ma, idx-1)
        
        if None in [ma_s, ma_l, ma_s_prev, ma_l_prev]:
            return 'hold'
        
        # 金叉
        if ma_s_prev <= ma_l_prev and ma_s > ma_l:
            if self.use_filters:
                if self.check_filters(data, idx) >= 2:
                    return 'buy'
            else:
                return 'buy'
        
        # 死叉
        if ma_s_prev >= ma_l_prev and ma_s < ma_l:
            return 'sell'
        
        return 'hold'


def backtest_single_stock(symbol: str, strategy_config: dict) -> Optional[dict]:
    """单只股票回测"""
    data = load_stock_data(symbol)
    
    if data is None or len(data) < strategy_config['long_ma'] + 10:
        return None
    
    strategy = Strategy(
        short_ma=strategy_config['short_ma'],
        long_ma=strategy_config['long_ma'],
        profit_stop=strategy_config['profit_stop'],
        use_filters=strategy_config['use_filters']
    )
    
    # 回测引擎
    capital = 100000
    fee_rate = 0.0003
    position = None
    cost_price = 0
    highest_price = 0
    trades = []
    
    for i in range(len(data)):
        price = float(data['close'].iloc[i])
        sig = strategy.signal(data, i)
        
        # 移动止盈
        if position and price > highest_price:
            highest_price = price
        
        if position:
            dd = (highest_price - price) / highest_price
            if dd >= strategy.profit_stop:
                # 止盈卖出
                amount = position * price
                fee = amount * fee_rate
                profit = amount - (position * cost_price) - fee
                trades.append(profit)
                capital += amount - fee
                position = None
                continue
        
        if sig == 'buy' and not position:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                amount = shares * price
                fee = amount * fee_rate
                capital -= amount + fee
                position = shares
                cost_price = price
                highest_price = price
        
        elif sig == 'sell' and position:
            amount = position * price
            fee = amount * fee_rate
            profit = amount - (position * cost_price) - fee
            trades.append(profit)
            capital += amount - fee
            position = None
    
    if not trades:
        return None
    
    total_profit = sum(trades)
    win_trades = len([t for t in trades if t > 0])
    win_rate = win_trades / len(trades) * 100 if trades else 0
    
    return {
        'symbol': symbol,
        'total_profit': total_profit,
        'return_rate': (capital - 100000) / 100000,
        'win_rate': win_rate,
        'trade_count': len(trades)
    }


def run_strategy_test(strategy_config: dict, stock_list: List[str]) -> dict:
    """运行策略测试"""
    results = []
    
    for symbol in stock_list:
        try:
            r = backtest_single_stock(symbol, strategy_config)
            if r:
                results.append(r)
        except:
            continue
    
    if not results:
        return None
    
    returns = [r['return_rate'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    
    return {
        'name': strategy_config['name'],
        'short_ma': strategy_config['short_ma'],
        'long_ma': strategy_config['long_ma'],
        'profit_stop': strategy_config['profit_stop'],
        'use_filters': strategy_config['use_filters'],
        'stock_count': len(results),
        'avg_return': statistics.mean(returns) * 100,
        'median_return': statistics.median(returns) * 100,
        'win_rate_avg': statistics.mean(win_rates),
        'profitable_count': len([r for r in returns if r > 0]),
        'profitable_pct': len([r for r in returns if r > 0]) / len(results) * 100,
        'max_return': max(returns) * 100,
        'min_return': min(returns) * 100,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=None, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量测试')
    args = parser.parse_args()
    
    print('=' * 80)
    print('📊 策略参数优化器 - 寻找最优盈利策略')
    print('=' * 80)
    
    # 加载股票列表
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    
    # 抽样（默认抽样1000只加速）
    if not args.full and args.sample is None:
        args.sample = 1000
    
    if args.sample and len(stock_files) > args.sample:
        import random
        random.seed(42)
        stock_files = random.sample(stock_files, args.sample)
        print(f'抽样测试：{args.sample} 只股票')
    else:
        print(f'全量测试：{len(stock_files)} 只股票')
    
    print(f'策略组合：{len(STRATEGY_COMBINATIONS)} 个')
    print()
    
    all_results = []
    start_time = time.time()
    
    for i, config in enumerate(STRATEGY_COMBINATIONS):
        print(f"[{i+1}/{len(STRATEGY_COMBINATIONS)}] 测试策略：{config['name']}")
        
        result = run_strategy_test(config, stock_files)
        
        if result:
            all_results.append(result)
            print(f"   股票数：{result['stock_count']} 只")
            print(f"   平均收益：{result['avg_return']:.2f}%")
            print(f"   中位收益：{result['median_return']:.2f}%")
            print(f"   盈利占比：{result['profitable_pct']:.1f}%")
            print(f"   平均胜率：{result['win_rate_avg']:.1f}%")
            print()
    
    elapsed = time.time() - start_time
    
    if all_results:
        # 排序找出最优策略
        # 评分标准：中位收益 + 盈利占比 + 胜率
        for r in all_results:
            r['score'] = r['median_return'] + r['profitable_pct'] * 0.5 + r['win_rate_avg'] * 0.3
        
        sorted_results = sorted(all_results, key=lambda x: x['score'], reverse=True)
        
        print('=' * 80)
        print('🏆 策略排名 (综合评分)')
        print('=' * 80)
        
        print(f"\n{'排名':<6}{'策略名称':<35}{'中位收益':<12}{'盈利占比':<12}{'胜率':<12}{'评分':<12}")
        print('-' * 80)
        
        for rank, r in enumerate(sorted_results[:10], 1):
            print(f"{rank:<6}{r['name']:<35}"
                  f"{r['median_return']:>10.2f}%"
                  f"{r['profitable_pct']:>10.1f}%"
                  f"{r['win_rate_avg']:>10.1f}%"
                  f"{r['score']:>10.1f}")
        
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

测试股票：    {best['stock_count']} 只
平均收益：    {best['avg_return']:.2f}%
中位收益：    {best['median_return']:.2f}%
盈利占比：    {best['profitable_pct']:.1f}%
平均胜率：    {best['win_rate_avg']:.1f}%
最高收益：    {best['max_return']:.2f}%
最低收益：    {best['min_return']:.2f}%
""")
        
        # 保存结果
        df = pd.DataFrame(all_results)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = RESULTS_DIR / f'strategy_optimizer_{timestamp}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f'💾 结果已保存至：{output_file}')
        print(f'⏱️  总耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
        
        return best
    
    return None


if __name__ == '__main__':
    main()