#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略对比回测 - 找到胜率最高、盈利的选股策略

策略列表:
1. 双均线 MA5/MA10
2. 双均线 MA10/MA20
3. 双均线 MA15/MA20
4. 双均线 MA20/MA60
5. MACD 金叉死叉
6. RSI 超买超卖 (30/70)
7. 布林带突破
8. KDJ 金叉死叉
9. 量价突破 (放量上涨)
10. 缠论分型 + 蜡烛图

用法:
    python3 backtest_multi_strategies.py              # 全量回测
    python3 backtest_multi_strategies.py --sample 500 # 抽样回测
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import warnings
from typing import Dict, List, Tuple
import time

warnings.filterwarnings('ignore')

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
RESULTS_DIR.mkdir(exist_ok=True)

# 回测参数
INITIAL_CAPITAL = 10000  # 初始资金
FEE_RATE = 0.001  # 交易手续费 0.1%

def load_stock_data(symbol: str) -> pd.DataFrame:
    """加载股票数据"""
    filepath = DATA_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data or 'items' not in data:
            return None
        
        # 获取字段和数据
        fields = data['fields']
        items = data['items']
        
        # 转换为 DataFrame
        df = pd.DataFrame(items, columns=fields)
        
        # 重命名列
        df = df.rename(columns={
            'trade_date': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume',
            'amount': 'amount'
        })
        
        # 转换日期
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        # 按日期排序（从旧到新）
        df = df.sort_values('date').reset_index(drop=True)
        
        # 转换数值
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    except Exception as e:
        return None

# ============== 策略实现 ==============

def calc_ma(df: pd.DataFrame, period: int) -> pd.Series:
    """计算均线"""
    return df['close'].rolling(period).mean()

def calc_macd(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算 MACD"""
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd = (dif - dea) * 2
    return dif, dea, macd

def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算 RSI"""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_kdj(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算 KDJ"""
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    j = 3 * k - 2 * d
    return k, d, j

def calc_boll(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算布林带"""
    mid = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    return upper, mid, lower

def detect_fractal(df: pd.DataFrame) -> pd.Series:
    """检测分型 (缠论)"""
    # 底分型: 中间K线的低点比左右两边都低
    # 顶分型: 中间K线的高点比左右两边都高
    fractal = pd.Series(0, index=df.index)
    
    for i in range(1, len(df) - 1):
        # 底分型
        if df['low'].iloc[i] < df['low'].iloc[i-1] and df['low'].iloc[i] < df['low'].iloc[i+1]:
            fractal.iloc[i] = -1  # 底分型
        # 顶分型
        if df['high'].iloc[i] > df['high'].iloc[i-1] and df['high'].iloc[i] > df['high'].iloc[i+1]:
            fractal.iloc[i] = 1  # 顶分型
    
    return fractal

def detect_candlestick(df: pd.DataFrame) -> pd.Series:
    """检测蜡烛图形态"""
    signal = pd.Series(0, index=df.index)
    
    for i in range(1, len(df)):
        o1, c1, h1, l1 = df['open'].iloc[i-1], df['close'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1]
        o2, c2, h2, l2 = df['open'].iloc[i], df['close'].iloc[i], df['high'].iloc[i], df['low'].iloc[i]
        
        # 看涨形态
        # 大阳线
        if c2 > o2 and (c2 - o2) / o2 > 0.03:
            signal.iloc[i] = 1
        
        # 看涨吞没
        if c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1:
            signal.iloc[i] = 1
        
        # 锤头线
        if c2 > o2 and (l2 - min(o2, c2)) > (h2 - max(o2, c2)) * 2 and (l2 - min(o2, c2)) > (c2 - o2) * 2:
            signal.iloc[i] = 1
        
        # 看跌形态
        # 大阴线
        if c2 < o2 and (o2 - c2) / o2 > 0.03:
            signal.iloc[i] = -1
        
        # 看跌吞没
        if c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1:
            signal.iloc[i] = -1
        
        # 射击之星
        if c2 < o2 and (h2 - max(o2, c2)) > (max(o2, c2) - l2) * 2 and (h2 - max(o2, c2)) > (o2 - c2) * 2:
            signal.iloc[i] = -1
    
    return signal

# ============== 策略信号生成 ==============

def strategy_ma_cross(df: pd.DataFrame, short: int, long: int) -> pd.Series:
    """双均线金叉死叉策略"""
    ma_short = calc_ma(df, short)
    ma_long = calc_ma(df, long)
    
    signal = pd.Series(0, index=df.index)
    
    # 金叉买入
    cross_up = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
    signal[cross_up] = 1
    
    # 死叉卖出
    cross_down = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
    signal[cross_down] = -1
    
    return signal

def strategy_macd(df: pd.DataFrame) -> pd.Series:
    """MACD 金叉死叉策略"""
    dif, dea, macd = calc_macd(df)
    
    signal = pd.Series(0, index=df.index)
    
    # MACD 金叉买入
    cross_up = (dif > dea) & (dif.shift(1) <= dea.shift(1)) & (dif < 0)  # 零轴下金叉
    signal[cross_up] = 1
    
    # MACD 死叉卖出
    cross_down = (dif < dea) & (dif.shift(1) >= dea.shift(1))
    signal[cross_down] = -1
    
    return signal

def strategy_rsi(df: pd.DataFrame, low: int = 30, high: int = 70) -> pd.Series:
    """RSI 超买超卖策略"""
    rsi = calc_rsi(df)
    
    signal = pd.Series(0, index=df.index)
    
    # RSI < 30 超卖买入
    oversold = (rsi < low) & (rsi.shift(1) >= low)
    signal[oversold] = 1
    
    # RSI > 70 超买卖出
    overbought = (rsi > high) & (rsi.shift(1) <= high)
    signal[overbought] = -1
    
    return signal

def strategy_boll(df: pd.DataFrame) -> pd.Series:
    """布林带突破策略"""
    upper, mid, lower = calc_boll(df)
    
    signal = pd.Series(0, index=df.index)
    
    # 突破下轨买入
    break_lower = (df['close'] < lower) & (df['close'].shift(1) >= lower.shift(1))
    signal[break_lower] = 1
    
    # 突破上轨卖出
    break_upper = (df['close'] > upper) & (df['close'].shift(1) <= upper.shift(1))
    signal[break_upper] = -1
    
    return signal

def strategy_kdj(df: pd.DataFrame) -> pd.Series:
    """KDJ 金叉死叉策略"""
    k, d, j = calc_kdj(df)
    
    signal = pd.Series(0, index=df.index)
    
    # K线从下向上穿过D线，且J<20
    cross_up = (k > d) & (k.shift(1) <= d.shift(1)) & (j < 20)
    signal[cross_up] = 1
    
    # K线从上向下穿过D线，且J>80
    cross_down = (k < d) & (k.shift(1) >= d.shift(1)) & (j > 80)
    signal[cross_down] = -1
    
    return signal

def strategy_volume(df: pd.DataFrame) -> pd.Series:
    """量价突破策略"""
    # 放量上涨买入
    vol_ma = df['volume'].rolling(5).mean()
    
    signal = pd.Series(0, index=df.index)
    
    # 放量上涨 (成交量 > 5日均量 * 1.5 且 收盘价上涨)
    vol_up = (df['volume'] > vol_ma * 1.5) & (df['close'] > df['close'].shift(1))
    signal[vol_up] = 1
    
    # 放量下跌卖出
    vol_down = (df['volume'] > vol_ma * 1.5) & (df['close'] < df['close'].shift(1))
    signal[vol_down] = -1
    
    return signal

def strategy_chanlun_candle(df: pd.DataFrame) -> pd.Series:
    """缠论分型 + 蜡烛图组合策略"""
    fractal = detect_fractal(df)
    candle = detect_candlestick(df)
    
    signal = pd.Series(0, index=df.index)
    
    # 底分型 + 看涨蜡烛图 = 强买入信号
    strong_buy = (fractal == -1) & (candle == 1)
    signal[strong_buy] = 1
    
    # 顶分型 + 看跌蜡烛图 = 强卖出信号
    strong_sell = (fractal == 1) & (candle == -1)
    signal[strong_sell] = -1
    
    return signal

# ============== 回测引擎 ==============

def run_backtest(df: pd.DataFrame, signal: pd.Series, name: str) -> Dict:
    """运行回测"""
    if df is None or len(df) < 50:
        return None
    
    capital = INITIAL_CAPITAL
    position = 0  # 持仓股数
    buy_price = 0
    trades = []
    max_value = capital  # 最高市值
    max_drawdown = 0
    
    for i in range(len(df)):
        date = df['date'].iloc[i]
        close = df['close'].iloc[i]
        
        # 更新最高市值和最大回撤
        current_value = capital + position * close
        if current_value > max_value:
            max_value = current_value
        drawdown = (max_value - current_value) / max_value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        
        # 买入信号
        if signal.iloc[i] == 1 and position == 0:
            buy_amount = capital * (1 - FEE_RATE)
            position = buy_amount / close
            buy_price = close
            capital = 0
            trades.append({
                'type': 'buy',
                'date': date,
                'price': close,
                'shares': position
            })
        
        # 卖出信号
        elif signal.iloc[i] == -1 and position > 0:
            sell_amount = position * close * (1 - FEE_RATE)
            profit_pct = (close - buy_price) / buy_price * 100
            capital = sell_amount
            trades.append({
                'type': 'sell',
                'date': date,
                'price': close,
                'shares': position,
                'profit_pct': profit_pct
            })
            position = 0
    
    # 最终市值
    final_value = capital + position * df['close'].iloc[-1]
    total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # 计算胜率
    sell_trades = [t for t in trades if t['type'] == 'sell']
    win_trades = [t for t in sell_trades if t.get('profit_pct', 0) > 0]
    win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0
    
    return {
        'strategy': name,
        'total_return': total_return,
        'win_rate': win_rate,
        'trade_count': len(sell_trades),
        'max_drawdown': max_drawdown * 100,
        'final_value': final_value
    }

def backtest_single_stock(symbol: str) -> List[Dict]:
    """单只股票多策略回测"""
    df = load_stock_data(symbol)
    if df is None or len(df) < 100:
        return None
    
    results = []
    
    # 策略列表
    strategies = [
        ('MA5/MA10', lambda d: strategy_ma_cross(d, 5, 10)),
        ('MA10/MA20', lambda d: strategy_ma_cross(d, 10, 20)),
        ('MA15/MA20', lambda d: strategy_ma_cross(d, 15, 20)),
        ('MA20/MA60', lambda d: strategy_ma_cross(d, 20, 60)),
        ('MACD', strategy_macd),
        ('RSI', strategy_rsi),
        ('BOLL', strategy_boll),
        ('KDJ', strategy_kdj),
        ('Volume', strategy_volume),
        ('Chanlun+Candle', strategy_chanlun_candle),
    ]
    
    for name, func in strategies:
        try:
            signal = func(df)
            result = run_backtest(df, signal, name)
            if result:
                result['symbol'] = symbol
                results.append(result)
        except:
            pass
    
    return results

def backtest_all_stocks(sample: int = None):
    """全市场回测"""
    print('=' * 80)
    print('📊 多策略对比回测')
    print('=' * 80)
    
    # 获取所有股票文件
    all_files = list(DATA_DIR.glob('*.json'))
    all_symbols = [f.stem for f in all_files if f.name not in ['README', 'stock_list']]
    
    if sample:
        all_symbols = all_symbols[:sample]
    
    print(f'回测股票数：{len(all_symbols)}')
    print()
    
    start_time = time.time()
    
    # 策略统计汇总
    strategy_stats = {}
    
    for i, symbol in enumerate(all_symbols):
        if (i + 1) % 200 == 0:
            elapsed = time.time() - start_time
            print(f'进度：{i+1}/{len(all_symbols)} (耗时：{elapsed:.1f}秒)')
        
        results = backtest_single_stock(symbol)
        if results:
            for r in results:
                name = r['strategy']
                if name not in strategy_stats:
                    strategy_stats[name] = {
                        'returns': [],
                        'win_rates': [],
                        'trade_counts': [],
                        'drawdowns': [],
                        'win_stocks': 0,
                        'total_stocks': 0
                    }
                
                strategy_stats[name]['returns'].append(r['total_return'])
                strategy_stats[name]['win_rates'].append(r['win_rate'])
                strategy_stats[name]['trade_counts'].append(r['trade_count'])
                strategy_stats[name]['drawdowns'].append(r['max_drawdown'])
                strategy_stats[name]['total_stocks'] += 1
                if r['total_return'] > 0:
                    strategy_stats[name]['win_stocks'] += 1
    
    elapsed = time.time() - start_time
    
    # 输出结果
    print()
    print('=' * 80)
    print('📊 多策略对比结果')
    print('=' * 80)
    print()
    
    # 排序：按平均收益排序
    sorted_strategies = sorted(
        strategy_stats.items(),
        key=lambda x: np.mean(x[1]['returns']),
        reverse=True
    )
    
    print(f"{'策略':<20} {'平均收益':>10} {'胜率':>10} {'盈利股票':>10} {'交易次数':>10} {'最大回撤':>10}")
    print('-' * 80)
    
    final_results = []
    for name, stats in sorted_strategies:
        avg_return = np.mean(stats['returns'])
        avg_win_rate = np.mean([w for w in stats['win_rates'] if w > 0]) if stats['win_rates'] else 0
        win_pct = stats['win_stocks'] / stats['total_stocks'] * 100 if stats['total_stocks'] > 0 else 0
        avg_trades = np.mean(stats['trade_counts'])
        avg_drawdown = np.mean(stats['drawdowns'])
        
        print(f"{name:<20} {avg_return:>9.2f}% {avg_win_rate:>9.2f}% {win_pct:>9.2f}% {avg_trades:>10.1f} {avg_drawdown:>9.2f}%")
        
        final_results.append({
            'strategy': name,
            'avg_return': avg_return,
            'avg_win_rate': avg_win_rate,
            'win_stock_pct': win_pct,
            'avg_trades': avg_trades,
            'avg_drawdown': avg_drawdown,
            'total_stocks': stats['total_stocks']
        })
    
    print()
    print('=' * 80)
    print('🏆 推荐策略')
    print('=' * 80)
    
    # 找到胜率 > 50% 且平均收益 > 0 的策略
    good_strategies = [r for r in final_results if r['avg_win_rate'] > 50 and r['avg_return'] > 0]
    
    if good_strategies:
        best = good_strategies[0]
        print(f"✅ 最佳策略: {best['strategy']}")
        print(f"   平均收益: {best['avg_return']:.2f}%")
        print(f"   平均胜率: {best['avg_win_rate']:.2f}%")
        print(f"   盈利股票占比: {best['win_stock_pct']:.2f}%")
        print(f"   平均交易次数: {best['avg_trades']:.1f}")
    else:
        # 找收益最高的
        best = final_results[0]
        print(f"⚠️ 收益最高策略: {best['strategy']}")
        print(f"   平均收益: {best['avg_return']:.2f}%")
        print(f"   平均胜率: {best['avg_win_rate']:.2f}%")
        print(f"   盈利股票占比: {best['win_stock_pct']:.2f}%")
    
    # 保存结果
    output_file = RESULTS_DIR / f'multi_strategy_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    pd.DataFrame(final_results).to_csv(output_file, index=False)
    print()
    print(f'结果已保存: {output_file}')
    
    return final_results

def main():
    parser = argparse.ArgumentParser(description='多策略对比回测')
    parser.add_argument('--sample', type=int, help='抽样数量')
    
    args = parser.parse_args()
    
    backtest_all_stocks(args.sample)

if __name__ == '__main__':
    main()