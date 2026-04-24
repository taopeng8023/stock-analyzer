#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新策略对比回测 V2 - 再测 3 个经典策略

新策略：
1. 布林带下轨反弹策略
2. KDJ 超卖金叉策略
3. 量价背离策略

对比基准：
- 双均线 MA15/20 + 移动止盈 10%（当前最优）
- 平台突破（上一轮最佳）
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

# ============== 策略 1：布林带下轨反弹 ==============
def backtest_bollinger_rebound(df):
    """
    布林带下轨反弹策略
    买入：股价触及布林带下轨 + RSI<30
    卖出：触及中轨 OR 移动止盈 10%
    """
    if len(df) < 100:
        return None
    
    # 布林带
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        bb_lower = df['bb_lower'].iloc[idx]
        bb_mid = df['bb_mid'].iloc[idx]
        rsi = df['rsi'].iloc[idx]
        
        if pd.isna([bb_lower, bb_mid, rsi]).any():
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
            # 触及中轨卖出
            elif price >= bb_mid:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
        
        # 触及下轨 + RSI 超卖
        if not position and price <= bb_lower * 1.02 and rsi < 30:
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

# ============== 策略 2：KDJ 超卖金叉 ==============
def backtest_kdj_oversold(df):
    """
    KDJ 超卖金叉策略
    买入：K<20, D<20, K 上穿 D（金叉）
    卖出：K>80 OR K 下穿 D OR 移动止盈 10%
    """
    if len(df) < 100:
        return None
    
    # KDJ
    low_9 = df['low'].rolling(9).min()
    high_9 = df['high'].rolling(9).max()
    rsv = (df['close'] - low_9) / (high_9 - low_9) * 100
    df['k'] = rsv.rolling(3).mean()
    df['d'] = df['k'].rolling(3).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(30, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        k = df['k'].iloc[idx]
        d = df['d'].iloc[idx]
        k_prev = df['k'].iloc[idx-1]
        d_prev = df['d'].iloc[idx-1]
        
        if pd.isna([k, d, k_prev, d_prev]).any():
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
            # K>80 超买卖出
            elif k > 80:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
            # K 死叉 D
            elif k_prev >= d_prev and k < d:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
        
        # KDJ 超卖金叉
        if not position and k < 20 and d < 20 and k_prev <= d_prev and k > d:
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

# ============== 策略 3：量价背离 ==============
def backtest_volume_price_divergence(df):
    """
    量价背离策略
    买入：股价创新低 + 成交量萎缩（背离）
    卖出：股价上涨 10% OR 成交量放大 2 倍
    """
    if len(df) < 100:
        return None
    
    df['low_20d'] = df['low'].rolling(20).min()
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        low_20d = df['low_20d'].iloc[idx]
        vol_ma20 = df['vol_ma20'].iloc[idx]
        volume = df['volume'].iloc[idx]
        
        # 检查是否背离：股价创新低但成交量萎缩
        low_5d_ago = df['low'].iloc[idx-5] if idx >= 5 else price
        vol_5d_ago = df['volume'].iloc[idx-5] if idx >= 5 else volume
        
        price_new_low = price < low_5d_ago * 0.95  # 股价跌 5%
        volume_shrink = volume < vol_5d_ago * 0.7   # 成交量缩 30%
        
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
            # 成交量放大 2 倍卖出
            elif volume > vol_ma20 * 2:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
            # 持有 10 天卖出
            elif df.index[idx] - position['entry_idx'] >= 10:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
                highest = 0
        
        # 量价背离买入
        if not position and price_new_low and volume_shrink:
            if pd.notna(vol_ma20) and vol_ma20 > 0:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares, 'entry_idx': idx}
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
        
        # 持仓管理
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
        
        # 金叉买入
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
    """全市场回测"""
    print("=" * 80)
    print("🔬 新策略对比回测 V2")
    print(f"📅 回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    print(f"\n📋 测试策略:")
    print(f"   1. 布林带下轨反弹（触及下轨+RSI<30）")
    print(f"   2. KDJ 超卖金叉（K<20,D<20,金叉）")
    print(f"   3. 量价背离（股价新低 + 成交量缩）")
    print(f"   基准：双均线 MA15/20")
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    sampled = random.sample(stock_files, min(500, len(stock_files)))
    
    print(f"\n🔍 回测 {len(sampled)}只股票...\n")
    
    results = {
        'ma_base': [],
        'bollinger': [],
        'kdj': [],
        'divergence': []
    }
    
    for i, filepath in enumerate(sampled):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is None:
            continue
        
        # 回测所有策略
        r = backtest_ma_base(df)
        if r:
            r['symbol'] = symbol
            results['ma_base'].append(r)
        
        r = backtest_bollinger_rebound(df)
        if r:
            r['symbol'] = symbol
            results['bollinger'].append(r)
        
        r = backtest_kdj_oversold(df)
        if r:
            r['symbol'] = symbol
            results['kdj'].append(r)
        
        r = backtest_volume_price_divergence(df)
        if r:
            r['symbol'] = symbol
            results['divergence'].append(r)
        
        if (i + 1) % 100 == 0:
            print(f"  进度：{i+1}/{len(sampled)}")
    
    print(f"\n✅ 回测完成\n")
    
    # 输出报告
    print_report(results)
    
    return results

def print_report(results):
    """打印报告"""
    print("=" * 80)
    print("📊 策略对比报告 V2")
    print("=" * 80)
    
    strategies = [
        ('ma_base', '双均线 MA15/20（基准）'),
        ('bollinger', '布林带下轨反弹'),
        ('kdj', 'KDJ 超卖金叉'),
        ('divergence', '量价背离'),
    ]
    
    print(f"\n{'策略':<25} {'平均收益':>12} {'中位收益':>12} {'胜率':>10} {'盈利股':>10} {'交易':>8}")
    print("-" * 80)
    
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
        
        print(f"{name:<25} {avg_return:>10.2f}% {median_return:>10.2f}% {avg_winrate:>8.1f}% {profitable_ratio:>8.1f}% {avg_trades:>8.1f}")
    
    print("-" * 80)
    
    # 排名
    summary.sort(key=lambda x: x['avg_return'], reverse=True)
    
    print("\n" + "=" * 80)
    print("🏆 策略排名")
    print("=" * 80)
    
    for i, s in enumerate(summary, 1):
        medal = '🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else '  '
        print(f"{medal} {i}. {s['name']}: {s['avg_return']:+.2f}%")
    
    # 最佳策略详细
    best = summary[0]
    print(f"\n" + "=" * 80)
    print(f"🏆 最佳策略：{best['name']}")
    print("=" * 80)
    print(f"   平均收益：{best['avg_return']:+.2f}%")
    print(f"   中位收益：{best['median_return']:+.2f}%")
    print(f"   胜率：{best['win_rate']:.1f}%")
    print(f"   盈利股票：{best['profitable_ratio']:.1f}%")
    print(f"   平均交易：{best['trades']:.1f}次")
    
    # TOP 5
    results_best = results[best['key']]
    results_best.sort(key=lambda x: x['return'], reverse=True)
    
    print(f"\n🏆 {best['name']} TOP 5:")
    for i, r in enumerate(results_best[:5], 1):
        print(f"  {i}. {r['symbol']}: {r['return']:+.2f}% (胜率{r['win_rate']:.1f}%)")
    
    # 综合历次回测
    print("\n" + "=" * 80)
    print("📊 综合历次回测（13 个策略）")
    print("=" * 80)
    print("\n已测试策略:")
    print("  1. 双均线 MA15/20: +20% (全市场)")
    print("  2. 移动止盈 15%: +12.26%")
    print("  3. 移动止盈 10%: +11.53%")
    print("  4. 平台突破：-3.82%")
    print("  5. 双均线 V3 过滤：-5.92%")
    print("  6. 突破策略：-9.08%")
    print("  7. 均线多头排列：-22.07%")
    print("  8. MACD 金叉 + 均线：-25.67%")
    print(f"  9. {best['name']}: {best['avg_return']:+.2f}% (本次)")
    print("  10. 缠论组合：-1726%")
    print("  11. 动量策略：-2119%")
    print("  ...")
    
    print("\n" + "=" * 80)
    print("💡 最终结论")
    print("=" * 80)
    
    if best['key'] == 'ma_base':
        print(f"\n✅ 双均线策略仍是冠军！")
        print(f"   13 个策略回测证明：简单即美")
        print(f"   建议：双均线 MA15/20 + 移动止盈 10% + 选股池过滤")
    else:
        print(f"\n🎉 新冠军：{best['name']}")
        print(f"   建议：进一步全市场回测验证")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    results = backtest_all()
