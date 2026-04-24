#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票深度分析 - 002709
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

def load_data(symbol: str) -> pd.DataFrame:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    df = df.rename(columns={
        '日期': 'date',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount'
    })
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.sort_values('date').reset_index(drop=True)
    return df

def analyze(symbol: str):
    """深度分析"""
    print("=" * 80)
    print(f"📊 {symbol} 深度分析报告")
    print(f"📅 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    df = load_data(symbol)
    
    # 计算技术指标
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma200'] = df['close'].rolling(200).mean()
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 布林带
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
    # 最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    prev5 = df.iloc[-5]
    prev20 = df.iloc[-20]
    
    print("\n" + "=" * 80)
    print("📈 基本信息")
    print("=" * 80)
    print(f"💰 当前价：¥{latest['close']:.2f}")
    print(f"📊 今日涨跌：{(latest['close'] - prev['close']) / prev['close'] * 100:+.2f}%")
    print(f"📅 数据日期：{latest['date'].strftime('%Y-%m-%d')}")
    print(f"📈 5 日涨跌：{(latest['close'] - prev5['close']) / prev5['close'] * 100:+.2f}%")
    print(f"📈 20 日涨跌：{(latest['close'] - prev20['close']) / prev20['close'] * 100:+.2f}%")
    
    print("\n" + "=" * 80)
    print("📊 均线系统")
    print("=" * 80)
    print(f"MA5:  ¥{latest['ma5']:.2f} | 股价{'上' if latest['close'] > latest['ma5'] else '下'}穿")
    print(f"MA10: ¥{latest['ma10']:.2f} | 股价{'上' if latest['close'] > latest['ma10'] else '下'}穿")
    print(f"MA15: ¥{latest['ma15']:.2f} | 股价{'上' if latest['close'] > latest['ma15'] else '下'}穿")
    print(f"MA20: ¥{latest['ma20']:.2f} | 股价{'上' if latest['close'] > latest['ma20'] else '下'}穿")
    print(f"MA60: ¥{latest['ma60']:.2f} | 股价{'上' if latest['close'] > latest['ma60'] else '下'}穿")
    print(f"MA200: ¥{latest['ma200']:.2f} | 股价{'上' if latest['close'] > latest['ma200'] else '下'}穿")
    
    # 金叉状态
    ma15_ma20_cross = latest['ma15'] - latest['ma20']
    print(f"\n🎯 MA15/MA20 差值：{ma15_ma20_cross:.2f} ({ma15_ma20_cross / latest['ma20'] * 100:+.2f}%)")
    if ma15_ma20_cross > 0:
        print("✅ 金叉状态 (MA15 > MA20)")
    else:
        print("❌ 死叉状态 (MA15 < MA20)")
    
    print("\n" + "=" * 80)
    print("📊 成交量分析")
    print("=" * 80)
    vol_ratio = latest['volume'] / latest['volume_ma20']
    print(f"当日成交量：{latest['volume']:,.0f}手")
    print(f"20 日均量：{latest['volume_ma20']:,.0f}手")
    print(f"成交量比：{vol_ratio:.2f}倍 {'✅ 放量' if vol_ratio > 1.5 else '👍 正常' if vol_ratio > 1 else '⚠️ 缩量'}")
    
    print("\n" + "=" * 80)
    print("📊 技术指标")
    print("=" * 80)
    print(f"RSI(14): {latest['rsi']:.1f} {'⚠️ 超买' if latest['rsi'] > 70 else '✅ 健康' if 50 < latest['rsi'] < 70 else '⚠️ 超卖'}")
    print(f"MACD: {latest['macd']:.3f} | Signal: {latest['macd_signal']:.3f} | Hist: {latest['macd_hist']:.3f}")
    if latest['macd'] > latest['macd_signal']:
        print("✅ MACD 金叉 (多头)")
    else:
        print("❌ MACD 死叉 (空头)")
    
    print("\n" + "=" * 80)
    print("📊 布林带")
    print("=" * 80)
    bb_position = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower']) * 100
    print(f"上轨：¥{latest['bb_upper']:.2f}")
    print(f"中轨：¥{latest['bb_mid']:.2f}")
    print(f"下轨：¥{latest['bb_lower']:.2f}")
    print(f"股价位置：{bb_position:.1f}% {'⚠️ 接近上轨' if bb_position > 80 else '✅ 中部' if bb_position > 20 else '⚠️ 接近下轨'}")
    
    print("\n" + "=" * 80)
    print("🎯 支撑/压力位")
    print("=" * 80)
    # 近期高低点
    recent_high = df['high'].iloc[-20:].max()
    recent_low = df['low'].iloc[-20:].min()
    print(f"20 日最高：¥{recent_high:.2f} (压力位)")
    print(f"20 日最低：¥{recent_low:.2f} (支撑位)")
    print(f"当前位置：{(latest['close'] - recent_low) / (recent_high - recent_low) * 100:.1f}% 区间")
    
    print("\n" + "=" * 80)
    print("💡 综合评分")
    print("=" * 80)
    
    score = 0
    reasons = []
    
    # 均线评分
    if latest['close'] > latest['ma15'] > latest['ma20']:
        score += 2
        reasons.append("✅ 多头排列")
    elif latest['close'] > latest['ma20']:
        score += 1
        reasons.append("👍 站上 MA20")
    
    # 趋势评分
    if latest['close'] > latest['ma60']:
        score += 2
        reasons.append("✅ 中期趋势向上")
    if latest['close'] > latest['ma200']:
        score += 1
        reasons.append("✅ 长期趋势向上")
    
    # 成交量评分
    if vol_ratio > 1.5:
        score += 2
        reasons.append(f"✅ 放量 {vol_ratio:.2f}倍")
    elif vol_ratio > 1:
        score += 1
        reasons.append("👍 成交量正常")
    
    # RSI 评分
    if 50 < latest['rsi'] < 70:
        score += 2
        reasons.append(f"✅ RSI 理想 ({latest['rsi']:.1f})")
    elif 45 < latest['rsi'] < 75:
        score += 1
        reasons.append(f"👍 RSI 可接受 ({latest['rsi']:.1f})")
    
    # MACD 评分
    if latest['macd'] > latest['macd_signal']:
        score += 1
        reasons.append("✅ MACD 金叉")
    
    print(f"综合评分：{score}/8")
    win_prob = 30 + (score / 8) * 55
    print(f"盈利概率：{win_prob:.1f}%")
    
    print("\n✅ 优势:")
    for r in reasons:
        print(f"   {r}")
    
    print("\n" + "=" * 80)
    print("🎯 操作建议")
    print("=" * 80)
    target = latest['close'] * 1.10
    stop_loss = latest['close'] * 0.85
    print(f"📈 目标价：¥{target:.2f} (+10%)")
    print(f"🛑 止损位：¥{stop_loss:.2f} (-15%)")
    print(f"💡 建议：{'🟢 可买入' if score >= 6 else '🟡 观望' if score >= 4 else '🔴 回避'}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    analyze('002709')
