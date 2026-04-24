#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缠论分型 + 资金流 + 均线 组合策略回测 - 优化版 V2

优化点：
1. 改 AND 为 OR - 增加信号
2. 分型窗口从 5 日改为 3 日 - 更灵敏
3. 放量要求从 1.5 倍降到 1.3 倍
4. 增加信号权重评分，不是一刀切
5. 移动止盈从 15% 优化到 12%
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

# ============== 优化后的策略参数 ==============
STRATEGY_CONFIG = {
    'ma_short': 15,
    'ma_long': 20,
    'fractal_window': 3,  # V2: 5 日→3 日，更灵敏
    'volume_threshold': 1.3,  # V2: 1.5 倍→1.3 倍
    'trailing_stop': 0.12,  # V2: 15%→12%
    'fixed_stop_loss': 0.15,
    'fee_rate': 0.0003,
    'buy_threshold': 5,  # 买入评分阈值
    'sell_threshold': 4,  # 卖出评分阈值
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

def detect_fractal(df: pd.DataFrame, window: int = 3):
    """检测缠论分型（3 日窗口）"""
    top_fractals = []
    bottom_fractals = []
    
    for i in range(window, len(df) - window):
        # 底分型
        lows = df['low'].iloc[i-window:i+window+1].values
        if df['low'].iloc[i] < lows[:window].min() and df['low'].iloc[i] <= lows[window+1:].min():
            bottom_fractals.append(i)
        
        # 顶分型
        highs = df['high'].iloc[i-window:i+window+1].values
        if df['high'].iloc[i] > highs[:window].max() and df['high'].iloc[i] >= highs[window+1:].max():
            top_fractals.append(i)
    
    return top_fractals, bottom_fractals

def detect_candlestick(df: pd.DataFrame, idx: int):
    """检测蜡烛图形态"""
    o = df['open'].iloc[idx]
    c = df['close'].iloc[idx]
    h = df['high'].iloc[idx]
    l = df['low'].iloc[idx]
    
    body = abs(c - o)
    total = h - l
    if total < 0.001:
        return None
    
    # 锤头线（看涨）
    if (min(o,c) - l) > body * 2 and (h - max(o,c)) < body * 0.5:
        return 'bull'
    
    # 射击之星（看跌）
    if (h - max(o,c)) > body * 2 and (min(o,c) - l) < body * 0.5:
        return 'bear'
    
    # 大阳线（看涨）
    if body > total * 0.6 and c > o:
        return 'bull'
    
    # 大阴线（看跌）
    if body > total * 0.6 and c < o:
        return 'bear'
    
    return None

def generate_signal_score(df: pd.DataFrame, idx: int, bottom_fractals: list, top_fractals: list) -> tuple:
    """
    生成信号评分（0-10 分）
    Returns: (buy_score, sell_score)
    """
    buy_score = 0
    sell_score = 0
    
    # 1. 缠论分型（3 分）
    if idx in bottom_fractals:
        buy_score += 3
    if idx in top_fractals:
        sell_score += 3
    
    # 2. 均线状态（3 分）
    ma15 = df['ma15'].iloc[idx]
    ma20 = df['ma20'].iloc[idx]
    ma60 = df['ma60'].iloc[idx]
    
    if pd.notna(ma15) and pd.notna(ma20):
        if ma15 > ma20:
            buy_score += 2
            # 刚金叉额外 +1
            if idx > 0 and df['ma15'].iloc[idx-1] <= df['ma20'].iloc[idx-1]:
                buy_score += 1
        else:
            sell_score += 2
    
    if pd.notna(ma60):
        if df['close'].iloc[idx] > ma60:
            buy_score += 1
        else:
            sell_score += 1
    
    # 3. 成交量（2 分）
    vol_ma20 = df['volume_ma20'].iloc[idx]
    if vol_ma20 > 0:
        vol_ratio = df['volume'].iloc[idx] / vol_ma20
        if vol_ratio > STRATEGY_CONFIG['volume_threshold']:
            buy_score += 2
        elif vol_ratio > 1.0:
            buy_score += 1
    
    # 4. 蜡烛图（2 分）
    candle = detect_candlestick(df, idx)
    if candle == 'bull':
        buy_score += 2
    elif candle == 'bear':
        sell_score += 2
    
    # 5. 动量（额外 +1）
    if idx >= 5:
        momentum = (df['close'].iloc[idx] - df['close'].iloc[idx-5]) / df['close'].iloc[idx-5]
        if momentum > 0.05:  # 5 日涨超 5%
            buy_score += 1
        elif momentum < -0.05:
            sell_score += 1
    
    return buy_score, sell_score

def backtest(df: pd.DataFrame) -> dict:
    """回测"""
    if len(df) < 100:
        return None
    
    # 计算指标
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    # 检测分型
    top_fractals, bottom_fractals = detect_fractal(df, STRATEGY_CONFIG['fractal_window'])
    
    # 回测
    capital = 100000
    position = None
    trades = []
    highest_price = 0
    max_drawdown = 0
    peak_equity = capital
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        
        # 计算当前权益
        if position:
            equity = capital + position['shares'] * price
        else:
            equity = capital
        
        # 更新最大回撤
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity
        if dd > max_drawdown:
            max_drawdown = dd
        
        # 检查持仓
        if position:
            highest_price = max(highest_price, price)
            
            # 移动止盈
            if highest_price > position['cost'] * 1.08:
                if price <= highest_price * (1 - STRATEGY_CONFIG['trailing_stop']):
                    profit = (price - position['cost']) / position['cost'] * 100
                    capital = position['shares'] * price * 0.9997
                    trades.append(profit)
                    position = None
                    highest_price = 0
            
            # 固定止损
            elif price <= position['cost'] * (1 - STRATEGY_CONFIG['fixed_stop_loss']):
                profit = (price - position['cost']) / position['cost'] * 100
                capital = position['shares'] * price * 0.9997
                trades.append(profit)
                position = None
                highest_price = 0
        
        # 生成信号
        buy_score, sell_score = generate_signal_score(df, idx, bottom_fractals, top_fractals)
        
        # 开仓
        if not position and buy_score >= STRATEGY_CONFIG['buy_threshold']:
            if pd.notna(price) and price > 0:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares, 'buy_idx': idx}
                    highest_price = price
        
        # 平仓信号
        elif position and sell_score >= STRATEGY_CONFIG['sell_threshold']:
            profit = (price - position['cost']) / position['cost'] * 100
            capital = position['shares'] * price * 0.9997
            trades.append(profit)
            position = None
            highest_price = 0
    
    # 清空
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    # 统计
    profitable = [t for t in trades if t > 0]
    losing = [t for t in trades if t <= 0]
    
    return {
        'total_return': (capital / 100000 - 1) * 100,
        'win_rate': len(profitable) / len(trades) * 100,
        'avg_profit': np.mean(trades),
        'avg_win': np.mean(profitable) if profitable else 0,
        'avg_loss': np.mean(losing) if losing else 0,
        'trades': len(trades),
        'max_drawdown': max_drawdown * 100,
        'final_capital': capital
    }

def backtest_all():
    """全市场回测"""
    print("=" * 80)
    print("🔬 缠论分型 + 资金流 + 均线 组合策略回测 V2（优化版）")
    print(f"📅 回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    print(f"\n📋 优化点:")
    print(f"   • 分型窗口：5 日 → 3 日（更灵敏）")
    print(f"   • 放量要求：1.5 倍 → 1.3 倍（降低门槛）")
    print(f"   • 信号逻辑：AND → 评分制（增加信号）")
    print(f"   • 移动止盈：15% → 12%（提高收益捕获）")
    print(f"   • 买入阈值：≥5 分，卖出阈值：≥4 分")
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    total = len(stock_files)
    
    print(f"\n🔍 回测全市场 {total} 只股票...\n")
    
    results = []
    
    for i, filepath in enumerate(stock_files):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is not None:
            stats = backtest(df)
            if stats:
                stats['symbol'] = symbol
                results.append(stats)
        
        if (i + 1) % 1000 == 0:
            print(f"  进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
    
    print(f"\n✅ 回测完成，有效结果：{len(results)}只股票\n")
    
    # 统计分析
    if results:
        analyze(results)
    
    return results

def analyze(results: list):
    """分析结果"""
    print("=" * 80)
    print("📊 回测结果统计")
    print("=" * 80)
    
    avg_return = np.mean([r['total_return'] for r in results])
    median_return = np.median([r['total_return'] for r in results])
    avg_winrate = np.mean([r['win_rate'] for r in results])
    profitable_stocks = [r for r in results if r['total_return'] > 0]
    avg_maxdd = np.mean([r['max_drawdown'] for r in results])
    avg_trades = np.mean([r['trades'] for r in results])
    
    print(f"\n📈 整体表现:")
    print(f"   回测股票：{len(results)}只")
    print(f"   平均收益：{avg_return:.2f}%")
    print(f"   中位收益：{median_return:.2f}%")
    print(f"   平均胜率：{avg_winrate:.1f}%")
    print(f"   盈利股票：{len(profitable_stocks)}/{len(results)} ({len(profitable_stocks)/len(results)*100:.1f}%)")
    print(f"   平均最大回撤：{avg_maxdd:.2f}%")
    print(f"   平均交易次数：{avg_trades:.1f}次")
    
    # 收益分布
    print(f"\n📊 收益分布:")
    ranges = [
        ('>50%', [r for r in results if r['total_return'] > 50]),
        ('20-50%', [r for r in results if 20 < r['total_return'] <= 50]),
        ('0-20%', [r for r in results if 0 < r['total_return'] <= 20]),
        ('-20-0%', [r for r in results if -20 < r['total_return'] <= 0]),
        ('<-20%', [r for r in results if r['total_return'] <= -20]),
    ]
    
    for name, stocks in ranges:
        print(f"   {name}: {len(stocks)}只 ({len(stocks)/len(results)*100:.1f}%)")
    
    # TOP 10
    results.sort(key=lambda x: x['total_return'], reverse=True)
    print(f"\n🏆 TOP 10 最佳:")
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. {r['symbol']}: {r['total_return']:+.2f}% (胜率{r['win_rate']:.1f}%, 交易{r['trades']}次)")
    
    # 对比双均线
    print("\n" + "=" * 80)
    print("💡 与双均线策略对比")
    print("=" * 80)
    print("双均线策略：平均收益 +20%, 胜率 50-67%, 盈利股 65%")
    print(f"组合策略 V2: 平均收益 {avg_return:.1f}%, 胜率 {avg_winrate:.1f}%, 盈利股 {len(profitable_stocks)/len(results)*100:.1f}%")
    
    if avg_return > 20:
        print("\n✅ 组合策略 V2 优于双均线！")
    elif avg_return > 15:
        print("\n👍 组合策略 V2 表现相当，可用")
    else:
        print("\n⚠️ 组合策略 V2 仍需优化")
    
    print("=" * 80)

if __name__ == '__main__':
    results = backtest_all()
