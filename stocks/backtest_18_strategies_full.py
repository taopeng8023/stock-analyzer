#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
18 个策略全市场回测对比报告

整合所有已测试策略，使用全市场 3620 只股票数据进行回测对比

策略列表:
1. 双均线 MA15/20 (基准)
2. 移动止盈 15%
3. 移动止盈 10%
4. 平台突破
5. 涨停板策略
6. 低位十字星
7. 均线粘合突破
8. 缺口回补
9. 龙头股回调
10. 布林带下轨反弹
11. KDJ 超卖金叉
12. 量价背离
13. 缠论 + 蜡烛图
14. RSI 超买超卖
15. MACD 金叉死叉
16. 三重均线
17. 延迟入场
18. 成交量萎缩

数据来源：data_tushare/ 缓存的 3620 只股票
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import random
import warnings
import sys
import statistics
warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
REPORT_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_reports')
REPORT_DIR.mkdir(exist_ok=True)

def load_data(symbol):
    """加载股票数据（带异常过滤）"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data or len(data) < 100:
        return None
    
    # 过滤异常数据：价格必须为正且合理 (0.1-1000 元)
    filtered = [d for d in data 
                if d.get('收盘', 0) > 0.1 and d.get('收盘', 0) < 1000
                and d.get('最高', 0) > 0 and d.get('最低', 0) > 0
                and d.get('成交量', 0) >= 0]
    
    if len(filtered) < 100:
        return None
    
    df = pd.DataFrame(filtered)
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume'
    })
    # 兼容多种日期格式
    try:
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    except (ValueError, TypeError):
        df['date'] = pd.to_datetime(df['date'])  # 自动识别格式
    return df.sort_values('date').reset_index(drop=True)


# ============== 策略 1: 双均线 MA15/20 ==============
def backtest_ma_base(df):
    """双均线策略 (基准)"""
    if len(df) < 50:
        return None
    
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(30, len(df)):
        if pd.isna(df['ma15'].iloc[idx]) or pd.isna(df['ma20'].iloc[idx]):
            continue
        
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        if position:
            # 死叉卖出
            if df['ma15'].iloc[idx] < df['ma20'].iloc[idx] and df['ma15'].iloc[idx-1] >= df['ma20'].iloc[idx-1]:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 金叉买入
        if not position and df['ma15'].iloc[idx] > df['ma20'].iloc[idx] and df['ma15'].iloc[idx-1] <= df['ma20'].iloc[idx-1]:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 2: 移动止盈 15% ==============
def backtest_ma_trailing_15(df):
    """双均线 + 移动止盈 15%"""
    if len(df) < 50:
        return None
    
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(30, len(df)):
        if pd.isna(df['ma15'].iloc[idx]) or pd.isna(df['ma20'].iloc[idx]):
            continue
        
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        if position:
            highest = max(highest, price)
            # 移动止盈 15%
            if highest > position['cost'] * 1.15 and price <= highest * 0.85:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 死叉卖出
            elif df['ma15'].iloc[idx] < df['ma20'].iloc[idx]:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and df['ma15'].iloc[idx] > df['ma20'].iloc[idx] and df['ma15'].iloc[idx-1] <= df['ma20'].iloc[idx-1]:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 3: 移动止盈 10% ==============
def backtest_ma_trailing_10(df):
    """双均线 + 移动止盈 10%"""
    if len(df) < 50:
        return None
    
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    highest = 0
    
    for idx in range(30, len(df)):
        if pd.isna(df['ma15'].iloc[idx]) or pd.isna(df['ma20'].iloc[idx]):
            continue
        
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        if position:
            highest = max(highest, price)
            if highest > position['cost'] * 1.08 and price <= highest * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            elif df['ma15'].iloc[idx] < df['ma20'].iloc[idx]:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and df['ma15'].iloc[idx] > df['ma20'].iloc[idx] and df['ma15'].iloc[idx-1] <= df['ma20'].iloc[idx-1]:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 4: 平台突破 ==============
def backtest_platform_breakout(df):
    """平台突破策略"""
    if len(df) < 60:
        return None
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        # 20 日平台高点
        platform_high = df['high'].rolling(20).max().iloc[idx-20:idx].max()
        platform_low = df['low'].rolling(20).min().iloc[idx-20:idx].min()
        
        if position:
            # 跌破平台低点止损
            if price < platform_low * 0.98:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            # 持有 10 天卖出
            elif position['days'] >= 10:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        # 突破平台买入
        if not position and price > platform_high * 1.02:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                position = {'cost': price, 'shares': shares, 'days': 0}
        
        if position:
            position['days'] = position.get('days', 0) + 1
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 5: 涨停板 ==============
def backtest_limit_up(df):
    """涨停板策略"""
    if len(df) < 100:
        return None
    
    df['pct_change'] = df['close'].pct_change()
    
    capital = 100000
    position = None
    trades = []
    hold_days = 0
    
    for idx in range(40, len(df)):
        if pd.isna(df['pct_change'].iloc[idx]):
            continue
        
        if position:
            hold_days += 1
            price = df['close'].iloc[idx]
            
            if price <= position['cost'] * 0.92:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            elif hold_days >= 5:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and idx > 0:
            prev_pct = df['pct_change'].iloc[idx-1]
            if pd.notna(prev_pct) and prev_pct > 0.095:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 6: 低位十字星 ==============
def backtest_doji(df):
    """低位十字星策略"""
    if len(df) < 100:
        return None
    
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
        is_doji = total_range > 0 and body < total_range * 0.1
        rsi = df['rsi'].iloc[idx]
        
        if position:
            hold_days += 1
            if rsi > 50 or hold_days >= 10:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        elif is_doji and pd.notna(rsi) and rsi < 30:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 7: 均线粘合突破 ==============
def backtest_ma_squeeze(df):
    """均线粘合突破策略"""
    if len(df) < 60:
        return None
    
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        ma5 = df['ma5'].iloc[idx]
        ma10 = df['ma10'].iloc[idx]
        ma20 = df['ma20'].iloc[idx]
        
        if pd.isna([ma5, ma10, ma20]).any():
            continue
        
        # 均线粘合度
        ma_avg = (ma5 + ma10 + ma20) / 3
        squeeze = max(abs(ma5-ma_avg), abs(ma10-ma_avg), abs(ma20-ma_avg)) / ma_avg
        
        if position:
            if price < position['cost'] * 0.92 or price > position['cost'] * 1.20:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and squeeze < 0.03 and price > ma5 > ma10 > ma20:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 8: 缺口回补 ==============
def backtest_gap_fill(df):
    """缺口回补策略"""
    if len(df) < 60:
        return None
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        prev_close = df['close'].iloc[idx-1]
        prev_low = df['low'].iloc[idx-1]
        
        # 向下缺口
        has_gap_down = price < prev_low * 0.98
        
        if position:
            # 缺口回补或持有 5 天
            if price >= prev_close or position['days'] >= 5:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            elif price < position['cost'] * 0.95:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and has_gap_down:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                position = {'cost': price, 'shares': shares, 'prev_close': prev_close, 'days': 0}
        
        if position:
            position['days'] = position.get('days', 0) + 1
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 9: 龙头股回调 ==============
def backtest_leader_pullback(df):
    """龙头股回调策略"""
    if len(df) < 100:
        return None
    
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(80, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        # 20 日涨幅>30%
        price_20d_ago = df['close'].iloc[idx-20]
        gain_20d = (price - price_20d_ago) / price_20d_ago
        
        # 从高点回调
        high_20d = df['high'].rolling(20).max().iloc[idx]
        pullback = (high_20d - price) / high_20d
        
        if position:
            if price < position['cost'] * 0.90 or price > position['cost'] * 1.25:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and gain_20d > 0.30 and 0.05 < pullback < 0.15 and price > df['ma20'].iloc[idx]:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 10: 布林带下轨反弹 ==============
def backtest_bollinger_rebound(df):
    """布林带下轨反弹策略"""
    if len(df) < 100:
        return None
    
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
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
        
        if position:
            highest = max(highest, price)
            if highest > position['cost'] * 1.08 and price <= highest * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            elif price >= bb_mid:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 11: KDJ 超卖金叉 ==============
def backtest_kdj_oversold(df):
    """KDJ 超卖金叉策略"""
    if len(df) < 100:
        return None
    
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
        
        if position:
            highest = max(highest, price)
            if k > 80 or (k < d and k_prev >= d_prev):
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
            elif highest > position['cost'] * 1.08 and price <= highest * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and k < 20 and d < 20 and k > d and k_prev <= d_prev:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 12: 量价背离 ==============
def backtest_volume_price_divergence(df):
    """量价背离策略"""
    if len(df) < 100:
        return None
    
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        price_low_20 = df['low'].rolling(20).min().iloc[idx]
        vol = df['volume'].iloc[idx]
        vol_ma = df['vol_ma20'].iloc[idx]
        
        if pd.isna([price_low_20, vol_ma]).any():
            continue
        
        # 股价新低 + 成交量萎缩
        is_divergence = price <= price_low_20 * 1.02 and vol < vol_ma * 0.7
        
        if position:
            if price > position['cost'] * 1.10 or price < position['cost'] * 0.95:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and is_divergence:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 13: 缠论 + 蜡烛图 ==============
def backtest_chanlun_candle(df):
    """缠论 + 蜡烛图结合策略"""
    if len(df) < 100:
        return None
    
    capital = 100000
    position = None
    trades = []
    
    def detect_fractal(idx, window=5):
        if idx < window or idx >= len(df) - window:
            return None
        highs = [df['high'].iloc[idx+j] for j in range(-window, window+1)]
        lows = [df['low'].iloc[idx+j] for j in range(-window, window+1)]
        if df['high'].iloc[idx] == max(highs):
            return 'top'
        if df['low'].iloc[idx] == min(lows):
            return 'bottom'
        return None
    
    def detect_pattern(idx):
        o = df['open'].iloc[idx]
        c = df['close'].iloc[idx]
        h = df['high'].iloc[idx]
        l = df['low'].iloc[idx]
        body = abs(c - o)
        total = h - l
        if total > 0 and body < total * 0.1:
            return 'doji'
        if body > total * 0.7:
            return 'big'
        return None
    
    for idx in range(80, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        fractal = detect_fractal(idx)
        pattern = detect_pattern(idx)
        
        if position:
            if price < position['cost'] * 0.92 or price > position['cost'] * 1.15:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and fractal == 'bottom' and pattern in ['doji', 'big']:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 14: RSI 超买超卖 ==============
def backtest_rsi(df):
    """RSI 超买超卖策略"""
    if len(df) < 100:
        return None
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        rsi = df['rsi'].iloc[idx]
        if pd.isna(rsi):
            continue
        
        if position:
            if rsi > 70 or price < position['cost'] * 0.92:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and rsi < 30:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 15: MACD 金叉死叉 ==============
def backtest_macd(df):
    """MACD 金叉死叉策略"""
    if len(df) < 100:
        return None
    
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['dif'] = ema12 - ema26
    df['dea'] = df['dif'].ewm(span=9).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        dif = df['dif'].iloc[idx]
        dea = df['dea'].iloc[idx]
        dif_prev = df['dif'].iloc[idx-1]
        dea_prev = df['dea'].iloc[idx-1]
        
        if pd.isna([dif, dea, dif_prev, dea_prev]).any():
            continue
        
        if position:
            if dif < dea and dif_prev >= dea_prev:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and dif > dea and dif_prev <= dea_prev:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 16: 三重均线 ==============
def backtest_triple_ma(df):
    """三重均线策略 (MA5/10/20)"""
    if len(df) < 50:
        return None
    
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(30, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        ma5 = df['ma5'].iloc[idx]
        ma10 = df['ma10'].iloc[idx]
        ma20 = df['ma20'].iloc[idx]
        
        if pd.isna([ma5, ma10, ma20]).any():
            continue
        
        if position:
            if not (ma5 > ma10 > ma20):
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and ma5 > ma10 > ma20:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 17: 延迟入场 ==============
def backtest_delay_entry(df):
    """延迟入场策略"""
    if len(df) < 80:
        return None
    
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    signal_day = 0
    
    for idx in range(50, len(df)):
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
            if ma15 < ma20 or price < position['cost'] * 0.90:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        elif signal_day > 0:
            signal_day += 1
            if signal_day == 3 and ma15 > ma20:
                shares = int(capital * 0.95 / price / 100) * 100
                if shares > 0:
                    position = {'cost': price, 'shares': shares}
                    signal_day = 0
        elif ma15 > ma20 and ma15_prev <= ma20_prev:
            signal_day = 1
    
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append(profit)
    
    if not trades:
        return None
    
    profitable = [t for t in trades if t > 0]
    return {
        'return': (capital/100000-1)*100,
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 策略 18: 成交量萎缩 ==============
def backtest_volume_shrink(df):
    """成交量萎缩策略"""
    if len(df) < 100:
        return None
    
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    capital = 100000
    position = None
    trades = []
    
    for idx in range(50, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        vol = df['volume'].iloc[idx]
        vol_ma = df['vol_ma20'].iloc[idx]
        ma10 = df['ma10'].iloc[idx]
        ma20 = df['ma20'].iloc[idx]
        
        if pd.isna([vol, vol_ma, ma10, ma20]).any():
            continue
        
        vol_shrink = vol < vol_ma * 0.6
        
        if position:
            if price < position['cost'] * 0.92 or price > position['cost'] * 1.15:
                profit = (price - position['cost']) / position['cost'] * 100
                trades.append(profit)
                capital = position['shares'] * price * 0.9997
                position = None
        
        if not position and vol_shrink and price > ma10 > ma20:
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
        'win_rate': len(profitable)/len(trades)*100 if trades else 0,
        'trades': len(trades),
    }


# ============== 主回测函数 ==============
def backtest_all_strategies():
    """全市场回测 18 个策略"""
    print("=" * 80)
    print("📊 18 个策略全市场回测对比报告")
    print(f"📅 回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    total_stocks = len(stock_files)
    
    print(f"\n📋 测试策略:")
    strategies_info = [
        ("双均线 MA15/20", "基准策略"),
        ("移动止盈 15%", "MA15/20+ 移动止盈"),
        ("移动止盈 10%", "MA15/20+ 移动止盈"),
        ("平台突破", "20 日平台突破"),
        ("涨停板", "追涨停策略"),
        ("低位十字星", "RSI<30+ 十字星"),
        ("均线粘合突破", "MA5/10/20 粘合<3%"),
        ("缺口回补", "向下缺口博弈"),
        ("龙头股回调", "20 日涨 30%+ 回调"),
        ("布林带下轨反弹", "触及下轨+RSI<30"),
        ("KDJ 超卖金叉", "K<20,D<20, 金叉"),
        ("量价背离", "股价新低 + 成交量缩"),
        ("缠论 + 蜡烛图", "底分型 + 蜡烛图"),
        ("RSI 超买超卖", "RSI<30 买入/>70 卖出"),
        ("MACD 金叉死叉", "DIF 上穿/下穿 DEA"),
        ("三重均线", "MA5>MA10>MA20"),
        ("延迟入场", "金叉后延迟 3 天"),
        ("成交量萎缩", "vol<0.6*vol_ma20"),
    ]
    
    for i, (name, desc) in enumerate(strategies_info, 1):
        print(f"   {i:2d}. {name:<15} - {desc}")
    
    print(f"\n📁 数据源：{CACHE_DIR}")
    print(f"🔍 全市场 {total_stocks} 只股票")
    print("\n⏳ 开始回测...\n")
    
    # 策略映射
    strategy_funcs = {
        'ma_base': backtest_ma_base,
        'ma_trailing_15': backtest_ma_trailing_15,
        'ma_trailing_10': backtest_ma_trailing_10,
        'platform': backtest_platform_breakout,
        'limit_up': backtest_limit_up,
        'doji': backtest_doji,
        'ma_squeeze': backtest_ma_squeeze,
        'gap_fill': backtest_gap_fill,
        'leader': backtest_leader_pullback,
        'bollinger': backtest_bollinger_rebound,
        'kdj': backtest_kdj_oversold,
        'divergence': backtest_volume_price_divergence,
        'chanlun': backtest_chanlun_candle,
        'rsi': backtest_rsi,
        'macd': backtest_macd,
        'triple_ma': backtest_triple_ma,
        'delay': backtest_delay_entry,
        'volume_shrink': backtest_volume_shrink,
    }
    
    strategy_names = {
        'ma_base': '双均线 MA15/20',
        'ma_trailing_15': '移动止盈 15%',
        'ma_trailing_10': '移动止盈 10%',
        'platform': '平台突破',
        'limit_up': '涨停板',
        'doji': '低位十字星',
        'ma_squeeze': '均线粘合突破',
        'gap_fill': '缺口回补',
        'leader': '龙头股回调',
        'bollinger': '布林带下轨反弹',
        'kdj': 'KDJ 超卖金叉',
        'divergence': '量价背离',
        'chanlun': '缠论 + 蜡烛图',
        'rsi': 'RSI 超买超卖',
        'macd': 'MACD 金叉死叉',
        'triple_ma': '三重均线',
        'delay': '延迟入场',
        'volume_shrink': '成交量萎缩',
    }
    
    results = {key: [] for key in strategy_funcs.keys()}
    
    for i, filepath in enumerate(stock_files):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is None:
            continue
        
        for key, func in strategy_funcs.items():
            r = func(df)
            if r:
                r['symbol'] = symbol
                results[key].append(r)
        
        if (i + 1) % 200 == 0:
            print(f"  进度：{i+1}/{total_stocks} ({(i+1)/total_stocks*100:.1f}%) - 已处理 {sum(len(v) for v in results.values())} 条结果")
            sys.stdout.flush()
    
    print(f"\n✅ 回测完成，共处理 {total_stocks} 只股票\n")
    
    # 生成报告
    generate_report(results, strategy_names)
    
    # 保存结果
    save_results(results, strategy_names)
    
    return results


def generate_report(results, strategy_names):
    """生成对比报告"""
    print("=" * 80)
    print("📊 策略对比报告")
    print("=" * 80)
    
    print(f"\n{'策略':<18} {'平均收益':>12} {'中位收益':>12} {'胜率':>10} {'盈利股':>10} {'交易':>8}")
    print("-" * 85)
    
    summary = []
    
    for key, name in strategy_names.items():
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
            'count': len(r),
        })
        
        print(f"{name:<18} {avg_return:>10.2f}% {median_return:>10.2f}% {avg_winrate:>8.1f}% {profitable_ratio:>8.1f}% {avg_trades:>8.1f}")
    
    print("-" * 85)
    
    # 排名
    summary.sort(key=lambda x: x['avg_return'], reverse=True)
    
    print("\n" + "=" * 80)
    print("🏆 策略排名")
    print("=" * 80)
    
    for i, s in enumerate(summary, 1):
        medal = '🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else '  '
        print(f"{medal} {i:2d}. {s['name']}: {s['avg_return']:+.2f}%")
    
    # 最佳策略详情
    best = summary[0]
    print(f"\n" + "=" * 80)
    print(f"🏆 最佳策略：{best['name']}")
    print("=" * 80)
    print(f"   平均收益：{best['avg_return']:+.2f}%")
    print(f"   中位收益：{best['median_return']:+.2f}%")
    print(f"   胜率：{best['win_rate']:.1f}%")
    print(f"   盈利股票：{best['profitable_ratio']:.1f}%")
    print(f"   平均交易：{best['trades']:.1f}次")
    print(f"   测试股票：{best['count']}只")
    
    # TOP5 股票
    best_results = results[best['key']]
    best_results.sort(key=lambda x: x['return'], reverse=True)
    
    print(f"\n🏆 {best['name']} TOP 5 股票:")
    for i, r in enumerate(best_results[:5], 1):
        print(f"  {i}. {r['symbol']}: {r['return']:+.2f}% (胜率{r['win_rate']:.1f}%)")
    
    # 综合历史回测
    print("\n" + "=" * 80)
    print("📊 综合历次回测（18 个策略）")
    print("=" * 80)
    print("\n本次回测排名:")
    for i, s in enumerate(summary[:10], 1):
        print(f"  {i:2d}. {s['name']}: {s['avg_return']:+.2f}%")
    
    print("\n" + "=" * 80)


def save_results(results, strategy_names):
    """保存结果到文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = REPORT_DIR / f'backtest_18_strategies_{timestamp}.json'
    
    summary = []
    for key, name in strategy_names.items():
        r = results[key]
        if not r:
            continue
        
        summary.append({
            'key': key,
            'name': name,
            'avg_return': float(np.mean([x['return'] for x in r])),
            'median_return': float(np.median([x['return'] for x in r])),
            'win_rate': float(np.mean([x['win_rate'] for x in r])),
            'profitable_ratio': float(len([x for x in r if x['return'] > 0]) / len(r) * 100),
            'trades': float(np.mean([x['trades'] for x in r])),
            'count': len(r),
        })
    
    summary.sort(key=lambda x: x['avg_return'], reverse=True)
    
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'total_stocks': len(list(CACHE_DIR.glob('*.json'))),
        'strategies': summary,
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 报告已保存：{report_file}")


if __name__ == '__main__':
    results = backtest_all_strategies()
