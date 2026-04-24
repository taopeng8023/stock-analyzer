#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缠论分型 + 资金流 + 均线 组合策略回测 - 抽样快速版
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

# 策略参数
STRATEGY_CONFIG = {
    'ma_short': 15,
    'ma_long': 20,
    'fractal_window': 5,
    'volume_threshold': 1.5,
    'trailing_stop': 0.15,
    'fixed_stop_loss': 0.15,
    'fee_rate': 0.0003,
}

def load_data(symbol: str) -> pd.DataFrame:
    """加载股票数据"""
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

def detect_fractal(df: pd.DataFrame, window: int = 5):
    """检测分型"""
    bottom_fractals = []
    for i in range(window, len(df) - window):
        lows = df['low'].iloc[i-window:i+window+1].values
        if df['low'].iloc[i] < lows[:window].min() and df['low'].iloc[i] <= lows[window+1:].min():
            bottom_fractals.append(i)
    return bottom_fractals

def backtest(df: pd.DataFrame) -> dict:
    """简化回测"""
    if len(df) < 100:
        return None
    
    # 计算指标
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    # 检测分型
    bottom_fractals = detect_fractal(df, STRATEGY_CONFIG['fractal_window'])
    
    # 模拟回测
    capital = 100000
    position = None
    trades = []
    highest_price = 0
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        
        # 检查持仓
        if position:
            highest_price = max(highest_price, price)
            
            # 移动止盈
            if highest_price > position['cost'] * 1.05:
                if price <= highest_price * (1 - STRATEGY_CONFIG['trailing_stop']):
                    profit = (price - position['cost']) / position['cost'] * 100
                    capital = position['shares'] * price * 0.9997
                    trades.append(profit)
                    position = None
            
            # 固定止损
            elif price <= position['cost'] * (1 - STRATEGY_CONFIG['fixed_stop_loss']):
                profit = (price - position['cost']) / position['cost'] * 100
                capital = position['shares'] * price * 0.9997
                trades.append(profit)
                position = None
        
        # 开仓信号
        if not position and idx in bottom_fractals:
            # 均线金叉
            if df['ma15'].iloc[idx] > df['ma20'].iloc[idx]:
                # 放量
                vol_ratio = df['volume'].iloc[idx] / df['volume_ma20'].iloc[idx]
                if vol_ratio > 1.3:  # 降低要求
                    shares = int(capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        position = {'cost': price, 'shares': shares}
                        highest_price = price
    
    # 清空持仓
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    return {
        'total_return': (capital / 100000 - 1) * 100,
        'win_rate': sum(1 for t in trades if t > 0) / len(trades) * 100,
        'avg_profit': np.mean(trades),
        'trades': len(trades)
    }

def main():
    print("=" * 80)
    print("🔬 缠论分型 + 资金流 + 均线 组合策略回测 (抽样快速版)")
    print("=" * 80)
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    
    # 随机抽样 500 只
    sample_size = min(500, len(stock_files))
    sampled = random.sample(stock_files, sample_size)
    
    print(f"\n📊 抽样：{sample_size}只股票 / 总共{len(stock_files)}只")
    print(f"📋 策略：缠论底分型 + MA15/20 金叉 + 放量 + 移动止盈 15%\n")
    
    results = []
    
    for i, filepath in enumerate(sampled):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is not None:
            stats = backtest(df)
            if stats:
                stats['symbol'] = symbol
                results.append(stats)
        
        if (i + 1) % 100 == 0:
            print(f"  进度：{i+1}/{sample_size}")
    
    print(f"\n✅ 有效结果：{len(results)}只\n")
    
    # 统计
    if results:
        avg_return = np.mean([r['total_return'] for r in results])
        median_return = np.median([r['total_return'] for r in results])
        avg_winrate = np.mean([r['win_rate'] for r in results])
        profitable = sum(1 for r in results if r['total_return'] > 0)
        
        print("=" * 80)
        print("📊 回测结果")
        print("=" * 80)
        print(f"平均收益：{avg_return:.2f}%")
        print(f"中位收益：{median_return:.2f}%")
        print(f"平均胜率：{avg_winrate:.1f}%")
        print(f"盈利股票：{profitable}/{len(results)} ({profitable/len(results)*100:.1f}%)")
        
        # TOP 10
        results.sort(key=lambda x: x['total_return'], reverse=True)
        print(f"\n🏆 TOP 10:")
        for i, r in enumerate(results[:10], 1):
            print(f"  {i}. {r['symbol']}: {r['total_return']:+.2f}% (胜率{r['win_rate']:.1f}%)")
        
        print("\n" + "=" * 80)
        print("💡 结论：与双均线策略对比")
        print("=" * 80)
        print("双均线策略：平均收益 +20%, 胜率 50-67%")
        print(f"组合策略：平均收益 {avg_return:.1f}%, 胜率 {avg_winrate:.1f}%")
        
        if avg_return > 20 and avg_winrate > 60:
            print("\n✅ 组合策略优于双均线！")
        elif avg_return > 15:
            print("\n👍 组合策略表现相当，可考虑使用")
        else:
            print("\n⚠️ 组合策略需要进一步优化")
        print("=" * 80)

if __name__ == '__main__':
    main()
