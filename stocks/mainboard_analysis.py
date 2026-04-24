#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主板股票详细分析脚本
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")

# 主板股票列表（从选股结果中筛选）
MAINBOARD_STOCKS = [
    '603233', '603171', '600410', '002737', '002642', '002073', '603330', '603232'
]

def load_stock_data(code):
    """加载股票数据"""
    # 数据文件无后缀
    file_path = HISTORY_DIR / f"{code}.json"
    
    if not file_path.exists():
        return None
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    items = data.get('items', [])
    fields = data.get('fields', [])
    
    if not items or not fields:
        return None
    
    # 转 正序
    idx_map = {name: i for i, name in enumerate(fields)}
    df_data = []
    for item in reversed(items):
        row = {
            'date': item[idx_map['trade_date']],
            'open': item[idx_map['open']],
            'high': item[idx_map['high']],
            'low': item[idx_map['low']],
            'close': item[idx_map['close']],
            'vol': item[idx_map['vol']],
            'pct_chg': item[idx_map['pct_chg']]
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    return df

def calc_ma(df, period):
    """计算移动平均"""
    return df['close'].rolling(period).mean()

def calc_ema(df, period):
    """计算指数移动平均"""
    return df['close'].ewm(span=period, adjust=False).mean()

def calc_macd(df):
    """计算 MACD"""
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd.iloc[-1], signal.iloc[-1], hist.iloc[-1]

def calc_kdj(df):
    """计算 KDJ"""
    low_9 = df['low'].rolling(9).min()
    high_9 = df['high'].rolling(9).max()
    rsv = 100 * (df['close'] - low_9) / (high_9 - low_9 + 1e-10)
    
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k.iloc[-1], d.iloc[-1], j.iloc[-1]

def calc_rsi(df, period=14):
    """计算 RSI (Wilders 法)"""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - 100 / (1 + rs)
    return rsi.iloc[-1]

def calc_boll(df, period=20):
    """计算布林带"""
    ma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    
    close = df['close'].iloc[-1]
    ma_val = ma.iloc[-1]
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]
    
    position = (close - lower_val) / (upper_val - lower_val + 1e-10) * 100
    
    return ma_val, upper_val, lower_val, position

def analyze_stock(code):
    """分析单只股票"""
    df = load_stock_data(code)
    if df is None or len(df) < 60:
        return None
    
    # 基本信息
    current_price = df['close'].iloc[-1]
    today_change = df['pct_chg'].iloc[-1]
    
    # 均线
    ma5 = calc_ma(df, 5).iloc[-1]
    ma10 = calc_ma(df, 10).iloc[-1]
    ma20 = calc_ma(df, 20).iloc[-1]
    ma60 = calc_ma(df, 60).iloc[-1]
    
    # MACD
    macd, signal, hist = calc_macd(df)
    
    # KDJ
    k, d, j = calc_kdj(df)
    
    # RSI
    rsi = calc_rsi(df)
    
    # 布林带
    boll_ma, boll_upper, boll_lower, boll_pos = calc_boll(df)
    
    # 涨跌幅统计
    high_20 = df['high'].rolling(20).max().iloc[-1]
    low_20 = df['low'].rolling(20).min().iloc[-1]
    drop_from_high = (high_20 - current_price) / high_20 * 100
    
    # 10 日跌幅
    if len(df) > 10:
        price_10d = df['close'].iloc[-11]
        drop_10d = (price_10d - current_price) / price_10d * 100
    else:
        drop_10d = 0
    
    # 成交量
    vol_ma5 = df['vol'].rolling(5).mean().iloc[-1]
    vol_ma20 = df['vol'].rolling(20).mean().iloc[-1]
    vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1
    
    # 资金流代理
    money_flow = (df['vol'] * df['pct_chg'] / 1e6).iloc[-1]
    
    return {
        'code': code,
        'price': current_price,
        'change': today_change,
        'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'macd': macd, 'macd_signal': signal, 'macd_hist': hist,
        'kdj_k': k, 'kdj_d': d, 'kdj_j': j,
        'rsi': rsi,
        'boll_ma': boll_ma, 'boll_upper': boll_upper, 'boll_lower': boll_lower, 'boll_pos': boll_pos,
        'high_20': high_20, 'low_20': low_20, 'drop_from_high': drop_from_high,
        'drop_10d': drop_10d,
        'vol_ratio': vol_ratio,
        'money_flow': money_flow
    }

def generate_analysis(code):
    """生成详细分析报告"""
    data = analyze_stock(code)
    if not data:
        return f"❌ {code} 数据不足"
    
    report = []
    report.append(f"\n{'='*60}")
    report.append(f"📊 {code} 详细技术分析")
    report.append(f"{'='*60}")
    
    # 基本信息
    report.append(f"\n【基本信息】")
    report.append(f"  现价：¥{data['price']:.2f}  今日：{data['change']:+.2f}%")
    report.append(f"  20 日最高：¥{data['high_20']:.2f}  最低：¥{data['low_20']:.2f}")
    report.append(f"  距高点回撤：{data['drop_from_high']:.1f}%")
    report.append(f"  10 日跌幅：{data['drop_10d']:.1f}%")
    
    # 均线系统
    report.append(f"\n【均线系统】")
    report.append(f"  MA5:  ¥{data['ma5']:.2f}  {'✓站上' if data['price'] >= data['ma5'] else '✗跌破'}")
    report.append(f"  MA10: ¥{data['ma10']:.2f}  {'✓站上' if data['price'] >= data['ma10'] else '✗跌破'}")
    report.append(f"  MA20: ¥{data['ma20']:.2f}  {'✓站上' if data['price'] >= data['ma20'] else '✗跌破'}")
    report.append(f"  MA60: ¥{data['ma60']:.2f}  {'✓站上' if data['price'] >= data['ma60'] else '✗跌破'}")
    
    # 多头排列判断
    ma_bullish = data['ma5'] >= data['ma10'] >= data['ma20']
    report.append(f"  均线形态：{'🟢 多头排列' if ma_bullish else '🔴 空头/混乱'}")
    
    # MACD
    report.append(f"\n【MACD 指标】")
    report.append(f"  DIF: {data['macd']:.4f}  DEA: {data['macd_signal']:.4f}  柱：{data['macd_hist']:.4f}")
    macd_bullish = data['macd'] > data['macd_signal']
    report.append(f"  状态：{'🟢 金叉 (多头)' if macd_bullish else '🔴 死叉 (空头)'}")
    
    # KDJ
    report.append(f"\n【KDJ 指标】")
    report.append(f"  K: {data['kdj_k']:.1f}  D: {data['kdj_d']:.1f}  J: {data['kdj_j']:.1f}")
    if data['kdj_k'] > 80:
        report.append(f"  状态：🔴 超买区")
    elif data['kdj_k'] < 20:
        report.append(f"  状态：🟢 超卖区")
    else:
        report.append(f"  状态：⚪ 中性区")
    
    # RSI
    report.append(f"\n【RSI 指标】")
    report.append(f"  RSI(14): {data['rsi']:.1f}")
    if data['rsi'] > 70:
        report.append(f"  状态：🔴 超买")
    elif data['rsi'] < 30:
        report.append(f"  状态：🟢 超卖")
    else:
        report.append(f"  状态：⚪ 中性")
    
    # 布林带
    report.append(f"\n【布林带】")
    report.append(f"  中轨：¥{data['boll_ma']:.2f}  上轨：¥{data['boll_upper']:.2f}  下轨：¥{data['boll_lower']:.2f}")
    report.append(f"  位置：{data['boll_pos']:.1f}% ({'上轨附近' if data['boll_pos'] > 80 else '中轨附近' if data['boll_pos'] > 40 else '下轨附近'})")
    
    # 成交量
    report.append(f"\n【成交量】")
    report.append(f"  量比：{data['vol_ratio']:.2f} ({'放量' if data['vol_ratio'] > 1.5 else '缩量' if data['vol_ratio'] < 0.8 else '正常'})")
    report.append(f"  资金流：{data['money_flow']:+.2f}万")
    
    # 综合评分
    score = 0
    if data['price'] >= data['ma10']: score += 2
    if data['price'] >= data['ma20']: score += 1
    if macd_bullish: score += 2
    if data['rsi'] < 40: score += 2
    if data['kdj_k'] < 30: score += 1
    if data['drop_from_high'] > 10: score += 1
    if data['vol_ratio'] > 1.2: score += 1
    
    report.append(f"\n【综合评分】")
    report.append(f"  得分：{score}/10")
    if score >= 7:
        report.append(f"  评级：⭐⭐⭐⭐⭐ 强烈推荐")
    elif score >= 5:
        report.append(f"  评级：⭐⭐⭐⭐ 推荐")
    elif score >= 3:
        report.append(f"  评级：⭐⭐⭐ 观望")
    else:
        report.append(f"  评级：⭐⭐ 谨慎")
    
    # 操作建议
    report.append(f"\n【操作建议】")
    if score >= 7:
        report.append(f"  ✅ 建议建仓，仓位 30%")
        report.append(f"  止损：¥{data['price'] * 0.92:.2f} (-8%)")
        report.append(f"  止盈：¥{data['price'] * 1.10:.2f} (+10%)")
    elif score >= 5:
        report.append(f"  ⚠️ 可轻仓试探，仓位 15-20%")
        report.append(f"  止损：¥{data['price'] * 0.92:.2f} (-8%)")
    else:
        report.append(f"  ⏸️ 建议观望，等待更好信号")
    
    return '\n'.join(report)

def main():
    """主函数"""
    print(f"\n{'='*60}")
    print("📈 主板股票详细技术分析")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 筛选主板股票
    mainboard_candidates = [code for code in MAINBOARD_STOCKS if code.startswith(('60', '000', '001', '002'))]
    
    print(f"\n共分析 {len(mainboard_candidates)} 只主板股票:")
    print(f"  {', '.join(mainboard_candidates)}")
    
    for code in mainboard_candidates:
        report = generate_analysis(code)
        print(report)

if __name__ == '__main__':
    main()
