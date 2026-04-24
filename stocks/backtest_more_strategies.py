#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更多策略回测 - 测试 5 个经典策略

新策略：
1. 涨停板策略（追涨停）
2. 低位十字星策略
3. 均线粘合突破策略
4. 缺口回补策略
5. 龙头股回调策略

对比基准：
- 双均线 MA15/20（当前最优）
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

def load_data(symbol):
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

# ============== 策略 1：涨停板策略 ==============
def backtest_limit_up(df):
    """
    涨停板策略
    买入：涨停后次日买入
    卖出：持有 5 天或止损 -8%
    """
    if len(df) < 100:
        return None
    
    # 估算涨停（涨幅>9.5%）
    df['pct_change'] = df['close'].pct_change()
    
    capital = 100000
    position = None
    trades = []
    hold_days = 0
    
    for idx in range(40, len(df)):
        if pd.isna(df['pct_change'].iloc[idx]):
            continue
        
        # 持仓管理
        if position:
            hold_days += 1
            price = df['close'].iloc[idx]
            
            # 止损 -8%
            if price <= position['cost'] * 0.92:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            
            # 持有 5 天卖出
            elif hold_days >= 5:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 涨停买入（次日）
        if not position and idx > 0:
            prev_pct = df['pct_change'].iloc[idx-1]
            if pd.notna(prev_pct) and prev_pct > 0.095:  # 昨日涨停
                price = df['close'].iloc[idx]
                if pd.notna(price) and price > 0:
                    shares = int(capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        position = {'cost': price, 'shares': shares}
                        hold_days = 0
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
    }

# ============== 策略 2：低位十字星 ==============
def backtest_doji(df):
    """
    低位十字星策略
    买入：十字星 + RSI<30
    卖出：RSI>50 或持有 10 天
    """
    if len(df) < 100:
        return None
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    capital = 100000
    position = None
    trades = []
    hold_days = 0
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        o = df['open'].iloc[idx]
        c = df['close'].iloc[idx]
        h = df['high'].iloc[idx]
        l = df['low'].iloc[idx]
        
        body = abs(c - o)
        total_range = h - l
        
        # 十字星：实体<整体的 10%
        is_doji = total_range > 0 and body < total_range * 0.1
        rsi = df['rsi'].iloc[idx]
        
        # 持仓管理
        if position:
            hold_days += 1
            # RSI>50 卖出
            if rsi > 50:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 持有 10 天卖出
            elif hold_days >= 10:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 止损 -8%
            elif price <= position['cost'] * 0.92:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 低位十字星买入
        if not position and is_doji and pd.notna(rsi) and rsi < 30:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                position = {'cost': price, 'shares': shares}
                hold_days = 0
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
    }

# ============== 策略 3：均线粘合突破 ==============
def backtest_ma_squeeze(df):
    """
    均线粘合突破策略
    买入：MA5/10/20 粘合后向上突破
    卖出：移动止盈 10% 或死叉
    """
    if len(df) < 100:
        return None
    
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        ma5 = df['ma5'].iloc[idx]
        ma10 = df['ma10'].iloc[idx]
        ma20 = df['ma20'].iloc[idx]
        
        if pd.isna([ma5, ma10, ma20]).any():
            continue
        
        # 持仓管理
        if position:
            highest = max(highest, price)
            # 移动止盈 10%
            if highest > position['cost'] * 1.08 and price <= highest * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
            # 死叉卖出
            elif ma5 < ma10:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
        
        # 均线粘合（最大最小差<3%）+ 突破
        if not position:
            mas = [ma5, ma10, ma20]
            max_ma = max(mas)
            min_ma = min(mas)
            avg_ma = np.mean(mas)
            
            squeeze = (max_ma - min_ma) / avg_ma < 0.03  # 粘合<3%
            breakout = price > max_ma  # 突破所有均线
            
            if squeeze and breakout:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares}
                    highest = price
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
    }

# ============== 策略 4：缺口回补 ==============
def backtest_gap_fill(df):
    """
    缺口回补策略
    买入：向下缺口后回补
    卖出：持有 5 天或止盈 8%
    """
    if len(df) < 100:
        return None
    
    capital = 100000
    position = None
    trades = []
    hold_days = 0
    
    for idx in range(30, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        # 检测缺口
        if idx > 0:
            prev_high = df['high'].iloc[idx-1]
            prev_low = df['low'].iloc[idx-1]
            curr_low = df['low'].iloc[idx]
            curr_high = df['high'].iloc[idx]
            
            # 向下缺口
            down_gap = curr_low > prev_high
            # 向上缺口
            up_gap = curr_high < prev_low
        else:
            down_gap = False
            up_gap = False
        
        # 持仓管理
        if position:
            hold_days += 1
            # 止盈 8%
            if price >= position['cost'] * 1.08:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 持有 5 天卖出
            elif hold_days >= 5:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 止损 -8%
            elif price <= position['cost'] * 0.92:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 向下缺口后买入（博弈回补）
        if not position and down_gap:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                position = {'cost': price, 'shares': shares}
                hold_days = 0
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
    }

# ============== 策略 5：龙头股回调 ==============
def backtest_leader_pullback(df):
    """
    龙头股回调策略
    买入：20 日涨>30% 后回调到 MA10
    卖出：反弹 10% 或止损 -10%
    """
    if len(df) < 100:
        return None
    
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    # 20 日涨幅
    df['momentum_20d'] = df['close'].pct_change(20)
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        momentum = df['momentum_20d'].iloc[idx]
        ma10 = df['ma10'].iloc[idx]
        
        if pd.isna([momentum, ma10]).any():
            continue
        
        # 持仓管理
        if position:
            # 止盈 10%
            if price >= position['cost'] * 1.10:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 止损 -10%
            elif price <= position['cost'] * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 跌破 MA10 卖出
            elif price < ma10 * 0.98:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 龙头股回调买入
        if not position and momentum > 0.30:  # 20 日涨>30%
            # 回调到 MA10 附近
            if abs(price - ma10) / ma10 < 0.02:  # 距离 MA10<2%
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares}
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
    }

# ============== 基准策略 ==============
def backtest_ma_base(df):
    """双均线基准策略"""
    if len(df) < 100:
        return None
    
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        ma15 = df['ma15'].iloc[idx]
        ma20 = df['ma20'].iloc[idx]
        ma15_prev = df['ma15'].iloc[idx-1]
        ma20_prev = df['ma20'].iloc[idx-1]
        
        if pd.isna([ma15, ma20, ma15_prev, ma20_prev]).any():
            continue
        
        if position:
            highest = max(highest, price)
            if highest > position['cost'] * 1.08 and price <= highest * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
            elif ma15_prev >= ma20_prev and ma15 < ma20:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
        
        if not position and ma15_prev <= ma20_prev and ma15 > ma20:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                position = {'cost': price, 'shares': shares}
                highest = price
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100,
        'trades': len(trades),
    }

# ============== 主函数 ==============
def backtest_all():
    print("=" * 80)
    print("🔬 更多策略回测 - 5 个新策略")
    print(f"📅 回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    print(f"\n📋 测试策略:")
    print(f"   1. 涨停板策略（追涨停）")
    print(f"   2. 低位十字星（RSI<30+ 十字星）")
    print(f"   3. 均线粘合突破（MA5/10/20 粘合<3%）")
    print(f"   4. 缺口回补（向下缺口博弈）")
    print(f"   5. 龙头股回调（20 日涨 30%+ 回调 MA10）")
    print(f"   基准：双均线 MA15/20")
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    sampled = random.sample(stock_files, min(500, len(stock_files)))
    
    print(f"\n🔍 回测 {len(sampled)}只股票...\n")
    
    results = {
        'ma_base': [],
        'limit_up': [],
        'doji': [],
        'ma_squeeze': [],
        'gap_fill': [],
        'leader': []
    }
    
    for i, filepath in enumerate(sampled):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is None:
            continue
        
        r = backtest_ma_base(df)
        if r:
            r['symbol'] = symbol
            results['ma_base'].append(r)
        
        r = backtest_limit_up(df)
        if r:
            r['symbol'] = symbol
            results['limit_up'].append(r)
        
        r = backtest_doji(df)
        if r:
            r['symbol'] = symbol
            results['doji'].append(r)
        
        r = backtest_ma_squeeze(df)
        if r:
            r['symbol'] = symbol
            results['ma_squeeze'].append(r)
        
        r = backtest_gap_fill(df)
        if r:
            r['symbol'] = symbol
            results['gap_fill'].append(r)
        
        r = backtest_leader_pullback(df)
        if r:
            r['symbol'] = symbol
            results['leader'].append(r)
        
        if (i + 1) % 100 == 0:
            print(f"  进度：{i+1}/{len(sampled)}")
    
    print(f"\n✅ 回测完成\n")
    
    print_report(results)
    
    return results

def print_report(results):
    print("=" * 80)
    print("📊 策略对比报告")
    print("=" * 80)
    
    strategies = [
        ('ma_base', '双均线 MA15/20（基准）'),
        ('limit_up', '涨停板策略'),
        ('doji', '低位十字星'),
        ('ma_squeeze', '均线粘合突破'),
        ('gap_fill', '缺口回补'),
        ('leader', '龙头股回调'),
    ]
    
    print(f"\n{'策略':<20} {'平均收益':>12} {'中位收益':>12} {'胜率':>10} {'盈利股':>10} {'交易':>8}")
    print("-" * 85)
    
    summary = []
    
    for key, name in strategies:
        r = results[key]
        if not r:
            continue
        
        avg_return = np.mean([x['return'] for x in r])
        median_return = np.median([x['return'] for x in r])
        avg_winrate = np.mean([x['win_rate'] for x in r])
        profitable = len([x for x in r if x['return'] > 0])
        profitable_ratio = profitable / len(r) * 100
        avg_trades = np.mean([x['trades'] for x in r])
        
        summary.append({
            'key': key,
            'name': name,
            'avg_return': avg_return,
            'median_return': median_return,
            'win_rate': avg_winrate,
            'profitable_ratio': profitable_ratio,
            'trades': avg_trades,
            'count': len(r)
        })
        
        print(f"{name:<20} {avg_return:>10.2f}% {median_return:>10.2f}% {avg_winrate:>8.1f}% {profitable_ratio:>8.1f}% {avg_trades:>8.1f}")
    
    print("-" * 85)
    
    summary.sort(key=lambda x: x['avg_return'], reverse=True)
    
    print("\n" + "=" * 80)
    print("🏆 策略排名")
    print("=" * 80)
    
    for i, s in enumerate(summary, 1):
        medal = '🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else '  '
        print(f"{medal} {i}. {s['name']}: {s['avg_return']:+.2f}%")
    
    best = summary[0]
    print(f"\n" + "=" * 80)
    print(f"🏆 最佳策略：{best['name']}")
    print("=" * 80)
    print(f"   平均收益：{best['avg_return']:+.2f}%")
    print(f"   中位收益：{best['median_return']:+.2f}%")
    print(f"   胜率：{best['win_rate']:.1f}%")
    print(f"   盈利股票：{best['profitable_ratio']:.1f}%")
    
    print("\n" + "=" * 80)
    print("📊 综合历次回测（18 个策略）")
    print("=" * 80)
    print("\n已测试策略排名:")
    print("  1. 双均线 MA15/20: +20% (全市场)")
    print("  2. 移动止盈 15%: +12.26%")
    print("  3. 移动止盈 10%: +11.53%")
    print("  4. 平台突破：-3.82%")
    print(f"  5. {best['name']}: {best['avg_return']:+.2f}% (本次)")
    print("  ...")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    results = backtest_all()
