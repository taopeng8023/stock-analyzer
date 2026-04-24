#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
600163 全面分析 - 4 月 TOP 推荐第 2 名
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

def load_data(symbol):
    filepath = CACHE_DIR / f'{symbol}.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume'
    })
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df.sort_values('date').reset_index(drop=True)

def analyze(symbol):
    df = load_data(symbol)
    
    # 计算指标
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma200'] = df['close'].rolling(200).mean()
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    
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
    
    # 最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    prev5 = df.iloc[-5]
    prev20 = df.iloc[-20]
    
    print("=" * 80)
    print(f"📊 600163 全面分析 - 4 月 TOP 推荐第 2 名")
    print(f"📅 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    print(f"\n💰 基本信息")
    print(f"   现价：¥{latest['close']:.2f}")
    print(f"   今日涨跌：{(latest['close'] - prev['close']) / prev['close'] * 100:+.2f}%")
    print(f"   5 日涨跌：{(latest['close'] - prev5['close']) / prev5['close'] * 100:+.2f}%")
    print(f"   20 日涨跌：{(latest['close'] - prev20['close']) / prev20['close'] * 100:+.2f}%")
    
    print(f"\n📊 均线系统")
    print(f"   MA5:  ¥{latest['ma5']:.2f} | {'✅ 上穿' if latest['close'] > latest['ma5'] else '❌ 下穿'}")
    print(f"   MA10: ¥{latest['ma10']:.2f} | {'✅ 上穿' if latest['close'] > latest['ma10'] else '❌ 下穿'}")
    print(f"   MA15: ¥{latest['ma15']:.2f} | {'✅ 上穿' if latest['close'] > latest['ma15'] else '❌ 下穿'}")
    print(f"   MA20: ¥{latest['ma20']:.2f} | {'✅ 上穿' if latest['close'] > latest['ma20'] else '❌ 下穿'}")
    print(f"   MA60: ¥{latest['ma60']:.2f} | {'✅ 上穿' if latest['close'] > latest['ma60'] else '❌ 下穿'}")
    print(f"   MA200: ¥{latest['ma200']:.2f} | {'✅ 上穿' if latest['close'] > latest['ma200'] else '❌ 下穿'}")
    
    # 金叉状态
    ma15_ma20 = latest['ma15'] - latest['ma20']
    print(f"\n   MA15/MA20 差值：{ma15_ma20:.2f} ({ma15_ma20 / latest['ma20'] * 100:+.2f}%)")
    if ma15_ma20 > 0:
        print(f"   ✅ 金叉状态")
    else:
        print(f"   ❌ 死叉状态")
    
    print(f"\n📊 成交量")
    vol_ratio = latest['volume'] / latest['vol_ma20'] if latest['vol_ma20'] > 0 else 0
    print(f"   当日成交量：{latest['volume']:,.0f}手")
    print(f"   20 日均量：{latest['vol_ma20']:,.0f}手")
    print(f"   成交量比：{vol_ratio:.2f}倍 {'✅ 放量' if vol_ratio > 1.5 else '👍 正常' if vol_ratio > 1 else '⚠️ 缩量'}")
    
    print(f"\n📊 技术指标")
    rsi = latest['rsi']
    print(f"   RSI(14): {rsi:.1f} {'⚠️ 超买' if rsi > 70 else '✅ 健康' if 50 < rsi < 70 else '⚠️ 超卖'}")
    print(f"   MACD: {latest['macd']:.3f} | Signal: {latest['macd_signal']:.3f}")
    if latest['macd'] > latest['macd_signal']:
        print(f"   ✅ MACD 金叉")
    else:
        print(f"   ❌ MACD 死叉")
    
    # 评分
    score = 0
    reasons = []
    warnings = []
    
    if latest['ma15'] > latest['ma20']:
        score += 2
        reasons.append("✅ MA15/20 金叉")
    else:
        warnings.append("⚠️ MA15/20 死叉")
    
    if latest['close'] > latest['ma60']:
        score += 2
        reasons.append(f"✅ 股价>MA60 ({(latest['close']-latest['ma60'])/latest['ma60']*100:+.1f}%)")
    else:
        warnings.append("⚠️ 股价<MA60")
    
    if latest['close'] > latest['ma200']:
        score += 1
        reasons.append("✅ 长期趋势向上")
    
    if vol_ratio > 1.5:
        score += 2
        reasons.append(f"✅ 放量{vol_ratio:.1f}倍")
    elif vol_ratio > 1:
        score += 1
        reasons.append("👍 成交量正常")
    else:
        warnings.append("⚠️ 缩量")
    
    if 50 < rsi < 70:
        score += 2
        reasons.append(f"✅ RSI 理想({rsi:.0f})")
    elif 45 < rsi < 75:
        score += 1
        reasons.append(f"👍 RSI 可接受({rsi:.0f})")
    else:
        warnings.append(f"⚠️ RSI{'超买' if rsi>70 else '超卖'}({rsi:.0f})")
    
    if latest['macd'] > latest['macd_signal']:
        score += 1
        reasons.append("✅ MACD 金叉")
    else:
        warnings.append("⚠️ MACD 死叉")
    
    print(f"\n💡 综合评分：{score}/8")
    
    print(f"\n✅ 优势:")
    for r in reasons:
        print(f"   {r}")
    
    if warnings:
        print(f"\n⚠️ 风险:")
        for w in warnings:
            print(f"   {w}")
    
    # 目标价和止损
    target = latest['close'] * 1.10
    stop_loss = latest['close'] * 0.85
    
    print(f"\n🎯 操作建议")
    print(f"   建议：{'🟢 强烈买入' if score >= 8 else '🟢 可买入' if score >= 6 else '🟡 观望' if score >= 4 else '🔴 回避'}")
    print(f"   目标价：¥{target:.2f} (+10%)")
    print(f"   止损价：¥{stop_loss:.2f} (-15%)")
    
    # 与持仓对比
    print(f"\n📊 与主人持仓对比")
    print(f"   天赐材料 (002709): 10/8 分，¥48.17 (-0.17%)")
    print(f"   600163: {score}/8 分，¥{latest['close']:.2f}")
    
    if score >= 8:
        print(f"\n✅ 600163 与天赐材料同为优质股，建议配置！")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    analyze('600163')
